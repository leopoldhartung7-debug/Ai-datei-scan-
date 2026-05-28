"""Tests for the smart renamer."""

from __future__ import annotations

from smartfolders.ai.rename import SmartRenamer
from smartfolders.constants import Category


def test_invoice_rename():
    r = SmartRenamer()
    s = r.suggest("IMG_4832.png", Category.INVOICE, text="Rechnung Amazon 2026 Betrag")
    assert s.changed
    assert "Rechnung" in s.new_name
    assert "Amazon" in s.new_name
    assert s.new_name.endswith(".png")


def test_coding_screenshot_rename():
    r = SmartRenamer()
    s = r.suggest("Screenshot_949.png", Category.SCREENSHOT,
                  text="Python OpenCV error traceback")
    assert s.changed
    assert "Python" in s.new_name
    assert s.new_name.lower().endswith(".png")


def test_contract_rename():
    r = SmartRenamer()
    s = r.suggest("document.pdf", Category.CONTRACT, text="Mietvertrag Wohnung Wien")
    assert "Mietvertrag" in s.new_name


def test_no_change_when_already_clean():
    r = SmartRenamer()
    s = r.suggest("Rechnung_Amazon_2026.png", Category.INVOICE, text="Rechnung Amazon 2026")
    # Should not suggest an identical name.
    assert s.new_name.lower() != "rechnung_amazon_2026.png" or not s.changed


def test_sanitization_removes_illegal_chars():
    r = SmartRenamer()
    s = r.suggest("x.pdf", Category.CONTRACT, text="Vertrag: a/b?c*")
    assert all(ch not in s.new_name for ch in '<>:"/\\|?*')


def test_extension_preserved():
    r = SmartRenamer()
    s = r.suggest("photo.jpeg", Category.INVOICE, text="Rechnung Paypal 2025")
    assert s.new_name.endswith(".jpeg")
