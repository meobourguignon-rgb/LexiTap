"""Настройки приложения и их мягкий разбор.

Файл config.json лежит рядом с приложением, поэтому вся папка остаётся
переносной: копируем её на другой ПК — поведение переезжает вместе с ней.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "hotkeys": {
        "to_russian": "ctrl+alt+home",
        "to_english": "ctrl+alt+end",
        "quit": "ctrl+alt+q",
    },
    "toast": {
        "size": 400,
        "margin": 24,
        "duration_seconds": 8,
        "max_source_chars": 220,
    },
    "translation": {
        "timeout_seconds": 8,
        "max_chars": 2000,
        "providers": ["google", "mymemory"],
        "auto_send": True,
    },
    "sound": {
        "enabled": True,
        "notify_file": "notify.wav",
        "error_file": "error.wav",
    "theme_rainbow": False,
    "theme_rainbow_enabled": False,
    },
    "show_startup_hint": True,
}


@dataclass(frozen=True)
class HotkeyConfig:
    to_russian: str = "ctrl+alt+home"
    to_english: str = "ctrl+alt+end"
    quit: str = "ctrl+alt+q"


@dataclass(frozen=True)
class ToastConfig:
    size: int = 400
    margin: int = 24
    duration_seconds: float = 8.0
    max_source_chars: int = 220


@dataclass(frozen=True)
class TranslationConfig:
    timeout_seconds: float = 8.0
    max_chars: int = 2000
    providers: tuple[str, ...] = ("google", "mymemory")
    auto_send: bool = True


@dataclass(frozen=True)
class SoundConfig:
    enabled: bool = True
    notify_file: str = "notify.wav"
    error_file: str = "error.wav"


@dataclass(frozen=True)
class AppConfig:
    hotkeys: HotkeyConfig
    toast: ToastConfig
    translation: TranslationConfig
    sound: SoundConfig
    show_startup_hint: bool = True


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_text(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _as_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return default
    return max(minimum, min(maximum, int(value)))


def _as_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return default
    return max(minimum, min(maximum, float(value)))


def _as_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _as_providers(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if not isinstance(value, list):
        return default
    names = tuple(item.strip().lower() for item in value if isinstance(item, str) and item.strip())
    return names or default


def build_config(raw: Mapping[str, Any]) -> AppConfig:
    """Собрать настройки из словаря, подставляя значения по умолчанию."""
    hotkeys = _mapping(raw.get("hotkeys"))
    toast = _mapping(raw.get("toast"))
    translation = _mapping(raw.get("translation"))
    sound = _mapping(raw.get("sound"))

    return AppConfig(
        hotkeys=HotkeyConfig(
            to_russian=_as_text(hotkeys.get("to_russian"), "ctrl+alt+home"),
            to_english=_as_text(hotkeys.get("to_english"), "ctrl+alt+end"),
            quit=_as_text(hotkeys.get("quit"), "ctrl+alt+q"),
        ),
        toast=ToastConfig(
            size=_as_int(toast.get("size"), 400, 240, 800),
            margin=_as_int(toast.get("margin"), 24, 0, 200),
            duration_seconds=_as_float(toast.get("duration_seconds"), 8.0, 2.0, 60.0),
            max_source_chars=_as_int(toast.get("max_source_chars"), 220, 40, 2000),
        ),
        translation=TranslationConfig(
            timeout_seconds=_as_float(translation.get("timeout_seconds"), 8.0, 2.0, 30.0),
            max_chars=_as_int(translation.get("max_chars"), 2000, 200, 5000),
            providers=_as_providers(translation.get("providers"), ("google", "mymemory")),
            auto_send=_as_bool(translation.get("auto_send"), True),
        ),
        sound=SoundConfig(
            enabled=_as_bool(sound.get("enabled"), True),
            notify_file=_as_text(sound.get("notify_file"), "notify.wav"),
            error_file=_as_text(sound.get("error_file"), "error.wav"),
        ),
        show_startup_hint=_as_bool(raw.get("show_startup_hint"), True),
    )


def load_config(path: Path) -> AppConfig:
    """Прочитать config.json; при любой проблеме вернуть значения по умолчанию."""
    raw: Mapping[str, Any] = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            LOGGER.warning("Не удалось прочитать %s: %s", path, exc)
        else:
            if isinstance(loaded, Mapping):
                raw = loaded
            else:
                LOGGER.warning("Ожидался объект JSON в %s, получено %s", path, type(loaded).__name__)
    return build_config(raw)


def write_default_config(path: Path) -> None:
    """Создать config.json с настройками по умолчанию."""
    path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_config(path: Path) -> AppConfig:
    """Создать файл настроек при первом запуске и сразу его прочитать."""
    if not path.exists():
        try:
            write_default_config(path)
            LOGGER.info("Создан файл настроек %s", path)
        except OSError as exc:
            LOGGER.warning("Не удалось создать %s: %s", path, exc)
    return load_config(path)
