"""Edit portable employer choices, then deliberately open one discovery board."""
import copy
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from desktop_theme import polish_widgets, reserve_footer
from discovery_window import DiscoveryWindow
from employer_watchlist import read_watchlist, save_watchlist, validate_board, validate_filters, validate_watchlist
from provider_boards import PROVIDERS


class WatchlistWindow(tk.Toplevel):
    def __init__(self, parent, store, markets, on_import):
        super().__init__(parent)
        self.store, self.markets, self.on_import = store, markets, on_import
        self.boards, self.loaded_index = [], None
        self.title("RoleWeave - Employer watchlist")
        self.geometry("1050x800")
        self.minsize(900, 700)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Your employer boards", font=("Segoe UI", 15)).pack(anchor="w")
        ttk.Label(body, text="Portable source choices are separate from shelf backups. Opening a watchlist never fetches; each board still needs explicit review and Fetch.", wraplength=850).pack(anchor="w", pady=8)
        self.name = tk.StringVar(value="New employer watchlist")
        ttk.Entry(body, textvariable=self.name).pack(fill="x")
        tabs = ttk.Notebook(body)
        tabs.pack(fill="both", expand=True, pady=8)
        boards = ttk.Frame(tabs, padding=8)
        filters = ttk.Frame(tabs, padding=8)
        tabs.add(boards, text="Employer boards")
        tabs.add(filters, text="Saved local filters")
        self.rows = ttk.Treeview(boards, columns=("provider", "token", "company", "market"), show="headings", height=3)
        for key in ("provider", "token", "company", "market"):
            self.rows.heading(key, text=key.capitalize())
            self.rows.column(key, width=180)
        self.rows.pack(fill="both", expand=True, pady=6)
        self.rows.bind("<<TreeviewSelect>>", self.load_selected)
        form = ttk.Frame(boards)
        form.pack(fill="x")
        self.provider = tk.StringVar(value="greenhouse")
        self.token = tk.StringVar()
        self.company = tk.StringVar()
        self.market = tk.StringVar(value="")
        for row, (label, variable) in enumerate((("Provider", self.provider), ("Board token", self.token),
                                                ("Employer label", self.company), ("Default market (user choice)", self.market))):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=3)
            if variable is self.provider:
                field = ttk.Combobox(form, values=PROVIDERS, textvariable=variable, state="readonly")
            elif variable is self.market:
                field = ttk.Combobox(form, values=list(markets), textvariable=variable, state="readonly")
            else:
                field = ttk.Entry(form, textvariable=variable)
            field.grid(row=row, column=1, sticky="ew", padx=8)
        form.columnconfigure(1, weight=1)
        actions = ttk.Frame(boards)
        actions.pack(fill="x", pady=8)
        for label, command in (("Add board", self.add_board), ("Update selected", self.update_board),
                               ("Remove selected", self.remove_board), ("Clear editor", self.clear_editor)):
            ttk.Button(actions, text=label, command=command).pack(side="left", padx=(0, 8))
        self.include = tk.StringVar()
        self.exclude = tk.StringVar()
        self.search_description = tk.BooleanVar(value=False)
        ttk.Label(filters, text="Literal included phrase (blank includes all observed rows)").pack(anchor="w")
        ttk.Entry(filters, textvariable=self.include).pack(fill="x", pady=8)
        ttk.Label(filters, text="Literal excluded phrase (optional)").pack(anchor="w")
        ttk.Entry(filters, textvariable=self.exclude).pack(fill="x", pady=8)
        ttk.Checkbutton(filters, text="Search posting descriptions too", variable=self.search_description).pack(anchor="w")
        ttk.Label(filters, text="These phrases are applied locally after Fetch. They are not transmitted to providers.", wraplength=800).pack(anchor="w", pady=12)
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=8)
        for label, command in (("Open watchlist JSON", self.open_file), ("Save as new JSON", self.save_file),
                               ("Open selected board", self.open_board)):
            ttk.Button(footer, text=label, command=command).pack(side="left", padx=(0, 8))
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="Add explicit employer boards and save a new portable file.")
        ttk.Label(body, textvariable=self.status, wraplength=850).pack(anchor="w")
        self.editor_baseline = self.editor_state()
        self.baseline = self.state()
        self.protocol("WM_DELETE_WINDOW", self.close)
        reserve_footer(body)
        polish_widgets(self)

    def editor_state(self):
        return (self.provider.get(), self.token.get(), self.company.get(), self.market.get())

    def filters(self):
        return {"include": self.include.get(), "exclude": self.exclude.get(),
                "search_description": self.search_description.get()}

    def data(self):
        return {"format": "roleweave-watchlist-v1", "name": self.name.get(), "boards": copy.deepcopy(self.boards),
                "filters": self.filters()}

    def state(self):
        return json.dumps(self.data(), sort_keys=True), self.editor_state()

    def editor_pending(self):
        return self.editor_state() != self.editor_baseline

    def board_from_editor(self):
        return validate_board({"provider": self.provider.get(), "token": self.token.get().strip(),
                               "company": self.company.get().strip(), "market": self.markets.get(self.market.get())})

    def refresh_rows(self):
        self.rows.delete(*self.rows.get_children())
        for index, board in enumerate(self.boards):
            self.rows.insert("", "end", iid=str(index), values=tuple(board[key] for key in ("provider", "token", "company", "market")))

    def clear_editor(self):
        self.loaded_index = None
        self.provider.set("greenhouse")
        self.token.set("")
        self.company.set("")
        self.market.set("")
        self.rows.selection_remove(*self.rows.selection())
        self.editor_baseline = self.editor_state()

    def selected_index(self):
        selection = self.rows.selection()
        if not selection:
            raise ValueError("Select a saved board row")
        return int(selection[0])

    def load_selected(self, _event=None):
        try:
            index = self.selected_index()
        except ValueError:
            return
        if index == self.loaded_index:
            return
        if self.editor_pending() and not messagebox.askyesno("Discard board editor edits?", "Discard unapplied board edits before selecting another row?", parent=self):
            if self.loaded_index is not None:
                self.rows.selection_set(str(self.loaded_index))
            else:
                self.rows.selection_remove(*self.rows.selection())
            return
        board = self.boards[index]
        self.provider.set(board["provider"])
        self.token.set(board["token"])
        self.company.set(board["company"])
        self.market.set(next(label for label, value in self.markets.items() if value == board["market"]))
        self.loaded_index = index
        self.editor_baseline = self.editor_state()

    def apply_board(self, replacing=None):
        board = self.board_from_editor()
        boards = copy.deepcopy(self.boards)
        if replacing is None:
            boards.append(board)
        else:
            boards[replacing] = board
        validate_watchlist({"format": "roleweave-watchlist-v1", "name": "Draft", "boards": boards, "filters": self.filters()})
        self.boards = boards
        self.clear_editor()
        self.refresh_rows()
        self.status.set("Draft board choices updated; save a new JSON to keep them.")

    def add_board(self):
        try:
            self.apply_board()
        except ValueError as exc:
            self.status.set(str(exc))

    def update_board(self):
        try:
            self.apply_board(self.selected_index())
        except ValueError as exc:
            self.status.set(str(exc))

    def remove_board(self):
        try:
            del self.boards[self.selected_index()]
            self.clear_editor()
            self.refresh_rows()
            self.status.set("Board removed from this draft; existing JSON files are unchanged.")
        except ValueError as exc:
            self.status.set(str(exc))

    def guard_editor(self):
        if self.editor_pending():
            raise ValueError("Add/update the board or Clear editor before using/saving this watchlist")

    def open_file(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard watchlist draft?", "Discard unsaved watchlist edits and open another file?", parent=self):
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("Employer watchlist", "*.json")])
        if not path:
            return
        try:
            data = read_watchlist(path)
            self.boards = data["boards"]
            self.name.set(data["name"])
            self.include.set(data["filters"]["include"])
            self.exclude.set(data["filters"]["exclude"])
            self.search_description.set(data["filters"]["search_description"])
            self.clear_editor()
            self.refresh_rows()
            self.baseline = self.state()
            self.status.set("Watchlist opened locally. No source was fetched.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def save_file(self):
        try:
            self.guard_editor()
            data = validate_watchlist(self.data())
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Private employer watchlist", "*.json")])
            if path:
                save_watchlist(data, path)
                self.baseline = self.state()
                self.status.set("Portable watchlist saved. Keep it separately from shelf backups.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def open_board(self):
        try:
            self.guard_editor()
            board = self.boards[self.selected_index()]
            filters = validate_filters(self.filters())
            child = DiscoveryWindow(self, self.store, self.markets, self.on_import)
            child.provider.set(board["provider"])
            child.token.insert(0, board["token"])
            child.company.insert(0, board["company"])
            child.market.set(next(label for label, value in self.markets.items() if value == board["market"]))
            child.query.set(filters["include"])
            child.exclude.set(filters["exclude"])
            child.search_description.set(filters["search_description"])
            child.status.set("Saved board choices loaded. Review market/employer and explicitly Fetch.")
            child.bind("<Destroy>", lambda event: self.grab_set() if event.widget is child and self.winfo_viewable() else None, add="+")
            return child
        except ValueError as exc:
            self.status.set(str(exc))

    def close(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard watchlist draft?", "Close without saving these watchlist edits?", parent=self):
            return
        self.destroy()
