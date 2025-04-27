import atexit
import logging
import threading
from typing import Any, Callable


class Scheduler:
    def __init__(self, debounce: float | int):
        self._debounce: float = float(debounce)
        self._lock = threading.Lock()
        self._timer = threading.Timer(0, self._execute, [lambda _=0: None, 0])
        self._charged = False
        atexit.register(self.cancel)

    @property
    def charged(self) -> bool:
        with self._lock:
            return self._charged

    def _execute(self, task: Callable[[int], Any], param: int) -> None:
        with self._lock:
            self._charged = False
        try:
            task(param)
        except Exception as e:
            logging.error(f"Task error: {e}")

    def _cancel(self) -> None:
        self._timer.cancel()
        self._charged = False

    def cancel(self) -> None:
        with self._lock:
            self._cancel()

    def run(self, task: Callable[[int], Any], param: int) -> None:
        with self._lock:
            self._cancel()
            self._timer = threading.Timer(self._debounce, self._execute, [task, param])
            self._charged = True
            self._timer.start()
