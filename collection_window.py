"""Explicit multi-board observations with per-source evidence and selected imports."""
import copy
import sqlite3
import tkinter as tk
from tkinter import filedialog, ttk

from background_task import BackgroundTask
from collection_archive import archive_collection, read_collection_archive
from desktop_theme import polish_widgets, reserve_footer
from discovery import discovered_snapshot
from employer_watchlist import validate_watchlist
from watchlist_fetch import collection_rows, fetch_watchlist, validate_collection, validate_selection


class CollectionWindow(tk.Toplevel):
    def __init__(self, parent, store, watchlist, indices, markets, on_import):
        data = copy.deepcopy(validate_watchlist(watchlist))
        indices = validate_selection(data, indices)
        super().__init__(parent)
        self.store, self.markets, self.on_import = store, markets, on_import
        self.watchlist_data, self.selected_indices = data, indices
        self.collection, self.visible = None, []
        self.task = BackgroundTask(self)
        self.title("RoleWeave - Selected employer boards")
        self.geometry("1100x820")
        self.minsize(900, 700)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        self.heading = tk.StringVar(value=data["name"])
        ttk.Label(body, textvariable=self.heading, font=("Segoe UI", 15), wraplength=850).pack(anchor="w")
        ttk.Label(body, text="Fetch only selected public boards. Each source keeps its own observation time/status. Review source and market before importing one posting.", wraplength=850).pack(anchor="w", pady=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=4)
        self.fetch_button = ttk.Button(actions, text="Fetch selected boards", command=self.fetch, style="Primary.TButton")
        self.fetch_button.pack(side="left")
        ttk.Button(actions, text="Cancel fetch", command=self.cancel).pack(side="left", padx=8)
        self.tools_menu = tk.Menu(self, tearoff=False)
        self.tools_menu.add_command(label="Save private collection observation", command=self.save_archive)
        self.tools_menu.add_command(label="Open saved collection observation", command=self.open_archive)
        ttk.Menubutton(actions, text="Observation tools", menu=self.tools_menu).pack(side="left", padx=8)
        self.coverage = tk.StringVar(value=f"{len(indices)} boards selected; nothing fetched")
        ttk.Label(actions, textvariable=self.coverage).pack(side="left", padx=8)
        filters = ttk.Frame(body)
        filters.pack(fill="x", pady=4)
        self.include = tk.StringVar(value=data["filters"]["include"])
        self.exclude = tk.StringVar(value=data["filters"]["exclude"])
        self.search_description = tk.BooleanVar(value=data["filters"]["search_description"])
        ttk.Label(filters, text="Include phrase").grid(row=0, column=0, sticky="w")
        include = ttk.Entry(filters, textvariable=self.include, width=23)
        include.grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Label(filters, text="Exclude phrase").grid(row=0, column=2)
        exclude = ttk.Entry(filters, textvariable=self.exclude, width=23)
        exclude.grid(row=0, column=3, padx=8, sticky="ew")
        for field in (include, exclude):
            field.bind("<KeyRelease>", lambda _event: self.filter_rows())
        ttk.Checkbutton(filters, text="Search descriptions too", variable=self.search_description, command=self.filter_rows).grid(row=1, column=0, columnspan=2, sticky="w")
        filters.columnconfigure(1, weight=1)
        filters.columnconfigure(3, weight=1)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True, pady=8)
        results = ttk.Frame(self.tabs)
        source_tab = ttk.Frame(self.tabs)
        self.tabs.add(results, text="Observed postings")
        self.tabs.add(source_tab, text="Source observations / failures")
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1, minsize=80)
        results.rowconfigure(1, weight=1, minsize=80)
        listing = ttk.Frame(results)
        listing.grid(row=0, column=0, sticky="nsew")
        listing.columnconfigure(0, weight=1)
        listing.rowconfigure(0, weight=1)
        self.rows = ttk.Treeview(listing, columns=("title", "company", "provider", "location"), show="headings", height=3, selectmode="browse")
        for key, label, width in (("title", "Title", 270), ("company", "Your employer label", 190),
                                  ("provider", "Provider", 110), ("location", "Provider location label", 230)):
            self.rows.heading(key, text=label)
            self.rows.column(key, width=width)
        self.rows.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(listing, command=self.rows.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(listing, orient="horizontal", command=self.rows.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.rows.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.rows.bind("<<TreeviewSelect>>", self.preview_selected)
        self.preview = tk.Text(results, height=4, wrap="word", state="disabled")
        self.preview.grid(row=1, column=0, sticky="nsew", pady=8)
        self.sources = tk.Text(source_tab, height=8, wrap="word", state="disabled")
        self.sources.pack(fill="both", expand=True)
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=8)
        ttk.Label(footer, text="Review market").pack(side="left")
        self.market = tk.StringVar(value="")
        ttk.Combobox(footer, values=list(markets), textvariable=self.market, state="readonly", width=27).pack(side="left", padx=8)
        ttk.Button(footer, text="Import selected posting", command=self.import_selected).pack(side="left")
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="No background scan, stage change or eligibility inference.")
        ttk.Label(body, textvariable=self.status, wraplength=850).pack(anchor="w")
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Destroy>", lambda event: self.task.cancel() if event.widget is self else None)
        reserve_footer(body)
        polish_widgets(self)

    def set_text(self, widget, value):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", value)
        widget.configure(state="disabled")

    def clear_observation(self):
        self.collection = None
        self.visible = []
        self.set_text(self.sources, "")
        self.filter_rows()

    def archive_snapshot(self):
        if self.task.active is not None or self.collection is None:
            raise ValueError("Finish/cancel fetching and choose a current observation first")
        snapshot = copy.deepcopy(self.collection)
        snapshot["watchlist"]["filters"] = {"include": self.include.get(), "exclude": self.exclude.get(),
                                               "search_description": self.search_description.get()}
        return validate_collection(snapshot)

    def save_archive(self):
        try:
            snapshot = self.archive_snapshot()
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Private collection archive", "*.json")])
            if path:
                archive_collection(snapshot, path)
                self.status.set("All original source observations and current local view filters saved privately. No file was overwritten.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_archive(self):
        try:
            if self.task.active is not None:
                raise ValueError("Wait for or cancel fetching before opening another observation")
            path = filedialog.askopenfilename(parent=self, filetypes=[("Private collection archive", "*.json")])
            if not path:
                return
            collection = read_collection_archive(path)
            self.watchlist_data = copy.deepcopy(collection["watchlist"])
            self.selected_indices = list(collection["selected_indices"])
            self.heading.set(self.watchlist_data["name"] + " - saved observation")
            self.include.set(self.watchlist_data["filters"]["include"])
            self.exclude.set(self.watchlist_data["filters"]["exclude"])
            self.search_description.set(self.watchlist_data["filters"]["search_description"])
            self.received(collection)
            self.status.set("Offline replay. Original source times are preserved; current availability remains unverified.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def fetch(self):
        if self.task.active is not None:
            self.status.set("Cancel or wait for the current fetch")
            return
        self.clear_observation()
        self.fetch_button.configure(state="disabled")
        self.status.set("Fetching only the selected public boards; source failures will be shown separately.")
        self.task.start(lambda event: fetch_watchlist(self.watchlist_data, self.selected_indices, event), self.received, self.failed)

    def received(self, collection):
        self.fetch_button.configure(state="normal")
        try:
            validate_collection(collection)
            if collection["watchlist"] != self.watchlist_data or collection["selected_indices"] != self.selected_indices:
                raise ValueError("Selected source scope changed; returned results discarded")
            self.collection = copy.deepcopy(collection)
        except ValueError as exc:
            self.failed(str(exc))
            return
        lines = []
        success = {entry["board_index"]: entry["feed"] for entry in collection["feeds"]}
        failures = {entry["board_index"]: entry["error"] for entry in collection["failures"]}
        for index in self.selected_indices:
            board = self.watchlist_data["boards"][index]
            lines.append(f"{board['company']} | {board['provider']} / {board['token']} | your default market: {board['market']}")
            if index in success:
                feed = success[index]
                lines.append(f"OBSERVED {len(feed['jobs'])} posts at {feed['fetched_at']}\nResponse SHA256: {feed['response_sha256']}")
            else:
                lines.append("FAILED: " + failures[index] + "\nNo absence/closure inference is made.")
            lines.append("")
        self.set_text(self.sources, "\n".join(lines))
        self.filter_rows()
        self.status.set(f"{len(success)} source observations; {len(failures)} failed sources. Inspect per-source details; coverage and eligibility are unverified.")

    def failed(self, message):
        self.fetch_button.configure(state="normal")
        self.clear_observation()
        self.status.set(message + ". No saved jobs or stages changed.")

    def cancel(self):
        self.task.cancel()
        self.fetch_button.configure(state="normal")
        self.status.set("Cancelled locally. A public GET may already have reached a provider.")

    def filter_rows(self):
        self.rows.delete(*self.rows.get_children())
        self.visible = []
        self.set_text(self.preview, "")
        self.market.set("")
        if self.collection is None:
            self.coverage.set(f"{len(self.selected_indices)} boards selected; no current observation")
            return
        try:
            self.visible = collection_rows(self.collection, {"include": self.include.get(), "exclude": self.exclude.get(),
                                                            "search_description": self.search_description.get()})
        except ValueError as exc:
            self.status.set(str(exc))
            return
        for index, row in enumerate(self.visible):
            self.rows.insert("", "end", iid=str(index), values=(row["title"], row["company"], row["provider"], row["location"]))
        total = sum(len(entry["feed"]["jobs"]) for entry in self.collection["feeds"])
        self.coverage.set(f"{len(self.visible)} of {total} observed posts; {len(self.collection['failures'])} failed sources")

    def selected(self):
        if self.task.active is not None:
            raise ValueError("Wait for or cancel the current fetch before importing")
        selection = self.rows.selection()
        if self.collection is None or not selection:
            raise ValueError("Fetch and select one observed posting first")
        return self.visible[int(selection[0])]

    def preview_selected(self, _event=None):
        try:
            row = self.selected()
        except ValueError:
            return
        self.set_text(self.preview, f"Your employer label: {row['company']}\nProvider: {row['provider']} / {row['token']}\nObserved: {row['fetched_at']}\nResponse SHA256: {row['response_sha256']}\n\n" + row["posting"])
        self.market.set(next(label for label, value in self.markets.items() if value == row["market"]))

    def import_selected(self):
        try:
            row = self.selected()
            snapshot = discovered_snapshot(row, self.markets.get(self.market.get()))
            identifier = self.store.save(snapshot, row["title"], row["company"], row["url"])
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.status.set("Selected posting imported as an unreviewed snapshot. No application was submitted.")
        try:
            self.on_import(identifier)
        except (OSError, ValueError, sqlite3.Error):
            self.status.set("Posting saved, but workspace refresh failed. Reopen it from the shelf.")

    def close(self):
        self.task.cancel()
        self.destroy()
