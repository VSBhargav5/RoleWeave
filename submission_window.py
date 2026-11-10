"""Explicit manual submission observations; no sending or provider access."""
from datetime import date
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from application_dossier import JOB_FIELDS, MAX_DOSSIER_BYTES, verify_dossier_bytes
from desktop_theme import polish_widgets, reserve_footer
from submission_receipt import CHANNELS, record_submission


class SubmissionWindow(tk.Toplevel):
    def __init__(self, parent, store, job_id, on_change):
        self.job = store.load(job_id)
        super().__init__(parent)
        self.store, self.on_change = store, on_change
        self.dossier = None
        self.title("RoleWeave - Report a manual submission")
        self.geometry("900x700")
        self.minsize(850, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=self.job["company"] + " - " + self.job["title"], font=("Segoe UI", 14), wraplength=800).pack(anchor="w")
        ttk.Label(body, text="Record an application you submitted yourself. A prepared dossier links the evidence version; it does not prove which files were sent.", wraplength=800).pack(anchor="w", pady=8)
        ttk.Button(body, text="Choose and verify prepared dossier", command=self.load_dossier).pack(anchor="w")
        self.evidence = tk.StringVar(value="No prepared dossier selected.")
        ttk.Label(body, textvariable=self.evidence, wraplength=800).pack(anchor="w", pady=8)
        form = ttk.Frame(body)
        form.pack(fill="x")
        self.submitted_on = tk.StringVar(value=date.today().isoformat())
        self.channel = tk.StringVar(value="")
        self.reference = tk.StringVar()
        ttk.Label(form, text="Your observed date (YYYY-MM-DD)").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.submitted_on).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Label(form, text="Your submission channel").grid(row=1, column=0, sticky="w", pady=8)
        ttk.Combobox(form, textvariable=self.channel, values=CHANNELS, state="readonly").grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Label(form, text="Your reference (optional)").grid(row=2, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.reference).grid(row=2, column=1, sticky="ew", padx=8)
        form.columnconfigure(1, weight=1)
        ttk.Label(body, text="Your observation / correction context").pack(anchor="w", pady=(12, 4))
        self.note = tk.Text(body, height=4, wrap="word")
        self.note.pack(fill="both", expand=True)
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I personally submitted an application and confirm this observation.", variable=self.confirmed).pack(anchor="w", pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        ttk.Button(actions, text="Record my submission observation", command=self.record).pack(side="left")
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="Records applied as a manual history revision; current follow-up is retained.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w", pady=8)
        self.baseline = self.state()
        self.protocol("WM_DELETE_WINDOW", self.close)
        reserve_footer(body)
        polish_widgets(self)

    def state(self):
        return (self.submitted_on.get(), self.channel.get(), self.reference.get(), self.note.get("1.0", "end-1c"), self.dossier)

    def load_dossier(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Private application dossier", "*.zip")])
        if not path:
            return
        try:
            with open(path, "rb") as handle:
                payload = handle.read(MAX_DOSSIER_BYTES + 1)
            report = verify_dossier_bytes(payload)
            if report["job"] != {key: self.job[key] for key in JOB_FIELDS}:
                raise ValueError("Dossier belongs to a different exact saved review")
            self.dossier = payload
            self.confirmed.set(False)
            self.evidence.set("Prepared dossier " + report["sha256"] + "\nFrozen resume " + report["resume_id"])
            self.status.set("Dossier verified. Enter your own submission details and confirm.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def record(self):
        try:
            if self.dossier is None:
                raise ValueError("Choose and verify the matching prepared dossier first")
            record_submission(self.store, self.job["id"], self.dossier, self.submitted_on.get(),
                              self.channel.get(), self.reference.get(), self.note.get("1.0", "end-1c"),
                              confirmed=self.confirmed.get())
            self.confirmed.set(False)
            self.baseline = self.state()
            self.status.set("User-reported submission recorded; original evidence and earlier history retained.")
            self.on_change(self.job["id"])
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.confirmed.set(False)
            self.status.set(str(exc))

    def close(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard unrecorded observation?", "Close without recording these submission details?", parent=self):
            return
        self.destroy()
