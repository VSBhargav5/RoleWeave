"""Human-selected evidence, validated with the existing exact-quote contract."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
from uuid import uuid4

from roleweave import review, text, revise_fact, remove_fact
from profile_editor import CareerFactPicker
from ai_requirements import adopt_quotes
from ai_window import AIRequirementsWindow


class EvidenceEditor(tk.Toplevel):
    def __init__(self, parent, data, on_save, career_profile=None):
        super().__init__(parent)
        self.data = copy.deepcopy(data)
        self.original_data = copy.deepcopy(data)
        self.on_save = on_save
        self.career_profile = career_profile
        self.editing_fact_id = None
        self.title("RoleWeave · Review requirements and evidence")
        self.geometry("1000x760")
        self.minsize(800, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text="Link exact posting quotes to claims you have reviewed.",
                  font=("Segoe UI", 14)).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(body, text="Links are your assertions; this does not verify qualification or eligibility.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.posting = tk.Text(body, height=7, wrap="word")
        self.posting.insert("1.0", data["posting"])
        self.posting.configure(state="disabled")
        self.posting.grid(row=2, column=0, columnspan=2, sticky="nsew")
        body.rowconfigure(2, weight=1)
        requirements = ttk.LabelFrame(body, text="1. Posting requirements", padding=10)
        requirements.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=12)
        facts = ttk.LabelFrame(body, text="2. Career / project facts", padding=10)
        facts.grid(row=3, column=1, sticky="nsew", pady=12)
        self.requirements = tk.Listbox(requirements, height=6, exportselection=False)
        self.requirements.pack(fill="both", expand=True)
        self.requirements.bind("<<ListboxSelect>>", self.load_requirement)
        ttk.Label(requirements, text="Exact quote (or select text in the posting above)").pack(anchor="w")
        self.quote = tk.Text(requirements, height=3, wrap="word")
        self.quote.pack(fill="x", pady=4)
        ttk.Button(requirements, text="Use selected posting text", command=self.use_selected_quote).pack(anchor="w")
        actions = ttk.Frame(requirements)
        actions.pack(fill="x", pady=8)
        ttk.Button(actions, text="Add requirement", command=self.add_requirement).pack(side="left")
        ttk.Button(actions, text="Update selected", command=self.update_requirement).pack(side="left", padx=6)
        ttk.Button(requirements, text="Remove selected requirement", command=self.remove_requirement).pack(anchor="w")
        ttk.Button(requirements, text="AI: propose exact requirement quotes…", command=self.open_ai).pack(anchor="w", pady=4)
        ttk.Label(facts, text="Select facts to link to the requirement (Ctrl-click for multiple).",
                  wraplength=420).pack(anchor="w")
        self.facts = tk.Listbox(facts, height=6, selectmode="multiple", exportselection=False)
        self.facts.pack(fill="both", expand=True)
        fact_actions = ttk.Frame(facts)
        fact_actions.pack(fill="x", pady=4)
        ttk.Button(fact_actions, text="Load one fact", command=self.load_fact).pack(side="left")
        ttk.Button(fact_actions, text="Update loaded fact", command=self.update_fact).pack(side="left", padx=6)
        ttk.Button(fact_actions, text="Remove one fact", command=self.delete_fact).pack(side="left")
        ttk.Label(facts, text="Claim · state project versus employment accurately").pack(anchor="w")
        self.claim = tk.Text(facts, height=3, wrap="word")
        self.claim.pack(fill="x", pady=4)
        ttk.Label(facts, text="Source / provenance").pack(anchor="w")
        self.source = ttk.Entry(facts)
        self.source.pack(fill="x")
        self.reviewed = tk.BooleanVar(value=False)
        ttk.Checkbutton(facts, text="I reviewed this claim and its source", variable=self.reviewed).pack(anchor="w", pady=4)
        ttk.Button(facts, text="Add fact", command=self.add_fact).pack(anchor="w")
        ttk.Button(facts, text="Clear fact fields", command=self.clear_fact_form).pack(anchor="w", pady=4)
        ttk.Button(facts, text="Copy reviewed career facts…", command=self.open_career_facts,
                   state="normal" if career_profile else "disabled").pack(anchor="w", pady=4)
        self.status = tk.StringVar(value="Select an existing requirement to edit its quote or fact links. Unlinked means needs review.")
        ttk.Label(body, textvariable=self.status, wraplength=930).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Button(body, text="Save reviewed snapshot", command=self.save).grid(row=5, column=0, sticky="w", pady=12)
        ttk.Button(body, text="Cancel · discard changes", command=self.destroy).grid(row=5, column=1, sticky="e")
        self.refresh()
        self.protocol("WM_DELETE_WINDOW", self.request_close)

    def request_close(self):
        quote = self.quote.get("1.0", "end-1c")
        refs = [self.data["facts"][i]["id"] for i in self.facts.curselection()]
        pending_quote = quote.strip() and not any(item["quote"] == quote and item["fact_ids"] == refs
                                                 for item in self.data["requirements"])
        pending = (self.data != self.original_data or self.claim.get("1.0", "end-1c").strip()
                   or self.source.get().strip() or pending_quote)
        if pending and not messagebox.askyesno("Discard evidence draft?",
                                              "Evidence changes have not been saved. Discard them?", parent=self):
            return
        self.destroy()

    def refresh(self):
        self.requirements.delete(0, "end")
        for item in self.data["requirements"]:
            state = "linked" if item["fact_ids"] else "needs review"
            self.requirements.insert("end", f"[{state}] {item['quote']}")
        self.facts.delete(0, "end")
        for fact in self.data["facts"]:
            state = "reviewed" if fact["reviewed"] else "unreviewed"
            self.facts.insert("end", f"[{state}] {fact['claim']} | {fact['source']}")

    def open_career_facts(self):
        if self.career_profile:
            return CareerFactPicker(self, self.career_profile, self.copy_career_facts)

    def open_ai(self):
        return AIRequirementsWindow(self, self.data["posting"], self.accept_ai_quotes)

    def accept_ai_quotes(self, quotes, source_hash):
        self.data = adopt_quotes(self.data, quotes, source_hash)
        self.refresh()
        self.status.set("Reviewed AI quotes added to this unsaved draft without fact links. Save reviewed snapshot to persist.")

    def copy_career_facts(self, facts):
        existing = {fact["id"]: fact for fact in self.data["facts"]}
        for fact in facts:
            if fact["id"] in existing and existing[fact["id"]] != fact:
                raise ValueError("A different fact already uses this copied ID; no facts were changed")
        additions = [fact for fact in facts if fact["id"] not in existing]
        review({**self.data, "facts": additions, "requirements": []})
        self.data["facts"].extend(additions)
        self.refresh()
        self.status.set(f"Copied {len(additions)} frozen career facts. Select and link them to exact requirements before saving.")

    def use_selected_quote(self):
        try:
            value = self.posting.get("sel.first", "sel.last")
        except tk.TclError:
            self.status.set("Select the exact requirement in the posting first.")
            return
        self.quote.delete("1.0", "end")
        self.quote.insert("1.0", value)

    def add_fact(self):
        try:
            fact = {"id": f"fact-{uuid4()}",
                    "claim": text(self.claim.get("1.0", "end-1c"), "Claim"),
                    "source": text(self.source.get(), "Source"), "reviewed": self.reviewed.get()}
            review({**self.data, "facts": [fact], "requirements": []})
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.data["facts"].append(fact)
        self.refresh()
        self.clear_fact_form()
        self.status.set("Fact added to this draft. Select it, then Add or Update a requirement to link it. Save to persist.")

    def clear_fact_form(self):
        self.claim.delete("1.0", "end")
        self.source.delete(0, "end")
        self.reviewed.set(False)
        self.editing_fact_id = None

    def load_fact(self):
        if len(self.facts.curselection()) != 1:
            self.status.set("Select exactly one fact to load.")
            return
        if self.claim.get("1.0", "end-1c").strip() or self.source.get().strip():
            self.status.set("Apply or clear the pending fact fields before loading another fact.")
            return
        fact = self.data["facts"][self.facts.curselection()[0]]
        self.editing_fact_id = fact["id"]
        self.claim.insert("1.0", fact["claim"])
        self.source.insert(0, fact["source"])
        self.reviewed.set(False)
        self.status.set("Fact loaded with review unchecked. Changes unlink it from requirements; review and relink deliberately.")

    def update_fact(self):
        if self.editing_fact_id is None:
            self.status.set("Load one fact before updating it.")
            return
        try:
            draft, removed = revise_fact(self.data, self.editing_fact_id,
                                          self.claim.get("1.0", "end-1c"), self.source.get(), self.reviewed.get())
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.data = draft
        self.clear_fact_form()
        self.refresh()
        self.status.set(f"Fact updated in draft; removed {removed} requirement link(s). Review and relink as needed, then save.")

    def delete_fact(self):
        if self.claim.get("1.0", "end-1c").strip() or self.source.get().strip():
            self.status.set("Apply or clear pending fact fields before removing a fact.")
            return
        if len(self.facts.curselection()) != 1:
            self.status.set("Select exactly one fact to remove.")
            return
        try:
            self.data = remove_fact(self.data, self.data["facts"][self.facts.curselection()[0]]["id"])
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.clear_fact_form()
        self.refresh()
        self.status.set("Unlinked fact removed from draft. Save to persist; original snapshots stay intact.")

    def load_requirement(self, _event=None):
        if not self.requirements.curselection():
            return
        item = self.data["requirements"][self.requirements.curselection()[0]]
        self.quote.delete("1.0", "end")
        self.quote.insert("1.0", item["quote"])
        self.facts.selection_clear(0, "end")
        for index, fact in enumerate(self.data["facts"]):
            if fact["id"] in item["fact_ids"]:
                self.facts.selection_set(index)

    def change_requirement(self, index=None):
        item = {"id": self.data["requirements"][index]["id"] if index is not None else f"requirement-{uuid4()}",
                "quote": self.quote.get("1.0", "end-1c"),
                "fact_ids": [self.data["facts"][i]["id"] for i in self.facts.curselection()]}
        try:
            review({**self.data, "requirements": [item]})
        except ValueError as exc:
            self.status.set(str(exc))
            return
        if index is None:
            self.data["requirements"].append(item)
        else:
            self.data["requirements"][index] = item
        selected = len(self.data["requirements"]) - 1 if index is None else index
        self.refresh()
        self.requirements.selection_set(selected)
        self.load_requirement()
        self.status.set("Requirement updated in this draft. Save reviewed snapshot to persist changes.")

    def add_requirement(self):
        self.change_requirement()

    def update_requirement(self):
        if self.requirements.curselection():
            self.change_requirement(self.requirements.curselection()[0])
        else:
            self.status.set("Select a requirement to update first.")

    def remove_requirement(self):
        if self.requirements.curselection():
            del self.data["requirements"][self.requirements.curselection()[0]]
            self.refresh()
            self.quote.delete("1.0", "end")
            self.status.set("Requirement removed from draft. Save to persist; original snapshot is preserved.")

    def save(self):
        try:
            if self.claim.get("1.0", "end-1c").strip() or self.source.get().strip():
                raise ValueError("Add the pending fact or clear its fields before saving.")
            quote = self.quote.get("1.0", "end-1c")
            refs = [self.data["facts"][i]["id"] for i in self.facts.curselection()]
            if quote.strip() and not any(item["quote"] == quote and item["fact_ids"] == refs
                                         for item in self.data["requirements"]):
                raise ValueError("Add or Update the pending requirement before saving, or clear its quote.")
            review(self.data)
            self.on_save(self.data)
        except (ValueError, OSError) as exc:
            self.status.set(str(exc))
            return
        self.destroy()
