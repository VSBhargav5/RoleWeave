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
from applications import STAGES, current_application
from application_tracker import ApplicationTracker
from profile_editor import CareerProfileEditor
from resume_builder import ResumeBuilder
from demo_data import seed_practice
from runtime_paths import APP_VERSION, default_database_path, new_practice_path
from startup_selftest import run_self_test
from application_dossier import verify_dossier
from dossier_window import DossierWindow
from letter_window import LetterWindow, FrozenLetterWindow
from cover_letter import read_letter
from submission_window import SubmissionWindow
from correspondence_window import CorrespondenceWindow
from watchlist_window import WatchlistWindow
from rehearsal_window import RehearsalWindow
from rehearsal_journal import read_rehearsal, rehearsal_source_item
from discovery_window import DiscoveryWindow
from roleweave import MAX_BYTES, review_snapshot
from desktop_theme import apply_theme, polish_widgets, reserve_footer
from source_links import source_link
from workspace_exports import review_list_csv, follow_up_list
from review_history import ReviewHistory
from interview_practice import InterviewPractice
from workspace_health import inspect_database
from visual_components import EvidenceCards, WeaveArt
from desktop_errors import install_error_handler
from application_journey import ApplicationJourney

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

        rail = ttk.Frame(self, style="Rail.TFrame", padding=(14, 24), width=168)
        rail.grid(row=0, column=0, sticky="nsew")
        rail.grid_propagate(False)
        rail.columnconfigure(0, weight=1)
        rail.rowconfigure(8, weight=1)
        brand = ttk.Frame(rail, style="Rail.TFrame")
        brand.grid(row=0, column=0, sticky="w")
        tk.Label(brand, text="rw", background="#6254d9", foreground="white", font=("Segoe UI", 11, "bold"), padx=5, pady=4).pack(side="left", padx=(0, 7))
        ttk.Label(brand, text="RoleWeave", style="Rail.TLabel", font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Label(rail, text="Your career workspace.", style="RailMuted.TLabel").grid(row=1, column=0, sticky="w", pady=(5, 30))
        ttk.Label(rail, text="YOUR WORKSPACE", style="RailMuted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 10))
        ttk.Button(rail, text="Job workspace", style="ActiveRail.TButton", command=self.focus_workspace).grid(row=3, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="Discover jobs", style="Rail.TButton", command=self.open_discovery).grid(row=4, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="Career profile", style="Rail.TButton", command=self.open_profile).grid(row=5, column=0, sticky="ew", pady=3)
        ttk.Button(rail, text="Resume studio", style="Rail.TButton", command=self.open_resume).grid(row=6, column=0, sticky="ew", pady=3)
        ttk.Label(rail, text="LOCAL WORKSPACE", style="RailMuted.TLabel").grid(row=9, column=0, sticky="w", pady=(0, 8))
        ttk.Button(rail, text="Back up shelf", style="Rail.TButton", command=self.backup_shelf).grid(row=10, column=0, sticky="ew")
        ttk.Button(rail, text="Restore backup", style="Rail.TButton", command=self.restore_shelf).grid(row=11, column=0, sticky="ew")
        ttk.Button(rail, text="Getting started", style="Rail.TButton", command=self.open_help).grid(row=12, column=0, sticky="ew")
        ttk.Label(rail, text=f"v{APP_VERSION}\nStored locally. Sent by you.", style="RailMuted.TLabel", wraplength=135).grid(row=13, column=0, sticky="w", pady=(24, 0))

        workspace = ttk.Frame(self, style="App.TFrame", padding=(22, 14, 22, 12))
        workspace.grid(row=0, column=1, sticky="nsew")
        workspace.columnconfigure(0, weight=1)
        workspace.rowconfigure(3, weight=1)
        heading = ttk.Frame(workspace, style="Hero.TFrame", padding=(20, 10))
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="ROLEWEAVE / YOUR OPPORTUNITIES", style="HeroEyebrow.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(heading, text="Your next chapter.", style="HeroTitle.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.profile_status = tk.StringVar()
        ttk.Label(heading, textvariable=self.profile_status, style="HeroNote.TLabel").grid(row=2, column=0, sticky="w")
        WeaveArt(heading).grid(row=0, column=1, rowspan=3, padx=12)
        ttk.Button(heading, text="+  Add opportunity", style="Hero.TButton", command=self.new_posting).grid(row=0, column=2, rowspan=3, sticky="e")

        metrics = ttk.Frame(workspace, style="App.TFrame")
        metrics.grid(row=1, column=0, sticky="ew", pady=(12, 12))
        self.metric_values = {}
        for column, (key, label, note) in enumerate((("saved", "Saved reviews", "Individual review snapshots"),
                                                   ("due", "Follow-ups due", "Active through today"),
                                                   ("resumes", "Resume versions", "Reviewed, frozen documents"))):
            metrics.columnconfigure(column, weight=1, uniform="metrics")
            tone = ("Violet", "Amber", "Mint")[column]
            card = ttk.Frame(metrics, padding=(16, 8), style=tone + ".TFrame")
            card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 12, 0))
            card.columnconfigure(0, weight=1)
            value = tk.StringVar(value="0")
            self.metric_values[key] = value
            ttk.Label(card, text=label, style=tone + ".TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(card, textvariable=value, style=tone + "Value.TLabel").grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 0))
            ttk.Label(card, text=note, style=tone + "Note.TLabel").grid(row=1, column=0, sticky="w")

        content = ttk.Frame(workspace, style="App.TFrame")
        content.grid(row=3, column=0, sticky="nsew")
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        left = ttk.Frame(content, padding=12, width=300, style="Panel.TFrame")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_propagate(False)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(7, weight=1)
        library_heading = ttk.Frame(left)
        library_heading.grid(row=0, column=0, sticky="ew")
        ttk.Label(library_heading, text="Opportunities", style="Section.TLabel").pack(side="left")
        self.sort_order = tk.StringVar(value="newest")
        sort_menu = tk.Menu(self, tearoff=False)
        for label, value in (("Newest", "newest"), ("Oldest", "oldest"), ("Title", "title"), ("Company", "company"), ("Follow-up date", "follow_up")):
            sort_menu.add_radiobutton(label=label, variable=self.sort_order, value=value, command=self.refresh)
        ttk.Menubutton(library_heading, text="Sort", menu=sort_menu).pack(side="right")
        self.library_count = tk.StringVar(value="No saved reviews")
        ttk.Label(left, textvariable=self.library_count, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 12))
        ttk.Label(left, text="SEARCH YOUR SHELF", style="Eyebrow.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 5))
        self.search = tk.StringVar()
        search_row = ttk.Frame(left)
        search_row.grid(row=3, column=0, sticky="ew")
        search_row.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search_row, textvariable=self.search, width=12)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: self.refresh())
        ttk.Button(search_row, text="Go", command=self.refresh).grid(row=0, column=1, padx=(6, 0))
        filter_row = ttk.Frame(left)
        filter_row.grid(row=4, column=0, sticky="ew", pady=8)
        self.filter_button = ttk.Button(filter_row, text="Filters +", command=self.toggle_filters)
        self.filter_button.pack(side="left")
        self.filter_summary = tk.StringVar(value="All markets / all stages")
        ttk.Label(filter_row, textvariable=self.filter_summary, style="Muted.TLabel", font=("Segoe UI", 8), wraplength=150).pack(side="right")
        self.filters_panel = ttk.Frame(left)
        self.filter = tk.StringVar(value="All markets")
        chooser = ttk.Combobox(self.filters_panel, textvariable=self.filter, state="readonly", values=["All markets", *MARKET_LABELS], width=20, style="Filter.TCombobox")
        chooser.pack(fill="x")
        chooser.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.stage_filter = tk.StringVar(value="All stages")
        stage_row = ttk.Frame(self.filters_panel)
        stage_row.pack(fill="x", pady=5)
        stage_filter = ttk.Combobox(stage_row, textvariable=self.stage_filter, values=["All stages", *STAGES], state="readonly", width=11, style="Filter.TCombobox")
        stage_filter.pack(side="left", fill="x", expand=True)
        stage_filter.bind("<<ComboboxSelected>>", lambda _event: self.refresh())
        self.due_only = tk.BooleanVar(value=False)
        ttk.Checkbutton(stage_row, text="Due only", variable=self.due_only, command=self.refresh, style="Filter.TCheckbutton").pack(side="left", padx=(8, 0))
        self.search_posting = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.filters_panel, text="Include posting text", variable=self.search_posting, command=self.refresh, style="Filter.TCheckbutton").pack(anchor="w")
        ttk.Separator(left).grid(row=6, column=0, sticky="ew", pady=(0, 8))
        listing = ttk.Frame(left)
        listing.grid(row=7, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.jobs = ttk.Treeview(listing, columns=("stage",), show="tree headings", selectmode="browse", height=5, style="Opportunity.Treeview")
        self.jobs.heading("#0", text="ROLE / COMPANY", anchor="w")
        self.jobs.heading("stage", text="STAGE", anchor="w")
        self.jobs.column("#0", width=165, minwidth=120, stretch=True)
        self.jobs.column("stage", width=80, minwidth=75, stretch=False)
        self.jobs.tag_configure("due", foreground="#f7c268")
        self.jobs.tag_configure("inactive", foreground="#94a0b7")
        self.jobs.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(listing, command=self.jobs.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        self.jobs.configure(yscrollcommand=vertical.set)
        self.jobs.bind("<<TreeviewSelect>>", self.open_selected)
        self.empty_library = ttk.Label(self.jobs, text="Your next opportunity\nstarts here.\n\nDiscover a role or add a job.", style="Muted.TLabel", wraplength=205, justify="center")

        right = ttk.Frame(content, padding=18, style="Panel.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        self.review_title = tk.StringVar(value="Review a new opportunity")
        self.review_subtitle = tk.StringVar(value="Add a posting, then connect it to facts you can defend.")
        review_heading = ttk.Frame(right)
        review_heading.grid(row=0, column=0, sticky="ew")
        review_heading.columnconfigure(0, weight=1)
        title_label = ttk.Label(review_heading, textvariable=self.review_title, style="ReviewTitle.TLabel", wraplength=520)
        title_label.grid(row=0, column=0, sticky="w")
        self.review_stage = tk.StringVar(value="New draft")
        ttk.Label(review_heading, textvariable=self.review_stage, style="Badge.TLabel").grid(row=0, column=1, sticky="ne", padx=(8, 0))
        subtitle_label = ttk.Label(right, textvariable=self.review_subtitle, style="Muted.TLabel", wraplength=520)
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 12))
        right.bind("<Configure>", lambda event: (title_label.configure(wraplength=max(190, event.width - 150)), subtitle_label.configure(wraplength=max(190, event.width - 150))))
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
        self.evidence_summary = tk.StringVar(value="Exact quotes. Reviewed facts. Your decision.")
        ttk.Label(evidence_tab, textvariable=self.evidence_summary, style="Eyebrow.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.evidence = EvidenceCards(evidence_tab)
        self.evidence.grid(row=1, column=0, sticky="nsew")
        self.show_evidence("No saved review selected. Save a posting, then review its requirements and career evidence.")
        next_actions = ttk.Frame(evidence_tab)
        next_actions.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(next_actions, text="Application notes / follow-up", command=self.open_tracker).pack(side="left")
        export_menu = tk.Menu(self, tearoff=False)
        export_menu.add_command(label="Open saved employer collection...", command=self.open_collection_file)
        export_menu.add_command(label="Employer watchlists...", command=self.open_watchlist)
        export_menu.add_command(label="Review local email correspondence...", command=self.open_correspondence)
        export_menu.add_command(label="Record my manual submission...", command=self.open_submission)
        export_menu.add_command(label="Prepare reviewed cover letter...", command=self.open_letter)
        export_menu.add_command(label="Open frozen letter version...", command=self.open_letter_file)
        export_menu.add_command(label="Private application dossier...", command=self.open_dossier)
        export_menu.add_command(label="Verify private dossier without extracting...", command=self.verify_dossier_file)
        export_menu.add_command(label="Preparation pack (.txt)", command=self.export_pack)
        export_menu.add_command(label="Original review (.json)", command=self.export_selected)
        export_menu.add_command(label="Import review JSON…", command=self.import_review)
        export_menu.add_command(label="Open saved source posting in browser", command=self.open_source)
        export_menu.add_command(label="Inspect backup without restoring", command=self.inspect_backup)
        export_menu.add_command(label="Export this filtered review list (.csv)", command=self.export_list)
        export_menu.add_command(label="Export filtered active follow-ups (.ics)", command=self.export_followups)
        export_menu.add_command(label="Compare related saved versions", command=self.open_versions)
        export_menu.add_command(label="Practise linked interview evidence", command=self.open_practice_cards)
        export_menu.add_command(label="Write/save rehearsal answers...", command=self.open_rehearsal)
        export_menu.add_command(label="Google Calendar follow-up sync...", command=self.open_google_calendar)
        export_menu.add_command(label="Open private rehearsal version...", command=self.open_rehearsal_file)
        export_menu.add_command(label="Check local database storage", command=self.check_database)
        export_menu.add_command(label="Audit saved sources and references (read-only)", command=self.audit_shelf)
        ttk.Menubutton(next_actions, text="Review files", menu=export_menu).pack(side="left", padx=8)
        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="Save posting only", command=self.save).pack(side="left")
        ttk.Button(actions, text="Apply workspace", style="Primary.TButton", command=self.open_application).pack(side="left", padx=8)
        ttk.Button(actions, text="Reload saved", command=self.reload_saved).pack(side="right")
        self.status = tk.StringVar(value="Your shelf stays local. Discovery and AI requests happen only when you choose them.")
        status_label = ttk.Label(workspace, textvariable=self.status, style="AppMuted.TLabel", wraplength=900)
        status_label.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        workspace.bind("<Configure>", lambda event: status_label.configure(wraplength=max(300, event.width - 44)))
        polish_widgets(self)
        self.baseline = self.form_state()
        self.refresh()
        self.profile_changed()
        root.bind("<Control-f>", self.focus_search)
        root.bind("<Control-n>", lambda _event: self.shortcut(self.new_posting))
        root.bind("<Control-e>", lambda _event: self.shortcut(self.edit_evidence))

    def focus_workspace(self):
        self.detail_tabs.select(0)
        self.posting.focus_set()

    def open_application(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Save a job and save/discard edits before opening its Apply workspace.")
            return
        try:
            return ApplicationJourney(self)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def open_correspondence(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before linking correspondence.")
            return
        return CorrespondenceWindow(self.winfo_toplevel(), self.store, self.current_id, self.tracking_changed)

    def open_submission(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before recording its submission observation.")
            return
        return SubmissionWindow(self.winfo_toplevel(), self.store, self.current_id, self.tracking_changed)

    def open_letter(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before preparing its letter.")
            return
        profile = self.store.active_profile()
        if profile is None:
            self.status.set("Create and activate a reviewed career profile first.")
            return
        return LetterWindow(self.winfo_toplevel(), profile, self.store.load(self.current_id))

    def open_letter_file(self):
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), filetypes=[("Private letter version", "*.json")])
        if not path:
            return
        try:
            snapshot, _record = read_letter(path)
            return FrozenLetterWindow(self.winfo_toplevel(), snapshot)
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_dossier(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before preparing its dossier.")
            return
        return DossierWindow(self.winfo_toplevel(), self.store, self.current_id)

    def verify_dossier_file(self):
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), filetypes=[("Private application dossier", "*.zip")])
        if not path:
            return
        try:
            result = verify_dossier(path)
            messagebox.showinfo("Private dossier verified", f"Frozen documents replayed successfully.\n{result['job']['company']} - {result['job']['title']}\n{result['file_count']} files; history revision {result['history_revision']}\nIntegrity is not proof of submission or source truth.", parent=self.winfo_toplevel())
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_versions(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before comparing versions.")
            return
        return ReviewHistory(self.winfo_toplevel(), self.store, self.current_id)

    def open_rehearsal(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before drafting its rehearsal.")
            return
        return RehearsalWindow(self.winfo_toplevel(), self.store.load(self.current_id))

    def open_rehearsal_file(self):
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), filetypes=[("Private rehearsal version", "*.json")])
        if not path:
            return
        try:
            snapshot, record = read_rehearsal(path)
            return RehearsalWindow(self.winfo_toplevel(), rehearsal_source_item(record), snapshot=snapshot)
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_practice_cards(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before practising its evidence.")
            return
        return InterviewPractice(self.winfo_toplevel(), self.store.load(self.current_id))

    def check_database(self):
        try:
            counts = inspect_database(self.store.path)
            messagebox.showinfo("Read-only storage check", "SQLite quick_check passed.\n" + "\n".join(f"{key}: {value}" for key, value in counts.items()) + "\nThis checks storage structure, not source authenticity or completeness.", parent=self.winfo_toplevel())
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def audit_shelf(self):
        try:
            from shelf_audit import audit_database, export_audit
            report = audit_database(self.store.path)
            summary = ("Stored source/reference checks passed." if report["ok"] else "Stored source/reference issues found. Preserve this shelf; no repair was attempted.")
            summary += "\n" + "\n".join(f"{key}: {value}" for key, value in report["counts"].items())
            summary += "\nIssues: " + str(len(report["issues"])) + "\n" + "\n".join(row["table"] + ": " + row["code"] for row in report["issues"][:12])
            summary += "\nThis does not authenticate career claims or guarantee recovery. Separate journal/dossier/archive files are outside this check.\n\nExport a private JSON report with stored IDs and check results?"
            if messagebox.askyesno("Read-only shelf source/reference audit", summary, parent=self.winfo_toplevel()):
                path = filedialog.asksaveasfilename(parent=self.winfo_toplevel(), defaultextension=".json", filetypes=[("Private shelf audit", "*.json")])
                if path:
                    export_audit(report, path, confirmed=True)
            self.status.set("Read-only audit finished: " + str(len(report["issues"])) + " issues. No shelf data changed.")
            return report
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def focus_search(self, _event=None):
        self.search_entry.focus_set()
        self.search_entry.selection_range(0, "end")
        return "break"

    @staticmethod
    def shortcut(action):
        action()
        return "break"

    def open_source(self):
        if self.has_draft_changes() or self.current_id is None:
            self.status.set("Select a saved review and save/discard edits before opening its source.")
            return
        try:
            url = source_link(self.store.load(self.current_id)["source_url"])
            if not webbrowser.open(url):
                self.status.set("Your browser did not open the saved job page. Check your default browser, or copy the HTTPS URL from Job details.")
                return
            self.status.set("Opened the saved posting URL in your browser. This does not submit an application.")
        except (ValueError, OSError, sqlite3.Error, webbrowser.Error) as exc:
            self.status.set(str(exc))

    def inspect_backup(self):
        path = filedialog.askopenfilename(filetypes=[("RoleWeave backup", "*.json")])
        if path:
            try:
                counts = self.store.inspect_backup(path)
                messagebox.showinfo("Backup validated in an isolated shelf", "\n".join(f"{key.replace('_', ' ').title()}: {value}" for key, value in counts.items()) + "\nCurrent workspace unchanged. Hashes do not prove authenticity.", parent=self.winfo_toplevel())
            except (OSError, ValueError, sqlite3.Error) as exc:
                self.status.set(str(exc))

    def export_list(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("Filtered review list", "*.csv")])
        if path:
            try:
                review_list_csv(self.rows, path)
                self.status.set(f"Exported {len(self.rows)} displayed review rows. No notes, facts or resumes included; keep this file private.")
            except (OSError, ValueError) as exc:
                self.status.set(str(exc))

    def export_followups(self):
        path = filedialog.asksaveasfilename(defaultextension=".ics", filetypes=[("Filtered follow-ups", "*.ics")])
        if path:
            try:
                count = follow_up_list(self.store, self.rows, path)
                self.status.set(f"Exported {count} private calendar events. Import manually; existing remote events are not changed.")
            except (OSError, ValueError, sqlite3.Error) as exc:
                self.status.set(str(exc))

    def profile_changed(self):
        profile = self.store.active_profile()
        name = profile["profile"]["name"] if profile else ""
        self.profile_status.set("Profile: " + name[:34] + ("…" if len(name) > 34 else "") if profile else "Start here: create your career profile and reviewed facts.")

    def open_collection_file(self):
        if self.has_draft_changes():
            self.status.set("Save/discard posting edits before opening an importable collection.")
            return
        path = filedialog.askopenfilename(parent=self.winfo_toplevel(), filetypes=[("Private collection archive", "*.json")])
        if not path:
            return
        try:
            from collection_archive import read_collection_archive
            from collection_window import CollectionWindow
            collection = read_collection_archive(path)
            child = CollectionWindow(self.winfo_toplevel(), self.store, collection["watchlist"],
                                     collection["selected_indices"], MARKET_LABELS, self.show_saved)
            child.received(collection)
            child.status.set("Offline replay of saved source observations; current availability is unverified.")
            return child
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_watchlist(self):
        if self.has_draft_changes():
            self.status.set("Save/discard posting edits before using employer watchlists.")
            return
        return WatchlistWindow(self.winfo_toplevel(), self.store, MARKET_LABELS, self.show_saved)

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

    def open_google_calendar(self):
        if self.current_id is None or self.has_draft_changes():
            self.status.set("Select a saved review and save/discard edits before Calendar sync.")
            return
        from google_calendar_window import GoogleCalendarWindow
        try:
            return GoogleCalendarWindow(self.winfo_toplevel(), self.store, self.current_id)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def open_help(self):
        window = tk.Toplevel(self.winfo_toplevel())
        window.title(f"RoleWeave {APP_VERSION} - Getting started and readiness")
        window.geometry("900x700")
        window.minsize(700, 500)
        window.transient(self.winfo_toplevel())
        window.grab_set()
        body = ttk.Frame(window, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Start with one job and facts you can defend", font=("Segoe UI", 15), wraplength=650).pack(anchor="w")
        ttk.Label(body, text="Core local MVP: 8 workflow groups implemented and tested offline. Personal acceptance and optional live services need separate checks.", wraplength=650).pack(anchor="w", pady=8)
        tabs = ttk.Notebook(body)
        tabs.pack(fill="both", expand=True)
        pages = {
            "First use": "\n\n".join([
                "1. Use the separate synthetic practice workspace first. It never replaces your personal shelf.",
                "2. Career profile: enter identity and sourced facts. Review each claim and distinguish projects from employment.",
                "3. Paste a permitted job or use Public job discovery / Employer watchlists. Greenhouse, Lever global/EU and Ashby are supported subsets. Fetch is deliberate; board compatibility and limits vary.",
                "4. Choose India/remote or relocation explicitly. Review exact requirement quotes and link relevant evidence. A location label is not eligibility or sponsorship proof.",
                "5. Build a reviewed resume. Preview and approve selected claims, save a frozen version, export HTML/PDF/TXT. Review files can prepare a reviewed letter and private dossier, then recipient-only files.",
                "6. Record decisions, manual submission observations and local email excerpts yourself. Nothing sends applications, reads a mailbox or links accounts. Export follow-ups as calendar files if useful.",
                "7. Evidence & next steps > Review files > Write/save rehearsal answers: choose questions, draft, reveal evidence, save/reopen and compare exact-source private versions. Time and draft changes do not prove learning.",
                "8. Back up the full shelf and test restore in a separate practice database. Review files can inspect backups, check storage and audit saved sources/references. Keep separate exported files backed up too."
            ]),
            "Readiness and remaining work": "\n\n".join([
                "READY FOR A LOCAL TRIAL - 8/8 core workflow groups implemented and offline tested. This is not proof of personal usefulness or a production-readiness percentage.",
                "1. Windows portable/installed runtime: automated delivery checks pass; manual wizard/scaling acceptance remains yours.",
                "2. Posting review, exact evidence and separate markets: implemented and regression-tested.",
                "3. Reusable reviewed career profiles: implemented and regression-tested.",
                "4. Frozen resume and reviewed letter preparation: implemented and regression-tested; personally proofread every exported document.",
                "5. Private dossiers and recipient-only files: implemented and regression-tested; private source/history files are not recruiter attachments.",
                "6. Manual application stages, follow-ups and correspondence: implemented and regression-tested; observations do not prove delivery or sender authenticity.",
                "7. Source-bound rehearsal drafts, packs and differences: implemented and regression-tested; no answer grading or learning claim.",
                "8. Shelf backup/restore and read-only audits: implemented and regression-tested; no recovery guarantee for arbitrary corruption.",
                "PARTLY VALIDATED: Public discovery depends on the selected board. Live checks parsed Greenhouse and Lever EU; Lever global's example was empty. Ashby's example board exceeded the supported posting size and was refused, not partially imported.",
                "LIVE TRIAL NEEDED: Optional AI quote proposals are implemented/offline tested. Enter a key only in the app and consent to one reviewed request; API cost/quality and account access are not verified.",
                "LIVE CALENDAR TRIAL NEEDED: Local calendar export is tested. Review files > Google Calendar follow-up sync now supports explicit app-created-calendar OAuth and one reviewed reminder at a time. Desktop OAuth client setup, Google consent and real writes remain unverified.",
                "NOT IMPLEMENTED: Connected mailbox sync, general calendar synchronization, global automatic job search and automatic applications. Narrow Google follow-up sync is optional and requires your reviewed account consent; it is not background two-way account synchronization.",
                "PERSONAL ACCEPTANCE: Complete one permitted posting-to-document-to-tracking-to-restore workflow, note problems, and check every career claim. This cannot be marked complete by more commits."
            ]),
            "Your data and boundaries": (
                f"Current database:\n{self.store.path.resolve()}\n\n"
                "Portable/installed builds use LOCALAPPDATA/RoleWeave/jobs.db; source launchers use the repository private/jobs.db. They are different shelves. Back up the source shelf and explicitly restore it in the portable app if migrating.\n\n"
                "Shelf backups include saved reviews, profiles, frozen resumes and application history, not unsaved drafts or separate journal/letter/dossier/source archive files. Keep private backups of those files separately.\n\n"
                "Exports and backups are unencrypted. Check recipient-only files before sharing. Source hashes detect byte changes; they do not authenticate claims.\n\n"
                "Discovery sends a public board token and normal connection metadata. Optional AI sends only the reviewed posting payload after explicit consent. No API key is read from files/environment or saved in the shelf. Cancelling locally cannot reverse provider processing or charges.\n\n"
                "No service is contacted when this guide opens. No installer, export, account linking or application submission is automatic. Optional Google follow-up sync is available through Review files and requires separate scope/read/write confirmations."
            )
        }
        window.help_pages = {}
        for title, content in pages.items():
            pane = ttk.Frame(tabs, padding=8)
            pane.rowconfigure(0, weight=1)
            pane.columnconfigure(0, weight=1)
            output = tk.Text(pane, wrap="word", height=8)
            output.grid(row=0, column=0, sticky="nsew")
            scroll = ttk.Scrollbar(pane, orient="vertical", command=output.yview)
            scroll.grid(row=0, column=1, sticky="ns")
            output.configure(yscrollcommand=scroll.set)
            output.insert("1.0", content)
            output.configure(state="disabled")
            window.help_pages[title] = output
            tabs.add(pane, text=title)
        window.help_tabs = tabs
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(12, 0))
        def practice():
            window.destroy()
            self.open_practice()
        ttk.Button(actions, text="Open separate synthetic practice workspace", command=practice).pack(side="left")
        ttk.Button(actions, text="Close", command=window.destroy).pack(side="right")
        reserve_footer(body)
        polish_widgets(window)
        return window

    def refresh(self):
        try:
            rows = self.store.list_jobs(MARKET_LABELS.get(self.filter.get()),
                                        stage=None if self.stage_filter.get() == "All stages" else self.stage_filter.get(),
                                        query=self.search.get(), due_on=date.today().isoformat() if self.due_only.get() else None,
                                        search_posting=self.search_posting.get(), sort=self.sort_order.get())
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
        children = self.jobs.get_children()
        if children:
            self.jobs.delete(*children)
        for item in self.rows:
            due = bool(item["follow_up"] and item["follow_up"] <= date.today().isoformat() and item["stage"] not in ("closed", "withdrawn"))
            company = item["company"] + (" / " + item["follow_up"] if item["follow_up"] else "")
            self.jobs.insert("", "end", iid=item["id"], text=item["title"] + "\n" + company,
                             values=(item["stage"].title(),), tags=("due",) if due else ("inactive",) if item["stage"] in ("closed", "withdrawn") else ())
        summary = [self.filter.get(), self.stage_filter.get()]
        if self.due_only.get():
            summary.append("Due only")
        if self.search_posting.get():
            summary.append("Posting text")
        self.filter_summary.set(" / ".join(summary))
        selected = next((row for row in all_rows if row["id"] == self.current_id), None)
        if selected is not None:
            self.review_stage.set(selected["stage"].title())
        if rows:
            self.empty_library.place_forget()
        else:
            self.empty_library.configure(text="No reviews match these filters.\nTry another market or search." if all_rows else "No saved reviews yet.\nDiscover a role or add a job.")
            self.empty_library.place(relx=.5, rely=.5, anchor="center")
        self.select_job(self.current_id)

    def toggle_filters(self):
        if self.filters_panel.winfo_manager():
            self.filters_panel.grid_remove()
            self.filter_button.configure(text="Filters +")
        else:
            self.filters_panel.grid(row=5, column=0, sticky="ew", pady=(0, 8))
            self.filter_button.configure(text="Filters -")

    def select_job(self, identifier):
        if self.jobs.selection():
            self.jobs.selection_remove(*self.jobs.selection())
        if identifier is not None and self.jobs.exists(identifier):
            self.jobs.selection_set(identifier)
            self.jobs.focus(identifier)
            self.jobs.see(identifier)

    def tracking_changed(self, identifier):
        self.refresh()
        self.select_job(identifier)

    def open_tracker(self):
        if self.has_draft_changes():
            self.status.set("Save your posting edits or Reload saved review before tracking its saved version.")
            return
        if not self.jobs.selection():
            self.status.set("Select a saved review to track. Tracking does not submit applications.")
            return
        try:
            return ApplicationTracker(self.winfo_toplevel(), self.store,
                                      self.jobs.selection()[0], self.tracking_changed)
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

    def show_evidence(self, value, requirements=None):
        self.evidence.render(value, requirements)

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
        if not self.jobs.selection():
            return
        identifier = self.jobs.selection()[0]
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
        self.show_evidence("\n".join(lines) or "No reviewed requirements in this snapshot.", item["review"]["requirements"])
        self.current_id = identifier
        self.review_title.set(item["title"][:64] + ("…" if len(item["title"]) > 64 else ""))
        self.review_stage.set(current_application(self.store.application_history(identifier))["stage"].title())
        linked = sum(bool(row["evidence"]) for row in item["review"]["requirements"])
        self.evidence_summary.set(f"{count} requirements  /  {linked} linked  /  {count - linked} open for review")
        self.review_subtitle.set(f"{item['company'][:80]}  ·  {self.market.get()}")
        self.baseline = self.form_state()
        self.status.set(f"Saved review {identifier[:8]} · {count} requirement quotes. Review evidence before linking facts. Saving posting only creates a new review without links.")

    def new_posting(self):
        if not self.discard_draft():
            return
        self.loaded_review = None
        self.current_id = None
        self.jobs.selection_remove(*self.jobs.selection())
        self.review_title.set("Review a new opportunity")
        self.review_stage.set("New draft")
        self.evidence_summary.set("Exact quotes. Reviewed facts. Your decision.")
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
        if not self.jobs.selection():
            self.status.set("Select a saved job before exporting its original review.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Review JSON", "*.json")])
        if not path:
            return
        try:
            self.store.export(self.jobs.selection()[0], path)
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
        if not self.jobs.selection():
            self.status.set("Select a saved review to export its preparation pack.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Preparation pack", "*.txt")])
        if not path:
            return
        try:
            self.store.export_preparation_pack(self.jobs.selection()[0], path)
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
    install_error_handler(root)
    root.title(f"RoleWeave {APP_VERSION} - {'Synthetic practice' if args.demo else 'Job workspace'}")
    # Leave room for window chrome/taskbar in Tk's DPI-scaled screen coordinates.
    initial_width = max(1040, min(1360, root.winfo_screenwidth() - 80))
    initial_height = max(700, min(880, root.winfo_screenheight() - 120))
    initial_x = max(0, (root.winfo_screenwidth() - initial_width) // 2)
    initial_y = 12
    root.geometry(f"{initial_width}x{initial_height}+{initial_x}+{initial_y}")
    root.minsize(1040, 700)
    try:
        path = new_practice_path(default_database_path().parent) if args.demo else args.db or default_database_path()
        store = JobStore(path)
        identifier = seed_practice(store) if args.demo else None
        shelf = JobShelf(root, store)
        if identifier:
            shelf.show_saved(identifier)
            shelf.detail_tabs.select(1)
            shelf.status.set("Synthetic practice only. Your main workspace is unchanged.")
        elif not store.list_jobs() and not store.active_profile():
            shelf.status.set("Welcome. Start with Career profile, or use Getting started to open a separate synthetic practice workspace.")
        root.protocol("WM_DELETE_WINDOW", shelf.close)
    except (OSError, sqlite3.Error, ValueError, RuntimeError, tk.TclError) as exc:
        messagebox.showerror("Could not open RoleWeave", str(exc), parent=root)
        root.destroy()
        return 1
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
