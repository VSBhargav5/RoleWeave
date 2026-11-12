"""Visible UI failure reporting without persisting payloads, secrets or tracebacks."""
import tkinter as tk
from tkinter import messagebox

from runtime_paths import APP_VERSION


def install_error_handler(root):
    showing = False

    def report(_exception_type, _exception, _traceback):
        nonlocal showing
        if showing:
            return
        showing = True
        try:
            messagebox.showerror(
                "RoleWeave action interrupted",
                f"RoleWeave {APP_VERSION} — RW-UI-001\n\n"
                "An unexpected error interrupted this action. It was not automatically retried. "
                "Some saved changes may already have completed; inspect them before repeating the action.\n\n"
                "Preserve any unsaved text separately, then close and reopen the app. "
                "If it happens again, report this code and the steps using synthetic data. "
                "Do not share your database, keys, tokens or private application files.\n\n"
                "No error details were logged or transmitted by this handler.", parent=root)
        except tk.TclError:
            pass  # A destroyed interpreter cannot display another dialog.
        finally:
            showing = False

    root.report_callback_exception = report
