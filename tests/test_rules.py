"""Tests for the rule evaluation engine."""

from __future__ import annotations

import time

from smartfolders.constants import Category
from smartfolders.core.models import (
    ActionType,
    ConditionField,
    ConditionOp,
    FileRecord,
    Rule,
    RuleAction,
    RuleCondition,
)
from smartfolders.core.rules import RuleEngine, render_target


def _rule(name, field, op, value, action=ActionType.MOVE, target="dst", **kw):
    return Rule(
        name=name,
        conditions=[RuleCondition(field, op, value)],
        actions=[RuleAction(action, target)],
        **kw,
    )


def test_equals_match():
    engine = RuleEngine([_rule("inv", ConditionField.CATEGORY, ConditionOp.EQUALS, "invoice")])
    rec = FileRecord(path="/a.pdf", category=Category.INVOICE)
    actions = engine.evaluate(rec)
    assert len(actions) == 1
    assert actions[0][1].type is ActionType.MOVE


def test_no_match():
    engine = RuleEngine([_rule("inv", ConditionField.CATEGORY, ConditionOp.EQUALS, "invoice")])
    rec = FileRecord(path="/a.py", category=Category.CODE)
    assert engine.evaluate(rec) == []


def test_extension_and_contains():
    engine = RuleEngine([
        _rule("py", ConditionField.EXTENSION, ConditionOp.EQUALS, "py"),
        _rule("name", ConditionField.NAME, ConditionOp.CONTAINS, "test"),
    ])
    rec = FileRecord(path="/test_app.py")
    actions = engine.evaluate(rec)
    assert len(actions) == 2


def test_match_all_vs_any():
    rule_all = Rule(
        name="all",
        match_all=True,
        conditions=[
            RuleCondition(ConditionField.EXTENSION, ConditionOp.EQUALS, "zip"),
            RuleCondition(ConditionField.SIZE, ConditionOp.GREATER_THAN, "1000"),
        ],
        actions=[RuleAction(ActionType.ARCHIVE, "Archives")],
    )
    small_zip = FileRecord(path="/a.zip", size=10)
    big_zip = FileRecord(path="/b.zip", size=5000)
    engine = RuleEngine([rule_all])
    assert engine.evaluate(small_zip) == []
    assert len(engine.evaluate(big_zip)) == 1

    rule_any = Rule(**{**rule_all.__dict__, "match_all": False, "id": None})
    engine.set_rules([rule_any])
    assert len(engine.evaluate(small_zip)) == 1


def test_age_days_condition():
    old = FileRecord(path="/old.zip", modified_at=time.time() - 40 * 86400)
    fresh = FileRecord(path="/new.zip", modified_at=time.time())
    engine = RuleEngine([_rule("age", ConditionField.AGE_DAYS, ConditionOp.GREATER_THAN, "30")])
    assert len(engine.evaluate(old)) == 1
    assert engine.evaluate(fresh) == []


def test_regex_match():
    engine = RuleEngine([_rule("re", ConditionField.NAME, ConditionOp.MATCHES, r"report_\d{4}")])
    assert len(engine.evaluate(FileRecord(path="/report_2026.pdf"))) == 1
    assert engine.evaluate(FileRecord(path="/summary.pdf")) == []


def test_priority_ordering_and_stop():
    high = _rule("high", ConditionField.EXTENSION, ConditionOp.EQUALS, "pdf",
                 priority=1, stop_processing=True)
    low = _rule("low", ConditionField.EXTENSION, ConditionOp.EQUALS, "pdf", priority=10)
    engine = RuleEngine([low, high])
    actions = engine.evaluate(FileRecord(path="/x.pdf"))
    # stop_processing on the high-priority rule means only it runs.
    assert len(actions) == 1
    assert actions[0][0].name == "high"


def test_disabled_rule_skipped():
    engine = RuleEngine([_rule("x", ConditionField.EXTENSION, ConditionOp.EQUALS, "pdf", enabled=False)])
    assert engine.evaluate(FileRecord(path="/a.pdf")) == []


def test_render_target_placeholders():
    rec = FileRecord(path="/a.pdf", category=Category.INVOICE, modified_at=time.mktime((2026, 3, 15, 0, 0, 0, 0, 0, -1)))
    out = render_target("Docs/{category}/{year}/{month}", rec)
    assert out == "Docs/invoice/2026/03"
