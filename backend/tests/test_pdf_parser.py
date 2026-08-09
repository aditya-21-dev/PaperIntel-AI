import fitz
import pytest

from app.services.pdf_parser import EmptyPDFError, PDFParser


def make_pdf_bytes(pages: list[list[tuple[str, float]]]) -> bytes:
    document = fitz.open()
    for page_lines in pages:
        page = document.new_page()
        y = 72
        for text, size in page_lines:
            page.insert_text((72, y), text, fontsize=size)
            y += size + 12
    result = document.tobytes()
    document.close()
    return result


@pytest.fixture
def parser() -> PDFParser:
    return PDFParser()


def test_extracts_structured_research_paper(parser: PDFParser) -> None:
    pdf_bytes = make_pdf_bytes([[
        ('A Practical Study of PDF Extraction', 18),
        ('Alice Smith, Bob Jones', 11),
        ('Abstract', 12),
        ('This paper presents a deterministic extraction workflow for research papers.', 10),
        ('Keywords: PDF parsing, document analysis, research', 10),
        ('1 Introduction', 12),
        ('Introduction text describes the research context.', 10),
        ('Figure 1: Processing pipeline', 10),
        ('Table 1: Extracted metadata fields', 10),
    ], [
        ('2 Methodology', 12),
        ('Methods are implemented with deterministic heuristics.', 10),
        ('References', 12),
        ('[1] A. Author. PDF extraction methods. 2024.', 10),
        ('[2] B. Author. Structured documents. 2023.', 10),
    ]])

    result = parser.parse(pdf_bytes)

    assert result['document']['page_count'] == 2
    assert result['metadata']['title'] == 'A Practical Study of PDF Extraction'
    assert result['metadata']['authors'] == ['Alice Smith', 'Bob Jones']
    assert result['metadata']['abstract'].startswith('This paper presents')
    assert result['metadata']['keywords'] == ['PDF parsing', 'document analysis', 'research']
    assert [section['title'] for section in result['sections']] == ['Introduction', 'Methodology']
    assert len(result['references']) == 2
    assert result['figures'][0]['caption'] == 'Processing pipeline'
    assert result['tables'][0]['caption'] == 'Extracted metadata fields'
    assert result['statistics']['word_count'] > 20


def test_pdf_without_optional_sections_returns_empty_values(parser: PDFParser) -> None:
    pdf_bytes = make_pdf_bytes([[('An Untitled Note', 18), ('A short body without marked sections.', 10)]])

    result = parser.parse(pdf_bytes)

    assert result['metadata']['abstract'] is None
    assert result['metadata']['keywords'] == []
    assert result['references'] == []
    assert result['figures'] == []
    assert result['tables'] == []


def test_empty_pdf_is_rejected(parser: PDFParser) -> None:
    document = fitz.open()
    document.new_page()
    pdf_bytes = document.tobytes()
    document.close()

    with pytest.raises(EmptyPDFError):
        parser.parse(pdf_bytes)
