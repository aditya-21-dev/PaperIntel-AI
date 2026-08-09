"""Generic fixed-point forward chaining for PaperIntel rules."""

from __future__ import annotations

from typing import Any

from .models import Fact, Pattern, Rule, match_pattern


class ForwardChainer:
    def __init__(self, max_iterations: int = 50, max_rule_firings: int = 500) -> None:
        self.max_iterations = max_iterations
        self.max_rule_firings = max_rule_firings

    def infer(self, initial_facts: list[Fact], rules: tuple[Rule, ...] | list[Rule]) -> dict[str, Any]:
        """Apply rules until a fixed point or a configured safety limit is reached."""
        facts_by_key = {fact.key: fact for fact in initial_facts}
        facts = list(facts_by_key.values())
        derived_facts: list[Fact] = []
        traces: list[dict[str, Any]] = []
        fired_applications: set[tuple[str, tuple[str, tuple[str, ...], bool], tuple[tuple[str, tuple[str, ...], bool], ...]]] = set()
        ordered_rules = sorted(rules, key=lambda rule: (rule.priority, rule.id))
        iteration = 0
        limit_error: str | None = None

        while iteration < self.max_iterations:
            iteration += 1
            newly_derived = False
            for rule in ordered_rules:
                for bindings, supporting_facts in self._satisfied_bindings(rule.premises, facts):
                    conclusion_pattern = rule.conclusion.instantiate(bindings)
                    conclusion = Fact(
                        predicate=conclusion_pattern.predicate,
                        arguments=conclusion_pattern.arguments,
                        value=conclusion_pattern.value,
                        evidence={
                            'source_module': 'reasoning_engine',
                            'rule_id': rule.id,
                            'supporting_facts': [fact.notation() for fact in supporting_facts],
                        },
                        origin='derived',
                    )
                    application_key = (rule.id, conclusion.key, tuple(fact.key for fact in supporting_facts))
                    if application_key in fired_applications:
                        continue
                    if len(fired_applications) >= self.max_rule_firings:
                        limit_error = f'Maximum rule firing limit ({self.max_rule_firings}) was reached.'
                        break
                    fired_applications.add(application_key)
                    is_new = conclusion.key not in facts_by_key
                    traces.append({
                        'derived_fact': conclusion.to_dict(),
                        'rule_id': rule.id,
                        'rule_name': rule.name,
                        'supporting_facts': [fact.notation() for fact in supporting_facts],
                        'explanation': rule.explanation,
                        'new_fact': is_new,
                    })
                    if is_new:
                        facts_by_key[conclusion.key] = conclusion
                        facts.append(conclusion)
                        derived_facts.append(conclusion)
                        newly_derived = True
                if limit_error:
                    break
            if limit_error or not newly_derived:
                break

        if iteration >= self.max_iterations and newly_derived and not limit_error:
            limit_error = f'Maximum inference iteration limit ({self.max_iterations}) was reached.'

        return {
            'success': limit_error is None,
            'initial_facts': [fact.to_dict() for fact in initial_facts],
            'derived_facts': [fact.to_dict() for fact in derived_facts],
            'reasoning_trace': traces,
            'iterations': iteration,
            'rule_firings': len(fired_applications),
            'limit_reached': limit_error is not None,
            'error': limit_error,
        }

    def _satisfied_bindings(self, premises: tuple[Pattern, ...], facts: list[Fact]) -> list[tuple[dict[str, str], list[Fact]]]:
        matches: list[tuple[dict[str, str], list[Fact]]] = [({}, [])]
        for premise in premises:
            next_matches: list[tuple[dict[str, str], list[Fact]]] = []
            for bindings, support in matches:
                for fact in facts:
                    updated_bindings = match_pattern(premise, fact, bindings)
                    if updated_bindings is not None:
                        next_matches.append((updated_bindings, [*support, fact]))
            matches = next_matches
            if not matches:
                break
        return matches
