"""Review, freeze and export a resume from a specific career profile version."""
import hashlib
import os
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
from desktop_theme import polish_widgets, reserve_footer

from resume_render import MAX_RESUME_BYTES, PDF_AVAILABLE, resume_text
from career_profile import profile_snapshot
from resume_versions import decoded


class ResumeBuilder(tk.Toplevel):
    def __init__(self, parent, store, profile, job=None, on_save=lambda: None):
        super().__init__(parent)
        self.store, self.profile, self.job, self.on_save = store, profile, job, on_save
        self.prepared = None
        self.last_export = None
        self.current_version = None
        self.title("RoleWeave - Resume versions")
        self.geometry("1000x800")
        self.minsize(800, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Build a resume from facts you reviewed", font=("Segoe UI", 16)).pack(anchor="w")
        context = f"New resume source: {profile['profile']['name']} - profile version {profile['id'][:8]}"
        if job:
            context += f"\nFor saved review: {job['company']} - {job['title']} ({job['id'][:8]})"
        ttk.Label(body, text=context, wraplength=920).pack(anchor="w", pady=8)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        create = ttk.Frame(self.tabs, padding=12)
        saved = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(create, text="Select and review")
        self.tabs.add(saved, text="Saved versions / export")
        self.label = tk.StringVar(value=f"{job['title']} - {job['company']}" if job else "General resume")
        ttk.Label(create, text="Version label (for your records; not printed)").pack(anchor="w")
        label = ttk.Entry(create, textvariable=self.label)
        label.pack(fill="x", pady=4)
        label.bind("<KeyRelease>", self.invalidate)
        ttk.Label(create, text="Select relevant reviewed claims (Ctrl-click for multiple). Unreviewed claims are excluded.", wraplength=880).pack(anchor="w")
        self.choices = [fact for fact in profile["profile"]["facts"] if fact["reviewed"]]
        self.facts = tk.Listbox(create, height=4, selectmode="extended", exportselection=False)
        self.facts.pack(fill="x", pady=6)
        for fact in self.choices:
            self.facts.insert("end", f"{fact['section']} - {fact['claim']}")
        self.facts.bind("<<ListboxSelect>>", self.invalidate)
        ttk.Button(create, text="Preview exact resume text", command=self.preview).pack(anchor="w", pady=4)
        self.preview_text = tk.Text(create, height=8, wrap="word", state="disabled")
        self.preview_text.pack(fill="both", expand=True, pady=6)
        self.include_pdf = tk.BooleanVar(value=PDF_AVAILABLE)
        ttk.Checkbutton(create, text="Include PDF (choose HTML-only if a character is unsupported)", variable=self.include_pdf,
                        command=self.invalidate, state="normal" if PDF_AVAILABLE else "disabled").pack(anchor="w")
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(create, text="I reviewed this resume's identity, summary and selected claims", variable=self.confirmed).pack(anchor="w", pady=6)
        ttk.Button(create, text="Save frozen resume version", style="Primary.TButton", command=self.save).pack(anchor="w", pady=6)
        self.only_this_job = tk.BooleanVar(value=job is not None)
        ttk.Checkbutton(saved, text="Only versions for this exact saved job review", variable=self.only_this_job,
                        command=self.refresh_versions, state="normal" if job else "disabled").pack(anchor="w")
        self.versions = tk.Listbox(saved, height=7, exportselection=False)
        self.versions.pack(fill="x")
        self.versions.bind("<<ListboxSelect>>", self.load_version)
        self.saved_provenance = tk.StringVar(value="Select a saved version to inspect its frozen profile and document content.")
        ttk.Label(saved, textvariable=self.saved_provenance, wraplength=880).pack(anchor="w", pady=6)
        self.saved_preview = tk.Text(saved, height=10, wrap="word", state="disabled")
        self.saved_preview.pack(fill="both", expand=True, pady=8)
        exports = ttk.Frame(saved)
        exports.pack(fill="x")
        ttk.Button(exports, text="Export saved HTML…", command=lambda: self.export("html")).pack(side="left")
        self.pdf_button = ttk.Button(exports, text="Export saved PDF…", command=lambda: self.export("pdf"), state="disabled")
        self.pdf_button.pack(side="left", padx=8)
        ttk.Button(exports, text="Export text…", command=lambda: self.export("txt")).pack(side="left", padx=8)
        self.open_button = ttk.Button(exports, text="Open exported file", command=self.open_exported, state="disabled")
        self.open_button.pack(side="left")
        self.status = tk.StringVar(value="Choose relevant facts and preview. Nothing is rewritten, inferred or sent.")
        ttk.Label(body, textvariable=self.status, wraplength=920).pack(anchor="w", pady=8)
        ttk.Button(body, text="Close", command=self.close).pack(anchor="e")
        self.baseline = self.selection_state()
        self.refresh_versions()
        if not self.choices:
            self.status.set("No reviewed career facts are available. Close this window and review facts in My career profile.")
        reserve_footer(body)
        reserve_footer(create)
        reserve_footer(saved)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def selection_state(self):
        return (self.label.get(), tuple(self.choices[i]["id"] for i in self.facts.curselection()), self.include_pdf.get())

    def invalidate(self, _event=None):
        self.prepared = None
        self.confirmed.set(False)
        self.set_preview(self.preview_text, "Selection changed. Preview again before reviewing and saving.")
        self.status.set("Selection changed. Preview again, then review before saving.")

    def set_preview(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def preview(self):
        identifiers = list(self.selection_state()[1])
        self.confirmed.set(False)
        try:
            text = resume_text(self.profile["profile"], identifiers)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.set_preview(self.preview_text, text)
        self.prepared = self.selection_state()
        self.status.set("Review this exact text. Sources and unselected facts stay in your private records, not the exported resume.")

    def save(self):
        if self.prepared != self.selection_state() or not self.confirmed.get():
            self.status.set("Preview the current selection and explicitly confirm your review first.")
            return
        try:
            identifier = self.store.create_resume(self.profile["id"], list(self.selection_state()[1]), self.label.get(),
                                                   self.job["id"] if self.job else None, self.include_pdf.get(), confirmed=True)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.baseline = self.selection_state()
        self.confirmed.set(False)
        self.refresh_versions()
        self.versions.selection_set(next(i for i, row in enumerate(self.rows) if row["id"] == identifier))
        self.load_version()
        self.tabs.select(1)
        self.on_save()
        self.status.set("Resume version saved. Export it below and inspect the document before using it.")

    def refresh_versions(self):
        self.rows = self.store.list_resumes(self.job["id"] if self.job and self.only_this_job.get() else None)
        self.current_version = None
        self.pdf_button.configure(state="disabled")
        self.set_preview(self.saved_preview, "Select a version from this list. Broaden the filter to see other jobs or general resumes.")
        self.versions.delete(0, "end")
        for item in self.rows:
            formats = "HTML + PDF" if item["has_pdf"] else "HTML-only"
            self.versions.insert("end", f"{item['created_at'][:19]} UTC - {item['label']} [{formats}]")

    def load_version(self, _event=None):
        if not self.versions.curselection():
            return
        try:
            item = self.store.load_resume(self.rows[self.versions.curselection()[0]]["id"])
            record = item["resume"]
            profile, _digest = profile_snapshot(decoded(record["profile_snapshot_base64"], 1024 * 1024))
            self.set_preview(self.saved_preview, resume_text(profile, record["selected_fact_ids"]))
            self.current_version = item["id"]
            self.saved_provenance.set(f"Saved version {item['id'][:8]} - {record['label']}\n"
                                      f"Frozen identity: {profile['name']} - profile {record['profile_id'][:8]}")
            self.pdf_button.configure(state="normal" if record["pdf_base64"] else "disabled")
            self.status.set("Saved version loaded. Future profile changes do not change these stored document bytes.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.current_version = None
            self.status.set(str(exc))

    def export(self, format):
        if self.current_version is None:
            self.status.set("Select a saved resume version first.")
            return
        path = filedialog.asksaveasfilename(defaultextension="." + format,
                                          initialfile=f"resume-{self.current_version[:8]}.{format}",
                                          filetypes=[(format.upper() + " resume", "*." + format)])
        if not path:
            return
        try:
            self.export_sha = self.store.export_resume(self.current_version, path, format)
            self.last_export = Path(path)
            self.open_button.configure(state="normal")
            self.status.set(f"Saved {format.upper()} to {path}. The exported document contains no private source notes.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def open_exported(self):
        if self.last_export is None:
            return
        try:
            with self.last_export.open("rb") as source:
                payload = source.read(MAX_RESUME_BYTES + 1)
            if hashlib.sha256(payload).hexdigest() != self.export_sha:
                raise ValueError("Exported file changed. Re-export the saved version to a new filename before opening it here.")
            if os.name == "nt":
                os.startfile(str(self.last_export.resolve()))
            else:
                webbrowser.open(self.last_export.resolve().as_uri())
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def close(self):
        if self.selection_state() != self.baseline and not messagebox.askyesno("Discard resume selection?", "This selection has not been saved as a resume version. Discard it?", parent=self):
            return
        self.destroy()
