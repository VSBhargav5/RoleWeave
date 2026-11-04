"""Human-authored career details and reusable sourced facts."""
import copy
import json
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from uuid import uuid4
from desktop_theme import polish_widgets, reserve_footer

from career_profile import PROFILE_FIELDS, SECTIONS, imported_career_facts, validate_profile
from career_profile import profile_snapshot
from safe_export import publish_bytes


class CareerProfileEditor(tk.Toplevel):
    def __init__(self, parent, store, on_save, job=None):
        super().__init__(parent)
        self.store, self.on_save, self.job = store, on_save, job
        self.title("RoleWeave - Career profile")
        self.geometry("960x760")
        self.minsize(800, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Your reusable career profile", font=("Segoe UI", 17)).pack(anchor="w")
        ttk.Label(body, text="Enter only facts you can defend. Saving a correction preserves earlier versions.", wraplength=880).pack(anchor="w", pady=8)
        versions = ttk.Frame(body)
        versions.pack(fill="x", pady=4)
        self.version_choice = ttk.Combobox(versions, state="readonly", width=52)
        self.version_choice.pack(side="left", fill="x", expand=True)
        self.version_choice.bind("<<ComboboxSelected>>", self.load_version)
        ttk.Button(versions, text="Make selected version active", command=self.activate).pack(side="left", padx=8)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True, pady=8)
        details = ttk.Frame(self.tabs, padding=12)
        facts = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(details, text="Identity and summary")
        self.tabs.add(facts, text="Career / project facts")
        details.columnconfigure(1, weight=1)
        self.fields = {}
        for row, key in enumerate(PROFILE_FIELDS[:-1]):
            ttk.Label(details, text=key.replace("_", " ").title() + (" *" if key == "name" else "")).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
            field = ttk.Entry(details)
            field.grid(row=row, column=1, sticky="ew")
            self.fields[key] = field
        ttk.Label(details, text="Summary - your own reviewed wording; optional").grid(row=6, column=0, columnspan=2, sticky="w", pady=(16, 6))
        self.summary = tk.Text(details, height=7, wrap="word", undo=True)
        self.summary.grid(row=7, column=0, columnspan=2, sticky="nsew")
        details.rowconfigure(7, weight=1)
        ttk.Label(details, text="Dates, employers, degrees and metrics are never inferred. Include them in a claim only if you can verify them.", wraplength=850).grid(row=8, column=0, columnspan=2, sticky="w", pady=10)
        facts.columnconfigure(0, weight=1)
        facts.columnconfigure(1, weight=2)
        facts.rowconfigure(0, weight=1)
        fact_list = ttk.Frame(facts, padding=(0, 0, 14, 0))
        fact_list.grid(row=0, column=0, sticky="nsew")
        fact_form = ttk.Frame(facts)
        fact_form.grid(row=0, column=1, sticky="nsew")
        self.fact_query = tk.StringVar()
        query_entry = ttk.Entry(fact_list, textvariable=self.fact_query)
        query_entry.pack(fill="x", pady=(0, 5))
        query_entry.bind("<KeyRelease>", lambda _event: self.refresh_facts())
        self.facts = tk.Listbox(fact_list, height=5, width=24, exportselection=False)
        self.facts.pack(fill="both", expand=True)
        actions = ttk.Frame(fact_list)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Load selected fact", command=self.load_fact).pack(fill="x")
        ttk.Button(actions, text="Remove from draft", command=self.remove_fact).pack(fill="x", pady=5)
        ttk.Button(actions, text="Copy linked job facts", command=self.copy_job_facts).pack(fill="x")
        ttk.Label(fact_form, text="Claim: describe its project, employment, course or skill context", wraplength=340).pack(anchor="w")
        self.claim = tk.Text(fact_form, height=3, width=32, wrap="word")
        self.claim.pack(fill="x", pady=4)
        ttk.Label(fact_form, text="Source / provenance").pack(anchor="w")
        self.source = ttk.Entry(fact_form, width=28)
        self.source.pack(fill="x", pady=4)
        controls = ttk.Frame(fact_form)
        controls.pack(fill="x", pady=4)
        self.section = tk.StringVar(value="Additional")
        ttk.Combobox(controls, textvariable=self.section, values=SECTIONS, state="readonly", width=18).pack(fill="x")
        self.reviewed = tk.BooleanVar(value=False)
        ttk.Checkbutton(controls, text="I reviewed this claim and source", variable=self.reviewed).pack(anchor="w")
        buttons = ttk.Frame(fact_form)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Add new fact", command=self.add_fact).grid(row=0, column=0, sticky="w")
        ttk.Button(buttons, text="Update loaded fact", command=self.update_fact).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Button(buttons, text="Clear fact fields", command=self.clear_fact).grid(row=1, column=0, columnspan=2, sticky="w", pady=5)
        reserve_footer(fact_list)
        self.status = tk.StringVar(value="Profile revisions affect future copies. Older job reviews and resume versions remain unchanged.")
        ttk.Label(body, textvariable=self.status, wraplength=880).pack(anchor="w", pady=8)
        footer = ttk.Frame(body)
        footer.pack(fill="x")
        ttk.Button(footer, text="Save new profile version", style="Primary.TButton", command=self.save).pack(side="left")
        ttk.Button(footer, text="Import profile JSON", command=self.import_profile).pack(side="left", padx=6)
        ttk.Button(footer, text="Export saved profile", command=self.export_profile).pack(side="left")
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        self.versions = store.list_profiles()
        self.version_choice.configure(values=[row["created_at"][:19] + " UTC - " + row["id"][:8] for row in self.versions])
        current = store.active_profile()
        data = current["profile"] if current else {**{key: "" for key in PROFILE_FIELDS}, "facts": []}
        self.selected_version = current["id"] if current else None
        if current:
            self.version_choice.current(next(i for i, row in enumerate(self.versions) if row["id"] == current["id"]))
        self.set_data(data)
        reserve_footer(body)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def set_data(self, data):
        self.data = copy.deepcopy(data)
        self.imported_draft = False
        self.original = copy.deepcopy(data)
        for key, field in self.fields.items():
            field.delete(0, "end")
            field.insert(0, data[key])
        self.summary.delete("1.0", "end")
        self.summary.insert("1.0", data["summary"])
        self.clear_fact()
        self.refresh_facts()

    def content(self):
        return {**{key: field.get() for key, field in self.fields.items()},
                "summary": self.summary.get("1.0", "end-1c"), "facts": copy.deepcopy(self.data["facts"])}

    def import_profile(self):
        if self.dirty() and not messagebox.askyesno("Replace profile draft?", "Discard these unsaved profile edits before importing?", parent=self):
            return
        path = filedialog.askopenfilename(parent=self, filetypes=[("Career profile JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "rb") as handle:
                data, _digest = profile_snapshot(handle.read(1024 * 1024 + 1))
            for fact in data["facts"]:
                fact["reviewed"] = False
            self.set_data(data)
            self.imported_draft = True
            self.selected_version = None
            self.version_choice.set("Imported draft — not saved")
            self.status.set("Profile imported into this draft. All facts need your review; Save creates a new version.")
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))

    def export_profile(self):
        if self.selected_version is None or self.dirty():
            self.status.set("Save or discard profile edits before exporting a saved version.")
            return
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Career profile JSON", "*.json")])
        if path:
            try:
                publish_bytes(path, self.store.load_profile(self.selected_version)["snapshot"])
                self.status.set("Saved profile exported, including private sources. Keep the unencrypted file private.")
            except (OSError, ValueError, sqlite3.Error) as exc:
                self.status.set(str(exc))

    def pending_fact(self):
        return bool(self.claim.get("1.0", "end-1c").strip() or self.source.get().strip())

    def dirty(self):
        return self.content() != self.original or self.pending_fact() or self.imported_draft

    def clear_fact(self):
        self.fact_id = None
        self.claim.delete("1.0", "end")
        self.source.delete(0, "end")
        self.reviewed.set(False)
        self.section.set("Additional")

    def refresh_facts(self):
        self.facts.delete(0, "end")
        query = self.fact_query.get().strip().casefold()
        self.visible_fact_indices = [i for i, fact in enumerate(self.data["facts"]) if query in
                                     (fact["claim"] + " " + fact["source"] + " " + fact["section"]).casefold()]
        for i in self.visible_fact_indices:
            fact = self.data["facts"][i]
            self.facts.insert("end", f"[{fact['section']}] {'reviewed' if fact['reviewed'] else 'unreviewed'} - {fact['claim']}")

    def load_fact(self):
        if not self.facts.curselection():
            self.status.set("Select a career fact first.")
            return
        if self.pending_fact():
            self.status.set("Apply or clear pending fact fields first.")
            return
        fact = self.data["facts"][self.visible_fact_indices[self.facts.curselection()[0]]]
        self.fact_id = fact["id"]
        self.claim.insert("1.0", fact["claim"])
        self.source.insert(0, fact["source"])
        self.section.set(fact["section"])
        self.reviewed.set(False)
        self.status.set("Review was reset. Correct the claim, choose its section and review it before Update.")

    def apply_fact(self, identifier):
        fact = {"id": identifier, "claim": self.claim.get("1.0", "end-1c"), "source": self.source.get(),
                "section": self.section.get(), "reviewed": self.reviewed.get()}
        data = self.content()
        data["name"] = data["name"] or "Draft"
        validate_profile({**data, "facts": [fact]})
        return fact

    def add_fact(self):
        try:
            fact = self.apply_fact(str(uuid4()))
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.data["facts"].append(fact)
        self.clear_fact()
        self.refresh_facts()
        self.status.set("Fact added to draft. Save the profile version to reuse it.")

    def update_fact(self):
        if self.fact_id is None:
            self.status.set("Load a fact before updating it.")
            return
        try:
            fact = self.apply_fact(self.fact_id)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.data["facts"] = [fact if old["id"] == self.fact_id else old for old in self.data["facts"]]
        self.clear_fact()
        self.refresh_facts()
        self.status.set("Correction is in this draft. Existing job and resume copies remain unchanged.")

    def remove_fact(self):
        if self.pending_fact() or not self.facts.curselection():
            self.status.set("Clear pending fields and select a fact before removing it.")
            return
        if not messagebox.askyesno("Remove fact from draft?", "Earlier saved profile versions and copied job facts will remain intact.", parent=self):
            return
        del self.data["facts"][self.visible_fact_indices[self.facts.curselection()[0]]]
        self.refresh_facts()

    def copy_job_facts(self):
        if not self.job:
            self.status.set("Select a saved job in the workspace before opening the career profile.")
            return
        existing = {fact["source"] for fact in self.data["facts"]}
        count = 0
        for requirement in self.job["review"]["requirements"]:
            for fact in requirement["evidence"]:
                source = f"{fact['source']}\nSaved job {self.job['id']}, fact {fact['id']}"
                if source not in existing:
                    self.data["facts"].append({"id": str(uuid4()), "claim": fact["claim"], "source": source,
                                               "reviewed": False, "section": "Additional"})
                    existing.add(source)
                    count += 1
        self.refresh_facts()
        self.status.set(f"Copied {count} linked claims as unreviewed Additional facts. Review and classify each yourself.")

    def load_version(self, _event=None):
        if self.dirty() and not messagebox.askyesno("Discard profile draft?", "Load another saved profile and discard these edits?", parent=self):
            if self.selected_version:
                self.version_choice.current(next(i for i, row in enumerate(self.versions) if row["id"] == self.selected_version))
            else:
                self.version_choice.set("")
            return
        try:
            identifier = self.versions[self.version_choice.current()]["id"]
            self.set_data(self.store.load_profile(identifier)["profile"])
            self.selected_version = identifier
            self.status.set("Historical version loaded. Make it active explicitly, or edit and save a new version.")
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))

    def activate(self):
        if self.dirty() or self.selected_version is None:
            self.status.set("Save or discard edits before choosing an existing active version.")
            return
        try:
            self.store.activate_profile(self.selected_version)
            self.on_save()
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.status.set("Selected profile version is now active for future job copies and resumes.")

    def save(self):
        if self.pending_fact():
            self.status.set("Add/Update the pending fact, or Clear fact fields, before saving.")
            return
        data = self.content()
        if data == self.original and self.selected_version is not None:
            self.status.set("No profile changes. Use Make selected version active instead.")
            return
        try:
            self.store.save_profile(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        except (OSError, ValueError, sqlite3.Error) as exc:
            self.status.set(str(exc))
            return
        self.on_save()
        self.destroy()

    def close(self):
        if self.dirty() and not messagebox.askyesno("Discard profile edits?", "These profile edits have not been saved. Discard them?", parent=self):
            return
        self.destroy()


class CareerFactPicker(tk.Toplevel):
    def __init__(self, parent, profile, on_copy):
        super().__init__(parent)
        self.parent_editor = parent
        self.profile, self.on_copy = profile, on_copy
        self.title("RoleWeave - Choose reviewed career facts")
        self.geometry("800x440")
        self.transient(parent)
        self.grab_set()
        ttk.Label(self, text=f"{profile['profile']['name']} - frozen profile {profile['id'][:8]}", padding=12).pack(anchor="w")
        ttk.Label(self, text="Choose relevant facts. Copying does not link them to a job requirement.", wraplength=740).pack(anchor="w", padx=12)
        self.choices = [fact for fact in profile["profile"]["facts"] if fact["reviewed"]]
        self.list = tk.Listbox(self, selectmode="extended", exportselection=False, height=10)
        self.list.pack(fill="both", expand=True, padx=12, pady=12)
        for fact in self.choices:
            self.list.insert("end", f"{fact['section']} - {fact['claim']}")
        self.status = tk.StringVar(value="Only reviewed facts are available. Sources and profile version are preserved.")
        ttk.Label(self, textvariable=self.status, wraplength=740).pack(anchor="w", padx=12)
        ttk.Button(self, text="Copy selected facts into this review", command=self.copy).pack(anchor="w", padx=12, pady=12)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self):
        self.destroy()
        if self.parent_editor.winfo_exists():
            self.parent_editor.grab_set()

    def copy(self):
        identifiers = [self.choices[index]["id"] for index in self.list.curselection()]
        if not identifiers:
            self.status.set("Select at least one reviewed fact.")
            return
        try:
            self.on_copy(imported_career_facts(self.profile, identifiers))
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.close()
