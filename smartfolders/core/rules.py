"""Rule evaluation engine.

Rules are evaluated against :class:`FileRecord` instances. The engine is pure
and side-effect free: :meth:`RuleEngine.evaluate` returns the list of actions
that *would* apply; actually performing them (moving, renaming, deleting) is the
job of :class:`smartfolders.core.organizer.Organizer`. Keeping evaluation pure
makes it trivially unit-testable and lets the UI offer a "dry run" preview.
"""

from __future__ import annotations

import re
import time
from pathlib import Path

from ..utils.logging import get_logger
from .models import (
    ActionType,
    ConditionField,
    ConditionOp,
    FileRecord,
    Rule,
    RuleAction,
    RuleCondition,
)

log = get_logger(__name__)


class RuleEngine:
    """Evaluates an ordered list of rules against files."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self._rules: list[Rule] = []
        if rules:
            self.set_rules(rules)

    def set_rules(self, rules: list[Rule]) -> None:
        self._rules = sorted(rules, key=lambda r: (r.priority, r.id or 0))

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    # ------------------------------------------------------------------ eval
    def evaluate(self, record: FileRecord) -> list[tuple[Rule, RuleAction]]:
        """Return ``(rule, action)`` pairs for all matching, enabled rules.

        Respects ``stop_processing``: once a matched rule has it set, no later
        rules are considered.
        """
        result: list[tuple[Rule, RuleAction]] = []
        for rule in self._rules:
            if not rule.enabled:
                continue
            if self.matches(rule, record):
                for action in rule.actions:
                    result.append((rule, action))
                if rule.stop_processing:
                    break
        return result

    def matches(self, rule: Rule, record: FileRecord) -> bool:
        if not rule.conditions:
            return False
        checks = (self._check_condition(c, record) for c in rule.conditions)
        return all(checks) if rule.match_all else any(checks)

    # ------------------------------------------------------------ conditions
    def _check_condition(self, cond: RuleCondition, record: FileRecord) -> bool:
        actual = self._field_value(cond.field, record)
        return self._apply_op(cond.op, actual, cond.value)

    @staticmethod
    def _field_value(field: ConditionField, record: FileRecord):
        if field is ConditionField.EXTENSION:
            return record.extension.lstrip(".").lower()
        if field is ConditionField.NAME:
            return record.name.lower()
        if field is ConditionField.CATEGORY:
            return record.category.value
        if field is ConditionField.SIZE:
            return record.size
        if field is ConditionField.AGE_DAYS:
            ref = record.modified_at or record.created_at or time.time()
            return max(0.0, (time.time() - ref) / 86400.0)
        if field is ConditionField.CONTENT:
            return f"{record.ocr_text}\n{record.content_preview}".lower()
        if field is ConditionField.TAG:
            return ",".join(record.tags).lower()
        return ""

    @staticmethod
    def _apply_op(op: ConditionOp, actual, expected: str) -> bool:
        # Numeric comparisons
        if op in (ConditionOp.GREATER_THAN, ConditionOp.LESS_THAN):
            try:
                a, e = float(actual), float(expected)
            except (TypeError, ValueError):
                return False
            return a > e if op is ConditionOp.GREATER_THAN else a < e

        a_str = str(actual).lower()
        e_str = str(expected).lower()

        if op is ConditionOp.EQUALS:
            return a_str == e_str
        if op is ConditionOp.NOT_EQUALS:
            return a_str != e_str
        if op is ConditionOp.CONTAINS:
            return e_str in a_str
        if op is ConditionOp.STARTS_WITH:
            return a_str.startswith(e_str)
        if op is ConditionOp.ENDS_WITH:
            return a_str.endswith(e_str)
        if op is ConditionOp.IN:
            options = {x.strip().lower() for x in e_str.split(",") if x.strip()}
            return a_str in options
        if op is ConditionOp.MATCHES:
            try:
                return re.search(expected, str(actual), re.IGNORECASE) is not None
            except re.error:
                log.warning("Invalid regex in rule condition: %r", expected)
                return False
        return False


# --------------------------------------------------------------------------- #
# Default rule set
# --------------------------------------------------------------------------- #
def default_rules() -> list[Rule]:
    """A small, useful starter rule set seeded on first run."""
    return [
        Rule(
            name="Sort invoices",
            priority=10,
            conditions=[RuleCondition(ConditionField.CATEGORY, ConditionOp.EQUALS, "invoice")],
            actions=[RuleAction(ActionType.MOVE, "Documents/Invoices")],
        ),
        Rule(
            name="Sort screenshots",
            priority=20,
            conditions=[RuleCondition(ConditionField.CATEGORY, ConditionOp.EQUALS, "screenshot")],
            actions=[RuleAction(ActionType.MOVE, "Pictures/Screenshots")],
        ),
        Rule(
            name="Group code files",
            priority=30,
            conditions=[RuleCondition(ConditionField.CATEGORY, ConditionOp.EQUALS, "code")],
            actions=[RuleAction(ActionType.MOVE, "Code")],
        ),
        Rule(
            name="Archive old ZIP files",
            priority=40,
            match_all=True,
            conditions=[
                RuleCondition(ConditionField.EXTENSION, ConditionOp.EQUALS, "zip"),
                RuleCondition(ConditionField.AGE_DAYS, ConditionOp.GREATER_THAN, "30"),
            ],
            actions=[RuleAction(ActionType.ARCHIVE, "Archives")],
            enabled=False,
        ),
    ]


def render_target(pattern: str, record: FileRecord) -> str:
    """Expand ``{placeholders}`` in a rule action target.

    Supported tokens: ``{category}`` ``{ext}`` ``{name}`` ``{stem}``
    ``{year}`` ``{month}`` ``{day}``.
    """
    stem = Path(record.name).stem
    ts = time.localtime(record.modified_at or time.time())
    mapping = {
        "category": record.category.value,
        "ext": record.extension.lstrip("."),
        "name": record.name,
        "stem": stem,
        "year": time.strftime("%Y", ts),
        "month": time.strftime("%m", ts),
        "day": time.strftime("%d", ts),
    }
    out = pattern
    for key, val in mapping.items():
        out = out.replace("{" + key + "}", str(val))
    return out
