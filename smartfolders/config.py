"""Application configuration: a typed settings object with JSON persistence.

The :class:`AppConfig` dataclass is the single source of truth for every user
preference. It is serialised to ``settings.json`` in the per-user config dir and
reloaded on startup. All fields have sane defaults so a fresh install works
without any configuration.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .constants import ScanIntensity
from .utils.logging import get_logger
from .utils.paths import (
    app_config_dir,
    default_database_path,
    default_watched_folders,
)

log = get_logger(__name__)

SETTINGS_FILENAME = "settings.json"


@dataclass
class PerformanceConfig:
    """How much of the machine the background engine may use."""

    intensity: ScanIntensity = ScanIntensity.BALANCED
    max_worker_threads: int = 4
    cpu_limit_percent: int = 70          # soft target; workers throttle above it
    ram_limit_mb: int = 1024             # soft cap for caches / models
    io_chunk_kb: int = 256
    cache_size_mb: int = 256
    throttle_on_battery: bool = True
    pause_on_fullscreen: bool = True     # don't scan while user games / presents

    def clamp(self) -> None:
        self.max_worker_threads = max(1, min(self.max_worker_threads, 64))
        self.cpu_limit_percent = max(10, min(self.cpu_limit_percent, 100))
        self.ram_limit_mb = max(128, self.ram_limit_mb)
        self.cache_size_mb = max(32, self.cache_size_mb)


@dataclass
class AIConfig:
    """Toggles and model choices for the AI subsystem."""

    enabled: bool = True
    auto_classify: bool = True
    auto_rename: bool = False            # off by default - renaming is invasive
    auto_move: bool = False              # off by default - moving is invasive
    ocr_enabled: bool = True
    ocr_languages: str = "deu+eng"
    semantic_search: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    duplicate_detection: bool = True
    perceptual_image_match: bool = True
    perceptual_threshold: int = 8        # max hamming distance for "similar"
    confidence_threshold: float = 0.55   # below this -> "Other", needs review


@dataclass
class UIConfig:
    theme: str = "dark"                  # "dark" | "light"
    accent_color: str = "#2563eb"        # strong blue
    start_minimized: bool = False
    minimize_to_tray: bool = True
    close_to_tray: bool = True
    show_notifications: bool = True
    language: str = "en"
    window_width: int = 1180
    window_height: int = 760


@dataclass
class AppConfig:
    """Top-level configuration aggregate."""

    watched_folders: list[str] = field(default_factory=list)
    organized_root: str = ""             # where organized files are moved to
    database_path: str = ""
    autostart: bool = True               # start watching on launch
    run_at_login: bool = False
    first_run: bool = True

    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # ------------------------------------------------------------------ paths
    @staticmethod
    def settings_path() -> Path:
        return Path(app_config_dir()) / SETTINGS_FILENAME

    # ----------------------------------------------------------------- create
    @classmethod
    def create_default(cls) -> AppConfig:
        cfg = cls()
        cfg.watched_folders = [str(p) for p in default_watched_folders()]
        cfg.organized_root = str(Path.home() / "SmartFolders")
        cfg.database_path = str(default_database_path())
        return cfg

    # ------------------------------------------------------------------- load
    @classmethod
    def load(cls, path: str | Path | None = None) -> AppConfig:
        path = Path(path) if path else cls.settings_path()
        if not path.exists():
            cfg = cls.create_default()
            cfg.save(path)
            log.info("Created default settings at %s", path)
            return cfg
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cfg = cls.from_dict(data)
            cfg.first_run = False
            return cfg
        except (json.JSONDecodeError, OSError, TypeError, ValueError) as exc:
            log.error("Failed to read settings (%s); using defaults", exc)
            return cls.create_default()

    @classmethod
    def from_dict(cls, data: dict) -> AppConfig:
        perf = PerformanceConfig(**_filter(PerformanceConfig, data.get("performance", {})))
        # ScanIntensity may arrive as a plain string from JSON.
        if isinstance(perf.intensity, str):
            perf.intensity = ScanIntensity(perf.intensity)
        ai = AIConfig(**_filter(AIConfig, data.get("ai", {})))
        ui = UIConfig(**_filter(UIConfig, data.get("ui", {})))
        top = _filter(cls, data, exclude={"performance", "ai", "ui"})
        cfg = cls(performance=perf, ai=ai, ui=ui, **top)
        if not cfg.database_path:
            cfg.database_path = str(default_database_path())
        if not cfg.watched_folders:
            cfg.watched_folders = [str(p) for p in default_watched_folders()]
        if not cfg.organized_root:
            cfg.organized_root = str(Path.home() / "SmartFolders")
        return cfg

    # ------------------------------------------------------------------- save
    def save(self, path: str | Path | None = None) -> None:
        path = Path(path) if path else self.settings_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.performance.clamp()
        payload = self.to_dict()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)  # atomic write
        log.debug("Saved settings to %s", path)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["performance"]["intensity"] = self.performance.intensity.value
        return data


def _filter(cls, data: dict, exclude: set[str] | None = None) -> dict:
    """Keep only keys that are valid dataclass fields (forward-compatible)."""
    exclude = exclude or set()
    valid = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return {k: v for k, v in data.items() if k in valid and k not in exclude}
