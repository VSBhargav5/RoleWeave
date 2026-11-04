"""Deliberate session-key AI request, then human selection into an unsaved review."""
import tkinter as tk
from tkinter import ttk, filedialog
from desktop_theme import polish_widgets, reserve_footer

from ai_requirements import ENDPOINT, MODEL, posting_hash, propose_requirements, request_payload
from background_task import BackgroundTask
from safe_export import publish_bytes


class AIRequirementsWindow(tk.Toplevel):
    def __init__(self, parent, posting, on_accept):
        super().__init__(parent)
        self.editor, self.posting, self.on_accept = parent, posting, on_accept
        self.source_hash = posting_hash(posting)
        self.payload = request_payload(posting)
        self.proposals = []
        self.task = BackgroundTask(self)
        self.title("RoleWeave - Review AI requirement request")
        self.geometry("1000x760")
        self.minsize(820, 650)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=16)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="AI proposes quotes. You decide what belongs in the review.", font=("Segoe UI", 14)).pack(anchor="w")
        ttk.Label(body, text=f"Destination: {ENDPOINT}\nModel: {MODEL} · output cap: 2048 tokens · no tools or retries", wraplength=940).pack(anchor="w", pady=8)
        self.tabs = ttk.Notebook(body)
        self.tabs.pack(fill="both", expand=True)
        request = ttk.Frame(self.tabs, padding=8)
        results = ttk.Frame(self.tabs, padding=8)
        self.tabs.add(request, text="Review exact request (posting only)")
        self.tabs.add(results, text="Review proposed quotes")
        self.payload_view = tk.Text(request, height=12, wrap="word")
        self.payload_view.insert("1.0", self.payload.decode("utf-8"))
        self.payload_view.configure(state="disabled")
        self.payload_view.pack(fill="both", expand=True)
        ttk.Label(request, text="Your key is only used in the authorization header. Career facts, identity, notes and resumes are not included.", wraplength=900).pack(anchor="w", pady=6)
        ttk.Label(request, text="Session-only API key (masked; not saved)").pack(anchor="w")
        self.key = tk.StringVar()
        ttk.Entry(request, textvariable=self.key, show="•").pack(fill="x", pady=4)
        ttk.Label(request, text="Charges may apply. store=false is not a zero-retention guarantee. Send only permitted material. Cancellation cannot undo remote processing or charges.", wraplength=900).pack(anchor="w", pady=6)
        self.consent = tk.BooleanVar(value=False)
        ttk.Checkbutton(request, text="I reviewed this exact payload and authorize this one provider request", variable=self.consent).pack(anchor="w")
        controls = ttk.Frame(request)
        controls.pack(fill="x", pady=8)
        self.send_button = ttk.Button(controls, text="Send reviewed request", style="Primary.TButton", command=self.send)
        self.send_button.pack(side="left")
        ttk.Button(controls, text="Cancel request", command=self.cancel).pack(side="left", padx=8)
        ttk.Button(controls, text="Export request JSON", command=self.export_request).pack(side="left")
        ttk.Label(results, text="Select only quotes that actually state requirements. A quote can be exact yet irrelevant or malicious.", wraplength=900).pack(anchor="w")
        self.quotes = tk.Listbox(results, selectmode="extended", exportselection=False, height=8)
        self.quotes.pack(fill="both", expand=True, pady=8)
        self.quote_preview = tk.Text(results, height=5, wrap="word", state="disabled")
        self.quote_preview.pack(fill="both", expand=True)
        self.quotes.bind("<<ListboxSelect>>", self.preview_quotes)
        self.reviewed = tk.BooleanVar(value=False)
        ttk.Checkbutton(results, text="I reviewed the selected quotes as job requirements", variable=self.reviewed).pack(anchor="w", pady=6)
        ttk.Button(results, text="Add selected quotes to unsaved evidence review", command=self.accept).pack(anchor="w")
        self.status = tk.StringVar(value="Nothing is sent until you authorize and press Send. No facts or links are generated.")
        ttk.Label(body, textvariable=self.status, wraplength=940).pack(anchor="w", pady=8)
        ttk.Button(body, text="Close", command=self.close).pack(anchor="e")
        reserve_footer(body)
        reserve_footer(request)
        reserve_footer(results)
        polish_widgets(self)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Destroy>", self.destroyed)

    def send(self):
        if not self.consent.get():
            self.status.set("Review the exact payload and authorize this one request first.")
            return
        if not self.key.get():
            self.status.set("Enter your API key in the masked session field. It is never read from files.")
            return
        if self.task.active is not None:
            self.status.set("Cancel or wait for the current request.")
            return
        self.proposals = []
        self.quotes.delete(0, "end")
        self.reviewed.set(False)
        self.consent.set(False)
        key, payload, posting = self.key.get(), self.payload, self.posting
        self.send_button.configure(state="disabled")
        self.status.set("Sending the reviewed posting to OpenAI. Cancel discards local results; remote charges may still occur.")
        self.task.start(lambda event: propose_requirements(posting, payload, key, True, event), self.received, self.failed)

    def export_request(self):
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".json", filetypes=[("Reviewed request payload", "*.json")])
        if path:
            try:
                publish_bytes(path, self.payload)
                self.status.set("Exact posting-only request exported without authorization header/key. Private local file; nothing sent.")
            except (OSError, ValueError) as exc:
                self.status.set(str(exc))

    def received(self, proposals):
        self.send_button.configure(state="normal")
        self.proposals = proposals
        self.quotes.delete(0, "end")
        for quote in proposals:
            self.quotes.insert("end", quote)
        self.reviewed.set(False)
        self.tabs.select(1)
        self.status.set(f"{len(proposals)} exact quote proposals. Select, inspect and review them before adding. No database changes yet.")

    def failed(self, error):
        self.send_button.configure(state="normal")
        self.status.set(error + ". No automatic retry; authorize again to send another request.")

    def cancel(self):
        self.task.cancel()
        self.consent.set(False)
        self.send_button.configure(state="normal")
        self.status.set("Cancelled locally. A sent request may still be processed or charged remotely.")

    def preview_quotes(self, _event=None):
        self.reviewed.set(False)
        self.quote_preview.configure(state="normal")
        self.quote_preview.delete("1.0", "end")
        self.quote_preview.insert("1.0", "\n\n".join(self.proposals[i] for i in self.quotes.curselection()))
        self.quote_preview.configure(state="disabled")

    def accept(self):
        selected = [self.proposals[i] for i in self.quotes.curselection()]
        if not selected or not self.reviewed.get():
            self.status.set("Select and explicitly review at least one quote. Nothing has been added.")
            return
        try:
            self.on_accept(selected, self.source_hash)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        self.close()

    def destroyed(self, event):
        if event.widget is self:
            self.task.cancel()
            self.key.set("")

    def close(self):
        self.task.cancel()
        self.key.set("")
        self.destroy()
        if self.editor.winfo_exists():
            self.editor.grab_set()
