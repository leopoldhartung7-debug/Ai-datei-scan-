"""Tests for duplicate detection and hashing helpers."""

from __future__ import annotations

from smartfolders.ai.duplicates import DuplicateFinder
from smartfolders.core.models import FileRecord
from smartfolders.utils.hashing import file_sha256, quick_signature


def _make(tmp_path, name, content: bytes) -> FileRecord:
    p = tmp_path / name
    p.write_bytes(content)
    return FileRecord(path=str(p), size=len(content))


def test_exact_duplicates(tmp_path):
    a = _make(tmp_path, "a.txt", b"hello world " * 100)
    b = _make(tmp_path, "b.txt", b"hello world " * 100)
    c = _make(tmp_path, "c.txt", b"different content here")
    finder = DuplicateFinder(perceptual=False)
    groups = finder.find_exact([a, b, c])
    assert len(groups) == 1
    assert groups[0].count == 2
    assert groups[0].kind == "exact"
    assert groups[0].wasted_bytes == a.size


def test_no_false_positive(tmp_path):
    a = _make(tmp_path, "a.txt", b"aaa")
    b = _make(tmp_path, "b.txt", b"bbb")
    finder = DuplicateFinder(perceptual=False)
    assert finder.find_exact([a, b]) == []


def test_sha256_matches_for_identical(tmp_path):
    a = _make(tmp_path, "a.bin", b"X" * 5000)
    b = _make(tmp_path, "b.bin", b"X" * 5000)
    assert file_sha256(a.path) == file_sha256(b.path)
    assert quick_signature(a.path) == quick_signature(b.path)


def test_quick_signature_differs_on_size(tmp_path):
    a = _make(tmp_path, "a.bin", b"X" * 5000)
    b = _make(tmp_path, "b.bin", b"X" * 4999)
    assert quick_signature(a.path) != quick_signature(b.path)


def test_find_all_combines(tmp_path):
    a = _make(tmp_path, "a.txt", b"same" * 50)
    b = _make(tmp_path, "b.txt", b"same" * 50)
    finder = DuplicateFinder(perceptual=False)
    groups = finder.find_all([a, b])
    assert sum(g.count for g in groups) == 2
