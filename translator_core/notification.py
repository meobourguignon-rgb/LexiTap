"""Карточка уведомления в стиле окон Translater (CTkMaker-дизайн).

Тёмные панели #2b2b2b/#272727, акцент #6366f1, шрифт Cascadia Code
и боковая полоса — как в MainWindow и Settings. Окно без рамки, всегда
поверх остальных, не забирает фокус и не появляется в Alt+Tab.
"""

from __future__ import annotations

import ctypes
import logging
import sys
import tkinter as tk
from ctypes import wintypes
from functools import lru_cache

import customtkinter as ctk
from typing import Any, Callable

from . import icon
from .config import ToastConfig

LOGGER = logging.getLogger(__name__)

BG = "#2b2b2b"
SURFACE = "#272727"
BORDER = "#565b5e"
ACCENT = "#6366f1"
ACCENT_HOVER = "#4f46e5"
TEXT = "#ffffff"
MUTED = "#dce4ee"
ERROR = "#ff8a8a"
FOOTER = "#a0a0a0"
FONT_FAMILY = "Cascadia Code SemiBold"


def _font(size: int, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)

GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SPI_GETWORKAREA = 0x0030
GA_ROOT = 2


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


@lru_cache(maxsize=1)
def _user32() -> Any:
    library = ctypes.WinDLL("user32", use_last_error=True)
    library.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    library.GetAncestor.restype = wintypes.HWND
    library.SystemParametersInfoW.argtypes = [
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        wintypes.UINT,
    ]
    library.SystemParametersInfoW.restype = wintypes.BOOL
    library.SetWindowRgn.argtypes = [wintypes.HWND, wintypes.HRGN, wintypes.BOOL]
    library.SetWindowPos.argtypes = [
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    return library


class ToastWindow:
    """Один переиспользуемый тост: показать / обновить / скрыть."""

    def __init__(self, root: tk.Tk, config: ToastConfig) -> None:
        self._config = config
        self._size = config.size
        self._animation = 0
        self._hide_job: str | None = None
        self._hovered = False
        self._persistent = False
        self._hwnd = 0

        ctk.set_appearance_mode("dark")

        self._window = ctk.CTkToplevel(root)
        self._window.withdraw()
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.configure(fg_color=BG)
        self._build_widgets()
        self._window.update_idletasks()
        self._prepare_native_window()

        self._window.bind("<Enter>", self._on_enter, add="+")
        self._window.bind("<Leave>", self._on_leave, add="+")

    # ------------------------------------------------------------------ вид

    def _build_widgets(self) -> None:
        frame = ctk.CTkFrame(
            self._window,
            fg_color=BG,
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
        )
        frame.pack(fill="both", expand=True)
        frame.bind("<Button-1>", lambda _event: self.hide())

        # Левая полоса — отсылка к сайдбару основных окон.
        sidebar = ctk.CTkFrame(frame, width=46, fg_color=SURFACE, corner_radius=6)
        sidebar.pack(side="left", fill="y", padx=(5, 0), pady=5)
        sidebar.pack_propagate(False)

        brand_image = icon.ctk_image(34, 9)
        if brand_image is not None:
            # Ссылку нужно держать: иначе CustomTkinter потеряет картинку.
            self._brand_image = brand_image
            brand = ctk.CTkLabel(
                sidebar,
                text="",
                image=brand_image,
                fg_color="transparent",
                width=34,
                height=34,
            )
        else:
            brand = ctk.CTkLabel(
                sidebar,
                text="T",
                fg_color=ACCENT,
                text_color="#14161c",
                corner_radius=6,
                font=_font(16, "bold"),
                width=34,
                height=34,
            )
        brand.pack(pady=(12, 8))
        ctk.CTkFrame(sidebar, width=26, height=2, fg_color="#505050").pack(pady=4)
        accent_bar = ctk.CTkFrame(sidebar, width=3, fg_color=ACCENT, corner_radius=2)
        accent_bar.pack(fill="y")

        content = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
        content.pack(side="left", fill="both", expand=True)

        header_row = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        header_row.pack(fill="x", padx=(10, 12), pady=(13, 10))

        self._header = ctk.CTkLabel(
            header_row,
            text="",
            text_color=TEXT,
            fg_color=ACCENT,
            corner_radius=6,
            font=_font(10, "bold"),
            anchor="w",
            padx=10,
            pady=5,
        )
        self._header.pack(side="left", fill="x", expand=True, padx=(0, 8))

        close_button = ctk.CTkButton(
            header_row,
            text="×",
            command=self.hide,
            width=28,
            height=28,
            corner_radius=6,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color=TEXT,
            font=_font(14, "bold"),
        )
        close_button.pack(side="right")

        self._source_title = ctk.CTkLabel(
            content,
            text="ИСХОДНЫЙ ТЕКСТ",
            text_color=FOOTER,
            font=_font(9, "bold"),
            anchor="w",
        )
        self._source_title.pack(fill="x", padx=(10, 12), pady=(0, 6))

        source_panel = ctk.CTkFrame(
            content,
            fg_color=SURFACE,
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
        )
        source_panel.pack(fill="x", padx=(10, 12))
        self._source = ctk.CTkTextbox(
            source_panel,
            height=52,
            wrap="word",
            fg_color="transparent",
            text_color=MUTED,
            font=_font(10),
            corner_radius=0,
            border_width=0,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self._source.configure(state="disabled")
        self._source.pack(fill="x", padx=9, pady=7)

        result_row = ctk.CTkFrame(content, fg_color="transparent", corner_radius=0)
        result_row.pack(fill="x", padx=(10, 12), pady=(14, 6))
        ctk.CTkLabel(
            result_row,
            text="ПЕРЕВОД",
            text_color=FOOTER,
            font=_font(9, "bold"),
            anchor="w",
        ).pack(side="left")

        result_panel = ctk.CTkFrame(
            content,
            fg_color=SURFACE,
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
        )
        result_panel.pack(fill="both", expand=True, padx=(10, 12))
        ctk.CTkFrame(
            result_panel, fg_color=ACCENT, width=3, corner_radius=2
        ).pack(side="left", fill="y", padx=(4, 0), pady=10)
        self._body = ctk.CTkTextbox(
            result_panel,
            wrap="word",
            fg_color="transparent",
            text_color=TEXT,
            font=_font(13),
            height=140,
            corner_radius=0,
            border_width=0,
            scrollbar_button_color=ACCENT,
            scrollbar_button_hover_color=ACCENT_HOVER,
        )
        self._body.configure(state="disabled")
        self._body.pack(side="left", fill="both", expand=True, padx=(8, 4), pady=7)
        self._body.bind("<MouseWheel>", self._on_wheel)
        self._body.bind("<Enter>", self._on_enter)
        self._body.bind("<Leave>", self._on_leave)

        self._footer = ctk.CTkLabel(
            content,
            text="НАВЕДИТЕ, ЧТОБЫ ПРОЧИТАТЬ  ·  КЛИК — ЗАКРЫТЬ",
            text_color=FOOTER,
            font=_font(8, "bold"),
            anchor="w",
        )
        self._footer.pack(fill="x", padx=(10, 12), pady=(10, 12))

    # ------------------------------------------------------------ нативный вид

    def _prepare_native_window(self) -> None:
        if sys.platform != "win32":
            return
        try:
            user32 = _user32()
            handle = user32.GetAncestor(self._window.winfo_id(), GA_ROOT)
            self._hwnd = int(handle or self._window.winfo_id())

            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
            get_long.argtypes = [wintypes.HWND, ctypes.c_int]
            get_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            set_long.restype = ctypes.c_ssize_t

            style = get_long(self._hwnd, GWL_EXSTYLE)
            set_long(
                self._hwnd,
                GWL_EXSTYLE,
                style | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW,
            )
        except (AttributeError, OSError):
            LOGGER.exception("Не удалось настроить нативный стиль окна")

    # ------------------------------------------------------------------ показ

    def show(
        self,
        header: str,
        preview: str,
        body: str,
        duration: float,
        error: bool = False,
    ) -> None:
        self._cancel_hide()
        self._animation += 1
        self._header.configure(text=header.upper())
        self._set_text(self._source, preview)
        self._set_text(self._body, body)
        self._body.configure(text_color=ERROR if error else TEXT)
        self._persistent = len(body.split()) > 40

        self._place()
        try:
            self._window.attributes("-alpha", 0.0)
        except tk.TclError:
            pass
        self._window.deiconify()
        self._apply_native_window_position()
        self._window.lift()
        self._fade(0.0, 0.97)
        if not self._persistent:
            self._hide_job = self._window.after(
                int(max(2.0, duration) * 1000), self._auto_hide
            )

    def hide(self) -> None:
        self._cancel_hide()
        self._persistent = False
        self._animation += 1

        def finish() -> None:
            if self._window.winfo_exists():
                self._window.withdraw()

        self._fade(0.97, 0.0, on_done=finish)

    def destroy(self) -> None:
        self._cancel_hide()
        if self._window.winfo_exists():
            self._window.destroy()

    # ------------------------------------------------------------- внутреннее

    def _set_text(self, widget: ctk.CTkTextbox, value: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")
        widget.yview_moveto(0.0)

    def _place(self) -> None:
        margin = self._config.margin
        x, y = self._bottom_right(margin)
        self._window.geometry(f"{self._size}x{self._size}+{x}+{y}")

    def _bottom_right(self, margin: int) -> tuple[int, int]:
        size = self._size
        if sys.platform == "win32":
            try:
                area = _Rect()
                if _user32().SystemParametersInfoW(
                    SPI_GETWORKAREA, 0, ctypes.byref(area), 0
                ):
                    return area.right - size - margin, area.bottom - size - margin
            except OSError:
                LOGGER.exception("Не удалось определить рабочую область экрана")
        width = self._window.winfo_screenwidth()
        height = self._window.winfo_screenheight()
        return width - size - margin, height - size - margin - 40

    def _apply_native_window_position(self) -> None:
        if not self._hwnd:
            return
        try:
            _user32().SetWindowPos(
                self._hwnd,
                wintypes.HWND(-1),
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except OSError:
            LOGGER.exception("SetWindowPos не сработал")

    def _fade(self, start: float, end: float, on_done: Callable[[], None] | None = None) -> None:
        generation = self._animation
        steps = 10

        def step(index: int) -> None:
            if generation != self._animation:
                return
            value = start + (end - start) * index / steps
            try:
                self._window.attributes("-alpha", value)
            except tk.TclError:
                return
            if index >= steps:
                if on_done is not None:
                    on_done()
                return
            self._window.after(16, step, index + 1)

        step(1)

    def _cancel_hide(self) -> None:
        if self._hide_job is not None:
            try:
                self._window.after_cancel(self._hide_job)
            except tk.TclError:
                pass
            self._hide_job = None

    def _auto_hide(self) -> None:
        self._hide_job = None
        if self._persistent:
            return
        if self._hovered:
            self._hide_job = self._window.after(1500, self._auto_hide)
            return
        self.hide()

    def _on_enter(self, _event: tk.Event) -> None:
        self._hovered = True
        self._cancel_hide()

    def _on_leave(self, _event: tk.Event) -> None:
        self._hovered = False
        if self._persistent:
            self._cancel_hide()
            return
        if self._hide_job is None:
            self._hide_job = self._window.after(2500, self._auto_hide)

    def _on_wheel(self, event: tk.Event) -> str:
        self._body.yview_scroll(int(-event.delta / 120), "units")
        return "break"
