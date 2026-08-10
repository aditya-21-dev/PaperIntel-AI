"""Structured CSP variables and constraints, independent from the solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_OPERATORS = frozenset({
    'EQUALS', 'NOT_EQUALS', 'LESS_THAN', 'LESS_THAN_OR_EQUAL',
    'GREATER_THAN', 'GREATER_THAN_OR_EQUAL', 'BETWEEN', 'IMPLIES',
    'ALL_EQUALS', 'ORDERED', 'DIFFERENT',
})
SEVERITIES = frozenset({'ERROR', 'WARNING'})


class CSPValidationError(ValueError):
    """Raised when a CSP variable, constraint, or profile is malformed."""


def value_sort_key(value: object) -> tuple[str, str]:
    """Provide deterministic ordering for the primitive finite-domain values we accept."""
    return type(value).__name__, repr(value)


@dataclass(frozen=True)
class CSPVariable:
    name: str
    domain: tuple[bool | int | str, ...]
    evidence: dict[str, Any] | None = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise CSPValidationError('CSP variables require a non-empty name.')
        if not self.domain:
            raise CSPValidationError(f'CSP variable {self.name} has an empty domain.')
        if any(not isinstance(value, (bool, int, str)) for value in self.domain):
            raise CSPValidationError(f'CSP variable {self.name} uses an unsupported domain value.')
        if len(set(self.domain)) != len(self.domain):
            raise CSPValidationError(f'CSP variable {self.name} has duplicate domain values.')

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {'name': self.name, 'domain': list(self.domain)}
        if self.evidence is not None:
            result['evidence'] = self.evidence
        return result


@dataclass(frozen=True)
class Constraint:
    """A declarative finite-domain constraint; solvers only call its generic methods."""

    id: str
    name: str
    variables: tuple[str, ...]
    operator: str
    expected: Any
    severity: str
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id or not isinstance(self.name, str) or not self.name:
            raise CSPValidationError('Constraints require an ID and a name.')
        if not self.variables or not all(isinstance(variable, str) and variable for variable in self.variables):
            raise CSPValidationError(f'Constraint {self.id} requires one or more variables.')
        if self.operator not in SUPPORTED_OPERATORS:
            raise CSPValidationError(f'Constraint {self.id} uses unsupported operator {self.operator!r}.')
        if self.severity not in SEVERITIES:
            raise CSPValidationError(f'Constraint {self.id} uses unsupported severity {self.severity!r}.')
        if not isinstance(self.explanation, str) or not self.explanation:
            raise CSPValidationError(f'Constraint {self.id} requires an explanation.')
        expected_counts = {
            'EQUALS': 1, 'NOT_EQUALS': 1, 'LESS_THAN': 1, 'LESS_THAN_OR_EQUAL': 1,
            'GREATER_THAN': 1, 'GREATER_THAN_OR_EQUAL': 1, 'BETWEEN': 1,
            'IMPLIES': 2, 'ORDERED': 2, 'DIFFERENT': 2,
        }
        if self.operator in expected_counts and len(self.variables) != expected_counts[self.operator]:
            raise CSPValidationError(f'Constraint {self.id} expects {expected_counts[self.operator]} variables.')
        if self.operator == 'ALL_EQUALS' and len(self.variables) < 2:
            raise CSPValidationError(f'Constraint {self.id} requires at least two variables.')
        if self.operator == 'BETWEEN' and (
            not isinstance(self.expected, dict)
            or not isinstance(self.expected.get('min'), (int, float))
            or not isinstance(self.expected.get('max'), (int, float))
        ):
            raise CSPValidationError(f'Constraint {self.id} requires numeric min and max values.')
        if self.operator == 'IMPLIES' and (
            not isinstance(self.expected, dict) or 'if' not in self.expected or 'then' not in self.expected
        ):
            raise CSPValidationError(f'Constraint {self.id} requires implication if/then values.')

    def is_satisfied(self, values: dict[str, bool | int | str]) -> bool:
        """Evaluate a complete assignment for this constraint's scope only."""
        if set(values) != set(self.variables):
            raise CSPValidationError(f'Constraint {self.id} was evaluated with an incomplete scope assignment.')
        ordered = [values[variable] for variable in self.variables]
        if self.operator == 'EQUALS':
            return ordered[0] == self.expected
        if self.operator == 'NOT_EQUALS':
            return ordered[0] != self.expected
        if self.operator == 'LESS_THAN':
            return ordered[0] < self.expected
        if self.operator == 'LESS_THAN_OR_EQUAL':
            return ordered[0] <= self.expected
        if self.operator == 'GREATER_THAN':
            return ordered[0] > self.expected
        if self.operator == 'GREATER_THAN_OR_EQUAL':
            return ordered[0] >= self.expected
        if self.operator == 'BETWEEN':
            return self.expected['min'] <= ordered[0] <= self.expected['max']
        if self.operator == 'IMPLIES':
            return ordered[0] != self.expected['if'] or ordered[1] == self.expected['then']
        if self.operator == 'ALL_EQUALS':
            return all(value == self.expected for value in ordered)
        if self.operator == 'ORDERED':
            return ordered[0] < ordered[1]
        return ordered[0] != ordered[1]

    def evaluate_partial(self, assignment: dict[str, bool | int | str]) -> tuple[str, Any]:
        """Return a three-state direct validation result without inventing missing values."""
        actual = assignment.get(self.variables[0]) if len(self.variables) == 1 else {
            variable: assignment.get(variable) for variable in self.variables
        }
        if any(variable not in assignment for variable in self.variables):
            return 'UNKNOWN', actual
        scoped = {variable: assignment[variable] for variable in self.variables}
        return ('SATISFIED' if self.is_satisfied(scoped) else 'VIOLATED'), actual

    def expected_notation(self) -> str:
        display = {
            'EQUALS': '= ', 'NOT_EQUALS': '!= ', 'LESS_THAN': '< ', 'LESS_THAN_OR_EQUAL': '<= ',
            'GREATER_THAN': '> ', 'GREATER_THAN_OR_EQUAL': '>= ',
        }
        if self.operator in display:
            return f'{display[self.operator]}{self.expected}'
        if self.operator == 'BETWEEN':
            return f"between {self.expected['min']} and {self.expected['max']}"
        if self.operator == 'IMPLIES':
            return f"if {self.variables[0]} = {self.expected['if']}, then {self.variables[1]} = {self.expected['then']}"
        if self.operator == 'ALL_EQUALS':
            return f'all equal {self.expected}'
        if self.operator == 'ORDERED':
            return f'{self.variables[0]} before {self.variables[1]}'
        return f'{self.variables[0]} != {self.variables[1]}'

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'variables': list(self.variables),
            'operator': self.operator,
            'expected': self.expected,
            'severity': self.severity,
            'explanation': self.explanation,
        }


@dataclass(frozen=True)
class CSPProblem:
    variables: dict[str, CSPVariable]
    constraints: tuple[Constraint, ...]

    def __post_init__(self) -> None:
        if not self.variables:
            raise CSPValidationError('A CSP requires variables.')
        if set(self.variables) != {variable.name for variable in self.variables.values()}:
            raise CSPValidationError('CSP variable dictionary keys must match variable names.')
        known_ids: set[str] = set()
        for constraint in self.constraints:
            if constraint.id in known_ids:
                raise CSPValidationError(f'Duplicate constraint ID {constraint.id}.')
            known_ids.add(constraint.id)
            unknown = set(constraint.variables) - set(self.variables)
            if unknown:
                raise CSPValidationError(f'Constraint {constraint.id} references unknown variables: {sorted(unknown)}.')

