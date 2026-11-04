"""Compare immutable related review snapshots without merging their tracking."""
import difflib
import json
import tkinter as tk
from tkinter import ttk

from desktop_theme import polish_widgets
from roleweave import review_snapshot


def review_difference(left, right):
    for item in (left, right):
        review_snapshot(item["snapshot"])
    before = json.dumps(json.loads(left["snapshot"]), ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    after = json.dumps(json.loads(right["snapshot"]), ensure_ascii=False, indent=2, sort_keys=True).splitlines()
    return "\n".join(difflib.unified_diff(before, after, fromfile=left["id"], tofile=right["id"], lineterm="")) or "No review JSON differences. Metadata or application observations may differ."


class ReviewHistory(tk.Toplevel):
    def __init__(self, parent, store, identifier):
        super().__init__(parent)
        self.store, self.current = store, store.load(identifier)
        self.title("RoleWeave - Related review versions")
        self.geometry("950x650")
        self.transient(parent)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Compare saved evidence versions", style="Section.TLabel").pack(anchor="w")
        ttk.Label(body, text="Related by exact source URL, or matching title/company when URL is blank. Tracking stays separate; this is not an application count.", wraplength=880).pack(anchor="w", pady=8)
        self.rows = [row for row in store.list_jobs() if
                     (self.current["source_url"] and row["source_url"] == self.current["source_url"]) or
                     (not self.current["source_url"] and row["title"] == self.current["title"] and row["company"] == self.current["company"])]
        self.versions = ttk.Combobox(body, state="readonly", values=[f"{r['captured_at'][:19]} UTC / {r['id'][:8]} / {r['stage']}" for r in self.rows])
        self.versions.pack(fill="x", pady=8)
        self.versions.bind("<<ComboboxSelected>>", self.compare)
        self.output = tk.Text(body, wrap="word", height=15, state="disabled")
        self.output.pack(fill="both", expand=True)
        ttk.Button(body, text="Close", command=self.destroy).pack(anchor="e", pady=8)
        from desktop_theme import reserve_footer
        reserve_footer(body)
        polish_widgets(self)
        if self.rows:
            self.versions.current(0)
            self.compare()

    def compare(self, _event=None):
        if self.versions.current() < 0:
            return
        try:
            content = review_difference(self.store.load(self.rows[self.versions.current()]["id"]), self.current)
        except (OSError, ValueError) as exc:
            content = str(exc)
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", content)
        self.output.configure(state="disabled")
