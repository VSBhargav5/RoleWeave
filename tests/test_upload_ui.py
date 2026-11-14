import os
from pathlib import Path
from unittest.mock import patch
import unittest

import test_dossier_ui as dossier_ui


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows upload workflow")
class UploadUITests(unittest.TestCase):
    def setUp(self):
        dossier_ui.DossierUITests.setUp(self)

    def prepared(self):
        self.window.choices.selection_set(0)
        self.window.preview()
        self.window.confirmed.set(True)
        return self.window.open_upload_folder()

    def test_review_required_then_save_actual_files_and_open_folder(self):
        self.assertIsNone(self.window.open_upload_folder())
        upload = self.prepared()
        self.assertTrue(upload.formats["txt"].get())
        with patch("upload_window.messagebox.askyesno", return_value=True), patch("upload_window.filedialog.askdirectory", return_value=str(self.folder)):
            upload.export()
        self.assertEqual({p.name for p in upload.last_folder.iterdir()}, {"resume.txt", "EXPORT-INFO.txt"})
        with patch("upload_window.os.startfile") as opener:
            upload.open_folder()
        opener.assert_called_once_with(upload.last_folder)
        self.assertEqual(self.store.application_history(self.job), [])
        upload.destroy()

    def test_cancel_empty_selection_and_failed_retry_do_not_claim_new_output(self):
        upload = self.prepared()
        with patch("upload_window.messagebox.askyesno", return_value=False), patch("upload_window.filedialog.askdirectory") as chooser:
            upload.export()
            chooser.assert_not_called()
        upload.formats["txt"].set(False)
        upload.export()
        self.assertIn("Select at least", upload.status.get())
        upload.formats["txt"].set(True)
        with patch("upload_window.messagebox.askyesno", return_value=True), patch("upload_window.filedialog.askdirectory", return_value=str(self.folder)):
            upload.export()
            first = upload.last_folder
            with patch("upload_window.export_upload_folder", side_effect=OSError("synthetic disk failure")):
                upload.export()
        self.assertIsNone(upload.last_folder)
        self.assertTrue(upload.open_button.instate(["disabled"]))
        self.assertTrue((first / "EXPORT-INFO.txt").exists())
        self.assertIn("did not complete", upload.status.get())
        upload.destroy()

    def test_supported_minimum_keeps_export_and_close_controls_visible(self):
        upload = self.prepared()
        self.root.deiconify()
        self.window.deiconify()
        upload.deiconify()
        upload.geometry("650x400")
        upload.update()
        from tkinter import ttk
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for button in walk(upload):
            if isinstance(button, ttk.Button):
                self.assertTrue(button.winfo_ismapped())
                self.assertGreaterEqual(button.winfo_height(), 28)
                self.assertLessEqual(button.winfo_rooty() - upload.winfo_rooty() + button.winfo_height(), upload.winfo_height())
        upload.destroy()
