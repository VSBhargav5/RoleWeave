"""Local evidence rehearsal; no generated claims, scoring or learning assertions."""
import tkinter as tk
from tkinter import ttk
from desktop_theme import polish_widgets, reserve_footer
from roleweave import review_snapshot


def practice_cards(item):
    result = review_snapshot(item["snapshot"])
    if result["input_sha256"] != item["input_sha256"]:
        raise ValueError("Practice source fingerprint mismatch")
    return [{"quote": row["quote"],
             "prompt": "Explain a relevant example for this exact requirement. Distinguish project practice from employment.",
             "evidence": "\n\n".join(f"{fact['claim']}\nSource: {fact['source']}" for fact in row["evidence"]) or
                         "No evidence linked. Review this open question; do not invent an example."}
            for row in result["requirements"]]


class InterviewPractice(tk.Toplevel):
    def __init__(self, parent, item):
        super().__init__(parent)
        self.cards, self.position = practice_cards(item), 0
        self.title("RoleWeave - Evidence rehearsal")
        self.geometry("850x600")
        self.transient(parent)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Practise the evidence you can explain", style="Section.TLabel").pack(anchor="w")
        ttk.Label(body, text=f"Frozen review {item['id'][:8]}. Local rehearsal only; no answer grading or completion claim.", wraplength=780).pack(anchor="w", pady=8)
        self.counter = tk.StringVar()
        ttk.Label(body, textvariable=self.counter, style="Eyebrow.TLabel").pack(anchor="w")
        self.output = tk.Text(body, wrap="word", height=14, state="disabled")
        self.output.pack(fill="both", expand=True, pady=12)
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        ttk.Button(actions, text="Previous", command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(actions, text="Reveal linked evidence", style="Primary.TButton", command=lambda: self.render(True)).pack(side="left", padx=8)
        ttk.Button(actions, text="Next", command=lambda: self.move(1)).pack(side="left")
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")
        reserve_footer(body)
        polish_widgets(self)
        self.render()

    def move(self, delta):
        if self.cards:
            self.position = (self.position + delta) % len(self.cards)
        self.render()

    def render(self, reveal=False):
        self.counter.set(f"Card {self.position + 1} of {len(self.cards)}" if self.cards else "No requirement cards yet")
        if self.cards:
            card = self.cards[self.position]
            content = card["quote"] + "\n\n" + card["prompt"] + "\n\n" + (card["evidence"] if reveal else "Think through your example, then reveal the linked evidence.")
        else:
            content = "Add exact requirement quotes in Review evidence before practising."
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", content)
        self.output.configure(state="disabled")
