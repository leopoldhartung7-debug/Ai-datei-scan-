"""Hybrid semantic + keyword search.

Combines two signals and fuses their ranks:

* **Lexical:** SQLite FTS5 full-text search over name/tags/OCR/preview.
* **Semantic:** cosine similarity between the query embedding and stored file
  embeddings (works with either the transformer or the hashing-fallback backend).

The query is also lightly parsed for *filters* expressed in natural language
("PDFs from March", "invoices from amazon") so the results respect obvious
constraints. This gives the ChatGPT-style search experience requested in the
spec while remaining 100% local.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..constants import Category
from ..core.database import Database
from ..core.models import FileRecord
from ..utils.logging import get_logger
from .embeddings import EmbeddingEngine

log = get_logger(__name__)

_MONTHS = {
    "january": 1, "februar": 2, "february": 2, "januar": 1, "märz": 3, "march": 3,
    "april": 4, "mai": 5, "may": 5, "juni": 6, "june": 6, "juli": 7, "july": 7,
    "august": 8, "september": 9, "oktober": 10, "october": 10,
    "november": 11, "dezember": 12, "december": 12,
}

_CATEGORY_HINTS = {
    "rechnung": Category.INVOICE, "rechnungen": Category.INVOICE, "invoice": Category.INVOICE,
    "invoices": Category.INVOICE, "vertrag": Category.CONTRACT, "contract": Category.CONTRACT,
    "lebenslauf": Category.APPLICATION, "cv": Category.APPLICATION, "resume": Category.APPLICATION,
    "bewerbung": Category.APPLICATION, "screenshot": Category.SCREENSHOT,
    "screenshots": Category.SCREENSHOT, "meme": Category.MEME, "memes": Category.MEME,
    "foto": Category.PHOTO, "fotos": Category.PHOTO, "photo": Category.PHOTO,
    "code": Category.CODE, "coding": Category.CODE, "steuer": Category.TAX,
}

_EXT_HINTS = {
    "pdf": ".pdf", "pdfs": ".pdf", "png": ".png", "jpg": ".jpg", "jpeg": ".jpeg",
    "word": ".docx", "excel": ".xlsx", "powerpoint": ".pptx", "zip": ".zip",
    "video": ".mp4", "videos": ".mp4", "mp3": ".mp3",
}


@dataclass
class SearchHit:
    record: FileRecord
    score: float
    matched_on: str


@dataclass
class ParsedQuery:
    text: str
    category: Category | None = None
    extension: str | None = None
    month: int | None = None
    year: int | None = None


class SemanticSearch:
    """Searches the file index using lexical + semantic fusion."""

    def __init__(self, db: Database, embeddings: EmbeddingEngine | None = None) -> None:
        self.db = db
        self.embeddings = embeddings

    # ------------------------------------------------------------------ public
    def search(self, query: str, limit: int = 50) -> list[SearchHit]:
        parsed = self.parse_query(query)
        lexical = self._lexical(parsed, limit * 2)
        semantic = self._semantic(parsed, limit * 2)
        fused = self._fuse(lexical, semantic)
        filtered = [hit for hit in fused if self._passes_filters(hit.record, parsed)]
        filtered.sort(key=lambda h: h.score, reverse=True)
        return filtered[:limit]

    # ----------------------------------------------------------- query parsing
    def parse_query(self, query: str) -> ParsedQuery:
        lower = query.lower()
        parsed = ParsedQuery(text=query)
        for word in re.findall(r"[a-zäöüß]+", lower):
            if word in _CATEGORY_HINTS and parsed.category is None:
                parsed.category = _CATEGORY_HINTS[word]
            if word in _EXT_HINTS and parsed.extension is None:
                parsed.extension = _EXT_HINTS[word]
            if word in _MONTHS and parsed.month is None:
                parsed.month = _MONTHS[word]
        ym = re.search(r"\b(20\d{2}|19\d{2})\b", lower)
        if ym:
            parsed.year = int(ym.group(0))
        return parsed

    # --------------------------------------------------------------- retrieval
    def _lexical(self, parsed: ParsedQuery, limit: int) -> list[SearchHit]:
        results = self.db.search_fts(parsed.text, limit)
        # FTS rank is implicit (best first); assign a descending score.
        hits = []
        n = len(results)
        for i, rec in enumerate(results):
            hits.append(SearchHit(rec, score=(n - i) / max(n, 1), matched_on="keyword"))
        return hits

    def _semantic(self, parsed: ParsedQuery, limit: int) -> list[SearchHit]:
        if not self.embeddings or not self.db.has_embeddings():
            return []
        qvec = self.embeddings.encode(parsed.text)
        scored: list[tuple[int, float]] = []
        for file_id, vec in self.db.iter_embeddings():
            sim = self.embeddings.cosine(qvec, vec)
            if sim > 0.05:
                scored.append((file_id, sim))
        scored.sort(key=lambda kv: kv[1], reverse=True)
        hits: list[SearchHit] = []
        for file_id, sim in scored[:limit]:
            rec = self.db.get_file_by_id(file_id)
            if rec:
                hits.append(SearchHit(rec, score=sim, matched_on="semantic"))
        return hits

    @staticmethod
    def _fuse(lexical: list[SearchHit], semantic: list[SearchHit]) -> list[SearchHit]:
        """Reciprocal-rank-style fusion keyed by file path."""
        by_path: dict[str, SearchHit] = {}
        for weight, group in ((0.45, lexical), (0.55, semantic)):
            for rank, hit in enumerate(group):
                contribution = weight * (1.0 / (rank + 1)) + weight * 0.2 * hit.score
                existing = by_path.get(hit.record.path)
                if existing:
                    existing.score += contribution
                    if hit.matched_on not in existing.matched_on:
                        existing.matched_on += f"+{hit.matched_on}"
                else:
                    by_path[hit.record.path] = SearchHit(
                        hit.record, contribution, hit.matched_on
                    )
        return list(by_path.values())

    # ----------------------------------------------------------------- filters
    @staticmethod
    def _passes_filters(rec: FileRecord, parsed: ParsedQuery) -> bool:
        if parsed.category and rec.category is not parsed.category:
            return False
        if parsed.extension and rec.extension.lower() != parsed.extension:
            return False
        if parsed.year or parsed.month:
            import time as _t

            ts = rec.modified_at or rec.created_at
            if ts:
                lt = _t.localtime(ts)
                if parsed.year and lt.tm_year != parsed.year:
                    return False
                if parsed.month and lt.tm_mon != parsed.month:
                    return False
        return True
