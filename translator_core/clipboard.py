"""Копирование выделенного текста через буфер обмена Windows.

Буфер обмена — единственный способ получить выделение из чужого приложения
без установки UI Automation. Мы запоминаем прежнее текстовое содержимое,
нажимаем Ctrl+C, читаем результат и возвращаем буфер как было.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from functools import lru_cache
from typing import Any

LOGGER = logging.getLogger(__name__)

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_A = 0x41
VK_C = 0x43
VK_V = 0x56
VK_RETURN = 0x0D
KEY_PRESSED = 0x8000

_ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class _KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", _ULONG_PTR),
    ]


class _HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _InputUnion(ctypes.Union):
    _fields_ = [
        ("ki", _KeyboardInput),
        ("mi", _MouseInput),
        ("hi", _HardwareInput),
    ]


class _Input(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", _InputUnion)]


@lru_cache(maxsize=1)
def _user32() -> Any:
    library = ctypes.WinDLL("user32", use_last_error=True)
    library.OpenClipboard.argtypes = [wintypes.HWND]
    library.OpenClipboard.restype = wintypes.BOOL
    library.CloseClipboard.restype = wintypes.BOOL
    library.EmptyClipboard.restype = wintypes.BOOL
    library.GetClipboardData.argtypes = [wintypes.UINT]
    library.GetClipboardData.restype = wintypes.HANDLE
    library.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
    library.SetClipboardData.restype = wintypes.HANDLE
    library.GetClipboardSequenceNumber.restype = wintypes.DWORD
    library.GetAsyncKeyState.argtypes = [ctypes.c_int]
    library.GetAsyncKeyState.restype = ctypes.c_short
    library.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(_Input), ctypes.c_int]
    library.SendInput.restype = wintypes.UINT
    return library


@lru_cache(maxsize=1)
def _kernel32() -> Any:
    library = ctypes.WinDLL("kernel32", use_last_error=True)
    library.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    library.GlobalAlloc.restype = wintypes.HGLOBAL
    library.GlobalLock.argtypes = [wintypes.HGLOBAL]
    library.GlobalLock.restype = wintypes.LPVOID
    library.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    library.GlobalFree.argtypes = [wintypes.HGLOBAL]
    return library


def read_text(retries: int = 12) -> str | None:
    """Прочитать UNICODE-текст из буфера обмена или None."""
    user32 = _user32()
    kernel32 = _kernel32()
    for _ in range(retries):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.01)
    else:
        return None

    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return None
        try:
            return ctypes.wstring_at(pointer)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def write_text(text: str, retries: int = 12) -> bool:
    """Положить текст в буфер обмена, заменив прежнее содержимое."""
    user32 = _user32()
    kernel32 = _kernel32()
    payload = text.encode("utf-16-le") + b"\x00\x00"

    for _ in range(retries):
        if user32.OpenClipboard(None):
            break
        time.sleep(0.01)
    else:
        return False

    try:
        if not user32.EmptyClipboard():
            return False
        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(payload))
        if not handle:
            return False
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            return False
        ctypes.memmove(pointer, payload, len(payload))
        kernel32.GlobalUnlock(handle)
        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            return False
        return True
    finally:
        user32.CloseClipboard()


def _wait_modifiers_released(user32: Any, timeout: float = 1.0) -> None:
    """Дождаться, пока отпустят Ctrl/Alt, иначе Ctrl+C уйдёт с зажатым Alt."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = user32.GetAsyncKeyState(VK_CONTROL) | user32.GetAsyncKeyState(VK_MENU)
        if not state & KEY_PRESSED:
            return
        time.sleep(0.01)


def _send_shortcut(user32: Any, virtual_key: int, modifier: int | None) -> bool:
    """Нажать клавишу, при необходимости — вместе с модификатором."""
    events: list[tuple[int, int]] = []
    if modifier is not None:
        events.append((modifier, 0))
    events.append((virtual_key, 0))
    events.append((virtual_key, KEYEVENTF_KEYUP))
    if modifier is not None:
        events.append((modifier, KEYEVENTF_KEYUP))

    inputs = (_Input * len(events))()
    for index, (key, flags) in enumerate(events):
        inputs[index].type = INPUT_KEYBOARD
        inputs[index].union.ki = _KeyboardInput(
            wVk=key, wScan=0, dwFlags=flags, time=0, dwExtraInfo=0
        )
    # SendInput ждёт POINTER(_Input), поэтому передаём сам массив: ctypes
    # приводит его к указателю на первый элемент. byref здесь дал бы
    # указатель на массив и ArgumentError.
    sent = user32.SendInput(len(events), inputs, ctypes.sizeof(_Input))
    return sent == len(events)


def _send_ctrl_c(user32: Any) -> bool:
    return _send_shortcut(user32, VK_C, VK_CONTROL)


def _send_ctrl_a(user32: Any) -> bool:
    return _send_shortcut(user32, VK_A, VK_CONTROL)


def replace_selection_with(text: str, press_enter: bool = False) -> bool:
    """Вставить текст вместо выделения (Ctrl+V) и, если нужно, отправить Enter.

    Выделение в чужом приложении остаётся активным после Ctrl+C, поэтому
    Ctrl+V заменяет его переводом, а Enter отправляет сообщение.
    """
    if not text.strip():
        return False
    try:
        user32 = _user32()
    except OSError:
        LOGGER.exception("Не удалось загрузить user32")
        return False

    if not write_text(text):
        LOGGER.warning("Не удалось положить перевод в буфер обмена")
        return False

    _wait_modifiers_released(user32)
    if not _send_shortcut(user32, VK_V, VK_CONTROL):
        LOGGER.warning("SendInput не отправил Ctrl+V")
        return False
    if press_enter:
        time.sleep(0.15)
        if not _send_shortcut(user32, VK_RETURN, None):
            LOGGER.warning("SendInput не отправил Enter")
            return False
    return True


def copy_selection(timeout: float = 1.0, select_all: bool = False) -> str | None:
    """Скопировать текст или всё содержимое активного поля.

    При select_all сначала отправляется Ctrl+A; в любом случае прежнее
    содержимое буфера обмена восстанавливается после копирования.
    """
    try:
        user32 = _user32()
    except OSError:
        LOGGER.exception("Не удалось загрузить user32")
        return None

    previous = read_text()
    sequence = user32.GetClipboardSequenceNumber()

    _wait_modifiers_released(user32)
    if select_all:
        if not _send_ctrl_a(user32):
            LOGGER.warning("SendInput не отправил Ctrl+A")
            return None
        time.sleep(0.05)
    if not _send_ctrl_c(user32):
        LOGGER.warning("SendInput не отправил Ctrl+C")
        return None

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if user32.GetClipboardSequenceNumber() != sequence:
            break
        time.sleep(0.02)

    selected = read_text()
    if previous is not None and selected != previous:
        write_text(previous)
    elif previous is None and selected is not None:
        # Прежнее содержимое было нетекстовым — вернуть его нельзя,
        # поэтому оставляем то, что скопировали.
        LOGGER.debug("Буфер обмена был без текста, восстановление пропущено")

    if selected is None:
        return None
    cleaned = selected.strip()
    return cleaned or None
