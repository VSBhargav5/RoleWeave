import os
from pathlib import Path
import tempfile
import unittest
from datetime import date

from demo_data import seed_practice
from job_store import JobStore


@unittest.skipUnless(os.name == "nt", "Native Windows workspace design and navigation")
class DesktopDesignTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = JobStore(Path(self.temp.name) / "jobs.db")
        self.job = seed_practice(self.store)
        self.root = tk.Tk()
        self.root.geometry("1180x780")
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.root.update_idletasks)
        self.shelf = JobShelf(self.root, self.store)
        self.shelf.show_saved(self.job)
        self.root.update_idletasks()

    def test_global_counts_survive_filters_and_empty_state_keeps_saved_review(self):
        self.store.record_application(self.job, "applied", "Synthetic reminder", date.today().isoformat())
        self.shelf.refresh()
        self.assertEqual(self.shelf.metric_values["saved"].get(), "2")
        self.assertEqual(self.shelf.metric_values["due"].get(), "1")
        self.shelf.search.set("no matching title")
        self.shelf.refresh()
        self.assertEqual(self.shelf.rows, [])
        self.assertTrue(self.shelf.empty_library.place_info())
        self.assertIn("match these filters", self.shelf.empty_library.cget("text"))
        self.assertEqual(self.shelf.current_id, self.job)
        self.assertEqual(self.shelf.metric_values["saved"].get(), "2")
        self.store.record_application(self.job, "closed", "", date.today().isoformat())
        self.shelf.refresh()
        self.assertEqual(self.shelf.metric_values["due"].get(), "0")

    def test_tabs_preserve_posting_draft_and_resume_save_refreshes_count(self):
        self.shelf.detail_tabs.select(1)
        self.assertIn("Needs your review", self.shelf.evidence.get("1.0", "end"))
        self.shelf.posting.insert("end", " Unsaved wording.")
        self.shelf.focus_workspace()
        self.assertEqual(self.shelf.detail_tabs.index("current"), 0)
        self.assertTrue(self.shelf.has_draft_changes())
        self.shelf.posting.delete("1.0", "end")
        self.shelf.posting.insert("1.0", self.shelf.loaded_review["posting"])
        builder = self.shelf.open_resume()
        builder.facts.selection_set(0)
        builder.preview()
        builder.confirmed.set(True)
        builder.save()
        self.assertEqual(self.shelf.metric_values["resumes"].get(), "1")
        builder.close()

    def test_primary_actions_fit_supported_minimum_window_sizes(self):
        from tkinter import ttk
        def buttons(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    ancestor, visible_tab = child, True
                    while ancestor is not widget.winfo_toplevel():
                        parent = ancestor.master
                        if isinstance(parent, ttk.Notebook) and str(ancestor) != parent.select():
                            visible_tab = False
                            break
                        ancestor = parent
                    if visible_tab:
                        yield child
                yield from buttons(child)

        def assert_fits(window):
            window.update()
            for button in buttons(window):
                with self.subTest(window=window.title(), action=button.cget("text")):
                    x = button.winfo_rootx() - window.winfo_rootx()
                    y = button.winfo_rooty() - window.winfo_rooty()
                    self.assertTrue(button.winfo_ismapped(), "An action on the current page was hidden")
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertGreaterEqual(button.winfo_height(), 28, "Action was collapsed by the layout")
                    self.assertLessEqual(x + button.winfo_width(), window.winfo_width())
                    self.assertLessEqual(y + button.winfo_height(), window.winfo_height())

        self.root.geometry("1040x700")
        assert_fits(self.root)
        self.assertGreaterEqual(self.shelf.posting.winfo_height(), 160)
        profile = self.shelf.open_profile()
        profile.geometry("800x650")
        assert_fits(profile)
        profile.tabs.select(1)
        assert_fits(profile)
        self.assertGreaterEqual(profile.facts.winfo_height(), 48)
        profile.close()
        resume = self.shelf.open_resume()
        resume.geometry("800x650")
        assert_fits(resume)
        resume.tabs.select(1)
        assert_fits(resume)
        resume.close()
        discovery = self.shelf.open_discovery()
        discovery.geometry("850x650")
        assert_fits(discovery)
        self.assertGreaterEqual(discovery.preview.winfo_height(), 80)
        discovery.close()
        editor = self.shelf.edit_evidence()
        editor.geometry("800x700")
        assert_fits(editor)
        self.assertGreaterEqual(editor.facts.winfo_height(), 48)
        self.assertGreaterEqual(editor.requirements.winfo_height(), 48)
        assistant = editor.open_ai()
        assistant.geometry("820x650")
        assert_fits(assistant)
        self.assertGreaterEqual(assistant.payload_view.winfo_height(), 60)
        assistant.tabs.select(1)
        assert_fits(assistant)
        assistant.close()
        editor.destroy()
