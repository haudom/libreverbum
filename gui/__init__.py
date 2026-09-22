"""Qt-Oberfläche von LibreVerbum — `python -m gui`.

Voraussetzungen
----------------
PySide6 (Gruppe `gui`, `pyproject.toml`) ist installiert. Dieses Paket ruft den Kern
(`libreverbum`) und die Anwendungsschicht (`app`) nur auf, es kennt keine von beiden von
innen — dieselbe Architekturregel wie für `cli/` (technik.md §1, §7; geprüft in
`tests/test_architecture.py`).

Liefert
-------
`python -m gui` (siehe `gui/__main__.py`, `gui/app.py`) startet das Fenster;
`gui/workers.py` trägt NLP- und Modellaufrufe aus dem Oberflächen-Thread heraus (Regel 9);
`gui/qml/` die Token-Datei (`Theme.qml`, seit AP 14) und die Bildschirme, ab AP 15 mit
`Main.qml`.
"""
