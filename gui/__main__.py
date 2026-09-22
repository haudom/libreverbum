"""Startpunkt für `python -m gui`.

Voraussetzungen
----------------
Wird als Modul ausgeführt (`python -m gui`), nicht importiert — die eigentliche
Anwendung steht in `gui/app.py`, damit sie ohne `__main__`-Umweg testbar bleibt.

Liefert
-------
Nichts Eigenes: reicht nur an `gui.app.main()` weiter und beendet den Prozess mit
dessen Ergebnis als Rückgabewert.
"""

from __future__ import annotations

from gui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
