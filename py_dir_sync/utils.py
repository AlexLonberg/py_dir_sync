import hashlib
import logging
import os
import pathlib
import shutil
from typing import TYPE_CHECKING, Any, Iterable

from .types import ChangeFiles

if TYPE_CHECKING:
    from .filter import Filter

_DOT_PATH = pathlib.Path(".")


def validate_strings(items: Iterable[Any]) -> None | set[str]:
    """
    Возвращает набор уникальных непустых строк или `None`, если ни одной строки не найдено.
    """
    uniq = set[str]()
    for item in items:
        if isinstance(item, str) and (trimmed := item.strip()):
            uniq.add(trimmed)
    return uniq if len(uniq) > 0 else None


def validate_path_pair(
    src_abs_dir_path: pathlib.Path, dest_abs_dir_path: pathlib.Path
) -> tuple[pathlib.Path, pathlib.Path]:
    """
    Проверяет что оба аргумента являются абсолютными путями к каталогам, не вложены друг в друга и существуют на диске.

    Исключения:
    - `FileNotFoundError`: Путь не существует
    - `ValueError`: Если нарушены условия валидации
    """
    try:
        normalize_src = src_abs_dir_path.resolve(strict=True)
        normalize_dest = dest_abs_dir_path.resolve(strict=True)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Путь не существует: {e.filename}") from None

    if not normalize_src.is_absolute() or not normalize_dest.is_absolute():
        raise ValueError(
            f"Оба пути src:'{src_abs_dir_path}' и dest:'{dest_abs_dir_path}' должны быть абсолютными"
        )
    if not normalize_src.is_dir():
        raise ValueError(f"src:'{src_abs_dir_path}' не является каталогом")
    if not normalize_dest.is_dir():
        raise ValueError(f"dest:'{dest_abs_dir_path}' не является каталогом")
    if normalize_src.is_relative_to(normalize_dest) or normalize_dest.is_relative_to(
        normalize_src
    ):
        raise ValueError(
            f"src:'{src_abs_dir_path}' и dest:'{dest_abs_dir_path}' не могут быть вложенными или равными путями"
        )
    return (normalize_src, normalize_dest)


def path_to_str(path: str | bytes) -> str:
    """
    Проверяет является ли путь `bytes` и приводит к строке.
    """
    return path.decode("utf-8", errors="replace") if isinstance(path, bytes) else path


def file_hash(abs_file_path: str | os.PathLike[str]) -> None | bytes:
    """
    Хеш файла или `None`, если не удалось прочитать файл.
    """
    hash_obj = hashlib.md5()
    try:
        with open(abs_file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_obj.update(chunk)
        return hash_obj.digest()
    except Exception as e:
        logging.error(f"Error reading file {abs_file_path}: {e}")
        return None


def is_equals_by_hash(
    abs_file_path1: pathlib.Path, abs_file_path2: pathlib.Path
) -> bool:
    """
    Сравнивает два файла по хешу. Если один из файлов не удалось прочитать, возвращает `False`.
    """
    try:
        if abs_file_path1.stat().st_size != abs_file_path2.stat().st_size:
            return False
    except:
        return False
    hash1 = file_hash(abs_file_path1)
    if not hash1:
        return False
    return hash1 == file_hash(abs_file_path2)


def get_path_and_parents[T: pathlib.PurePath | pathlib.Path](path: T) -> list[T]:
    """
    Возвращает массив пути и всех его родительских директорий не включая `"."`.

    В основном эта функция должна применяться к относительным путям. Для пути `"C:/foo/bar"` не вернет корень диска
    `C:/` и остановиться на `"C:/foo"`
    """
    return [] if path == _DOT_PATH else [path, *path.parents[:-1]]


def is_child[T: pathlib.PurePath | pathlib.Path](
    maybe_parent: T, maybe_child: T
) -> bool:
    """
    Является ли путь `maybe_child` дочерним относительно `maybe_parent`.
    """
    return maybe_child.is_relative_to(maybe_parent) and maybe_child != maybe_parent


def extract_top_dirs[T: pathlib.PurePath | pathlib.Path](paths: set[T]) -> list[T]:
    """
    Извлекает из списка каталоги верхнего уровня.
    Пути к каталогам могут быть только списком относительных или абсолютных путей, смешивание не допускается.
    """
    sorted_paths: list[T] = sorted(paths, key=lambda p: (len(p.parts), p.as_posix()))
    top_dirs = list[T]()
    for path in sorted_paths:
        if not any(is_child(top, path) for top in top_dirs):
            top_dirs.append(path)
    return top_dirs


def extract_child_files[T: pathlib.PurePath | pathlib.Path](
    dirs: set[T], files: set[T]
) -> list[T]:
    """
    Извлекает все файлы `files`, которые являются дочерними по отношению к одному из каталогов `dirs`.
    Пути к каталогам и файлам могут быть только абсолютными или относительными, смешивание не допускается.
    """
    child_files = list[T]()
    for file in files:
        if any(is_child(top, file) for top in dirs):
            child_files.append(file)
    return child_files


def read_dir(
    base_abs_path: pathlib.PurePath, abs_path: pathlib.Path, filter: "None | Filter"
) -> tuple[set[pathlib.Path], set[pathlib.Path]]:
    """
    Собирает список файлов в каталоге `abs_path` и возвращает список путей относительно `base_abs_path`.
    Первым элементом кортежа возвращаются каталоги, вторым файлы.
    `base_abs_path` должен быть родительским или равным `abs_path`.
    """
    dir_paths = set[pathlib.Path]()
    file_paths = set[pathlib.Path]()
    # При отсутствии пути walk() не вызывает ошибок и просто ничего не делает
    for root, dirs, files in abs_path.walk(on_error=None):
        rel_root = root.relative_to(base_abs_path)
        for dir in dirs:
            rel_dir = rel_root.joinpath(dir)
            if not filter or filter.match_relative_dir(rel_dir):
                dir_paths.add(rel_dir)
        for file in files:
            rel_file = rel_root.joinpath(file)
            if not filter or filter.match_relative_file(rel_file):
                file_paths.add(rel_file)
    return (dir_paths, file_paths)


def sync_dir(
    base_src_abs_dir: pathlib.Path,
    base_dest_abs_dir: pathlib.Path,
    rel_path: pathlib.PurePath,
    src_filter: "Filter",
) -> ChangeFiles:
    """
    Синхронизирует каталог `base_src_abs_dir/rel_path` с каталогом `base_dest_abs_dir/rel_path`.
    Возвращает списки созданных, модифицированных и удаленных файлов.

    Пути возвращаются относительно `base_src_abs_dir`, но ограничить каталог синхронизации можно через передачу
    дочернего `rel_path`. Для полной синхронизации используйте пустой путь `pathlib.PurePath(".")`.
    """
    src_abs_dir = base_src_abs_dir.joinpath(rel_path)
    dest_abs_dir = base_dest_abs_dir.joinpath(rel_path)
    # Собираем допустимые файлы в src_abs_dir
    src_dirs, src_files = read_dir(base_src_abs_dir, src_abs_dir, src_filter)
    # Собираем все файлы в dest_abs_dir
    dest_dirs, dest_files = read_dir(base_dest_abs_dir, dest_abs_dir, None)

    # Определяем каталоги которых нет в src_dirs и извлекаем каталоги верхнего уровня
    all_deleted_dirs = dest_dirs - src_dirs
    deleted_dirs = set(extract_top_dirs(all_deleted_dirs))
    # Известные удаленные файлы
    deleted_files_in_dirs = set(extract_child_files(deleted_dirs, dest_files))
    # Удаляем каталоги верхнего уровня и зависящие от них файлы
    for dir in deleted_dirs:
        shutil.rmtree(base_dest_abs_dir.joinpath(dir), ignore_errors=True)

    # Определяем оставшиеся файлы которых нет в src_dirs.
    dest_files = dest_files - deleted_files_in_dirs
    deleted_files = dest_files - src_files
    for file in deleted_files:
        base_dest_abs_dir.joinpath(file).unlink(missing_ok=True)

    # В каталоге могут оказаться файлы, которые не проходят фильтр. Обрабатываем последние файлы, которые не подходят.
    dest_files = dest_files - deleted_files
    wrong_files = set[pathlib.Path]()
    for file in dest_files:
        if not src_filter.match_relative_file(file):
            wrong_files.add(file)
            base_dest_abs_dir.joinpath(file).unlink(missing_ok=True)

    # Актуальные оставшиеся файлы, которые могут быть полностью похожими или модифицированными.
    # Список этих файлов точно есть в src_files
    dest_files = dest_files - wrong_files

    # Все удаленные файлы
    deleted = deleted_files_in_dirs | deleted_files | wrong_files

    created_dirs = set[pathlib.Path]()
    created = set[pathlib.Path]()
    modified = set[pathlib.Path]()
    # Проходимся по всем файлам которые нужно скопировать.
    # Файлы имеющиеся в dest_files проверяем на необходимость копирования по хешу.
    # Если файлы на тех же местах, но не подходят по хешу, отнесем их к модифицированным.
    for file in src_files:
        src_abs_path = base_src_abs_dir.joinpath(file)
        dest_abs_path = base_dest_abs_dir.joinpath(file)
        has_file = file in dest_files
        if has_file and is_equals_by_hash(src_abs_path, dest_abs_path):
            continue
        parent_dir = file.parent
        if (parent_dir != _DOT_PATH) and parent_dir not in created_dirs:
            base_dest_abs_dir.joinpath(parent_dir).mkdir(parents=True, exist_ok=True)
            created_dirs.add(parent_dir)
        shutil.copy2(src_abs_path, dest_abs_path)
        if has_file:
            modified.add(file)
        else:
            created.add(file)

    # Этого не должно случиться, но на всякий случай проверим:
    # не осталось ли у нас подозрительных файлов попавших в dest_files
    suspicious_files = dest_files - src_files
    if len(suspicious_files) > 0:
        logging.warning(
            f"Удаление файлов не попавших в 'dest' при сканировании каталога, но отсутствующих в 'src'"
        )
        for file in suspicious_files:
            deleted.add(file)
            base_dest_abs_dir.joinpath(file).unlink(missing_ok=True)

    # На всякий случай проверим не занесли ли мы созданные, модифицированные или равные файлы в удаленные
    deleted = deleted - src_files

    return ChangeFiles(
        created=(created if len(created) > 0 else None),
        modified=(modified if len(modified) > 0 else None),
        deleted=(deleted if len(deleted) > 0 else None),
    )
