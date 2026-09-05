import pytest
from pathlib import Path

from app.services.text_extraction import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extracts_text_from_docx():
    data = (FIXTURES / "sample_resume.docx").read_bytes()
    text = extract_text(data, "sample_resume.docx")
    assert "Python" in text
    assert "5 years" in text


def test_extracts_text_from_pdf():
    data = (FIXTURES / "sample_resume.pdf").read_bytes()
    text = extract_text(data, "sample_resume.pdf")
    assert "Python" in text


def test_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"whatever", "resume.txt")


def test_rejects_corrupt_pdf():
    with pytest.raises(ValueError, match="Could not read"):
        extract_text(b"not a real pdf", "resume.pdf")
