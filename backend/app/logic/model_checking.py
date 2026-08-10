"""Bounded, genuine propositional model checking for Module 5."""

from __future__ import annotations

from itertools import product
from typing import Iterable

from .models import Formula, evaluate, formula_symbols


class ModelLimitError(ValueError):
    """Raised before checking a propositional model space that is too large."""


class ModelChecker:
    def __init__(self, max_symbols: int = 16, max_models: int = 65536, max_detailed_models: int = 64) -> None:
        self.max_symbols = max_symbols
        self.max_models = max_models
        self.max_detailed_models = max_detailed_models

    def check(self, knowledge_base: Iterable[Formula], query: Formula, include_models: bool = False) -> dict[str, object]:
        formulas = tuple(knowledge_base)
        symbols = sorted(set().union(*(formula_symbols(formula) for formula in (*formulas, query))))
        model_count = 1 << len(symbols)
        if len(symbols) > self.max_symbols or model_count > self.max_models:
            raise ModelLimitError(
                f'Logical verification needs {model_count} models for {len(symbols)} symbols; '
                f'the configured safety limit is {self.max_models} models / {self.max_symbols} symbols.'
            )

        satisfying_models = 0
        query_true_models = 0
        query_false_models = 0
        detailed_models: list[dict[str, object]] = []
        true_witness: dict[str, object] | None = None
        false_witness: dict[str, object] | None = None

        for values in product((False, True), repeat=len(symbols)):
            assignment = dict(zip(symbols, values))
            if not all(evaluate(formula, assignment) for formula in formulas):
                continue
            satisfying_models += 1
            query_value = evaluate(query, assignment)
            witness = {'assignment': assignment, 'query_value': query_value}
            if query_value:
                query_true_models += 1
                true_witness = true_witness or witness
            else:
                query_false_models += 1
                false_witness = false_witness or witness
            if include_models and len(detailed_models) < self.max_detailed_models:
                detailed_models.append(witness)

        if satisfying_models == 0:
            status = 'INCONSISTENT'
            explanation = 'No Boolean model satisfies the supplied knowledge base, so a three-state query result would be vacuous.'
            counter_models: list[dict[str, object]] = []
        elif query_false_models == 0:
            status = 'ENTAILED'
            explanation = 'The query is true in every model that satisfies the supplied knowledge base.'
            counter_models = []
        elif query_true_models == 0:
            status = 'CONTRADICTED'
            explanation = 'The query is false in every model that satisfies the supplied knowledge base; its negation is entailed.'
            counter_models = [false_witness] if false_witness else []
        else:
            status = 'UNKNOWN'
            explanation = 'Some models satisfying the knowledge base make the query true and others make it false.'
            counter_models = [witness for witness in (true_witness, false_witness) if witness]

        result: dict[str, object] = {
            'success': True,
            'status': status,
            'symbols': symbols,
            'models_checked': model_count,
            'models_satisfying_kb': satisfying_models,
            'counter_models': counter_models,
            'trace': [
                {'step': 'symbols_extracted', 'symbols': symbols},
                {'step': 'model_space_checked', 'models_checked': model_count},
                {
                    'step': 'knowledge_base_models',
                    'models_satisfying_kb': satisfying_models,
                    'query_true_models': query_true_models,
                    'query_false_models': query_false_models,
                },
                {'step': 'classification', 'status': status, 'explanation': explanation},
            ],
            'explanation': explanation,
        }
        if include_models:
            result['models'] = detailed_models
            result['models_truncated'] = satisfying_models > len(detailed_models)
        return result
