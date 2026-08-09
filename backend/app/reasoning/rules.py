"""The small, controlled Module 4 rule base.

Rules are data. The forward and backward engines never special-case a paper
structure rule, so future rules can be added without changing inference logic.
"""

from .models import Pattern, Rule


REASONING_PREDICATES = {
    'PaperHasAbstract', 'PaperHasKeywords', 'PaperHasIntroduction', 'PaperHasLiteratureReview',
    'PaperHasMethodology', 'PaperHasResults', 'PaperHasDiscussion', 'PaperHasConclusion',
    'PaperHasReferences', 'PaperHasFigures', 'PaperHasTables', 'CoreStructureComplete',
    'HasCompleteResultsDiscussionFlow', 'HasReferenceSection', 'HasAtLeastOneFigure',
    'HasAtLeastOneTable', 'HasMajorStructuralComponents',
}


DEFAULT_RULES: tuple[Rule, ...] = (
    Rule(
        id='R001',
        name='complete_core_structure',
        premises=(
            Pattern('PaperHasAbstract', ('P',)),
            Pattern('HasMajorStructuralComponents', ('P',)),
        ),
        conclusion=Pattern('CoreStructureComplete', ('P',)),
        explanation='The paper has an abstract and all major structural components.',
        priority=10,
    ),
    Rule(
        id='R002',
        name='major_structural_components',
        premises=(
            Pattern('PaperHasIntroduction', ('P',)),
            Pattern('PaperHasMethodology', ('P',)),
            Pattern('PaperHasResults', ('P',)),
            Pattern('PaperHasConclusion', ('P',)),
        ),
        conclusion=Pattern('HasMajorStructuralComponents', ('P',)),
        explanation='The paper contains introduction, methodology, results, and conclusion sections.',
        priority=20,
    ),
    Rule(
        id='R003',
        name='reference_section_present',
        premises=(Pattern('PaperHasReferences', ('P',)),),
        conclusion=Pattern('HasReferenceSection', ('P',)),
        explanation='The knowledge base records one or more references for the paper.',
        priority=30,
    ),
    Rule(
        id='R004',
        name='at_least_one_figure',
        premises=(Pattern('PaperHasFigures', ('P',)),),
        conclusion=Pattern('HasAtLeastOneFigure', ('P',)),
        explanation='The knowledge base records at least one figure for the paper.',
        priority=40,
    ),
    Rule(
        id='R005',
        name='at_least_one_table',
        premises=(Pattern('PaperHasTables', ('P',)),),
        conclusion=Pattern('HasAtLeastOneTable', ('P',)),
        explanation='The knowledge base records at least one table for the paper.',
        priority=50,
    ),
    Rule(
        id='R006',
        name='complete_results_discussion_flow',
        premises=(
            Pattern('PaperHasResults', ('P',)),
            Pattern('PaperHasDiscussion', ('P',)),
            Pattern('PaperHasConclusion', ('P',)),
        ),
        conclusion=Pattern('HasCompleteResultsDiscussionFlow', ('P',)),
        explanation='The paper contains results, discussion, and conclusion components.',
        priority=60,
    ),
)
