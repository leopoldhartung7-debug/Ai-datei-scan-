"""SmartFolders - AI-powered file organization assistant.

A modern, fully local desktop application that watches your folders, classifies
incoming files with AI, renames them intelligently, runs OCR, finds duplicates
and lets you search your files semantically - all offline.

The package is split into focused sub-packages:

* :mod:`smartfolders.core`    - file watching, scanning, organizing, rules, DB.
* :mod:`smartfolders.ai`      - classification, OCR, embeddings, search, rename.
* :mod:`smartfolders.system`  - hardware detection and auto-tuned settings.
* :mod:`smartfolders.ui`      - the PyQt6 desktop interface.
* :mod:`smartfolders.utils`   - shared helpers (logging, hashing, paths).
"""

from __future__ import annotations

__app_name__ = "SmartFolders"
__version__ = "1.0.0"
__author__ = "SmartFolders"
__license__ = "Proprietary - All Rights Reserved"

__all__ = ["__app_name__", "__version__", "__author__", "__license__"]
