"""Data models shared by the Module 4 rule base and inference engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def is_variable(value: str) -> bool:
    """Rules use all-uppercase identifiers such as P as variables."""
    return value.isupper() and value.replace('_', '').isalnum()


@dataclass(frozen=True)
class Pattern:
    predicate: str
    arguments: tuple[str, ...]
    value: bool = True

    def instantiate(self, bindings: dict[str, str]) -> 'Pattern':
        return Pattern(
            predicate=self.predicate,
            arguments=tuple(bindings.get(argument, argument) if is_variable(argument) else argument for argument in self.arguments),
            value=self.value,
        )

    def notation(self) -> str:
        statement = f"{self.predicate}({', '.join(self.arguments)})"
        return statement if self.value else f'NOT {statement}'


@dataclass(frozen=True)
class Fact:
    predicate: str
    arguments: tuple[str, ...]
    value: bool
    evidence: dict[str, Any] | None = field(default=None, compare=False, hash=False)
    origin: str = field(default='knowledge_base', compare=False, hash=False)

    @property
    def key(self) -> tuple[str, tuple[str, ...], bool]:
        return self.predicate, self.arguments, self.value

    def notation(self) -> str:
        statement = f"{self.predicate}({', '.join(self.arguments)})"
        return statement if self.value else f'NOT {statement}'

    def to_dict(self) -> dict[str, Any]:
        result = {
            'predicate': self.predicate,
            'arguments': list(self.arguments),
            'value': self.value,
            'origin': self.origin,
        }
        if self.evidence is not None:
            result['evidence'] = self.evidence
        return result


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    premises: tuple[Pattern, ...]
    conclusion: Pattern
    explanation: str
    priority: int = 100
    source_module: str = 'module_4'

    def to_dict(self) -> dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'premises': [
                {'predicate': premise.predicate, 'arguments': list(premise.arguments), 'value': premise.value}
                for premise in self.premises
            ],
            'conclusion': {
                'predicate': self.conclusion.predicate,
                'arguments': list(self.conclusion.arguments),
                'value': self.conclusion.value,
            },
            'explanation': self.explanation,
            'priority': self.priority,
            'source_module': self.source_module,
        }


def match_pattern(pattern: Pattern, fact: Fact, bindings: dict[str, str] | None = None) -> dict[str, str] | None:
    """Unify a rule pattern with a concrete fact without altering either object."""
    if pattern.predicate != fact.predicate or pattern.value != fact.value or len(pattern.arguments) != len(fact.arguments):
        return None
    result = dict(bindings or {})
    for pattern_argument, fact_argument in zip(pattern.arguments, fact.arguments):
        if is_variable(pattern_argument):
            existing = result.get(pattern_argument)
            if existing is not None and existing != fact_argument:
                return None
            result[pattern_argument] = fact_argument
        elif pattern_argument != fact_argument:
            return None
    return result
