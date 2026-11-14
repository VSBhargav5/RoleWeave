import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from applications import current_application
from job_store import JobStore


@unittest.skipUnless(os.name == "nt" and os.environ.get("ROLEWEAVE_TEST_NATIVE_ARCHIVE") == "1", "Native Windows complete application journey")
class ApplicationJourneyTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        from desktop import JobShelf
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.store = JobStore(self.folder / "jobs.db")
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.shelf = JobShelf(self.root, self.store)
        for key, value in (("Job title", "Synthetic Engineer"), ("Company", "Synthetic Co"), ("Source URL (optional)", "https://example.invalid/apply")):
            self.shelf.fields[key].insert(0, value)
        self.shelf.posting.insert("1.0", "Synthetic role. Python required.")
        self.shelf.save()

    def test_new_user_prepares_documents_opens_page_tracks_and_restores_without_private_dossier(self):
        journey = self.shelf.open_application()
        self.assertTrue(journey.buttons["resume"].instate(["disabled"]))
        self.assertTrue(journey.buttons["files"].instate(["disabled"]))
        profile = journey.launch("profile")
        profile.fields["name"].insert(0, "Synthetic Applicant")
        profile.claim.insert("1.0", "Built a Python practice project.")
        profile.source.insert(0, "Private synthetic notes; not employment")
        profile.section.set("Projects")
        profile.reviewed.set(True)
        profile.add_fact()
        profile.save()
        editor = self.shelf.open_application().launch("evidence")
        picker = editor.open_career_facts()
        picker.list.selection_set(0)
        picker.copy()
        editor.facts.selection_set(0)
        editor.quote.insert("1.0", "Python required.")
        editor.add_requirement()
        editor.save()
        exact_job = self.shelf.current_id
        self.assertTrue(self.store.load(exact_job)["review"]["requirements"][0]["evidence"])
        builder = self.shelf.open_application().launch("resume")
        builder.facts.selection_set(0)
        builder.preview()
        builder.confirmed.set(True)
        builder.save()
        resume = self.folder / "resume.pdf"
        with patch("resume_builder.filedialog.asksaveasfilename", return_value=str(resume)):
            builder.export("pdf")
        self.assertTrue(resume.read_bytes().startswith(b"%PDF"))
        from pypdf import PdfReader
        text = "".join(page.extract_text() for page in PdfReader(resume).pages)
        self.assertIn("Synthetic Applicant", text)
        self.assertNotIn("Private synthetic notes", text)
        builder.destroy()
        letter = self.shelf.open_application().launch("letter")
        letter.choices.selection_set(0)
        letter.motivation.insert("1.0", "I enjoy building reliable Python tools.")
        letter.preview()
        letter.confirmed.set(True)
        target = self.folder / "cover-letter.txt"
        with patch("letter_window.filedialog.asksaveasfilename", return_value=str(target)):
            letter.export("txt")
        self.assertIn("Built a Python practice project.", target.read_text(encoding="utf-8"))
        self.assertNotIn("Private synthetic notes", target.read_text(encoding="utf-8"))
        letter.destroy()
        files = self.shelf.open_application().launch("files")
        files.choices.selection_set(0)
        files.preview()
        files.confirmed.set(True)
        upload = files.open_upload_folder()
        upload.formats["txt"].set(True)
        with patch("upload_window.messagebox.askyesno", return_value=True), patch("upload_window.filedialog.askdirectory", return_value=str(self.folder)):
            upload.export()
        self.assertEqual({p.name for p in upload.last_folder.iterdir()}, {"resume.pdf", "resume.txt", "EXPORT-INFO.txt"})
        self.assertEqual((upload.last_folder / "resume.pdf").read_bytes(), resume.read_bytes())
        upload.destroy()
        files.destroy()
        with patch("desktop.webbrowser.open", return_value=True) as browser:
            self.shelf.open_application().launch("source")
        browser.assert_called_once_with("https://example.invalid/apply")
        self.assertEqual(self.store.application_history(exact_job), [])
        tracker = self.shelf.open_application().launch("track")
        receipt = tracker.open_submission()
        receipt.channel.set("Employer portal")
        receipt.reference.set("SYNTHETIC-CONFIRMATION")
        receipt.note.insert("1.0", "Synthetic test only; no real application sent.")
        receipt.follow_up.set("2026-12-01")
        receipt.confirmed.set(True)
        receipt.record()
        self.assertEqual(tracker.stage.get(), "applied")
        receipt.destroy()
        tracker.destroy()
        self.assertEqual(current_application(self.store.application_history(exact_job))["stage"], "applied")
        backup = self.folder / "backup.json"
        self.store.backup(backup)
        restored = JobStore(self.folder / "restored.db")
        restored.restore(backup)
        self.assertEqual(restored.application_history(exact_job), self.store.application_history(exact_job))
        self.assertEqual(restored.load(exact_job)["snapshot"], self.store.load(exact_job)["snapshot"])
        self.assertEqual(len(restored.list_resumes(exact_job)), 1)
        self.assertEqual(list(self.folder.glob("*.zip")), [], "Neither ZIP nor private dossier is required for the complete handoff")

    def test_draft_or_changed_job_blocks_workspace_actions(self):
        journey = self.shelf.open_application()
        self.shelf.posting.insert("end", " Unsaved")
        with patch("desktop.webbrowser.open") as browser:
            journey.launch("source")
            browser.assert_not_called()
        self.assertTrue(journey.winfo_exists())
        self.assertIn("draft changed", journey.status.get())
        self.assertIsNone(self.shelf.open_application())
        journey.destroy()

    def test_browser_failure_does_not_claim_open_or_applied(self):
        with patch("desktop.webbrowser.open", return_value=False):
            self.shelf.open_application().launch("source")
        self.assertIn("did not open", self.shelf.status.get())
        self.assertEqual(self.store.application_history(self.shelf.current_id), [])
        import webbrowser
        with patch("desktop.webbrowser.open", side_effect=webbrowser.Error("Synthetic browser launch failure")):
            self.shelf.open_application().launch("source")
        self.assertIn("Synthetic browser launch failure", self.shelf.status.get())

    def test_missing_source_is_explained_and_minimum_size_keeps_actions_visible(self):
        self.root.deiconify()
        journey = self.shelf.open_application()
        journey.geometry("850x650")
        journey.update()
        for button in journey.buttons.values():
            self.assertTrue(button.winfo_ismapped())
            self.assertGreaterEqual(button.winfo_height(), 28)
            self.assertLessEqual(button.winfo_rooty() - journey.winfo_rooty() + button.winfo_height(), journey.winfo_height())
        journey.destroy()
        other = self.store.save(self.store.load(self.shelf.current_id)["snapshot"], "Other", "Synthetic", "")
        self.shelf.show_saved(other)
        journey = self.shelf.open_application()
        self.assertTrue(journey.buttons["source"].instate(["disabled"]))
        self.assertFalse(journey.buttons["track"].instate(["disabled"]))
        journey.destroy()
