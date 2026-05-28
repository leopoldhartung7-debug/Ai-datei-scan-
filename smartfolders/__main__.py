"""Command-line entry point.

Usage:
    python -m smartfolders                 # launch the desktop UI
    python -m smartfolders --minimized     # launch hidden to the tray
    python -m smartfolders --headless      # run the engine without a GUI
    python -m smartfolders scan [PATHS...]  # one-off organize of folders (headless)
    python -m smartfolders search "query"   # search the index from the terminal
    python -m smartfolders --version
"""

from __future__ import annotations

import argparse
import sys
import time

from . import __version__
from .config import AppConfig
from .utils.logging import get_logger, setup_logging

log = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smartfolders", description="SmartFolders AI file assistant")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument("--minimized", action="store_true", help="start hidden in the system tray")
    parser.add_argument("--headless", action="store_true", help="run the engine without a GUI")
    parser.add_argument("--log-level", default="INFO", help="DEBUG / INFO / WARNING / ERROR")
    sub = parser.add_subparsers(dest="command")

    scan_p = sub.add_parser("scan", help="scan and organize folders, then exit")
    scan_p.add_argument("paths", nargs="*", help="folders to scan (default: configured)")
    scan_p.add_argument("--watch", action="store_true", help="keep watching after the initial scan")

    search_p = sub.add_parser("search", help="search the index and print results")
    search_p.add_argument("query", help="natural-language query")
    search_p.add_argument("--limit", type=int, default=20)

    sub.add_parser("dupes", help="scan the index for duplicates and print groups")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    setup_logging(args.log_level)

    if args.version:
        print(f"SmartFolders {__version__}")
        return 0

    config = AppConfig.load()

    if args.command == "scan":
        return _cmd_scan(config, args.paths or None, watch=args.watch)
    if args.command == "search":
        return _cmd_search(config, args.query, args.limit)
    if args.command == "dupes":
        return _cmd_dupes(config)

    if args.headless:
        return _run_headless(config)

    # Default: launch the GUI.
    from .ui import run_app

    return run_app(config, start_minimized=args.minimized)


# --------------------------------------------------------------------------- #
# Headless commands
# --------------------------------------------------------------------------- #
def _make_engine(config: AppConfig):
    from .engine import SmartFoldersEngine

    return SmartFoldersEngine(config)


def _cmd_scan(config: AppConfig, paths: list[str] | None, watch: bool) -> int:
    engine = _make_engine(config)
    engine.start()
    engine.scan_now(paths)
    print("Scanning... (Ctrl+C to stop)")
    try:
        if watch:
            while True:
                time.sleep(2)
        else:
            # Wait for the queue to drain.
            idle_cycles = 0
            while idle_cycles < 3:
                time.sleep(1)
                if engine.stats.queue_size == 0:
                    idle_cycles += 1
                else:
                    idle_cycles = 0
            stats = engine.stats.as_dict()
            print(
                f"Done. Processed {stats['files_processed']} files, "
                f"classified {stats['files_classified']}, OCR {stats['ocr_done']}."
            )
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        engine.close()
    return 0


def _cmd_search(config: AppConfig, query: str, limit: int) -> int:
    engine = _make_engine(config)
    hits = engine.query(query, limit)
    if not hits:
        print("No matches.")
    for hit in hits:
        rec = hit.record
        print(f"[{rec.category.label:12}] {rec.name}  ({hit.matched_on}, {hit.score:.2f})")
        print(f"    {rec.path}")
    engine.close()
    return 0


def _cmd_dupes(config: AppConfig) -> int:
    engine = _make_engine(config)
    groups = engine.find_duplicates()
    if not groups:
        print("No duplicates found.")
    from .utils.paths import human_size

    for g in groups:
        print(f"\n{g.kind.upper()} group ({g.count} files, {human_size(g.wasted_bytes)} reclaimable):")
        for rec in g.files:
            print(f"    {rec.path}")
    engine.close()
    return 0


def _run_headless(config: AppConfig) -> int:
    engine = _make_engine(config)
    engine.start()
    if config.autostart:
        engine.scan_now()
    print("SmartFolders engine running headless. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
