"""RoleWeave: manually save and review jobs locally on Windows."""
import argparse
from datetime import date
import json
from pathlib import Path
import sqlite3
import tkinter as tk
import webbrowser
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
from desktop_theme import apply_theme, polish_widgets
from source_links import source_link

MARKET_LABELS = {"India / remote from India": "india_remote", "International relocation": "relocation"}


class JobShelf(ttk.Frame):
    def __init__(self, root, store):
        apply_theme(root)
        super().__init__(root, style="App.TFrame")
        self.store = store
        self.loaded_review = None
        self.current_id = None
        self.pack(fill="both", expand=True)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        rail = ttk.Frame(self, style="Rail.TFrame", padding=(16, 24), width=180)
        rail.grid(row=0, column=0, sticky="nsew")
        rail.grid_propagate(False)
        rail.columnconfigure(0, weight=1)
        rail.rowconfigure(8, weight=1)
        ttk.Label(rail, text="RoleWeave", style="Brand.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(rail, text="A considered next move.", style="RailMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 30))
        ttk.Label(rail, text="YOUR WORKSPACE", style="RailMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 10))
        ttk.Button(rail, text="  Job workspace", style="ActiveRail.TButton", command=self.focus_workspace).grid(row=3, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="  Discover jobs", style="Rail.TButton", command=self.open_discovery).grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="  Career profile", style="Rail.TButton", command=self.open_profile).grid(row=5, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="  Resume studio", style="Rail.TButton", command=self.open_resume).grid(row=6, column=0, sticky="ew", pady=3)
        ttk.Label(rail, text="LOCAL WORKSPACE", style="RailMuted.TLabel").grid(row=9, column=0, sticky="w", pady=(0, 8))
        ttk.Button(rail, text="Back up workspace", style="Rail.TButton", command=self.backup_shelf).grid(row=10, column=0, sticky="ew")
        ttk.Button(rail, text="Restore backup", style="Rail.TButton", command=self.restore_shelf).grid(row=11, column=0, sticky="ew")
        ttk.Button(rail, text="Getting started", style="Rail.TButton", command=self.open_help).grid(row=12, column=0, sticky="ew")
        ttk.Label(rail, text=f"v{APP_VERSION}  /  Windows\nYou control every send.", style="RailMuted.TLabel").grid(row=13, column=0, sticky="w", pady=(24, 0))

        workspace = ttk.Frame(self, style="App.TFrame", padding=(22, 20, 22, 12))
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.columnconfigure(0, weight=1)
        workspace.rowconfigure(3, weight=1)
        heading = ttk.Frame(workspace, style="App.TFrame")
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Make your next move.", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(heading, text="+  Add a job", style="Primary.TButton", command=self.new_posting).grid(row=0, column=1, sticky="e")
        self.profile_status = tk.StringVar()
        ttk.Label(heading, textvariable=self.profile_status, style="AppMuted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        metrics = ttk.Frame(workspace, style="App.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(18, 16))
        self.metric_values = {}
        for column, (key, label, note) in enumerate((("saved", "SAVED REVIEWS", "Snapshots, not unique applications"),
                                                   ("due", "FOLLOW-UPS DUE", "Active reminders through today"),
                                                   ("resumes", "RESUME VERSIONS", "Frozen documents you reviewed"))):
            metrics.columnconfigure(column, weight=1, uniform="metrics")
            card = ttk.Frame(metrics, padding=(14, 10))
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 10, 0))
            value = tk.StringVar(value="0")
            self.metric_values[key] = value
            ttk.Label(card, text=label, style="Eyebrow.TLabel").pack(anchor="w")
            ttk.Label(card, textvariable=value, style="Metric.TLabel").pack(anchor="w")
            ttk.Label(card, text=note, style="Muted.TLabel", font=("Segoe UI", 8)).pack(anchor="w")

        content = ttk.Frame(workspace, style="App.TFrame")
        content.grid(row=3, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        left = ttk.Frame(content, padding=14, width=280)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.grid_propagate(False)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(6, weight=1)
        ttk.Label(left, text="Your opportunities", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.library_count = tk.StringVar(value="No saved reviews")
        ttk.Label(left, textvariable=self.library_count, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 12))
        self.search = tk.StringVar()
        search = ttk.Entry(left, textvariable=self.search)
        search.grid(row=2, column=0, sticky="ew")
        search.bind("<Return>", lambda _event: self.refresh())
        ttk.Label(left, text="Search title, company or latest note", style="Muted.TLabel", font=("Segoe UI", 8)).grid(row=3, column=0, sticky="w", pady=(4, 10))
        filters = ttk.Frame(left)
        filters.grid(row=4, column=0, sticky="ew")
        self.filter = tk.StringVar(value="All markets")
        chooser = ttk.Combobox(filters, textvariable=self.filter, state="readonly", values=["All markets", *MARKET_LABELS], width=24)
        chooser.pack(fill="x")
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.stage_filter = tk.StringVar(value="All stages")
        stage_filter = ttk.Combobox(filters, textvariable=self.stage_filter, values=["All stages", *STAGES], state="readonly", width=24)
        stage_filter.pack(fill="x", pady=7)
        stage_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.due_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(filters, text="Follow-ups due", variable=self.due_only, command=self.refresh).pack(anchor="w")
        self.search_posting = tk.BooleanVar(value=False)
        ttk.Checkbutton(filters, text="Search posting text too", variable=self.search_posting, command=self.refresh).pack(anchor="w")
        ttk.Button(left, text="Apply search / refresh", command=self.refresh).grid(row=5, column=0, sticky="ew", pady=(8, 10))
        listing = ttk.Frame(left)
        listing.grid(row=6, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.jobs = tk.Listbox(listing, width=26, height=6, exportselection=False)
        self.jobs.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(listing, command=self.jobs.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(listing, orient="horizontal", command=self.jobs.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.jobs.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        self.jobs.bind("<<ListboxSelect>>", self.open_selected)
        self.empty_library = ttk.Label(self.jobs, text="No saved reviews yet.\nDiscover a role or add a job.", style="Muted.TLabel", wraplength=205, justify="center")

        right = ttk.Frame(content, padding=18)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self.review_title = tk.StringVar(value="Review a new opportunity")
        self.review_subtitle = tk.StringVar(value="Add a posting, then connect it to facts you can defend.")
        title_label = ttk.Label(right, textvariable=self.review_title, style="Section.TLabel", wraplength=520)
        title_label.grid(row=0, column=0, sticky="w")
        subtitle_label = ttk.Label(right, textvariable=self.review_subtitle, style="Muted.TLabel", wraplength=520)
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 12))
        right.bind("<Configure>", lambda event: (title_label.configure(wraplength=max(300, event.width - 36)), subtitle_label.configure(wraplength=max(300, event.width - 36))))
        self.detail_tabs = ttk.Notebook(right)
        self.detail_tabs.grid(row=2, column=0, sticky="nsew")
        posting_tab = ttk.Frame(self.detail_tabs, padding=(0, 12, 0, 0))
        evidence_tab = ttk.Frame(self.detail_tabs, padding=(0, 12, 0, 0))
        details_tab = ttk.Frame(self.detail_tabs, padding=(0, 12, 0, 0))
        self.detail_tabs.add(posting_tab, text="Job posting")
        self.detail_tabs.add(evidence_tab, text="Evidence & next steps")
        self.detail_tabs.add(details_tab, text="Job details")
        details_tab.columnconfigure(0, weight=1)
        details_tab.columnconfigure(1, weight=1)
        self.fields = {}
        for column, label in enumerate(("Job title", "Company")):
            cell = ttk.Frame(details_tab)
            cell.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0))
            ttk.Label(cell, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0, 4))
            field = ttk.Entry(cell, width=12)
            field.pack(fill="x")
            self.fields[label] = field
        ttk.Label(details_tab, text="Source URL (optional)", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w", pady=(16, 4))
        self.fields["Source URL (optional)"] = ttk.Entry(details_tab)
        self.fields["Source URL (optional)"].grid(row=2, column=0, columnspan=2, sticky="ew")
        self.market = tk.StringVar(value=next(iter(MARKET_LABELS)))
        ttk.Label(details_tab, text="Market", style="Muted.TLabel").grid(row=3, column=0, columnspan=2, sticky="w", pady=(16, 4))
        ttk.Combobox(details_tab, textvariable=self.market, state="readonly", values=list(MARKET_LABELS)).grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Label(details_tab, text="A market label keeps your search organized. It does not verify location eligibility or sponsorship.\n\nPaste the description in Job posting. Changes are saved only when you choose Save posting only or save a reviewed evidence version.", style="Muted.TLabel", wraplength=450).grid(row=5, column=0, columnspan=2, sticky="w", pady=20)
        posting_tab.columnconfigure(0, weight=1)
        posting_tab.rowconfigure(1, weight=1)
        ttk.Label(posting_tab, text="READ THE ROLE. KEEP THE ORIGINAL WORDING.", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.posting = tk.Text(posting_tab, wrap="word", height=6, undo=True)
        self.posting.grid(row=1, column=0, sticky="nsew")
        posting_scroll = ttk.Scrollbar(posting_tab, command=self.posting.yview)
        posting_scroll.grid(row=1, column=1, sticky="ns")
        self.posting.configure(yscrollcommand=posting_scroll.set)
        evidence_tab.columnconfigure(0, weight=1)
        evidence_tab.rowconfigure(1, weight=1)
        ttk.Label(evidence_tab, text="Exact quotes. Reviewed facts. Your decision.", style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))
        self.evidence = tk.Text(evidence_tab, wrap="word", height=8, state="disabled")
        self.evidence.grid(row=1, column=0, sticky="nsew")
        evidence_scroll = ttk.Scrollbar(evidence_tab, command=self.evidence.yview)
        evidence_scroll.grid(row=1, column=1, sticky="ns")
        self.evidence.configure(yscrollcommand=evidence_scroll.set)
        self.show_evidence("No saved review selected. Save a posting, then review its requirements and career evidence.")
        next_actions = ttk.Frame(evidence_tab)
        next_actions.grid(row=2, column=0, sticky="ew", pady=10)
        ttk.Button(next_actions, text="Application notes / follow-up", command=self.open_tracker).pack(side="left")
        export_menu = tk.Menu(self, tearoff=False)
        export_menu.add_command(label="Preparation pack (.txt)", command=self.export_pack)
        export_menu.add_command(label="Original review (.json)", command=self.export_selected)
        export_menu.add_command(label="Import review JSON…", command=self.import_review)
        export_menu.add_command(label="Open saved source posting in browser", command=self.open_source)
        ttk.Menubutton(next_actions, text="Review files", menu=export_menu).pack(side="left", padx=8)
        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="Save posting only", style="Primary.TButton", command=self.save).pack(side="left")
        ttk.Button(actions, text="Review evidence", command=self.edit_evidence).pack(side="left", padx=8)
        ttk.Button(actions, text="Reload saved", command=self.reload_saved).pack(side="right")
        self.status = tk.StringVar(value="Your shelf stays local. Discovery and AI requests happen only when you choose them.")
        status_label = ttk.Label(workspace, textvariable=self.status, style="AppMuted.TLabel", wraplength=900)
        status_label.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        workspace.bind("<Configure>", lambda event: status_label.configure(wraplength=max(300, event.width - 44)))
        polish_widgets(self)
        self.baseline = self.form_state()
        self.refresh()
        self.profile_changed()

    def focus_workspace(self):
        self.detail_tabs.select(0)
        self.posting.focus_set()

    def open_source(self):
        if self.has_draft_changes() or self.current_id is None:
            self.status.set("Select a saved review and save/discard edits before opening its source.")
            return
        try:
            url = source_link(self.store.load(self.current_id)["source_url"])
            webbrowser.open(url)
            self.status.set("Opened the saved posting URL in your browser. This does not submit an application.")
        except (ValueError, OSError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def profile_changed(self):
        profile = self.store.active_profile()
        name = profile["profile"]["name"] if profile else ""
        self.profile_status.set("Profile: " + name[:70] + ("…" if len(name) > 70 else "") if profile else "Start here: create your career profile and reviewed facts.")

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
                self.status.set("Start with Career profile: add your identity and reviewed facts before building a resume.")
                return
            job = self.store.load(self.current_id) if self.current_id else None
            return ResumeBuilder(self.winfo_toplevel(), self.store, profile, job,
                                 self.resume_saved)
        except (OSError, ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not open resumes", str(exc))

    def resume_saved(self):
        self.refresh()
        self.status.set("A reviewed resume version was saved. Export from the resume window.")

    def open_practice(self):
        try:
            store = JobStore(new_practice_path(self.store.path.parent))
            identifier = seed_practice(store)
            window = tk.Toplevel(self.winfo_toplevel())
            window.title(f"RoleWeave {APP_VERSION} - Synthetic practice")
            window.geometry("1180x780")
            window.minsize(1040, 700)
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
        instructions = ["1. Career profile: enter your identity, summary and sourced facts. Choose each fact's section and review it.",
                        "2. Paste a permitted posting or use Discover public jobs for one Greenhouse board. Choose the market explicitly.",
                        "3. Review evidence: select exact quotes and link relevant facts deliberately. Optional AI proposes quotes only after payload review and consent.",
                        "4. Build a resume: select reviewed claims, preview and approve. Save a frozen version, then export HTML/PDF.",
                        "5. Application notes: record decisions and follow-up dates; export a calendar file if useful. Nothing submits applications or links calendar accounts.",
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
                                        query=self.search.get(), due_on=date.today().isoformat() if self.due_only.get() else None,
                                        search_posting=self.search_posting.get())
            all_rows = self.store.list_jobs()
            resume_count = len(self.store.list_resumes())
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.rows = rows
        self.metric_values["saved"].set(str(len(all_rows)))
        self.metric_values["due"].set(str(sum(1 for item in all_rows if item["follow_up"] and item["follow_up"] <= date.today().isoformat() and item["stage"] not in ("closed", "withdrawn"))))
        self.metric_values["resumes"].set(str(resume_count))
        self.library_count.set(f"{len(rows)} shown · {len(all_rows)} saved reviews")
        self.jobs.delete(0, "end")
        for item in self.rows:
            due = f" · follow-up {item['follow_up']}" if item['follow_up'] else ""
            self.jobs.insert("end", f"{item['title']}  /  {item['company']}  ·  {item['stage']}{due}")
        if rows:
            self.empty_library.place_forget()
        else:
            self.empty_library.configure(text="No reviews match these filters.\nTry another market or search." if all_rows else "No saved reviews yet.\nDiscover a role or add a job.")
            self.empty_library.place(relx=.5, rely=.5, anchor="center")
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
        self.detail_tabs.select(0)

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
            self.detail_tabs.select(1)

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
            label = "Linked evidence" if requirement["evidence"] else "Needs your review"
            lines.append(f"{label}  /  {requirement['quote']}")
            lines.extend(f"  • {fact['claim']}\n    Source: {fact['source']}" for fact in requirement["evidence"])
            lines.append("")
        self.show_evidence("\n".join(lines) or "No reviewed requirements in this snapshot.")
        self.current_id = identifier
        self.review_title.set(item["title"][:110] + ("…" if len(item["title"]) > 110 else ""))
        self.review_subtitle.set(f"{item['company'][:80]}  ·  {self.market.get()}")
        self.baseline = self.form_state()
        self.status.set(f"Saved review {identifier[:8]} · {count} requirement quotes. Review evidence before linking facts. Saving posting only creates a new review without links.")

    def new_posting(self):
        if not self.discard_draft():
            return
        self.loaded_review = None
        self.current_id = None
        self.jobs.selection_clear(0, "end")
        self.review_title.set("Review a new opportunity")
        self.review_subtitle.set("Add a posting, then connect it to facts you can defend.")
        self.detail_tabs.select(2)
        for field in self.fields.values():
            field.delete(0, "end")
        self.posting.delete("1.0", "end")
        self.baseline = self.form_state()
        self.show_evidence("No saved review selected. New postings have no reviewed evidence.")
        self.status.set("New posting. Enter title/company and market in Job details, then paste the description in Job posting.")

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
    root.geometry("1180x780")
    root.minsize(1040, 700)
    try:
        path = new_practice_path(default_database_path().parent) if args.demo else args.db or default_database_path()
        store = JobStore(path)
        identifier = seed_practice(store) if args.demo else None
        shelf = JobShelf(root, store)
        if identifier:
            shelf.show_saved(identifier)
            shelf.status.set("Synthetic practice only. Your main workspace is unchanged.")
        elif not store.list_jobs() and not store.active_profile():
            shelf.status.set("Welcome. Start with Career profile, or use Getting started to open a separate synthetic practice workspace.")
        root.protocol("WM_DELETE_WINDOW", shelf.close)
    except (OSError, sqlite3.Error, ValueError) as exc:
        messagebox.showerror("Could not open local database", str(exc))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
