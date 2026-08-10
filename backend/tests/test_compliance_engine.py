"""Module 6 CSP and paper-compliance tests using the real Module 2/3 schema."""

from copy import deepcopy

from fastapi.testclient import TestClient

from app.compliance.agent import ComplianceAgent
from app.compliance.models import CSPProblem, CSPVariable, Constraint
from app.compliance.solver import CSPSolver
from app.services.knowledge_engine import KnowledgeEngine
from main import app


def variable(name: str, *domain: bool | int) -> CSPVariable:
    return CSPVariable(name, domain)


def constraint(identifier: str, name: str, variables: tuple[str, ...], operator: str, expected: object) -> Constraint:
    return Constraint(identifier, name, variables, operator, expected, 'ERROR', f'Explanation for {name}.')


def module_2_document(
    *,
    pages: int = 6,
    abstract: str = 'A concise abstract for compliance testing.',
    abstract_words: int = 6,
    keywords: list[str] | None = None,
    references: int = 2,
    include_sections: bool = True,
) -> dict:
    sections = []
    if include_sections:
        sections = [
            {'number': '1', 'title': 'Introduction', 'text': 'Context.', 'page_start': 1, 'page_end': 1},
            {'number': '2', 'title': 'Methodology', 'text': 'Method.', 'page_start': 2, 'page_end': 2},
            {'number': '3', 'title': 'Results', 'text': 'Results.', 'page_start': 3, 'page_end': 3},
            {'number': '4', 'title': 'Conclusion', 'text': 'Conclusion.', 'page_start': 4, 'page_end': 4},
        ]
    return {
        'document': {'filename': 'compliance-paper.pdf', 'file_size': 2048, 'page_count': pages},
        'metadata': {
            'title': 'Compliance Test Paper', 'title_confidence': 'high', 'authors': ['A. Author'],
            'authors_confidence': 'high', 'abstract': abstract, 'abstract_word_count': abstract_words,
            'keywords': ['constraint satisfaction'] if keywords is None else keywords,
        },
        'sections': sections,
        'references': [{'number': index, 'text': f'Reference {index}'} for index in range(1, references + 1)],
        'figures': [], 'tables': [], 'statistics': {}, 'warnings': [],
    }


def knowledge_base(**kwargs: object) -> dict:
    result, validation = KnowledgeEngine().build(module_2_document(**kwargs))
    assert validation['valid'] is True
    return result


def profile(requirements: dict[str, object]) -> dict:
    return {'profile_id': 'custom', 'venue': 'Test Venue', 'requirements': requirements}


def test_csp_variables_domains_and_unary_binary_multi_variable_constraints() -> None:
    abstract = variable('AbstractPresent', False, True)
    methodology = variable('MethodologyPresent', False, True)
    results = variable('ResultsPresent', False, True)
    required = constraint('C001', 'abstract_required', ('AbstractPresent',), 'EQUALS', True)
    implication = constraint('C002', 'methodology_results', ('MethodologyPresent', 'ResultsPresent'), 'IMPLIES', {'if': True, 'then': True})
    all_sections = constraint('C003', 'all_sections', ('AbstractPresent', 'MethodologyPresent', 'ResultsPresent'), 'ALL_EQUALS', True)
    problem = CSPProblem({'AbstractPresent': abstract, 'MethodologyPresent': methodology, 'ResultsPresent': results}, (required, implication, all_sections))

    assert problem.variables['AbstractPresent'].domain == (False, True)
    assert required.is_satisfied({'AbstractPresent': True}) is True
    assert implication.is_satisfied({'MethodologyPresent': True, 'ResultsPresent': False}) is False
    assert all_sections.is_satisfied({'AbstractPresent': True, 'MethodologyPresent': True, 'ResultsPresent': True}) is True


def test_constraint_propagation_reduces_domains_and_chains_implications() -> None:
    variables = {name: variable(name, False, True) for name in ('A', 'B', 'C')}
    problem = CSPProblem(variables, (
        constraint('C001', 'a_required', ('A',), 'EQUALS', True),
        constraint('C002', 'a_implies_b', ('A', 'B'), 'IMPLIES', {'if': True, 'then': True}),
        constraint('C003', 'b_implies_c', ('B', 'C'), 'IMPLIES', {'if': True, 'then': True}),
    ))

    result = CSPSolver().solve(problem)

    assert result['solutions_found'] == 1
    assert result['solutions'][0] == {'A': True, 'B': True, 'C': True}
    assert result['propagation_steps'] >= 3
    assert any(event['event'] == 'domain_reduced' for event in result['trace'])
    assert {'CONSTRAINT_CHECKED', 'DOMAIN_REDUCED', 'SOLUTION_FOUND'} <= {
        event['event_type'] for event in result['trace']
    }


def test_propagation_detects_empty_domains_before_search() -> None:
    problem = CSPProblem({'A': variable('A', False, True)}, (
        constraint('C001', 'must_be_true', ('A',), 'EQUALS', True),
        constraint('C002', 'must_be_false', ('A',), 'EQUALS', False),
    ))

    result = CSPSolver().solve(problem)

    assert result['solutions_found'] == 0
    assert result['conflicts'][0]['type'] == 'empty_domain'
    assert result['nodes_visited'] == 0


def test_backtracking_mrv_forward_checking_and_multiple_solutions() -> None:
    two_variable_problem = CSPProblem(
        {'A': variable('A', False, True), 'B': variable('B', False, True)},
        (constraint('C001', 'different', ('A', 'B'), 'DIFFERENT', None),),
    )
    solutions = CSPSolver().solve(two_variable_problem, max_solutions=2)
    assert solutions['solutions_found'] == 2
    assert any(event['event'] == 'variable_selected' and event['heuristic'] == 'MRV_with_degree_tiebreaker' for event in solutions['trace'])
    assert any(event['event'] == 'domain_reduced' for event in solutions['trace'])
    assert any(event['event_type'] == 'FORWARD_CHECK' for event in solutions['trace'])

    impossible = CSPProblem(
        {name: variable(name, False, True) for name in ('A', 'B', 'C')},
        (
            constraint('C001', 'ab_different', ('A', 'B'), 'DIFFERENT', None),
            constraint('C002', 'ac_different', ('A', 'C'), 'DIFFERENT', None),
            constraint('C003', 'bc_different', ('B', 'C'), 'DIFFERENT', None),
        ),
    )
    failed = CSPSolver().solve(impossible)
    assert failed['solutions_found'] == 0
    assert failed['backtracking_steps'] >= 2
    assert any(event['event'] == 'backtrack' for event in failed['trace'])
    assert any(event['event_type'] == 'CONFLICT_DETECTED' for event in failed['trace'])


def test_mrv_selects_the_variable_with_the_smallest_remaining_domain() -> None:
    problem = CSPProblem({
        'A': variable('A', 0, 1, 2),
        'B': variable('B', False, True),
    }, ())

    result = CSPSolver().solve(problem)
    selected = next(event for event in result['trace'] if event['event'] == 'variable_selected')

    assert selected['variable'] == 'B'
    assert selected['heuristic'] == 'MRV_with_degree_tiebreaker'


def test_compliance_reports_fully_compliant_paper_and_possible_configuration() -> None:
    result = ComplianceAgent().analyze(knowledge_base(), profile({
        'max_pages': 6, 'abstract_required': True, 'max_abstract_words': 250,
        'keywords_required': True, 'min_references': 2,
        'required_sections': ['Introduction', 'Methodology', 'Results', 'Conclusion'],
    }))

    assert result['status'] == 'COMPLIANT'
    assert result['constraints']['violated'] == []
    assert result['constraints']['unknown'] == []
    assert result['possible_configurations']
    assert result['solver']['propagation_steps'] > 0


def test_compliance_explains_page_abstract_and_reference_violations() -> None:
    agent = ComplianceAgent()
    page = agent.analyze(knowledge_base(pages=7), profile({'max_pages': 6}))
    missing_abstract = agent.analyze(knowledge_base(abstract='', abstract_words=0), profile({'abstract_required': True}))
    long_abstract = agent.analyze(knowledge_base(abstract_words=300), profile({'max_abstract_words': 250}))
    low_references = agent.analyze(knowledge_base(references=1), profile({'min_references': 2}))

    assert page['status'] == 'NON_COMPLIANT'
    assert page['violations'][0]['difference'] == 1
    assert 'Actual value: 7' in page['violations'][0]['explanation']
    assert missing_abstract['violations'][0]['constraint_name'] == 'abstract_required'
    assert long_abstract['violations'][0]['constraint_name'] == 'max_abstract_words'
    assert low_references['violations'][0]['constraint_name'] == 'min_references'


def test_compliance_handles_multiple_violations_unknown_values_and_requirement_conflicts() -> None:
    multiple = ComplianceAgent().analyze(knowledge_base(pages=7, abstract='', abstract_words=0, keywords=[], references=0), profile({
        'max_pages': 6, 'abstract_required': True, 'keywords_required': True, 'min_references': 2,
    }))
    incomplete_kb = deepcopy(knowledge_base())
    incomplete_kb['paper']['attributes']['page_count'] = None
    incomplete = ComplianceAgent().analyze(incomplete_kb, profile({'max_pages': 6}))
    contradictory = ComplianceAgent().analyze(knowledge_base(), profile({'min_pages': 8, 'max_pages': 6}))

    assert multiple['status'] == 'NON_COMPLIANT'
    assert len(multiple['violations']) == 4
    assert incomplete['status'] == 'INCOMPLETE'
    assert incomplete['constraints']['unknown'][0]['constraint_name'] == 'max_pages'
    assert contradictory['status'] == 'NO_SOLUTION'
    assert contradictory['requirements_consistent'] is False
    assert contradictory['solver']['conflicts']


def test_compliance_api_uses_knowledge_base_or_existing_module_2_output() -> None:
    document = module_2_document(pages=7)
    base = knowledge_base(pages=7)
    client = TestClient(app)
    requirements = {'max_pages': 6, 'abstract_required': True}

    profiles = client.get('/api/compliance/profiles')
    csp = client.post('/api/compliance/csp', json={'knowledge_base': base, 'venue': 'Test Venue', 'requirements': requirements})
    validate = client.post('/api/compliance/validate', json={'knowledge_base': base, 'requirements': requirements})
    structured = client.post('/api/compliance/csp', json={'structured_document': document, 'requirements': requirements})

    assert profiles.status_code == 200
    assert profiles.json()['profiles'][0]['id'] == 'generic_research_paper'
    assert csp.status_code == 200 and csp.json()['status'] == 'NON_COMPLIANT'
    assert csp.json()['solver_phases']['requirements']['propagation_steps'] > 0
    assert csp.json()['solver_phases']['paper_assignment']['conflicts']
    assert all('phase' in event and 'event_type' in event for event in csp.json()['solver_trace'])
    assert validate.status_code == 200 and validate.json()['solver'] is None
    assert structured.status_code == 200 and structured.json()['status'] == 'NON_COMPLIANT'
