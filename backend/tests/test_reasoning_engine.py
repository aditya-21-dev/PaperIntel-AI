"""Module 4 reasoning tests using Module 3 knowledge-base output as input."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.reasoning.agent import ReasoningAgent, facts_from_knowledge_base
from app.reasoning.backward_chaining import BackwardChainer
from app.reasoning.forward_chaining import ForwardChainer
from app.reasoning.models import Fact, Pattern, Rule
from app.reasoning.rules import DEFAULT_RULES
from app.services.knowledge_engine import KnowledgeEngine
from main import app, reasoning_agent


def module_2_document(include_results: bool = True) -> dict:
    sections = [
        {'number': '1', 'title': 'Introduction', 'text': 'Problem context.', 'page_start': 1, 'page_end': 1},
        {'number': '2', 'title': 'Methodology', 'text': 'Deterministic method.', 'page_start': 1, 'page_end': 2},
        {'number': '4', 'title': 'Conclusion', 'text': 'Concluding statement.', 'page_start': 3, 'page_end': 3},
    ]
    if include_results:
        sections.insert(2, {'number': '3', 'title': 'Results', 'text': 'Observed result.', 'page_start': 2, 'page_end': 2})
    return {
        'document': {'filename': 'module-3-input.pdf', 'file_size': 1200, 'page_count': 3},
        'metadata': {
            'title': 'Reasoning Test Paper', 'title_confidence': 'high', 'authors': [],
            'authors_confidence': 'low', 'abstract': 'A structured abstract.',
            'abstract_word_count': 3, 'keywords': [],
        },
        'sections': sections,
        'references': [{'number': 1, 'text': 'A reference.'}],
        'figures': [{'number': 1, 'caption': 'A figure.', 'page': 2, 'detected_from': 'caption'}],
        'tables': [{'number': 1, 'caption': 'A table.', 'page': 2, 'detected_from': 'caption'}],
        'statistics': {},
        'warnings': [],
    }


def rule(rule_id: str, premises: tuple[Pattern, ...], conclusion: Pattern) -> Rule:
    return Rule(rule_id, rule_id.lower(), premises, conclusion, f'Explanation for {rule_id}.')


@pytest.fixture(autouse=True)
def clear_reasoning_agent():
    reasoning_agent.clear()
    yield
    reasoning_agent.clear()


def test_forward_chaining_consumes_module_3_output_and_derives_multi_step_facts() -> None:
    knowledge_base, validation = KnowledgeEngine().build(module_2_document())

    result = ForwardChainer().infer(facts_from_knowledge_base(knowledge_base), DEFAULT_RULES)

    assert validation['valid'] is True
    derived = {fact['predicate'] for fact in result['derived_facts']}
    assert {'HasMajorStructuralComponents', 'CoreStructureComplete', 'HasReferenceSection', 'HasAtLeastOneFigure', 'HasAtLeastOneTable'} <= derived
    core_trace = next(item for item in result['reasoning_trace'] if item['derived_fact']['predicate'] == 'CoreStructureComplete')
    assert core_trace['rule_id'] == 'R001'
    assert core_trace['supporting_facts']
    assert core_trace['explanation']


def test_forward_chaining_handles_multiple_rules_duplicate_conclusions_and_fixed_point() -> None:
    facts = [Fact('Seed', ('paper_001',), True)]
    rules = (
        rule('R1', (Pattern('Seed', ('P',)),), Pattern('SameConclusion', ('P',))),
        rule('R2', (Pattern('Seed', ('P',)),), Pattern('SameConclusion', ('P',))),
    )

    result = ForwardChainer().infer(facts, rules)

    assert [fact['predicate'] for fact in result['derived_facts']] == ['SameConclusion']
    assert [trace['rule_id'] for trace in result['reasoning_trace']] == ['R1', 'R2']
    assert result['reasoning_trace'][1]['new_fact'] is False
    assert result['iterations'] == 2


def test_forward_chaining_handles_rule_chains_cycles_no_match_and_limits() -> None:
    chain_rules = (
        rule('R1', (Pattern('A', ('P',)),), Pattern('B', ('P',))),
        rule('R2', (Pattern('B', ('P',)),), Pattern('C', ('P',))),
    )
    chain = ForwardChainer().infer([Fact('A', ('paper_001',), True)], chain_rules)
    assert [fact['predicate'] for fact in chain['derived_facts']] == ['B', 'C']

    cyclic = ForwardChainer().infer(
        [Fact('A', ('paper_001',), True)],
        (rule('R1', (Pattern('A', ('P',)),), Pattern('B', ('P',))), rule('R2', (Pattern('B', ('P',)),), Pattern('A', ('P',)))),
    )
    assert cyclic['success'] is True
    assert [fact['predicate'] for fact in cyclic['derived_facts']] == ['B']

    no_match = ForwardChainer().infer([Fact('A', ('paper_001',), False)], chain_rules)
    assert no_match['derived_facts'] == []

    limited = ForwardChainer(max_rule_firings=0).infer([Fact('A', ('paper_001',), True)], chain_rules)
    assert limited['success'] is False
    assert limited['limit_reached'] is True


def test_backward_chaining_handles_known_and_derived_goals() -> None:
    chainer = BackwardChainer()
    known = chainer.prove(Fact('A', ('paper_001',), True), [Fact('A', ('paper_001',), True)], [])
    derived = chainer.prove(
        Fact('C', ('paper_001',), True),
        [Fact('A', ('paper_001',), True)],
        (rule('R1', (Pattern('A', ('P',)),), Pattern('B', ('P',))), rule('R2', (Pattern('B', ('P',)),), Pattern('C', ('P',)))),
    )

    assert known['status'] == 'known_true'
    assert derived['established'] is True
    assert derived['rule_used'] == 'R2'
    assert derived['supporting_facts'] == ['A(paper_001)']
    assert any(item['step'] == 'rule_established' for item in derived['reasoning_trace'])


def test_backward_chaining_reports_unknown_missing_and_known_false_without_conflation() -> None:
    premise_rule = rule('R1', (Pattern('A', ('P',)), Pattern('B', ('P',))), Pattern('C', ('P',)))
    missing = BackwardChainer().prove(Fact('C', ('paper_001',), True), [Fact('A', ('paper_001',), True)], (premise_rule,))
    unknown = BackwardChainer().prove(Fact('Unrelated', ('paper_001',), True), [], ())
    false = BackwardChainer().prove(Fact('A', ('paper_001',), True), [Fact('A', ('paper_001',), False)], ())

    assert missing['established'] is False
    assert missing['missing_facts'] == ['B(paper_001)']
    assert unknown['status'] == 'unknown'
    assert unknown['missing_facts'] == ['Unrelated(paper_001)']
    assert false['status'] == 'known_false'
    assert false['known_false_facts'] == ['NOT A(paper_001)']
    assert false['missing_facts'] == []


def test_backward_chaining_handles_multiple_rules_cycles_and_depth_limits() -> None:
    multiple_rules = (
        rule('R1', (Pattern('Missing', ('P',)),), Pattern('Goal', ('P',))),
        rule('R2', (Pattern('A', ('P',)),), Pattern('Goal', ('P',))),
    )
    multiple = BackwardChainer().prove(Fact('Goal', ('paper_001',), True), [Fact('A', ('paper_001',), True)], multiple_rules)
    assert multiple['established'] is True
    assert multiple['rule_used'] == 'R2'
    assert multiple['attempted_rules'] == ['R1', 'R2']

    cycle_rules = (
        rule('R1', (Pattern('B', ('P',)),), Pattern('A', ('P',))),
        rule('R2', (Pattern('A', ('P',)),), Pattern('B', ('P',))),
    )
    cycle = BackwardChainer().prove(Fact('A', ('paper_001',), True), [], cycle_rules)
    assert cycle['established'] is False
    assert any(item['step'] == 'cycle_detected' for item in cycle['reasoning_trace'])

    depth = BackwardChainer(max_depth=1).prove(Fact('C', ('paper_001',), True), [Fact('A', ('paper_001',), True)], (rule('R1', (Pattern('A', ('P',)),), Pattern('B', ('P',))), rule('R2', (Pattern('B', ('P',)),), Pattern('C', ('P',)))) )
    assert depth['limit_reached'] is True


def test_reasoning_agent_and_api_consume_module_3_knowledge_base() -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document())
    agent = ReasoningAgent()
    agent.perceive(knowledge_base)
    backward = agent.backward_reason({'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']})
    assert backward['established'] is True

    client = TestClient(app)
    forward_response = client.post('/api/reasoning/forward', json={'knowledge_base': deepcopy(knowledge_base)})
    assert forward_response.status_code == 200
    assert any(fact['predicate'] == 'CoreStructureComplete' for fact in forward_response.json()['derived_facts'])

    backward_response = client.post('/api/reasoning/backward', json={
        'knowledge_base': deepcopy(knowledge_base),
        'goal': {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']},
    })
    assert backward_response.status_code == 200
    assert backward_response.json()['established'] is True


def test_backward_reasoning_explains_missing_module_3_fact() -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document(include_results=False))
    result = ReasoningAgent().backward_reason(
        {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']},
        knowledge_base,
    )

    assert result['established'] is False
    assert 'NOT PaperHasResults(paper_001)' in result['known_false_facts']
    assert result['explanation']
