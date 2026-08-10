"""Safe, structured propositional-formula and CNF representations for Module 5."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


FORMULA_TYPES = frozenset({'ATOM', 'NOT', 'AND', 'OR', 'IMPLIES', 'BICONDITIONAL'})


class FormulaValidationError(ValueError):
    """Raised when an external formula is malformed or exceeds the safe grammar."""


@dataclass(frozen=True)
class Formula:
    """An immutable AST. Formula input is data, never executable Python."""

    kind: str
    operands: tuple['Formula', ...] = ()
    name: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in FORMULA_TYPES:
            raise FormulaValidationError(f'Unsupported formula type: {self.kind!r}.')
        if self.kind == 'ATOM':
            if not isinstance(self.name, str) or not self.name.strip() or len(self.name) > 256:
                raise FormulaValidationError('An atom requires a non-empty name no longer than 256 characters.')
            if any(ord(character) < 32 for character in self.name):
                raise FormulaValidationError('Atom names cannot contain control characters.')
            if self.operands:
                raise FormulaValidationError('An atom cannot contain operands.')
            return
        if self.name is not None:
            raise FormulaValidationError(f'{self.kind} formulas cannot define an atom name.')
        expected_counts = {'NOT': 1, 'IMPLIES': 2, 'BICONDITIONAL': 2}
        if self.kind in expected_counts and len(self.operands) != expected_counts[self.kind]:
            raise FormulaValidationError(f'{self.kind} requires exactly {expected_counts[self.kind]} operands.')
        if self.kind in {'AND', 'OR'} and len(self.operands) < 2:
            raise FormulaValidationError(f'{self.kind} requires at least two operands.')
        if not all(isinstance(operand, Formula) for operand in self.operands):
            raise FormulaValidationError('Formula operands must be structured formulas.')

    @classmethod
    def atom(cls, name: str) -> 'Formula':
        return cls('ATOM', name=name.strip() if isinstance(name, str) else name)

    @classmethod
    def from_dict(cls, raw: object) -> 'Formula':
        if not isinstance(raw, dict):
            raise FormulaValidationError('A formula must be an object.')
        kind = raw.get('type')
        if not isinstance(kind, str):
            raise FormulaValidationError('Formula type is required.')
        kind = kind.upper()
        if kind == 'ATOM':
            if set(raw) - {'type', 'name'}:
                raise FormulaValidationError('ATOM accepts only type and name fields.')
            return cls.atom(raw.get('name'))
        if set(raw) - {'type', 'operands'}:
            raise FormulaValidationError(f'{kind} accepts only type and operands fields.')
        operands = raw.get('operands')
        if not isinstance(operands, list):
            raise FormulaValidationError(f'{kind} requires an operands list.')
        return cls(kind, tuple(cls.from_dict(operand) for operand in operands))

    def to_dict(self) -> dict[str, object]:
        if self.kind == 'ATOM':
            return {'type': 'ATOM', 'name': self.name}
        return {'type': self.kind, 'operands': [operand.to_dict() for operand in self.operands]}

    def notation(self) -> str:
        if self.kind == 'ATOM':
            return self.name or ''
        if self.kind == 'NOT':
            return f'NOT ({self.operands[0].notation()})'
        symbols = {'AND': ' AND ', 'OR': ' OR ', 'IMPLIES': ' -> ', 'BICONDITIONAL': ' <-> '}
        return f"({symbols[self.kind].join(operand.notation() for operand in self.operands)})"


@dataclass(frozen=True)
class Literal:
    """A structured clause literal; positive=False means logical negation."""

    atom: str
    positive: bool = True

    def __post_init__(self) -> None:
        Formula.atom(self.atom)

    @property
    def complement(self) -> 'Literal':
        return Literal(self.atom, not self.positive)

    def notation(self) -> str:
        return self.atom if self.positive else f'NOT ({self.atom})'

    def sort_key(self) -> tuple[str, bool]:
        return self.atom, not self.positive


Clause = frozenset[Literal]


def formula_symbols(formula: Formula) -> set[str]:
    if formula.kind == 'ATOM':
        return {formula.name or ''}
    return set().union(*(formula_symbols(operand) for operand in formula.operands))


def evaluate(formula: Formula, model: dict[str, bool]) -> bool:
    """Evaluate only a validated AST against a complete Boolean model."""
    if formula.kind == 'ATOM':
        if formula.name not in model:
            raise FormulaValidationError(f'Model does not assign the symbol {formula.name!r}.')
        return model[formula.name]
    if formula.kind == 'NOT':
        return not evaluate(formula.operands[0], model)
    if formula.kind == 'AND':
        return all(evaluate(operand, model) for operand in formula.operands)
    if formula.kind == 'OR':
        return any(evaluate(operand, model) for operand in formula.operands)
    if formula.kind == 'IMPLIES':
        left, right = formula.operands
        return not evaluate(left, model) or evaluate(right, model)
    left, right = formula.operands
    return evaluate(left, model) == evaluate(right, model)


def negate(formula: Formula) -> Formula:
    if formula.kind == 'NOT':
        return formula.operands[0]
    return Formula('NOT', (formula,))


def eliminate_implications(formula: Formula) -> Formula:
    """Eliminate -> and <-> while preserving the validated tree structure."""
    if formula.kind == 'ATOM':
        return formula
    if formula.kind == 'NOT':
        return Formula('NOT', (eliminate_implications(formula.operands[0]),))
    if formula.kind == 'IMPLIES':
        left, right = (eliminate_implications(item) for item in formula.operands)
        return Formula('OR', (negate(left), right))
    if formula.kind == 'BICONDITIONAL':
        left, right = (eliminate_implications(item) for item in formula.operands)
        return Formula('AND', (Formula('OR', (negate(left), right)), Formula('OR', (negate(right), left))))
    return Formula(formula.kind, tuple(eliminate_implications(operand) for operand in formula.operands))


def to_nnf(formula: Formula) -> Formula:
    """Push NOT operators to atoms using De Morgan's laws and double-negation removal."""
    implication_free = eliminate_implications(formula)

    def walk(current: Formula, negated: bool = False) -> Formula:
        if current.kind == 'ATOM':
            return negate(current) if negated else current
        if current.kind == 'NOT':
            return walk(current.operands[0], not negated)
        if current.kind not in {'AND', 'OR'}:
            raise FormulaValidationError('NNF conversion encountered an unsupported formula form.')
        kind = {'AND': 'OR', 'OR': 'AND'}[current.kind] if negated else current.kind
        return Formula(kind, tuple(walk(operand, negated) for operand in current.operands))

    return walk(implication_free)


def _literal_from_nnf(formula: Formula) -> Literal:
    if formula.kind == 'ATOM':
        return Literal(formula.name or '', True)
    if formula.kind == 'NOT' and formula.operands[0].kind == 'ATOM':
        return Literal(formula.operands[0].name or '', False)
    raise FormulaValidationError('CNF conversion expected a literal in negation normal form.')


def _merge_clauses(left: Clause, right: Clause) -> Clause | None:
    merged = left | right
    if any(literal.complement in merged for literal in merged):
        return None
    return frozenset(merged)


def cnf_clauses(formula: Formula) -> frozenset[Clause]:
    """Convert a formula to a deterministic set of CNF clauses without using string parsing."""
    nnf = to_nnf(formula)

    def clauses(current: Formula) -> frozenset[Clause]:
        if current.kind in {'ATOM', 'NOT'}:
            return frozenset({frozenset({_literal_from_nnf(current)})})
        if current.kind == 'AND':
            return frozenset().union(*(clauses(operand) for operand in current.operands))
        if current.kind == 'OR':
            combinations: frozenset[Clause] = frozenset({frozenset()})
            for operand in current.operands:
                operand_clauses = clauses(operand)
                if not operand_clauses:
                    return frozenset()
                combinations = frozenset(
                    merged
                    for left in combinations
                    for right in operand_clauses
                    if (merged := _merge_clauses(left, right)) is not None
                )
                if not combinations:
                    return frozenset()
            return combinations
        raise FormulaValidationError('CNF conversion encountered an unsupported formula form.')

    return clauses(nnf)


def clauses_for_formulas(formulas: Iterable[Formula]) -> frozenset[Clause]:
    return frozenset().union(*(cnf_clauses(formula) for formula in formulas))


def clause_to_list(clause: Clause) -> list[dict[str, object]]:
    return [{'atom': literal.atom, 'positive': literal.positive, 'notation': literal.notation()} for literal in sorted(clause, key=Literal.sort_key)]


def clause_notation(clause: Clause) -> str:
    return 'EMPTY CLAUSE' if not clause else ' OR '.join(literal.notation() for literal in sorted(clause, key=Literal.sort_key))
