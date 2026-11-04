"""Local stage and follow-up observations for one exact saved review."""
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from desktop_theme import polish_widgets

from applications import STAGES, current_application


class ApplicationTracker(tk.Toplevel):
    def __init__(self, parent, store, identifier, on_change):
        item = store.load(identifier)
        super().__init__(parent)
        self.store, self.identifier, self.on_change = store, identifier, on_change
        self.title("RoleWeave · Application notes")
        self.geometry("800x620")
        self.minsize(650, 500)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(6, weight=1)
        ttk.Label(body, text=f"{item['company']} · {item['title']}", font=("Segoe UI", 14), wraplength=740).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(body, text=f"Saved review {identifier[:8]} · {item['market']}\n"
                  "Manual observations only. This does not submit applications or verify outcomes.",
                  wraplength=740).grid(row=1, column=0, columnspan=2, sticky="w", pady=8)
        self.stage = tk.StringVar(value="saved")
        self.follow_up = tk.StringVar()
        ttk.Label(body, text="Stage").grid(row=2, column=0, sticky="w")
        ttk.Combobox(body, textvariable=self.stage, values=STAGES, state="readonly").grid(row=2, column=1, sticky="ew")
        ttk.Label(body, text="Follow up · YYYY-MM-DD\nBlank clears the date").grid(row=3, column=0, sticky="w")
        ttk.Entry(body, textvariable=self.follow_up).grid(row=3, column=1, sticky="ew", pady=8)
        ttk.Label(body, text="Decision / observation note").grid(row=4, column=0, sticky="w")
        self.note = tk.Text(body, height=4, wrap="word")
        self.note.grid(row=4, column=1, sticky="ew")
        ttk.Label(body, text="History · earlier entries are preserved; add an entry to correct one").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self.history = tk.Text(body, height=8, wrap="word", state="disabled")
        self.history.grid(row=6, column=0, columnspan=2, sticky="nsew")
        self.status = tk.StringVar(value="Follow-up dates are local calendar dates. No background notifications.")
        ttk.Label(body, textvariable=self.status, wraplength=740).grid(row=7, column=0, columnspan=2, sticky="w", pady=8)
        ttk.Button(body, text="Record observation", style="Primary.TButton", command=self.record).grid(row=8, column=0, sticky="w")
        ttk.Button(body, text="Close", command=self.close).grid(row=8, column=1, sticky="e")
        ttk.Button(body, text="Export saved follow-up to calendar (.ics)…", command=self.export_calendar).grid(row=9, column=0, columnspan=2, sticky="w", pady=8)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    def refresh(self):
        events = self.store.application_history(self.identifier)
        self.current = current_application(events)
        self.stage.set(self.current["stage"])
        self.follow_up.set(self.current["follow_up"])
        lines = [f"#{event['revision']} · {event['recorded_at']} · {event['stage']}\n"
                 f"Follow-up: {event['follow_up'] or 'none'}\n{event['note']}" for event in events]
        self.history.configure(state="normal")
        self.history.delete("1.0", "end")
        self.history.insert("1.0", "\n\n".join(lines) or "No observations recorded for this saved review.")
        self.history.configure(state="disabled")

    def record(self):
        note = self.note.get("1.0", "end-1c")
        if self.stage.get() == self.current["stage"] and self.follow_up.get() == self.current["follow_up"] and not note.strip():
            self.status.set("No change to record. Add a note or change the stage/follow-up date.")
            return
        try:
            event = self.store.record_application(self.identifier, self.stage.get(), note, self.follow_up.get())
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(f"Could not record: {exc}")
            return
        self.current = event
        self.note.delete("1.0", "end")
        try:
            self.refresh()
            self.on_change(self.identifier)
            self.status.set("Observation saved. Earlier entries and original review bytes are unchanged.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(f"Observation saved, but view refresh failed: {exc}")

    def close(self):
        pending = (self.note.get("1.0", "end-1c").strip() or self.stage.get() != self.current["stage"]
                   or self.follow_up.get() != self.current["follow_up"])
        if pending and not messagebox.askyesno("Discard unrecorded tracking edits?",
                                              "These changes have not been recorded. Discard them?", parent=self):
            return
        self.destroy()

    def export_calendar(self):
        if (self.note.get("1.0", "end-1c").strip() or self.stage.get() != self.current["stage"]
                or self.follow_up.get() != self.current["follow_up"]):
            self.status.set("Record or discard tracking edits before exporting the saved follow-up.")
            return
        if not self.current["follow_up"] or self.current["stage"] in ("closed", "withdrawn"):
            self.status.set("Record an active follow-up date first.")
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".ics", filetypes=[("Calendar follow-up", "*.ics")])
        if not path:
            return
        try:
            self.store.export_follow_up(self.identifier, path)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.status.set("Private calendar file exported with job title/company and date; notes/resume excluded. Import it yourself in your calendar. Nothing sent; later changes need re-export.")
