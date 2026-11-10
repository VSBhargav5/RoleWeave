"""Review the exact private dossier bytes before deliberate local export."""
from io import BytesIO
import json
import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk
import zipfile

from application_dossier import build_dossier
from desktop_theme import polish_widgets, reserve_footer
from safe_export import publish_bytes


class DossierWindow(tk.Toplevel):
    def __init__(self, parent, store, job_id):
        self.job = store.load(job_id)
        super().__init__(parent)
        self.store, self.prepared = store, None
        self.title("RoleWeave - Private application dossier")
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
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed this private archive and confirm local export.", variable=self.confirmed).pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Export private dossier ZIP", command=self.export).pack(side="left")
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")
        self.status = tk.StringVar(value="Create a job-specific frozen resume first." if not self.versions else "No submission will be recorded or sent.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w")
        reserve_footer(body)
        polish_widgets(self)

    def invalidate(self, _event=None):
        self.prepared = None
        self.confirmed.set(False)
        for output in (self.manifest, self.resume_text):
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
            payload = build_dossier(self.job, self.store.load_resume(identifier), self.store.application_history(self.job["id"]))
            with zipfile.ZipFile(BytesIO(payload)) as archive:
                manifest = archive.read("manifest.json").decode("utf-8")
                resume = archive.read("resume.txt").decode("utf-8")
            for output, content in ((self.manifest, manifest), (self.resume_text, resume)):
                output.configure(state="normal")
                output.insert("1.0", content)
                output.configure(state="disabled")
            self.prepared = (identifier, payload)
            self.status.set("Exact bytes prepared. Review the privacy warning and files, then confirm.")
        except (OSError, ValueError, sqlite3.Error) as exc:
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
