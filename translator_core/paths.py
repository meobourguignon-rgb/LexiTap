"""Пути, которые одинаково работают из исходников и из собранного .exe."""

from __future__ import annotations

import sys
from pathlib import Path


def _application_dir() -> Path:
    """Папка, рядом с которой лежит config.json и куда можно писать."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


APP_DIR = _application_dir()
# В onefile-сборке PyInstaller распаковывает данные в sys._MEIPASS.
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))

CONFIG_PATH = APP_DIR / "config.json"
ASSETS_DIR = APP_DIR / "assets"
LOG_DIR = APP_DIR / "logs"


def resource_asset(name: str) -> Path:
    """Сначала ищем файл рядом с приложением, затем во встроенных ресурсах."""
    local = ASSETS_DIR / name
    if local.exists():
        return local
    return RESOURCE_DIR / "assets" / name
