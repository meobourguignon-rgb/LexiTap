from ctkmaker import CTkScript


class ButtonExitPy(CTkScript):
    def exit_app(self):
        self.widget.winfo_toplevel().destroy()