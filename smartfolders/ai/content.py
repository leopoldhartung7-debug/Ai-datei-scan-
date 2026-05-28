"""Lightweight text extraction used to feed the classifier and search index.

We deliberately avoid heavy parsers for the common path: plain-text and code
files are read directly, PDFs use PyMuPDF if available, and everything else
returns an empty preview (OCR handles images separately). All functions are
defensive - extraction failures never propagate.
"""

from __future__ import annotations

from pathlib import Path

from ..constants import MAX_TEXT_INDEX_BYTES, PDF_EXTENSIONS, TEXT_EXTENSIONS
from ..utils.logging import get_logger

log = get_logger(__name__)

CODE_LIKE = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".xml",
    ".yaml", ".yml", ".toml", ".c", ".cpp", ".h", ".java", ".cs", ".go",
    ".rs", ".rb", ".php", ".sh", ".sql", ".md",
}


def extract_preview(path: str | Path, max_chars: int = 4000) -> str:
    """Return a best-effort text preview of *path* (may be empty)."""
    p = Path(path)
    ext = p.suffix.lower()
    try:
        if ext in TEXT_EXTENSIONS or ext in CODE_LIKE:
            return _read_text(p, max_chars)
        if ext in PDF_EXTENSIONS:
            return _read_pdf(p, max_chars)
    except Exception:  # pragma: no cover - never fail on a single file
        log.debug("preview extraction failed for %s", p, exc_info=True)
    return ""


def _read_text(path: Path, max_chars: int) -> str:
    if path.stat().st_size > MAX_TEXT_INDEX_BYTES:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read(max_chars)
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text[:max_chars]


def _read_pdf(path: Path, max_chars: int) -> str:
    try:
        import fitz  # PyMuPDF
    except Exception:
        return ""
    text_parts: list[str] = []
    try:
        with fitz.open(path) as doc:
            for page in doc:
                text_parts.append(page.get_text())
                if sum(len(t) for t in text_parts) >= max_chars:
                    break
    except Exception:
        return ""
    return "".join(text_parts)[:max_chars]


def pdf_is_scanned(path: str | Path) -> bool:
    """Heuristic: a PDF with almost no extractable text is likely a scan -> OCR."""
    text = _read_pdf(path, 200)
    return len(text.strip()) < 20
