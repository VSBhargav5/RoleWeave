"""Local cover-letter authoring and frozen document review; no provider calls."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from cover_letter import export_letter, letter_snapshot, make_letter, read_letter
from desktop_theme import polish_widgets, reserve_footer


class LetterWindow(tk.Toplevel):
    def __init__(self, parent, profile, job):
        super().__init__(parent)
        self.profile, self.job = profile, job
        self.prepared = None
        self.title("RoleWeave - Reviewed cover letter")
        self.geometry("1000x760")
        self.minsize(850, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=job["company"] + " - " + job["title"], font=("Segoe UI", 14), wraplength=800).pack(anchor="w")
        ttk.Label(body, text="Selected claims are copied exactly. Introduction and closing are your own statements. A private JSON version includes the full source profile; TXT includes only the letter.", wraplength=800).pack(anchor="w", pady=8)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        draft = ttk.Frame(self.tabs)
        self.output = tk.Text(self.tabs, wrap="word", state="disabled", height=6)
        self.tabs.add(draft, text="Select and write")
        self.tabs.add(self.output, text="Review exact letter")
        ttk.Label(draft, text="Reviewed claims from profile " + profile["id"][:8]).pack(anchor="w")
        self.facts = [fact for fact in profile["profile"]["facts"] if fact["reviewed"]]
        self.choices = tk.Listbox(draft, height=3, selectmode="extended", exportselection=False)
        self.choices.pack(fill="x", pady=4)
        for fact in self.facts:
            self.choices.insert("end", fact["section"] + " - " + fact["claim"])
        self.choices.bind("<<ListboxSelect>>", self.invalidate)
        ttk.Label(draft, text="Your introduction / reason for interest (required)").pack(anchor="w")
        self.motivation = tk.Text(draft, height=3, wrap="word")
        self.motivation.pack(fill="both", expand=True, pady=4)
        self.motivation.bind("<KeyRelease>", self.invalidate)
        ttk.Label(draft, text="Your closing").pack(anchor="w")
        self.closing = tk.Text(draft, height=2, wrap="word")
        self.closing.pack(fill="x", pady=4)
        self.closing.insert("1.0", "Thank you for considering my application.")
        self.closing.bind("<KeyRelease>", self.invalidate)
        ttk.Button(draft, text="Preview exact letter", command=self.preview).pack(anchor="w", pady=4)
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed every selected claim and my own statements.", variable=self.confirmed).pack(anchor="w")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Save private version JSON", command=lambda: self.export("json")).pack(side="left")
        ttk.Button(actions, text="Export letter TXT", command=lambda: self.export("txt")).pack(side="left", padx=8)
        ttk.Button(actions, text="Close", command=self.close).pack(side="right")
        self.status = tk.StringVar(value="Nothing is sent or marked submitted.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w")
        self.baseline = self.state()
        self.protocol("WM_DELETE_WINDOW", self.close)
        reserve_footer(body)
        polish_widgets(self)

    def state(self):
        return ([self.facts[index]["id"] for index in self.choices.curselection()],
                self.motivation.get("1.0", "end-1c"), self.closing.get("1.0", "end-1c"))

    def invalidate(self, _event=None):
        self.prepared = None
        self.confirmed.set(False)
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def preview(self):
        self.invalidate()
        try:
            state = self.state()
            snapshot = make_letter(self.profile, state[0], self.job, state[1], state[2], confirmed=True)
            record, _digest = letter_snapshot(snapshot)
            self.output.configure(state="normal")
            self.output.insert("1.0", record["text"])
            self.output.configure(state="disabled")
            self.prepared = (state, snapshot)
            self.tabs.select(1)
            self.status.set("Review the exact letter, then confirm before saving/exporting.")
        except ValueError as exc:
            self.status.set(str(exc))

    def export(self, format):
        try:
            if self.prepared is None or self.prepared[0] != self.state() or not self.confirmed.get():
                raise ValueError("Preview the current inputs and confirm review first")
            path = filedialog.asksaveasfilename(parent=self, defaultextension="." + format,
                    filetypes=[("Private source version" if format == "json" else "Letter text", "*." + format)])
            if path:
                export_letter(self.prepared[1], path, format, confirmed=True)
                self.baseline = self.state()
                self.status.set("Reviewed letter exported locally. No application was sent.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def close(self):
        if self.state() != self.baseline and not messagebox.askyesno("Discard unsaved letter?", "Close without saving the current letter inputs?", parent=self):
            return
        self.destroy()


class FrozenLetterWindow(tk.Toplevel):
    def __init__(self, parent, snapshot):
        record, _digest = letter_snapshot(snapshot)
        super().__init__(parent)
        self.snapshot = snapshot
        self.title("RoleWeave - Frozen letter version")
        self.geometry("900x650")
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        context = record["job_context"]
        ttk.Label(body, text=context["company"] + " - " + context["title"], font=("Segoe UI", 14), wraplength=800).pack(anchor="w")
        ttk.Label(body, text="Frozen profile " + record["profile_id"] + "; saved review " + context["id"], wraplength=800).pack(anchor="w", pady=8)
        output = tk.Text(body, wrap="word", height=8)
        output.pack(fill="both", expand=True)
        output.insert("1.0", record["text"])
        output.configure(state="disabled")
        self.confirmed = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text="I reviewed this frozen letter before exporting.", variable=self.confirmed).pack(anchor="w")
        ttk.Button(body, text="Export this letter TXT", command=self.export).pack(anchor="w", pady=8)
        self.status = tk.StringVar(value="Current profile edits do not change this file.")
        ttk.Label(body, textvariable=self.status, wraplength=800).pack(anchor="w")
        ttk.Button(body, text="Close", command=self.destroy).pack(anchor="e")
        reserve_footer(body)
        polish_widgets(self)

    def export(self):
        try:
            if not self.confirmed.get():
                raise ValueError("Review and confirm this frozen letter first")
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt", filetypes=[("Letter text", "*.txt")])
            if path:
                export_letter(self.snapshot, path, "txt", confirmed=True)
                self.status.set("Frozen letter exported. Nothing was sent.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))
