@echo off
chcp 65001 >nul
cd /d "%~dp0"

if exist "Translater.exe" (
    start "" "Translater.exe"
    exit /b
)

set VENV=.venv
set PYW=%VENV%\Scripts\pythonw.exe

if not exist "%PYW%" (
    echo Первый запуск: создаю окружение %VENV% и ставлю зависимости...
    py -3 -m venv "%VENV%" 2>nul
    if errorlevel 1 python -m venv "%VENV%"
    if not exist "%PYW%" goto no_python
    "%VENV%\Scripts\python.exe" -m pip install --upgrade pip --quiet
    "%VENV%\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto deps_fail
)

start "" "%PYW%" "%~dp0translator.py"
exit /b

:no_python
echo Python 3 не найден.
echo Установите Python 3.10+ с https://www.python.org/downloads/windows/
echo либо соберите один файл: python build.py (см. README)
pause
exit /b 1

:deps_fail
echo Не удалось установить зависимости в %VENV%.
echo Проверьте интернет и запустите start.bat снова.
pause
exit /b 1
