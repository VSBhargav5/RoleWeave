"""RoleWeave: manually save and review jobs locally on Windows."""
import argparse
from datetime import date
import json
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from job_store import JobStore
from evidence_editor import EvidenceEditor
from applications import STAGES
from application_tracker import ApplicationTracker
from profile_editor import CareerProfileEditor
from resume_builder import ResumeBuilder
from demo_data import seed_practice
from runtime_paths import APP_VERSION, default_database_path, new_practice_path
from startup_selftest import run_self_test
from discovery_window import DiscoveryWindow
from roleweave import MAX_BYTES, review_snapshot

MARKET_LABELS = {"India / remote from India": "india_remote", "International relocation": "relocation"}


class JobShelf(ttk.Frame):
    def __init__(self, root, store):
        super().__init__(root, padding=16)
        self.store = store
        self.loaded_review = None
        self.current_id = None
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(self, text=f"RoleWeave {APP_VERSION} · Your job workspace", font=("Segoe UI", 18)).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(self, text="Save selected postings. Review evidence and eligibility separately.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 12))
        toolbar = ttk.Frame(self)
        toolbar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        ttk.Button(toolbar, text="My career profile…", command=self.open_profile).pack(side="left")
        ttk.Button(toolbar, text="Build / export resume…", command=self.open_resume).pack(side="left", padx=8)
        ttk.Button(toolbar, text="Start here / help…", command=self.open_help).pack(side="left")
        self.profile_status = tk.StringVar()
        ttk.Label(toolbar, textvariable=self.profile_status, wraplength=330).pack(side="left", padx=12)
        left = ttk.Frame(self, padding=(0, 0, 16, 0))
        left.grid(row=3, column=0, sticky="nsew")
        self.search = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.search)
        ttk.Label(left, text="Search title, company, URL or latest note").pack(anchor="w")
        search.pack(fill="x")
        search.bind("<Return>", lambda _event: self.refresh())
        ttk.Button(left, text="Search / refresh", command=self.refresh).pack(fill="x", pady=4)
        ttk.Button(left, text="Discover public jobs…", command=self.open_discovery).pack(fill="x", pady=4)
        self.filter = tk.StringVar(value="All markets")
        chooser = ttk.Combobox(left, textvariable=self.filter, state="readonly",
                               values=["All markets", *MARKET_LABELS], width=30)
        chooser.pack(fill="x")
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.stage_filter = tk.StringVar(value="All stages")
        stage_filter = ttk.Combobox(left, textvariable=self.stage_filter, values=["All stages", *STAGES], state="readonly")
        stage_filter.pack(fill="x", pady=4)
        stage_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.due_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Follow-ups due today or earlier", variable=self.due_only, command=self.refresh).pack(anchor="w")
        self.jobs = tk.Listbox(left, width=34, height=10, exportselection=False)
        self.jobs.pack(fill="both", expand=True, pady=8)
        horizontal = ttk.Scrollbar(left, orient="horizontal", command=self.jobs.xview)
        horizontal.pack(fill="x")
        self.jobs.configure(xscrollcommand=horizontal.set)
        self.jobs.bind("<<ListboxSelect>>", self.open_selected)
        ttk.Button(left, text="Application notes / follow-up…", command=self.open_tracker).pack(fill="x", pady=4)
        ttk.Button(left, text="Export preparation pack…", command=self.export_pack).pack(fill="x", pady=4)
        ttk.Button(left, text="Export original review JSON…", command=self.export_selected).pack(fill="x")
        ttk.Button(left, text="Back up full shelf…", command=self.backup_shelf).pack(fill="x", pady=(8, 0))
        ttk.Button(left, text="Restore shelf backup…", command=self.restore_shelf).pack(fill="x", pady=4)
        right = ttk.Frame(self)
        right.grid(row=3, column=1, sticky="nsew")
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
        ttk.Button(actions, text="Save posting only", command=self.save).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(actions, text="Review evidence…", command=self.edit_evidence).grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(actions, text="Import review JSON…", command=self.import_review).grid(row=0, column=2, padx=4, pady=4)
        ttk.Button(actions, text="New posting", command=self.new_posting).grid(row=1, column=0, padx=4, pady=4)
        ttk.Button(actions, text="Reload saved review", command=self.reload_saved).grid(row=1, column=1, padx=4, pady=4)
        self.status = tk.StringVar(value="Local shelf. Network requests only through explicit discovery or AI actions. No application submissions.")
        ttk.Label(self, textvariable=self.status, wraplength=900).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))
        self.baseline = self.form_state()
        self.refresh()
        self.profile_changed()

    def profile_changed(self):
        profile = self.store.active_profile()
        self.profile_status.set("Profile: " + profile["profile"]["name"] if profile else "Start here: create your career profile and reviewed facts.")

    def open_discovery(self):
        if self.has_draft_changes():
            self.status.set("Save or discard posting edits before importing discovered jobs.")
            return
        return DiscoveryWindow(self.winfo_toplevel(), self.store, MARKET_LABELS, self.show_saved)

    def open_profile(self):
        try:
            job = self.store.load(self.current_id) if self.current_id else None
            return CareerProfileEditor(self.winfo_toplevel(), self.store, self.profile_changed, job)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open career profile", str(exc))

    def open_resume(self):
        if self.has_draft_changes():
            self.status.set("Save or discard posting edits before building a resume for the saved review.")
            return
        try:
            profile = self.store.active_profile()
            if profile is None:
                self.status.set("Start with My career profile: add your identity and reviewed facts before building a resume.")
                return
            job = self.store.load(self.current_id) if self.current_id else None
            return ResumeBuilder(self.winfo_toplevel(), self.store, profile, job,
                                 lambda: self.status.set("A reviewed resume version was saved. Export from the resume window."))
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open resumes", str(exc))

    def open_practice(self):
        try:
            store = JobStore(new_practice_path(self.store.path.parent))
            identifier = seed_practice(store)
            window = tk.Toplevel(self.winfo_toplevel())
            window.title(f"RoleWeave {APP_VERSION} - Synthetic practice")
            window.geometry("1100x760")
            window.minsize(900, 620)
            shelf = JobShelf(window, store)
            shelf.show_saved(identifier)
            shelf.status.set("Synthetic practice workspace. Your main shelf has not been changed.")
            window.protocol("WM_DELETE_WINDOW", shelf.close)
            return shelf
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open practice", str(exc))

    def open_help(self):
        window = tk.Toplevel(self.winfo_toplevel())
        window.title(f"RoleWeave {APP_VERSION} - Getting started")
        window.geometry("820x620")
        window.transient(self.winfo_toplevel())
        window.grab_set()
        body = ttk.Frame(window, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Start with one job and facts you can defend", font=("Segoe UI", 16)).pack(anchor="w")
        instructions = ["1. My career profile: enter your identity, summary and sourced facts. Choose each fact's section and review it.",
                        "2. Paste a permitted job posting, choose its market and save it. Keep India/remote and relocation separate.",
                        "3. Review evidence: copy relevant career facts, select exact requirement quotes and link them deliberately.",
                        "4. Build a resume: select reviewed claims, preview and approve. Save a frozen version, then export HTML/PDF.",
                        "5. Application notes: record your decisions and follow-up dates. These are manual observations, not submissions.",
                        "6. Back up the full shelf regularly. V3 includes your profile, resume versions and application history."]
        for instruction in instructions:
            ttk.Label(body, text=instruction, wraplength=760).pack(anchor="w", pady=7)
        ttk.Label(body, text=f"Current database:\n{self.store.path.resolve()}\nExports and backups contain private information and are not encrypted.",
                  wraplength=760).pack(anchor="w", pady=12)
        ttk.Label(body, text="Moving from a source checkout to a standalone portable app? Back up here, then restore in the new app. Source and portable defaults use different data folders.",
                  wraplength=760).pack(anchor="w", pady=6)
        def practice():
            window.destroy()
            self.open_practice()
        ttk.Button(body, text="Open separate synthetic practice workspace", command=practice).pack(anchor="w", pady=10)
        ttk.Button(body, text="Close", command=window.destroy).pack(anchor="e")

    def refresh(self):
        try:
            rows = self.store.list_jobs(MARKET_LABELS.get(self.filter.get()),
                                        stage=None if self.stage_filter.get() == "All stages" else self.stage_filter.get(),
                                        query=self.search.get(), due_on=date.today().isoformat() if self.due_only.get() else None)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.rows = rows
        self.jobs.delete(0, "end")
        for item in self.rows:
            due = f" · follow-up {item['follow_up']}" if item['follow_up'] else ""
            self.jobs.insert("end", f"[{item['stage']}] {item['company']} · {item['title']}{due}")
        self.select_job(self.current_id)

    def select_job(self, identifier):
        self.jobs.selection_clear(0, "end")
        for index, item in enumerate(self.rows):
            if item["id"] == identifier:
                self.jobs.selection_set(index)
                break

    def tracking_changed(self, identifier):
        self.refresh()
        self.select_job(identifier)

    def open_tracker(self):
        if self.has_draft_changes():
            self.status.set("Save your posting edits or Reload saved review before tracking its saved version.")
            return
        if not self.jobs.curselection():
            self.status.set("Select a saved review to track. Tracking does not submit applications.")
            return
        try:
            return ApplicationTracker(self.winfo_toplevel(), self.store,
                                      self.rows[self.jobs.curselection()[0]]["id"], self.tracking_changed)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open tracking", str(exc))

    def details(self):
        return [self.fields[key].get() for key in self.fields]

    def form_state(self):
        return (tuple(self.details()), self.market.get(), self.posting.get("1.0", "end-1c"))

    def has_draft_changes(self):
        return self.form_state() != self.baseline

    def discard_draft(self):
        return not self.has_draft_changes() or messagebox.askyesno(
            "Discard unsaved posting edits?", "The posting edits have not been saved. Discard them?",
            parent=self.winfo_toplevel())

    def close(self):
        if self.discard_draft():
            self.winfo_toplevel().destroy()

    def show_saved(self, identifier):
        self.filter.set("All markets")
        self.stage_filter.set("All stages")
        self.search.set("")
        self.due_only.set(False)
        self.refresh()
        self.select_job(identifier)
        self.load_job(identifier)

    def reload_saved(self):
        if self.current_id is None:
            self.status.set("Select a saved review first, or choose New posting to clear an unsaved draft.")
            return
        if not self.discard_draft():
            return
        identifier = self.current_id
        self.select_job(identifier)
        try:
            self.load_job(identifier)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not reload", str(exc))

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
            identifier = self.store.save(snapshot, *self.details())
            self.show_saved(identifier)
            self.show_evidence("New snapshot saved without requirements or evidence links. Original reviews remain saved.")
            self.status.set("New posting snapshot saved. No requirements or career evidence reviewed yet.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save", str(exc))

    def edit_evidence(self):
        data = {"market": MARKET_LABELS[self.market.get()],
                "posting": self.posting.get("1.0", "end-1c"),
                "facts": self.loaded_review["facts"] if self.loaded_review else [],
                "requirements": self.loaded_review["requirements"] if self.loaded_review else []}
        details = self.details()

        def save_review(review_data):
            snapshot = json.dumps(review_data, ensure_ascii=False).encode("utf-8")
            try:
                identifier = self.store.save(snapshot, *details)
            except sqlite3.Error as exc:
                raise ValueError("Database write failed; review was not saved") from exc
            self.show_saved(identifier)
            self.status.set("Reviewed snapshot saved. Original snapshots are preserved; links do not verify qualification.")

        return EvidenceEditor(self.winfo_toplevel(), data, save_review, self.store.active_profile())

    def open_selected(self, _event=None):
        if not self.jobs.curselection():
            return
        identifier = self.rows[self.jobs.curselection()[0]]["id"]
        if identifier == self.current_id:
            return
        if not self.discard_draft():
            self.select_job(self.current_id)
            return
        try:
            self.load_job(identifier)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open", str(exc))

    def load_job(self, identifier):
        item = self.store.load(identifier)
        data = json.loads(item["snapshot"])
        self.loaded_review = data
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
        self.current_id = identifier
        self.baseline = self.form_state()
        self.status.set(f"Snapshot {item['input_sha256'][:12]} · {count} requirement(s). "
                        "Review evidence to edit links; Save posting only discards links in the new snapshot. "
                        "Export JSON to inspect its evidence. Eligibility and completeness are unverified.")

    def new_posting(self):
        if not self.discard_draft():
            return
        self.loaded_review = None
        self.current_id = None
        self.jobs.selection_clear(0, "end")
        for field in self.fields.values():
            field.delete(0, "end")
        self.posting.delete("1.0", "end")
        self.baseline = self.form_state()
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
        if self.has_draft_changes():
            self.status.set("Save or discard posting edits before exporting a saved review.")
            return
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

    def backup_shelf(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("RoleWeave backup", "*.json")])
        if not path:
            return
        try:
            count = self.store.backup(path)
            self.status.set(f"Backed up {count} snapshots including job metadata and evidence. Keep this unencrypted file private.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not back up", str(exc))

    def export_pack(self):
        if self.has_draft_changes():
            self.status.set("Save your posting edits or Reload saved review before exporting its saved preparation pack.")
            return
        if not self.jobs.curselection():
            self.status.set("Select a saved review to export its preparation pack.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Preparation pack", "*.txt")])
        if not path:
            return
        try:
            self.store.export_preparation_pack(self.rows[self.jobs.curselection()[0]]["id"], path)
            self.status.set("Private preparation pack exported from saved evidence and history. No application was submitted.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not export preparation pack", str(exc))

    def restore_shelf(self):
        path = filedialog.askopenfilename(filetypes=[("RoleWeave backup", "*.json")])
        if not path:
            return
        try:
            added, skipped = self.store.restore(path)
            self.refresh()
            self.status.set(f"Restored {added} snapshots; skipped {skipped} already saved. Compatible tracking history restored; existing jobs preserved.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not restore", str(exc))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"RoleWeave {APP_VERSION}")
    paths = parser.add_mutually_exclusive_group()
    paths.add_argument("--db", type=Path)
    paths.add_argument("--demo", action="store_true", help="Open a fresh separate synthetic practice shelf")
    paths.add_argument("--self-test", type=Path, help="Verify this runtime using a new synthetic output folder")
    args = parser.parse_args()
    if args.self_test:
        raise SystemExit(0 if run_self_test(args.self_test, JobShelf) else 2)
    root = tk.Tk()
    root.title(f"RoleWeave {APP_VERSION} - {'Synthetic practice' if args.demo else 'Job workspace'}")
    root.geometry("1100x760")
    root.minsize(900, 620)
    try:
        path = new_practice_path(default_database_path().parent) if args.demo else args.db or default_database_path()
        store = JobStore(path)
        identifier = seed_practice(store) if args.demo else None
        shelf = JobShelf(root, store)
        if identifier:
            shelf.show_saved(identifier)
            shelf.status.set("Synthetic practice only. Your main workspace is unchanged.")
        elif not store.list_jobs() and not store.active_profile():
            shelf.status.set("Welcome. Start with My career profile, or use Start here / help to open a separate synthetic practice workspace.")
        root.protocol("WM_DELETE_WINDOW", shelf.close)
    except (OSError, sqlite3.Error, ValueError) as exc:
        messagebox.showerror("Could not open local database", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
