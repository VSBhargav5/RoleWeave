"""Shared desktop palette and typography; standard Tk/ttk, no theme dependency."""
import tkinter as tk
from tkinter import ttk

CANVAS = "#f4f5fa"
PAPER = "#ffffff"
INK = "#20243b"
MUTED = "#667085"
ACCENT = "#6254d9"
RAIL = "#161b2d"
LINE = "#e1e4ee"


def apply_theme(window):
    style = ttk.Style(window)
    if "roleweave" not in style.theme_names():
        style.theme_create("roleweave", parent="clam")
    if style.theme_use() != "roleweave":
        style.theme_use("roleweave")
    style.configure(".", font=("Segoe UI", 10), background=PAPER, foreground=INK)
    style.configure("TFrame", background=PAPER)
    style.configure("Panel.TFrame", background=PAPER, borderwidth=1, relief="solid", bordercolor=LINE)
    style.configure("ReviewTitle.TLabel", font=("Segoe UI", 18, "bold"))
    style.configure("Opportunity.Treeview", rowheight=58, font=("Segoe UI", 10), borderwidth=0)
    style.configure("Opportunity.Treeview.Heading", font=("Segoe UI", 8, "bold"), padding=(10, 9))
    for name, background, foreground in (("Violet", "#eeebff", "#5544bf"),
                                         ("Amber", "#fff4df", "#956219"),
                                         ("Mint", "#e8f5ef", "#277450")):
        style.configure(name + ".TFrame", background=background)
        style.configure(name + ".TLabel", background=background, foreground=foreground, font=("Segoe UI", 9, "bold"))
        style.configure(name + "Value.TLabel", background=background, foreground=INK, font=("Segoe UI", 27, "bold"))
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
    style.configure("Rail.TLabel", foreground="#dbe8ec", background=RAIL)
    style.configure("Brand.TLabel", foreground=PAPER, background=RAIL, font=("Segoe UI", 18, "bold"))
    style.configure("RailMuted.TLabel", foreground="#a8c3cd", background=RAIL, font=("Segoe UI", 9))
    style.configure("Badge.TLabel", foreground=ACCENT, background="#eeebff", padding=(10, 5), font=("Segoe UI", 9, "bold"))
    style.configure("TButton", background=PAPER, foreground=INK, bordercolor=LINE, lightcolor=LINE,
                    darkcolor=LINE, borderwidth=1, relief="solid", padding=(12, 8), focusthickness=2, focuscolor=ACCENT)
    style.map("TButton", background=[("pressed", "#e6e2ff"), ("active", "#f0edff")],
              foreground=[("disabled", "#899ba3")])
    style.configure("TMenubutton", background=PAPER, foreground=INK, padding=(12, 8), bordercolor=LINE)
    style.configure("Primary.TButton", background=ACCENT, foreground=PAPER, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("disabled", "#e2dff3"), ("pressed", "#4436af"), ("active", "#5142c4")],
              foreground=[("disabled", "#77718f"), ("!disabled", PAPER)])
    style.configure("Rail.TButton", background=RAIL, foreground="#dce0f1", borderwidth=0,
                    bordercolor=RAIL, lightcolor=RAIL, darkcolor=RAIL, anchor="w", padding=(12, 11))
    style.map("Rail.TButton", background=[("active", "#282b46"), ("pressed", "#343451")], foreground=[("!disabled", PAPER)])
    style.configure("ActiveRail.TButton", background="#38305e", foreground=PAPER, anchor="w", padding=(12, 11))
    style.map("ActiveRail.TButton", background=[("active", "#343451")], foreground=[("!disabled", PAPER)])
    style.configure("TEntry", fieldbackground="#fafbfe", bordercolor=LINE, padding=(9, 7), insertcolor=INK)
    style.map("TEntry", bordercolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground="#fafbfe", background="#f0f5f6", padding=(8, 6), arrowsize=13)
    style.map("TCombobox", fieldbackground=[("readonly", "#fafbfe")], foreground=[("readonly", INK)],
              selectbackground=[("readonly", "#fafbfe")], selectforeground=[("readonly", INK)], bordercolor=[("focus", ACCENT)])
    style.configure("TCheckbutton", padding=(0, 4), background=PAPER)
    style.configure("Filter.TCombobox", padding=(6, 3), font=("Segoe UI", 9))
    style.configure("Filter.TCheckbutton", padding=0, font=("Segoe UI", 9))
    style.map("TCheckbutton", background=[("active", PAPER)])
    style.configure("TNotebook", background=PAPER, borderwidth=0, bordercolor=LINE, lightcolor=PAPER, darkcolor=PAPER, tabmargins=(0, 8, 0, 0))
    style.configure("TNotebook.Tab", padding=(15, 9), background="#f0f1f7", foreground=MUTED, bordercolor=LINE, lightcolor="#f0f1f7", darkcolor="#f0f1f7", font=("Segoe UI", 10, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#eeebff")], lightcolor=[("selected", "#eeebff")], darkcolor=[("selected", "#eeebff")], foreground=[("selected", ACCENT)])
    style.configure("TLabelframe", background=PAPER, bordercolor=LINE, relief="solid")
    style.configure("TLabelframe.Label", background=PAPER, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
    style.configure("Treeview", background=PAPER, fieldbackground=PAPER, foreground=INK,
                    rowheight=34, borderwidth=0)
    style.map("Treeview", background=[("selected", "#e7e3ff")], foreground=[("selected", "#41368d")])
    style.configure("Treeview.Heading", background="#edf3f5", foreground=MUTED, padding=(10, 9), font=("Segoe UI", 9, "bold"))
    style.configure("TScrollbar", background="#d4d6e3", troughcolor="#f4f5fa", borderwidth=0, bordercolor=PAPER, lightcolor=PAPER, darkcolor=PAPER, arrowcolor=MUTED, gripcount=0, arrowsize=10, width=10)
    window.configure(background=CANVAS)
    window.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
    window.option_add("*TCombobox*Listbox.background", PAPER)
    window.option_add("*TCombobox*Listbox.foreground", INK)
    # ttk queues ThemeChanged at idle. Drain it while this Tk interpreter still
    # owns its event command, including windows closed before mainloop starts.
    window.update_idletasks()


def polish_widgets(window):
    """Style classic Tk text/list widgets that ttk styles cannot reach."""
    for widget in window.winfo_children():
        if isinstance(widget, tk.Text):
            widget.configure(font=("Segoe UI", 10), background="#fafbfe", foreground=INK,
                             insertbackground=INK, selectbackground="#e1dcff", selectforeground="#41368d",
                             relief="flat", borderwidth=0, highlightthickness=1,
                             highlightbackground=LINE, highlightcolor=ACCENT, padx=12, pady=10, spacing1=2, spacing3=4)
        elif isinstance(widget, tk.Listbox):
            widget.configure(font=("Segoe UI", 10), background="#fafbfe", foreground=INK,
                             selectbackground="#e7e3ff", selectforeground="#41368d", activestyle="none",
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
