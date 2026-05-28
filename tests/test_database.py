"""Tests for the SQLite persistence layer."""

from __future__ import annotations

from smartfolders.constants import Category, FileAction
from smartfolders.core.models import (
    ActionType,
    ConditionField,
    ConditionOp,
    FileRecord,
    HistoryEntry,
    Rule,
    RuleAction,
    RuleCondition,
)


def test_upsert_and_get(db):
    rec = FileRecord(path="/tmp/a.pdf", size=123, category=Category.INVOICE, tags=["amazon", "2026"])
    file_id = db.upsert_file(rec)
    assert file_id > 0

    fetched = db.get_file("/tmp/a.pdf")
    assert fetched is not None
    assert fetched.category is Category.INVOICE
    assert fetched.size == 123
    assert "amazon" in fetched.tags


def test_upsert_is_idempotent_on_path(db):
    db.upsert_file(FileRecord(path="/tmp/a.pdf", size=1))
    db.upsert_file(FileRecord(path="/tmp/a.pdf", size=2))
    assert db.count_files() == 1
    assert db.get_file("/tmp/a.pdf").size == 2


def test_update_path(db):
    db.upsert_file(FileRecord(path="/tmp/old.pdf"))
    db.update_file_path("/tmp/old.pdf", "/tmp/new.pdf")
    assert db.get_file("/tmp/old.pdf") is None
    moved = db.get_file("/tmp/new.pdf")
    assert moved is not None and moved.name == "new.pdf"


def test_category_counts(db):
    db.upsert_file(FileRecord(path="/a.pdf", category=Category.INVOICE))
    db.upsert_file(FileRecord(path="/b.pdf", category=Category.INVOICE))
    db.upsert_file(FileRecord(path="/c.py", category=Category.CODE))
    counts = db.category_counts()
    assert counts[Category.INVOICE.value] == 2
    assert counts[Category.CODE.value] == 1


def test_fts_search(db):
    db.upsert_file(FileRecord(path="/inv.pdf", name="rechnung_amazon.pdf",
                              ocr_text="Betrag 49 EUR amazon order"))
    db.upsert_file(FileRecord(path="/cv.pdf", name="lebenslauf.pdf",
                              content_preview="curriculum vitae software engineer"))
    hits = db.search_fts("amazon")
    assert any(h.path == "/inv.pdf" for h in hits)
    hits2 = db.search_fts("lebenslauf")
    assert any(h.path == "/cv.pdf" for h in hits2)


def test_embeddings_roundtrip(db):
    fid = db.upsert_file(FileRecord(path="/x.txt"))
    db.store_embedding(fid, [0.1, 0.2, 0.3, 0.4], "test-model")
    assert db.has_embeddings()
    stored = dict(db.iter_embeddings())
    assert fid in stored
    assert len(stored[fid]) == 4
    assert abs(stored[fid][1] - 0.2) < 1e-6


def test_rules_crud(db):
    rule = Rule(
        name="Move invoices",
        conditions=[RuleCondition(ConditionField.CATEGORY, ConditionOp.EQUALS, "invoice")],
        actions=[RuleAction(ActionType.MOVE, "Documents/Invoices")],
    )
    rid = db.save_rule(rule)
    assert rid > 0
    rules = db.get_rules()
    assert len(rules) == 1
    assert rules[0].conditions[0].value == "invoice"

    rule.id = rid
    rule.enabled = False
    db.save_rule(rule)
    assert db.get_rules(enabled_only=True) == []

    db.delete_rule(rid)
    assert db.get_rules() == []


def test_history(db):
    db.add_history(HistoryEntry(path="/a.pdf", action=FileAction.MOVED, detail="x"))
    db.add_history(HistoryEntry(path="/b.pdf", action=FileAction.RENAMED))
    recent = db.recent_history()
    assert len(recent) == 2
    db.clear_history()
    assert db.recent_history() == []


def test_preferences_and_meta(db):
    db.set_pref("foo", "bar")
    assert db.get_pref("foo") == "bar"
    assert db.get_pref("missing", "default") == "default"
    assert db.get_meta("schema_version") is not None
