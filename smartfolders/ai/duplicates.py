"""Duplicate and near-duplicate detection.

Three tiers, cheap to expensive:

1. **Quick signature** (size + head/tail hash) groups obvious candidates.
2. **Exact match** via full SHA-256 confirms byte-identical duplicates.
3. **Perceptual hash** (optional) groups visually similar images even when
   re-encoded / resized, using Hamming distance under a configurable threshold.

Returns :class:`DuplicateGroup` objects; the UI lets the user pick which copy to
keep. Nothing is deleted here - deletion goes through the Organizer's trash-safe
path.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ..constants import IMAGE_EXTENSIONS
from ..core.models import FileRecord
from ..utils.hashing import file_sha256, hamming_distance, perceptual_hash, quick_signature
from ..utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class DuplicateGroup:
    kind: str                     # "exact" | "similar"
    files: list[FileRecord] = field(default_factory=list)
    key: str = ""

    @property
    def wasted_bytes(self) -> int:
        """Bytes that could be reclaimed by keeping a single copy."""
        if len(self.files) <= 1:
            return 0
        return sum(f.size for f in self.files[1:])

    @property
    def count(self) -> int:
        return len(self.files)


class DuplicateFinder:
    """Finds exact and near-duplicate files among a set of records."""

    def __init__(self, perceptual: bool = True, phash_threshold: int = 8) -> None:
        self.perceptual = perceptual
        self.phash_threshold = phash_threshold

    # ------------------------------------------------------------------ exact
    def find_exact(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        """Group byte-identical files. Computes hashes lazily for candidates."""
        by_signature: dict[str, list[FileRecord]] = defaultdict(list)
        for rec in records:
            try:
                sig = quick_signature(rec.path)
            except OSError:
                continue
            by_signature[sig].append(rec)

        groups: list[DuplicateGroup] = []
        for candidates in by_signature.values():
            if len(candidates) < 2:
                continue
            by_hash: dict[str, list[FileRecord]] = defaultdict(list)
            for rec in candidates:
                digest = rec.sha256 or self._safe_sha(rec.path)
                if digest:
                    rec.sha256 = digest
                    by_hash[digest].append(rec)
            for digest, group in by_hash.items():
                if len(group) >= 2:
                    group.sort(key=lambda r: r.path)
                    groups.append(DuplicateGroup("exact", group, digest))
        groups.sort(key=lambda g: g.wasted_bytes, reverse=True)
        return groups

    # --------------------------------------------------------------- similar
    def find_similar_images(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        if not self.perceptual:
            return []
        images = [r for r in records if r.extension.lower() in IMAGE_EXTENSIONS]
        hashed: list[tuple[FileRecord, str]] = []
        for rec in images:
            ph = rec.phash or perceptual_hash(rec.path)
            if ph:
                rec.phash = ph
                hashed.append((rec, ph))

        groups: list[DuplicateGroup] = []
        used: set[int] = set()
        for i, (rec_a, hash_a) in enumerate(hashed):
            if i in used:
                continue
            cluster = [rec_a]
            for j in range(i + 1, len(hashed)):
                if j in used:
                    continue
                rec_b, hash_b = hashed[j]
                if _hash_distance(hash_a, hash_b) <= self.phash_threshold:
                    cluster.append(rec_b)
                    used.add(j)
            if len(cluster) >= 2:
                used.add(i)
                cluster.sort(key=lambda r: r.path)
                groups.append(DuplicateGroup("similar", cluster, hash_a))
        groups.sort(key=lambda g: g.count, reverse=True)
        return groups

    def find_all(self, records: list[FileRecord]) -> list[DuplicateGroup]:
        exact = self.find_exact(records)
        exact_paths = {f.path for g in exact for f in g.files}
        remaining = [r for r in records if r.path not in exact_paths]
        similar = self.find_similar_images(remaining)
        return exact + similar

    @staticmethod
    def _safe_sha(path: str) -> str:
        try:
            return file_sha256(path)
        except OSError:
            return ""


def _hash_distance(a: str, b: str) -> int:
    """Hamming distance tolerant of both hex (imagehash) and our fallback."""
    try:
        return hamming_distance(a, b)
    except ValueError:
        # Fall back to per-character difference for non-hex hashes.
        return sum(1 for x, y in zip(a, b, strict=False) if x != y) + abs(len(a) - len(b))
