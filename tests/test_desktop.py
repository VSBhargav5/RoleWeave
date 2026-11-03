import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.name == "nt", "Native Windows Tk smoke")
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
                shelf.jobs.selection_set(0)
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
                shelf.jobs.selection_set(0)
                shelf.open_selected()
                self.assertIn("needs_review", shelf.evidence.get("1.0", "end-1c"))
                root.update_idletasks()
            finally:
                root.destroy()
