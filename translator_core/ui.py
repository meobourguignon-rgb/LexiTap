"""Экраны Translater, сгенерированные CTkMaker.

Здесь только разметка и внешний вид: ни переводов, ни конфигурации, ни
системных вызовов. Всем этим занимается ``translator_core.app``, который
находит виджеты по именам и подменяет команды кнопок.

Файл условно «машинный»: при перегенерации из CTkMaker классы ``MainWindow``
и ``Settings`` перезаписываются, поэтому ручные правки поведения стоит
держать в ``app.py``, а в разметке — только то, что нельзя выразить в
редакторе (перенос длинных подписей, размеры кнопок).
"""

from __future__ import annotations

import customtkinter as ctk
from PIL import Image

from scripts.button_exit_py import ButtonExitPy
from scripts.home_py import HomePy
from scripts.settings_py import ButtonSettingsPy, SettingsPy

from .paths import resource_asset


def _asset(name: str) -> str:
    """Абсолютный путь к картинке дизайна (работает и из .exe)."""
    return str(resource_asset(f"images/{name}"))



class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Translater")
        self.geometry("800x600")
        self._script_0 = ButtonSettingsPy()
        self._script_1 = HomePy()
        self._script_2 = SettingsPy()
        self._script_3 = ButtonExitPy()
        self._build_ui()
        self._script_0.widget = self.main_window
        self._script_1.widget = self.main
        self._script_2.widget = self.settings
        self._script_3.widget = self.exit
        self._script_0.on_start()
        self._script_1.on_start()
        self._script_2.on_start()
        self._script_3.on_start()
        self.protocol("WM_DELETE_WINDOW", lambda: (self._script_0.on_close(), self._script_1.on_close(), self._script_2.on_close(), self._script_3.on_close(), self.destroy()))

    def _build_ui(self):
        self.main_window = ctk.CTkFrame(
            self,
            width=551,
            height=436,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#2b2b2b',
        )
        self.main_window.place(x=125, y=67)

        self.departments = ctk.CTkFrame(
            self.main_window,
            width=129,
            height=452,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#272727',
        )
        self.departments.place(x=0, y=-12)

        self.main = ctk.CTkButton(
            self.departments,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Home',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('house.png')), dark_image=Image.open(_asset('house.png')), size=(20, 20)),
            command=self._script_1.open_main,
        )
        self.main.place(x=9, y=51)

        self.settings = ctk.CTkButton(
            self.departments,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Settings',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('monitor-cog.png')), dark_image=Image.open(_asset('monitor-cog.png')), size=(20, 20)),
            command=self._script_2.open_settings,
        )
        self.settings.place(x=11, y=92)

        self.exit = ctk.CTkButton(
            self.departments,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Exit',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('door-open.png')), dark_image=Image.open(_asset('door-open.png')), size=(20, 20)),
            command=self._script_3.exit_app,
        )
        self.exit.place(x=11, y=137)

        self.separator = ctk.CTkFrame(
            self.departments,
            width=110,
            height=3,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#505050',
        )
        self.separator.place(x=10, y=185)

        self.icon = ctk.CTkLabel(
            self.departments,
            width=96,
            height=227,
            fg_color='transparent',
            text='',
            image=ctk.CTkImage(light_image=Image.open(_asset('photo_2026-08-09_17-54-54.jpg')), dark_image=Image.open(_asset('photo_2026-08-09_17-54-54.jpg')), size=(96, 227)),
            compound="left",
        )
        self.icon.place(x=17, y=207)

        self.label_4 = ctk.CTkLabel(
            self.departments,
            width=110,
            corner_radius=0,
            fg_color='transparent',
            text='Hello, World!',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_4.place(x=10, y=18)

        self.label_6 = ctk.CTkLabel(
            self.main_window,
            width=386,
            height=403,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Translater - это быстрый переводчик текста прямо в приложениях.\n\nСкройте окно в трей, чтобы переводчик продолжал работать в фоне. Для перевода нужен интернет.',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            justify='left',
            wraplength=356,
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="bold", slant="roman", underline=True),
        )
        self.label_6.place(x=143, y=16)



class Settings(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Settings")
        self.geometry("800x600")
        self._script_0 = HomePy()
        self._script_1 = SettingsPy()
        self._script_2 = ButtonExitPy()
        self._build_ui()
        self._script_0.widget = self.button_1
        self._script_1.widget = self.button_2
        self._script_2.widget = self.button_3
        self._script_0.on_start()
        self._script_1.on_start()
        self._script_2.on_start()
        self.protocol("WM_DELETE_WINDOW", lambda: (self._script_0.on_close(), self._script_1.on_close(), self._script_2.on_close(), self.destroy()))

    def _build_ui(self):
        self.frame_1 = ctk.CTkFrame(
            self,
            width=551,
            height=436,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#2b2b2b',
        )
        self.frame_1.place(x=125, y=74)

        self.frame_2 = ctk.CTkFrame(
            self.frame_1,
            width=129,
            height=452,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#272727',
        )
        self.frame_2.place(x=0, y=-12)

        self.button_1 = ctk.CTkButton(
            self.frame_2,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Home',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('house.png')), dark_image=Image.open(_asset('house.png')), size=(20, 20)),
            command=self._script_0.open_main,
        )
        self.button_1.place(x=9, y=51)

        self.button_2 = ctk.CTkButton(
            self.frame_2,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Settings',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('monitor-cog.png')), dark_image=Image.open(_asset('monitor-cog.png')), size=(20, 20)),
            command=self._script_1.open_settings,
        )
        self.button_2.place(x=11, y=92)

        self.button_3 = ctk.CTkButton(
            self.frame_2,
            width=107,
            height=22,
            corner_radius=3,
            border_width=0,
            border_color='#efefef',
            text='Exit',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
            image=ctk.CTkImage(light_image=Image.open(_asset('door-open.png')), dark_image=Image.open(_asset('door-open.png')), size=(20, 20)),
            command=self._script_2.exit_app,
        )
        self.button_3.place(x=11, y=137)

        self.frame_3 = ctk.CTkFrame(
            self.frame_2,
            width=110,
            height=3,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#505050',
        )
        self.frame_3.place(x=10, y=185)

        self.image_1 = ctk.CTkLabel(
            self.frame_2,
            width=96,
            height=227,
            fg_color='transparent',
            text='',
            image=ctk.CTkImage(light_image=Image.open(_asset('photo_2026-08-09_17-54-54.jpg')), dark_image=Image.open(_asset('photo_2026-08-09_17-54-54.jpg')), size=(96, 227)),
            compound="left",
        )
        self.image_1.place(x=17, y=207)

        self.label_1 = ctk.CTkLabel(
            self.frame_2,
            width=110,
            corner_radius=0,
            fg_color='transparent',
            text='Hello, World!',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_1.place(x=10, y=18)

        self.label_3 = ctk.CTkLabel(
            self.frame_1,
            width=348,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Звук уведомлений',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_3.place(x=135, y=15)

        self.checkbox_1 = ctk.CTkCheckBox(
            self.frame_1,
            width=24,
            height=20,
            corner_radius=6,
            border_width=3,
            border_color='#949A9F',
            fg_color='#6366f1',
            hover_color='#4f46e5',
            checkmark_color='#e5e5e5',
            text='',
            text_color='#dce4ee',
            text_color_disabled='#737373',
        )
        self.checkbox_1.place(x=500, y=17)

        self.label_4 = ctk.CTkLabel(
            self.frame_1,
            width=348,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Автоотправка (Enter)',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_4.place(x=135, y=62)

        self.checkbox_2 = ctk.CTkCheckBox(
            self.frame_1,
            width=24,
            height=20,
            corner_radius=6,
            border_width=3,
            border_color='#949A9F',
            fg_color='#6366f1',
            hover_color='#4f46e5',
            checkmark_color='#e5e5e5',
            text='',
            text_color='#dce4ee',
            text_color_disabled='#737373',
        )
        self.checkbox_2.place(x=500, y=65)

        self.label_6 = ctk.CTkLabel(
            self.frame_1,
            width=348,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Подсказка при запуске',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_6.place(x=135, y=115)

        self.checkbox_3 = ctk.CTkCheckBox(
            self.frame_1,
            width=24,
            height=20,
            corner_radius=6,
            border_width=3,
            border_color='#949A9F',
            fg_color='#6366f1',
            hover_color='#4f46e5',
            checkmark_color='#e5e5e5',
            text='',
            text_color='#dce4ee',
            text_color_disabled='#737373',
        )
        self.checkbox_3.place(x=500, y=115)

        self.frame_4 = ctk.CTkFrame(
            self.frame_1,
            width=391,
            height=3,
            corner_radius=6,
            border_width=0,
            border_color='#565b5e',
            fg_color='#505050',
        )
        self.frame_4.place(x=143, y=173)

        self.label_9 = ctk.CTkLabel(
            self.frame_1,
            width=240,
            height=28,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Переводит выделенный текст',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            justify='left',
            wraplength=220,
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_9.place(x=135, y=200)

        self.button_4 = ctk.CTkButton(
            self.frame_1,
            width=126,
            height=28,
            corner_radius=0,
            border_width=0,
            border_color='#efefef',
            text='CTRL + ALT + HOME',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.button_4.place(x=381, y=200)

        self.label_10 = ctk.CTkLabel(
            self.frame_1,
            width=240,
            height=44,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Переводит выделенный текст на английский и отправляет его',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            justify='left',
            wraplength=240,
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_10.place(x=135, y=243)

        self.button_5 = ctk.CTkButton(
            self.frame_1,
            width=126,
            height=28,
            corner_radius=0,
            border_width=0,
            border_color='#efefef',
            text='CTRL + ALT + END',
            text_color='#ffffff',
            fg_color='#6366f1',
            hover_color='#4e50bd',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.button_5.place(x=381, y=251)

        self.label_12 = ctk.CTkLabel(
            self.frame_1,
            width=373,
            height=94,
            corner_radius=0,
            fg_color='transparent',
            bg_color='#6366f1',
            text='Нажмите на сочетание, чтобы изменить его.\nEsc — отменить изменение.',
            text_color='#ffffff',
            text_color_disabled='#a0a0a0',
            compound='left',
            font=ctk.CTkFont(family='Cascadia Code SemiBold', size=13, weight="normal", slant="roman"),
        )
        self.label_12.place(x=135, y=309)
