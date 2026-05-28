"""Cross-platform hardware detection.

Uses :mod:`psutil` when available for accurate CPU/RAM figures, and falls back
to the standard library (``os``, ``platform``, ``shutil``) otherwise. GPU and
storage-type detection are best-effort and OS-specific (Windows/macOS/Linux).

The detected :class:`HardwareInfo` feeds the AI optimizer, which turns it into
concrete performance settings.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

from ..utils.logging import get_logger

log = get_logger(__name__)

try:
    import psutil

    _HAVE_PSUTIL = True
except Exception:  # pragma: no cover
    _HAVE_PSUTIL = False


@dataclass
class HardwareInfo:
    os_name: str = ""
    os_version: str = ""
    arch: str = ""
    cpu_model: str = ""
    physical_cores: int = 1
    logical_cores: int = 1
    cpu_freq_mhz: float = 0.0
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    disk_total_gb: float = 0.0
    disk_free_gb: float = 0.0
    storage_type: str = "unknown"      # "ssd" | "hdd" | "unknown"
    has_gpu: bool = False
    gpu_name: str = ""
    on_battery: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def is_apple_silicon(self) -> bool:
        return self.os_name == "Darwin" and self.arch in ("arm64", "aarch64")

    def summary(self) -> str:
        gpu = self.gpu_name or ("GPU" if self.has_gpu else "no dedicated GPU")
        return (
            f"{self.os_name} {self.os_version} ({self.arch}) | "
            f"{self.cpu_model or 'CPU'} {self.physical_cores}C/{self.logical_cores}T | "
            f"{self.total_ram_mb // 1024} GB RAM | "
            f"{self.storage_type.upper()} {self.disk_free_gb:.0f}/{self.disk_total_gb:.0f} GB | "
            f"{gpu}"
        )


def detect_hardware() -> HardwareInfo:
    info = HardwareInfo()
    info.os_name = platform.system()
    info.os_version = platform.release()
    info.arch = platform.machine().lower()
    info.cpu_model = _detect_cpu_model()
    info.logical_cores = os.cpu_count() or 1

    if _HAVE_PSUTIL:
        info.physical_cores = psutil.cpu_count(logical=False) or info.logical_cores
        vm = psutil.virtual_memory()
        info.total_ram_mb = vm.total // (1024 * 1024)
        info.available_ram_mb = vm.available // (1024 * 1024)
        try:
            freq = psutil.cpu_freq()
            info.cpu_freq_mhz = float(freq.max or freq.current or 0.0)
        except Exception:
            info.cpu_freq_mhz = 0.0
        info.on_battery = _detect_on_battery_psutil()
    else:
        info.physical_cores = max(1, info.logical_cores // 2)
        info.total_ram_mb = _fallback_ram_mb()
        info.available_ram_mb = info.total_ram_mb

    info.disk_total_gb, info.disk_free_gb = _disk_usage_gb()
    info.storage_type = _detect_storage_type()
    info.has_gpu, info.gpu_name = _detect_gpu()
    return info


# --------------------------------------------------------------------------- #
# Detection helpers
# --------------------------------------------------------------------------- #
def _detect_cpu_model() -> str:
    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=3
            )
            return out.strip()
        if sys.platform.startswith("linux"):
            with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        if sys.platform.startswith("win"):
            return os.environ.get("PROCESSOR_IDENTIFIER", platform.processor())
    except Exception:
        pass
    return platform.processor() or "Unknown CPU"


def _fallback_ram_mb() -> int:
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/meminfo", encoding="utf-8") as fh:
                for line in fh:
                    if line.startswith("MemTotal"):
                        kb = int(line.split()[1])
                        return kb // 1024
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return (pages * page_size) // (1024 * 1024)
    except Exception:
        pass
    return 4096  # conservative assumption


def _disk_usage_gb() -> tuple[float, float]:
    try:
        path = os.path.abspath(os.sep)
        usage = shutil.disk_usage(path)
        gb = 1024 ** 3
        return usage.total / gb, usage.free / gb
    except Exception:
        return 0.0, 0.0


def _detect_storage_type() -> str:
    try:
        if sys.platform.startswith("linux"):
            # rotational flag: 0 = SSD, 1 = HDD
            for dev in ("sda", "nvme0n1", "vda"):
                rot = f"/sys/block/{dev}/queue/rotational"
                if os.path.exists(rot):
                    with open(rot) as fh:
                        return "hdd" if fh.read().strip() == "1" else "ssd"
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["system_profiler", "SPStorageDataType"], text=True, timeout=6
            )
            low = out.lower()
            if "solid state" in low or "ssd" in low or "apple ssd" in low:
                return "ssd"
            if "rotational" in low:
                return "hdd"
        if sys.platform.startswith("win"):
            # Modern Windows machines are overwhelmingly SSD; treat as SSD unless
            # we can prove otherwise via a quick PowerShell probe.
            try:
                out = subprocess.check_output(
                    ["powershell", "-NoProfile", "-Command",
                     "Get-PhysicalDisk | Select-Object -ExpandProperty MediaType"],
                    text=True, timeout=6, stderr=subprocess.DEVNULL,
                )
                low = out.lower()
                if "ssd" in low:
                    return "ssd"
                if "hdd" in low:
                    return "hdd"
            except Exception:
                return "ssd"
    except Exception:
        pass
    return "unknown"


def _detect_gpu() -> tuple[bool, str]:
    try:
        if sys.platform == "darwin":
            out = subprocess.check_output(
                ["system_profiler", "SPDisplaysDataType"], text=True, timeout=6
            )
            for line in out.splitlines():
                if "Chipset Model:" in line:
                    return True, line.split(":", 1)[1].strip()
            return True, "Apple GPU"
        # NVIDIA present?
        if shutil.which("nvidia-smi"):
            try:
                out = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    text=True, timeout=5,
                )
                name = out.strip().splitlines()[0] if out.strip() else "NVIDIA GPU"
                return True, name
            except Exception:
                return True, "NVIDIA GPU"
        if sys.platform.startswith("win"):
            try:
                out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    text=True, timeout=6, stderr=subprocess.DEVNULL,
                )
                names = [line.strip() for line in out.splitlines()[1:] if line.strip()]
                if names:
                    return True, names[0]
            except Exception:
                pass
    except Exception:
        pass
    return False, ""


def _detect_on_battery_psutil() -> bool:
    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return False
        return not battery.power_plugged
    except Exception:
        return False
