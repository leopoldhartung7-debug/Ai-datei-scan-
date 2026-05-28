"""Tests for the embedding engine and hybrid search (fallback backend)."""

from __future__ import annotations

from smartfolders.ai.embeddings import EmbeddingEngine
from smartfolders.ai.search import SemanticSearch
from smartfolders.constants import Category
from smartfolders.core.models import FileRecord


def test_fallback_embeddings_are_normalised():
    eng = EmbeddingEngine(fallback_dim=64)
    if eng.is_ml_backend:
        return  # skip when a real model is present
    vec = eng.encode("invoice from amazon")
    assert len(vec) == 64
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_cosine_self_similarity():
    eng = EmbeddingEngine(fallback_dim=64)
    v = eng.encode("python opencv error traceback")
    assert abs(eng.cosine(v, v) - 1.0) < 1e-6


def test_similar_texts_score_higher():
    eng = EmbeddingEngine(fallback_dim=128)
    if eng.is_ml_backend:
        return
    a = eng.encode("rechnung amazon zahlung betrag")
    b = eng.encode("amazon rechnung betrag bezahlt")
    c = eng.encode("python opencv error code")
    assert eng.cosine(a, b) > eng.cosine(a, c)


def test_query_parsing():
    search = SemanticSearch(db=None, embeddings=None)  # parsing needs no db
    parsed = search.parse_query("Zeig Rechnungen von Amazon vom März 2026")
    assert parsed.category is Category.INVOICE
    assert parsed.month == 3
    assert parsed.year == 2026


def test_pdf_extension_filter_parsed():
    search = SemanticSearch(db=None, embeddings=None)
    parsed = search.parse_query("Finde PDFs vom Januar")
    assert parsed.extension == ".pdf"
    assert parsed.month == 1


def test_search_end_to_end(db):
    eng = EmbeddingEngine(fallback_dim=128)
    search = SemanticSearch(db, eng)

    rec = FileRecord(path="/inv.pdf", name="rechnung_amazon.pdf",
                     category=Category.INVOICE, ocr_text="amazon betrag 49 eur rechnung")
    fid = db.upsert_file(rec)
    db.store_embedding(fid, eng.encode(rec.searchable_text), eng.backend_name)

    rec2 = FileRecord(path="/code.py", name="main.py", category=Category.CODE,
                      content_preview="import numpy python script")
    fid2 = db.upsert_file(rec2)
    db.store_embedding(fid2, eng.encode(rec2.searchable_text), eng.backend_name)

    hits = search.search("amazon rechnung", limit=10)
    assert hits
    assert hits[0].record.path == "/inv.pdf"
