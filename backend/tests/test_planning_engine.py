"""Module 7 state-space search and Module 6 integration tests."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.compliance.agent import ComplianceAgent
from app.compliance.models import Constraint
from app.planning.actions import build_improvement_actions
from app.planning.agent import ImprovementPlanningAgent
from app.planning.models import Condition, ImprovementAction, PaperState, PlanningValidationError, StateEffect
from app.planning.search import PlanningProblem, SearchPlanner
from app.services.knowledge_engine import KnowledgeEngine
from main import app


def action(
    identifier: str,
    name: str,
    condition: Condition,
    effect: StateEffect,
    cost: int,
) -> ImprovementAction:
    return ImprovementAction(identifier, name, (condition,), (effect,), cost, (effect.variable,), f'{name} explanation.')


def simple_problem() -> PlanningProblem:
    goal = Constraint('C001', 'target_x', ('X',), 'EQUALS', 2, 'ERROR', 'X must reach two.')
    return PlanningProblem(
        PaperState.from_dict({'X': 0}),
        (
            action('A001', 'Direct', Condition('X', 'EQUALS', 0), StateEffect('X', 'SET', 2), 5),
            action('A002', 'FirstStep', Condition('X', 'EQUALS', 0), StateEffect('X', 'SET', 1), 1),
            action('A003', 'SecondStep', Condition('X', 'EQUALS', 1), StateEffect('X', 'SET', 2), 1),
            action('A004', 'LoopBack', Condition('X', 'EQUALS', 1), StateEffect('X', 'SET', 0), 1),
        ),
        (goal,),
    )


def module_2_document(
    *,
    pages: int = 8,
    abstract_words: int = 320,
    keywords: list[str] | None = None,
    references: int = 10,
) -> dict:
    return {
        'document': {'filename': 'planning-paper.pdf', 'file_size': 2048, 'page_count': pages},
        'metadata': {
            'title': 'Planning Test Paper', 'title_confidence': 'high', 'authors': ['A. Author'],
            'authors_confidence': 'high', 'abstract': 'Abstract text.', 'abstract_word_count': abstract_words,
            'keywords': [] if keywords is None else keywords,
        },
        'sections': [
            {'number': '1', 'title': 'Introduction', 'text': 'Context.', 'page_start': 1, 'page_end': 1},
            {'number': '2', 'title': 'Methodology', 'text': 'Method.', 'page_start': 2, 'page_end': 2},
            {'number': '3', 'title': 'Results', 'text': 'Results.', 'page_start': 3, 'page_end': 3},
            {'number': '4', 'title': 'Conclusion', 'text': 'Conclusion.', 'page_start': 4, 'page_end': 4},
        ],
        'references': [{'number': index, 'text': f'Reference {index}'} for index in range(1, references + 1)],
        'figures': [], 'tables': [], 'statistics': {}, 'warnings': [],
    }


def compliance_result(
    *,
    pages: int = 8,
    abstract_words: int = 320,
    keywords: list[str] | None = None,
    references: int = 10,
    requirements: dict | None = None,
) -> dict:
    knowledge_base, validation = KnowledgeEngine().build(module_2_document(
        pages=pages, abstract_words=abstract_words, keywords=keywords, references=references,
    ))
    assert validation['valid'] is True
    return ComplianceAgent().analyze(knowledge_base, {
        'profile_id': 'custom',
        'venue': 'Planning Venue',
        'requirements': requirements if requirements is not None else {
            'max_pages': 6, 'max_abstract_words': 250, 'keywords_required': True, 'min_references': 15,
        },
    })


def test_paper_state_is_immutable_equal_and_serializable() -> None:
    first = PaperState.from_dict({'ReferenceCount': 10, 'PageCount': 8})
    second = PaperState.from_dict({'PageCount': 8, 'ReferenceCount': 10})

    assert first == second
    assert first.to_dict() == {'PageCount': 8, 'ReferenceCount': 10}
    assert first.with_updates({'PageCount': 6}).to_dict()['PageCount'] == 6


def test_action_preconditions_transition_and_cost() -> None:
    reduce_pages = action('A001', 'ReducePageCount', Condition('PageCount', 'GREATER_THAN', 6), StateEffect('PageCount', 'SET', 6), 4)
    current = PaperState.from_dict({'PageCount': 8})

    assert reduce_pages.is_applicable(current) is True
    assert reduce_pages.apply(current).to_dict() == {'PageCount': 6}
    assert reduce_pages.cost == 4
    assert reduce_pages.is_applicable(PaperState.from_dict({'PageCount': 6})) is False
    with pytest.raises(PlanningValidationError):
        reduce_pages.apply(PaperState.from_dict({'PageCount': 6}))


def test_goal_can_be_already_satisfied_or_reached_after_actions() -> None:
    problem = simple_problem()
    already = PlanningProblem(PaperState.from_dict({'X': 2}), problem.actions, problem.constraints)

    assert already.goal_evaluation(already.initial_state).reached is True
    assert problem.goal_evaluation(problem.initial_state).reached is False
    result = SearchPlanner().solve(problem, 'ucs')
    assert result['status'] == 'PLAN_FOUND'
    assert result['final_state'] == {'X': 2}


def test_ucs_selects_the_lower_cost_plan_and_prunes_duplicates() -> None:
    result = SearchPlanner().solve(simple_problem(), 'ucs')

    assert result['total_cost'] == 2
    assert [item['id'] for item in result['actions']] == ['A002', 'A003']
    assert any(item['event'] == 'STATE_PRUNED' and item['reason'] == 'duplicate_or_higher_cost_state' for item in result['trace'])


def test_astar_uses_an_explainable_admissible_heuristic_and_finds_plan() -> None:
    result = SearchPlanner().solve(simple_problem(), 'astar')

    assert result['status'] == 'PLAN_FOUND'
    assert result['total_cost'] == 2
    assert result['heuristic']['admissible'] is True
    assert any(item['event'] == 'HEURISTIC_CALCULATED' for item in result['trace'])


def test_astar_heuristic_ignores_prerequisites_and_keeps_the_low_cost_path() -> None:
    target = Constraint('C001', 'target_x', ('X',), 'EQUALS', 2, 'ERROR', 'X must reach two.')
    problem = PlanningProblem(
        PaperState.from_dict({'X': 0, 'Y': 0}),
        (
            action('A001', 'ExpensiveDirect', Condition('X', 'EQUALS', 0), StateEffect('X', 'SET', 2), 10),
            action('A002', 'PrepareOne', Condition('Y', 'EQUALS', 0), StateEffect('Y', 'SET', 1), 1),
            action('A003', 'PrepareTwo', Condition('Y', 'EQUALS', 1), StateEffect('Y', 'SET', 2), 1),
            ImprovementAction(
                'A004', 'CheapFinish',
                (Condition('Y', 'EQUALS', 2), Condition('X', 'EQUALS', 0)),
                (StateEffect('X', 'SET', 2),), 1, ('X',), 'Finish after prerequisites.',
            ),
        ),
        (target,),
    )

    result = SearchPlanner().solve(problem, 'astar')

    assert result['total_cost'] == 3
    assert [item['id'] for item in result['actions']] == ['A002', 'A003', 'A004']
    assert any(item['event'] == 'HEURISTIC_CALCULATED' and item['estimate'] == 1 for item in result['trace'])


@pytest.mark.parametrize('method', ['ucs', 'astar'])
def test_search_reports_no_solution_and_respects_search_limit(method: str) -> None:
    target = Constraint('C001', 'target_x', ('X',), 'EQUALS', 2, 'ERROR', 'X must reach two.')
    no_solution = PlanningProblem(
        PaperState.from_dict({'X': 0}),
        (action('A001', 'OnlyStep', Condition('X', 'EQUALS', 0), StateEffect('X', 'SET', 1), 1),),
        (target,),
    )

    assert SearchPlanner().solve(no_solution, method)['status'] == 'NO_SOLUTION'
    limited = SearchPlanner(max_states=1).solve(simple_problem(), method)
    assert limited['status'] == 'SEARCH_LIMIT_REACHED'
    assert limited['success'] is False


@pytest.mark.parametrize('method', ['ucs', 'astar'])
def test_search_reports_depth_limit_instead_of_false_no_solution(method: str) -> None:
    problem = simple_problem()
    two_step_only = PlanningProblem(problem.initial_state, problem.actions[1:3], problem.constraints)

    result = SearchPlanner(max_depth=1).solve(two_step_only, method)

    assert result['status'] == 'SEARCH_LIMIT_REACHED'
    assert result['success'] is False
    assert any(event['event'] == 'SEARCH_LIMIT_REACHED' and event['reason'] == 'maximum_search_depth_reached' for event in result['trace'])


def test_module_6_violations_become_a_hypothetical_improvement_plan() -> None:
    compliance = compliance_result()
    original_compliance = deepcopy(compliance)
    result = ImprovementPlanningAgent().plan(compliance, 'astar')

    assert compliance['status'] == 'NON_COMPLIANT'
    assert result['status'] == 'PLAN_FOUND'
    assert {item['name'] for item in result['actions']} == {'ReducePageCount', 'ReduceAbstractLength', 'AddKeywords', 'AddReferences'}
    assert result['final_state']['PageCount'] == 6
    assert result['final_state']['AbstractLength'] == 250
    assert result['final_state']['KeywordsPresent'] is True
    assert result['final_state']['ReferenceCount'] == 15
    assert 'paper has not been modified' in result['explanation']
    assert result['explanation'].endswith('Projected state \u2014 the paper has not been modified.')
    assert compliance == original_compliance


def test_compliant_paper_needs_no_hypothetical_improvement() -> None:
    compliance = compliance_result(
        pages=5,
        abstract_words=200,
        keywords=['ai', 'planning'],
        references=20,
    )
    original_compliance = deepcopy(compliance)

    result = ImprovementPlanningAgent().plan(compliance, 'astar')

    assert compliance['status'] == 'COMPLIANT'
    assert result['status'] == 'NO_IMPROVEMENT_NEEDED'
    assert result['actions'] == []
    assert result['total_cost'] == 0
    assert result['states_explored'] == 0
    assert result['final_state'] == result['initial_state']
    assert any(event['event'] == 'NO_IMPROVEMENT_NEEDED' for event in result['trace'])
    assert compliance == original_compliance


def test_page_only_violation_generates_a_page_reduction_action() -> None:
    compliance = compliance_result(
        pages=7,
        abstract_words=200,
        keywords=['planning'],
        references=20,
        requirements={'max_pages': 6},
    )

    result = ImprovementPlanningAgent().plan(compliance, 'ucs')

    assert result['status'] == 'PLAN_FOUND'
    assert [item['name'] for item in result['actions']] == ['ReducePageCount']
    assert result['final_state']['PageCount'] == 6


def test_action_cost_overrides_are_validated_and_used_for_planning() -> None:
    compliance = compliance_result()
    overrides = {
        'ReducePageCount': 1,
        'ReduceAbstractLength': 1,
        'AddKeywords': 1,
        'AddReferences': 1,
    }

    result = ImprovementPlanningAgent().plan(compliance, 'astar', action_costs=overrides)
    available = build_improvement_actions(
        PaperState.from_dict({'PageCount': 8}), {'max_pages': 6}, {'ReducePageCount': 9},
    )

    assert result['status'] == 'PLAN_FOUND'
    assert result['total_cost'] == 4
    assert result['cost_model']['action_costs']['ReducePageCount'] == 1
    assert available[0].cost == 9
    with pytest.raises(ValueError, match='unsupported modeled action names'):
        ImprovementPlanningAgent().plan(compliance, action_costs={'InventPaperContent': 1})


def test_module_6_unknown_or_inconsistent_requirements_do_not_produce_a_false_plan() -> None:
    incomplete = deepcopy(compliance_result())
    incomplete['variables']['PageCount']['value'] = None
    incomplete['variables']['PageCount']['known'] = False
    incomplete['constraints']['unknown'] = [{
        'constraint_id': 'C001', 'constraint_name': 'max_pages', 'status': 'UNKNOWN',
    }]
    conflict = deepcopy(compliance_result())
    conflict['requirements_consistent'] = False
    conflict['status'] = 'NO_SOLUTION'

    assert ImprovementPlanningAgent().plan(incomplete)['status'] == 'INCOMPLETE'
    assert ImprovementPlanningAgent().plan(conflict)['status'] == 'NO_SOLUTION'


def test_planning_api_consumes_a_module_6_result_or_existing_paper_input() -> None:
    compliance = compliance_result()
    knowledge_base, _ = KnowledgeEngine().build(module_2_document())
    client = TestClient(app)

    direct = client.post('/api/planning/search', json={'compliance_result': compliance, 'method': 'astar'})
    integrated = client.post('/api/planning/search', json={
        'knowledge_base': knowledge_base,
        'requirements': {'max_pages': 6, 'max_abstract_words': 250, 'keywords_required': True, 'min_references': 15},
        'method': 'ucs',
    })
    configured = client.post('/api/planning/search', json={
        'compliance_result': compliance,
        'method': 'astar',
        'action_costs': {
            'ReducePageCount': 1,
            'ReduceAbstractLength': 1,
            'AddKeywords': 1,
            'AddReferences': 1,
        },
    })
    invalid_costs = client.post('/api/planning/search', json={
        'compliance_result': compliance,
        'action_costs': {'InventPaperContent': 1},
    })

    assert direct.status_code == 200 and direct.json()['status'] == 'PLAN_FOUND'
    assert integrated.status_code == 200 and integrated.json()['algorithm'] == 'Uniform-Cost Search'
    assert configured.status_code == 200 and configured.json()['total_cost'] == 4
    assert invalid_costs.status_code == 400
