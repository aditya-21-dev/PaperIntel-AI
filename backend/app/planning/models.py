"""Serializable state-space planning primitives for Module 7."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


StateValue = bool | int | str
SUPPORTED_OPERATORS = frozenset({
    'EQUALS', 'NOT_EQUALS', 'LESS_THAN', 'LESS_THAN_OR_EQUAL',
    'GREATER_THAN', 'GREATER_THAN_OR_EQUAL',
})
SUPPORTED_EFFECTS = frozenset({'SET'})


class PlanningValidationError(ValueError):
    """Raised when a planning state, condition, or action is malformed."""


def _valid_value(value: object) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, int):
        return value >= 0
    return isinstance(value, str)


@dataclass(frozen=True)
class PaperState:
    """An immutable, hashable hypothetical state; it never changes the source paper."""

    values: tuple[tuple[str, StateValue], ...]

    def __post_init__(self) -> None:
        names = [name for name, _ in self.values]
        if names != sorted(names) or len(set(names)) != len(names):
            raise PlanningValidationError('Paper-state values must have unique, sorted variable names.')
        if any(not isinstance(name, str) or not name or not _valid_value(value) for name, value in self.values):
            raise PlanningValidationError('Paper-state values must be named non-negative primitive values.')

    @classmethod
    def from_dict(cls, values: dict[str, StateValue]) -> PaperState:
        if not isinstance(values, dict):
            raise PlanningValidationError('A paper state must be created from an object.')
        return cls(tuple(sorted(values.items())))

    def to_dict(self) -> dict[str, StateValue]:
        return dict(self.values)

    def get(self, variable: str) -> StateValue | None:
        return self.to_dict().get(variable)

    def with_updates(self, updates: dict[str, StateValue]) -> PaperState:
        values = self.to_dict()
        values.update(updates)
        return PaperState.from_dict(values)


@dataclass(frozen=True)
class Condition:
    """A data-defined precondition evaluated by the generic action model."""

    variable: str
    operator: str
    expected: StateValue

    def __post_init__(self) -> None:
        if not isinstance(self.variable, str) or not self.variable or self.operator not in SUPPORTED_OPERATORS or not _valid_value(self.expected):
            raise PlanningValidationError('Planning conditions require a variable, supported operator, and primitive expected value.')

    def matches(self, state: PaperState) -> bool:
        actual = state.get(self.variable)
        if actual is None or type(actual) is not type(self.expected):
            return False
        if self.operator == 'EQUALS':
            return actual == self.expected
        if self.operator == 'NOT_EQUALS':
            return actual != self.expected
        if self.operator == 'LESS_THAN':
            return actual < self.expected
        if self.operator == 'LESS_THAN_OR_EQUAL':
            return actual <= self.expected
        if self.operator == 'GREATER_THAN':
            return actual > self.expected
        return actual >= self.expected

    def to_dict(self) -> dict[str, StateValue | str]:
        return {'variable': self.variable, 'operator': self.operator, 'expected': self.expected}


@dataclass(frozen=True)
class StateEffect:
    """A data-defined state transition; Module 7 currently uses deterministic SET effects."""

    variable: str
    operation: str
    value: StateValue

    def __post_init__(self) -> None:
        if not isinstance(self.variable, str) or not self.variable or self.operation not in SUPPORTED_EFFECTS or not _valid_value(self.value):
            raise PlanningValidationError('State effects require a variable, supported operation, and primitive value.')

    def apply(self, state: PaperState) -> PaperState:
        return state.with_updates({self.variable: self.value})

    def to_dict(self) -> dict[str, StateValue | str]:
        return {'variable': self.variable, 'operation': self.operation, 'value': self.value}


@dataclass(frozen=True)
class ImprovementAction:
    """A possible editing task, represented independently from the search algorithms."""

    id: str
    name: str
    preconditions: tuple[Condition, ...]
    effects: tuple[StateEffect, ...]
    cost: int
    affected_variables: tuple[str, ...]
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id or not isinstance(self.name, str) or not self.name:
            raise PlanningValidationError('Improvement actions require an ID and a name.')
        if not self.effects or not isinstance(self.cost, int) or isinstance(self.cost, bool) or self.cost <= 0:
            raise PlanningValidationError('Improvement actions require effects and a positive integer cost.')
        if not self.affected_variables or not all(isinstance(variable, str) and variable for variable in self.affected_variables):
            raise PlanningValidationError('Improvement actions require affected variables.')
        if not isinstance(self.explanation, str) or not self.explanation:
            raise PlanningValidationError('Improvement actions require an explanation.')

    def is_applicable(self, state: PaperState) -> bool:
        return all(condition.matches(state) for condition in self.preconditions)

    def apply(self, state: PaperState) -> PaperState:
        if not self.is_applicable(state):
            raise PlanningValidationError(f'Action {self.id} cannot be applied because its preconditions are not met.')
        result = state
        for effect in self.effects:
            result = effect.apply(result)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'preconditions': [condition.to_dict() for condition in self.preconditions],
            'effects': [effect.to_dict() for effect in self.effects],
            'cost': self.cost,
            'affected_variables': list(self.affected_variables),
            'explanation': self.explanation,
        }
