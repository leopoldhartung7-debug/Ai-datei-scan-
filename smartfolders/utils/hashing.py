"""Hashing helpers for duplicate detection.

* :func:`file_sha256`     - exact content hash (streaming, constant memory).
* :func:`quick_signature` - cheap (size, head, tail) hash for pre-filtering.
* :func:`perceptual_hash` - near-duplicate image hash (optional ``imagehash``,
  with a pure-python average-hash fallback when Pillow is available).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK = 1024 * 256  # 256 KiB streaming chunk


def file_sha256(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file's full contents."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def quick_signature(path: str | Path, sample: int = 65536) -> str:
    """Fast, collision-tolerant signature for the *first pass* of dedup.

    Combines file size with a hash of the first and last ``sample`` bytes. Files
    with different signatures are guaranteed different; matching signatures are
    then confirmed with a full :func:`file_sha256`.
    """
    p = Path(path)
    size = p.stat().st_size
    h = hashlib.sha1()
    h.update(str(size).encode())
    with open(p, "rb") as fh:
        head = fh.read(sample)
        h.update(head)
        if size > sample * 2:
            fh.seek(-sample, 2)
            h.update(fh.read(sample))
    return f"{size}:{h.hexdigest()}"


def _average_hash_fallback(path: str | Path, hash_size: int = 8) -> str | None:
    """Pure-Pillow average hash used when the ``imagehash`` package is absent."""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        img = Image.open(path).convert("L").resize(
            (hash_size, hash_size), Image.Resampling.LANCZOS
        )
    except Exception:
        return None
    pixels = list(img.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if px >= avg else "0" for px in pixels)
    # Pack the bit string into a hex digest.
    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def perceptual_hash(path: str | Path) -> str | None:
    """Return a perceptual hash for near-duplicate image detection.

    Returns ``None`` if no imaging backend is available, allowing callers to
    skip perceptual comparison gracefully.
    """
    try:
        import imagehash
        from PIL import Image

        return str(imagehash.phash(Image.open(path)))
    except Exception:
        return _average_hash_fallback(path)


def hamming_distance(a: str, b: str) -> int:
    """Hamming distance between two equal-length hex hashes (bit difference)."""
    if len(a) != len(b):
        return max(len(a), len(b)) * 4
    return bin(int(a, 16) ^ int(b, 16)).count("1")
