"""Prüft `gui.workers.run_in_worker` gegen Regel 9 und Regel 13 (dokumentation.md §4;
bauplan-phase2.md AP 15 — „Regel 9 wird hier zum ersten Mal prüfbar").

Dazu drei Befunde einer Durchsicht (Commit `d993e3e`): B8 (`except Exception` statt
`except BaseException`), B9 (dass `on_done`/`on_error` im Hauptfaden laufen, war
ungeprüft) und B10 (ein verworfener Rückgabewert ließ den Arbeiter vorzeitig einsammeln).
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


def test_run_in_worker_delivers_a_base_exception_to_on_error(qt_gui_app: QGuiApplication) -> None:
    """Befund B8 (Durchsicht d993e3e): `except Exception` fängt kein `BaseException` —
    `SystemExit` und `KeyboardInterrupt` sind direkte Nachkommen von `BaseException`, kein
    `Exception`. Regel 13 verlangt „jede Ausnahme"; das war wörtlich gemeint, aber nicht
    umgesetzt.

    Verfälschung: `except BaseException` in `Worker.run` wieder auf `except Exception`
    zurücksetzen → `on_error` würde nie gerufen, `loop.exec()` liefe bis zum
    3-Sekunden-Sicherheitsnetz durch, und `caught` bliebe leer — die Zusicherung unten
    wird rot."""
    del qt_gui_app
    from PySide6.QtCore import QEventLoop, QTimer

    from gui.workers import run_in_worker

    def boom() -> None:
        raise SystemExit(7)

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
    assert isinstance(caught[0], SystemExit)
    worker.wait(1000)


def test_run_in_worker_callbacks_run_on_the_main_thread(qt_gui_app: QGuiApplication) -> None:
    """Befund B9 (Durchsicht d993e3e): `on_done`/`on_error` laufen im Hauptfaden, nicht im
    Arbeiterfaden — bisher ungeprüft, obwohl der Modulkopf genau das zusichert.

    Verfälschung: in `run_in_worker` `worker.succeeded.connect(on_done)` durch
    `worker.succeeded.connect(on_done, Qt.ConnectionType.DirectConnection)` ersetzen →
    `on_done` liefe dann synchron im Arbeiterfaden, und die Zusicherung unten wird rot."""
    del qt_gui_app
    from PySide6.QtCore import QEventLoop, QThread, QTimer

    from gui.workers import run_in_worker

    loop = QEventLoop()
    seen_threads: list[QThread] = []

    def on_done(result: object) -> None:
        del result
        seen_threads.append(QThread.currentThread())
        loop.quit()

    def on_error(error: object) -> None:
        raise AssertionError(f"unerwarteter Fehler: {error}")

    main_thread = QThread.currentThread()
    worker = run_in_worker(lambda: 42, on_done=on_done, on_error=on_error)
    safety_net = QTimer.singleShot(3000, loop.quit)
    del safety_net
    loop.exec()

    assert seen_threads == [main_thread]
    worker.wait(1000)


def test_run_in_worker_still_calls_back_when_the_return_value_is_discarded(
    qt_gui_app: QGuiApplication,
) -> None:
    """Befund B10 (Durchsicht d993e3e): Verwirft der Aufrufer den Rückgabewert von
    `run_in_worker`, muss der Arbeiter trotzdem fertig werden — vorher konnte Python ihn
    vor `finished` einsammeln, und `on_done` kam dann gar nicht mehr an (an einem echten
    Lauf beobachtet: Exit 127, ohne jede Meldung).

    Verfälschung: das Eintragen in `_ACTIVE_WORKERS`/`worker.finished.connect(lambda: ...
    .discard(worker))` aus `run_in_worker` entfernen → `gc.collect()` sammelt den nicht
    mehr referenzierten Arbeiter vor `finished` ein, `on_done` kommt nicht an, und die
    Zusicherung unten wird rot."""
    del qt_gui_app
    import gc

    from PySide6.QtCore import QEventLoop, QTimer

    from gui.workers import run_in_worker

    loop = QEventLoop()
    done: list[object] = []

    def on_done(result: object) -> None:
        done.append(result)
        loop.quit()

    def on_error(error: object) -> None:
        raise AssertionError(f"unerwarteter Fehler: {error}")

    def start_worker() -> None:
        run_in_worker(lambda: time.sleep(0.2), on_done=on_done, on_error=on_error)
        # Rückgabewert bewusst verworfen (kein `worker = ...`) — genau der Fall aus
        # Befund B10. gc.collect() erzwingt, was Python sonst irgendwann von selbst täte,
        # damit der Test nicht vom Zufall abhängt, wann der Müll eingesammelt wird.
        gc.collect()

    QTimer.singleShot(0, start_worker)
    safety_net = QTimer.singleShot(3000, loop.quit)
    del safety_net
    loop.exec()

    assert done == [None]
