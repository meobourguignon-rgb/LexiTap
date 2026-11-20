"""Точка входа Translater.

Здесь намеренно нет логики: только выбор темы и запуск контроллера.
Разметка живёт в ``translator_core/ui.py``, поведение — в
``translator_core/app.py``, системные возможности — в остальных модулях
``translator_core``.
"""

from __future__ import annotations

import customtkinter as ctk

from translator_core.app import TranslatorApp


def main() -> None:
    ctk.set_appearance_mode("dark")
    TranslatorApp().start()


if __name__ == "__main__":
    main()
