"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from smartfolders.core.database import Database


@pytest.fixture()
def db(tmp_path):
    database = Database(tmp_path / "test.db")
    yield database
    database.close()


@pytest.fixture()
def sample_files(tmp_path):
    """Create a handful of files of different kinds for pipeline tests."""
    files = {}
    (tmp_path / "invoice_amazon.pdf").write_text("Rechnung Amazon Betrag 49,99 EUR MwSt")
    files["invoice"] = tmp_path / "invoice_amazon.pdf"
    (tmp_path / "script.py").write_text("import numpy as np\nprint('hello')\n")
    files["code"] = tmp_path / "script.py"
    (tmp_path / "Screenshot_2026.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    files["screenshot"] = tmp_path / "Screenshot_2026.png"
    (tmp_path / "notes.txt").write_text("just some plain notes about the meeting project")
    files["text"] = tmp_path / "notes.txt"
    return files
