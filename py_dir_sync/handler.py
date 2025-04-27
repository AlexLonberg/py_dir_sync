import logging
import pathlib
import shutil
from typing import TYPE_CHECKING, Any, Literal

from .scheduler import Scheduler
from .utils import is_child, is_equals_by_hash, read_dir, sync_dir

if TYPE_CHECKING:
    from .filter import Filter
    from .pair import SyncPathPair
    from .types import ChangeHandler


class FileHandler:
    """
    Обработчик событий изменения файлов и записи/перемещения/удаления с диска.
    Сохраняет структуру директорий между source и destination.
    """

    def __init__(
        self,
        handler: "ChangeHandler",
        path_pair: "SyncPathPair",
        filter: "Filter",
        remove_empty: bool,
        force_sync: int,
        force_sync_interval: float | int,
    ):
        self._handler = handler
        self._path_pair = path_pair
        self._filter = filter
        self._remove_empty = remove_empty
        self._force_sync = force_sync
        self._forcesync_interval = force_sync_interval
        self._scheduler: None | Scheduler = (
            Scheduler(force_sync_interval) if force_sync > 0 else None
        )

    @property
    def path_pair(self) -> "SyncPathPair":
        return self._path_pair

    def _schedule_force_sync(self, attempt: int) -> None:
        attempt += 1
        if attempt > self._force_sync:
            return
        self._sync_rel_dir(pathlib.PurePath("."), attempt)

    def _error_handler(self, e: Exception, attempt: int = 0):
        logging.error(f"Error: {str(e)}")
        self._handler(error=e)
        if self._scheduler:
            logging.info("Scheduling force sync...")
            self._scheduler.run(self._schedule_force_sync, attempt)

    def detect_dir_for_abs_src(
        self, abs_src_path: pathlib.PurePath
    ) -> Literal[0, 1, 2]:
        try:
            rel = abs_src_path.relative_to(self._path_pair.src)
            abs = self._path_pair.dest.joinpath(rel)
            if abs.is_dir():
                return 1
            if abs.is_file():
                return 2
        except Exception as e:
            logging.warning(
                f"Не удалось определить тип файла '{abs_src_path}' относительно каталога src: '{self._path_pair.src}'"
            )
            self._error_handler(e)
        return 0

    def _sync_rel_dir(self, rel: pathlib.PurePath, attempt: int = 0) -> None:
        try:
            result = sync_dir(
                self._path_pair.src, self._path_pair.dest, rel, self._filter
            )
        except Exception as e:
            self._error_handler(e, attempt)
            return
        if (
            (result["created"] and len(result["created"]) > 0)
            or (result["modified"] and len(result["modified"]) > 0)
            or (result["deleted"] and len(result["deleted"]) > 0)
        ):
            self._handler(**result)

    def _remove_if_empty_dir(self, dir_path: pathlib.Path) -> None:
        current_dir = dir_path
        while is_child(self.path_pair.dest, current_dir):
            if any(current_dir.iterdir()):
                break
            # Если папка не пуста, вызывается исключение OSError: [WinError 145] Папка не пуста: 'C:/foo/bar/*'
            current_dir.rmdir()
            current_dir = current_dir.parent

    def sync(self) -> None:
        self._sync_rel_dir(pathlib.PurePath("."))

    def created_dir(self, src: pathlib.Path, rel: pathlib.Path) -> None:
        self._sync_rel_dir(rel)

    def created_file(self, src: pathlib.Path, rel: pathlib.Path) -> None:
        try:
            dest_path = self._path_pair.dest.joinpath(rel)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_path)
        except Exception as e:
            self._error_handler(e)
            return
        self._handler(created={dest_path})

    def modified_dir(self, src: pathlib.Path, rel: pathlib.Path) -> None:
        self._sync_rel_dir(rel)

    def modified_file(self, src: pathlib.Path, rel: pathlib.Path) -> None:
        try:
            dest_path = self._path_pair.dest.joinpath(rel)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_path)
        except Exception as e:
            self._error_handler(e)
            return
        self._handler(modified={dest_path})

    def moved_dir(
        self,
        old_src: pathlib.PurePath,
        old_rel: pathlib.PurePath,
        src: pathlib.Path,
        rel: pathlib.Path,
    ) -> None:
        try:
            old_dest_path = self._path_pair.dest.joinpath(old_rel)
            dest_path = self._path_pair.dest.joinpath(rel)
            if old_dest_path.is_dir():
                shutil.move(old_dest_path, dest_path)
                if self._remove_empty:
                    self._remove_if_empty_dir(old_dest_path.parent)
            else:
                dest_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self._error_handler(e)
            return
        self._sync_rel_dir(rel)

    def moved_file(
        self,
        old_src: pathlib.PurePath,
        old_rel: pathlib.PurePath,
        src: pathlib.Path,
        rel: pathlib.Path,
    ) -> None:
        kv: None | dict[Any, Any] = None
        try:
            old_dest_path = self._path_pair.dest.joinpath(old_rel)
            dest_path = self._path_pair.dest.joinpath(rel)
            if old_dest_path.is_file():
                if is_equals_by_hash(src, old_dest_path):
                    shutil.move(old_dest_path, dest_path)
                    if self._remove_empty:
                        self._remove_if_empty_dir(old_dest_path.parent)
                    kv = {"moved": {(old_dest_path, dest_path)}}
                else:
                    old_dest_path.unlink(missing_ok=True)
                    if self._remove_empty:
                        self._remove_if_empty_dir(old_dest_path.parent)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest_path)
                    kv = {"created": {dest_path}, "deleted": {old_dest_path}}
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest_path)
                kv = {"created": {dest_path}}
        except Exception as e:
            self._error_handler(e)
            return
        if kv:
            self._handler(**kv)

    def deleted_dir(self, src: pathlib.PurePath, rel: pathlib.PurePath) -> None:
        try:
            dest_path = self._path_pair.dest.joinpath(rel)
            _dirs, files = read_dir(self._path_pair.dest, dest_path, None)
            shutil.rmtree(dest_path, ignore_errors=True)
            if self._remove_empty:
                self._remove_if_empty_dir(dest_path.parent)
        except Exception as e:
            self._error_handler(e)
            return
        if len(files) > 0:
            self._handler(deleted=files)

    def deleted_file(self, src: pathlib.PurePath, rel: pathlib.PurePath) -> None:
        try:
            dest_path = self._path_pair.dest.joinpath(rel)
            dest_path.unlink(missing_ok=True)
            if self._remove_empty:
                self._remove_if_empty_dir(dest_path.parent)
        except Exception as e:
            self._error_handler(e)
            return
        self._handler(deleted={dest_path})
