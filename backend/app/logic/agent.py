"""Module 5 agent that verifies Module 3 facts plus Module 4 derived facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.reasoning.agent import ReasoningAgent, facts_from_knowledge_base
from app.reasoning.models import Fact
from app.services.knowledge_engine import validate_knowledge_base

from .model_checking import ModelChecker, ModelLimitError
from .models import Formula, FormulaValidationError, clauses_for_formulas, negate
from .resolution import ResolutionLimitError, ResolutionProver


class LogicInputError(ValueError):
    """Raised for malformed Module 5 API inputs."""


def proposition_name(predicate: str, arguments: tuple[str, ...] | list[str]) -> str:
    if not isinstance(predicate, str) or not predicate.strip() or not isinstance(arguments, (tuple, list)) or not all(isinstance(argument, str) and argument for argument in arguments):
        raise LogicInputError('A proposition requires a non-empty predicate and entity-ID arguments.')
    return f"{predicate.strip()}({', '.join(arguments)})"


def formula_from_fact(fact: Fact) -> Formula:
    atom = Formula.atom(proposition_name(fact.predicate, fact.arguments))
    return atom if fact.value else negate(atom)


def formula_from_query(query: object) -> Formula:
    if not isinstance(query, dict):
        raise LogicInputError('A query must be a structured formula or a predicate-and-arguments object.')
    if 'formula' in query:
        return Formula.from_dict(query['formula'])
    if 'type' in query:
        return Formula.from_dict(query)
    predicate = query.get('predicate')
    arguments = query.get('arguments')
    value = query.get('value', True)
    if not isinstance(value, bool):
        raise LogicInputError('Query value must be Boolean when supplied.')
    atom = Formula.atom(proposition_name(predicate, arguments))
    return atom if value else negate(atom)


@dataclass(frozen=True)
class PreparedKnowledge:
    formulas: tuple[Formula, ...]
    facts: tuple[dict[str, Any], ...]
    module_4: dict[str, Any]


class LogicAgent:
    """A stateless logical-verification agent operating only on supplied in-memory data."""

    def __init__(self, model_checker: ModelChecker | None = None, resolver: ResolutionProver | None = None) -> None:
        self._model_checker = model_checker or ModelChecker()
        self._resolver = resolver or ResolutionProver()

    def prepare(self, knowledge_base: dict[str, Any]) -> PreparedKnowledge:
        validation = validate_knowledge_base(knowledge_base)
        if not validation['valid']:
            raise LogicInputError('Knowledge base validation failed before logical verification.')

        source_facts = facts_from_knowledge_base(knowledge_base)
        module_4_result = ReasoningAgent().forward_reason(knowledge_base)
        derived_facts = [
            Fact(
                item['predicate'], tuple(item['arguments']), item['value'], item.get('evidence'), item.get('origin', 'derived'),
            )
            for item in module_4_result['derived_facts']
        ]
        unique_facts: dict[tuple[str, tuple[str, ...], bool], Fact] = {
            fact.key: fact for fact in (*source_facts, *derived_facts)
        }
        facts = tuple(unique_facts.values())
        formulas = tuple(formula_from_fact(fact) for fact in facts)
        return PreparedKnowledge(
            formulas=formulas,
            facts=tuple({
                **fact.to_dict(),
                'proposition': proposition_name(fact.predicate, fact.arguments),
            } for fact in facts),
            module_4={
                'derived_facts': module_4_result['derived_facts'],
                'reasoning_trace': module_4_result['reasoning_trace'],
                'rules': ReasoningAgent.rules(),
                'success': module_4_result['success'],
            },
        )

    def model_check(self, knowledge_base: dict[str, Any], query: object, include_models: bool = False) -> dict[str, Any]:
        prepared = self.prepare(knowledge_base)
        formula = formula_from_query(query)
        try:
            result = self._model_checker.check(prepared.formulas, formula, include_models)
        except ModelLimitError as exc:
            result = {
                'success': False,
                'status': 'LIMIT_EXCEEDED',
                'error': str(exc),
                'trace': [{'step': 'model_limit_reached', 'explanation': str(exc)}],
            }
        return self._with_context(result, formula, prepared)

    def resolution(self, knowledge_base: dict[str, Any], query: object) -> dict[str, Any]:
        prepared = self.prepare(knowledge_base)
        formula = formula_from_query(query)
        try:
            consistency = self._resolver.check_unsatisfiable(prepared.formulas)
            if consistency['empty_clause_derived']:
                result = {
                    **consistency,
                    'status': 'INCONSISTENT',
                    'explanation': 'The knowledge base is inconsistent, so it cannot yield a meaningful three-state proof result.',
                }
                return self._with_context(result, formula, prepared)

            direct_proof = self._resolver.prove(prepared.formulas, formula)
            if direct_proof['empty_clause_derived']:
                result = {
                    **direct_proof,
                    'status': 'ENTAILED',
                    'proved_formula': formula.notation(),
                    'explanation': 'Resolution derived the empty clause from the knowledge base and the negated query.',
                }
                return self._with_context(result, formula, prepared)

            opposite = negate(formula)
            opposite_proof = self._resolver.prove(prepared.formulas, opposite)
            if opposite_proof['empty_clause_derived']:
                result = {
                    **opposite_proof,
                    'status': 'CONTRADICTED',
                    'proved_formula': opposite.notation(),
                    'query_attempt': self._proof_summary(direct_proof),
                    'explanation': 'Resolution derived the empty clause for the negation of the query, so the query is contradicted.',
                }
                return self._with_context(result, formula, prepared)
            result = {
                **direct_proof,
                'status': 'UNKNOWN',
                'query_attempt': self._proof_summary(direct_proof),
                'negated_query_attempt': self._proof_summary(opposite_proof),
                'explanation': 'Resolution could prove neither the query nor its negation from the supplied knowledge base.',
            }
        except ResolutionLimitError as exc:
            result = {
                'success': False,
                'status': 'LIMIT_EXCEEDED',
                'empty_clause_derived': False,
                'clauses': [],
                'proof_steps': [],
                'error': str(exc),
                'explanation': 'Resolution stopped at a configured safety limit; no logical conclusion was returned.',
            }
        return self._with_context(result, formula, prepared)

    def prove(self, knowledge_base: dict[str, Any], query: object) -> dict[str, Any]:
        result = self.resolution(knowledge_base, query)
        result['method'] = 'propositional_resolution'
        return result

    def consistency(self, knowledge_base: dict[str, Any]) -> dict[str, Any]:
        prepared = self.prepare(knowledge_base)
        try:
            result = self._resolver.check_unsatisfiable(prepared.formulas)
        except ResolutionLimitError as exc:
            return {
                'success': False,
                'consistent': None,
                'status': 'LIMIT_EXCEEDED',
                'conflicts': [],
                'trace': [{'step': 'resolution_limit_reached', 'explanation': str(exc)}],
                'error': str(exc),
                **self._context(prepared),
            }
        consistent = not result['empty_clause_derived']
        initial_clauses = clauses_for_formulas(prepared.formulas)
        conflicts = self._resolver.direct_unit_conflicts(initial_clauses)
        if not consistent and not conflicts:
            conflicts.append({
                'type': 'resolution_conflict',
                'message': 'Resolution derived the empty clause, proving that the clause set is unsatisfiable.',
                'proof_step': result['proof_steps'][-1]['step'] if result['proof_steps'] else None,
            })
        return {
            'success': True,
            'consistent': consistent,
            'status': 'CONSISTENT' if consistent else 'INCONSISTENT',
            'conflicts': conflicts,
            'trace': [
                {'step': 'cnf_generated', 'clause_count': len(initial_clauses)},
                {
                    'step': 'resolution_completed',
                    'empty_clause_derived': result['empty_clause_derived'],
                    'iterations': result['iterations'],
                },
            ],
            'proof_steps': result['proof_steps'],
            'clauses': result['clauses'],
            'explanation': 'The knowledge base is satisfiable under propositional logic.' if consistent else 'The knowledge base is inconsistent: resolution derived the empty clause.',
            **self._context(prepared),
        }

    @staticmethod
    def _proof_summary(result: dict[str, Any]) -> dict[str, Any]:
        return {
            'empty_clause_derived': result['empty_clause_derived'],
            'iterations': result['iterations'],
            'clause_count': result['clause_count'],
        }

    @staticmethod
    def _context(prepared: PreparedKnowledge) -> dict[str, Any]:
        return {
            'knowledge_facts': list(prepared.facts),
            'module_4': prepared.module_4,
        }

    def _with_context(self, result: dict[str, Any], formula: Formula, prepared: PreparedKnowledge) -> dict[str, Any]:
        return {
            **result,
            'query': formula.to_dict(),
            'query_notation': formula.notation(),
            **self._context(prepared),
        }
