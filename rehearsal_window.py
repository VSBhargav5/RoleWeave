"""Private answer drafts for exact job requirements; no grading or learning claims."""
import copy
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from desktop_theme import polish_widgets, reserve_footer
from rehearsal_cards import practice_cards
from rehearsal_journal import export_rehearsal, make_rehearsal, rehearsal_snapshot
from resume_versions import job_context


class RehearsalWindow(tk.Toplevel):
    def __init__(self, parent, item, snapshot=None):
        cards = practice_cards(item)
        loaded = rehearsal_snapshot(snapshot)[0] if snapshot is not None else None
        if loaded is not None and loaded["job_context"] != job_context(item):
            raise ValueError("Rehearsal version belongs to another exact saved review")
        super().__init__(parent)
        self.item, self.cards = copy.deepcopy(item), cards
        self.card_by_id = {card["requirement_id"]: card for card in cards}
        self.selected_ids, self.answers, self.position = [], {}, 0
        self.elapsed_seconds = loaded["elapsed_seconds"] if loaded else 0
        self.last_snapshot = snapshot
        self.title("RoleWeave - Private rehearsal journal")
        self.geometry("1050x800")
        self.minsize(900, 700)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        role = item["company"] + " - " + item["title"]
        ttk.Label(body, text=role[:200] + ("..." if len(role) > 200 else ""), font=("Segoe UI", 14), wraplength=850).pack(anchor="w")
        ttk.Label(body, text="Private versions include the full frozen review/facts. Drafts and recorded time do not verify learning. Saved review " + item["id"][:8], wraplength=850).pack(anchor="w", pady=8)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        selection = ttk.Frame(self.tabs, padding=8)
        practice = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(selection, text="Choose source questions")
        self.tabs.add(practice, text="Draft and rehearse")
        ttk.Label(selection, text="Choose 1-30 exact requirements (Ctrl-click for multiple).").pack(anchor="w")
        self.choices = tk.Listbox(selection, selectmode="extended", exportselection=False, height=8)
        self.choices.pack(fill="both", expand=True, pady=8)
        for card in cards:
            self.choices.insert("end", card["quote"][:160])
        ttk.Button(selection, text="Use selected questions", command=self.start_selected).pack(anchor="w")
        practice.columnconfigure(0, weight=1)
        practice.rowconfigure(2, weight=1, minsize=80)
        practice.rowconfigure(3, weight=1, minsize=80)
        self.counter = tk.StringVar()
        ttk.Label(practice, textvariable=self.counter).grid(row=0, column=0, sticky="w")
        navigation = ttk.Frame(practice)
        navigation.grid(row=1, column=0, sticky="ew", pady=4)
        ttk.Button(navigation, text="Previous", command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(navigation, text="Reveal linked evidence", command=self.reveal_evidence).pack(side="left", padx=8)
        ttk.Button(navigation, text="Next", command=lambda: self.move(1)).pack(side="left")
        self.source = tk.Text(practice, height=4, wrap="word", state="disabled")
        self.source.grid(row=2, column=0, sticky="nsew", pady=8)
        self.draft_tabs = ttk.Notebook(practice)
        self.draft_tabs.grid(row=3, column=0, sticky="nsew")
        self.answer = tk.Text(self.draft_tabs, height=4, wrap="word")
        self.reflection = tk.Text(self.draft_tabs, height=4, wrap="word")
        self.draft_tabs.add(self.answer, text="Your answer draft (up to 6000 characters)")
        self.draft_tabs.add(self.reflection, text="Your reflection (up to 2000 characters)")
        self.confirmed = tk.BooleanVar(value=False)
        for field in (self.answer, self.reflection):
            field.bind("<KeyRelease>", lambda _event: self.confirmed.set(False))
        ttk.Checkbutton(body, text="I reviewed this private rehearsal version before exporting.", variable=self.confirmed).pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Save new private journal JSON", command=self.save).pack(side="left")
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="Select source questions. No answers are generated or graded.")
        ttk.Label(body, textvariable=self.status, wraplength=850).pack(anchor="w")
        if loaded:
            self.selected_ids = [entry["requirement_id"] for entry in loaded["answers"]]
            self.answers = {entry["requirement_id"]: copy.deepcopy(entry) for entry in loaded["answers"]}
            for index, card in enumerate(cards):
                if card["requirement_id"] in self.answers:
                    self.choices.selection_set(index)
            self.tabs.select(1)
        self.render()
        self.baseline = self.state()
        self.protocol("WM_DELETE_WINDOW", self.close)
        reserve_footer(body)
        polish_widgets(self)

    def capture_current(self):
        if self.selected_ids:
            entry = self.answers[self.selected_ids[self.position]]
            entry["answer"] = self.answer.get("1.0", "end-1c")
            entry["reflection"] = self.reflection.get("1.0", "end-1c")

    def state(self):
        self.capture_current()
        return json.dumps({"selected": self.selected_ids, "answers": [self.answers[key] for key in self.selected_ids],
                           "elapsed_seconds": self.elapsed_seconds}, sort_keys=True)

    def start_selected(self):
        self.capture_current()
        selected = [self.cards[index]["requirement_id"] for index in self.choices.curselection()]
        entries = [copy.deepcopy(self.answers.get(key, {"requirement_id": key, "answer": "", "reflection": ""})) for key in selected]
        try:
            make_rehearsal(self.item, entries, elapsed_seconds=self.elapsed_seconds, confirmed=True)
            removed = [entry for key, entry in self.answers.items() if key not in selected and (entry["answer"].strip() or entry["reflection"].strip())]
            if removed and not messagebox.askyesno("Remove draft answers?", "The new selection removes questions with draft text. Discard those draft answers?", parent=self):
                return
            self.selected_ids, self.answers, self.position = selected, {entry["requirement_id"]: entry for entry in entries}, 0
            self.confirmed.set(False)
            self.last_snapshot = None
            self.render()
            self.tabs.select(1)
            self.status.set("Source questions selected. Draft in your own words; reveal linked evidence when ready.")
        except ValueError as exc:
            self.status.set(str(exc))

    def render(self, reveal=False):
        if self.selected_ids:
            key = self.selected_ids[self.position]
            card, entry = self.card_by_id[key], self.answers[key]
            self.counter.set(f"Question {self.position + 1} of {len(self.selected_ids)}")
            content = card["quote"] + "\n\n" + card["prompt"] + "\n\n" + (card["evidence"] if reveal else "Think through your example before revealing linked evidence.")
        else:
            entry = {"answer": "", "reflection": ""}
            content = "Choose exact requirement questions before drafting. Open requirements remain review questions."
            self.counter.set("No source questions selected")
        self.source.configure(state="normal")
        self.source.delete("1.0", "end")
        self.source.insert("1.0", content)
        self.source.configure(state="disabled")
        for field, key in ((self.answer, "answer"), (self.reflection, "reflection")):
            field.configure(state="normal")
            field.delete("1.0", "end")
            field.insert("1.0", entry[key])
            field.configure(state="normal" if self.selected_ids else "disabled")

    def move(self, delta):
        self.capture_current()
        if self.selected_ids:
            self.position = (self.position + delta) % len(self.selected_ids)
        self.render()

    def reveal_evidence(self):
        self.capture_current()
        self.render(reveal=True)

    def save(self):
        try:
            current = self.state()
            if current == self.baseline and self.last_snapshot is not None:
                raise ValueError("No changed rehearsal inputs to save; retain the existing version")
            if not self.confirmed.get():
                raise ValueError("Review and confirm this private version first")
            entries = [copy.deepcopy(self.answers[key]) for key in self.selected_ids]
            snapshot = make_rehearsal(self.item, entries, elapsed_seconds=self.elapsed_seconds, confirmed=True)
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Private rehearsal version", "*.json")])
            if path:
                export_rehearsal(snapshot, path, confirmed=True)
                self.last_snapshot = snapshot
                self.baseline = self.state()
                self.status.set("Private source-bound version saved. This does not verify learning or change application history.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def close(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard unsaved rehearsal?", "Close without saving these answer/reflection changes?", parent=self):
            return
        self.destroy()
