from types import SimpleNamespace
import unittest
from unittest.mock import patch
import tkinter as tk

from desktop_errors import install_error_handler


class DesktopErrorTests(unittest.TestCase):
    def test_error_is_visible_without_private_exception_details_or_retry(self):
        root = SimpleNamespace()
        install_error_handler(root)
        private = RuntimeError("secret token /private/resume.pdf synthetic-sensitive-content")
        with patch("desktop_errors.messagebox.showerror") as dialog:
            root.report_callback_exception(type(private), private, None)
        message = dialog.call_args.args[1]
        self.assertIn("RW-UI-001", message)
        self.assertIn("Some saved changes may already have completed", message)
        self.assertNotIn(str(private), message)
        self.assertEqual(dialog.call_args.kwargs, {"parent": root})

    def test_reentrant_error_is_not_a_dialog_loop_and_later_errors_work(self):
        root = SimpleNamespace()
        install_error_handler(root)
        def reentrant(*_args, **_kwargs):
            root.report_callback_exception(RuntimeError, RuntimeError("nested"), None)
        with patch("desktop_errors.messagebox.showerror", side_effect=reentrant) as dialog:
            root.report_callback_exception(RuntimeError, RuntimeError("first"), None)
            self.assertEqual(dialog.call_count, 1)
            root.report_callback_exception(RuntimeError, RuntimeError("second"), None)
            self.assertEqual(dialog.call_count, 2)

    def test_destroyed_interpreter_does_not_raise_a_second_failure(self):
        root = SimpleNamespace()
        install_error_handler(root)
        with patch("desktop_errors.messagebox.showerror", side_effect=tk.TclError("gone")):
            root.report_callback_exception(RuntimeError, RuntimeError("failed"), None)

    def test_browser_startup_failure_never_falls_back_to_native_workspace(self):
        import sqlite3
        import desktop
        with patch("sys.argv", ["desktop.py", "--legacy", "--db", "synthetic-do-not-create.db"]), \
             patch("desktop.tk.Tk") as native, \
             patch("web_server.run_application", side_effect=sqlite3.OperationalError("synthetic locked database")), \
             patch("desktop.messagebox.showerror") as dialog:
            self.assertEqual(desktop.main(), 1)
        native.assert_not_called()
        dialog.assert_called_once()
