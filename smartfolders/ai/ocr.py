"""Optical character recognition.

Uses Tesseract via ``pytesseract`` when the native binary is present. PDFs are
rasterised page-by-page (PyMuPDF preferred, ``pdf2image`` as fallback). When no
OCR backend is available the engine reports ``available = False`` and
:meth:`extract` returns an empty string, so callers degrade gracefully.

Cross-platform note: on Windows the Tesseract install path is auto-detected; on
macOS/Linux it is expected on ``PATH`` (e.g. ``brew install tesseract``).
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..constants import IMAGE_EXTENSIONS, PDF_EXTENSIONS
from ..utils.logging import get_logger

log = get_logger(__name__)

_WINDOWS_TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)


class OCREngine:
    """Extracts text from images and scanned PDFs."""

    def __init__(self, languages: str = "deu+eng", max_pages: int = 10) -> None:
        self.languages = languages
        self.max_pages = max_pages
        self._pytesseract = None
        self._pil = None
        self.available = self._init_backend()

    def _init_backend(self) -> bool:
        try:
            import pytesseract
            from PIL import Image  # noqa: F401

            self._pytesseract = pytesseract
            from PIL import Image as _Image

            self._pil = _Image
        except Exception:
            log.info("OCR backend unavailable (pytesseract/Pillow not installed)")
            return False

        binary = self._locate_tesseract()
        if binary:
            self._pytesseract.pytesseract.tesseract_cmd = binary
            log.info("OCR backend ready (tesseract=%s, lang=%s)", binary, self.languages)
            return True
        log.info("Tesseract binary not found; OCR disabled")
        return False

    @staticmethod
    def _locate_tesseract() -> str | None:
        found = shutil.which("tesseract")
        if found:
            return found
        if sys.platform.startswith("win"):
            for candidate in _WINDOWS_TESSERACT_CANDIDATES:
                if os.path.exists(candidate):
                    return candidate
        return None

    # ------------------------------------------------------------------ public
    def extract(self, path: str | Path) -> str:
        if not self.available:
            return ""
        p = Path(path)
        ext = p.suffix.lower()
        try:
            if ext in IMAGE_EXTENSIONS:
                return self._ocr_image(p)
            if ext in PDF_EXTENSIONS:
                return self._ocr_pdf(p)
        except Exception:  # pragma: no cover - OCR must never crash the pipeline
            log.warning("OCR failed for %s", p, exc_info=True)
        return ""

    def _ocr_image(self, path: Path) -> str:
        img = self._pil.open(path)
        return self._pytesseract.image_to_string(img, lang=self.languages).strip()

    def _ocr_pdf(self, path: Path) -> str:
        pages = self._rasterise_pdf(path)
        texts = [self._pytesseract.image_to_string(img, lang=self.languages) for img in pages]
        return "\n".join(t.strip() for t in texts if t.strip())

    def _rasterise_pdf(self, path: Path) -> list:
        # Prefer PyMuPDF (no external poppler dependency).
        try:
            import fitz

            images = []
            with fitz.open(path) as doc:
                for i, page in enumerate(doc):
                    if i >= self.max_pages:
                        break
                    pix = page.get_pixmap(dpi=200)
                    images.append(self._pil.frombytes("RGB", (pix.width, pix.height), pix.samples))
            return images
        except Exception:
            pass
        try:
            from pdf2image import convert_from_path

            return convert_from_path(str(path), dpi=200, last_page=self.max_pages)
        except Exception:
            return []
