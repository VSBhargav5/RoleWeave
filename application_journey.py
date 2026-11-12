"""One visible path from a saved job to documents, manual application and tracking."""
import tkinter as tk
from tkinter import ttk

from applications import current_application
from desktop_theme import polish_widgets, reserve_footer
from source_links import source_link


class ApplicationJourney(tk.Toplevel):
    def __init__(self, shelf):
        self.shelf, self.job_id = shelf, shelf.current_id
        job = shelf.store.load(self.job_id)
        profile = shelf.store.active_profile()
        resumes = shelf.store.list_resumes(self.job_id)
        state = current_application(shelf.store.application_history(self.job_id))
        try:
            source_link(job["source_url"])
            source_available = True
        except ValueError:
            source_available = False
        super().__init__(shelf.winfo_toplevel())
        self.title("RoleWeave - Apply workspace")
        self.geometry("960x760")
        self.minsize(850, 650)
        self.transient(shelf.winfo_toplevel())
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Your application, step by step", style="ReviewTitle.TLabel").pack(anchor="w")
        ttk.Label(body, text=job["title"] + " · " + job["company"], wraplength=790).pack(anchor="w", pady=(4, 6))
        ttk.Label(body, text="Upload your reviewed documents and submit on the employer's website yourself. Opening a page or exporting files does not submit an application.", style="Muted.TLabel", wraplength=790).pack(anchor="w")
        self.stage = tk.StringVar(value="Your recorded stage: " + state["stage"].title() + " · Follow-up: " + (state["follow_up"] or "not set"))
        ttk.Label(body, textvariable=self.stage, style="Eyebrow.TLabel").pack(anchor="w", pady=10)
        self.routes = {"profile": shelf.open_profile, "evidence": shelf.edit_evidence,
                       "resume": shelf.open_resume, "letter": shelf.open_letter,
                       "files": shelf.open_dossier, "source": shelf.open_source,
                       "track": shelf.open_tracker}
        steps = (
            ("profile", "1. Your career profile", "Review your identity and sourced career claims." if profile else "Start here: create and activate your reviewed profile.", "Review profile", True),
            ("evidence", "2. Review this job", "Read its requirements and link relevant evidence; gaps remain visible.", "Review evidence", True),
            ("resume", "3. Prepare your resume", f"{len(resumes)} saved resume version(s) for this exact job. Preview, approve, save and export." if profile else "Create an active profile first. You choose which reviewed claims to include.", "Build / export resume", profile is not None),
            ("letter", "4. Optional cover letter", "Write and review a letter using your sourced claims; skip if unnecessary.", "Prepare letter", profile is not None),
            ("files", "5. Optional document bundle", "Save an upload-ready folder of selected resume/letter files. No ZIP extraction; private dossiers stay private." if resumes else "Save a resume for this exact job first; general resumes are not substituted.", "Prepare files", bool(resumes)),
            ("source", "6. Apply on the job site", "Open the saved HTTPS posting and follow the employer's application process." if source_available else "Add a valid HTTPS source URL in Job details, then save the posting; or apply independently.", "Open saved job page", source_available),
            ("track", "7. Record what happened", "After you submit, record the date/channel/reference and a follow-up in tracking. A private dossier is optional.", "Record / follow up", True),
        )
        self.buttons = {}
        for key, title, hint, action, enabled in steps:
            row = ttk.Frame(body)
            row.pack(fill="x", pady=6)
            copy = ttk.Frame(row)
            copy.pack(side="left", fill="x", expand=True)
            ttk.Label(copy, text=title, font=("Segoe UI", 11, "bold")).pack(anchor="w")
            ttk.Label(copy, text=hint, style="Muted.TLabel", wraplength=555, justify="left").pack(anchor="w")
            button = ttk.Button(row, text=action, width=22, command=lambda key=key: self.launch(key), state="normal" if enabled else "disabled")
            button.pack(side="right", padx=(14, 0))
            self.buttons[key] = button
            row.bind("<Configure>", lambda event, label=copy.winfo_children()[1]: label.configure(wraplength=max(260, event.width - 240)))
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=(10, 0))
        self.status = tk.StringVar(value="Return here after each step to see the saved state. Private submission receipts remain optional under Review files.")
        ttk.Label(footer, textvariable=self.status, wraplength=630, style="Muted.TLabel").pack(side="left")
        ttk.Button(footer, text="Close", command=self.destroy).pack(side="right")
        reserve_footer(body)
        polish_widgets(self)

    def launch(self, key):
        if self.shelf.current_id != self.job_id or self.shelf.has_draft_changes():
            self.status.set("The selected job or draft changed. Close this workspace, save/discard edits and reopen for the intended job.")
            return
        if key not in self.routes or self.buttons[key].instate(["disabled"]):
            return
        action = self.routes[key]
        self.destroy()
        return action()
