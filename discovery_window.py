"""Fetch, preview and deliberately import one public employer board."""
import sqlite3
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
from desktop_theme import polish_widgets, reserve_footer

from background_task import BackgroundTask
from discovery import discovered_snapshot
from provider_boards import PROVIDERS, source_endpoint, fetch_source, board_identity
from discovery_archive import export_archive, load_archive, compare_observations


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
        ttk.Label(body, text="Discover one employer's public job board", font=("Segoe UI", 15)).pack(anchor="w")
        ttk.Label(body, text="Explicit GET only. The provider sees the board token and connection metadata; your profile is not sent.", wraplength=800).pack(anchor="w", pady=4)
        inputs = ttk.Frame(body)
        inputs.pack(fill="x")
        self.provider = tk.StringVar(value="greenhouse")
        ttk.Label(inputs, text="Provider").grid(row=0, column=0, sticky="w")
        provider = ttk.Combobox(inputs, values=PROVIDERS, textvariable=self.provider, state="readonly", width=24)
        provider.grid(row=0, column=1, padx=8, pady=(0, 6))
        provider.bind("<<ComboboxSelected>>", lambda _event: self.source_changed())
        ttk.Label(inputs, text="Lever EU has a separate board region; choose it explicitly.").grid(row=0, column=2, columnspan=2, sticky="w")
        ttk.Label(inputs, text="Board token").grid(row=1, column=0, sticky="w")
        self.token = ttk.Entry(inputs, width=26)
        self.token.grid(row=1, column=1, padx=8)
        ttk.Label(inputs, text="Employer label (your label)").grid(row=1, column=2)
        self.company = ttk.Entry(inputs, width=32)
        self.company.grid(row=1, column=3, padx=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        self.fetch_button = ttk.Button(actions, text="Fetch public board", style="Primary.TButton", command=self.fetch)
        self.fetch_button.pack(side="left")
        ttk.Button(actions, text="Cancel fetch", command=self.cancel).pack(side="left", padx=8)
        observation_tools = ttk.Menubutton(actions, text="Observation tools")
        menu = tk.Menu(observation_tools, tearoff=False)
        for label, command in (("Use employer board URL", self.use_board_url),
                               ("Save observation", self.export_observation),
                               ("Open saved observation", self.open_observation),
                               ("Compare observation", self.compare_observation)):
            menu.add_command(label=label, command=command)
        observation_tools.configure(menu=menu)
        observation_tools.pack(side="left", padx=8)
        ttk.Label(body, text="Filter returned titles / locations locally").pack(anchor="w")
        self.query = tk.StringVar()
        query = ttk.Entry(body, textvariable=self.query)
        query.pack(fill="x")
        query.bind("<KeyRelease>", lambda _event: self.filter_rows())
        filter_options = ttk.Frame(body)
        filter_options.pack(fill="x", pady=4)
        self.search_description = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_options, text="Search description too", variable=self.search_description, command=self.filter_rows).pack(side="left")
        ttk.Label(filter_options, text="Exclude phrase").pack(side="left", padx=8)
        self.exclude = tk.StringVar()
        exclude = ttk.Entry(filter_options, textvariable=self.exclude, width=26)
        exclude.pack(side="left")
        exclude.bind("<KeyRelease>", lambda _event: self.filter_rows())
        self.filtered_count = tk.StringVar(value="0 of 0 observed posts")
        ttk.Label(filter_options, textvariable=self.filtered_count).pack(side="right")
        self.rows = ttk.Treeview(body, columns=("title", "location", "updated"), show="headings", height=2, selectmode="browse")
        for key, label, width in (("title", "Title", 400), ("location", "Provider location label", 280), ("updated", "Provider time label", 210)):
            self.rows.heading(key, text=label)
            self.rows.column(key, width=width)
        self.rows.pack(fill="both", expand=True, pady=4)
        self.rows.bind("<<TreeviewSelect>>", self.preview_selected)
        self.preview = tk.Text(body, height=3, wrap="word", state="disabled")
        self.preview.pack(fill="both", expand=True)
        bottom = ttk.Frame(body)
        bottom.pack(fill="x", pady=8)
        ttk.Label(bottom, text="Choose market explicitly").pack(side="left")
        self.market = tk.StringVar(value="")
        ttk.Combobox(bottom, values=list(markets), textvariable=self.market, state="readonly", width=29).pack(side="left", padx=8)
        ttk.Button(bottom, text="Import selected posting", command=self.import_selected).pack(side="left")

        self.status = tk.StringVar(value="No automatic eligibility, sponsorship or closure inference. Fetching does not submit an application.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w", pady=4)
        ttk.Button(body, text="Close", command=self.close).pack(anchor="e")
        reserve_footer(body)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Destroy>", lambda event: self.task.cancel() if event.widget is self else None)

    def fetch(self):
        token = self.token.get().strip()
        try:
            provider = self.provider.get()
            host, path = source_endpoint(provider, token)
            if self.task.active is not None:
                raise ValueError("Cancel or wait for the current fetch")
            # Clear visible results before a new observation; failure cannot import
            # a stale listing or mutate previously saved application observations.
            self.feed = None
            self.filter_rows()
            self.fetch_button.configure(state="disabled")
            self.status.set("Fetching https://" + host + path)
            self.task.start(lambda event: fetch_source(provider, token, event), self.received, self.failed)
        except ValueError as exc:
            self.status.set(str(exc))

    def use_board_url(self):
        value = simpledialog.askstring("Employer board", "Paste the HTTPS employer board URL (not an individual job):", parent=self)
        if value is None:
            return
        try:
            provider, token = board_identity(value)
            self.source_changed()
            self.provider.set(provider)
            self.token.delete(0, "end")
            self.token.insert(0, token)
            self.company.delete(0, "end")
            self.status.set("Board selected locally. Enter a checked employer label, then explicitly Fetch.")
        except ValueError as exc:
            self.status.set(str(exc))

    def compare_observation(self):
        try:
            if not self.feed:
                raise ValueError("Fetch or open the current observation first")
            path = filedialog.askopenfilename(parent=self, filetypes=[("Earlier discovery archive", "*.json")])
            if not path:
                return
            before = load_archive(path)
            result = compare_observations(before, self.feed)
            window = tk.Toplevel(self)
            window.title("RoleWeave - Observed board changes")
            window.geometry("850x550")
            output = tk.Text(window, wrap="word")
            output.pack(fill="both", expand=True, padx=16, pady=16)
            output.insert("1.0", "Earlier: " + before["fetched_at"] + "\nCurrent: " + self.feed["fetched_at"] +
                          "\nNot observed does not mean closed. No saved jobs or stages changed.\n\n" +
                          "\n".join(row["state"] + " | " + row["title"] + " | " + row["url"] for row in result))
            output.configure(state="disabled")
            ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)
            return window
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def export_observation(self):
        try:
            if not self.feed:
                raise ValueError("Fetch or open an observation first")
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Private discovery archive", "*.json")])
            if path:
                export_archive(self.feed, path)
                self.status.set("Observation saved with original response bytes. Keep private; integrity is not authenticity.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_observation(self):
        path = filedialog.askopenfilename(parent=self, filetypes=[("Private discovery archive", "*.json")])
        if not path:
            return
        try:
            feed = load_archive(path)
            self.task.cancel()
            self.provider.set(feed["provider"])
            self.token.delete(0, "end")
            self.token.insert(0, feed["token"])
            self.company.delete(0, "end")
            self.received(feed)
            self.status.set("Offline replay at " + feed["fetched_at"] + "; availability unverified. Enter a checked employer label before importing.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def source_changed(self):
        self.task.cancel()
        self.feed = None
        self.filter_rows()
        self.fetch_button.configure(state="normal")
        self.status.set("Provider changed. Fetch the selected board before importing.")

    def received(self, feed):
        self.fetch_button.configure(state="normal")
        if feed.get("provider", "greenhouse") != self.provider.get():
            self.feed = None
            self.filter_rows()
            self.status.set("Provider changed while fetching; results discarded.")
            return
        if feed["token"] != self.token.get().strip():
            self.feed = None
            self.filter_rows()
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
        excluded = self.exclude.get().casefold()
        observed = self.feed["jobs"] if self.feed else []
        self.visible = []
        for row in observed:
            haystack = row["title"] + " " + row["location"]
            if self.search_description.get():
                haystack += " " + row["posting"]
            haystack = haystack.casefold()
            if query in haystack and (not excluded or excluded not in haystack):
                self.visible.append(row)
        self.filtered_count.set(f"{len(self.visible)} of {len(observed)} observed posts")
        for index, row in enumerate(self.visible):
            self.rows.insert("", "end", iid=str(index), values=(row["title"], row["location"], row["updated_at"]))

    def selected(self):
        selection = self.rows.selection()
        if not self.feed or not selection:
            raise ValueError("Fetch and select a posting first")
        if self.feed.get("provider", "greenhouse") != self.provider.get():
            raise ValueError("Discovery provider changed; fetch again before importing")
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
        self.preview.insert("1.0", f"Fetch observed UTC: {self.feed['fetched_at']}\nResponse byte SHA256: {self.feed['response_sha256']}\n\n" + row["posting"])
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
