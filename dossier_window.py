"""Review the exact private dossier bytes before deliberate local export."""
from io import BytesIO
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import zipfile

from application_dossier import build_dossier
from desktop_theme import polish_widgets, reserve_footer
from safe_export import publish_bytes
from recipient_bundle import recipient_bytes
from upload_window import UploadWindow
from cover_letter import read_letter
from letter_window import LetterWindow
from career_profile import profile_snapshot
from resume_versions import decoded
from roleweave import MAX_BYTES


class DossierWindow(tk.Toplevel):
    def __init__(self, parent, store, job_id):
        self.job = store.load(job_id)
        super().__init__(parent)
        self.store, self.prepared = store, None
        self.letter_snapshot = None
        self.title("RoleWeave - Application files")
        self.geometry("1000x760")
        self.minsize(850, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=self.job["company"] + " - " + self.job["title"], font=("Segoe UI", 14), wraplength=800).pack(anchor="w")
        ttk.Label(body, text="PRIVATE ARCHIVE: includes profile details, source notes, original review and application history. Keep for your own records; do not send the whole dossier to an employer.", wraplength=800).pack(anchor="w", pady=8)
        ttk.Label(body, text="Choose a resume frozen for this exact review:").pack(anchor="w")
        self.versions = store.list_resumes(job_id)
        self.choices = tk.Listbox(body, height=3, exportselection=False)
        self.choices.pack(fill="x", pady=6)
        for version in self.versions:
            self.choices.insert("end", version["label"] + " | " + version["id"][:8])
        self.choices.bind("<<ListboxSelect>>", self.invalidate)
        ttk.Button(body, text="Preview dossier", command=self.preview).pack(anchor="w")
        tabs = ttk.Notebook(body)
        tabs.pack(fill="both", expand=True, pady=8)
        self.manifest = tk.Text(tabs, wrap="word", state="disabled", height=6)
        self.resume_text = tk.Text(tabs, wrap="word", state="disabled", height=6)
        tabs.add(self.manifest, text="Private manifest and files")
        tabs.add(self.resume_text, text="Frozen resume text")
        self.letter_text = tk.Text(tabs, wrap="word", state="disabled", height=6)
        tabs.add(self.letter_text, text="Frozen letter text")
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed this private archive and confirm local export.", variable=self.confirmed).pack(anchor="w")
        ttk.Button(body, text="Save upload-ready folder…", style="Primary.TButton", command=self.open_upload_folder).pack(anchor="w", pady=(6, 0))
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Export private dossier ZIP", command=self.export).pack(side="left")
        ttk.Button(actions, text="Export recipient ZIP", command=self.export_resume_files).pack(side="left", padx=8)
        letter_menu = tk.Menu(self, tearoff=False)
        letter_menu.add_command(label="Prepare letter from matching profile", command=self.prepare_matching_letter)
        letter_menu.add_command(label="Attach saved matching letter", command=self.attach_letter)
        letter_menu.add_command(label="Remove letter", command=self.clear_letter)
        ttk.Menubutton(actions, text="Letter", menu=letter_menu).pack(side="left")
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")
        self.status = tk.StringVar(value="Create a job-specific frozen resume first." if not self.versions else "No submission will be recorded or sent.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w")
        reserve_footer(body)
        polish_widgets(self)

    def invalidate(self, _event=None):
        self.prepared = None
        self.confirmed.set(False)
        for output in (self.manifest, self.resume_text, self.letter_text):
            output.configure(state="normal")
            output.delete("1.0", "end")
            output.configure(state="disabled")

    def preview(self):
        self.invalidate()
        try:
            selection = self.choices.curselection()
            if not selection:
                raise ValueError("Select an exact-review resume version")
            identifier = self.versions[selection[0]]["id"]
            payload = build_dossier(self.job, self.store.load_resume(identifier), self.store.application_history(self.job["id"]), letter=self.letter_snapshot)
            with zipfile.ZipFile(BytesIO(payload)) as archive:
                manifest = archive.read("manifest.json").decode("utf-8")
                resume = archive.read("resume.txt").decode("utf-8")
                letter = archive.read("cover-letter.txt").decode("utf-8") if "cover-letter.txt" in archive.namelist() else "No letter attached."
            for output, content in ((self.manifest, manifest), (self.resume_text, resume), (self.letter_text, letter)):
                output.configure(state="normal")
                output.insert("1.0", content)
                output.configure(state="disabled")
            self.prepared = (identifier, payload)
            self.status.set("Exact bytes prepared. Review the privacy warning and files, then confirm.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def prepare_matching_letter(self):
        try:
            selection = self.choices.curselection()
            if not selection:
                raise ValueError("Select the frozen resume whose profile the letter should use")
            resume = self.store.load_resume(self.versions[selection[0]]["id"])["resume"]
            snapshot = decoded(resume["profile_snapshot_base64"], MAX_BYTES)
            profile, digest = profile_snapshot(snapshot)
            item = {"id": resume["profile_id"], "snapshot": snapshot,
                    "snapshot_sha256": digest, "profile": profile}
            return LetterWindow(self, item, self.job)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def attach_letter(self):
        try:
            selection = self.choices.curselection()
            if not selection:
                raise ValueError("Select the exact resume before attaching its matching letter")
            path = filedialog.askopenfilename(parent=self, filetypes=[("Private frozen letter", "*.json")])
            if not path:
                return
            snapshot, _record = read_letter(path)
            resume = self.store.load_resume(self.versions[selection[0]]["id"])
            build_dossier(self.job, resume, self.store.application_history(self.job["id"]), letter=snapshot)
            self.invalidate()
            self.letter_snapshot = snapshot
            self.status.set("Matching letter attached. Preview and review all documents before confirming.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def clear_letter(self):
        self.invalidate()
        self.letter_snapshot = None
        self.status.set("Letter removed from this draft dossier.")

    def open_upload_folder(self):
        selection = self.choices.curselection()
        if self.prepared is None or not self.confirmed.get() or not selection or self.versions[selection[0]]["id"] != self.prepared[0]:
            self.status.set("Preview the selected resume and confirm review before choosing upload files.")
            return
        return UploadWindow(self, self.prepared[1])

    def export_resume_files(self):
        try:
            selection = self.choices.curselection()
            if self.prepared is None or not self.confirmed.get() or not selection or self.versions[selection[0]]["id"] != self.prepared[0]:
                raise ValueError("Preview and confirm this exact resume selection first")
            value = simpledialog.askstring("Recipient documents", "Formats to include, separated by commas: txt, html, pdf, letter", parent=self)
            if value is None:
                return
            formats = [part.strip() for part in value.split(",")]
            payload = recipient_bytes(self.prepared[1], formats)
            if not messagebox.askyesno("Review resume files", "Export only: " + ", ".join("cover-letter.txt" if value == "letter" else "resume." + value for value in formats) + "\nPrivate evidence and history are excluded. Review the documents before sending them yourself.", parent=self):
                return
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".zip", filetypes=[("Resume documents only", "*.zip")])
            if path:
                publish_bytes(path, payload)
                self.status.set("Selected documents exported. Nothing was sent or marked applied.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def export(self):
        try:
            selection = self.choices.curselection()
            if self.prepared is None or not self.confirmed.get() or not selection or self.versions[selection[0]]["id"] != self.prepared[0]:
                raise ValueError("Preview this selection and confirm private export first")
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".zip", filetypes=[("Private application dossier", "*.zip")])
            if path:
                publish_bytes(path, self.prepared[1])
                self.status.set("Exact reviewed bytes exported. No application was submitted or stage changed.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))
