"""Goal-driven backward chaining with explicit unknown, false, and cycle states."""

from __future__ import annotations

from typing import Any

from .models import Fact, Pattern, Rule, match_pattern


class BackwardChainer:
    def __init__(self, max_depth: int = 20) -> None:
        self.max_depth = max_depth

    def prove(self, goal: Fact, facts: list[Fact], rules: tuple[Rule, ...] | list[Rule]) -> dict[str, Any]:
        facts_by_key = {fact.key: fact for fact in facts}
        trace: list[dict[str, Any]] = []
        result = self._prove_goal(
            goal=goal,
            facts_by_key=facts_by_key,
            rules=sorted(rules, key=lambda rule: (rule.priority, rule.id)),
            trace=trace,
            active_goals=set(),
            depth=0,
        )
        return {
            'success': not result['limit_reached'],
            'goal': goal.to_dict(),
            'established': result['established'],
            'status': result['status'],
            'supporting_facts': result['supporting_facts'],
            'missing_facts': result['missing_facts'],
            'known_false_facts': result['known_false_facts'],
            'attempted_rules': result['attempted_rules'],
            'rule_used': result['rule_used'],
            'reasoning_trace': trace,
            'explanation': result['explanation'],
            'limit_reached': result['limit_reached'],
        }

    def _prove_goal(
        self,
        goal: Fact,
        facts_by_key: dict[tuple[str, tuple[str, ...], bool], Fact],
        rules: list[Rule],
        trace: list[dict[str, Any]],
        active_goals: set[tuple[str, tuple[str, ...], bool]],
        depth: int,
    ) -> dict[str, Any]:
        if depth >= self.max_depth:
            trace.append({'step': 'depth_limit', 'goal': goal.notation(), 'depth': depth})
            return self._result(goal, False, 'limit_reached', limit_reached=True, explanation=f'Proof depth limit reached while checking {goal.notation()}.')
        if goal.key in active_goals:
            trace.append({'step': 'cycle_detected', 'goal': goal.notation()})
            return self._result(goal, False, 'unknown', explanation=f'Cycle detected while checking {goal.notation()}.')

        known = facts_by_key.get(goal.key)
        if known:
            trace.append({'step': 'known_fact', 'goal': goal.notation(), 'value': known.value})
            return self._result(goal, True, 'known_true', supporting_facts=[known.notation()], explanation=f'{goal.notation()} is a known fact in the knowledge base.')

        opposite_key = (goal.predicate, goal.arguments, not goal.value)
        opposite = facts_by_key.get(opposite_key)
        if opposite:
            trace.append({'step': 'known_opposite_fact', 'goal': goal.notation(), 'known_fact': opposite.notation()})
            return self._result(goal, False, 'known_false', known_false_facts=[opposite.notation()], explanation=f'{goal.notation()} cannot be established because {opposite.notation()} is known.')

        active_goals.add(goal.key)
        try:
            matching_rules: list[tuple[Rule, dict[str, str]]] = []
            for rule in rules:
                bindings = match_pattern(rule.conclusion, goal)
                if bindings is not None:
                    matching_rules.append((rule, bindings))
            if not matching_rules:
                trace.append({'step': 'unknown_goal', 'goal': goal.notation()})
                return self._result(goal, False, 'unknown', missing_facts=[goal.notation()], explanation=f'{goal.notation()} is unknown: no fact or rule can establish it.')

            attempted_rules: list[str] = []
            missing_facts: list[str] = []
            known_false_facts: list[str] = []
            for rule, bindings in matching_rules:
                attempted_rules.append(rule.id)
                trace.append({'step': 'try_rule', 'goal': goal.notation(), 'rule_id': rule.id, 'rule_name': rule.name})
                premise_results = []
                for premise in rule.premises:
                    instantiated = premise.instantiate(bindings)
                    premise_goal = Fact(instantiated.predicate, instantiated.arguments, instantiated.value)
                    premise_results.append(self._prove_goal(premise_goal, facts_by_key, rules, trace, active_goals, depth + 1))
                if all(result['established'] for result in premise_results):
                    supports = self._unique(item for result in premise_results for item in result['supporting_facts'])
                    trace.append({'step': 'rule_established', 'goal': goal.notation(), 'rule_id': rule.id, 'supporting_facts': supports})
                    return self._result(
                        goal,
                        True,
                        'established',
                        supporting_facts=supports,
                        attempted_rules=attempted_rules,
                        rule_used=rule.id,
                        explanation=rule.explanation,
                    )
                trace.append({'step': 'rule_not_established', 'goal': goal.notation(), 'rule_id': rule.id})
                missing_facts.extend(item for result in premise_results for item in result['missing_facts'])
                known_false_facts.extend(item for result in premise_results for item in result['known_false_facts'])
                if any(result['limit_reached'] for result in premise_results):
                    return self._result(
                        goal,
                        False,
                        'limit_reached',
                        missing_facts=self._unique(missing_facts),
                        known_false_facts=self._unique(known_false_facts),
                        attempted_rules=attempted_rules,
                        limit_reached=True,
                        explanation=f'Proof limit reached while checking premises for {goal.notation()}.',
                    )
            status = 'known_false' if known_false_facts and not missing_facts else 'unknown'
            if known_false_facts and missing_facts:
                explanation = f'{goal.notation()} could not be established: some premises are known false and others are unknown.'
            elif known_false_facts:
                explanation = f'{goal.notation()} could not be established because a required premise is known false.'
            else:
                explanation = f'{goal.notation()} could not be established because required facts are missing or unknown.'
            return self._result(
                goal,
                False,
                status,
                missing_facts=self._unique(missing_facts),
                known_false_facts=self._unique(known_false_facts),
                attempted_rules=attempted_rules,
                explanation=explanation,
            )
        finally:
            active_goals.discard(goal.key)

    @staticmethod
    def _unique(items: Any) -> list[str]:
        return list(dict.fromkeys(items))

    @staticmethod
    def _result(
        goal: Fact,
        established: bool,
        status: str,
        supporting_facts: list[str] | None = None,
        missing_facts: list[str] | None = None,
        known_false_facts: list[str] | None = None,
        attempted_rules: list[str] | None = None,
        rule_used: str | None = None,
        limit_reached: bool = False,
        explanation: str = '',
    ) -> dict[str, Any]:
        return {
            'goal': goal.notation(),
            'established': established,
            'status': status,
            'supporting_facts': supporting_facts or [],
            'missing_facts': missing_facts or [],
            'known_false_facts': known_false_facts or [],
            'attempted_rules': attempted_rules or [],
            'rule_used': rule_used,
            'limit_reached': limit_reached,
            'explanation': explanation,
        }
