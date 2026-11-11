"""Owned drawing assets and bounded rich evidence presentation for the native UI."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk


def install_surfaces(style, root):
    """Nine-slice images retain ordinary ttk controls and keyboard semantics."""
    if hasattr(root, "_rw_surfaces"):
        return
    images = []
    def image(fill, outside, radius=10, border=None, size=32):
        scale = 3
        bitmap = Image.new("RGBA", (size * scale, size * scale), outside)
        draw = ImageDraw.Draw(bitmap)
        draw.rounded_rectangle((scale, scale, (size - 1) * scale, (size - 1) * scale), radius=radius * scale,
                               fill=fill, outline=border or fill, width=scale)
        picture = ImageTk.PhotoImage(bitmap.resize((size, size), Image.Resampling.LANCZOS), master=root)
        images.append(picture)
        return picture
    for name, fill, outside in (("Panel", "#121724", "#090c14"), ("Hero", "#21152f", "#090c14"),
                                 ("Violet", "#21172f", "#090c14"), ("Amber", "#2c2319", "#090c14"),
                                 ("Mint", "#102d2a", "#090c14"), ("EvidenceCard", "#121724", "#0d121d")):
        element = "RW." + name + ".surface"
        style.element_create(element, "image", image(fill, outside, 16, size=48), border=18, padding=0, sticky="nswe")
        style.layout(name + ".TFrame", [(element, {"sticky": "nswe"})])
        style.configure(name + ".TFrame", background=fill, borderwidth=0)
    for name, fill, hover, text, outside in (("TButton", "#222b3d", "#303b52", "#e1e7f7", "#121724"),
                                            ("Primary.TButton", "#7c3aed", "#8350df", "#ffffff", "#121724"),
                                            ("Hero.TButton", "#5eead4", "#99f6e4", "#082d29", "#21152f"),
                                            ("Rail.TButton", "#0c101b", "#1b2438", "#e1e7f7", "#0c101b"),
                                            ("ActiveRail.TButton", "#6d3fc4", "#8758e8", "#ffffff", "#0c101b")):
        element = "RW." + name + ".button"
        normal, active = image(fill, outside), image(hover, outside)
        pressed, disabled = image(hover, outside, border="#bba8ed"), image("#252c3a", outside)
        focused = image(fill, outside, border="#bba8ed")
        style.element_create(element, "image", normal, ("disabled", disabled), ("pressed", pressed), ("active", active), ("focus", focused), border=11, padding=0, sticky="nswe")
        style.layout(name, [(element, {"sticky": "nswe", "children": [("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        style.configure(name, foreground=text, background=fill, borderwidth=0, padding=(14, 7))
        style.map(name, foreground=[("disabled", "#7f8aa0"), ("!disabled", text)], background=[])
    element = "RW.tab.surface"
    style.element_create(element, "image", image("#1d2638", "#121724"), ("selected", image("#7547cf", "#121724")), border=11, padding=0, sticky="nswe")
    style.layout("TNotebook.Tab", [(element, {"sticky": "nswe", "children": [("Notebook.padding", {"sticky": "nswe", "children": [("Notebook.label", {"sticky": "nswe"})]})]})])
    style.map("TNotebook.Tab", foreground=[("selected", "#ffffff"), ("!selected", "#a7b1c9")], background=[])
    checks = []
    for selected in (False, True):
        bitmap = Image.new("RGBA", (48, 48), "#121724")
        draw = ImageDraw.Draw(bitmap)
        draw.rounded_rectangle((3, 3, 44, 44), radius=10, fill="#8b5cf6" if selected else "#101726", outline="#b89cff" if selected else "#64708c", width=3)
        if selected:
            draw.line((11, 24, 20, 33, 37, 13), fill="white", width=6)
        picture = ImageTk.PhotoImage(bitmap.resize((16, 16), Image.Resampling.LANCZOS), master=root)
        checks.append(picture); images.append(picture)
    style.element_create("RW.Check.indicator", "image", checks[0], ("selected", checks[1]), sticky="")
    style.layout("TCheckbutton", [("Checkbutton.padding", {"sticky": "nswe", "children": [("RW.Check.indicator", {"side": "left", "sticky": ""}), ("Checkbutton.focus", {"side": "left", "sticky": "w", "children": [("Checkbutton.label", {"sticky": "nswe"})]})]})])
    root._rw_surfaces = images


class WeaveArt(tk.Canvas):
    """Decorative brand geometry, deliberately unrelated to user metrics."""
    def __init__(self, parent):
        super().__init__(parent, width=140, height=65, background="#21152f", highlightthickness=0, takefocus=False)
        # A radial color gradient is decorative branding, not a metric/chart.
        glow = Image.new("RGB", (140, 65), "#21152f")
        pixels = glow.load()
        for y in range(65):
            for x in range(140):
                purple = max(0, 1 - ((x - 62) ** 2 + (y - 32) ** 2) ** .5 / 65) ** 2
                cyan = max(0, 1 - ((x - 112) ** 2 + (y - 22) ** 2) ** .5 / 42) ** 2
                pixels[x, y] = (int(33 + 65 * purple), int(21 + 65 * cyan), int(47 + 100 * purple + 40 * cyan))
        self._glow = ImageTk.PhotoImage(glow, master=self)
        self.create_image(0, 0, image=self._glow, anchor="nw")
        for width, color in ((18, "#392653"), (11, "#6840a0"), (5, "#c4a7ff")):
            self.create_line(8, 48, 38, 14, 70, 49, 104, 12, 136, 42, smooth=True, width=width, fill=color)
        for width, color in ((12, "#164c50"), (6, "#1ca89a"), (3, "#76ffe1")):
            self.create_line(8, 18, 38, 51, 70, 15, 104, 51, 136, 16, smooth=True, width=width, fill=color)
        self.create_oval(115, 0, 128, 13, fill="#ffbc89", outline="")



class EvidenceCards(ttk.Frame):
    """Read-only cards with complete copy text and bounded 20-card pages."""
    PAGE_SIZE = 20

    def __init__(self, parent):
        super().__init__(parent)
        self.plain_text, self.requirements, self.page = "", [], 0
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 3))
        info = ttk.Frame(toolbar)
        info.pack(fill="x")
        self.page_label = ttk.Label(info, style="Muted.TLabel")
        self.page_label.pack(side="left")
        self.page_choice = ttk.Combobox(info, state="readonly", width=15)
        self.page_choice.bind("<<ComboboxSelected>>", lambda _event: self.change_page(self.page_choice.current() - self.page))
        ttk.Button(info, text="Copy review text", command=self.copy_text).pack(side="right")
        self.canvas = tk.Canvas(self, background="#0d121d", highlightthickness=0, takefocus=True)
        self.canvas.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.content = ttk.Frame(self.canvas, style="EvidenceCanvas.TFrame")
        self.window_id = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Next>", lambda _e: self.canvas.yview_scroll(1, "pages"))
        self.canvas.bind("<Prior>", lambda _e: self.canvas.yview_scroll(-1, "pages"))
        self.wrap_labels = []

    def render(self, plain_text, requirements=None):
        self.plain_text, self.requirements, self.page = plain_text, list(requirements or []), 0
        self.draw_page()

    def draw_page(self):
        for child in self.content.winfo_children():
            child.destroy()
        self.wrap_labels = []
        start = self.page * self.PAGE_SIZE
        visible = self.requirements[start:start + self.PAGE_SIZE]
        for number, requirement in enumerate(visible, start + 1):
            card = ttk.Frame(self.content, style="EvidenceCard.TFrame", padding=16)
            card.pack(fill="x", padx=4, pady=(4, 10))
            linked = bool(requirement["evidence"])
            label = ttk.Label(card, text=f"{number:02d}   " + ("LINKED EVIDENCE" if linked else "OPEN REVIEW QUESTION"), style="Linked.TLabel" if linked else "Open.TLabel")
            label.pack(anchor="w", pady=(0, 8))
            quote = ttk.Label(card, text=requirement["quote"], style="Quote.TLabel", justify="left", wraplength=400)
            quote.pack(anchor="w", fill="x", pady=(0, 8)); self.wrap_labels.append(quote)
            for fact in requirement["evidence"]:
                claim = ttk.Label(card, text=fact["claim"], justify="left", wraplength=400)
                claim.pack(anchor="w", fill="x", pady=(0, 5)); self.wrap_labels.append(claim)
                source = ttk.Label(card, text="Source: " + fact["source"], style="Muted.TLabel", justify="left", wraplength=400)
                source.pack(anchor="w", fill="x", pady=(0, 8)); self.wrap_labels.append(source)
            if not linked:
                note = ttk.Label(card, text="No evidence is linked yet. Review this requirement without inventing an example.", style="Muted.TLabel", justify="left", wraplength=400)
                note.pack(anchor="w", fill="x"); self.wrap_labels.append(note)
        if not visible:
            empty = ttk.Label(self.content, text=self.plain_text, style="EmptyEvidence.TLabel", justify="left", wraplength=400, padding=20)
            empty.pack(fill="x", padx=4, pady=4); self.wrap_labels.append(empty)
        self.page_label.configure(text=f"{start + 1}-{start + len(visible)} of {len(self.requirements)} requirements" if visible else "Review workspace")
        self.page_label.pack_forget()
        self.page_choice.pack_forget()
        if len(self.requirements) > self.PAGE_SIZE:
            pages = (len(self.requirements) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
            self.page_choice.configure(values=[f"Page {index + 1} of {pages}" for index in range(pages)])
            self.page_choice.current(self.page)
            self.page_choice.pack(side="left")
        else:
            self.page_label.pack(side="left")
        def bind_wheel(widget):
            widget.bind("<MouseWheel>", self.wheel)
            for child in widget.winfo_children(): bind_wheel(child)
        bind_wheel(self.content)
        self.resize()
        self.canvas.yview_moveto(0)

    def resize(self, _event=None):
        width = max(1, self.canvas.winfo_width())
        self.canvas.itemconfigure(self.window_id, width=width)
        for label in self.wrap_labels:
            label.configure(wraplength=max(120, width - 48))

    def change_page(self, delta):
        pages = max(1, (len(self.requirements) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = max(0, min(pages - 1, self.page + delta))
        self.draw_page()

    def wheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def copy_text(self):
        self.clipboard_clear()
        self.clipboard_append(self.plain_text)
