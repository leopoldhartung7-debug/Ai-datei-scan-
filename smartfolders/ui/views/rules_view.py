"""Rules management: one-click templates plus a low-typing rule editor."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
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

from ...constants import Category
from ...core.models import (
    ActionType,
    ConditionField,
    ConditionOp,
    Rule,
    RuleAction,
    RuleCondition,
)
from ..widgets import Card

# Suggested values offered as a dropdown per condition field, so the user picks
# instead of typing.
_VALUE_SUGGESTIONS: dict[ConditionField, list[str]] = {
    ConditionField.CATEGORY: [c.value for c in Category],
    ConditionField.EXTENSION: [
        "pdf", "png", "jpg", "jpeg", "zip", "docx", "xlsx", "pptx", "mp4", "mp3", "py", "txt",
    ],
    ConditionField.AGE_DAYS: ["7", "30", "90", "180", "365"],
}


def rule_templates() -> list[tuple[str, Rule]]:
    """Ready-made rules that can be added with a single click (no typing)."""

    def cat_move(name: str, category: Category, dest: str, priority: int) -> tuple[str, Rule]:
        return name, Rule(
            name=name,
            priority=priority,
            conditions=[RuleCondition(ConditionField.CATEGORY, ConditionOp.EQUALS, category.value)],
            actions=[RuleAction(ActionType.MOVE, dest)],
        )

    archive_old_zip = Rule(
        name="Alte ZIPs archivieren",
        priority=80,
        match_all=True,
        conditions=[
            RuleCondition(ConditionField.EXTENSION, ConditionOp.EQUALS, "zip"),
            RuleCondition(ConditionField.AGE_DAYS, ConditionOp.GREATER_THAN, "30"),
        ],
        actions=[RuleAction(ActionType.ARCHIVE, "Archive")],
    )

    return [
        cat_move("Rechnungen einsortieren", Category.INVOICE, "Dokumente/Rechnungen", 10),
        cat_move("Verträge einsortieren", Category.CONTRACT, "Dokumente/Verträge", 11),
        cat_move("Bewerbungen einsortieren", Category.APPLICATION, "Dokumente/Bewerbungen", 12),
        cat_move("Steuer einsortieren", Category.TAX, "Dokumente/Steuer", 13),
        cat_move("Uni-Dateien einsortieren", Category.UNIVERSITY, "Dokumente/Uni", 14),
        cat_move("Screenshots sortieren", Category.SCREENSHOT, "Bilder/Screenshots", 20),
        cat_move("Fotos einsortieren", Category.PHOTO, "Bilder/Fotos", 21),
        cat_move("Code gruppieren", Category.CODE, "Code", 30),
        ("Alte ZIPs archivieren", archive_old_zip),
    ]


class RuleDialog(QDialog):
    """Create / edit a single rule with minimal typing."""

    def __init__(self, rule: Rule | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Regel bearbeiten" if rule else "Neue Regel")
        self.setMinimumWidth(480)
        self.rule = rule or Rule(name="Neue Regel")
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
        form.addRow("Priorität (kleiner = zuerst)", self.priority)

        cond_row = QHBoxLayout()
        self.cond_field = QComboBox()
        for f in ConditionField:
            self.cond_field.addItem(f.value, f)
        self.cond_field.currentIndexChanged.connect(self._update_value_suggestions)
        self.cond_op = QComboBox()
        for o in ConditionOp:
            self.cond_op.addItem(o.value, o)
        # Editable combo: offers suggestions but still allows free text.
        self.cond_value = QComboBox()
        self.cond_value.setEditable(True)
        self.cond_value.setMinimumWidth(140)
        cond_row.addWidget(self.cond_field)
        cond_row.addWidget(self.cond_op)
        cond_row.addWidget(self.cond_value, 1)
        form.addRow("Wenn", _wrap(cond_row))

        act_row = QHBoxLayout()
        self.act_type = QComboBox()
        for a in ActionType:
            self.act_type.addItem(a.value, a)
        self.act_target = QLineEdit()
        self.act_target.setPlaceholderText("Zielordner / Muster, z. B. Dokumente/Rechnungen")
        browse = QPushButton("Durchsuchen…")
        browse.clicked.connect(self._browse_target)
        act_row.addWidget(self.act_type)
        act_row.addWidget(self.act_target, 1)
        act_row.addWidget(browse)
        form.addRow("Dann", _wrap(act_row))

        layout.addLayout(form)

        hint = QLabel(
            "Tipp: Bei Wenn = category einfach eine Kategorie aus der Liste wählen. "
            "Platzhalter im Ziel: {category} {ext} {year} {month}."
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

    def _update_value_suggestions(self) -> None:
        field = self.cond_field.currentData()
        current = self.cond_value.currentText()
        self.cond_value.clear()
        self.cond_value.addItems(_VALUE_SUGGESTIONS.get(field, []))
        self.cond_value.setCurrentText(current)

    def _browse_target(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if folder:
            self.act_target.setText(folder)

    def _load(self) -> None:
        self.name_edit.setText(self.rule.name)
        self.priority.setValue(self.rule.priority)
        if self.rule.conditions:
            c = self.rule.conditions[0]
            self.cond_field.setCurrentIndex(self.cond_field.findData(c.field))
            self.cond_op.setCurrentIndex(self.cond_op.findData(c.op))
            self._update_value_suggestions()
            self.cond_value.setCurrentText(c.value)
        else:
            self._update_value_suggestions()
        if self.rule.actions:
            a = self.rule.actions[0]
            self.act_type.setCurrentIndex(self.act_type.findData(a.type))
            self.act_target.setText(a.target)

    def result_rule(self) -> Rule:
        self.rule.name = self.name_edit.text().strip() or "Unbenannte Regel"
        self.rule.priority = self.priority.value()
        self.rule.conditions = [
            RuleCondition(
                self.cond_field.currentData(),
                self.cond_op.currentData(),
                self.cond_value.currentText().strip(),
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
        add_btn = QPushButton("Eigene Regel")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_rule)
        header.addWidget(add_btn)
        root.addLayout(header)

        # --- One-click templates ---------------------------------------------
        templates_card = Card("Vorlagen – mit einem Klick hinzufügen (kein Tippen nötig)")
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (label, _rule) in enumerate(rule_templates()):
            chip = QPushButton(label)
            chip.setObjectName("Chip")
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.clicked.connect(lambda _=False, name=label: self._add_template(name))
            grid.addWidget(chip, i // 3, i % 3)
        templates_card.body().addLayout(grid)
        root.addWidget(templates_card)

        # --- Quick rule by filename (the simplest possible rule) -------------
        quick = Card("Schnellregel: nach Dateiname einsortieren")
        qrow = QHBoxLayout()
        qrow.setSpacing(8)
        qrow.addWidget(QLabel("Wenn Dateiname"))
        self.q_match = QComboBox()
        self.q_match.addItem("enthält", ConditionOp.CONTAINS)
        self.q_match.addItem("beginnt mit", ConditionOp.STARTS_WITH)
        self.q_match.addItem("endet mit", ConditionOp.ENDS_WITH)
        qrow.addWidget(self.q_match)
        self.q_text = QLineEdit()
        self.q_text.setPlaceholderText("z. B. Rechnung")
        qrow.addWidget(self.q_text, 1)
        qrow.addWidget(QLabel("→ verschieben nach"))
        self.q_dest = QLineEdit()
        self.q_dest.setPlaceholderText("z. B. Dokumente/Rechnungen")
        qrow.addWidget(self.q_dest, 1)
        q_browse = QPushButton("Durchsuchen…")
        q_browse.clicked.connect(self._browse_quick_dest)
        qrow.addWidget(q_browse)
        q_add = QPushButton("Regel hinzufügen")
        q_add.setObjectName("Primary")
        q_add.clicked.connect(self._add_quick_rule)
        qrow.addWidget(q_add)
        self.q_text.returnPressed.connect(self._add_quick_rule)
        self.q_dest.returnPressed.connect(self._add_quick_rule)
        quick.body().addLayout(qrow)
        root.addWidget(quick)

        info = QLabel(
            "Aktiviere eine Regel mit dem Häkchen. Reihenfolge nach Priorität. "
            "Doppelklick zum Bearbeiten. Damit Regeln Dateien verschieben, in "
            "Einstellungen -> AI -> Auto-Move einschalten."
        )
        info.setObjectName("Muted")
        info.setWordWrap(True)
        root.addWidget(info)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._edit_rule)
        self.list.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.list, 1)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Bearbeiten")
        edit_btn.clicked.connect(lambda: self._edit_selected())
        del_btn = QPushButton("Löschen")
        del_btn.setObjectName("Danger")
        del_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch(1)
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        btn_row.addWidget(self.status)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------ data
    def refresh(self) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for rule in self.engine.db.get_rules():
            item = QListWidgetItem(_summarise(rule))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if rule.enabled else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, rule.id)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _browse_quick_dest(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Zielordner wählen")
        if folder:
            self.q_dest.setText(folder)

    def _add_quick_rule(self) -> None:
        text = self.q_text.text().strip()
        dest = self.q_dest.text().strip()
        if not text or not dest:
            self.status.setText("Bitte Dateiname-Text und Zielordner angeben.")
            return
        op = self.q_match.currentData()
        op_label = self.q_match.currentText()
        rule = Rule(
            name=f"Name {op_label} '{text}' -> {dest}",
            priority=50,
            conditions=[RuleCondition(ConditionField.NAME, op, text)],
            actions=[RuleAction(ActionType.MOVE, dest)],
        )
        self.engine.db.save_rule(rule)
        self.engine.reload_rules()
        self.refresh()
        self.q_text.clear()
        self.q_dest.clear()
        self.status.setText(f"Regel hinzugefügt: Dateiname {op_label} '{text}' -> {dest}")

    def _add_template(self, name: str) -> None:
        existing = {r.name for r in self.engine.db.get_rules()}
        if name in existing:
            self.status.setText(f"{name}: bereits vorhanden.")
            return
        for label, rule in rule_templates():
            if label == name:
                self.engine.db.save_rule(rule)
                break
        self.engine.reload_rules()
        self.refresh()
        self.status.setText(f"Vorlage hinzugefügt: {name}")

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        rule = self._rule_by_id(item.data(Qt.ItemDataRole.UserRole))
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
        if QMessageBox.question(self, "Regel löschen", "Ausgewählte Regel löschen?") == \
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
    conds = " UND ".join(
        f"{c.field.value} {c.op.value} '{c.value}'" for c in rule.conditions
    ) or "(keine Bedingung)"
    acts = ", ".join(f"{a.type.value} {a.target}".strip() for a in rule.actions) or "(keine Aktion)"
    return f"[{rule.priority}] {rule.name}\n    WENN {conds}\n    DANN {acts}"


def _wrap(layout) -> QWidget:
    w = QWidget()
    w.setLayout(layout)
    return w
