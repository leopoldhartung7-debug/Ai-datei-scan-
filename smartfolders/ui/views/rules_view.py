"""Rules management: list, toggle, create and edit automation rules via a GUI."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...core.models import (
    ActionType,
    ConditionField,
    ConditionOp,
    Rule,
    RuleAction,
    RuleCondition,
)


class RuleDialog(QDialog):
    """Create / edit a single rule (one condition + one action - kept simple)."""

    def __init__(self, rule: Rule | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit rule" if rule else "New rule")
        self.setMinimumWidth(440)
        self.rule = rule or Rule(name="New rule")
        self._build()
        self._load()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Name", self.name_edit)

        self.priority = QSpinBox()
        self.priority.setRange(1, 999)
        self.priority.setValue(100)
        form.addRow("Priority (lower = first)", self.priority)

        cond_row = QHBoxLayout()
        self.cond_field = QComboBox()
        for f in ConditionField:
            self.cond_field.addItem(f.value, f)
        self.cond_op = QComboBox()
        for o in ConditionOp:
            self.cond_op.addItem(o.value, o)
        self.cond_value = QLineEdit()
        self.cond_value.setPlaceholderText("value")
        cond_row.addWidget(self.cond_field)
        cond_row.addWidget(self.cond_op)
        cond_row.addWidget(self.cond_value)
        form.addRow("Condition", _wrap(cond_row))

        act_row = QHBoxLayout()
        self.act_type = QComboBox()
        for a in ActionType:
            self.act_type.addItem(a.value, a)
        self.act_target = QLineEdit()
        self.act_target.setPlaceholderText("target folder / pattern (e.g. Documents/Invoices)")
        act_row.addWidget(self.act_type)
        act_row.addWidget(self.act_target, 1)
        form.addRow("Action", _wrap(act_row))

        layout.addLayout(form)

        hint = QLabel(
            "Placeholders in targets: {category} {ext} {year} {month}. "
            "Targets are relative to your organized root unless absolute."
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self) -> None:
        self.name_edit.setText(self.rule.name)
        self.priority.setValue(self.rule.priority)
        if self.rule.conditions:
            c = self.rule.conditions[0]
            self.cond_field.setCurrentIndex(self.cond_field.findData(c.field))
            self.cond_op.setCurrentIndex(self.cond_op.findData(c.op))
            self.cond_value.setText(c.value)
        if self.rule.actions:
            a = self.rule.actions[0]
            self.act_type.setCurrentIndex(self.act_type.findData(a.type))
            self.act_target.setText(a.target)

    def result_rule(self) -> Rule:
        self.rule.name = self.name_edit.text().strip() or "Unnamed rule"
        self.rule.priority = self.priority.value()
        self.rule.conditions = [
            RuleCondition(
                self.cond_field.currentData(),
                self.cond_op.currentData(),
                self.cond_value.text().strip(),
            )
        ]
        self.rule.actions = [
            RuleAction(self.act_type.currentData(), self.act_target.text().strip())
        ]
        return self.rule


class RulesView(QWidget):
    def __init__(self, engine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.engine = engine
        self._build()
        self.refresh()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("Rules & Automation")
        title.setObjectName("H1")
        header.addWidget(title)
        header.addStretch(1)
        add_btn = QPushButton("New rule")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_rule)
        header.addWidget(add_btn)
        root.addLayout(header)

        info = QLabel(
            "Rules run top-to-bottom by priority. Enable a rule with its checkbox. "
            "Double-click to edit."
        )
        info.setObjectName("Muted")
        root.addWidget(info)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._edit_rule)
        self.list.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(lambda: self._edit_selected())
        del_btn = QPushButton("Delete")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for rule in self.engine.db.get_rules():
            summary = _summarise(rule)
            item = QListWidgetItem(summary)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if rule.enabled else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, rule.id)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        rule_id = item.data(Qt.ItemDataRole.UserRole)
        rule = self._rule_by_id(rule_id)
        if rule:
            rule.enabled = item.checkState() == Qt.CheckState.Checked
            self.engine.db.save_rule(rule)
            self.engine.reload_rules()

    def _add_rule(self) -> None:
        dlg = RuleDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.engine.db.save_rule(dlg.result_rule())
            self.engine.reload_rules()
            self.refresh()

    def _edit_rule(self, item: QListWidgetItem) -> None:
        rule = self._rule_by_id(item.data(Qt.ItemDataRole.UserRole))
        if not rule:
            return
        dlg = RuleDialog(rule, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.engine.db.save_rule(dlg.result_rule())
            self.engine.reload_rules()
            self.refresh()

    def _edit_selected(self) -> None:
        item = self.list.currentItem()
        if item:
            self._edit_rule(item)

    def _delete_selected(self) -> None:
        item = self.list.currentItem()
        if not item:
            return
        if QMessageBox.question(self, "Delete rule", "Delete the selected rule?") == \
                QMessageBox.StandardButton.Yes:
            self.engine.db.delete_rule(item.data(Qt.ItemDataRole.UserRole))
            self.engine.reload_rules()
            self.refresh()

    def _rule_by_id(self, rule_id) -> Rule | None:
        for rule in self.engine.db.get_rules():
            if rule.id == rule_id:
                return rule
        return None


def _summarise(rule: Rule) -> str:
    conds = " AND ".join(
        f"{c.field.value} {c.op.value} '{c.value}'" for c in rule.conditions
    ) or "(no conditions)"
    acts = ", ".join(f"{a.type.value} {a.target}".strip() for a in rule.actions) or "(no actions)"
    return f"[{rule.priority}] {rule.name}\n    IF {conds}\n    THEN {acts}"


def _wrap(layout) -> QWidget:
    w = QWidget()
    w.setLayout(layout)
    return w
