"""AI-optimized settings.

Turns detected :class:`HardwareInfo` into a concrete, balanced
:class:`PerformanceConfig`. The logic is a transparent heuristic ("expert
system") rather than a black box, so the UI can show *why* each value was
chosen - which is exactly what users want from an "Auto Optimize" button.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import PerformanceConfig
from ..constants import ScanIntensity
from .hardware import HardwareInfo


@dataclass
class OptimizedSettings:
    performance: PerformanceConfig
    rationale: list[str] = field(default_factory=list)
    ocr_recommended: bool = True
    embedding_recommended: bool = True


def recommend_settings(hw: HardwareInfo) -> OptimizedSettings:
    perf = PerformanceConfig()
    why: list[str] = []

    logical = max(1, hw.logical_cores)
    ram_gb = hw.total_ram_mb / 1024 if hw.total_ram_mb else 4

    # --- Worker threads: leave headroom for the OS / foreground apps ---------
    if logical <= 2:
        workers = 1
    elif logical <= 4:
        workers = 2
    elif logical <= 8:
        workers = max(2, logical - 2)
    else:
        workers = min(logical - 2, 12)
    perf.max_worker_threads = workers
    why.append(f"{workers} worker threads (of {logical} logical cores) - leaves headroom for the UI")

    # --- Intensity: scale with cores + storage speed -------------------------
    if logical >= 8 and hw.storage_type == "ssd" and ram_gb >= 16:
        perf.intensity = ScanIntensity.PERFORMANCE
        why.append("Performance mode: 8+ cores, SSD and 16 GB+ RAM detected")
    elif logical <= 2 or ram_gb < 4:
        perf.intensity = ScanIntensity.ECO
        why.append("Eco mode: limited cores/RAM, minimising footprint")
    else:
        perf.intensity = ScanIntensity.BALANCED
        why.append("Balanced mode for typical hardware")

    # --- CPU soft cap --------------------------------------------------------
    perf.cpu_limit_percent = 60 if logical <= 4 else 75
    why.append(f"CPU soft cap at {perf.cpu_limit_percent}% to stay responsive")

    # --- RAM budget: caches + models ----------------------------------------
    if ram_gb >= 32:
        perf.ram_limit_mb = 4096
    elif ram_gb >= 16:
        perf.ram_limit_mb = 2048
    elif ram_gb >= 8:
        perf.ram_limit_mb = 1024
    else:
        perf.ram_limit_mb = 512
    why.append(f"{perf.ram_limit_mb} MB RAM budget (~{ram_gb:.0f} GB total)")

    # --- Cache size scales with storage speed + RAM --------------------------
    if hw.storage_type == "ssd":
        perf.cache_size_mb = min(1024, perf.ram_limit_mb // 2)
        why.append("Larger cache: fast SSD storage")
    else:
        perf.cache_size_mb = min(256, perf.ram_limit_mb // 4)
        why.append("Smaller cache to reduce HDD seek thrashing")

    # --- I/O chunk size ------------------------------------------------------
    perf.io_chunk_kb = 1024 if hw.storage_type == "ssd" else 256

    # --- Battery / mobility --------------------------------------------------
    perf.throttle_on_battery = True
    if hw.on_battery:
        perf.intensity = ScanIntensity.ECO
        perf.max_worker_threads = max(1, perf.max_worker_threads // 2)
        why.append("On battery now: throttled to Eco to preserve power")

    perf.clamp()

    # --- Feature recommendations --------------------------------------------
    ocr_ok = ram_gb >= 4
    emb_ok = ram_gb >= 4
    if hw.is_apple_silicon:
        why.append("Apple Silicon detected: local AI models run efficiently on this machine")
    if not ocr_ok:
        why.append("OCR off by default: <4 GB RAM")
    if not emb_ok:
        why.append("Semantic model off by default: <4 GB RAM (keyword search still works)")

    return OptimizedSettings(
        performance=perf,
        rationale=why,
        ocr_recommended=ocr_ok,
        embedding_recommended=emb_ok,
    )
