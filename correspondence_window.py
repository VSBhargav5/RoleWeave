"""Deliberately inspect a local email and record a selected exact excerpt."""
import hashlib
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from correspondence import record_correspondence
from desktop_theme import polish_widgets, reserve_footer
from mail_observation import MAX_MAIL_BYTES, mail_observation


class CorrespondenceWindow(tk.Toplevel):
    def __init__(self, parent, store, job_id, on_change):
        self.job = store.load(job_id)
        super().__init__(parent)
        self.store, self.on_change = store, on_change
        self.source = None
        self.title("RoleWeave - Review local correspondence")
        self.geometry("1000x760")
        self.minsize(850, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=self.job["company"] + " - " + self.job["title"], font=("Segoe UI", 14), wraplength=800).pack(anchor="w")
        ttk.Label(body, text="Choose a permitted local .eml file. Attachments and HTML are not opened. Select an exact plaintext excerpt; the recorded note does not authenticate the sender or change stage.", wraplength=800).pack(anchor="w", pady=8)
        ttk.Button(body, text="Open local email file", command=self.load_mail).pack(anchor="w")
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True, pady=8)
        preview = ttk.Frame(self.tabs)
        review = ttk.Frame(self.tabs)
        self.tabs.add(preview, text="Read original plaintext")
        self.tabs.add(review, text="Review selected observation")
        self.headers = tk.Text(preview, height=3, wrap="word", state="disabled")
        self.headers.pack(fill="x", pady=4)
        self.body_text = tk.Text(preview, height=5, wrap="word", state="disabled")
        self.body_text.pack(fill="both", expand=True)
        ttk.Button(preview, text="Use selected body excerpt", command=self.use_selection).pack(anchor="w", pady=8)
        ttk.Label(review, text="Exact source excerpt (at most 1400 characters)").pack(anchor="w")
        self.quote = tk.Text(review, height=4, wrap="word")
        self.quote.pack(fill="both", expand=True, pady=4)
        ttk.Label(review, text="Your observation (optional, at most 1000 characters)").pack(anchor="w")
        self.note = tk.Text(review, height=3, wrap="word")
        self.note.pack(fill="x", pady=4)
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed this permitted correspondence and selected excerpt.", variable=self.confirmed).pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Record reviewed observation", command=self.record).pack(side="left")
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="No mailbox account is connected. Original email and attachments remain outside the shelf.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w")
        self.baseline = self.state()
        self.protocol("WM_DELETE_WINDOW", self.close)
        reserve_footer(preview)
        reserve_footer(body)
        polish_widgets(self)

    def state(self):
        return (hashlib.sha256(self.source).hexdigest() if self.source is not None else None,
                self.quote.get("1.0", "end-1c"), self.note.get("1.0", "end-1c"))

    def load_mail(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Permitted local email", "*.eml")])
        if not path:
            return
        try:
            with open(path, "rb") as handle:
                source = handle.read(MAX_MAIL_BYTES + 1)
            observation = mail_observation(source)
            self.source = source
            self.confirmed.set(False)
            for output, content in ((self.headers, "\n".join(key + ": " + value for key, value in observation["headers"].items()) +
                      "\nIgnored attachments/messages: " + str(len(observation["ignored_attachment_names"]))),
                      (self.body_text, observation["body"])):
                output.configure(state="normal")
                output.delete("1.0", "end")
                output.insert("1.0", content)
                output.configure(state="disabled")
            self.quote.delete("1.0", "end")
            self.note.delete("1.0", "end")
            self.tabs.select(0)
            self.status.set("Plaintext loaded locally. Select an excerpt; message headers are not authenticated.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def use_selection(self):
        try:
            quote = self.body_text.get("sel.first", "sel.last")
            self.quote.delete("1.0", "end")
            self.quote.insert("1.0", quote)
            self.confirmed.set(False)
            self.tabs.select(1)
        except tk.TclError:
            self.status.set("Select plaintext in the email body first.")

    def record(self):
        try:
            if self.source is None:
                raise ValueError("Open a permitted local email first")
            record_correspondence(self.store, self.job["id"], self.source, self.quote.get("1.0", "end-1c"),
                                  self.note.get("1.0", "end-1c"), confirmed=self.confirmed.get())
            self.confirmed.set(False)
            self.baseline = self.state()
            self.status.set("Exact excerpt recorded; stage and follow-up retained. Original email is not copied.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        try:
            self.on_change(self.job["id"])
        except (OSError, ValueError, sqlite3.Error):
            self.status.set("Observation saved, but workspace refresh failed. Reopen the saved review.")

    def close(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard unrecorded correspondence?", "Close without recording these selected observations?", parent=self):
            return
        self.destroy()
