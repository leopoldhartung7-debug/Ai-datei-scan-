"""AI subsystem: classification, OCR, embeddings, semantic search, rename.

Every module here is built to *degrade gracefully*: if the heavy optional
dependency (``sentence-transformers``, ``transformers``, ``pytesseract`` ...) is
missing, a lightweight pure-python fallback keeps the feature working at reduced
quality rather than crashing. This is what makes SmartFolders fully offline and
installable on a minimal machine.
"""

from __future__ import annotations

from .classifier import ClassificationResult, FileClassifier
from .duplicates import DuplicateFinder, DuplicateGroup
from .embeddings import EmbeddingEngine
from .ocr import OCREngine
from .rename import SmartRenamer
from .search import SemanticSearch

__all__ = [
    "ClassificationResult",
    "FileClassifier",
    "DuplicateFinder",
    "DuplicateGroup",
    "EmbeddingEngine",
    "OCREngine",
    "SmartRenamer",
    "SemanticSearch",
]
