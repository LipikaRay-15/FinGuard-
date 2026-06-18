import tkinter as tk
from tkinter import ttk

# Palette Colors (Slate/Dark Mode Theme)
BG_COLOR = "#0F172A"         # Main slate background
SIDEBAR_COLOR = "#111827"    # Darker sidebar
CARD_COLOR = "#1E293B"       # Slate card background
PRIMARY_COLOR = "#2563EB"    # Electric blue
SUCCESS_COLOR = "#10B981"    # Green
WARNING_COLOR = "#F59E0B"    # Yellow-Orange
DANGER_COLOR = "#EF4444"     # Red
TEXT_COLOR = "#F8FAFC"       # Bright white text
SUBTEXT_COLOR = "#94A3B8"    # Soft gray text

# Typography (Segoe UI Font Families)
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_HEADER = (FONT_FAMILY, 13, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 11, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_CAPTION = (FONT_FAMILY, 9)

def setup_theme(root):
    """
    Initializes flat, custom ttk styles on top of the 'clam' base theme.
    """
    style = ttk.Style(root)
    
    # Force use of 'clam' theme to enable background customization on Windows
    if "clam" in style.theme_names():
        style.theme_use("clam")
        
    # Configure root/global options
    style.configure(".",
        background=BG_COLOR,
        foreground=TEXT_COLOR,
        font=FONT_BODY,
        fieldbackground=CARD_COLOR,
        borderwidth=0,
        highlightthickness=0
    )
    
    # Standard Frames
    style.configure("TFrame", background=BG_COLOR)
    style.configure("Sidebar.TFrame", background=SIDEBAR_COLOR)
    style.configure("Card.TFrame", background=CARD_COLOR, borderwidth=0)
    style.configure("Header.TFrame", background=BG_COLOR)
    
    # Standard Labels
    style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
    style.configure("Sidebar.TLabel", background=SIDEBAR_COLOR, foreground=TEXT_COLOR, font=FONT_BODY)
    style.configure("Card.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR)
    style.configure("CardTitle.TLabel", background=CARD_COLOR, foreground=SUBTEXT_COLOR, font=FONT_CAPTION)
    style.configure("CardVal.TLabel", background=CARD_COLOR, foreground=TEXT_COLOR, font=FONT_HEADER)
    style.configure("HeaderTitle.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=FONT_TITLE)
    
    # Standard Buttons
    style.configure("TButton",
        background=PRIMARY_COLOR,
        foreground=TEXT_COLOR,
        borderwidth=0,
        focuscolor=PRIMARY_COLOR,
        focusthickness=0,
        padding=(12, 6),
        font=FONT_SUBHEADER
    )
    style.map("TButton",
        background=[("active", "#1D4ED8"), ("pressed", "#1E3A8A")]
    )
    
    # Sidebar Navigation Buttons
    style.configure("Sidebar.TButton",
        background=SIDEBAR_COLOR,
        foreground=SUBTEXT_COLOR,
        borderwidth=0,
        focuscolor=SIDEBAR_COLOR,
        focusthickness=0,
        padding=(16, 10),
        font=FONT_SUBHEADER
    )
    style.map("Sidebar.TButton",
        background=[("active", "#1F2937"), ("pressed", "#374151")],
        foreground=[("active", TEXT_COLOR)]
    )
    
    # Accent / Color specific buttons
    style.configure("Success.TButton", background=SUCCESS_COLOR)
    style.map("Success.TButton", background=[("active", "#059669")])
    
    style.configure("Danger.TButton", background=DANGER_COLOR)
    style.map("Danger.TButton", background=[("active", "#DC2626")])
    
    style.configure("Warning.TButton", background=WARNING_COLOR)
    style.map("Warning.TButton", background=[("active", "#D97706")])

    # Text Entries
    style.configure("TEntry",
        fieldbackground=CARD_COLOR,
        foreground=TEXT_COLOR,
        background=CARD_COLOR,
        insertcolor=TEXT_COLOR,
        padding=6,
        borderwidth=1,
        lightcolor="#334155",
        darkcolor="#334155"
    )
    style.map("TEntry",
        fieldbackground=[("focus", "#0F172A")],
        bordercolor=[("focus", PRIMARY_COLOR)]
    )

    # Combo Box
    style.configure("TCombobox",
        fieldbackground=CARD_COLOR,
        background=CARD_COLOR,
        foreground=TEXT_COLOR,
        arrowcolor=TEXT_COLOR,
        padding=6
    )

    # Progress Bar
    style.configure("Horizontal.TProgressbar",
        troughcolor=CARD_COLOR,
        background=PRIMARY_COLOR,
        thickness=10
    )
    
    # Treeview (Tables)
    style.configure("Treeview",
        background=CARD_COLOR,
        fieldbackground=CARD_COLOR,
        foreground=TEXT_COLOR,
        rowheight=32,
        font=FONT_BODY,
        borderwidth=0
    )
    style.configure("Treeview.Heading",
        background=SIDEBAR_COLOR,
        foreground=SUBTEXT_COLOR,
        font=FONT_SUBHEADER,
        padding=8,
        borderwidth=0
    )
    style.map("Treeview",
        background=[("selected", PRIMARY_COLOR)],
        foreground=[("selected", TEXT_COLOR)]
    )
