"""Tests for config persistence, hardware optimizer and the scanner."""

from __future__ import annotations

from smartfolders.config import AppConfig
from smartfolders.constants import ScanIntensity
from smartfolders.core.scanner import Scanner
from smartfolders.system.hardware import HardwareInfo
from smartfolders.system.optimizer import recommend_settings


def test_config_roundtrip(tmp_path):
    path = tmp_path / "settings.json"
    cfg = AppConfig.create_default()
    cfg.ai.ocr_enabled = False
    cfg.performance.max_worker_threads = 7
    cfg.performance.intensity = ScanIntensity.TURBO
    cfg.save(path)

    loaded = AppConfig.load(path)
    assert loaded.ai.ocr_enabled is False
    assert loaded.performance.max_worker_threads == 7
    assert loaded.performance.intensity is ScanIntensity.TURBO
    assert loaded.first_run is False


def test_config_handles_missing_keys(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text('{"ai": {"enabled": false}, "unknown_future_key": 1}')
    cfg = AppConfig.load(path)
    assert cfg.ai.enabled is False
    # Defaults fill in the rest.
    assert cfg.performance.max_worker_threads >= 1
    assert cfg.watched_folders


def test_optimizer_low_end():
    hw = HardwareInfo(logical_cores=2, total_ram_mb=2048, storage_type="hdd")
    rec = recommend_settings(hw)
    assert rec.performance.intensity is ScanIntensity.ECO
    assert rec.performance.max_worker_threads == 1
    assert rec.rationale


def test_optimizer_high_end():
    hw = HardwareInfo(logical_cores=16, total_ram_mb=32768, storage_type="ssd")
    rec = recommend_settings(hw)
    assert rec.performance.intensity is ScanIntensity.PERFORMANCE
    assert rec.performance.max_worker_threads >= 8
    assert rec.performance.cache_size_mb >= 256


def test_optimizer_on_battery_throttles():
    hw = HardwareInfo(logical_cores=8, total_ram_mb=16384, storage_type="ssd", on_battery=True)
    rec = recommend_settings(hw)
    assert rec.performance.intensity is ScanIntensity.ECO


def test_scanner_walks_and_ignores(tmp_path):
    (tmp_path / "keep.txt").write_text("x")
    (tmp_path / "skip.tmp").write_text("x")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.pdf").write_text("x")

    scanner = Scanner()
    found = {p.name for p in scanner.scan(tmp_path)}
    assert "keep.txt" in found
    assert "deep.pdf" in found
    assert "skip.tmp" not in found
    assert "config" not in found  # .git pruned
