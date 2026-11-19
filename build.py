"""Сборка Translater.exe через PyInstaller (onefile, windowed).

Запуск из окружения сборки (.venv):

    .venv\\Scripts\\python.exe build.py

Готовый exe попадает в корень проекта (./Translater.exe), а не в dist/.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

PYINSTALLER_ARGS = [
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "Translater",
    "--icon", "assets/app.ico",
    "--add-data", "assets;assets",
    "--add-data", "config.json:.",
    "--collect-data", "customtkinter",
    "--hidden-import", "pystray._win32",
    "translator.py",
]


def main() -> int:
    print("[1/2] Сборка Translater.exe через PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", *PYINSTALLER_ARGS],
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print("Сборка не удалась.")
        return result.returncode

    src = ROOT / "dist" / "Translater.exe"
    dst = ROOT / "Translater.exe"
    if not src.exists():
        print(f"PyInstaller не создал {src}")
        return 1
    shutil.copy2(src, dst)
    print(f"Готово: {dst}")

    for path in (ROOT / "dist", ROOT / "Translater.spec"):
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
