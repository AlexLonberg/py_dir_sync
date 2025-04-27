import atexit
from typing import TYPE_CHECKING, Iterable

from .matcher import FilenameMatcher
from .watcher import FileWatcher

if TYPE_CHECKING:
    from .pair import SyncPathPair
    from .types import ChangeHandler


class DirSync:
    """
    Синхронизирует изменения файлов каталога source с сохранением структуры на целевой каталог destination.
    """

    def __init__(
        self,
        handler: "ChangeHandler",
        path_pair: "SyncPathPair",
        exclude: Iterable[str],
        include: Iterable[str],
        auto_sync: bool,
        remove_empty: bool,
        force_sync: int = 0,
        force_sync_interval: float | int = 1,
    ):
        """
        Параметры:
        - handler - Слушатель изменений.
        - path_pair - Каталог источника и целевой диретории.
        - exclude - Список паттернов для исключения.
        - include - Список паттернов для включения. Не применяется к каталогам.
        - auto_sync - При запуске директории будут синхронизированы.
        - remove_empty - Удалять пустые каталоги, если в них больше нет файлов.
        - force_sync - Если установлено и больше `0`, то любая ошибка вызовет принудительную синхронизацию каталога.
                      Максимальное количество раз ограничено параметром.
        - force_sync_interval - Интервал после которого следует запустить принудительную синхронизацию.
        """
        self._handler = handler
        self._path_pair = path_pair
        self._exclude = FilenameMatcher(exclude)
        self._include = FilenameMatcher(include)
        self._auto_sync = auto_sync
        self._remove_empty = remove_empty
        self._force_sync = (
            force_sync if force_sync >= 0 else 0,
            force_sync_interval if force_sync_interval >= 0 else 0,
        )
        self._watcher: None | FileWatcher = None
        atexit.register(self.stop)

    @property
    def path_pair(self) -> "SyncPathPair":
        return self._path_pair

    @property
    def exclude(self) -> FilenameMatcher:
        return self._exclude

    @property
    def include(self) -> FilenameMatcher:
        return self._include

    @property
    def auto_sync(self) -> bool:
        return self._auto_sync

    @property
    def remove_empty(self) -> bool:
        return self._remove_empty

    @property
    def force_sync(self) -> tuple[int, float | int]:
        return self._force_sync

    @property
    def running(self) -> bool:
        return self._watcher.running if self._watcher else False

    def start(self) -> None:
        if not self._watcher:
            self._watcher = FileWatcher(
                self._handler,
                self._path_pair,
                self._exclude,
                self._include,
                self._auto_sync,
                self._remove_empty,
                self._force_sync[0],
                self._force_sync[1],
            )
        self._watcher.start()

    def stop(self) -> None:
        if self._watcher:
            self._watcher.stop()
            self._watcher = None
