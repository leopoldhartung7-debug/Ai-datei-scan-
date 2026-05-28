#!/usr/bin/env python3
"""SmartFolders one-step installer / bootstrapper.

Installs *everything* SmartFolders needs on Windows, macOS and Linux:

1. Verifies the Python version.
2. Installs all Python dependencies (core + AI + OCR + media) via pip.
3. Installs the native **Tesseract OCR** engine using the platform package
   manager (winget/choco on Windows, Homebrew on macOS, apt/dnf/pacman on
   Linux). Asks for confirmation unless ``--yes`` is given.
4. Pre-downloads the local semantic-search model so the app works fully offline
   afterwards.

Run it from the project root:

    python install.py            # interactive, installs the full experience
    python install.py --yes      # non-interactive (assume yes to prompts)
    python install.py --minimal  # core deps only (skip AI/OCR/native)
    python install.py --venv     # install into a local .venv first

It is safe to re-run; already satisfied steps are skipped.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 11)
EMBED_MODEL = "all-MiniLM-L6-v2"


# --------------------------------------------------------------------------- #
# Pretty printing
# --------------------------------------------------------------------------- #
def info(msg: str) -> None:
    print(f"\033[36m=>\033[0m {msg}")


def ok(msg: str) -> None:
    print(f"\033[32mok\033[0m {msg}")


def warn(msg: str) -> None:
    print(f"\033[33m!!\033[0m {msg}")


def err(msg: str) -> None:
    print(f"\033[31mxx\033[0m {msg}")


def run(cmd: list[str], check: bool = True) -> int:
    info("$ " + " ".join(cmd))
    try:
        return subprocess.run(cmd, check=check).returncode
    except FileNotFoundError:
        err(f"command not found: {cmd[0]}")
        return 127
    except subprocess.CalledProcessError as exc:
        if check:
            raise
        return exc.returncode


def ask(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        return input(f"{question} [Y/n] ").strip().lower() in ("", "y", "yes")
    except EOFError:
        return True


# --------------------------------------------------------------------------- #
# Steps
# --------------------------------------------------------------------------- #
def check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        err(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required, found {sys.version.split()[0]}")
        sys.exit(1)
    ok(f"Python {sys.version.split()[0]} on {sys.platform}")


def maybe_create_venv(use_venv: bool) -> str:
    """Return the python executable to use for the rest of the install."""
    if not use_venv:
        return sys.executable
    venv_dir = ROOT / ".venv"
    if not venv_dir.exists():
        info("Creating virtual environment in .venv ...")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    if sys.platform.startswith("win"):
        py = venv_dir / "Scripts" / "python.exe"
    else:
        py = venv_dir / "bin" / "python"
    ok(f"Using virtual environment: {py}")
    return str(py)


def install_python_deps(python: str, minimal: bool) -> None:
    info("Upgrading pip ...")
    run([python, "-m", "pip", "install", "--upgrade", "pip"], check=False)

    if minimal:
        packages = ["PyQt6>=6.6,<7.0", "watchdog>=4.0", "psutil>=5.9", "platformdirs>=4.0"]
        info("Installing core dependencies (minimal) ...")
        run([python, "-m", "pip", "install", *packages])
    else:
        req = ROOT / "requirements.txt"
        info("Installing all Python dependencies from requirements.txt ...")
        run([python, "-m", "pip", "install", "-r", str(req)])
        # send2trash improves the duplicate "move to trash" UX on all platforms.
        run([python, "-m", "pip", "install", "send2trash"], check=False)
    ok("Python dependencies installed")


def install_tesseract(assume_yes: bool) -> None:
    if shutil.which("tesseract"):
        ok("Tesseract OCR already installed")
        return
    if not ask("Install the native Tesseract OCR engine now?", assume_yes):
        warn("Skipping Tesseract; OCR will be disabled until it is installed.")
        return

    if sys.platform == "darwin":
        _install_tesseract_macos(assume_yes)
    elif sys.platform.startswith("win"):
        _install_tesseract_windows()
    else:
        _install_tesseract_linux()

    if shutil.which("tesseract"):
        ok("Tesseract OCR installed")
    else:
        warn("Tesseract not detected on PATH yet. You may need to restart your shell.")


def _install_tesseract_macos(assume_yes: bool) -> None:
    if not shutil.which("brew"):
        warn("Homebrew not found. Install it from https://brew.sh then re-run, "
             "or install Tesseract manually: brew install tesseract tesseract-lang")
        return
    run(["brew", "install", "tesseract", "tesseract-lang"], check=False)


def _install_tesseract_windows() -> None:
    if shutil.which("winget"):
        run(["winget", "install", "--silent", "--accept-package-agreements",
             "--accept-source-agreements", "UB-Mannheim.TesseractOCR"], check=False)
    elif shutil.which("choco"):
        run(["choco", "install", "-y", "tesseract"], check=False)
    else:
        warn("Neither winget nor choco found. Download the installer from "
             "https://github.com/UB-Mannheim/tesseract/wiki and run it.")


def _install_tesseract_linux() -> None:
    if shutil.which("apt-get"):
        run(["sudo", "apt-get", "update"], check=False)
        run(["sudo", "apt-get", "install", "-y", "tesseract-ocr",
             "tesseract-ocr-deu", "tesseract-ocr-eng"], check=False)
    elif shutil.which("dnf"):
        run(["sudo", "dnf", "install", "-y", "tesseract", "tesseract-langpack-deu"], check=False)
    elif shutil.which("pacman"):
        run(["sudo", "pacman", "-S", "--noconfirm", "tesseract", "tesseract-data-deu",
             "tesseract-data-eng"], check=False)
    else:
        warn("Unknown Linux package manager. Install 'tesseract-ocr' with your distro tools.")


def predownload_model(python: str, assume_yes: bool) -> None:
    if not ask(f"Pre-download the offline AI model '{EMBED_MODEL}' (~90 MB)?", assume_yes):
        warn("Skipping model download; the lightweight fallback will be used until downloaded.")
        return
    info("Downloading semantic model (one time) ...")
    code = (
        "from sentence_transformers import SentenceTransformer;"
        f"SentenceTransformer('{EMBED_MODEL}');"
        "print('model ready')"
    )
    rc = run([python, "-c", code], check=False)
    if rc == 0:
        ok("AI model downloaded and cached for offline use")
    else:
        warn("Model download failed (no network?). The app still works with the fallback.")


def final_message(python: str, use_venv: bool) -> None:
    print()
    ok("SmartFolders is installed!")
    print("\nLaunch it with:")
    if use_venv and not sys.platform.startswith("win"):
        print("    .venv/bin/python -m smartfolders")
    elif use_venv:
        print("    .venv\\Scripts\\python -m smartfolders")
    else:
        print(f"    {Path(python).name} -m smartfolders")
    print("\nOr build a standalone app/exe with:")
    print("    python build/build_exe.py")
    print()


# --------------------------------------------------------------------------- #
def main() -> int:
    parser = argparse.ArgumentParser(description="Install SmartFolders and its dependencies")
    parser.add_argument("--yes", "-y", action="store_true", help="assume yes to all prompts")
    parser.add_argument("--minimal", action="store_true", help="install core dependencies only")
    parser.add_argument("--venv", action="store_true", help="install into a local .venv")
    parser.add_argument("--skip-tesseract", action="store_true", help="do not install Tesseract")
    parser.add_argument("--skip-model", action="store_true", help="do not pre-download the AI model")
    args = parser.parse_args()

    print("=" * 60)
    print("  SmartFolders installer")
    print("=" * 60)

    check_python()
    python = maybe_create_venv(args.venv)
    install_python_deps(python, args.minimal)

    if not args.minimal:
        if not args.skip_tesseract:
            install_tesseract(args.yes)
        if not args.skip_model:
            predownload_model(python, args.yes)

    final_message(python, args.venv)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        err("\nInstallation cancelled.")
        sys.exit(1)
