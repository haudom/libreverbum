"""Hintergrundfaden der Oberfläche — NLP- und Modellaufrufe laufen nie im Oberflächen-Thread
(Regel 9, dokumentation.md §4).

Voraussetzungen
----------------
`fn` darf keine Qt-Objekte des Hauptfadens anfassen (bauplan-phase2.md, Abschnitt 8: „Aus
einem Arbeiterfaden nie ein `QObject` des Hauptfadens anfassen; nur Signale senden"); eine
`sqlite3`-Verbindung bleibt in dem Faden, der sie öffnet (technik.md §12, Festlegung 1) —
öffnet `fn` selbst eine, bleibt sie also in diesem Arbeiterfaden. Der Aufrufer hält eine
Referenz auf den zurückgegebenen Arbeiter, bis er fertig ist — ohne sie räumt Python das
`QObject` weg, während Qt es noch braucht (dieselbe Falle wie bei der Engine, Abschnitt 8).

Liefert
-------
`run_in_worker(fn, *, on_done, on_error)`: startet `fn` in einem eigenen `QThread` und
liefert das Ergebnis oder die Ausnahme über Qt-Signale an `on_done`/`on_error` zurück — Qt
stellt Signale über Threadgrenzen in die Ereignisschleife des Hauptfadens, deshalb dürfen
beide Rückrufe dort wieder auf die Oberfläche zugreifen.

Regeln
------
Eine Ausnahme in `fn` erreicht **immer** `on_error`, nie ein `except`, das nur
protokolliert und weiterläuft (Regel 13) — sonst bleibt die Oberfläche auf dem laufenden
Bildschirm stehen, ohne dass etwas den Fehlschlag meldet.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThread, Signal


class Worker(QThread):
    """Führt `fn` im eigenen Faden aus und meldet Ergebnis oder Ausnahme über Signale.

    Kein öffentlicher Konstruktor außerhalb von `run_in_worker` vorgesehen — die Klasse
    trägt nur die beiden Signale und die Ausführung, keine eigene Fachlichkeit."""

    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, fn: Callable[[], Any], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        # REGEL (dokumentation.md §4, Regel 13): Kein except, das nur protokolliert und
        # weiterläuft. Eine Ausnahme im Arbeiterfaden landete sonst nur auf `stderr`
        # (Standardverhalten von QThread) und die Oberfläche bliebe stumm auf der
        # laufenden Etappe stehen — hier erreicht sie stattdessen immer `on_error`.
        try:
            result = self._fn()
        except Exception as error:  # Absicht: jede Ausnahme erreicht on_error (Regel 13)
            self.failed.emit(error)
        else:
            self.succeeded.emit(result)


def run_in_worker(
    fn: Callable[[], Any],
    *,
    on_done: Callable[[Any], None],
    on_error: Callable[[Any], None],
    parent: QObject | None = None,
) -> Worker:
    """Startet `fn` in einem eigenen `QThread`; `on_done(ergebnis)` beziehungsweise
    `on_error(ausnahme)` laufen im Hauptfaden (siehe Modulkopf, „Liefert").

    Der zurückgegebene `Worker` räumt sich nach `finished` selbst auf (`deleteLater`); der
    Aufrufer hält bis dahin trotzdem eine eigene Referenz, sonst kann Python ihn vorher
    einsammeln (bauplan-phase2.md, Abschnitt 8)."""
    worker = Worker(fn, parent)
    worker.succeeded.connect(on_done)
    worker.failed.connect(on_error)
    worker.finished.connect(worker.deleteLater)
    worker.start()
    return worker
