"""PDF-to-structured-paper extraction for PaperIntel Module 2.

The parser deliberately contains no scoring, recommendation, database, or model logic.
It produces the stable document representation consumed by later modules.
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import pdfplumber


class PDFParsingError(Exception):
    """Raised when a PDF cannot be opened or parsed safely."""


class PasswordProtectedPDFError(PDFParsingError):
    """Raised for encrypted PDFs that need a password."""


class EmptyPDFError(PDFParsingError):
    """Raised for genuinely blank PDFs (not image-only/scanned PDFs)."""


@dataclass
class PageText:
    number: int
    text: str
    lines: list[str]
    image_count: int


@dataclass
class Heading:
    line_index: int
    page: int
    number: str | None
    title: str


REFERENCE_TITLES = {'references', 'bibliography'}
KEYWORD_RE = re.compile(r'^\s*(?:keywords?|key\s*words?|index\s*terms?)\s*(?:[—–:-]\s*|\.\s*)?(.*)$', re.IGNORECASE)
ABSTRACT_RE = re.compile(r'^\s*abstract\s*(?:[—–:-]\s*|\.\s*)?(.*)$', re.IGNORECASE)
NUMBERED_HEADING_RE = re.compile(
    r'^\s*(?P<number>\d+(?:\.\d+)*|[IVXLCDM]+)\s*[.)]?\s+(?P<title>[A-Za-z][A-Za-z0-9 &/,:;()\-]{0,100})\s*$',
    re.IGNORECASE,
)
FIGURE_RE = re.compile(r'^\s*(?:figure|fig\.)\s*(?:no\.\s*)?(?P<number>\d+|[IVXLCDM]+)\s*[:.\-—–]?\s*(?P<caption>.*)$', re.IGNORECASE)
TABLE_RE = re.compile(r'^\s*table\s*(?:no\.\s*)?(?P<number>\d+|[IVXLCDM]+)\s*[:.\-—–]?\s*(?P<caption>.*)$', re.IGNORECASE)
REFERENCE_ITEM_RE = re.compile(r'^\s*(?:\[(?P<bracket>\d+)\]|(?P<plain>\d+)[.)])\s+(?P<text>.+)$')
WORD_RE = re.compile(r"\b[\w][\w'’-]*\b")

UNNUMBERED_SECTION_TITLES = {
    'introduction', 'background', 'related work', 'literature review', 'methodology',
    'methods', 'materials and methods', 'experimental setup', 'experiments', 'results',
    'discussion', 'results and discussion', 'conclusion', 'conclusions', 'future work',
    'limitations', 'acknowledgments', 'acknowledgements', 'appendix', 'appendices',
    'references', 'bibliography',
}
AUTHOR_STOP_WORDS = {
    'abstract', 'department', 'university', 'institute', 'school', 'faculty', 'college',
    'laboratory', 'lab', 'email', 'corresponding', 'keywords', 'index terms', 'received',
}


def _normalise_space(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def _word_count(value: str) -> int:
    return len(WORD_RE.findall(value))


def _roman_to_int(value: str) -> int | None:
    if value.isdigit():
        return int(value)
    numerals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    value = value.upper()
    if not value or any(character not in numerals for character in value):
        return None
    total = 0
    previous = 0
    for character in reversed(value):
        current = numerals[character]
        total += -current if current < previous else current
        previous = max(previous, current)
    return total


class PDFParser:
    """Extract text and document structure from a PDF using deterministic heuristics."""

    def parse(self, pdf_source: str | Path | bytes) -> dict[str, Any]:
        """Parse a filesystem PDF or in-memory bytes (useful for tests and callers)."""
        try:
            if isinstance(pdf_source, bytes):
                document = fitz.open(stream=pdf_source, filetype='pdf')
            else:
                document = fitz.open(str(pdf_source))
        except (fitz.FileDataError, RuntimeError, OSError) as exc:
            raise PDFParsingError('Unable to open PDF.') from exc

        try:
            if document.needs_pass:
                raise PasswordProtectedPDFError('PDF requires a password.')
            if document.page_count == 0:
                raise EmptyPDFError('PDF has no pages.')

            pages, first_page_blocks = self._extract_pages(document)
            full_text = '\n'.join(page.text for page in pages)
            total_words = _word_count(full_text)
            image_count = sum(page.image_count for page in pages)
            if total_words == 0 and image_count == 0:
                raise EmptyPDFError('PDF has no text or image content.')

            flattened_lines = [
                (page.number, line)
                for page in pages
                for line in page.lines
                if line.strip()
            ]
            title, title_confidence, title_bottom = self._extract_title(first_page_blocks)
            authors, authors_confidence = self._extract_authors(first_page_blocks, title_bottom)
            abstract = self._extract_abstract(flattened_lines)
            keywords = self._extract_keywords(flattened_lines)
            headings = self._find_headings(flattened_lines)
            references_start = next(
                (heading.line_index for heading in headings if heading.title.lower() in REFERENCE_TITLES),
                None,
            )
            sections = self._build_sections(flattened_lines, headings, references_start)
            references = self._extract_references(flattened_lines, references_start)
            figures = self._extract_captioned_items(flattened_lines, FIGURE_RE)
            tables = self._extract_captioned_items(flattened_lines, TABLE_RE)
            if not tables:
                tables = self._detect_uncaptioned_native_tables(pdf_source)

            word_counts = [
                {'page': page.number, 'word_count': _word_count(page.text)}
                for page in pages
            ]
            empty_pages = [entry['page'] for entry in word_counts if entry['word_count'] == 0]
            low_text_pages = [
                entry['page'] for entry in word_counts
                if 0 < entry['word_count'] < 20
            ]
            warnings: list[str] = []
            pages_without_text = len(empty_pages)
            if total_words == 0 and image_count > 0:
                warnings.append('This PDF may be scanned or image-based and may require OCR.')
            elif pages_without_text / len(pages) >= 0.6 and image_count > 0:
                warnings.append('Most pages have little or no extractable text and may require OCR.')
            if low_text_pages and len(low_text_pages) < len(pages):
                warnings.append(f'{len(low_text_pages)} page(s) contain very little extractable text.')

            return {
                'document': {'filename': None, 'file_size': None, 'page_count': len(pages)},
                'metadata': {
                    'title': title,
                    'title_confidence': title_confidence,
                    'authors': authors,
                    'authors_confidence': authors_confidence,
                    'abstract': abstract,
                    'abstract_word_count': _word_count(abstract or ''),
                    'keywords': keywords,
                },
                'sections': sections,
                'references': references,
                'figures': figures,
                'tables': tables,
                'statistics': {
                    'word_count': total_words,
                    'character_count': len(full_text),
                    'words_per_page': word_counts,
                    'empty_pages': empty_pages,
                    'low_text_pages': low_text_pages,
                    'section_count': len(sections),
                    'reference_count': len(references),
                    'figure_count': len(figures),
                    'table_count': len(tables),
                },
                'warnings': warnings,
            }
        except PasswordProtectedPDFError:
            raise
        except EmptyPDFError:
            raise
        except (fitz.FileDataError, RuntimeError, ValueError, OSError) as exc:
            raise PDFParsingError('Unable to extract document content.') from exc
        finally:
            document.close()

    @staticmethod
    def _extract_pages(document: fitz.Document) -> tuple[list[PageText], list[dict[str, Any]]]:
        pages: list[PageText] = []
        first_page_blocks: list[dict[str, Any]] = []
        for index, page in enumerate(document):
            text = page.get_text('text', sort=True).strip()
            lines = [_normalise_space(line) for line in text.splitlines() if _normalise_space(line)]
            pages.append(PageText(
                number=index + 1,
                text=text,
                lines=lines,
                image_count=len(page.get_images(full=True)),
            ))
            if index == 0:
                first_page_blocks = PDFParser._text_blocks(page)
        return pages, first_page_blocks

    @staticmethod
    def _text_blocks(page: fitz.Page) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        page_data = page.get_text('dict', flags=fitz.TEXTFLAGS_TEXT)
        for block in page_data.get('blocks', []):
            if block.get('type') != 0:
                continue
            spans = [span for line in block.get('lines', []) for span in line.get('spans', [])]
            text = _normalise_space(' '.join(span.get('text', '') for span in spans))
            if not text:
                continue
            sizes = [float(span.get('size', 0)) for span in spans if span.get('size')]
            blocks.append({
                'text': text,
                'x0': float(block.get('bbox', (0, 0, 0, 0))[0]),
                'y0': float(block.get('bbox', (0, 0, 0, 0))[1]),
                'x1': float(block.get('bbox', (0, 0, 0, 0))[2]),
                'y1': float(block.get('bbox', (0, 0, 0, 0))[3]),
                'font_size': max(sizes, default=0),
                'mean_font_size': statistics.mean(sizes) if sizes else 0,
                'page_width': float(page.rect.width),
                'page_height': float(page.rect.height),
            })
        return blocks

    @staticmethod
    def _extract_title(blocks: list[dict[str, Any]]) -> tuple[str | None, str, float | None]:
        if not blocks:
            return None, 'low', None
        body_sizes = [block['mean_font_size'] for block in blocks if block['mean_font_size'] > 0]
        body_size = statistics.median(body_sizes) if body_sizes else 0
        candidates: list[tuple[float, dict[str, Any]]] = []
        excluded = ('abstract', 'keywords', 'index terms', 'doi', 'copyright', '@', 'http://', 'https://')
        for block in blocks:
            text = block['text']
            lowered = text.lower()
            if (
                block['y0'] > block['page_height'] * 0.48
                or not 10 <= len(text) <= 220
                or any(marker in lowered for marker in excluded)
                or _word_count(text) < 3
            ):
                continue
            centre = (block['x0'] + block['x1']) / 2
            centredness = max(0, 1 - abs(centre - block['page_width'] / 2) / (block['page_width'] / 2))
            size_advantage = max(0, block['font_size'] - body_size)
            topness = max(0, 1 - block['y0'] / (block['page_height'] * 0.48))
            score = size_advantage * 2.5 + centredness + topness
            if block['font_size'] >= body_size + 1.5:
                score += 2
            candidates.append((score, block))

        if not candidates:
            return None, 'low', None
        score, candidate = max(candidates, key=lambda item: item[0])
        if score < 3.5:
            return None, 'low', None
        confidence = 'high' if candidate['font_size'] >= body_size + 2 else 'medium'
        return candidate['text'], confidence, candidate['y1']

    @staticmethod
    def _extract_authors(blocks: list[dict[str, Any]], title_bottom: float | None) -> tuple[list[str], str]:
        if title_bottom is None:
            return [], 'low'
        candidates: list[str] = []
        for block in blocks:
            text = block['text']
            lowered = text.lower()
            if (
                block['y0'] < title_bottom - 2
                or block['y0'] > block['page_height'] * 0.52
                or '@' in text
                or any(word in lowered for word in AUTHOR_STOP_WORDS)
            ):
                continue
            for part in re.split(r'\s*(?:,|;|\band\b|\n)\s*', text, flags=re.IGNORECASE):
                cleaned = re.sub(r'[*†‡\d]+$', '', part).strip(' ,;')
                words = cleaned.split()
                if not 2 <= len(words) <= 4:
                    continue
                if all(re.fullmatch(r"[A-Z][A-Za-z'’-]*\.?", word) for word in words):
                    candidates.append(cleaned)
        unique_authors = list(dict.fromkeys(candidates))
        if not unique_authors:
            return [], 'low'
        return unique_authors, 'medium' if len(unique_authors) <= 12 else 'low'

    @staticmethod
    def _is_heading(line: str) -> tuple[str | None, str] | None:
        cleaned = _normalise_space(line).rstrip(':')
        lowered = cleaned.lower()
        if lowered in UNNUMBERED_SECTION_TITLES:
            return None, cleaned
        match = NUMBERED_HEADING_RE.match(cleaned)
        if not match:
            return None
        title = _normalise_space(match.group('title')).rstrip(':')
        title_words = _word_count(title)
        if not 1 <= title_words <= 12 or title.endswith('.') or '@' in title:
            return None
        if title.lower().startswith(('fig', 'table')):
            return None
        return match.group('number'), title

    def _find_headings(self, lines: list[tuple[int, str]]) -> list[Heading]:
        headings: list[Heading] = []
        for index, (page, line) in enumerate(lines):
            detected = self._is_heading(line)
            if detected:
                number, title = detected
                headings.append(Heading(index, page, number, title))
        return headings

    def _extract_abstract(self, lines: list[tuple[int, str]]) -> str | None:
        for index, (_, line) in enumerate(lines):
            match = ABSTRACT_RE.match(line)
            if not match:
                continue
            collected = [match.group(1).strip()] if match.group(1).strip() else []
            for _, next_line in lines[index + 1:]:
                if KEYWORD_RE.match(next_line) or self._is_heading(next_line):
                    break
                collected.append(next_line)
            abstract = _normalise_space(' '.join(collected))
            return abstract or None
        return None

    def _extract_keywords(self, lines: list[tuple[int, str]]) -> list[str]:
        for index, (_, line) in enumerate(lines):
            match = KEYWORD_RE.match(line)
            if not match:
                continue
            collected = [match.group(1).strip()] if match.group(1).strip() else []
            for _, next_line in lines[index + 1:index + 4]:
                if self._is_heading(next_line) or ABSTRACT_RE.match(next_line):
                    break
                if not collected and next_line:
                    collected.append(next_line)
                    break
            value = _normalise_space(' '.join(collected)).strip(' .;:—–-')
            if not value:
                return []
            return [
                keyword.strip(' .;:—–-')
                for keyword in re.split(r'[,;•]', value)
                if keyword.strip(' .;:—–-')
            ]
        return []

    @staticmethod
    def _build_sections(
        lines: list[tuple[int, str]], headings: list[Heading], references_start: int | None,
    ) -> list[dict[str, Any]]:
        section_headings = [
            heading for heading in headings
            if heading.title.lower() not in REFERENCE_TITLES
            and (references_start is None or heading.line_index < references_start)
        ]
        sections: list[dict[str, Any]] = []
        for position, heading in enumerate(section_headings):
            next_index = (
                section_headings[position + 1].line_index
                if position + 1 < len(section_headings)
                else (references_start if references_start is not None else len(lines))
            )
            text_lines = [text for _, text in lines[heading.line_index + 1:next_index]]
            section_text = _normalise_space(' '.join(text_lines))
            pages = [page for page, text in lines[heading.line_index + 1:next_index] if text.strip()]
            sections.append({
                'number': heading.number,
                'title': heading.title,
                'text': section_text,
                'page_start': heading.page,
                'page_end': max(pages, default=heading.page),
            })
        return sections

    @staticmethod
    def _extract_references(lines: list[tuple[int, str]], start_index: int | None) -> list[dict[str, Any]]:
        if start_index is None:
            return []
        references: list[dict[str, Any]] = []
        current_number: int | None = None
        current_parts: list[str] = []

        def save_current() -> None:
            if current_number is not None and current_parts:
                references.append({
                    'number': current_number,
                    'text': _normalise_space(' '.join(current_parts)),
                })

        for _, line in lines[start_index + 1:]:
            match = REFERENCE_ITEM_RE.match(line)
            if match:
                save_current()
                current_number = int(match.group('bracket') or match.group('plain'))
                current_parts = [match.group('text')]
            elif current_number is not None:
                current_parts.append(line)
        save_current()
        return references

    @staticmethod
    def _extract_captioned_items(lines: list[tuple[int, str]], pattern: re.Pattern[str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[tuple[int | None, int, str]] = set()
        for page, line in lines:
            match = pattern.match(line)
            if not match:
                continue
            number = _roman_to_int(match.group('number'))
            caption = _normalise_space(match.group('caption')).strip(' :—–-') or None
            key = (number, page, caption or '')
            if key in seen:
                continue
            seen.add(key)
            items.append({'number': number, 'caption': caption, 'page': page, 'detected_from': 'caption'})
        return items

    @staticmethod
    def _detect_uncaptioned_native_tables(pdf_source: str | Path | bytes) -> list[dict[str, Any]]:
        """Use pdfplumber only as a fallback for native tables without detectable captions."""
        detected: list[dict[str, Any]] = []
        try:
            source = BytesIO(pdf_source) if isinstance(pdf_source, bytes) else str(pdf_source)
            with pdfplumber.open(source) as pdf:
                for page_number, page in enumerate(pdf.pages, start=1):
                    if page.find_tables():
                        detected.append({
                            'number': None,
                            'caption': None,
                            'page': page_number,
                            'detected_from': 'native_table',
                        })
        except Exception:
            # Secondary detection must not prevent a successful primary extraction.
            return []
        return detected
