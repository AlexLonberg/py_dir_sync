import atexit
import logging
import pathlib
from typing import TYPE_CHECKING

from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from .filter import Filter
from .handler import FileHandler
from .utils import path_to_str

if TYPE_CHECKING:
    from .matcher import FilenameMatcher
    from .pair import SyncPathPair
    from .types import ChangeHandler


class FileWatchHandler(FileSystemEventHandler):
    def __init__(self, filter: Filter, handler: FileHandler):
        self._filter = filter
        self._handler = handler

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent):
        try:
            path = pathlib.Path(path_to_str(event.src_path))
            if rel := self._filter.match(event.is_directory, path):
                if event.is_directory:
                    self._handler.created_dir(path, rel)
                else:
                    self._handler.created_file(path, rel)
        except Exception as e:
            logging.error(f"Error handling created event: {e}")

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent):
        try:
            path = pathlib.Path(path_to_str(event.src_path))
            if rel := self._filter.match(event.is_directory, path):
                if event.is_directory:
                    self._handler.modified_dir(path, rel)
                else:
                    self._handler.modified_file(path, rel)
        except Exception as e:
            logging.error(f"Error handling modified event: {e}")

    def on_moved(self, event: DirMovedEvent | FileMovedEvent):
        try:
            src = pathlib.PurePath(path_to_str(event.src_path))
            dest = pathlib.Path(path_to_str(event.dest_path))
            src_rel = self._filter.match(event.is_directory, src)
            dest_rel = self._filter.match(event.is_directory, dest)
            if dest_rel:
                # Оба пути доступны, значит перемещаем
                if src_rel:
                    if event.is_directory:
                        self._handler.moved_dir(src, src_rel, dest, dest_rel)
                    else:
                        self._handler.moved_file(src, src_rel, dest, dest_rel)
                # Если файл был перемещен из-за пределов недоступной области, то он фактически создается
                elif event.is_directory:
                    self._handler.created_dir(dest, dest_rel)
                else:
                    self._handler.created_file(dest, dest_rel)
            # Новое расположение не подходит - это удаление
            elif src_rel:
                if event.is_directory:
                    self._handler.deleted_dir(src, src_rel)
                else:
                    self._handler.deleted_file(src, src_rel)
        except Exception as e:
            logging.error(f"Error handling moved event: {e}")

    def on_deleted(self, event: DirDeletedEvent | FileDeletedEvent):
        # NOTE У этого события неверное свойство is_directory, вероятно из-за отсутствия файла после события удаления
        try:
            path = pathlib.PurePath(path_to_str(event.src_path))
            dir_or_file = self._handler.detect_dir_for_abs_src(path)
            if dir_or_file == 0:
                return
            is_dir = dir_or_file == 1
            if rel := self._filter.match(is_dir, path):
                if is_dir:
                    self._handler.deleted_dir(path, rel)
                else:
                    self._handler.deleted_file(path, rel)
        except Exception as e:
            logging.error(f"Error handling deleted event: {e}")


class FileWatcher:
    def __init__(
        self,
        handler: "ChangeHandler",
        path_pair: "SyncPathPair",
        exclude: "FilenameMatcher",
        include: "FilenameMatcher",
        auto_sync: bool,
        remove_empty: bool,
        force_sync: int,
        force_sync_interval: float | int,
    ):
        self._filter = Filter(path_pair.src, exclude, include)
        self._handler = FileHandler(
            handler,
            path_pair,
            self._filter,
            remove_empty,
            force_sync,
            force_sync_interval,
        )
        self._watch_handler = FileWatchHandler(self._filter, self._handler)
        self._auto_sync = auto_sync
        self._observer = None
        self._running = False
        atexit.register(self.stop)

    @property
    def path_pair(self) -> "SyncPathPair":
        return self._handler.path_pair

    @property
    def auto_sync(self) -> bool:
        return self._auto_sync

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            logging.warning("Watcher is already running")
            return
        self._observer = Observer()
        self._observer.schedule(
            self._watch_handler, self.path_pair.src.as_posix(), recursive=True
        )
        self._observer.start()
        self._running = True
        logging.info("File watcher started")
        if self._auto_sync:
            self._handler.sync()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._observer:
            observer = self._observer
            self._observer = None
            observer.stop()
            observer.join()
        logging.info("File watcher stopped")
