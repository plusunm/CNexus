"""Extract plain text from uploaded documents for memory capture."""

from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
PDF_EXTENSIONS = {".pdf"}
DOCX_EXTENSIONS = {".docx"}
DOC_EXTENSIONS = {".doc"}
SUPPORTED_EXTENSIONS = TEXT_EXTENSIONS | PDF_EXTENSIONS | DOCX_EXTENSIONS | DOC_EXTENSIONS

_DEFAULT_MAX_CHARS = 4000


class DocumentParseError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _decode_text(data: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_pdf(data: bytes) -> str:
    reader_cls = None
    try:
        from pypdf import PdfReader  # type: ignore

        reader_cls = PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore

            reader_cls = PdfReader
        except ImportError as exc:
            raise DocumentParseError(
                "pdf_support_missing",
                "PDF parsing requires the pypdf package",
            ) from exc

    reader = reader_cls(io.BytesIO(data))
    parts: List[str] = []
    for page in reader.pages:
        chunk = (page.extract_text() or "").strip()
        if chunk:
            parts.append(chunk)
    text = "\n\n".join(parts).strip()
    if not text:
        raise DocumentParseError("pdf_empty", "No extractable text found in PDF")
    return text


def _parse_docx(data: bytes) -> str:
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise DocumentParseError(
            "docx_support_missing",
            "DOCX parsing requires the python-docx package",
        ) from exc

    doc = Document(io.BytesIO(data))
    parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    text = "\n".join(parts).strip()
    if not text:
        raise DocumentParseError("docx_empty", "No extractable text found in DOCX")
    return text


def extract_keywords(text: str, *, limit: int = 8) -> List[str]:
    """Lightweight keyword hints from parsed text (no LLM)."""
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z]{3,}", (text or "").lower())
    if not tokens:
        return []
    counts = Counter(tokens)
    return [word for word, _ in counts.most_common(limit)]


def parse_document_bytes(
    filename: str,
    data: bytes,
    *,
    max_chars: int = _DEFAULT_MAX_CHARS,
) -> Dict[str, Any]:
    name = (filename or "upload").strip() or "upload"
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentParseError(
            "unsupported_format",
            f"Unsupported file type: {ext or '(none)'}",
        )
    if not data:
        raise DocumentParseError("empty_file", "Uploaded file is empty")

    if ext in TEXT_EXTENSIONS:
        text = _decode_text(data).strip()
        fmt = "text"
    elif ext in PDF_EXTENSIONS:
        text = _parse_pdf(data).strip()
        fmt = "pdf"
    elif ext in DOCX_EXTENSIONS:
        text = _parse_docx(data).strip()
        fmt = "docx"
    else:
        raise DocumentParseError(
            "legacy_doc_unsupported",
            "Legacy .doc files are not supported — save as .docx or .pdf",
        )

    if not text:
        raise DocumentParseError("no_text", "Document contains no readable text")

    truncated = len(text) > max_chars
    clipped = text[:max_chars]
    return {
        "filename": name,
        "format": fmt,
        "text": clipped,
        "char_count": len(clipped),
        "truncated": truncated,
        "keywords": extract_keywords(clipped),
    }
