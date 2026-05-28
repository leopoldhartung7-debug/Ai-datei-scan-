"""System inspection and auto-tuning of performance settings."""

from __future__ import annotations

from . import autostart
from .hardware import HardwareInfo, detect_hardware
from .optimizer import OptimizedSettings, recommend_settings

__all__ = [
    "HardwareInfo",
    "detect_hardware",
    "OptimizedSettings",
    "recommend_settings",
    "autostart",
]
