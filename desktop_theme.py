"""Shared desktop palette and typography; standard Tk/ttk, no theme dependency."""
import tkinter as tk
from tkinter import ttk, font
from visual_components import install_surfaces

CANVAS = "#090c14"
PAPER = "#121724"
INK = "#eef2ff"
MUTED = "#a1acc2"
ACCENT = "#b89cff"
RAIL = "#0c101b"
LINE = "#29334a"
BODY_FAMILY = "Segoe UI"


def apply_theme(window):
    style = ttk.Style(window)
    if "roleweave" not in style.theme_names():
        style.theme_create("roleweave", parent="clam")
    if style.theme_use() != "roleweave":
        style.theme_use("roleweave")
    global BODY_FAMILY
    available = set(font.families(window))
    BODY_FAMILY = next((name for name in ("Segoe UI Variable Text", "Segoe UI", "Arial") if name in available), "TkDefaultFont")
    style.configure(".", font=(BODY_FAMILY, 11), background=PAPER, foreground=INK)
    style.configure("TFrame", background=PAPER)
    style.configure("Panel.TFrame", background=PAPER, borderwidth=1, relief="solid", bordercolor=LINE)
    style.configure("ReviewTitle.TLabel", font=("Segoe UI", 18, "bold"))
    style.configure("Opportunity.Treeview", rowheight=58, font=(BODY_FAMILY, 11), borderwidth=0)
    style.configure("Opportunity.Treeview.Heading", font=("Segoe UI", 8, "bold"), padding=(10, 9))
    for name, background, foreground in (("Violet", "#21172f", "#c4adff"),
                                         ("Amber", "#2c2319", "#f7c268"),
                                         ("Mint", "#102d2a", "#67e8c7")):
        style.configure(name + ".TFrame", background=background)
        style.configure(name + ".TLabel", background=background, foreground=foreground, font=("Segoe UI", 9, "bold"))
        style.configure(name + "Value.TLabel", background=background, foreground=foreground, font=("Segoe UI", 27, "bold"))
        style.configure(name + "Note.TLabel", background=background, foreground=MUTED, font=("Segoe UI", 8))
    style.configure("App.TFrame", background=CANVAS)
    style.configure("Rail.TFrame", background=RAIL)
    style.configure("TLabel", background=PAPER, foreground=INK)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("App.TLabel", background=CANVAS)
    style.configure("AppMuted.TLabel", background=CANVAS, foreground=MUTED)
    style.configure("Title.TLabel", background=CANVAS, font=("Segoe UI", 26, "bold"))
    style.configure("Section.TLabel", font=("Segoe UI", 14, "bold"))
    style.configure("Eyebrow.TLabel", foreground=ACCENT, font=("Segoe UI", 9, "bold"))
    style.configure("Metric.TLabel", font=("Segoe UI", 22, "bold"))
    style.configure("Rail.TLabel", foreground="#e1e7f7", background=RAIL)
    style.configure("Brand.TLabel", foreground=INK, background=RAIL, font=("Segoe UI", 18, "bold"))
    style.configure("RailMuted.TLabel", foreground="#a1acc2", background=RAIL, font=("Segoe UI", 9))
    style.configure("Badge.TLabel", foreground=ACCENT, background="#21172f", padding=(10, 5), font=("Segoe UI", 9, "bold"))
    style.configure("TButton", background=PAPER, foreground=INK, bordercolor=LINE, lightcolor=LINE,
                    darkcolor=LINE, borderwidth=1, relief="solid", padding=(12, 8), focusthickness=2, focuscolor=ACCENT)
    style.map("TButton", background=[("pressed", "#e6e2ff"), ("active", "#f0edff")],
              foreground=[("disabled", "#899ba3")])
    style.configure("TMenubutton", background=PAPER, foreground=INK, padding=(12, 8), bordercolor=LINE, arrowcolor=MUTED)
    style.configure("Primary.TButton", background=ACCENT, foreground=PAPER, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=(BODY_FAMILY, 11, "bold"))
    style.map("Primary.TButton", background=[("disabled", "#e2dff3"), ("pressed", "#4436af"), ("active", "#5142c4")],
              foreground=[("disabled", "#77718f"), ("!disabled", PAPER)])
    style.configure("Rail.TButton", background=RAIL, foreground="#e1e7f7", borderwidth=0,
                    bordercolor=RAIL, lightcolor=RAIL, darkcolor=RAIL, anchor="w", padding=(12, 11))
    style.map("Rail.TButton", background=[("active", "#282b46"), ("pressed", "#343451")], foreground=[("!disabled", PAPER)])
    style.configure("ActiveRail.TButton", background="#3b275b", foreground=PAPER, anchor="w", padding=(12, 11))
    style.map("ActiveRail.TButton", background=[("active", "#343451")], foreground=[("!disabled", PAPER)])
    style.configure("TEntry", fieldbackground="#0d1421", bordercolor=LINE, padding=(9, 7), insertcolor=INK)
    style.map("TEntry", bordercolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground="#0d1421", background="#1b2334", padding=(8, 6), arrowsize=13, arrowcolor=MUTED)
    style.map("TCombobox", fieldbackground=[("readonly", "#0d1421")], foreground=[("readonly", INK)],
              selectbackground=[("readonly", "#0d1421")], selectforeground=[("readonly", INK)], bordercolor=[("focus", ACCENT)])
    style.configure("TCheckbutton", padding=(0, 4), background=PAPER)
    style.configure("Filter.TCombobox", padding=(6, 3), font=("Segoe UI", 9))
    style.configure("Filter.TCheckbutton", padding=0, font=("Segoe UI", 9))
    style.map("TCheckbutton", background=[("active", PAPER)])
    style.configure("TNotebook", background=PAPER, borderwidth=0, bordercolor=PAPER, lightcolor=PAPER, darkcolor=PAPER, tabmargins=(0, 8, 0, 0))
    style.configure("TNotebook.Tab", padding=(15, 9), background="#1d2638", foreground=MUTED, bordercolor=LINE, lightcolor="#1d2638", darkcolor="#1d2638", font=(BODY_FAMILY, 11, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#21172f")], lightcolor=[("selected", "#21172f")], darkcolor=[("selected", "#21172f")], foreground=[("selected", ACCENT)])
    style.configure("TLabelframe", background=PAPER, bordercolor=LINE, relief="solid")
    style.configure("TLabelframe.Label", background=PAPER, foreground=ACCENT, font=(BODY_FAMILY, 11, "bold"))
    style.configure("Treeview", background=PAPER, fieldbackground=PAPER, foreground=INK,
                    rowheight=34, borderwidth=0)
    style.map("Treeview", background=[("selected", "#372650")], foreground=[("selected", "#f1eaff")])
    style.configure("Treeview.Heading", background="#192235", foreground=MUTED, padding=(10, 9), font=("Segoe UI", 9, "bold"))
    style.configure("TScrollbar", background="#3b4963", troughcolor="#090c14", borderwidth=0, bordercolor=PAPER, lightcolor=PAPER, darkcolor=PAPER, arrowcolor=MUTED, gripcount=0, arrowsize=10, width=10)
    style.configure("HeroTitle.TLabel", background="#21152f", foreground="#f7f3ff", font=(BODY_FAMILY, 24, "bold"))
    style.configure("HeroNote.TLabel", background="#21152f", foreground="#b6a4cd", font=(BODY_FAMILY, 10))
    style.configure("HeroEyebrow.TLabel", background="#21152f", foreground="#b89cff", font=(BODY_FAMILY, 8, "bold"))
    style.configure("EvidenceCanvas.TFrame", background="#0d121d")
    style.configure("Quote.TLabel", font=(BODY_FAMILY, 12, "bold"), foreground=INK)
    style.configure("Linked.TLabel", foreground="#5eead4", font=(BODY_FAMILY, 9, "bold"))
    style.configure("Open.TLabel", foreground="#f7c268", font=(BODY_FAMILY, 9, "bold"))
    style.configure("EmptyEvidence.TLabel", background="#0d121d", foreground=MUTED, font=(BODY_FAMILY, 12))
    install_surfaces(style, window._root())
    window.option_add("*Menu.background", "#171e2c")
    window.option_add("*Menu.foreground", INK)
    window.option_add("*Menu.activeBackground", "#6741d9")
    window.option_add("*Menu.activeForeground", "#ffffff")
    window.option_add("*Menu.font", (BODY_FAMILY, 11))
    window.configure(background=CANVAS)
    window.option_add("*TCombobox*Listbox.font", (BODY_FAMILY, 11))
    window.option_add("*TCombobox*Listbox.background", PAPER)
    window.option_add("*TCombobox*Listbox.foreground", INK)
    # ttk queues ThemeChanged at idle. Drain it while this Tk interpreter still
    # owns its event command, including windows closed before mainloop starts.
    window.update_idletasks()


def polish_widgets(window):
    """Style classic Tk text/list widgets that ttk styles cannot reach."""
    for widget in window.winfo_children():
        if isinstance(widget, tk.Text):
            widget.configure(font=(BODY_FAMILY, 11), background="#0d1421", foreground=INK,
                             insertbackground=INK, selectbackground="#3b2a5b", selectforeground="#f1eaff",
                             relief="flat", borderwidth=0, highlightthickness=1,
                             highlightbackground=LINE, highlightcolor=ACCENT, padx=12, pady=10, spacing1=2, spacing3=4)
        elif isinstance(widget, tk.Listbox):
            widget.configure(font=(BODY_FAMILY, 11), background="#0d1421", foreground=INK,
                             selectbackground="#372650", selectforeground="#f1eaff", activestyle="none",
                             relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=LINE,
                             highlightcolor=ACCENT, selectborderwidth=0)
        polish_widgets(widget)


def reserve_footer(container):
    """Allocate fixed controls before expandable content can consume their space.

    Called explicitly by packed dialogs. Keep their original visual order, but
    reserve bottom space for controls/status after the first expanding pane.
    """
    children = container.pack_slaves()
    expanding = [widget for widget in children if widget.pack_info().get("expand")]
    if not expanding:
        return
    first = expanding[0]
    for widget in reversed(children[children.index(first) + 1:]):
        if widget not in expanding:
            widget.pack_configure(side="bottom", before=first)
