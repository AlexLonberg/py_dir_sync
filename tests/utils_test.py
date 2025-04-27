import pathlib
import shutil
from typing import Any

from py_dir_sync import (
    ChangeFiles,
    FilenameMatcher,
    Filter,
    extract_child_files,
    extract_top_dirs,
    get_path_and_parents,
    is_child,
    sync_dir,
)

# import pytest


TEMP_DIR = pathlib.Path(__file__).parent.parent.joinpath(".temp", "test")


def test__get_path_and_parents():
    assert get_path_and_parents(pathlib.Path(".")) == []
    assert get_path_and_parents(pathlib.PurePath("C:/foo/bar")) == [
        pathlib.PurePath("C:/foo/bar"),
        pathlib.PurePath("C:/foo"),
    ]
    assert get_path_and_parents(pathlib.PurePath("foo/bar")) == [
        pathlib.PurePath("foo/bar"),
        pathlib.PurePath("foo"),
    ]


def test__extract_top_dirs():
    dirs = {
        pathlib.PurePath("foo/bar"),
        pathlib.PurePath("foo"),
        pathlib.PurePath("box/fox"),
    }
    assert extract_top_dirs(dirs) == [
        pathlib.PurePath("foo"),
        pathlib.PurePath("box/fox"),
    ]


def test__is_child():
    path0 = pathlib.PurePath(".")
    path1 = pathlib.PurePath("foo")
    path2 = pathlib.PurePath("foo")
    path3 = pathlib.PurePath("foo/bar")
    assert is_child(path0, path1) == True
    assert is_child(path1, path0) == False
    assert is_child(path1, path2) == False
    assert is_child(path1, path3) == True
    assert is_child(path3, path1) == False


def test__extract_child_files():
    dirs = {pathlib.PurePath("foo")}
    child = {pathlib.PurePath("foo/bar"), pathlib.PurePath("box/bar")}
    assert extract_child_files(dirs, child) == [pathlib.PurePath("foo/bar")]


# def test__top_created_dirs():
#     exists_dirs = {pathlib.PurePath("box")}
#     created_dirs = {
#         pathlib.PurePath("foo/bar"),
#         pathlib.PurePath("box"),
#         pathlib.PurePath("box/fox"),
#     }
#     assert top_created_dirs(exists_dirs, created_dirs) == [
#         pathlib.PurePath("foo"),
#         pathlib.PurePath("box/fox"),
#     ]


def setup__sync_dir(
    src_name: str = "src", dest_name: str = "dest"
) -> tuple[pathlib.Path, pathlib.Path]:
    src_dir = TEMP_DIR.joinpath(src_name)
    dest_dir = TEMP_DIR.joinpath(dest_name)
    shutil.rmtree(src_dir, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)
    src_dir.mkdir(parents=True, exist_ok=True)
    dest_dir.mkdir(parents=True, exist_ok=True)
    return (src_dir, dest_dir)


def create_fs_struct(root_path: pathlib.Path, struct: dict[str, Any]) -> None:
    for item in struct:
        path = root_path.joinpath(item)
        if isinstance(struct[item], dict):
            path.mkdir()
            create_fs_struct(path, struct[item])
        else:
            path.write_text(struct[item], encoding="utf-8")


def read_fs_struct(root_path: pathlib.Path) -> dict[str, Any]:
    struct: dict[str, Any] = {}
    for item in root_path.iterdir():
        if item.is_file():
            struct[item.name] = item.read_text(encoding="utf-8")
        elif item.is_dir():
            struct[item.name] = read_fs_struct(item)
    return struct


def test__sync_dir():
    # Создаем несколько файлов в разных каталогах с допустимы расширениями, и например .txt
    # Из каталога src_dir файлы с недопустимыми расширениями и папки .hidden копироваться не должны
    # Из папки dest_dir все недопустимые файлы и каталоги должны быть удалены

    src_dir, dest_dir = setup__sync_dir("src_root", "dest_root")
    create_fs_struct(
        src_dir,
        {
            ".hidden": {"file": ""},
            "note.md": "abc",
            "code.py": "import foo",
            "modified.py": "import bar",
            "settings": {"config.json": "[1]", "settings.json": "[1, 2, 3]"},
            "sub_folder": {"sub_dir": {"file.py": ""}},
        },
    )
    create_fs_struct(
        dest_dir,
        {
            ".hidden": {"file": ""},
            "note.md": "abc",
            "readme.md": "xyz",
            "code.py": "import foo",
            "modified.py": "import box",
            "settings": {"config.json": "[1]", "settings.json": "[1, 3]"},
            "folder": {"sub_dir": {"file.py": ""}},
        },
    )

    expected_struct = {
        "code.py": "import foo",
        "modified.py": "import bar",
        "settings": {"config.json": "[1]", "settings.json": "[1, 2, 3]"},
        "sub_folder": {"sub_dir": {"file.py": ""}},
    }

    expected_changed = dict(
        ChangeFiles(
            created=set(
                [
                    pathlib.Path("sub_folder/sub_dir/file.py"),
                ]
            ),
            modified=set(
                [pathlib.Path("modified.py"), pathlib.Path("settings/settings.json")]
            ),
            deleted=set(
                [
                    pathlib.PurePath(".hidden/file"),
                    pathlib.PurePath("note.md"),
                    pathlib.PurePath("readme.md"),
                    pathlib.PurePath("folder/sub_dir/file.py"),
                ]
            ),
        )
    )

    filter = Filter(
        base_abs_path=src_dir,
        exclude=FilenameMatcher([".hidden", ".hidden/*"]),
        include=FilenameMatcher(["*.py", "*.json"]),
    )

    # После синхронизации проверяем структуру на валидность допустимых файлов
    result = dict(sync_dir(src_dir, dest_dir, pathlib.PurePath("."), filter))
    actual_struct = read_fs_struct(dest_dir)

    assert result["created"] == expected_changed["created"]
    assert result["modified"] == expected_changed["modified"]
    assert result["deleted"] == expected_changed["deleted"]

    assert actual_struct == expected_struct
