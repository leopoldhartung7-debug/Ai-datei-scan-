"""Directory scanning.

The scanner performs the *initial* bulk walk of watched folders and yields
candidate files for the processing pipeline. It is intentionally lazy
(generator based) so a folder with hundreds of thousands of files can be
streamed without loading every path into memory at once.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from ..constants import (
    IGNORED_DIR_NAMES,
    IGNORED_SUFFIXES,
)
from ..utils.logging import get_logger

log = get_logger(__name__)


class Scanner:
    """Walks folders and yields files worth processing."""

    def __init__(
        self,
        ignored_dirs: frozenset[str] = IGNORED_DIR_NAMES,
        ignored_suffixes: tuple[str, ...] = IGNORED_SUFFIXES,
        follow_symlinks: bool = False,
        max_depth: int | None = None,
    ) -> None:
        self.ignored_dirs = ignored_dirs
        self.ignored_suffixes = ignored_suffixes
        self.follow_symlinks = follow_symlinks
        self.max_depth = max_depth

    def should_ignore(self, path: Path) -> bool:
        name = path.name
        lower = name.lower()
        if name in self.ignored_dirs:
            return True
        if lower.endswith(self.ignored_suffixes):
            return True
        if name.startswith("~$"):  # office lock files
            return True
        return False

    def scan(self, root: str | Path) -> Iterator[Path]:
        """Yield every eligible file beneath *root* (depth-first)."""
        root = Path(root)
        if not root.exists() or not root.is_dir():
            log.debug("Skip non-existent scan root: %s", root)
            return
        base_depth = len(root.parts)
        for dirpath, dirnames, filenames in os.walk(root, followlinks=self.follow_symlinks):
            current = Path(dirpath)
            # Prune ignored directories in place so os.walk does not descend.
            dirnames[:] = [d for d in dirnames if d not in self.ignored_dirs and not d.startswith(".")]
            if self.max_depth is not None:
                depth = len(current.parts) - base_depth
                if depth >= self.max_depth:
                    dirnames[:] = []
            for fname in filenames:
                fpath = current / fname
                if self.should_ignore(fpath):
                    continue
                try:
                    if fpath.is_file():
                        yield fpath
                except OSError:
                    continue

    def count(self, root: str | Path) -> int:
        """Count eligible files (used for progress bars). May be slow on big trees."""
        return sum(1 for _ in self.scan(root))

    def scan_many(self, roots: list[str | Path]) -> Iterator[Path]:
        seen: set[str] = set()
        for root in roots:
            for path in self.scan(root):
                key = str(path)
                if key not in seen:
                    seen.add(key)
                    yield path
