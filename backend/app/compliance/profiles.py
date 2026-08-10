"""Configurable publication-requirement profiles for the Module 6 CSP model."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .models import CSPValidationError


GENERIC_RESEARCH_PAPER_PROFILE: dict[str, Any] = {
    'id': 'generic_research_paper',
    'name': 'Generic Research Paper',
    'description': 'A transparent baseline profile that can be overridden for a target venue.',
    'venue': 'Generic Research Paper',
    'requirements': {
        'max_pages': 20,
        'abstract_required': True,
        'max_abstract_words': 350,
        'keywords_required': True,
        'min_keywords': 1,
        'required_sections': ['Introduction', 'Methodology', 'Results', 'Conclusion'],
        'min_references': 1,
    },
}

SUPPORTED_REQUIREMENTS = frozenset({
    'min_pages', 'max_pages', 'abstract_required', 'min_abstract_words', 'max_abstract_words',
    'keywords_required', 'min_keywords', 'required_sections', 'required_section_order',
    'min_references', 'max_references', 'figures_required', 'tables_required',
    'author_information_required', 'methodology_requires_results', 'results_requires_methodology',
})
SECTION_NAMES = {
    'introduction': 'Introduction',
    'methodology': 'Methodology',
    'results': 'Results',
    'conclusion': 'Conclusion',
}


def available_profiles() -> list[dict[str, Any]]:
    return [deepcopy(GENERIC_RESEARCH_PAPER_PROFILE)]


def resolve_profile(raw: object | None) -> dict[str, Any]:
    """Resolve the generic profile or a custom profile without hard-coding a venue."""
    if raw is None:
        return deepcopy(GENERIC_RESEARCH_PAPER_PROFILE)
    if not isinstance(raw, dict):
        raise CSPValidationError('Publication requirements must be an object.')
    if 'requirements' not in raw:
        raw = {'profile_id': 'custom', 'requirements': raw}
    requirements = raw.get('requirements')
    if not isinstance(requirements, dict):
        raise CSPValidationError('Publication requirements must contain a requirements object.')
    profile_id = raw.get('profile_id', 'custom')
    if profile_id == 'generic_research_paper':
        profile = deepcopy(GENERIC_RESEARCH_PAPER_PROFILE)
        profile['requirements'].update(requirements)
    elif profile_id == 'custom':
        profile = {
            'id': 'custom',
            'name': raw.get('name') if isinstance(raw.get('name'), str) and raw['name'].strip() else 'Custom Venue',
            'description': 'A caller-supplied publication requirement profile.',
            'venue': raw.get('venue') if isinstance(raw.get('venue'), str) and raw['venue'].strip() else 'Custom Venue',
            'requirements': deepcopy(requirements),
        }
    else:
        raise CSPValidationError(f'Unknown requirement profile {profile_id!r}.')
    _validate_requirements(profile['requirements'])
    return profile


def _validate_requirements(requirements: dict[str, Any]) -> None:
    unknown = set(requirements) - SUPPORTED_REQUIREMENTS
    if unknown:
        raise CSPValidationError(f'Unsupported publication requirements: {sorted(unknown)}.')
    for key, value in requirements.items():
        if key.startswith(('min_', 'max_')) and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            raise CSPValidationError(f'{key} must be a non-negative integer.')
        if key.endswith('_required') or key in {'methodology_requires_results', 'results_requires_methodology'}:
            if not isinstance(value, bool):
                raise CSPValidationError(f'{key} must be Boolean.')
    sections = requirements.get('required_sections', [])
    if not isinstance(sections, list) or any(not isinstance(section, str) or section.casefold() not in SECTION_NAMES for section in sections):
        raise CSPValidationError('required_sections must use supported section names.')
    order = requirements.get('required_section_order', [])
    if not isinstance(order, list) or any(
        not isinstance(pair, list) or len(pair) != 2
        or any(not isinstance(section, str) or section.casefold() not in SECTION_NAMES for section in pair)
        for pair in order
    ):
        raise CSPValidationError('required_section_order must be pairs of supported section names.')
