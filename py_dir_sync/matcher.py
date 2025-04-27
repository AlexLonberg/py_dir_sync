from fnmatch import fnmatch
from typing import Iterable

from .utils import validate_strings


# TODO Версия 3.12 не поддерживает pathlib.PurePath.full_match() который есть в 3.13 https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.match
#      На текущий момент удобнее использовать fnmatch, так как PurePath.match() не может работать с любой глубиной пути.
class FilenameMatcher:
    def __init__(self, patterns: None | Iterable[str]):
        self._patterns = validate_strings(patterns) if patterns else None

    def empty(self) -> bool:
        return not self._patterns

    def exclude(self, path: str) -> bool:
        if not self._patterns:
            return False
        for pattern in self._patterns:
            if fnmatch(path, pattern):
                return True
        return False

    def include(self, path: str) -> bool:
        if not self._patterns:
            return True
        for pattern in self._patterns:
            if fnmatch(path, pattern):
                return True
        return False
