"""Choose recipient documents and save a new upload-ready folder."""
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4
from io import BytesIO
import zipfile

from desktop_theme import polish_widgets
from recipient_bundle import export_upload_folder


class UploadWindow(tk.Toplevel):
    def __init__(self, parent, dossier):
        super().__init__(parent)
        self.dossier, self.last_folder = dossier, None
        self.title("RoleWeave - Upload-ready documents")
        self.geometry("700x430")
        self.minsize(650, 400)
        self.transient(parent)
        self.grab_set()
        body = ttk.Frame(self, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Choose files for the employer", style="Section.TLabel").pack(anchor="w")
        ttk.Label(body, text="Save actual documents in a new folder—no ZIP extraction. Private evidence and history are excluded. Nothing is uploaded or submitted.", wraplength=600).pack(anchor="w", pady=12)
        with zipfile.ZipFile(BytesIO(dossier)) as archive:
            available = set(archive.namelist())
        self.formats = {}
        for key, name in (("pdf", "resume.pdf"), ("txt", "resume.txt"), ("html", "resume.html"), ("letter", "cover-letter.txt")):
            flag = tk.BooleanVar(value=(key == "pdf" and name in available) or (key == "txt" and "resume.pdf" not in available))
            ttk.Checkbutton(body, text=name, variable=flag, state="normal" if name in available else "disabled").pack(anchor="w", pady=3)
            self.formats[key] = flag
        self.status = tk.StringVar(value="PDF is usually the useful portal attachment. Select the formats your employer requests.")
        ttk.Label(body, textvariable=self.status, wraplength=600).pack(fill="x", pady=12)
        actions = ttk.Frame(body)
        actions.pack(fill="x", side="bottom")
        ttk.Button(actions, text="Save upload folder", style="Primary.TButton", command=self.export).pack(side="left")
        self.open_button = ttk.Button(actions, text="Open saved folder", command=self.open_folder, state="disabled")
        self.open_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Close", command=self.destroy).pack(side="right")
        polish_widgets(self)

    def export(self):
        formats = [key for key, flag in self.formats.items() if flag.get()]
        if not formats:
            self.status.set("Select at least one employer document.")
            return
        if not messagebox.askyesno("Review employer-facing documents", "Save only: " + ", ".join("cover-letter.txt" if key == "letter" else "resume." + key for key in formats) + "\nPrivate source records and history are excluded. Proofread before you upload.", parent=self):
            return
        parent = filedialog.askdirectory(parent=self, title="Choose where to create the upload folder", mustexist=True)
        if not parent:
            return
        self.last_folder = None
        self.open_button.configure(state="disabled")
        destination = Path(parent) / ("RoleWeave-upload-" + uuid4().hex[:12])
        try:
            export_upload_folder(self.dossier, destination, formats, confirmed=True)
        except (OSError, ValueError) as exc:
            self.status.set(f"Export did not complete: {exc}. Do not use a partial folder; retry into a new folder.")
            return
        self.last_folder = destination
        self.open_button.configure(state="normal")
        self.status.set(f"Saved documents to {destination}. Upload only resume/letter files; EXPORT-INFO.txt is for your local reference.")

    def open_folder(self):
        if self.last_folder is None:
            return
        try:
            if not (self.last_folder / "EXPORT-INFO.txt").is_file():
                raise ValueError("The completed folder is missing. Export again to a new folder.")
            os.startfile(self.last_folder)
        except (OSError, ValueError) as exc:
            self.status.set(str(exc))
