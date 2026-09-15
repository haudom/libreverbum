"""Anwendungsschicht — was beide Oberflächen teilen und der Kern nicht kennt
(technik.md §14, E4; bauplan-phase2.md AP 3).

Aufgabe
-------
Trägt, was `cli/` und `gui/` gleichermaßen brauchen, aber `libreverbum/` nach technik.md §9
nicht kennen darf: Datenverzeichnis und `config.toml` (`app.config`), Auflösung des
Modellnamens (`app.model`) und die Namensbildung der Exportdateien (`app.export`). Was
dagegen **Verkettung von Kernschritten** ist — Anki-Deck schreiben, Druckseite schreiben,
eine Karte im Profil buchen —, liegt nach technik.md §7 in `libreverbum.pipeline`, nicht
hier (bauplan-phase2.md AP 2).

Dieses Paket liegt bewusst **neben** `cli/` und `gui/`, nicht unter einem der beiden:
Es importiert `libreverbum`, nie `cli`, `gui` oder Qt (`tests/test_architecture.py` prüft
alle drei Richtungen). Eine Oberfläche, die die andere importiert, wäre möglich, aber
schief — `app/` ist der gemeinsame Nenner statt einer Bevorzugung.

Voraussetzungen
---------------
Keine eigenen — jedes Modul hier nennt seine in seinem eigenen Docstring.

Liefert
-------
Fertige Pfade, eine fertige Modellserver-Adresse und fertige Exportdateinamen an den
Aufrufer (`cli.main`, künftig `gui/`) — nie eine eigene Vorgabe an den Kern zurück
(technik.md §9, „Der Kern kennt keine Vorgabe").
"""
