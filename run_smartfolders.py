#!/usr/bin/env python3
"""Frozen-app entry point for PyInstaller.

PyInstaller runs the given script as the top-level ``__main__`` module, which has
no package context - so a package's own ``__main__.py`` cannot be used directly
(its ``from . import ...`` relative imports would fail). This thin launcher uses
an absolute import instead, giving the bundled app a proper package context.

For normal development you can still use ``python -m smartfolders``; this file
exists specifically so ``build/build_exe.py`` produces a working executable.
"""

from __future__ import annotations

import sys

from smartfolders.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
