"""End-to-end pipeline test for the engine (headless, no GUI/network)."""

from __future__ import annotations

from smartfolders.config import AppConfig
from smartfolders.constants import Category
from smartfolders.engine import SmartFoldersEngine


def _config(tmp_path) -> AppConfig:
    cfg = AppConfig.create_default()
    cfg.database_path = str(tmp_path / "engine.db")
    cfg.organized_root = str(tmp_path / "organized")
    cfg.watched_folders = [str(tmp_path / "watch")]
    cfg.ai.ocr_enabled = False          # no tesseract in CI
    cfg.ai.semantic_search = True       # fallback embeddings are fine
    cfg.autostart = False
    return cfg


def test_process_file_classifies_and_indexes(tmp_path):
    watch = tmp_path / "watch"
    watch.mkdir()
    invoice = watch / "rechnung_amazon.pdf"
    invoice.write_text("Rechnung Amazon Betrag 99,00 EUR inkl MwSt Bestellung 2026")

    engine = SmartFoldersEngine(_config(tmp_path))
    try:
        rec = engine.process_file(str(invoice))
        assert rec is not None
        assert rec.category is Category.INVOICE
        # Indexed in the DB
        stored = engine.db.get_file(str(invoice))
        assert stored is not None
        assert stored.category is Category.INVOICE
        # Embedding stored for semantic search
        assert engine.db.has_embeddings()
        # Searchable
        hits = engine.query("amazon rechnung")
        assert any(h.record.path == str(invoice) for h in hits)
    finally:
        engine.close()


def test_process_code_file(tmp_path):
    watch = tmp_path / "watch"
    watch.mkdir()
    script = watch / "main.py"
    script.write_text("import numpy as np\n\ndef run():\n    return np.zeros(3)\n")

    engine = SmartFoldersEngine(_config(tmp_path))
    try:
        rec = engine.process_file(str(script))
        assert rec.category is Category.CODE
    finally:
        engine.close()


def test_default_rules_seeded(tmp_path):
    engine = SmartFoldersEngine(_config(tmp_path))
    try:
        rules = engine.db.get_rules()
        assert len(rules) >= 3
        names = {r.name for r in rules}
        assert "Rechnungen einsortieren" in names
    finally:
        engine.close()


def test_stats_update(tmp_path):
    watch = tmp_path / "watch"
    watch.mkdir()
    (watch / "a.txt").write_text("meeting notes project report")
    engine = SmartFoldersEngine(_config(tmp_path))
    try:
        engine.process_file(str(watch / "a.txt"))
        stats = engine.stats.as_dict()
        assert stats["files_processed"] == 1
        assert stats["files_classified"] == 1
    finally:
        engine.close()
