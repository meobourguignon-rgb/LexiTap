"""Значок приложения в системном трее (рядом с часами).

Меню повторяет горячие клавиши, поэтому переводчиком можно пользоваться
и без окна. pystray живёт в своём потоке, а действия передаются в
приложение через очередь — Tkinter нельзя трогать из чужого потока.
"""

from __future__ import annotations

import logging
from typing import Callable

from .icon import app_image

LOGGER = logging.getLogger(__name__)

TOOLTIP = "Translater — переводчик выделенного текста"


class TrayIcon:
    """Трей-значок с меню: открыть окно, перевести, выйти."""

    def __init__(
        self,
        on_show: Callable[[], None],
        on_translate_russian: Callable[[], None],
        on_translate_english: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self._on_show = on_show
        self._on_translate_russian = on_translate_russian
        self._on_translate_english = on_translate_english
        self._on_quit = on_quit
        self._icon = None

    def start(self) -> bool:
        """Показать значок; False, если pystray/Pillow недоступны."""
        try:
            import pystray
        except ImportError:
            LOGGER.warning("pystray не установлен, значок в трее недоступен")
            return False

        image = app_image(64, 12)
        if image is None:
            return False

        menu = pystray.Menu(
            pystray.MenuItem("Открыть Translater", self._action(self._on_show), default=True),
            pystray.MenuItem("Перевести на русский", self._action(self._on_translate_russian)),
            pystray.MenuItem("Перевести на английский", self._action(self._on_translate_english)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", self._action(self._on_quit)),
        )
        self._icon = pystray.Icon("translater", image, TOOLTIP, menu)
        try:
            self._icon.run_detached()
        except Exception:  # noqa: BLE001 - без трея приложение продолжает работать
            LOGGER.exception("Не удалось создать значок в трее")
            self._icon = None
            return False
        LOGGER.info("Значок в трее запущен")
        return True

    def notify(self, title: str, message: str) -> None:
        """Разовое всплывающее сообщение из трея (если система поддерживает)."""
        if self._icon is None:
            return
        try:
            self._icon.notify(message, title)
        except Exception:  # noqa: BLE001 - уведомление не критично
            LOGGER.debug("Трей-уведомление недоступно")

    def stop(self) -> None:
        if self._icon is None:
            return
        try:
            self._icon.stop()
        except Exception:  # noqa: BLE001
            LOGGER.exception("Не удалось остановить значок в трее")
        finally:
            self._icon = None

    @staticmethod
    def _action(callback: Callable[[], None]) -> Callable[..., None]:
        def handler(*_args: object) -> None:
            try:
                callback()
            except Exception:  # noqa: BLE001 - поток трея не должен падать
                LOGGER.exception("Ошибка действия в меню трея")

        return handler
