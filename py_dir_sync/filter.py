import logging
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .matcher import FilenameMatcher


class Filter:
    """
    Фильтр путей к файлам и каталогам.
    """

    def __init__(
        self,
        base_abs_path: pathlib.PurePath,
        exclude: "FilenameMatcher",
        include: "FilenameMatcher",
    ):
        """
        Передайте в параметр паттернов пути для исключения. Например: `exclude = ["*/site-packages/*"]`.
        Параметр `include` игнорируется для каталогов и проверяет только пути к файлам, пример: `exclude = ["*.py"]`.
        """
        self._base_abs_path = base_abs_path
        self._exclude = exclude
        self._include = include

    @property
    def base_abs_path(self) -> pathlib.PurePath:
        return self._base_abs_path

    def match_relative_dir(self, rel: pathlib.PurePath) -> bool:
        """
        Возвращает `True` если каталог следует включить.
        """
        return not self._exclude.exclude(rel.as_posix())

    def match_relative_file(self, rel: pathlib.PurePath) -> bool:
        """
        Возвращает `True` если файл следует включить.
        """
        rel_as_posix = rel.as_posix()
        # 1. Проверка исключений
        if self._exclude.exclude(rel_as_posix):
            return False
        # 2. Проверка включений
        return self._include.include(rel_as_posix)

    def match_relative_path(self, is_dir: bool, rel: pathlib.PurePath) -> bool:
        """
        Возвращает `True` если файл или каталог(задан `is_dir`) следует включить.
        """
        return self.match_relative_dir(rel) if is_dir else self.match_relative_file(rel)

    def match[T: pathlib.PurePath | pathlib.Path](
        self, is_dir: bool, abs_path: T
    ) -> None | T:
        """
        Возвращает `None` если путь не прошел проверку допустимости или относительный путь.
        """
        try:
            # Нормализуем и проверяем путь
            relative_path = abs_path.relative_to(self._base_abs_path)
        except Exception as e:
            logging.error(f"Ошибка получения относительного пути {e}")
            return None

        if self.match_relative_path(is_dir, relative_path):
            return relative_path
        return None
