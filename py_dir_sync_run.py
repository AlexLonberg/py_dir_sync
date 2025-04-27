import logging
import pathlib
import subprocess
from typing import AbstractSet

from py_dir_sync import DirSync, SyncPathPair


def select_folder() -> None | str:
    """
    Запускаем PowerShell скрипт для выбора папки
    """
    ps_script = """
    Add-Type -AssemblyName System.Windows.Forms
    $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
    $folderBrowser.ShowNewFolderButton = $false

    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    if ($folderBrowser.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
        Write-Output $folderBrowser.SelectedPath
    }
    """
    result = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            # "-ExecutionPolicy",
            # "Bypass",
            "-Command",
            ps_script,
        ],
        capture_output=True,
        encoding="utf-8",
        text=True,
        creationflags=0x08000000,
    )

    folder_path = result.stdout.strip()
    if len(folder_path) > 0:
        return pathlib.Path(folder_path).as_posix()
    return None


def handler(
    created: None | set[pathlib.Path] = None,
    modified: None | set[pathlib.Path] = None,
    moved: None | AbstractSet[tuple[pathlib.PurePath, pathlib.Path]] = None,
    deleted: None | AbstractSet[pathlib.PurePath] = None,
    error: None | Exception = None,
) -> None:
    logging.info("event")
    if created:
        logging.info(f"created {created}")
    if modified:
        logging.info(f"modified {modified}")
    if moved:
        logging.info(f"moved {moved}")
    if deleted:
        logging.info(f"deleted {deleted}")
    if error:
        logging.info(f"error {error}")
    logging.info("")


help = """
Живая демонстрация синхронизации изменения каталогов.

Демонстрационная версия устанавливает запрет для путей начинающихся с точки, например '.hidden'.
Синхронизируемые файлы ограничены расширениями .py, .json, .md, .txt.

Help:

Введите букву 's' после чего откроется окно для выбора каталога источника копирования.
Введите букву 'd' после чего откроется окно для выбора целевого каталога.

После выбора двух каталогов введите 'r' для запуска процесса синхронизации каталогов.
Изменяйте файлы первого каталога 's' и наблюдайте изменения в файловой системе каталога 'd'.

Для остановки синхронизации введите 'c'.
"""

exclude = [".*", "*/.*"]
include = ["*.py", "*.json", "*.md", "*.txt"]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info(help)
    running = False
    src = ""
    dest = ""
    pair: None | SyncPathPair = None
    ins: None | DirSync = None

    def reload():
        global pair, ins
        if not running:
            if ins:
                ins.stop()
            return
        if not src or not dest:
            return
        try:
            pair = SyncPathPair(pathlib.Path(src), pathlib.Path(dest))
        except:
            pair = None
        if pair and running:
            ins = DirSync(
                handler=handler,
                path_pair=pair,
                exclude=exclude,
                include=include,
                auto_sync=True,
                remove_empty=True,
                force_sync=3,
                force_sync_interval=2,
            )
            ins.start()

    while True:
        value = input("command: ")
        value = value.strip().lower()
        if value == "s":
            path = select_folder() or ""
            if src != path:
                src = path
                reload()
        elif value == "d":
            path = select_folder() or ""
            if dest != path:
                dest = path
                reload()
        elif value == "r":
            if not running:
                running = True
                reload()
        elif value == "c":
            if running:
                running = False
                reload()
