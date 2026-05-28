"""Tests for the offline file classifier."""

from __future__ import annotations

from smartfolders.ai.classifier import FileClassifier
from smartfolders.constants import Category


def test_code_by_extension():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("project/main.py")
    assert result.category is Category.CODE
    assert result.confidence > 0.7


def test_invoice_by_keywords():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("doc.pdf", text="Rechnung von Amazon Betrag 49,99 EUR inkl. MwSt")
    assert result.category is Category.INVOICE
    assert "amazon" in result.tags


def test_contract_by_keywords():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("file.pdf", text="Mietvertrag für die Wohnung, Vereinbarung")
    assert result.category is Category.CONTRACT


def test_screenshot_detection():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("Screenshot_2026-01-01.png", is_screenshot_hint=True)
    assert result.category is Category.SCREENSHOT


def test_coding_screenshot_tagged():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("Screenshot_42.png", text="Traceback most recent call last Python error",
                          is_screenshot_hint=True)
    assert result.category is Category.SCREENSHOT
    assert result.reason == "screenshot+code"


def test_photo_default_for_image():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("vacation.jpg")
    assert result.category in (Category.PHOTO, Category.WALLPAPER, Category.MEME)


def test_archive_extension():
    clf = FileClassifier(use_ml=False)
    assert clf.classify("backup.zip").category is Category.ARCHIVE


def test_year_tag_extracted():
    clf = FileClassifier(use_ml=False)
    result = clf.classify("steuer.pdf", text="Steuerbescheid Finanzamt 2025 Einkommensteuer")
    assert result.category is Category.TAX
    assert "2025" in result.tags
