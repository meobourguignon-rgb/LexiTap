import tkinter as tk
from typing import cast

from ctkmaker import CTkScript


class HomePy(CTkScript):
    def open_main(self):
        settings_window = self.widget.winfo_toplevel()

        if settings_window.master is None:
            return

        main_window = cast(tk.Tk, settings_window.master)

        setattr(main_window, "_settings_window", None)
        settings_window.destroy()

        main_window.deiconify()
        main_window.lift()
        main_window.focus_force()