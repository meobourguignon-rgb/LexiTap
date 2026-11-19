import sys

from ctkmaker import CTkScript


def open_settings_window(widget):
    main_window = widget.winfo_toplevel()

    module = sys.modules[main_window.__class__.__module__]
    settings_class = getattr(module, "Settings", None)

    if settings_class is None:
        raise RuntimeError(
            "Окно Settings не найдено. Проверь имя класса "
            "окна в сгенерированном Python-файле."
        )

    settings_window = settings_class(main_window)

    def return_to_main():
        settings_window.destroy()
        main_window.deiconify()
        main_window.lift()

    settings_window.protocol("WM_DELETE_WINDOW", return_to_main)
    main_window.withdraw()


class SettingsPy(CTkScript):
    def open_settings(self):
        open_settings_window(self.widget)


class ButtonSettingsPy(CTkScript):
    def open_settings(self):
        open_settings_window(self.widget)