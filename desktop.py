"""RoleWeave: manually save and review jobs locally on Windows."""
import argparse
import json
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from job_store import JobStore
from roleweave import MAX_BYTES, review_snapshot

MARKET_LABELS = {"India / remote from India": "india_remote", "International relocation": "relocation"}


class JobShelf(ttk.Frame):
    def __init__(self, root, store):
        super().__init__(root, padding=16)
        self.store = store
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="RoleWeave · Your local job shelf", font=("Segoe UI", 18)).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Save selected postings. Review evidence and eligibility separately.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))
        left = ttk.Frame(self, padding=(0, 0, 16, 0))
        left.grid(row=2, column=0, sticky="nsew")
        self.filter = tk.StringVar(value="All markets")
        chooser = ttk.Combobox(left, textvariable=self.filter, state="readonly",
                               values=["All markets", *MARKET_LABELS], width=30)
        chooser.pack(fill="x")
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.jobs = tk.Listbox(left, width=34, height=18, exportselection=False)
        self.jobs.pack(fill="both", expand=True, pady=8)
        self.jobs.bind("<<ListboxSelect>>", self.open_selected)
        ttk.Button(left, text="Export original review JSON…", command=self.export_selected).pack(fill="x")
        right = ttk.Frame(self)
        right.grid(row=2, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)
        self.fields = {}
        for row, label in enumerate(("Job title", "Company", "Source URL (optional)")):
            ttk.Label(right, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
            field = ttk.Entry(right)
            field.grid(row=row, column=1, sticky="ew")
            self.fields[label] = field
        ttk.Label(right, text="Market").grid(row=3, column=0, sticky="w")
        self.market = tk.StringVar(value=next(iter(MARKET_LABELS)))
        ttk.Combobox(right, textvariable=self.market, state="readonly",
                     values=list(MARKET_LABELS)).grid(row=3, column=1, sticky="ew", pady=4)
        ttk.Label(right, text="Posting text · paste a permitted posting, or select a saved job below").grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 4))
        self.posting = tk.Text(right, wrap="word", height=15, undo=True)
        self.posting.grid(row=5, column=0, columnspan=2, sticky="nsew")
        right.rowconfigure(5, weight=1)
        self.evidence = tk.Text(right, wrap="word", height=6, state="disabled")
        self.evidence.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.show_evidence("No saved review selected. New postings have no reviewed evidence.")
        actions = ttk.Frame(right)
        actions.grid(row=7, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Button(actions, text="Save as new snapshot", command=self.save).pack(side="left")
        ttk.Button(actions, text="Import review JSON…", command=self.import_review).pack(side="left", padx=8)
        ttk.Button(actions, text="New posting", command=self.new_posting).pack(side="left")
        self.status = tk.StringVar(value="Local only. No scraping, AI requests or application submissions.")
        ttk.Label(self, textvariable=self.status, wraplength=900).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.refresh()

    def refresh(self):
        self.rows = self.store.list_jobs(MARKET_LABELS.get(self.filter.get()))
        self.jobs.delete(0, "end")
        for item in self.rows:
            self.jobs.insert("end", f"{item['company']} · {item['title']}")

    def details(self):
        return [self.fields[key].get() for key in self.fields]

    def show_evidence(self, value):
        self.evidence.configure(state="normal")
        self.evidence.delete("1.0", "end")
        self.evidence.insert("1.0", value)
        self.evidence.configure(state="disabled")

    def save(self):
        try:
            data = {"market": MARKET_LABELS[self.market.get()],
                    "posting": self.posting.get("1.0", "end-1c"), "facts": [], "requirements": []}
            snapshot = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.store.save(snapshot, *self.details())
            self.refresh()
            self.show_evidence("New snapshot saved without requirements or evidence links. Original reviews remain saved.")
            self.status.set("New posting snapshot saved. No requirements or career evidence reviewed yet.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save", str(exc))

    def open_selected(self, _event=None):
        if not self.jobs.curselection():
            return
        try:
            item = self.store.load(self.rows[self.jobs.curselection()[0]]["id"])
            data = json.loads(item["snapshot"])
            for key, value in zip(self.fields, (item["title"], item["company"], item["source_url"])):
                self.fields[key].delete(0, "end")
                self.fields[key].insert(0, value)
            self.market.set(next(label for label, code in MARKET_LABELS.items() if code == item["market"]))
            self.posting.delete("1.0", "end")
            self.posting.insert("1.0", data["posting"])
            count = len(item["review"]["requirements"])
            lines = []
            for requirement in item["review"]["requirements"]:
                lines.append(f"{requirement['state']}: {requirement['quote']}")
                lines.extend(f"  {fact['claim']} (source: {fact['source']})" for fact in requirement["evidence"])
            self.show_evidence("\n".join(lines) or "No reviewed requirements in this snapshot.")
            self.status.set(f"Snapshot {item['input_sha256'][:12]} · {count} requirement(s). "
                            "Edits save a new posting with no evidence links; original review is preserved. "
                            "Export JSON to inspect its evidence. Eligibility and completeness are unverified.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open", str(exc))

    def new_posting(self):
        self.jobs.selection_clear(0, "end")
        for field in self.fields.values():
            field.delete(0, "end")
        self.posting.delete("1.0", "end")
        self.show_evidence("No saved review selected. New postings have no reviewed evidence.")
        self.status.set("New posting. Choose its market before saving.")

    def import_review(self):
        path = filedialog.askopenfilename(filetypes=[("Review JSON", "*.json")])
        if not path:
            return
        try:
            with Path(path).open("rb") as source:
                snapshot = source.read(MAX_BYTES + 1)
            review_snapshot(snapshot)
            self.store.save(snapshot, *self.details())
            self.refresh()
            self.status.set("Original JSON bytes imported. Its declared market is authoritative. Select it to inspect.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not import", str(exc))

    def export_selected(self):
        if not self.jobs.curselection():
            self.status.set("Select a saved job before exporting its original review.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Review JSON", "*.json")])
        if not path:
            return
        try:
            self.store.export(self.rows[self.jobs.curselection()[0]]["id"], path)
            self.status.set("Original review bytes exported. Job title/company/URL are only in the database.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not export", str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).parent / "private" / "jobs.db")
    args = parser.parse_args()
    root = tk.Tk()
    root.title("RoleWeave · Local job shelf")
    root.geometry("1050x700")
    root.minsize(800, 550)
    try:
        JobShelf(root, JobStore(args.db))
    except (OSError, sqlite3.Error, ValueError) as exc:
        messagebox.showerror("Could not open local database", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
