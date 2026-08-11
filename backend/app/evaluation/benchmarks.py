"""Small, explicit ground-truth cases used by the Module 9 evaluator."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import fitz

from app.compliance.models import Constraint
from app.planning.models import Condition, ImprovementAction, PaperState, StateEffect
from app.planning.search import PlanningProblem


def structured_paper(
    *,
    pages: int = 5,
    abstract_words: int = 120,
    include_results: bool = True,
    keywords: list[str] | None = None,
    references: int = 20,
) -> dict[str, Any]:
    """Return a controlled Module 2-shaped document with declared properties."""
    sections = [
        {'number': '1', 'title': 'Introduction', 'text': 'Problem context.', 'page_start': 1, 'page_end': 1},
        {'number': '2', 'title': 'Methodology', 'text': 'Deterministic method.', 'page_start': 2, 'page_end': 2},
        {'number': '4', 'title': 'Conclusion', 'text': 'Conclusion.', 'page_start': 4, 'page_end': 4},
    ]
    if include_results:
        sections.insert(2, {'number': '3', 'title': 'Results', 'text': 'Observed results.', 'page_start': 3, 'page_end': 3})
    return {
        'document': {'filename': 'module-9-benchmark.pdf', 'file_size': 4096, 'page_count': pages},
        'metadata': {
            'title': 'Module 9 Benchmark Paper', 'title_confidence': 'high',
            'authors': ['A. Researcher'], 'authors_confidence': 'high',
            'abstract': 'A controlled abstract.', 'abstract_word_count': abstract_words,
            'keywords': ['reasoning', 'planning'] if keywords is None else keywords,
        },
        'sections': sections,
        'references': [{'number': index, 'text': f'Reference {index}'} for index in range(1, references + 1)],
        'figures': [{'number': 1, 'caption': 'Pipeline.', 'page': 2, 'detected_from': 'caption'}],
        'tables': [{'number': 1, 'caption': 'Metrics.', 'page': 3, 'detected_from': 'caption'}],
        'statistics': {}, 'warnings': [],
    }


def document_with_unknown_page_count() -> dict[str, Any]:
    document = structured_paper()
    document['document']['page_count'] = None
    return document


def strict_requirements() -> dict[str, Any]:
    return {
        'profile_id': 'custom',
        'venue': 'Module 9 Benchmark Venue',
        'requirements': {
            'max_pages': 6,
            'max_abstract_words': 250,
            'keywords_required': True,
            'required_sections': ['Introduction', 'Methodology', 'Results', 'Conclusion'],
            'min_references': 15,
        },
    }


def knowledge_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'knowledge_complete_structure',
            'input': structured_paper(),
            'expected_facts': {
                'PaperHasAbstract': True, 'PaperHasKeywords': True,
                'PaperHasIntroduction': True, 'PaperHasMethodology': True,
                'PaperHasResults': True, 'PaperHasConclusion': True,
                'PaperHasReferences': True, 'PaperHasFigures': True, 'PaperHasTables': True,
            },
        },
        {
            'id': 'knowledge_missing_results_and_keywords',
            'input': structured_paper(include_results=False, keywords=[], references=0),
            'expected_facts': {
                'PaperHasAbstract': True, 'PaperHasKeywords': False,
                'PaperHasIntroduction': True, 'PaperHasMethodology': True,
                'PaperHasResults': False, 'PaperHasConclusion': True,
                'PaperHasReferences': False, 'PaperHasFigures': True, 'PaperHasTables': True,
            },
        },
    )


def reasoning_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'reasoning_established_goal', 'input': structured_paper(),
            'goal': {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001'], 'value': True},
            'expected_status': 'ESTABLISHED', 'expected_derived': {'CoreStructureComplete'},
        },
        {
            'id': 'reasoning_known_false_goal', 'input': structured_paper(include_results=False),
            'goal': {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001'], 'value': True},
            'expected_status': 'NOT_ESTABLISHED', 'expected_derived': set(),
        },
        {
            'id': 'reasoning_unsupported_goal', 'input': structured_paper(),
            'goal': {'predicate': 'PaperHasAppendix', 'arguments': ['paper_001'], 'value': True},
            'expected_status': 'UNSUPPORTED', 'expected_derived': set(),
        },
    )


def logic_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'logic_entailed', 'input': structured_paper(),
            'operation': 'query',
            'query': {'predicate': 'CoreStructureComplete', 'arguments': ['paper_001']},
            'expected_status': 'ENTAILED',
        },
        {
            'id': 'logic_contradicted', 'input': structured_paper(include_results=False),
            'operation': 'query',
            'query': {'predicate': 'PaperHasResults', 'arguments': ['paper_001']},
            'expected_status': 'CONTRADICTED',
        },
        {
            'id': 'logic_unknown', 'input': structured_paper(),
            'operation': 'query',
            'query': {'predicate': 'PaperHasAppendix', 'arguments': ['paper_001']},
            'expected_status': 'UNKNOWN',
        },
        {
            'id': 'logic_consistent', 'input': structured_paper(),
            'operation': 'consistency', 'expected_status': 'CONSISTENT',
        },
        {
            'id': 'logic_inconsistent', 'input': structured_paper(),
            'operation': 'inconsistent_consistency', 'expected_status': 'INCONSISTENT',
        },
    )


def compliance_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'csp_compliant', 'input': structured_paper(), 'requirements': strict_requirements(),
            'expected_status': 'COMPLIANT',
            'expected_constraints': {
                'max_pages': 'SATISFIED', 'max_abstract_words': 'SATISFIED',
                'keywords_required': 'SATISFIED', 'required_sections': 'SATISFIED',
                'min_references': 'SATISFIED',
            },
            'expected_requirements_consistent': True,
        },
        {
            'id': 'csp_page_violation', 'input': structured_paper(pages=7),
            'requirements': {'requirements': {'max_pages': 6}},
            'expected_status': 'NON_COMPLIANT', 'expected_constraints': {'max_pages': 'VIOLATED'},
            'expected_requirements_consistent': True,
        },
        {
            'id': 'csp_unknown_page_count', 'input': document_with_unknown_page_count(),
            'requirements': {'requirements': {'max_pages': 6}},
            'expected_status': 'INCOMPLETE', 'expected_constraints': {'max_pages': 'UNKNOWN'},
            'expected_requirements_consistent': True,
        },
        {
            'id': 'csp_inconsistent_requirements', 'input': structured_paper(),
            'requirements': {'requirements': {'min_pages': 8, 'max_pages': 6}},
            'expected_status': 'NO_SOLUTION', 'expected_constraints': {},
            'expected_requirements_consistent': False,
        },
    )


def _action(identifier: str, name: str, expected: int, cost: int) -> ImprovementAction:
    return ImprovementAction(
        identifier, name, (Condition('X', 'EQUALS', 0),), (StateEffect('X', 'SET', expected),),
        cost, ('X',), f'{name} benchmark action.',
    )


def no_solution_problem() -> PlanningProblem:
    goal = Constraint('C001', 'target_x', ('X',), 'EQUALS', 2, 'ERROR', 'X must reach two.')
    return PlanningProblem(PaperState.from_dict({'X': 0}), (_action('A001', 'OnlyStep', 1, 1),), (goal,))


def planning_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'planning_page_reduction', 'kind': 'compliance',
            'input': structured_paper(pages=7), 'requirements': {'requirements': {'max_pages': 6}},
            'expected_status': 'PLAN_FOUND', 'expected_cost': 4,
        },
        {
            'id': 'planning_no_solution', 'kind': 'problem', 'problem': no_solution_problem(),
            'expected_status': 'NO_SOLUTION', 'expected_cost': 0,
        },
    )


def integration_cases() -> tuple[dict[str, Any], ...]:
    return (
        {
            'id': 'integrated_ready', 'input': structured_paper(), 'requirements': strict_requirements(),
            'expected_status': 'READY',
        },
        {
            'id': 'integrated_needs_improvement', 'input': structured_paper(pages=7, abstract_words=300, references=10),
            'requirements': strict_requirements(), 'expected_status': 'NEEDS_IMPROVEMENT',
        },
    )


def pdf_extraction_cases() -> tuple[dict[str, Any], ...]:
    """Annotated PDFs are created in memory; expected values are the ground truth."""
    return (
        {
            'id': 'pdf_structured_research_paper',
            'pages': [[
                ('A Practical Study of PDF Extraction', 18), ('Alice Smith, Bob Jones', 11),
                ('Abstract', 12), ('This paper presents a deterministic extraction workflow for research papers.', 10),
                ('Keywords: PDF parsing, document analysis, research', 10), ('1 Introduction', 12),
                ('Introduction text describes the research context.', 10), ('Figure 1: Processing pipeline', 10),
                ('Table 1: Extracted metadata fields', 10),
            ], [
                ('2 Methodology', 12), ('Methods are implemented with deterministic heuristics.', 10),
                ('References', 12), ('[1] A. Author. PDF extraction methods. 2024.', 10),
                ('[2] B. Author. Structured documents. 2023.', 10),
            ]],
            'ground_truth': {
                'title': {'A Practical Study of PDF Extraction'},
                'authors': {'Alice Smith', 'Bob Jones'},
                'abstract': {'This paper presents a deterministic extraction workflow for research papers.'},
                'keywords': {'PDF parsing', 'document analysis', 'research'},
                'sections': {'Introduction', 'Methodology'},
                'references': {1, 2}, 'figures': {1}, 'tables': {1},
            },
        },
    )


def build_pdf_bytes(pages: list[list[tuple[str, float]]]) -> bytes:
    document = fitz.open()
    try:
        for page_lines in pages:
            page = document.new_page()
            y = 72
            for text, size in page_lines:
                page.insert_text((72, y), text, fontsize=size)
                y += size + 12
        return document.tobytes()
    finally:
        document.close()


def contradictory_knowledge_base(knowledge_base: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(knowledge_base)
    original = next(item for item in result['propositional_facts'] if item['predicate'] == 'PaperHasResults')
    opposite = deepcopy(original)
    opposite['value'] = not original['value']
    result['propositional_facts'].append(opposite)
    return result
