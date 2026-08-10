"""Module 5 tests for safe formulas, semantic model checking, and resolution."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.logic.agent import LogicAgent
from app.logic.model_checking import ModelChecker, ModelLimitError
from app.logic.models import Formula, FormulaValidationError, clause_notation, cnf_clauses, evaluate, negate
from app.logic.resolution import ResolutionLimitError, ResolutionProver
from app.services.knowledge_engine import KnowledgeEngine
from main import app


def atom(name: str) -> Formula:
    return Formula.atom(name)


def formula(kind: str, *operands: Formula) -> Formula:
    return Formula(kind, operands)


def clause_strings(value: Formula) -> set[str]:
    return {clause_notation(clause) for clause in cnf_clauses(value)}


def module_2_document() -> dict:
    """Representative actual Module 2 schema used for the Module 3 -> 4 -> 5 path."""
    return {
        'document': {'filename': 'logic-integration.pdf', 'file_size': 2048, 'page_count': 3},
        'metadata': {
            'title': 'Logical Verification Paper', 'title_confidence': 'high', 'authors': [],
            'authors_confidence': 'low', 'abstract': 'Structured abstract.', 'abstract_word_count': 2, 'keywords': [],
        },
        'sections': [
            {'number': '1', 'title': 'Introduction', 'text': 'Context.', 'page_start': 1, 'page_end': 1},
            {'number': '2', 'title': 'Methodology', 'text': 'Method.', 'page_start': 1, 'page_end': 2},
            {'number': '3', 'title': 'Results', 'text': 'Result.', 'page_start': 2, 'page_end': 2},
            {'number': '4', 'title': 'Conclusion', 'text': 'Conclusion.', 'page_start': 3, 'page_end': 3},
        ],
        'references': [{'number': 1, 'text': 'Reference.'}],
        'figures': [{'number': 1, 'caption': 'Figure.', 'page': 2, 'detected_from': 'caption'}],
        'tables': [{'number': 1, 'caption': 'Table.', 'page': 2, 'detected_from': 'caption'}],
        'statistics': {},
        'warnings': [],
    }


def test_safe_formula_representation_and_truth_evaluation() -> None:
    p, q = atom('P'), atom('Q')
    model = {'P': True, 'Q': False}

    assert evaluate(formula('AND', p, negate(q)), model) is True
    assert evaluate(formula('OR', negate(p), q), model) is False
    assert evaluate(formula('IMPLIES', p, q), model) is False
    assert evaluate(formula('BICONDITIONAL', p, q), model) is False
    assert Formula.from_dict({'type': 'AND', 'operands': [{'type': 'ATOM', 'name': 'P'}, {'type': 'NOT', 'operands': [{'type': 'ATOM', 'name': 'Q'}]}]}).notation() == '(P AND NOT (Q))'
    with pytest.raises(FormulaValidationError):
        Formula.from_dict({'type': 'ATOM', 'name': 'P', 'code': '__import__("os")'})


def test_cnf_conversion_covers_atoms_connectives_demorgan_and_distribution() -> None:
    p, q, r = atom('P'), atom('Q'), atom('R')

    assert clause_strings(p) == {'P'}
    assert clause_strings(negate(p)) == {'NOT (P)'}
    assert clause_strings(formula('AND', p, q)) == {'P', 'Q'}
    assert clause_strings(formula('OR', p, q)) == {'P OR Q'}
    assert clause_strings(formula('IMPLIES', p, q)) == {'NOT (P) OR Q'}
    assert clause_strings(formula('BICONDITIONAL', p, q)) == {'NOT (P) OR Q', 'P OR NOT (Q)'}
    assert clause_strings(negate(formula('OR', p, q))) == {'NOT (P)', 'NOT (Q)'}
    assert clause_strings(formula('OR', formula('AND', p, q), r)) == {'P OR R', 'Q OR R'}


def test_model_checking_distinguishes_entailed_contradicted_unknown_and_multiple_models() -> None:
    p, q, r = atom('P'), atom('Q'), atom('R')
    checker = ModelChecker()

    entailed = checker.check((p, formula('IMPLIES', p, q)), q)
    contradicted = checker.check((p,), negate(p))
    unknown = checker.check((p,), q, include_models=True)
    conjunction = checker.check((formula('AND', p, q),), p)
    disjunction = checker.check((formula('OR', p, q),), p)
    multi_step = checker.check((p, formula('IMPLIES', p, q), formula('IMPLIES', q, r)), r)

    assert entailed['status'] == 'ENTAILED'
    assert entailed['models_checked'] == 4
    assert entailed['models_satisfying_kb'] == 1
    assert contradicted['status'] == 'CONTRADICTED'
    assert unknown['status'] == 'UNKNOWN'
    assert len(unknown['counter_models']) == 2
    assert unknown['models_truncated'] is False
    assert conjunction['status'] == 'ENTAILED'
    assert disjunction['status'] == 'UNKNOWN'
    assert multi_step['status'] == 'ENTAILED'


def test_model_checker_enforces_symbol_and_model_limits() -> None:
    with pytest.raises(ModelLimitError):
        ModelChecker(max_symbols=1, max_models=2).check((atom('P'),), atom('Q'))


def test_resolution_proves_queries_generates_empty_clause_and_terminates() -> None:
    p, q, r = atom('P'), atom('Q'), atom('R')
    prover = ResolutionProver()

    simple = prover.prove((p, formula('IMPLIES', p, q)), q)
    multi_step = prover.prove((p, formula('IMPLIES', p, q), formula('IMPLIES', q, r)), r)
    non_entailed = prover.prove((p,), q)
    duplicates = prover.prove((p, p, formula('IMPLIES', p, q)), q)

    assert simple['empty_clause_derived'] is True
    assert simple['proof_steps'][-1]['result'] == []
    assert multi_step['empty_clause_derived'] is True
    assert non_entailed['empty_clause_derived'] is False
    assert len(duplicates['initial_clauses']) == 3
    with pytest.raises(ResolutionLimitError):
        ResolutionProver(max_iterations=0).prove((p,), p)


def test_resolution_detects_direct_and_indirect_inconsistency() -> None:
    p, q = atom('P'), atom('Q')
    prover = ResolutionProver()

    direct = prover.check_unsatisfiable((p, negate(p)))
    indirect = prover.check_unsatisfiable((p, formula('IMPLIES', p, q), negate(q)))
    consistent = prover.check_unsatisfiable((p, formula('IMPLIES', p, q)))

    assert direct['empty_clause_derived'] is True
    assert indirect['empty_clause_derived'] is True
    assert consistent['empty_clause_derived'] is False
    direct_conflicts = prover.direct_unit_conflicts(cnf_clauses(p) | cnf_clauses(negate(p)) | cnf_clauses(q) | cnf_clauses(negate(q)))
    assert {conflict['atom'] for conflict in direct_conflicts} == {'P', 'Q'}


def test_logic_agent_integrates_real_module_3_facts_and_module_4_derivations() -> None:
    knowledge_base, validation = KnowledgeEngine().build(module_2_document())
    agent = LogicAgent()
    query = {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']}

    model = agent.model_check(knowledge_base, query)
    resolution = agent.resolution(knowledge_base, query)
    consistency = agent.consistency(knowledge_base)

    assert validation['valid'] is True
    assert model['status'] == 'ENTAILED'
    assert resolution['status'] == 'ENTAILED'
    assert consistency['consistent'] is True
    assert any(fact['predicate'] == 'CoreStructureComplete' for fact in model['module_4']['derived_facts'])
    assert model['module_4']['reasoning_trace']
    assert any(fact['proposition'] == 'CoreStructureComplete(paper_001)' for fact in model['knowledge_facts'])


def test_logic_agent_reports_project_schema_conflicts_and_unknown_information() -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document())
    contradictory = deepcopy(knowledge_base)
    for predicate in ('PaperHasAbstract', 'PaperHasResults'):
        opposite = deepcopy(next(fact for fact in contradictory['propositional_facts'] if fact['predicate'] == predicate))
        opposite['value'] = False
        contradictory['propositional_facts'].append(opposite)

    agent = LogicAgent()
    conflict_result = agent.consistency(contradictory)
    unknown_result = agent.model_check(knowledge_base, {'predicate': 'PaperHasAppendix', 'arguments': ['paper_001']})

    assert conflict_result['consistent'] is False
    assert conflict_result['status'] == 'INCONSISTENT'
    assert {conflict['atom'] for conflict in conflict_result['conflicts']} == {
        'PaperHasAbstract(paper_001)', 'PaperHasResults(paper_001)',
    }
    assert unknown_result['status'] == 'UNKNOWN'


def test_logic_api_validates_formula_input_and_exposes_all_module_5_operations() -> None:
    knowledge_base, _ = KnowledgeEngine().build(module_2_document())
    client = TestClient(app)
    request = {
        'knowledge_base': knowledge_base,
        'query': {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']},
    }

    model = client.post('/api/logic/model-check', json=request)
    resolution = client.post('/api/logic/resolution', json=request)
    theorem = client.post('/api/logic/prove', json=request)
    consistency = client.post('/api/logic/consistency', json={'knowledge_base': knowledge_base})
    malformed = client.post('/api/logic/model-check', json={
        'knowledge_base': knowledge_base,
        'query': {'formula': {'type': 'ATOM', 'name': 'P', 'unexpected': True}},
    })

    assert model.status_code == 200 and model.json()['status'] == 'ENTAILED'
    assert resolution.status_code == 200 and resolution.json()['empty_clause_derived'] is True
    assert theorem.status_code == 200 and theorem.json()['method'] == 'propositional_resolution'
    assert consistency.status_code == 200 and consistency.json()['consistent'] is True
    assert malformed.status_code == 400
