@echo off
REM Путь к каталогу приложения
set APP_DIR=%~dp0

REM Путь к виртуальной среде
set VENV_DIR=%APP_DIR%\.venv

REM Перейти в каталог приложения
cd %APP_DIR%

REM Активировать виртуальную среду
call %VENV_DIR%\Scripts\activate

REM Запустить приложение
python ./py_dir_sync_run.py

REM Деактивировать виртуальную среду - Эта строка сразу закроет консоль.
REM deactivate

pause
