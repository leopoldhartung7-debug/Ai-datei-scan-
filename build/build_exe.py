#!/usr/bin/env python3
"""Build a standalone SmartFolders bundle with PyInstaller.

Cross-platform:

* **Windows** -> ``dist/SmartFolders/SmartFolders.exe`` (one-folder, fast start)
* **macOS**   -> ``dist/SmartFolders.app`` (double-clickable bundle)
* **Linux**   -> ``dist/SmartFolders/SmartFolders`` (portable folder)

Usage:
    python build/build_exe.py                 # one-folder build (recommended)
    python build/build_exe.py --onefile       # single-file executable
    python build/build_exe.py --clean         # clean previous build artifacts

The resulting bundle includes the full Python runtime and every dependency, so
end users do not need Python installed. The native Tesseract OCR engine is the
only optional external component (the app degrades gracefully without it; see
docs/BUILD.md for bundling instructions).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "SmartFolders"
ENTRY = ROOT / "run_smartfolders.py"


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not found; installing ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=6.6"], check=True)


def clean() -> None:
    for d in ("build/pyi", "dist"):
        path = ROOT / d
        if path.exists():
            print(f"Removing {path}")
            shutil.rmtree(path, ignore_errors=True)
    for spec in ROOT.glob("*.spec"):
        spec.unlink()


def build(onefile: bool) -> int:
    ensure_pyinstaller()

    # Hidden imports PyInstaller's static analysis can miss (optional deps that
    # are imported lazily inside try/except blocks).
    hidden = [
        "smartfolders.ui.app_qt",
        "smartfolders.ui.main_window",
        "watchdog.observers",
        "watchdog.observers.polling",
    ]
    collect_all = ["sentence_transformers", "transformers", "tokenizers"]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--noconsole",
        "--noconfirm",
        "--clean",
        "--workpath", str(ROOT / "build" / "pyi"),
        "--distpath", str(ROOT / "dist"),
        "--specpath", str(ROOT),
        "--paths", str(ROOT),
    ]
    cmd += ["--onefile"] if onefile else ["--onedir"]

    for h in hidden:
        cmd += ["--hidden-import", h]
    # collect-all is heavy; only include if the package is importable.
    for pkg in collect_all:
        if _importable(pkg):
            cmd += ["--collect-all", pkg]

    if sys.platform == "darwin":
        cmd += ["--osx-bundle-identifier", "com.smartfolders.app"]
        cmd += ["--windowed"]

    cmd.append(str(ENTRY))

    print("Running:\n  " + " ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode == 0:
        _print_output_location(onefile)
    return result.returncode


def _importable(pkg: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(pkg) is not None


def _print_output_location(onefile: bool) -> None:
    dist = ROOT / "dist"
    print("\nBuild complete. Artifact location:")
    if sys.platform == "darwin":
        print(f"  {dist / (APP_NAME + '.app')}")
    elif sys.platform.startswith("win"):
        if onefile:
            print(f"  {dist / (APP_NAME + '.exe')}")
        else:
            print(f"  {dist / APP_NAME / (APP_NAME + '.exe')}")
    else:
        target = dist / (APP_NAME if onefile else f"{APP_NAME}/{APP_NAME}")
        print(f"  {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standalone SmartFolders bundle")
    parser.add_argument("--onefile", action="store_true", help="produce a single-file executable")
    parser.add_argument("--clean", action="store_true", help="remove previous build artifacts and exit")
    args = parser.parse_args()

    if args.clean:
        clean()
        print("Cleaned.")
        return 0
    return build(args.onefile)


if __name__ == "__main__":
    sys.exit(main())
