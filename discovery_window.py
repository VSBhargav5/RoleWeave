"""Fetch, preview and deliberately import one public employer board."""
import sqlite3
import tkinter as tk
from tkinter import ttk

from background_task import BackgroundTask
from discovery import board_path, discovered_snapshot, fetch_board


class DiscoveryWindow(tk.Toplevel):
    def __init__(self, parent, store, markets, on_import):
        super().__init__(parent)
        self.store, self.markets, self.on_import = store, markets, on_import
        self.feed, self.visible = None, []
        self.title("RoleWeave - Public job discovery")
        self.geometry("1050x750")
        self.minsize(850, 650)
        self.transient(parent)
        self.grab_set()
        self.task = BackgroundTask(self)
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Discover one employer's public Greenhouse board", font=("Segoe UI", 15)).pack(anchor="w")
        ttk.Label(body, text="Explicit GET only. The provider sees the board token and connection metadata; your profile is not sent.", wraplength=960).pack(anchor="w", pady=6)
        inputs = ttk.Frame(body)
        inputs.pack(fill="x")
        ttk.Label(inputs, text="Board token").grid(row=0, column=0, sticky="w")
        self.token = ttk.Entry(inputs, width=26)
        self.token.grid(row=0, column=1, padx=8)
        ttk.Label(inputs, text="Employer label (your label)").grid(row=0, column=2)
        self.company = ttk.Entry(inputs, width=32)
        self.company.grid(row=0, column=3, padx=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        self.fetch_button = ttk.Button(actions, text="Fetch public board", command=self.fetch)
        self.fetch_button.pack(side="left")
        ttk.Button(actions, text="Cancel fetch", command=self.cancel).pack(side="left", padx=8)
        ttk.Label(body, text="Filter returned titles / locations locally").pack(anchor="w")
        self.query = tk.StringVar()
        query = ttk.Entry(body, textvariable=self.query)
        query.pack(fill="x")
        query.bind("<KeyRelease>", lambda _event: self.filter_rows())
        self.rows = ttk.Treeview(body, columns=("title", "location", "updated"), show="headings", height=7, selectmode="browse")
        for key, label, width in (("title", "Title", 400), ("location", "Provider location label", 280), ("updated", "Provider updated_at", 210)):
            self.rows.heading(key, text=label)
            self.rows.column(key, width=width)
        self.rows.pack(fill="both", expand=True, pady=8)
        self.rows.bind("<<TreeviewSelect>>", self.preview_selected)
        self.preview = tk.Text(body, height=9, wrap="word", state="disabled")
        self.preview.pack(fill="both", expand=True)
        bottom = ttk.Frame(body)
        bottom.pack(fill="x", pady=8)
        ttk.Label(bottom, text="Choose market explicitly").pack(side="left")
        self.market = tk.StringVar(value="")
        ttk.Combobox(bottom, values=list(markets), textvariable=self.market, state="readonly", width=29).pack(side="left", padx=8)
        ttk.Button(bottom, text="Import selected posting", command=self.import_selected).pack(side="left")
        self.status = tk.StringVar(value="No automatic eligibility, sponsorship or closure inference. Fetching does not submit an application.")
        ttk.Label(body, textvariable=self.status, wraplength=960).pack(anchor="w", pady=6)
        ttk.Button(body, text="Close", command=self.close).pack(anchor="e")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Destroy>", lambda event: self.task.cancel() if event.widget is self else None)

    def fetch(self):
        token = self.token.get().strip()
        try:
            path = board_path(token)
            if self.task.active is not None:
                raise ValueError("Cancel or wait for the current fetch")
            # Clear visible results before a new observation; failure cannot import
            # a stale listing or mutate previously saved application observations.
            self.feed = None
            self.filter_rows()
            self.fetch_button.configure(state="disabled")
            self.status.set("Fetching https://boards-api.greenhouse.io" + path)
            self.task.start(lambda event: fetch_board(token, event), self.received, self.failed)
        except ValueError as exc:
            self.status.set(str(exc))

    def received(self, feed):
        self.fetch_button.configure(state="normal")
        if feed["token"] != self.token.get().strip():
            self.status.set("Board token changed while fetching; results discarded. Fetch again.")
            return
        self.feed = feed
        self.filter_rows()
        self.status.set(f"Observed {len(feed['jobs'])} vacancy posts at {feed['fetched_at']}. This observation does not verify current availability or eligibility.")

    def failed(self, error):
        self.fetch_button.configure(state="normal")
        self.status.set(error + ". Saved jobs and stages have not been changed.")

    def cancel(self):
        self.task.cancel()
        self.fetch_button.configure(state="normal")
        self.status.set("Cancelled locally; no saved jobs changed. The public GET may already have reached the provider.")

    def filter_rows(self):
        self.rows.delete(*self.rows.get_children())
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.configure(state="disabled")
        query = self.query.get().casefold()
        self.visible = [row for row in (self.feed["jobs"] if self.feed else [])
                        if query in (row["title"] + " " + row["location"]).casefold()]
        for index, row in enumerate(self.visible):
            self.rows.insert("", "end", iid=str(index), values=(row["title"], row["location"], row["updated_at"]))

    def selected(self):
        selection = self.rows.selection()
        if not self.feed or not selection:
            raise ValueError("Fetch and select a posting first")
        if self.feed["token"] != self.token.get().strip():
            raise ValueError("Board token changed; fetch again before importing")
        return self.visible[int(selection[0])]

    def preview_selected(self, _event=None):
        try:
            row = self.selected()
        except ValueError:
            return
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", row["posting"])
        self.preview.configure(state="disabled")

    def import_selected(self):
        try:
            row = self.selected()
            company = self.company.get().strip()
            if not company:
                raise ValueError("Enter an employer label you checked against the board")
            snapshot = discovered_snapshot(row, self.markets.get(self.market.get()))
            identifier = self.store.save(snapshot, row["title"], company, row["url"])
            self.on_import(identifier)
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.status.set("Posting imported without requirements or career links. Review evidence next. Identical imports are refused; changed source records create new snapshots.")

    def close(self):
        self.task.cancel()
        self.destroy()
