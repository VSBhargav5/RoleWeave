import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows Tk smoke")
class DesktopTests(unittest.TestCase):
    def test_save_reopen_filter_and_import_preserve_posting(self):
        import tkinter as tk
        from desktop import JobShelf
        from job_store import JobStore
        with tempfile.TemporaryDirectory() as temp:
            root = tk.Tk()
            root.withdraw()
            try:
                store = JobStore(Path(temp) / "jobs.db")
                shelf = JobShelf(root, store)
                shelf.fields["Job title"].insert(0, "Synthetic Engineer")
                shelf.fields["Company"].insert(0, "Synthetic Ltd")
                posting = "Python required.\n  Preserve indentation and తెలుగు.\n"
                shelf.posting.insert("1.0", posting)
                with patch("desktop.messagebox.showerror") as error:
                    shelf.save()
                    error.assert_not_called()
                self.assertEqual(len(shelf.rows), 1)
                shelf.new_posting()
                shelf.jobs.selection_set(shelf.rows[0]["id"])
                shelf.open_selected()
                self.assertEqual(shelf.posting.get("1.0", "end-1c"), posting)
                shelf.filter.set("International relocation")
                shelf.refresh()
                self.assertEqual(shelf.rows, [])
                shelf.filter.set("All markets")
                fixture = Path(__file__).parents[1] / "examples/synthetic.json"
                with patch("desktop.filedialog.askopenfilename", return_value=str(fixture)), patch("desktop.messagebox.showerror") as error:
                    shelf.import_review()
                    error.assert_not_called()
                shelf.jobs.selection_set(shelf.rows[0]["id"])
                shelf.open_selected()
                self.assertIn("Needs your review", shelf.evidence.plain_text)
                backup = Path(temp) / "shelf-backup.json"
                with patch("desktop.filedialog.asksaveasfilename", return_value=str(backup)), patch("desktop.messagebox.showerror") as error:
                    shelf.backup_shelf()
                    error.assert_not_called()
                shelf.store = JobStore(Path(temp) / "restored.db")
                with patch("desktop.filedialog.askopenfilename", return_value=str(backup)), patch("desktop.messagebox.showerror") as error:
                    shelf.restore_shelf()
                    error.assert_not_called()
                self.assertEqual(len(shelf.rows), 2)
                self.assertIn("Restored 2", shelf.status.get())
                shelf.jobs.selection_set(shelf.rows[0]["id"])
                pack = Path(temp) / "prep.txt"
                with patch("desktop.filedialog.asksaveasfilename", return_value=str(pack)), patch("desktop.messagebox.showerror") as error:
                    shelf.export_pack()
                    error.assert_not_called()
                self.assertIn("ROLEWEAVE APPLICATION PREPARATION PACK", pack.read_text(encoding="utf-8"))
                root.update_idletasks()
            finally:
                root.destroy()
