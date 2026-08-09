"""Knowledge-based reasoning agent operating strictly on Module 3 knowledge bases."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.knowledge_engine import validate_knowledge_base

from .backward_chaining import BackwardChainer
from .forward_chaining import ForwardChainer
from .models import Fact
from .rules import DEFAULT_RULES


def facts_from_knowledge_base(knowledge_base: dict[str, Any]) -> list[Fact]:
    """Load Module 3 propositional facts; no PDF or structured-document parsing occurs here."""
    facts: list[Fact] = []
    for fact in knowledge_base.get('propositional_facts', []):
        if not isinstance(fact, dict):
            continue
        predicate = fact.get('predicate')
        arguments = fact.get('arguments')
        value = fact.get('value')
        if isinstance(predicate, str) and isinstance(arguments, list) and all(isinstance(argument, str) for argument in arguments) and isinstance(value, bool):
            facts.append(Fact(predicate, tuple(arguments), value, fact.get('evidence'), 'knowledge_base'))
    return facts


class ReasoningAgent:
    """PERCEIVE → UPDATE KNOWLEDGE → REASON → QUERY/EXPLAIN for a single in-memory KB."""

    def __init__(self) -> None:
        self._knowledge_base: dict[str, Any] | None = None
        self._facts: list[Fact] = []
        self._forward = ForwardChainer()
        self._backward = BackwardChainer()

    def perceive(self, knowledge_base: dict[str, Any]) -> None:
        validation = validate_knowledge_base(knowledge_base)
        if not validation['valid']:
            raise ValueError('Knowledge base validation failed before reasoning.')
        self._knowledge_base = deepcopy(knowledge_base)
        self._facts = facts_from_knowledge_base(self._knowledge_base)

    def forward_reason(self, knowledge_base: dict[str, Any] | None = None) -> dict[str, Any]:
        if knowledge_base is not None:
            self.perceive(knowledge_base)
        self._require_knowledge_base()
        return self._forward.infer(self._facts, DEFAULT_RULES)

    def backward_reason(self, goal: dict[str, Any], knowledge_base: dict[str, Any] | None = None) -> dict[str, Any]:
        if knowledge_base is not None:
            self.perceive(knowledge_base)
        self._require_knowledge_base()
        predicate = goal.get('predicate') if isinstance(goal, dict) else None
        arguments = goal.get('arguments') if isinstance(goal, dict) else None
        value = goal.get('value', True) if isinstance(goal, dict) else True
        if not isinstance(predicate, str) or not isinstance(arguments, list) or not all(isinstance(argument, str) for argument in arguments) or not isinstance(value, bool):
            raise ValueError('Goal requires a predicate, entity-ID arguments, and an optional Boolean value.')
        return self._backward.prove(Fact(predicate, tuple(arguments), value), self._facts, DEFAULT_RULES)

    @staticmethod
    def rules() -> list[dict[str, Any]]:
        return [rule.to_dict() for rule in DEFAULT_RULES]

    def clear(self) -> None:
        self._knowledge_base = None
        self._facts = []

    def _require_knowledge_base(self) -> None:
        if self._knowledge_base is None:
            raise LookupError('No Module 3 knowledge base is available for reasoning.')
