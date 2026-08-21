"""Aufruf per `python -m cli buch.epub` (bauplan.md T16) — dünner Aufruf von `cli.main`."""

from __future__ import annotations

import sys

from cli.main import main

if __name__ == "__main__":
    sys.exit(main())
