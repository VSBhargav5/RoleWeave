"""Reviewed, explicit, single-follow-up Calendar operations. No startup network."""
import copy
import json
import tkinter as tk
from tkinter import messagebox, ttk

from background_task import BackgroundTask
from desktop_theme import polish_widgets, reserve_footer
from google_calendar_auth import connect_session, create_calendar
from google_calendar_sync import SCOPE, desired_event, prepare_sync, read_remote, apply_sync


class GoogleCalendarWindow(tk.Toplevel):
    def __init__(self, parent, store, identifier):
        store.load(identifier)
        super().__init__(parent)
        self.store, self.identifier = store, identifier
        self.credentials, self.plan, self.remote = None, None, None
        self.task = BackgroundTask(self)
        self.title("RoleWeave - Google Calendar follow-up sync")
        self.geometry("1000x800")
        self.minsize(800, 650)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.close)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="One reviewed follow-up at a time", font=("Segoe UI", 16)).pack(anchor="w")
        ttk.Label(body, text="Optional session-only Google connection. No automatic sync, deletion, invitations or token files. Cancelling locally cannot undo an accepted remote write.", wraplength=750).pack(anchor="w", pady=8)
        tabs = ttk.Notebook(body)
        tabs.pack(fill="both", expand=True)
        session, reminder = ttk.Frame(tabs, padding=8), ttk.Frame(tabs, padding=8)
        tabs.add(session, text="1. Connect / choose calendar")
        tabs.add(reminder, text="2. Review / sync one follow-up")
        self.tabs = tabs
        self.client_id, self.client_secret = tk.StringVar(), tk.StringVar()
        for label, variable, masked in (("Desktop OAuth client ID", self.client_id, False), ("Desktop OAuth client secret (session only)", self.client_secret, True)):
            ttk.Label(session, text=label).pack(anchor="w")
            ttk.Entry(session, textvariable=variable, show="*" if masked else "").pack(fill="x", pady=(0, 8))
        ttk.Label(session, text="Requires your own Google Desktop OAuth client with Calendar API enabled. No client config/key is read from files or environment. Scope: " + SCOPE + "\nThis can manage app-created secondary calendars, including delete permission; RoleWeave implements no delete action. It does not request access to your primary calendar or mailbox.", wraplength=730).pack(anchor="w", pady=8)
        self.scope_consent = tk.BooleanVar(value=False)
        ttk.Checkbutton(session, text="I reviewed this scope and want Google browser consent for this session.", variable=self.scope_consent).pack(anchor="w")
        controls = ttk.Frame(session)
        controls.pack(fill="x", pady=8)
        ttk.Button(controls, text="Connect in browser", command=self.connect).pack(side="left")
        ttk.Button(controls, text="Disconnect locally", command=self.disconnect).pack(side="left", padx=8)
        ttk.Button(controls, text="Create separate RoleWeave calendar...", command=self.create).pack(side="left")
        ttk.Label(session, text="App-created calendar ID (copy it after creation for reuse; this field is not saved)").pack(anchor="w", pady=(12, 0))
        self.calendar_id = tk.StringVar()
        ttk.Entry(session, textvariable=self.calendar_id).pack(fill="x", pady=8)
        ttk.Label(session, text="Paste an existing calendar ID created by this same OAuth app, or deliberately create a new one above. Repeated Create makes additional calendars; inspect Google after an uncertain response before retrying. Closing this window clears credentials, not Google's granted consent or remote events.", wraplength=730).pack(anchor="w")
        self.include_details = tk.BooleanVar(value=False)
        ttk.Checkbutton(reminder, text="Include company and role in the event title (default is a generic private reminder)", variable=self.include_details).pack(anchor="w")
        self.read_consent = tk.BooleanVar(value=False)
        ttk.Checkbutton(reminder, text="I consent to read the matching event in this selected app-created calendar.", variable=self.read_consent).pack(anchor="w")
        row = ttk.Frame(reminder)
        row.pack(fill="x", pady=8)
        ttk.Button(row, text="Preview local reminder only", command=self.local_preview).pack(side="left")
        ttk.Button(row, text="Read remote / prepare change", command=self.prepare).pack(side="left", padx=8)
        pane = ttk.Frame(reminder)
        pane.pack(fill="both", expand=True)
        self.preview = tk.Text(pane, wrap="word", height=8, state="disabled")
        self.preview.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(pane, orient="vertical", command=self.preview.yview)
        scroll.pack(side="right", fill="y")
        self.preview.configure(yscrollcommand=scroll.set)
        self.write_consent = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed the exact remote/proposed fields and approve this one create/update.", variable=self.write_consent).pack(anchor="w", pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        ttk.Button(actions, text="Send reviewed follow-up", command=self.send).pack(side="left")
        ttk.Button(actions, text="Cancel current operation", command=self.cancel).pack(side="left", padx=8)
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="Disconnected. Opening this window sends nothing. Record/save an active follow-up date before previewing.")
        ttk.Label(body, textvariable=self.status, wraplength=750).pack(anchor="w", pady=8)
        self.calendar_id.trace_add("write", self.invalidate)
        self.include_details.trace_add("write", self.invalidate)
        reserve_footer(body)
        polish_widgets(self)

    def show(self, value):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", json.dumps(value, ensure_ascii=True, indent=2))
        self.preview.configure(state="disabled")

    def invalidate(self, *_args):
        self.task.cancel()
        self.plan, self.remote = None, None
        self.write_consent.set(False)
        self.read_consent.set(False)
        self.show({"status": "Inputs changed. Prepare a fresh reviewed reminder; a previously sent request may still finish remotely."})

    def failed(self, message):
        self.plan = None
        self.write_consent.set(False)
        self.status.set(message)

    def connect(self):
        try:
            if not self.scope_consent.get():
                raise ValueError("Review the Google scope checkbox before connecting")
            client_id, secret = self.client_id.get(), self.client_secret.get()
            self.task.start(lambda cancel: connect_session(client_id, secret, confirmed=True, cancel=cancel), self.connected, self.failed)
            self.client_secret.set("")
            self.status.set("Complete Google consent in the browser within 45 seconds. No calendar/event is created by connection alone.")
        except ValueError as exc:
            self.status.set(str(exc))

    def connected(self, credentials):
        self.credentials = credentials
        self.plan = None
        self.write_consent.set(False)
        self.status.set("Connected for this window only. Choose an app-created calendar; no event has been sent.")

    def disconnect(self):
        self.cancel()
        self.credentials = None
        self.client_secret.set("")
        self.scope_consent.set(False)
        self.status.set("Disconnected locally. Google consent/remote events remain; revoke access in Google settings if desired.")

    def create(self):
        try:
            if self.credentials is None:
                raise ValueError("Connect a session first")
            if not messagebox.askyesno("Create separate calendar?", "Create one new secondary Google calendar named RoleWeave Follow-ups? This writes to Google. Existing calendars are not reused automatically.", parent=self):
                return
            credentials = self.credentials
            self.task.start(lambda cancel: create_calendar(credentials, confirmed=True, cancel=cancel), self.created, self.failed)
            self.status.set("Creating one calendar. If cancelled or uncertain, inspect Google before trying Create again.")
        except ValueError as exc:
            self.status.set(str(exc))

    def created(self, identifier):
        self.calendar_id.set(identifier)
        self.status.set("Calendar created. Copy its ID for reuse; no follow-up event was sent. Review the reminder tab next.")

    def inputs(self):
        return self.store.load(self.identifier), self.store.application_history(self.identifier)

    def local_preview(self):
        try:
            self.task.cancel()
            self.plan = None
            self.write_consent.set(False)
            item, events = self.inputs()
            self.show({"local_only": True, "event": desired_event(item, events, include_details=self.include_details.get())})
            self.status.set("Local preview only. Connect/select a calendar and read remote state before sending.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def prepare(self):
        try:
            if self.credentials is None or not self.read_consent.get():
                raise ValueError("Connect and explicitly consent to read this calendar/event first")
            item, events = self.inputs()
            include_details, calendar_id = self.include_details.get(), self.calendar_id.get()
            desired = desired_event(item, events, include_details=include_details)
            credentials = self.credentials
            def work(cancel):
                remote = read_remote(credentials, calendar_id, desired["id"], cancel=cancel)
                return prepare_sync(item, events, calendar_id, remote, include_details=include_details), remote
            self.plan = None
            self.write_consent.set(False)
            self.task.start(work, self.prepared, self.failed)
            self.status.set("Reading one matching remote event. No calendar write is performed by preview.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def prepared(self, result):
        self.plan, self.remote = result
        previous = None if self.remote is None else {key: self.remote.get(key) for key in self.plan["event"]}
        self.show({"operation": self.plan["operation"], "calendar_id": self.plan["calendar_id"],
                   "previous_fields": previous, "proposed_event": self.plan["event"],
                   "limits": "One-way explicit reminder; no invitations/deletions or local tracking changes. ETag protects updates. Private event visibility is not encryption."})
        self.write_consent.set(False)
        self.status.set("Prepared exact create/update fields. Review and confirm this one change; local edits require a fresh preview.")

    def send(self):
        try:
            if self.plan is None or not self.write_consent.get():
                raise ValueError("Prepare and confirm the exact event change first")
            plan, credentials = copy.deepcopy(self.plan), self.credentials
            self.plan = None
            self.write_consent.set(False)
            self.task.start(lambda cancel: apply_sync(self.store, plan, credentials, confirmed=True, cancel=cancel), self.sent, self.failed)
            self.status.set("Sending one reviewed change. Cancellation cannot undo a remote write.")
        except ValueError as exc:
            self.status.set(str(exc))

    def sent(self, result):
        self.status.set("Calendar result: " + result["operation"] + ". Inspect Google to confirm. No local application history changed; re-preview before any further send.")

    def cancel(self):
        self.task.cancel()
        self.plan = None
        self.write_consent.set(False)
        self.status.set("Cancelled locally. A sent request or browser consent may still complete; inspect remote state before retrying.")

    def close(self):
        self.task.cancel()
        self.credentials = None
        self.client_secret.set("")
        self.destroy()
