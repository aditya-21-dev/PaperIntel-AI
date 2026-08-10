"""Bounded propositional resolution and consistency checking over structured clauses."""

from __future__ import annotations

from itertools import combinations
from typing import Iterable

from .models import Clause, Formula, Literal, clause_notation, clause_to_list, clauses_for_formulas, negate


class ResolutionLimitError(ValueError):
    """Raised when saturation cannot continue within its deterministic safety bounds."""


def _clause_key(clause: Clause) -> tuple[tuple[str, bool], ...]:
    return tuple(literal.sort_key() for literal in sorted(clause, key=Literal.sort_key))


def _is_tautology(clause: Clause) -> bool:
    return any(literal.complement in clause for literal in clause)


class ResolutionProver:
    def __init__(self, max_iterations: int = 100, max_clauses: int = 500) -> None:
        self.max_iterations = max_iterations
        self.max_clauses = max_clauses

    def prove(self, knowledge_base: Iterable[Formula], query: Formula) -> dict[str, object]:
        """Test KB entails query by refuting KB AND NOT(query)."""
        formulas = (*tuple(knowledge_base), negate(query))
        result = self._saturate(clauses_for_formulas(formulas))
        result['query'] = query.notation()
        result['negated_query'] = negate(query).notation()
        return result

    def check_unsatisfiable(self, formulas: Iterable[Formula]) -> dict[str, object]:
        """Use resolution directly to determine whether a knowledge base is inconsistent."""
        return self._saturate(clauses_for_formulas(tuple(formulas)))

    def _saturate(self, initial_clauses: frozenset[Clause]) -> dict[str, object]:
        known_clauses = {clause for clause in initial_clauses if not _is_tautology(clause)}
        if len(known_clauses) > self.max_clauses:
            raise ResolutionLimitError(f'Initial clause count ({len(known_clauses)}) exceeds the safety limit of {self.max_clauses}.')
        initial = sorted(known_clauses, key=_clause_key)
        processed_pairs: set[tuple[tuple[tuple[str, bool], ...], tuple[tuple[str, bool], ...]]] = set()
        proof_steps: list[dict[str, object]] = []
        iterations = 0

        if frozenset() in known_clauses:
            return self._result(True, known_clauses, initial, proof_steps, iterations)

        while True:
            if iterations >= self.max_iterations:
                raise ResolutionLimitError(f'Resolution reached the iteration limit of {self.max_iterations}.')
            iterations += 1
            additions: set[Clause] = set()
            ordered_clauses = sorted(known_clauses, key=_clause_key)
            for clause_a, clause_b in combinations(ordered_clauses, 2):
                pair_key = tuple(sorted((_clause_key(clause_a), _clause_key(clause_b))))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                for literal in sorted(clause_a, key=Literal.sort_key):
                    if literal.complement not in clause_b:
                        continue
                    resolvent = frozenset((clause_a - {literal}) | (clause_b - {literal.complement}))
                    if _is_tautology(resolvent) or resolvent in known_clauses or resolvent in additions:
                        continue
                    if len(known_clauses) + len(additions) >= self.max_clauses:
                        raise ResolutionLimitError(f'Resolution reached the clause limit of {self.max_clauses}.')
                    proof_steps.append({
                        'step': len(proof_steps) + 1,
                        'clause_a': clause_to_list(clause_a),
                        'clause_b': clause_to_list(clause_b),
                        'resolved_literal': literal.notation(),
                        'result': clause_to_list(resolvent),
                        'result_notation': clause_notation(resolvent),
                    })
                    if not resolvent:
                        known_clauses.add(resolvent)
                        return self._result(True, known_clauses, initial, proof_steps, iterations)
                    additions.add(resolvent)
            if not additions:
                return self._result(False, known_clauses, initial, proof_steps, iterations)
            known_clauses.update(additions)

    @staticmethod
    def _result(
        empty_clause_derived: bool,
        known_clauses: set[Clause],
        initial: list[Clause],
        proof_steps: list[dict[str, object]],
        iterations: int,
    ) -> dict[str, object]:
        return {
            'success': True,
            'empty_clause_derived': empty_clause_derived,
            'initial_clauses': [clause_to_list(clause) for clause in initial],
            'clauses': [clause_to_list(clause) for clause in sorted(known_clauses, key=_clause_key)],
            'proof_steps': proof_steps,
            'iterations': iterations,
            'clause_count': len(known_clauses),
        }

    @staticmethod
    def direct_unit_conflicts(clauses: Iterable[Clause]) -> list[dict[str, object]]:
        unit_literals = {next(iter(clause)) for clause in clauses if len(clause) == 1}
        conflicts: list[dict[str, object]] = []
        for literal in sorted(unit_literals, key=Literal.sort_key):
            if literal.positive and literal.complement in unit_literals:
                conflicts.append({
                    'type': 'direct_unit_conflict',
                    'atom': literal.atom,
                    'literals': [literal.notation(), literal.complement.notation()],
                    'message': f'Both {literal.notation()} and {literal.complement.notation()} are required.',
                })
        return conflicts
