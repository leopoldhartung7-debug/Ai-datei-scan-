"""File classification.

Two-stage design:

1. **Fast heuristic stage (always available, offline):** combines the file
   extension prior with keyword scoring over the filename and any extracted
   text / OCR. This alone produces good results and needs zero ML dependencies.
2. **Optional ML refinement:** when ``sentence-transformers`` is installed and
   enabled, ambiguous *document* files are re-scored with zero-shot semantic
   similarity against category descriptions, improving precision on tricky
   cases (e.g. distinguishing an invoice from a contract).

The classifier returns a :class:`ClassificationResult` with a confidence score
so the engine can decide whether to act automatically or flag for review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ..constants import (
    CATEGORY_KEYWORDS,
    EXTENSION_CATEGORY,
    IMAGE_EXTENSIONS,
    SCREENSHOT_NAME_PATTERNS,
    Category,
)
from ..utils.logging import get_logger

log = get_logger(__name__)

# Categories that benefit from content/keyword refinement (vs. pure extension).
_DOCUMENT_CATEGORIES = {
    Category.DOCUMENT,
    Category.INVOICE,
    Category.CONTRACT,
    Category.APPLICATION,
    Category.TAX,
    Category.UNIVERSITY,
    Category.WORK,
}

# Short natural-language descriptions used by the optional zero-shot stage.
_CATEGORY_DESCRIPTIONS: dict[Category, str] = {
    Category.INVOICE: "an invoice, bill, receipt or payment with amounts and VAT",
    Category.CONTRACT: "a legal contract, agreement, lease or terms of service",
    Category.APPLICATION: "a job application, CV, resume or cover letter",
    Category.TAX: "a tax document, tax return or tax office statement",
    Category.UNIVERSITY: "university lecture notes, exam, thesis or assignment",
    Category.WORK: "a work report, meeting minutes or business presentation",
    Category.DOCUMENT: "a generic text document or letter",
}


def _kw_in(keyword: str, haystack: str) -> bool:
    """Keyword presence test.

    Short keywords (<= 3 chars, e.g. "cv", "uni", "vat") require a word boundary
    to avoid false positives like "cv" inside "opencv". Longer keywords use plain
    substring matching so German compound words still match (e.g. the keyword
    "vertrag" matches "mietvertrag").
    """
    if len(keyword) <= 3:
        return re.search(rf"\b{re.escape(keyword)}\b", haystack) is not None
    return keyword in haystack


@dataclass
class ClassificationResult:
    category: Category
    confidence: float
    tags: list[str] = field(default_factory=list)
    reason: str = ""


class FileClassifier:
    """Classify a file into a :class:`Category` with a confidence score."""

    def __init__(self, embedding_engine=None, use_ml: bool = True) -> None:
        self._embeddings = embedding_engine
        self._use_ml = use_ml
        self._desc_vectors: dict[Category, list[float]] | None = None

    # ------------------------------------------------------------------ public
    def classify(
        self,
        path: str | Path,
        text: str = "",
        *,
        is_screenshot_hint: bool = False,
    ) -> ClassificationResult:
        p = Path(path)
        ext = p.suffix.lower()
        name = p.name.lower()
        haystack = f"{name}\n{text}".lower()

        base = EXTENSION_CATEGORY.get(ext, Category.OTHER)
        tags: list[str] = []

        # --- Images: distinguish screenshot / meme / wallpaper / photo -------
        if ext in IMAGE_EXTENSIONS:
            cat, conf, why = self._classify_image(name, haystack, is_screenshot_hint)
            tags = self._collect_tags(haystack)
            return ClassificationResult(cat, conf, tags, why)

        # --- Documents: keyword + optional ML refinement ---------------------
        if base in _DOCUMENT_CATEGORIES or ext == ".pdf":
            cat, conf, why = self._classify_document(haystack, base, bool(text))
            tags = self._collect_tags(haystack)
            return ClassificationResult(cat, conf, tags, why)

        # --- Everything else: extension prior is strong ----------------------
        conf = 0.9 if base is not Category.OTHER else 0.3
        return ClassificationResult(base, conf, self._collect_tags(haystack), "extension")

    # --------------------------------------------------------------- internals
    def _classify_image(
        self, name: str, haystack: str, hint: bool
    ) -> tuple[Category, float, str]:
        if hint or any(pat in name for pat in SCREENSHOT_NAME_PATTERNS):
            # Coding screenshot? error/traceback keywords push toward CODE tag.
            if any(_kw_in(k, haystack) for k in CATEGORY_KEYWORDS[Category.CODE]):
                return Category.SCREENSHOT, 0.85, "screenshot+code"
            return Category.SCREENSHOT, 0.8, "screenshot pattern"
        if any(_kw_in(k, haystack) for k in CATEGORY_KEYWORDS[Category.MEME]):
            return Category.MEME, 0.7, "meme keyword"
        if any(_kw_in(k, name) for k in CATEGORY_KEYWORDS[Category.WALLPAPER]):
            return Category.WALLPAPER, 0.7, "wallpaper keyword"
        return Category.PHOTO, 0.6, "image default"

    def _classify_document(
        self, haystack: str, base: Category, has_text: bool
    ) -> tuple[Category, float, str]:
        scores = self._keyword_scores(haystack)
        if scores:
            best_cat, best_score = max(scores.items(), key=lambda kv: kv[1])
            # Normalise a rough confidence from keyword density.
            conf = min(0.95, 0.55 + 0.1 * best_score)
            # Optional ML refinement when keywords are weak but we have text.
            if has_text and best_score <= 1 and self._ml_ready():
                ml_cat, ml_conf = self._ml_refine(haystack)
                if ml_cat and ml_conf > conf:
                    return ml_cat, ml_conf, "ml-zeroshot"
            return best_cat, conf, f"keywords:{best_cat.value}"

        if has_text and self._ml_ready():
            ml_cat, ml_conf = self._ml_refine(haystack)
            if ml_cat:
                return ml_cat, ml_conf, "ml-zeroshot"
        # Generic document fallback.
        return (base if base in _DOCUMENT_CATEGORIES else Category.DOCUMENT), 0.5, "doc default"

    @staticmethod
    def _keyword_scores(haystack: str) -> dict[Category, int]:
        scores: dict[Category, int] = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            if cat in (Category.SCREENSHOT, Category.MEME, Category.WALLPAPER, Category.CODE):
                continue
            count = sum(1 for kw in keywords if _kw_in(kw, haystack))
            if count:
                scores[cat] = count
        return scores

    @staticmethod
    def _collect_tags(haystack: str) -> list[str]:
        tags: set[str] = set()
        for _cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if " " not in kw and _kw_in(kw, haystack):
                    tags.add(kw)
        # Detect a 4-digit year as a useful tag.
        for match in re.findall(r"\b(?:19|20)\d{2}\b", haystack):
            tags.add(match)
        return sorted(tags)[:12]

    # ------------------------------------------------------------ ML refinement
    def _ml_ready(self) -> bool:
        return bool(self._use_ml and self._embeddings and self._embeddings.is_ml_backend)

    def _ml_refine(self, text: str) -> tuple[Category | None, float]:
        try:
            if self._desc_vectors is None:
                self._desc_vectors = {
                    cat: self._embeddings.encode(desc)
                    for cat, desc in _CATEGORY_DESCRIPTIONS.items()
                }
            query = self._embeddings.encode(text[:1000])
            best_cat, best_sim = None, -1.0
            for cat, vec in self._desc_vectors.items():
                sim = self._embeddings.cosine(query, vec)
                if sim > best_sim:
                    best_cat, best_sim = cat, sim
            # Map cosine [-1,1] -> confidence [0,1].
            conf = max(0.0, min(1.0, (best_sim + 1) / 2))
            return best_cat, round(conf, 3)
        except Exception:  # pragma: no cover
            log.debug("ML refinement failed", exc_info=True)
            return None, 0.0
