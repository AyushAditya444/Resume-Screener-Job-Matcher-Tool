import io

import pdfplumber
from docx import Document


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if lower_name.endswith(".docx"):
        return _extract_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {filename}")


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        text = "\n".join(pages).strip()
    except Exception as exc:
        raise ValueError("Could not read PDF file") from exc
    if not text:
        raise ValueError("Could not read PDF file: no extractable text")
    return text


def _extract_docx(file_bytes: bytes) -> str:
    try:
        document = Document(io.BytesIO(file_bytes))
        text = "\n".join(p.text for p in document.paragraphs).strip()
    except Exception as exc:
        raise ValueError("Could not read DOCX file") from exc
    if not text:
        raise ValueError("Could not read DOCX file: no extractable text")
    return text
