"""Smart, content-aware file renaming.

Generates clean, human-readable names from a file's category, extracted entities
(vendor, dates, amounts, project, error type) and OCR/text content. Examples:

    IMG_4832.png        -> Rechnung_Amazon_2026.png
    Screenshot_949.png  -> Python_OpenCV_Error.png
    document.pdf        -> Mietvertrag_Wohnung.pdf

The renamer is fully offline and rule/regex driven. It always returns a
*suggestion*; whether to apply it is controlled by the ``auto_rename`` setting
and/or the user confirming in the UI. It never produces an empty or unsafe name.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from ..constants import Category
from ..utils.logging import get_logger

log = get_logger(__name__)

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_GENERIC_NAMES = re.compile(
    r"^(img|image|photo|foto|screenshot|bildschirmfoto|document|dokument|scan|"
    r"untitled|unbenannt|file|datei|dsc|pic)[\s_-]*\d*$",
    re.IGNORECASE,
)

# Known vendors to recognise in invoices/receipts.
_VENDORS = (
    "amazon", "paypal", "apple", "google", "microsoft", "netflix", "spotify",
    "ebay", "vodafone", "telekom", "o2", "ikea", "media markt", "saturn",
    "dhl", "up s", "ups", "hetzner", "aws", "github", "openai",
)

_TECH_TERMS = (
    "python", "javascript", "typescript", "java", "react", "django", "flask",
    "numpy", "pandas", "opencv", "pytorch", "tensorflow", "docker", "kubernetes",
    "sql", "git", "linux", "node", "rust", "golang",
)

_ERROR_TERMS = (
    "error", "exception", "traceback", "warning", "failed", "fehler",
)


@dataclass
class RenameSuggestion:
    new_name: str
    confidence: float
    reason: str

    @property
    def changed(self) -> bool:
        return bool(self.new_name)


class SmartRenamer:
    """Produces filename suggestions from category + content."""

    def suggest(
        self, path: str | Path, category: Category, text: str = "", tags: list[str] | None = None
    ) -> RenameSuggestion:
        p = Path(path)
        ext = p.suffix
        stem = p.stem
        text = text or ""
        tags = tags or []

        tokens = self._build_tokens(category, stem, text, tags)
        if not tokens:
            return RenameSuggestion("", 0.0, "no signal")

        base = self._join(tokens)
        new_name = f"{base}{ext.lower()}"
        new_name = self._sanitize(new_name)

        # Only suggest if it differs meaningfully from the original.
        if new_name.lower() == p.name.lower():
            return RenameSuggestion("", 0.0, "already clean")
        confidence = self._confidence(stem, tokens)
        return RenameSuggestion(new_name, confidence, "+".join(t for t in tokens if t))

    # ------------------------------------------------------------- token build
    def _build_tokens(
        self, category: Category, stem: str, text: str, tags: list[str]
    ) -> list[str]:
        hay = f"{stem}\n{text}".lower()
        tokens: list[str] = []

        if category is Category.INVOICE:
            tokens.append("Rechnung")
            vendor = self._find_vendor(hay)
            if vendor:
                tokens.append(vendor.title().replace(" ", ""))
            tokens.append(self._find_year(hay) or self._this_year())
        elif category is Category.CONTRACT:
            tokens.append(self._contract_kind(hay))
            tokens.append(self._find_year(hay) or self._this_year())
        elif category is Category.APPLICATION:
            tokens.append("Bewerbung")
            tokens.append(self._find_year(hay) or self._this_year())
        elif category is Category.TAX:
            tokens.append("Steuer")
            tokens.append(self._find_year(hay) or self._this_year())
        elif category is Category.SCREENSHOT:
            tech = self._find_first(hay, _TECH_TERMS)
            err = self._find_first(hay, _ERROR_TERMS)
            if tech:
                tokens.append(tech.title())
            if err:
                tokens.append(err.title())
            if not tokens:
                tokens.append("Screenshot")
                tokens.append(self._find_date(hay) or self._today())
        elif category is Category.CODE:
            tech = self._find_first(hay, _TECH_TERMS)
            if tech:
                tokens.append(tech.title())
            tokens.append("Code")
        else:
            # Generic: only rename if the original is a junk name.
            if _GENERIC_NAMES.match(stem.strip()):
                tokens.append(category.label.replace(" ", ""))
                key = self._keywords_from_text(text)
                tokens.extend(key[:2])
                tokens.append(self._find_date(hay) or self._today())

        # Deduplicate while preserving order, drop empties.
        seen: set[str] = set()
        result: list[str] = []
        for t in tokens:
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                result.append(t)
        return result

    # ----------------------------------------------------------------- helpers
    @staticmethod
    def _find_vendor(hay: str) -> str | None:
        for v in _VENDORS:
            if v in hay:
                return v.replace(" ", "")
        return None

    @staticmethod
    def _find_first(hay: str, terms) -> str | None:
        for t in terms:
            if t in hay:
                return t
        return None

    @staticmethod
    def _contract_kind(hay: str) -> str:
        if "miet" in hay or "lease" in hay:
            return "Mietvertrag"
        if "arbeit" in hay or "employment" in hay:
            return "Arbeitsvertrag"
        if "kauf" in hay:
            return "Kaufvertrag"
        return "Vertrag"

    @staticmethod
    def _find_year(hay: str) -> str | None:
        m = re.search(r"\b(19|20)\d{2}\b", hay)
        return m.group(0) if m else None

    @staticmethod
    def _find_date(hay: str) -> str | None:
        m = re.search(r"\b(\d{4})[-_.](\d{2})[-_.](\d{2})\b", hay)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return None

    @staticmethod
    def _keywords_from_text(text: str) -> list[str]:
        words = re.findall(r"[A-Za-zÄÖÜäöüß]{4,}", text)
        freq: dict[str, int] = {}
        for w in words:
            wl = w.lower()
            freq[wl] = freq.get(wl, 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        return [w.title() for w, _ in ranked[:3]]

    @staticmethod
    def _this_year() -> str:
        return time.strftime("%Y")

    @staticmethod
    def _today() -> str:
        return time.strftime("%Y-%m-%d")

    @staticmethod
    def _join(tokens: list[str]) -> str:
        return "_".join(tokens)

    @staticmethod
    def _sanitize(name: str) -> str:
        name = _ILLEGAL.sub("", name)
        name = re.sub(r"\s+", "_", name.strip())
        name = re.sub(r"_+", "_", name).strip("_.")
        return name or f"file_{int(time.time())}"

    @staticmethod
    def _confidence(original_stem: str, tokens: list[str]) -> float:
        base = 0.6
        if _GENERIC_NAMES.match(original_stem.strip()):
            base += 0.2
        if len(tokens) >= 3:
            base += 0.1
        return round(min(base, 0.95), 2)
