"""Hintergrundfaden der Oberfläche — NLP- und Modellaufrufe laufen nie im Oberflächen-Thread
(Regel 9, dokumentation.md §4).

Voraussetzungen
----------------
`fn` darf keine Qt-Objekte des Hauptfadens anfassen (bauplan-phase2.md, Abschnitt 8: „Aus
einem Arbeiterfaden nie ein `QObject` des Hauptfadens anfassen; nur Signale senden"); eine
`sqlite3`-Verbindung bleibt in dem Faden, der sie öffnet (technik.md §12, Festlegung 1) —
öffnet `fn` selbst eine, bleibt sie also in diesem Arbeiterfaden.

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

# (Befund B10, Durchsicht d993e3e): Verwirft der Aufrufer den Rückgabewert von
# `run_in_worker` (etwa `run_in_worker(fn, on_done=..., on_error=...)` als Ausdruck ohne
# Zuweisung), sammelte Python den `Worker` vor `finished` ein — der Prozess endete dann
# ohne Meldung (Exit 127), ohne dass `on_done`/`on_error` je liefen. `run_in_worker` hält
# deshalb selbst eine Referenz in `_ACTIVE_WORKERS`, bis `finished` feuert; der Aufrufer
# braucht dafür keine eigene mehr.
#
# (Befund F13, Nachprüfung d00e7c9): Zwei stille Fehlschläge blieben trotzdem übrig —
# beendet sich die Anwendung, während ein Arbeiter noch läuft, endete der Prozess mit
# Exit 127, ohne jede Meldung (`wait_for_active_workers`, an `QGuiApplication.aboutToQuit`
# gehängt in `gui.app.build_engine`); und eine Ausnahme in `on_done`/`on_error` selbst kam
# nur als Traceback irgendwo auf stderr an, ohne erkennbaren Bezug zum Rückruf, und die
# Oberfläche blieb scheinbar unbeeindruckt auf der laufenden Etappe stehen
# (`_guarded` unten).
"""

from __future__ import annotations

import sys
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
        #
        # (Befund B8, Durchsicht d993e3e): `except Exception` fängt kein `BaseException`
        # — ein `KeyboardInterrupt` im Arbeiter erreichte `on_error` nie, ein `SystemExit`
        # beendete den ganzen Prozess, statt als Fehlschlag beim Aufrufer anzukommen.
        # „Jede Ausnahme" (Regel 13, Kommentar unten) ist wörtlich gemeint.
        try:
            result = self._fn()
        except BaseException as error:  # Absicht: jede Ausnahme erreicht on_error (Regel 13)
            self.failed.emit(error)
        else:
            self.succeeded.emit(result)


# (Befund B10, Durchsicht d993e3e): Der Modulzustand, der einen laufenden `Worker` am
# Leben hält, solange der Aufrufer selbst keine Referenz braucht — siehe Modulkopf.
_ACTIVE_WORKERS: set[Worker] = set()


def _guarded(callback: Callable[[Any], None], art: str) -> Callable[[Any], None]:
    """Hüllt `on_done`/`on_error` so ein, dass eine Ausnahme **darin** sichtbar auf stderr
    steht, statt nur als anonymer Traceback irgendwo im Protokoll zu verschwinden (Befund
    F13, Nachprüfung d00e7c9) — und läuft danach weiter durch (`raise`), verschluckt also
    selbst nichts (Regel 13: kein `except`, das nur protokolliert)."""

    def wrapped(value: Any) -> None:
        try:
            callback(value)
        except BaseException as error:
            print(f"FEHLER im Rückruf ({art}), nicht verschluckt: {error!r}", file=sys.stderr)
            raise

    return wrapped


def run_in_worker(
    fn: Callable[[], Any],
    *,
    on_done: Callable[[Any], None],
    on_error: Callable[[Any], None],
    parent: QObject | None = None,
) -> Worker:
    """Startet `fn` in einem eigenen `QThread`; `on_done(ergebnis)` beziehungsweise
    `on_error(ausnahme)` laufen im Hauptfaden (siehe Modulkopf, „Liefert").

    Der zurückgegebene `Worker` bleibt bis `finished` am Leben, auch wenn der Aufrufer den
    Rückgabewert verwirft (Befund B10, Durchsicht d993e3e) — `_ACTIVE_WORKERS` hält die
    Referenz, `finished` trägt ihn aus und räumt ihn danach über `deleteLater` auf."""
    worker = Worker(fn, parent)
    worker.succeeded.connect(_guarded(on_done, "on_done"))
    worker.failed.connect(_guarded(on_error, "on_error"))
    _ACTIVE_WORKERS.add(worker)
    worker.finished.connect(lambda: _ACTIVE_WORKERS.discard(worker))
    worker.finished.connect(worker.deleteLater)
    worker.start()
    return worker


def wait_for_active_workers(timeout_ms: int = 5000) -> None:
    """Wird an `QGuiApplication.aboutToQuit` gehängt (`gui.app.build_engine`, einmal je
    Prozess). Beendet sich die Anwendung, während ein Arbeiter noch läuft, endete der
    Prozess bisher mit Exit 127, ohne jede Meldung (Befund F13, Nachprüfung d00e7c9) — hier
    wird je laufendem Arbeiter gewartet und, falls er selbst das Zeitlimit reißt, das
    gemeldet statt stillschweigend abgeschnitten zu werden."""
    for worker in list(_ACTIVE_WORKERS):
        if not worker.isRunning():
            continue
        print(
            f"Anwendung beendet sich, ein Arbeiter läuft noch — warte bis {timeout_ms} ms",
            file=sys.stderr,
        )
        fertig = worker.wait(timeout_ms)
        if not fertig:
            print(f"Arbeiter nach {timeout_ms} ms nicht beendet, wird abgebrochen", file=sys.stderr)
