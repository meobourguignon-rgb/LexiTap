"""Глобальные горячие клавиши через RegisterHotKey.

Слушатель живёт в отдельном потоке со своей очередью сообщений Windows:
RegisterHotKey без окна привязывает WM_HOTKEY к потоку, поэтому цикла
GetMessage достаточно и не нужен скрытый HWND.
"""

from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable, Iterable

LOGGER = logging.getLogger(__name__)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HOTKEY_ID_BASE = 0xB000

VK_BY_NAME: dict[str, int] = {
    "home": 0x24,
    "end": 0x23,
    "insert": 0x2D,
    "delete": 0x2E,
    "pageup": 0x21,
    "pagedown": 0x22,
    "tab": 0x09,
    "space": 0x20,
    "escape": 0x1B,
    "enter": 0x0D,
}
VK_BY_NAME.update({f"f{number}": 0x6F + number for number in range(1, 13)})
VK_BY_NAME.update({chr(code).lower(): code for code in range(0x30, 0x3A)})
VK_BY_NAME.update({chr(code).lower(): code for code in range(0x41, 0x5B)})

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}


@dataclass(frozen=True)
class HotkeyBinding:
    action: str
    spec: str
    mods: int
    vk: int


def parse_hotkey(spec: str) -> tuple[int, int]:
    """'ctrl+alt+home' → (битовая маска модификаторов, виртуальный код)."""
    parts = [part.strip().lower() for part in spec.split("+") if part.strip()]
    if not parts:
        raise ValueError("пустое сочетание клавиш")

    mods = 0
    key: int | None = None
    for part in parts:
        if part in _MODIFIERS:
            mods |= _MODIFIERS[part]
        elif part in VK_BY_NAME:
            if key is not None:
                raise ValueError(f"в сочетании {spec!r} больше одной клавиши")
            key = VK_BY_NAME[part]
        else:
            raise ValueError(f"неизвестная клавиша {part!r} в {spec!r}")

    if key is None:
        raise ValueError(f"в сочетании {spec!r} нет клавиши, только модификаторы")
    if mods == 0:
        raise ValueError(f"сочетание {spec!r} без модификатора перехватило бы обычную клавишу")
    return mods, key


def build_binding(action: str, spec: str) -> HotkeyBinding:
    mods, vk = parse_hotkey(spec)
    return HotkeyBinding(action=action, spec=spec, mods=mods, vk=vk)


@lru_cache(maxsize=1)
def _user32() -> Any:
    library = ctypes.WinDLL("user32", use_last_error=True)
    library.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    library.RegisterHotKey.restype = wintypes.BOOL
    library.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    library.UnregisterHotKey.restype = wintypes.BOOL
    library.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    library.GetMessageW.restype = ctypes.c_int
    library.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    library.PostThreadMessageW.restype = wintypes.BOOL
    return library


class HotkeyListener:
    """Регистрирует сочетания и передаёт названия действий в callback."""

    def __init__(
        self,
        bindings: Iterable[HotkeyBinding],
        on_hotkey: Callable[[str], None],
    ) -> None:
        self._bindings = list(bindings)
        self._on_hotkey = on_hotkey
        self._actions: dict[int, str] = {}
        self._thread = threading.Thread(target=self._run, name="hotkey-listener", daemon=True)
        self._ready = threading.Event()
        self._thread_id = 0
        self.failures: list[str] = []

    def start(self) -> None:
        self._thread.start()
        self._ready.wait(timeout=3.0)

    def stop(self) -> None:
        if self._thread_id:
            _user32().PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

    def _run(self) -> None:
        user32 = _user32()
        self._thread_id = ctypes.WinDLL("kernel32").GetCurrentThreadId()

        for index, binding in enumerate(self._bindings):
            hotkey_id = HOTKEY_ID_BASE + index
            if user32.RegisterHotKey(None, hotkey_id, binding.mods | MOD_NOREPEAT, binding.vk):
                self._actions[hotkey_id] = binding.action
            else:
                LOGGER.warning("Сочетание %s занято другим приложением", binding.spec)
                self.failures.append(binding.spec)

        self._ready.set()

        message = wintypes.MSG()
        while True:
            result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result <= 0:
                break
            if message.message == WM_HOTKEY:
                action = self._actions.get(int(message.wParam))
                if action is None:
                    continue
                try:
                    self._on_hotkey(action)
                except Exception:  # noqa: BLE001 - слушатель не должен умирать
                    LOGGER.exception("Ошибка обработки сочетания %s", action)

        for hotkey_id in self._actions:
            user32.UnregisterHotKey(None, hotkey_id)
        LOGGER.info("Слушатель горячих клавиш остановлен")
