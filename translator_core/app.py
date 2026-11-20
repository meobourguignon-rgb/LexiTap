"""Контроллер приложения: связывает разметку, хоткеи, трей и перевод.

Слой не знает, как нарисованы окна: он получает их из ``translator_core.ui``
и обращается к виджетам по именам. Внутри — очередь событий из чужих
потоков (хоткеи, трей, перевод), которую разбирает Tk-цикл.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
from logging.handlers import RotatingFileHandler
from typing import Any

import customtkinter as ctk
from translator_core import clipboard, icon, sound

from translator_core.config import build_config, ensure_config
from translator_core.hotkeys import HotkeyListener, build_binding
from translator_core.language import direction_label, shorten
from translator_core.notification import ToastWindow
from translator_core.paths import APP_DIR, CONFIG_PATH
from translator_core.providers import Translation, TranslationError, Translator
from translator_core.tray import TrayIcon
from translator_core.ui import MainWindow, Settings

LOGGER = logging.getLogger("translater")


def setup_logging() -> None:
    """Включить запись в logs/translator.log (ошибка записи не критична)."""
    try:
        log_dir = APP_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_dir / "translator.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        logging.basicConfig(
            level=logging.INFO,
            handlers=[handler],
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    except OSError:
        pass


class TranslatorApp:
    """Соединяет сгенерированный CTkMaker-дизайн с логикой переводчика."""

    POLL_MS = 60

    def __init__(self) -> None:
        setup_logging()
        self._raw = self._load_raw()
        self.config = ensure_config(CONFIG_PATH)
        self.translator = Translator(self.config.translation)

        self._events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._running = False
        self._busy = False
        self._after_id: str | None = None
        self._hotkeys: HotkeyListener | None = None
        self._tray: TrayIcon | None = None
        self._tray_started = False
        self._toast_window: ToastWindow | None = None
        self._settings_window: Settings | None = None
        self._capture: dict[str, Any] | None = None

        self.root = MainWindow()
        self.root.controller = self
        icon.apply_window_icon(self.root)
        self._wire_main_window()

        # Тост создаётся при первом показе: при каждом показе — новое окно,
        # предыдущее закрывается (паттерн CTkMaker: _show_toast).
        sound.ensure_defaults()

    # ------------------------------------------------------------- конфиг

    @staticmethod
    def _load_raw() -> dict[str, Any]:
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save_raw(self) -> None:
        try:
            CONFIG_PATH.write_text(
                json.dumps(self._raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except OSError:
            LOGGER.exception("Не удалось сохранить %s", CONFIG_PATH)

    def _set(self, section: str, key: str, value: Any) -> None:
        self._raw.setdefault(section, {})[key] = value

    def _commit_settings(self) -> None:
        self._save_raw()
        self.config = build_config(self._raw)
        self.translator = Translator(self.config.translation)
        self._start_hotkeys()

    # ----------------------------------------------------------- уведомления

    def _show_toast(
        self,
        header: str,
        preview: str,
        body: str,
        duration: float,
        error: bool = False,
    ) -> None:
        """Показ тоста: при каждом показе создаём новое окно, предыдущее закрываем."""
        self._dismiss_toast()
        try:
            toast = ToastWindow(self.root, self.config.toast)
        except Exception:  # noqa: BLE001 - интерфейс должен работать без тоста
            LOGGER.exception("Не удалось создать окно уведомлений")
            return
        toast.show(
            header=header,
            preview=preview,
            body=body,
            duration=duration,
            error=error,
        )
        self._toast_window = toast

    def _dismiss_toast(self) -> None:
        if self._toast_window is not None:
            self._toast_window.destroy()
            self._toast_window = None

    # ------------------------------------------------------------- запуск

    def _wire_main_window(self) -> None:
        self.root.main.configure(command=self.show_main)
        self.root.settings.configure(command=self.open_settings)
        self.root.exit.configure(command=self.quit)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

    def start(self) -> None:
        self._running = True
        self._start_hotkeys()
        self._start_tray()
        self._after_id = self.root.after(self.POLL_MS, self._poll_events)
        if self.config.show_startup_hint:
            self.root.after(600, self._show_startup_hint)
        LOGGER.info("Translater запущен")
        self.root.mainloop()

    def _start_hotkeys(self) -> None:
        self._stop_hotkeys()
        try:
            bindings = [
                build_binding("to_russian", self.config.hotkeys.to_russian),
                build_binding("to_english", self.config.hotkeys.to_english),
                build_binding("quit", self.config.hotkeys.quit),
            ]
        except ValueError:
            LOGGER.exception("Некорректное сочетание клавиш в настройках")
            return
        listener = HotkeyListener(bindings, self._on_hotkey)
        listener.start()
        self._hotkeys = listener
        for spec in listener.failures:
            LOGGER.warning("Сочетание %s занято другой программой", spec)

    def _stop_hotkeys(self) -> None:
        if self._hotkeys is not None:
            self._hotkeys.stop()
            self._hotkeys = None

    def _start_tray(self) -> None:
        self._tray = TrayIcon(
            on_show=self.show_main,
            on_translate_russian=lambda: self._events.put(("hotkey", "to_russian")),
            on_translate_english=lambda: self._events.put(("hotkey", "to_english")),
            on_quit=lambda: self._events.put(("hotkey", "quit")),
        )
        self._tray_started = self._tray.start()

    def _show_startup_hint(self) -> None:
        if not self._running:
            return
        self._show_toast(
            header="Translater",
            preview="Переводчик готов к работе",
            body=(
                f"{self.config.hotkeys.to_russian.upper()} — перевести выделенный текст на русский.\n"
                f"{self.config.hotkeys.to_english.upper()} — перевести весь текст поля на английский и отправить.\n"
                "Окно можно закрыть: приложение останется в трее."
            ),
            duration=6.0,
        )

    # ----------------------------------------------------------- события

    def _on_hotkey(self, action: str) -> None:
        """Вызывается из потока слушателя/трея — только кладём событие в очередь."""
        self._events.put(("hotkey", action))

    def _poll_events(self) -> None:
        if not self._running:
            return
        while True:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            try:
                self._handle_event(event[0], event[1:])
            except Exception:  # noqa: BLE001 - одно событие не должно останавливать цикл
                LOGGER.exception("Ошибка обработки события %r", event[0])
        self._after_id = self.root.after(self.POLL_MS, self._poll_events)

    def _handle_event(self, kind: str, payload: tuple[Any, ...]) -> None:
        if kind == "hotkey":
            action = str(payload[0])
            if action == "quit":
                self.quit()
            elif action in ("to_russian", "to_english"):
                self.translate("ru" if action == "to_russian" else "en")
        elif kind == "translated":
            self._on_translated(*payload)
        elif kind == "error":
            self._show_error(str(payload[0]))

    # ------------------------------------------------------------ перевод

    def translate(self, target: str) -> None:
        if self._busy or not self._running:
            return
        self._busy = True
        threading.Thread(
            target=self._translate_worker,
            args=(target,),
            name=f"translate-{target}",
            daemon=True,
        ).start()

    def _translate_worker(self, target: str) -> None:
        try:
            # Ctrl+Alt+END должен брать всё содержимое активного поля (Ctrl+A).
            source = clipboard.copy_selection(select_all=(target == "en"))
            if not source:
                self._events.put(("error", "Не удалось скопировать текст из активного поля"))
                return
            result = self.translator.translate(source, target)
            self._events.put(("translated", source, result, target))
        except TranslationError as exc:
            self._events.put(("error", str(exc)))
        except Exception:  # noqa: BLE001 - поток не должен умирать
            LOGGER.exception("Непредвиденная ошибка перевода")
            self._events.put(("error", "Непредвиденная ошибка перевода"))
        finally:
            self._busy = False

    def _on_translated(self, source: str, result: Translation, target: str) -> None:
        if self.config.sound.enabled:
            sound.play(self.config.sound.notify_file)

        if target == "en":
            # Английский перевод только вставляется и отправляется — без тоста.
            if not clipboard.replace_selection_with(
                result.text, press_enter=self.config.translation.auto_send
            ):
                self._show_error("Не удалось вставить перевод в поле")
            return

        header = f"{direction_label(result.source_language, target)} · {result.provider}"
        self._show_toast(
            header=header,
            preview=shorten(source, self.config.toast.max_source_chars),
            body=result.text,
            duration=self.config.toast.duration_seconds,
        )

    def _show_error(self, message: str) -> None:
        LOGGER.warning(message)
        if self.config.sound.enabled:
            sound.play(self.config.sound.error_file)
        self._show_toast(
            header="Ошибка",
            preview=message,
            body=message,
            duration=self.config.toast.duration_seconds,
            error=True,
        )

    # --------------------------------------------------------------- окна

    def show_main(self) -> None:
        if self._settings_window is not None:
            if self._settings_window.winfo_exists():
                self._settings_window.destroy()
            self._settings_window = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_to_tray(self) -> None:
        if not self._tray_started:
            self._show_error("Значок в трее недоступен — окно оставлено открытым")
            return
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.withdraw()
        self.root.withdraw()

    def open_settings(self) -> None:
        if self._settings_window is not None and self._settings_window.winfo_exists():
            self._settings_window.deiconify()
            self._settings_window.lift()
            self._settings_window.focus_force()
            return

        self.root.withdraw()
        settings = Settings(self.root)
        settings.controller = self
        icon.apply_window_icon(settings)
        self._settings_window = settings
        self._wire_settings_window(settings)
        settings.lift()
        settings.focus_force()

    def _wire_settings_window(self, settings: Settings) -> None:
        settings.button_1.configure(command=self.show_main)
        settings.button_2.configure(command=lambda: None)
        settings.button_3.configure(command=self.quit)
        settings.protocol("WM_DELETE_WINDOW", self.show_main)

        settings.checkbox_1.select() if self.config.sound.enabled else settings.checkbox_1.deselect()
        settings.checkbox_2.select() if self.config.translation.auto_send else settings.checkbox_2.deselect()
        settings.checkbox_3.select() if self.config.show_startup_hint else settings.checkbox_3.deselect()

        settings.checkbox_1.configure(
            command=lambda: self._toggle("sound", "enabled", settings.checkbox_1.get())
        )
        settings.checkbox_2.configure(
            command=lambda: self._toggle("translation", "auto_send", settings.checkbox_2.get())
        )
        settings.checkbox_3.configure(
            command=lambda: self._toggle_top("show_startup_hint", settings.checkbox_3.get())
        )

        settings.button_4.configure(
            text=self.config.hotkeys.to_russian.upper(),
            command=lambda: self._start_capture("to_russian", settings),
        )
        settings.button_5.configure(
            text=self.config.hotkeys.to_english.upper(),
            command=lambda: self._start_capture("to_english", settings),
        )

    def _toggle(self, section: str, key: str, value: bool) -> None:
        self._set(section, key, bool(value))
        self._commit_settings()

    def _toggle_top(self, key: str, value: bool) -> None:
        self._raw[key] = bool(value)
        self._commit_settings()

    # -------------------------------------------------- переназначение клавиш

    def _start_capture(self, action: str, settings: Settings) -> None:
        self._stop_hotkeys()
        button = settings.button_4 if action == "to_russian" else settings.button_5
        funcid = settings.bind("<KeyPress>", self._on_capture_key, add="+")
        self._capture = {
            "action": action,
            "button": button,
            "settings": settings,
            "funcid": funcid,
        }
        button.configure(text="НАЖМИТЕ КЛАВИШИ", fg_color="#b45309")
        settings.label_12.configure(
            text="Нажмите новое сочетание с Ctrl/Alt/Shift…\nEsc — отменить изменение."
        )
        settings.focus_force()

    def _on_capture_key(self, event: Any) -> None:
        if self._capture is None:
            return
        keysym = str(getattr(event, "keysym", "") or "").lower()
        if keysym in ("escape", "esc"):
            self._cancel_capture()
            return
        if keysym in ("shift", "shift_l", "shift_r", "control", "control_l", "control_r",
                      "alt", "alt_l", "alt_r", "meta", "meta_l", "meta_r"):
            return

        name = {"return": "enter", "space": "space", "control": "ctrl"}.get(keysym, keysym)
        state = int(getattr(event, "state", 0))
        modifiers: list[str] = []
        if state & 0x0004:
            modifiers.append("ctrl")
        if state & 0x20000:
            modifiers.append("alt")
        if state & 0x0001:
            modifiers.append("shift")
        spec = "+".join(modifiers + [name])
        try:
            build_binding("capture", spec)
        except ValueError:
            return

        action = self._capture["action"]
        self._set("hotkeys", action, spec)
        self._save_raw()
        self.config = build_config(self._raw)
        self._end_capture()
        self._start_hotkeys()

    def _cancel_capture(self) -> None:
        self._end_capture()
        self._start_hotkeys()

    def _end_capture(self) -> None:
        capture = self._capture
        if capture is None:
            return
        self._capture = None
        settings: Settings = capture["settings"]
        funcid = capture["funcid"]
        button = capture["button"]
        action = capture["action"]

        if funcid:
            settings.unbind("<KeyPress>", funcid)
        settings.label_12.configure(
            text="Нажмите на сочетание, чтобы изменить его.\nEsc — отменить изменение."
        )
        if button.winfo_exists():
            spec = (
                self.config.hotkeys.to_russian
                if action == "to_russian"
                else self.config.hotkeys.to_english
            )
            button.configure(text=spec.upper(), fg_color="#6366f1")

    # -------------------------------------------------------------- выход

    def quit(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_hotkeys()
        if self._tray is not None:
            self._tray.stop()
            self._tray = None
        self._dismiss_toast()
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:  # noqa: BLE001 - окно могло уже закрыться
                pass
        LOGGER.info("Translater остановлен")
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001 - выход не должен зависеть от ошибок виджетов
            LOGGER.exception("Ошибка при закрытии окна, завершаем принудительно")
            try:
                self.root.quit()
            except Exception:  # noqa: BLE001
                pass
