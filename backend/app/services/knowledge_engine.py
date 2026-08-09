"""Deterministic knowledge engineering for a Module 2 structured paper.

This module creates a traceable knowledge base. It intentionally does not
perform theorem proving, forward/backward chaining, evaluation, scoring, or
natural-language reasoning.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


SOURCE_MODULE = 'pdf_parser'
SCHEMA_VERSION = '1.0'

ENTITY_TYPES = frozenset({
    'Paper', 'Author', 'Abstract', 'Keyword', 'Section', 'Subsection',
    'Reference', 'Figure', 'Table', 'Citation',
})

RELATIONSHIP_PREDICATES = {
    'has_author': 'Links a paper to an extracted author.',
    'has_abstract': 'Links a paper to its extracted abstract.',
    'has_keyword': 'Links a paper to an extracted keyword.',
    'has_section': 'Links a paper to a top-level section.',
    'has_subsection': 'Links a parent section to a subsection.',
    'has_reference': 'Links a paper to an extracted reference.',
    'has_figure': 'Links a paper to an extracted figure.',
    'has_table': 'Links a paper to an extracted table.',
    'contains_citation': 'Links a section to a referenced work cited in its extracted text.',
    'citation_refers_to': 'Links a citation occurrence to its resolved reference.',
    'contains_figure': 'Links a section to a figure that appears in it.',
    'contains_table': 'Links a section to a table that appears in it.',
    'appears_in': 'Links a figure or table to the section containing it.',
    'precedes': 'Marks the extracted order from one section to the next.',
    'follows': 'Marks the inverse extracted order between adjacent sections.',
}

PROPOSITIONAL_PREDICATES = {
    'PaperHasAbstract': 'The structured paper contains metadata.abstract.',
    'PaperHasKeywords': 'The structured paper contains one or more keywords.',
    'PaperHasIntroduction': 'The structured paper contains an introduction section.',
    'PaperHasMethodology': 'The structured paper contains a methods or methodology section.',
    'PaperHasResults': 'The structured paper contains a results section.',
    'PaperHasConclusion': 'The structured paper contains a conclusion section.',
    'PaperHasReferences': 'The structured paper contains one or more references.',
    'PaperHasFigures': 'The structured paper contains one or more figures.',
    'PaperHasTables': 'The structured paper contains one or more tables.',
}

CITATION_RE = re.compile(r'\[([0-9][0-9,\s\-–—]*)\]')
IDENTIFIER_RE = re.compile(r'[^a-z0-9]+')


class KnowledgeBaseInputError(ValueError):
    """Raised when the supplied data is not Module 2 structured output."""


def normalize_identifier(value: Any, fallback: str) -> str:
    """Return a deterministic, URL-safe identifier fragment without trusting input IDs."""
    normalised = IDENTIFIER_RE.sub('_', str(value or '').lower()).strip('_')
    return normalised or fallback


def _evidence(source_field: str, page: int | None = None, section: str | None = None, **details: Any) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        'source_module': SOURCE_MODULE,
        'source_field': source_field,
    }
    if page is not None:
        evidence['page'] = page
    if section:
        evidence['section'] = section
    evidence.update({key: value for key, value in details.items() if value is not None})
    return evidence


def _logical_form(predicate: str, subject: str, object_id: str) -> str:
    return f"{''.join(part.title() for part in predicate.split('_'))}({subject}, {object_id})"


def _list(document: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = document.get(key, [])
    return value if isinstance(value, list) else []


class KnowledgeEngine:
    """Transforms one Module 2 structured document into a validated knowledge base."""

    def build(self, structured_document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if not isinstance(structured_document, dict):
            raise KnowledgeBaseInputError('Structured paper data must be a JSON object.')
        document_info = structured_document.get('document')
        metadata = structured_document.get('metadata')
        if not isinstance(document_info, dict) or not isinstance(metadata, dict):
            raise KnowledgeBaseInputError('Module 2 document and metadata fields are required.')

        entities: dict[str, list[dict[str, Any]]] = {
            'authors': [], 'abstracts': [], 'keywords': [], 'sections': [], 'subsections': [],
            'references': [], 'figures': [], 'tables': [], 'citations': [],
        }
        evidence: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []
        facts: list[dict[str, Any]] = []
        counters: dict[str, int] = {}

        def next_id(kind: str) -> str:
            counters[kind] = counters.get(kind, 0) + 1
            return f'{kind}_{counters[kind]:03d}'

        def record_evidence(item: dict[str, Any]) -> dict[str, Any]:
            item_with_id = {'id': next_id('evidence'), **item}
            evidence.append(item_with_id)
            return item_with_id

        def add_entity(group: str, entity_type: str, name: str | None, attributes: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
            entity = {
                'id': next_id(entity_type.lower()),
                'type': entity_type,
                'name': name,
                'attributes': attributes,
                'evidence': record_evidence(source),
            }
            entities[group].append(entity)
            return entity

        def add_relationship(subject: str, predicate: str, object_id: str, source: dict[str, Any]) -> None:
            if predicate not in RELATIONSHIP_PREDICATES:
                raise ValueError(f'Unsupported relationship predicate: {predicate}')
            relation_evidence = record_evidence(source)
            relationships.append({
                'subject': subject,
                'predicate': predicate,
                'object': object_id,
                'logical_form': _logical_form(predicate, subject, object_id),
                'evidence': relation_evidence,
            })

        paper = {
            'id': 'paper_001',
            'type': 'Paper',
            'name': metadata.get('title') or document_info.get('filename'),
            'attributes': {
                'filename': document_info.get('filename'),
                'file_size': document_info.get('file_size'),
                'page_count': document_info.get('page_count'),
                'title_confidence': metadata.get('title_confidence'),
            },
            'evidence': record_evidence(_evidence('document,metadata', title_detected=bool(metadata.get('title')))),
        }

        for author in metadata.get('authors', []) if isinstance(metadata.get('authors'), list) else []:
            if not isinstance(author, str) or not author.strip():
                continue
            author_entity = add_entity(
                'authors', 'Author', author.strip(), {},
                _evidence('metadata.authors', confidence=metadata.get('authors_confidence')),
            )
            add_relationship(paper['id'], 'has_author', author_entity['id'], _evidence('metadata.authors'))

        abstract = metadata.get('abstract')
        if isinstance(abstract, str) and abstract.strip():
            abstract_entity = add_entity(
                'abstracts', 'Abstract', 'Abstract',
                {'text': abstract, 'word_count': metadata.get('abstract_word_count')},
                _evidence('metadata.abstract', section='Abstract'),
            )
            add_relationship(paper['id'], 'has_abstract', abstract_entity['id'], _evidence('metadata.abstract', section='Abstract'))

        seen_keywords: set[str] = set()
        for keyword in metadata.get('keywords', []) if isinstance(metadata.get('keywords'), list) else []:
            if not isinstance(keyword, str) or not keyword.strip():
                continue
            keyword_name = keyword.strip()
            normalised_keyword = normalize_identifier(keyword_name, 'keyword')
            if normalised_keyword in seen_keywords:
                continue
            seen_keywords.add(normalised_keyword)
            keyword_entity = add_entity(
                'keywords', 'Keyword', keyword_name, {'normalised': normalised_keyword},
                _evidence('metadata.keywords'),
            )
            add_relationship(paper['id'], 'has_keyword', keyword_entity['id'], _evidence('metadata.keywords'))

        section_records: list[tuple[dict[str, Any], dict[str, Any]]] = []
        section_by_number: dict[str, dict[str, Any]] = {}
        for section in _list(structured_document, 'sections'):
            if not isinstance(section, dict):
                continue
            title = section.get('title') if isinstance(section.get('title'), str) else None
            number = str(section.get('number')).strip() if section.get('number') is not None else None
            is_subsection = bool(number and '.' in number)
            group, entity_type = ('subsections', 'Subsection') if is_subsection else ('sections', 'Section')
            entity = add_entity(
                group, entity_type, title,
                {
                    'section_number': number,
                    'page_start': section.get('page_start'),
                    'page_end': section.get('page_end'),
                    'text': section.get('text') if isinstance(section.get('text'), str) else '',
                },
                _evidence('sections', page=section.get('page_start'), section=title),
            )
            section_records.append((entity, section))
            if number:
                section_by_number[number] = entity
            if is_subsection:
                parent = section_by_number.get(number.rsplit('.', maxsplit=1)[0])
                if parent:
                    add_relationship(parent['id'], 'has_subsection', entity['id'], _evidence('sections', page=section.get('page_start'), section=title))
                else:
                    add_relationship(paper['id'], 'has_section', entity['id'], _evidence('sections', page=section.get('page_start'), section=title))
            else:
                add_relationship(paper['id'], 'has_section', entity['id'], _evidence('sections', page=section.get('page_start'), section=title))

        ordered_sections = [entity for entity, _ in section_records]
        for previous, following in zip(ordered_sections, ordered_sections[1:]):
            add_relationship(previous['id'], 'precedes', following['id'], _evidence('sections', section=previous['name']))
            add_relationship(following['id'], 'follows', previous['id'], _evidence('sections', section=following['name']))

        references_by_number: dict[int, dict[str, Any]] = {}
        for reference in _list(structured_document, 'references'):
            if not isinstance(reference, dict):
                continue
            number = reference.get('number')
            if not isinstance(number, int):
                continue
            reference_entity = add_entity(
                'references', 'Reference', f'Reference {number}',
                {'reference_number': number, 'text': reference.get('text')},
                _evidence('references', section='References', reference_number=number),
            )
            references_by_number[number] = reference_entity
            add_relationship(paper['id'], 'has_reference', reference_entity['id'], _evidence('references', section='References', reference_number=number))

        figure_entities = self._add_visual_entities('figures', 'Figure', _list(structured_document, 'figures'), add_entity)
        for figure, source in figure_entities:
            add_relationship(paper['id'], 'has_figure', figure['id'], _evidence('figures', page=source.get('page'), figure_number=source.get('number')))
            containing_section = self._section_for_item(section_records, source)
            if containing_section:
                add_relationship(figure['id'], 'appears_in', containing_section['id'], _evidence('figures', page=source.get('page'), section=containing_section['name']))
                add_relationship(containing_section['id'], 'contains_figure', figure['id'], _evidence('figures', page=source.get('page'), section=containing_section['name']))

        table_entities = self._add_visual_entities('tables', 'Table', _list(structured_document, 'tables'), add_entity)
        for table, source in table_entities:
            add_relationship(paper['id'], 'has_table', table['id'], _evidence('tables', page=source.get('page'), table_number=source.get('number')))
            containing_section = self._section_for_item(section_records, source)
            if containing_section:
                add_relationship(table['id'], 'appears_in', containing_section['id'], _evidence('tables', page=source.get('page'), section=containing_section['name']))
                add_relationship(containing_section['id'], 'contains_table', table['id'], _evidence('tables', page=source.get('page'), section=containing_section['name']))

        for section_entity, section in section_records:
            section_text = section.get('text') if isinstance(section.get('text'), str) else ''
            for citation_text, cited_numbers in self._find_citations(section_text):
                citation_entity = add_entity(
                    'citations', 'Citation', citation_text,
                    {'reference_numbers': cited_numbers, 'section_id': section_entity['id']},
                    _evidence('sections.text', page=section.get('page_start'), section=section_entity['name'], citation=citation_text),
                )
                for reference_number in cited_numbers:
                    reference_entity = references_by_number.get(reference_number)
                    if not reference_entity:
                        continue
                    citation_evidence = _evidence('sections.text', page=section.get('page_start'), section=section_entity['name'], citation=citation_text)
                    add_relationship(section_entity['id'], 'contains_citation', reference_entity['id'], citation_evidence)
                    add_relationship(citation_entity['id'], 'citation_refers_to', reference_entity['id'], citation_evidence)

        section_titles = {str(entity['name']).casefold() for entity in ordered_sections if entity['name']}
        fact_inputs = {
            'PaperHasAbstract': (bool(abstract_entity if isinstance(abstract, str) and abstract.strip() else None), 'metadata.abstract'),
            'PaperHasKeywords': (bool(entities['keywords']), 'metadata.keywords'),
            'PaperHasIntroduction': (any('introduction' == title for title in section_titles), 'sections'),
            'PaperHasMethodology': (any(title in {'methodology', 'methods', 'materials and methods'} for title in section_titles), 'sections'),
            'PaperHasResults': (any(title == 'results' or title == 'results and discussion' for title in section_titles), 'sections'),
            'PaperHasConclusion': (any(title in {'conclusion', 'conclusions'} for title in section_titles), 'sections'),
            'PaperHasReferences': (bool(entities['references']), 'references'),
            'PaperHasFigures': (bool(entities['figures']), 'figures'),
            'PaperHasTables': (bool(entities['tables']), 'tables'),
        }
        for predicate, (value, source_field) in fact_inputs.items():
            fact_evidence = record_evidence(_evidence(source_field, present=value))
            facts.append({
                'predicate': predicate,
                'arguments': [paper['id']],
                'value': value,
                'evidence': fact_evidence,
            })

        knowledge_base = {
            'paper': paper,
            'entities': entities,
            'propositional_facts': facts,
            'relationships': relationships,
            'evidence': evidence,
            'metadata': {
                'schema_version': SCHEMA_VERSION,
                'generated_by': 'PaperIntel Knowledge Engine',
                'source_module': SOURCE_MODULE,
                'relationship_predicates': RELATIONSHIP_PREDICATES,
                'propositional_predicates': PROPOSITIONAL_PREDICATES,
            },
        }
        return knowledge_base, validate_knowledge_base(knowledge_base)

    @staticmethod
    def _add_visual_entities(
        group: str,
        entity_type: str,
        source_items: list[dict[str, Any]],
        add_entity: Any,
    ) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        created: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for item in source_items:
            if not isinstance(item, dict):
                continue
            number = item.get('number')
            name = f'{entity_type} {number}' if number is not None else f'Unlabelled {entity_type.lower()}'
            entity = add_entity(
                group, entity_type, name,
                {'number': number, 'caption': item.get('caption'), 'page': item.get('page'), 'detected_from': item.get('detected_from')},
                _evidence(group, page=item.get('page'), caption=item.get('caption'), item_number=number),
            )
            created.append((entity, item))
        return created

    @staticmethod
    def _section_for_item(section_records: list[tuple[dict[str, Any], dict[str, Any]]], item: dict[str, Any]) -> dict[str, Any] | None:
        page = item.get('page')
        caption = item.get('caption') if isinstance(item.get('caption'), str) else ''
        candidates = [
            entity for entity, section in section_records
            if isinstance(page, int)
            and isinstance(section.get('page_start'), int)
            and isinstance(section.get('page_end'), int)
            and section['page_start'] <= page <= section['page_end']
        ]
        if not candidates:
            return None
        if caption:
            caption_candidates = [
                entity for entity, section in section_records
                if entity in candidates and caption.casefold() in str(section.get('text', '')).casefold()
            ]
            if caption_candidates:
                return caption_candidates[-1]
        return candidates[-1]

    @staticmethod
    def _find_citations(text: str) -> list[tuple[str, list[int]]]:
        citations: list[tuple[str, list[int]]] = []
        for match in CITATION_RE.finditer(text):
            numbers: set[int] = set()
            for part in match.group(1).replace('–', '-').replace('—', '-').split(','):
                candidate = part.strip()
                if '-' in candidate:
                    start_end = [value.strip() for value in candidate.split('-', maxsplit=1)]
                    if len(start_end) == 2 and all(value.isdigit() for value in start_end):
                        start, end = (int(value) for value in start_end)
                        if 0 < end - start <= 50:
                            numbers.update(range(start, end + 1))
                elif candidate.isdigit():
                    numbers.add(int(candidate))
            if numbers:
                citations.append((match.group(0), sorted(numbers)))
        return citations


def validate_knowledge_base(knowledge_base: dict[str, Any]) -> dict[str, Any]:
    """Validate entity identity, controlled predicates, arguments, and graph references."""
    errors: list[dict[str, str]] = []
    if not isinstance(knowledge_base, dict):
        return {'valid': False, 'errors': [{'code': 'invalid_knowledge_base', 'message': 'Knowledge base must be an object.'}]}

    paper = knowledge_base.get('paper')
    if not isinstance(paper, dict) or not paper.get('id') or paper.get('type') != 'Paper':
        errors.append({'code': 'invalid_paper', 'message': 'A single Paper entity with an ID is required.'})

    entity_ids: set[str] = set()
    if isinstance(paper, dict) and paper.get('id'):
        entity_ids.add(paper['id'])
    entities = knowledge_base.get('entities')
    if not isinstance(entities, dict):
        errors.append({'code': 'invalid_entities', 'message': 'Entities must be grouped in an object.'})
        entities = {}
    for group, items in entities.items():
        if not isinstance(items, list):
            errors.append({'code': 'invalid_entity_group', 'message': f'Entity group {group} must be a list.'})
            continue
        for entity in items:
            entity_id = entity.get('id') if isinstance(entity, dict) else None
            entity_type = entity.get('type') if isinstance(entity, dict) else None
            if not entity_id or entity_type not in ENTITY_TYPES:
                errors.append({'code': 'invalid_entity', 'message': f'Entity in {group} has an invalid ID or type.'})
                continue
            if entity_id in entity_ids:
                errors.append({'code': 'duplicate_entity_id', 'message': f'Entity ID {entity_id} is not unique.'})
                continue
            entity_ids.add(entity_id)

    for relationship in knowledge_base.get('relationships', []):
        if not isinstance(relationship, dict):
            errors.append({'code': 'invalid_relationship', 'message': 'Relationship must be an object.'})
            continue
        predicate = relationship.get('predicate')
        if predicate not in RELATIONSHIP_PREDICATES:
            errors.append({'code': 'undefined_relationship_predicate', 'message': f'Predicate {predicate!r} is not allowed.'})
        for role in ('subject', 'object'):
            if relationship.get(role) not in entity_ids:
                errors.append({'code': 'missing_relationship_entity', 'message': f'Relationship {role} does not reference an entity.'})
        if not isinstance(relationship.get('evidence'), dict):
            errors.append({'code': 'missing_relationship_evidence', 'message': 'Relationship evidence is required.'})

    for fact in knowledge_base.get('propositional_facts', []):
        if not isinstance(fact, dict):
            errors.append({'code': 'invalid_fact', 'message': 'Fact must be an object.'})
            continue
        predicate = fact.get('predicate')
        if predicate not in PROPOSITIONAL_PREDICATES:
            errors.append({'code': 'undefined_fact_predicate', 'message': f'Predicate {predicate!r} is not allowed.'})
        arguments = fact.get('arguments')
        if not isinstance(arguments, list) or not arguments or any(argument not in entity_ids for argument in arguments):
            errors.append({'code': 'invalid_fact_arguments', 'message': f'Fact {predicate!r} has invalid arguments.'})
        if not isinstance(fact.get('value'), bool):
            errors.append({'code': 'invalid_fact_value', 'message': f'Fact {predicate!r} must have a Boolean value.'})
        if not isinstance(fact.get('evidence'), dict):
            errors.append({'code': 'missing_fact_evidence', 'message': f'Fact {predicate!r} requires evidence.'})

    return {'valid': not errors, 'errors': errors}


class KnowledgeAgent:
    """A minimal deterministic knowledge-based agent with perception, update, and query."""

    def __init__(self, engine: KnowledgeEngine | None = None) -> None:
        self._engine = engine or KnowledgeEngine()
        self._knowledge_base: dict[str, Any] | None = None

    def perceive(self, structured_document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        knowledge_base, validation = self._engine.build(structured_document)
        if validation['valid']:
            self._knowledge_base = deepcopy(knowledge_base)
        return knowledge_base, validation

    def query_fact(
        self, predicate: str, arguments: list[str], knowledge_base: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        base = knowledge_base if knowledge_base is not None else self._knowledge_base
        if base is None:
            raise LookupError('No knowledge base has been perceived yet.')
        for fact in base.get('propositional_facts', []):
            if fact.get('predicate') == predicate and fact.get('arguments') == arguments:
                return {'found': True, 'fact': fact}
        return {'found': False, 'fact': None}

    def clear(self) -> None:
        """Clear only the in-memory knowledge base, useful for tests and server reset."""
        self._knowledge_base = None
