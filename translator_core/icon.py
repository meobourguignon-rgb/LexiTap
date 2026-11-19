"""Иконка приложения для окна, уведомлений и трея.

Картинка берётся из assets/app.jpg — это квадратная копия image.jpg,
которую готовит tools/make_icon.py. Если файла нет, рисуем запасной
значок кодом, чтобы интерфейс не остался без иконки.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from .paths import resource_asset

LOGGER = logging.getLogger(__name__)

IMAGE_NAME = "app.jpg"
ICO_NAME = "app.ico"

_FALLBACK_BG = "#171A21"
_FALLBACK_ACCENT = "#8B7CFF"


def image_path() -> Path:
    return resource_asset(IMAGE_NAME)


def ico_path() -> Path | None:
    path = resource_asset(ICO_NAME)
    return path if path.exists() else None


def _fallback(Image: Any, ImageDraw: Any, ImageFont: Any) -> Any:
    """Простой значок «T» на акцентном фоне, если картинки нет."""
    canvas = Image.new("RGB", (256, 256), _FALLBACK_BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((8, 8, 248, 248), radius=56, fill=_FALLBACK_ACCENT)
    try:
        font = ImageFont.load_default(size=150)
    except (TypeError, ValueError):
        font = ImageFont.load_default()
    draw.text((128, 128), "T", font=font, fill="#14161C", anchor="mm")
    return canvas


def _source_image(Image: Any) -> Any:
    path = image_path()
    if path.exists():
        try:
            with Image.open(path) as handle:
                return handle.convert("RGB")
        except OSError as exc:
            LOGGER.warning("Не удалось открыть иконку %s: %s", path, exc)
    from PIL import ImageDraw, ImageFont

    return _fallback(Image, ImageDraw, ImageFont)


@lru_cache(maxsize=16)
def app_image(size: int = 64, corner_radius: int = 0) -> Any:
    """Квадратная иконка как PIL.Image (RGBA) или None, если нет Pillow."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        LOGGER.warning("Pillow не установлен, иконка недоступна")
        return None

    image = _source_image(Image).resize((size, size), Image.LANCZOS).convert("RGBA")
    if corner_radius > 0:
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=corner_radius, fill=255
        )
        image.putalpha(mask)
    return image


def ctk_image(size: int = 34, corner_radius: int = 9) -> Any:
    """Иконка для виджетов CustomTkinter (уведомление, шапка окна)."""
    try:
        import customtkinter as ctk
    except ImportError:
        return None
    image = app_image(size, corner_radius)
    if image is None:
        return None
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))


def apply_window_icon(window: Any) -> None:
    """Поставить значок окна: app.ico для заголовка и app.jpg для панели задач."""
    path = ico_path()
    if path is not None:
        try:
            window.iconbitmap(default=str(path))
        except Exception:  # noqa: BLE001 - без значка окно всё равно работает
            LOGGER.exception("Не удалось установить значок окна из app.ico")

    image = app_image(64)
    if image is None:
        return
    try:
        from PIL import ImageTk

        photo = ImageTk.PhotoImage(image)
    except Exception:  # noqa: BLE001
        return
    try:
        window.iconphoto(True, photo)
        # Ссылку нужно сохранить, иначе Tk потеряет картинку.
        setattr(window, "_translater_icon", photo)
    except Exception:  # noqa: BLE001
        LOGGER.debug("iconphoto недоступен", exc_info=True)
