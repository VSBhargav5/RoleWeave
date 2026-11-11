import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from job_store import JobStore
from rehearsal_journal import read_rehearsal


@unittest.skipUnless(os.name == "nt", "Native Windows rehearsal workflow")
class RehearsalUITests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "journal.json"
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.job = self.store.save((Path(__file__).parents[1] / "examples/synthetic.json").read_bytes(), "Engineer", "Synthetic")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.window = self.shelf.open_rehearsal()
        self.window.withdraw()

    def select_questions(self):
        self.window.choices.selection_set(0, 1)
        self.window.start_selected()

    def test_navigation_reveal_and_file_reopen_keep_exact_draft_identity(self):
        self.select_questions()
        self.window.answer.insert("1.0", "My CSV project draft.")
        self.window.reveal_evidence()
        self.assertEqual(self.window.answer.get("1.0", "end-1c"), "My CSV project draft.")
        self.window.move(1)
        self.assertEqual(self.window.answer.get("1.0", "end-1c"), "")
        self.window.reflection.insert("1.0", "Open Spark question.")
        self.window.move(-1)
        self.assertEqual(self.window.answer.get("1.0", "end-1c"), "My CSV project draft.")
        self.window.confirmed.set(True)
        with patch("rehearsal_window.filedialog.asksaveasfilename", return_value=str(self.path)):
            self.window.save()
        snapshot, record = read_rehearsal(self.path)
        self.assertFalse(record["learning_verified"])
        with patch("desktop.filedialog.askopenfilename", return_value=str(self.path)):
            opened = self.shelf.open_rehearsal_file()
        self.assertEqual(opened.answer.get("1.0", "end-1c"), "My CSV project draft.")
        opened.destroy()
        self.assertEqual(self.store.application_history(self.job), [])

    def test_removed_questions_and_window_close_do_not_discard_unconfirmed_drafts(self):
        self.select_questions()
        self.window.answer.insert("1.0", "Keep my answer.")
        self.window.choices.selection_clear(0, "end")
        self.window.choices.selection_set(1)
        with patch("rehearsal_window.messagebox.askyesno", return_value=False):
            self.window.start_selected()
            self.window.close()
        self.assertEqual(self.window.selected_ids, ["python", "spark"])
        self.assertTrue(self.window.winfo_exists())
        self.assertEqual(self.window.answer.get("1.0", "end-1c"), "Keep my answer.")

    def test_source_and_answer_panes_fit_minimum_size(self):
        from tkinter import ttk
        self.root.deiconify()
        self.window.deiconify()
        self.select_questions()
        self.window.geometry("900x700")
        self.window.update()
        self.assertGreaterEqual(self.window.source.winfo_height(), 80)
        self.assertGreaterEqual(self.window.answer.winfo_height(), 80)
        def walk(widget):
            for child in widget.winfo_children():
                yield child
                yield from walk(child)
        for widget in walk(self.window):
            if isinstance(widget, ttk.Button) and widget.winfo_ismapped():
                self.assertGreaterEqual(widget.winfo_height(), 28)
                y = widget.winfo_rooty() - self.window.winfo_rooty()
                self.assertLessEqual(y + widget.winfo_height(), self.window.winfo_height())

    def test_timer_requires_explicit_start_and_saved_version_captures_paused_time(self):
        self.window.toggle_timer()
        self.assertFalse(self.window.timer.running)
        self.select_questions()
        now = [10.0]
        self.window.timer.clock = lambda: now[0]
        self.window.toggle_timer()
        now[0] += 42.0
        self.window.confirmed.set(True)
        with patch("rehearsal_window.filedialog.asksaveasfilename", return_value=str(self.path)):
            self.window.save()
        self.assertEqual(read_rehearsal(self.path)[1]["elapsed_seconds"], 42)
        self.assertFalse(self.window.timer.running)
        with patch("rehearsal_window.messagebox.askyesno", return_value=False):
            self.window.reset_timer()
        self.assertEqual(self.window.timer.seconds(), 42)
        with patch("rehearsal_window.messagebox.askyesno", return_value=True):
            self.window.reset_timer()
        self.assertEqual(self.window.timer.seconds(), 0)
        self.assertNotEqual(self.window.state(), self.window.baseline)

    def test_private_tools_require_saved_inputs_and_comparison_rejects_unsaved_changes(self):
        self.select_questions()
        with patch("rehearsal_window.filedialog.askopenfilename") as choose:
            self.window.compare_version()
            choose.assert_not_called()
        self.window.confirmed.set(True)
        with patch("rehearsal_window.filedialog.asksaveasfilename", return_value=str(self.path)):
            self.window.save()
        with patch("rehearsal_window.filedialog.askopenfilename", return_value=str(self.path)):
            dialog = self.window.compare_version()
        self.assertIsNotNone(dialog)
        dialog.destroy()
        self.window.answer.insert("1.0", "Unsaved")
        with patch("rehearsal_window.filedialog.asksaveasfilename") as save:
            self.window.export_pack()
            save.assert_not_called()
        self.assertIn("Save a new", self.window.status.get())
