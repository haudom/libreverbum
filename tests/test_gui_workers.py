"""Prüft `gui.workers.run_in_worker` gegen Regel 9 und Regel 13 (dokumentation.md §4;
bauplan-phase2.md AP 15 — „Regel 9 wird hier zum ersten Mal prüfbar").
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from PySide6.QtGui import QGuiApplication

pytestmark = pytest.mark.needs_gui


def test_run_in_worker_keeps_the_event_loop_responsive(qt_gui_app: QGuiApplication) -> None:
    """Regel 9, prüfbare Hälfte (bauplan-phase2.md AP 15): `fn` läuft nicht im
    Oberflächen-Thread — ein 50-ms-Timer der Ereignisschleife feuert weiter, während der
    Arbeiter 0,5 s schläft.

    Verfälschung: `fn` **direkt** aufrufen statt über einen `QThread` (etwa `self._fn()`
    im Konstruktor von `Worker` statt in `run()`) → der Aufruf blockiert den Hauptfaden,
    der Timer feuert während der 0,5 s nicht, `ticks` bleibt bei 0 oder 1 stehen und die
    Zusicherung unten wird rot."""
    del qt_gui_app  # sorgt nur dafür, dass genau eine QGuiApplication existiert
    from PySide6.QtCore import QEventLoop, QTimer

    from gui.workers import Worker, run_in_worker

    ticks = 0

    def on_tick() -> None:
        nonlocal ticks
        ticks += 1

    timer = QTimer()
    timer.setInterval(50)
    timer.timeout.connect(on_tick)
    timer.start()

    loop = QEventLoop()
    done: list[object] = []
    errors: list[object] = []
    worker_box: list[Worker] = []

    def on_done(result: object) -> None:
        done.append(result)
        loop.quit()

    def on_error(error: object) -> None:
        errors.append(error)
        loop.quit()

    def start_worker() -> None:
        # Startet `run_in_worker` erst, **nachdem** `loop.exec()` bereits läuft (unten):
        # Ein `on_done`, das noch vor `loop.exec()` synchron feuert, riefe `loop.quit()`
        # auf eine Schleife, die noch gar nicht läuft — der Aufruf verhallt wirkungslos,
        # und der anschließende `loop.exec()` liefe unbemerkt bis zum Sicherheitsnetz
        # durch (mit vielen Ticks, obwohl `fn` synchron im Hauptfaden lief). Erst der
        # verzögerte Start über `QTimer.singleShot(0, …)` macht die Verfälschung sichtbar.
        worker_box.append(
            run_in_worker(lambda: time.sleep(0.5), on_done=on_done, on_error=on_error)
        )

    QTimer.singleShot(0, start_worker)
    safety_net = QTimer.singleShot(3000, loop.quit)
    del safety_net
    loop.exec()
    timer.stop()

    assert not errors, f"unerwarteter Fehler: {errors}"
    assert done == [None]
    # 0,5 s bei 50 ms Takt sind rechnerisch zehn Ticks; mit Toleranz nach unten genügen
    # fünf, um "lief im Hintergrund" von "blockierte den Hauptfaden" (0 oder 1 Tick) zu
    # unterscheiden.
    assert ticks >= 5, f"nur {ticks} Ticks während des 0,5-s-Schlafs — lief fn im Hauptfaden?"
    worker_box[0].wait(1000)


def test_run_in_worker_delivers_an_exception_to_on_error(qt_gui_app: QGuiApplication) -> None:
    """Regel 13: Eine Ausnahme im Arbeiterfaden erreicht **immer** `on_error`, nie ein
    `except`, das nur protokolliert und weiterläuft.

    Verfälschung: `except Exception: pass` statt `self.failed.emit(error)` in
    `Worker.run` → `on_error` wird nie gerufen, `loop.exec()` läuft bis zum
    3-Sekunden-Sicherheitsnetz und `caught` bleibt leer — die Zusicherung unten wird rot."""
    del qt_gui_app
    from PySide6.QtCore import QEventLoop, QTimer

    from gui.workers import run_in_worker

    def boom() -> None:
        raise ValueError("kaputt")

    loop = QEventLoop()
    caught: list[BaseException] = []
    unexpected: list[object] = []

    def on_done(result: object) -> None:
        unexpected.append(result)
        loop.quit()

    def on_error(error: BaseException) -> None:
        caught.append(error)
        loop.quit()

    worker = run_in_worker(boom, on_done=on_done, on_error=on_error)
    safety_net = QTimer.singleShot(3000, loop.quit)
    del safety_net
    loop.exec()

    assert not unexpected, f"boom() hätte scheitern müssen, lieferte {unexpected!r}"
    assert len(caught) == 1
    assert isinstance(caught[0], ValueError)
    assert str(caught[0]) == "kaputt"
    worker.wait(1000)
