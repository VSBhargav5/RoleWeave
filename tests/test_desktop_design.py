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

    def test_getting_started_explains_current_workflow_and_limits_without_network(self):
        from tkinter import ttk
        from unittest.mock import patch
        before = self.store.path.read_bytes()
        with patch("network_io.request_bytes") as send:
            guide = self.shelf.open_help()
            guide.geometry("700x500")
            for index, title in enumerate(guide.help_pages):
                guide.help_tabs.select(index)
                guide.update()
                page = guide.help_pages[title]
                self.assertEqual(page.cget("state"), "disabled")
                self.assertGreaterEqual(page.winfo_height(), 100)
            text = guide.help_pages["Readiness and remaining work"].get("1.0", "end")
            self.assertIn("8/8", text)
            self.assertIn("NOT IMPLEMENTED", text)
            self.assertIn("Ashby", text)
            self.assertIn("LIVE TRIAL NEEDED", text)
            data = guide.help_pages["Your data and boundaries"].get("1.0", "end")
            self.assertIn(str(self.store.path.resolve()), data)
            self.assertIn("different shelves", data)
            def walk(widget):
                for child in widget.winfo_children():
                    yield child
                    yield from walk(child)
            for button in walk(guide):
                if isinstance(button, ttk.Button):
                    self.assertTrue(button.winfo_ismapped())
                    self.assertGreaterEqual(button.winfo_height(), 28)
                    bottom = button.winfo_rooty() - guide.winfo_rooty() + button.winfo_height()
                    self.assertLessEqual(bottom, guide.winfo_height())
            guide.destroy()
            send.assert_not_called()
        self.assertEqual(self.store.path.read_bytes(), before)

    def test_rich_rows_and_hidden_filters_preserve_identity_stage_and_drafts(self):
        self.assertEqual(self.shelf.jobs.item(self.job, "text"), self.store.load(self.job)["title"] + "\n" + self.store.load(self.job)["company"])
        self.assertEqual(self.shelf.jobs.item(self.job, "values"), ("Saved",))
        self.assertEqual(self.shelf.jobs.selection(), (self.job,))
        self.assertEqual(self.shelf.filters_panel.winfo_manager(), "")
        self.shelf.posting.insert("end", " Unsaved draft.")
        self.shelf.toggle_filters()
        self.assertEqual(self.shelf.filters_panel.winfo_manager(), "grid")
        self.shelf.filter.set("International relocation")
        self.shelf.refresh()
        self.shelf.toggle_filters()
        self.assertIn("International relocation", self.shelf.filter_summary.get())
        self.assertEqual(self.shelf.current_id, self.job)
        self.assertIn("Unsaved draft.", self.shelf.posting.get("1.0", "end"))
        self.store.record_application(self.job, "interview", "Synthetic stage")
        self.shelf.refresh()
        self.assertEqual(self.shelf.review_stage.get(), "Interview")



@unittest.skipUnless(os.name == "nt", "Native Windows Tk lifecycle")
class ThemeLifecycleTests(unittest.TestCase):
    def test_immediate_close_has_no_queued_theme_error_and_does_not_run_timers(self):
        import tkinter as tk
        from desktop_theme import apply_theme
        for _attempt in range(2):
            root = tk.Tk()
            root.withdraw()
            root.tk.eval('set ::theme_errors {}; proc bgerror {message} {lappend ::theme_errors $message}')
            timer_called = []
            timer = root.after(0, lambda: timer_called.append(True))
            apply_theme(root)
            self.assertEqual(timer_called, [], "Theme setup must not process timer/network polling callbacks")
            root.after_cancel(timer)
            root.destroy()
            root.tk.call("update")
            self.assertEqual(root.tk.call("set", "::theme_errors"), "")
