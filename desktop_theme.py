"""Shared desktop palette and typography; standard Tk/ttk, no theme dependency."""
import tkinter as tk
from tkinter import ttk

CANVAS = "#f2f5f7"
PAPER = "#ffffff"
INK = "#18323e"
MUTED = "#5c727e"
ACCENT = "#08766c"
RAIL = "#142f3a"
LINE = "#d5e0e5"


def apply_theme(window):
    style = ttk.Style(window)
    if "roleweave" not in style.theme_names():
        style.theme_create("roleweave", parent="clam")
    style.theme_use("roleweave")
    style.configure(".", font=("Segoe UI", 10), background=PAPER, foreground=INK)
    style.configure("TFrame", background=PAPER)
    style.configure("App.TFrame", background=CANVAS)
    style.configure("Rail.TFrame", background=RAIL)
    style.configure("TLabel", background=PAPER, foreground=INK)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("App.TLabel", background=CANVAS)
    style.configure("AppMuted.TLabel", background=CANVAS, foreground=MUTED)
    style.configure("Title.TLabel", background=CANVAS, font=("Segoe UI", 23, "bold"))
    style.configure("Section.TLabel", font=("Segoe UI", 13, "bold"))
    style.configure("Eyebrow.TLabel", foreground=ACCENT, font=("Segoe UI", 9, "bold"))
    style.configure("Metric.TLabel", font=("Segoe UI", 22, "bold"))
    style.configure("Rail.TLabel", foreground="#dbe8ec", background=RAIL)
    style.configure("Brand.TLabel", foreground=PAPER, background=RAIL, font=("Segoe UI", 18, "bold"))
    style.configure("RailMuted.TLabel", foreground="#a8c3cd", background=RAIL, font=("Segoe UI", 9))
    style.configure("Badge.TLabel", foreground=ACCENT, background="#e5f4ef", padding=(10, 5), font=("Segoe UI", 9, "bold"))
    style.configure("TButton", background=PAPER, foreground=INK, bordercolor=LINE, lightcolor=LINE,
                    darkcolor=LINE, padding=(12, 8), focusthickness=2, focuscolor=ACCENT)
    style.map("TButton", background=[("pressed", "#dbece7"), ("active", "#edf5f3")],
              foreground=[("disabled", "#899ba3")])
    style.configure("TMenubutton", background=PAPER, foreground=INK, padding=(12, 8), bordercolor=LINE)
    style.configure("Primary.TButton", background=ACCENT, foreground=PAPER, bordercolor=ACCENT,
                    lightcolor=ACCENT, darkcolor=ACCENT, font=("Segoe UI", 10, "bold"))
    style.map("Primary.TButton", background=[("disabled", "#d9e5e2"), ("pressed", "#05594f"), ("active", "#09665d")],
              foreground=[("disabled", "#637d76"), ("!disabled", PAPER)])
    style.configure("Rail.TButton", background=RAIL, foreground="#dfebef", borderwidth=0,
                    bordercolor=RAIL, lightcolor=RAIL, darkcolor=RAIL, anchor="w", padding=(12, 11))
    style.map("Rail.TButton", background=[("active", "#254956"), ("pressed", "#315d68")], foreground=[("!disabled", PAPER)])
    style.configure("ActiveRail.TButton", background="#254b57", foreground=PAPER, anchor="w", padding=(12, 11))
    style.map("ActiveRail.TButton", background=[("active", "#315d68")], foreground=[("!disabled", PAPER)])
    style.configure("TEntry", fieldbackground="#fbfcfd", bordercolor=LINE, padding=(9, 7), insertcolor=INK)
    style.map("TEntry", bordercolor=[("focus", ACCENT)])
    style.configure("TCombobox", fieldbackground="#fbfcfd", background="#f0f5f6", padding=(8, 6), arrowsize=13)
    style.map("TCombobox", fieldbackground=[("readonly", "#fbfcfd")], foreground=[("readonly", INK)],
              selectbackground=[("readonly", "#fbfcfd")], selectforeground=[("readonly", INK)], bordercolor=[("focus", ACCENT)])
    style.configure("TCheckbutton", padding=(0, 4), background=PAPER)
    style.map("TCheckbutton", background=[("active", PAPER)])
    style.configure("TNotebook", background=PAPER, borderwidth=0, tabmargins=(0, 8, 0, 0))
    style.configure("TNotebook.Tab", padding=(17, 10), background="#edf2f4", foreground=MUTED)
    style.map("TNotebook.Tab", background=[("selected", PAPER)], foreground=[("selected", ACCENT)])
    style.configure("TLabelframe", background=PAPER, bordercolor=LINE, relief="solid")
    style.configure("TLabelframe.Label", background=PAPER, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
    style.configure("Treeview", background=PAPER, fieldbackground=PAPER, foreground=INK,
                    rowheight=34, borderwidth=0)
    style.map("Treeview", background=[("selected", "#d8eee7")], foreground=[("selected", "#064f48")])
    style.configure("Treeview.Heading", background="#edf3f5", foreground=MUTED, padding=(10, 9), font=("Segoe UI", 9, "bold"))
    style.configure("TScrollbar", background="#c4d3da", troughcolor="#f0f4f6", borderwidth=0, arrowsize=12)
    window.configure(background=CANVAS)
    window.option_add("*TCombobox*Listbox.font", ("Segoe UI", 10))
    window.option_add("*TCombobox*Listbox.background", PAPER)
    window.option_add("*TCombobox*Listbox.foreground", INK)


def polish_widgets(window):
    """Style classic Tk text/list widgets that ttk styles cannot reach."""
    for widget in window.winfo_children():
        if isinstance(widget, tk.Text):
            widget.configure(font=("Segoe UI", 10), background="#fbfcfd", foreground=INK,
                             insertbackground=INK, selectbackground="#c9e8de", selectforeground="#064f48",
                             relief="flat", borderwidth=0, highlightthickness=1,
                             highlightbackground=LINE, highlightcolor=ACCENT, padx=12, pady=10, spacing1=2, spacing3=4)
        elif isinstance(widget, tk.Listbox):
            widget.configure(font=("Segoe UI", 10), background="#fbfcfd", foreground=INK,
                             selectbackground="#d9eee7", selectforeground="#064f48", activestyle="none",
                             relief="flat", borderwidth=0, highlightthickness=1, highlightbackground=LINE,
                             highlightcolor=ACCENT, selectborderwidth=0)
        polish_widgets(widget)
