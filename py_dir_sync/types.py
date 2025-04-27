import pathlib
from typing import AbstractSet, Protocol, TypedDict


class ChangeFiles(TypedDict, total=True):
    created: None | set[pathlib.Path]
    modified: None | set[pathlib.Path]
    deleted: (
        None
        | set[pathlib.Path | pathlib.PurePath]
        | set[pathlib.PurePath]
        | set[pathlib.Path]
    )


class ChangeHandler(Protocol):
    """
    Обработчик событий изменения файлов.
    """

    def __call__(
        self,
        created: None | set[pathlib.Path] = None,
        modified: None | set[pathlib.Path] = None,
        moved: None | AbstractSet[tuple[pathlib.PurePath, pathlib.Path]] = None,
        deleted: None | AbstractSet[pathlib.PurePath] = None,
        error: None | Exception = None,
    ) -> None: ...
