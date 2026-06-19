"""
FinGuard UI – Theme & Design System
CustomTkinter 5.2.2 appearance configuration + color/font constants.
All names remain backward-compatible with existing page imports.
"""
import customtkinter as ctk
from tkinter import ttk

# ── Appearance ────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Color Palette ─────────────────────────────────────────────────────────────
BG_COLOR       = "#0F172A"   # Main slate background
SIDEBAR_COLOR  = "#111827"   # Darker sidebar
CARD_COLOR     = "#1E293B"   # Slate card background
PRIMARY_COLOR  = "#2563EB"   # Electric blue accent
SUCCESS_COLOR  = "#10B981"   # Emerald green
WARNING_COLOR  = "#F59E0B"   # Amber warning
DANGER_COLOR   = "#EF4444"   # Red danger
TEXT_COLOR     = "#F8FAFC"   # Bright white text
SUBTEXT_COLOR  = "#94A3B8"   # Soft slate-gray subtext
BORDER_COLOR   = "#1E293B"   # Subtle card borders
HOVER_COLOR    = "#1E3A5F"   # Hovered sidebar item bg
ACTIVE_COLOR   = "#172554"   # Active sidebar item bg

# Severity → Color mapping
SEVERITY_COLORS = {
    "CRITICAL": DANGER_COLOR,
    "HIGH":     "#F97316",   # Orange
    "MEDIUM":   WARNING_COLOR,
    "LOW":      SUCCESS_COLOR,
}

# Status → Color mapping
STATUS_COLORS = {
    "ACTIVE":        SUCCESS_COLOR,
    "BLOCKED":       DANGER_COLOR,
    "SUSPENDED":     WARNING_COLOR,
    "INACTIVE":      SUBTEXT_COLOR,
    "OPEN":          PRIMARY_COLOR,
    "UNDER_REVIEW":  WARNING_COLOR,
    "ESCALATED":     DANGER_COLOR,
    "RESOLVED":      SUCCESS_COLOR,
    "CLOSED":        SUBTEXT_COLOR,
    "FALSE_POSITIVE": "#8B5CF6",  # Purple
    "APPROVED":      SUCCESS_COLOR,
    "DECLINED":      DANGER_COLOR,
    "FLAGGED":       WARNING_COLOR,
    "PENDING":       WARNING_COLOR,
}

# Spacing tokens
SPACE_XS = 8
SPACE_S = 16
SPACE_M = 24
SPACE_L = 32
SPACE_XL = 48

# ── Typography ────────────────────────────────────────────────────────────────
FONT_FAMILY    = "Segoe UI"
FONT_TITLE     = (FONT_FAMILY, 32, "bold")
FONT_HEADER    = (FONT_FAMILY, 24, "bold")
FONT_SUBHEADER = (FONT_FAMILY, 18, "bold")
FONT_BODY      = (FONT_FAMILY, 14)
FONT_CAPTION   = (FONT_FAMILY, 12)
FONT_SMALL     = (FONT_FAMILY, 10)
FONT_BUTTON    = (FONT_FAMILY, 14, "bold")

# ── Indian Localization Helper ────────────────────────────────────────────────
def format_inr(number) -> str:
    """Formats a number in Indian numbering system (Lakhs, Crores) with Rupee symbol."""
    try:
        val = float(number)
    except (ValueError, TypeError):
        return f"₹{number}"
    
    if val.is_integer():
        s = str(int(val))
        decimal_part = ""
    else:
        s = f"{val:.2f}"
        s, decimal_part = s.split(".")
        decimal_part = "." + decimal_part
        
    if len(s) <= 3:
        return f"₹{s}{decimal_part}"
    
    last_three = s[-3:]
    remaining = s[:-3]
    
    out = []
    while remaining:
        out.append(remaining[-2:])
        remaining = remaining[:-2]
    out.reverse()
    
    formatted = ",".join(out) + "," + last_three
    return f"₹{formatted}{decimal_part}"

# ── CTk Font Objects (use in CTkLabel etc.) ────────────────────────────────────
def make_font(size: int, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)

# ── Treeview Dark Styling (for TableWidget) ───────────────────────────────────
def apply_treeview_style() -> ttk.Style:
    """
    Apply dark ttk.Style to Treeview widgets so they integrate with the CTk dark theme.
    Must be called after CTk root is created.
    """
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    style.configure("Dark.Treeview",
        background=CARD_COLOR,
        fieldbackground=CARD_COLOR,
        foreground=TEXT_COLOR,
        rowheight=36,
        font=FONT_BODY,
        borderwidth=0,
        relief="flat",
    )
    style.configure("Dark.Treeview.Heading",
        background="#0F172A",
        foreground=SUBTEXT_COLOR,
        font=FONT_SUBHEADER,
        padding=10,
        borderwidth=0,
        relief="flat",
    )
    style.map("Dark.Treeview",
        background=[("selected", PRIMARY_COLOR)],
        foreground=[("selected", TEXT_COLOR)],
    )
    style.layout("Dark.Treeview", [
        ("Dark.Treeview.treearea", {"sticky": "nswe"})
    ])

    # Custom Dashboard Treeview Styling (Reduced fonts and slightly increased rowheight)
    style.configure("Dashboard.Treeview",
        background=CARD_COLOR,
        fieldbackground=CARD_COLOR,
        foreground=TEXT_COLOR,
        rowheight=40,
        font=(FONT_FAMILY, 11),
        borderwidth=0,
        relief="flat",
    )
    style.configure("Dashboard.Treeview.Heading",
        background="#0F172A",
        foreground=SUBTEXT_COLOR,
        font=(FONT_FAMILY, 12, "bold"),
        padding=10,
        borderwidth=0,
        relief="flat",
    )
    style.map("Dashboard.Treeview",
        background=[("selected", PRIMARY_COLOR)],
        foreground=[("selected", TEXT_COLOR)],
    )
    style.layout("Dashboard.Treeview", [
        ("Dashboard.Treeview.treearea", {"sticky": "nswe"})
    ])

    # Also style scrollbar
    style.configure("Dark.Vertical.TScrollbar",
        background=CARD_COLOR,
        troughcolor=BG_COLOR,
        bordercolor=BG_COLOR,
        arrowcolor=SUBTEXT_COLOR,
    )
    style.configure("Dark.Horizontal.TScrollbar",
        background=CARD_COLOR,
        troughcolor=BG_COLOR,
        bordercolor=BG_COLOR,
        arrowcolor=SUBTEXT_COLOR,
    )
    return style


def setup_theme(root=None):
    """
    Backward-compatible entry point. Called from main_window.py after root created.
    """
    apply_treeview_style()


class BasePage(ctk.CTkFrame):
    """
    Standardized Page Layout structure.
    All pages inherit or use this layout pattern.
    Structure:
    - Header: Local title and quick buttons (Height: 80px)
    - Toolbar: Page-level action/search controls (Height: 60px)
    - Content Split Container:
        - Main Content (Left, weight=5)
        - Right Panel (Right, weight=3)
        - Gap between them: 24px
    - Footer: Pagination, records loaded count, status indicators.
    - All margins/paddings set to 24px.
    """
    def __init__(self, parent, title_text: str = "", has_right_panel: bool = True, **kwargs):
        super().__init__(parent, fg_color="#0F172A", corner_radius=0, **kwargs)
        
        # ── 1. Page Header (Height: 80px) ──
        self.page_header = ctk.CTkFrame(self, fg_color="transparent", height=80, corner_radius=0)
        self.page_header.pack(fill="x", padx=24, pady=(24, 0))
        self.page_header.pack_propagate(False)
        
        self.title_lbl = ctk.CTkLabel(
            self.page_header, text=title_text,
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color="#F8FAFC"
        )
        self.title_lbl.pack(side="left", anchor="center")
        
        # Header actions container (right side)
        self.header_actions = ctk.CTkFrame(self.page_header, fg_color="transparent")
        self.header_actions.pack(side="right", fill="y")
        
        # ── 2. Toolbar Frame ──
        self.toolbar = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.toolbar.pack(fill="x", padx=24, pady=(8, 8))
        self.toolbar.pack_propagate(False)
        
        # ── 3. Content Area ──
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=24, pady=8)
        
        if has_right_panel:
            self.content_container.columnconfigure(0, weight=5)
            self.content_container.columnconfigure(1, weight=3)
            self.content_container.rowconfigure(0, weight=1)
            
            # Left Content Pane
            self.main_content = ctk.CTkFrame(self.content_container, fg_color="transparent")
            self.main_content.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
            
            # Right Panel Pane
            self.right_panel = ctk.CTkFrame(self.content_container, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#2D3748")
            self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
            self.right_panel.pack_propagate(False)
        else:
            self.main_content = ctk.CTkFrame(self.content_container, fg_color="transparent")
            self.main_content.pack(fill="both", expand=True)
            self.right_panel = None
            
        # ── 4. Footer Frame ──
        self.footer = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.footer.pack(fill="x", side="bottom", padx=24, pady=(8, 24))
        self.footer.pack_propagate(False)


# ── CTkScrollableFrame Smooth Scrolling Monkeypatch ────────────────────────────

def smooth_mouse_wheel_all(self, event):
    if not self.check_if_master_is_canvas(event.widget):
        return

    # Check if shift key is pressed or orientation is horizontal
    is_shift = self._shift_pressed
    is_horizontal = (self._orientation == "horizontal" or is_shift)
    canvas = self._parent_canvas

    if is_horizontal:
        curr_left, curr_right = canvas.xview()
        page_width = curr_right - curr_left
        if page_width >= 1.0:
            return

        if not hasattr(self, '_target_x'):
            self._target_x = curr_left
            self._animating_x = False

        direction = -1 if event.delta > 0 else 1
        step = 0.05
        self._target_x = max(0.0, min(1.0 - page_width, self._target_x + direction * step))

        def smooth_scroll_step_x():
            if not hasattr(self, '_target_x') or not canvas.winfo_exists():
                return
            curr = canvas.xview()[0]
            diff = self._target_x - curr
            if abs(diff) > 0.0001:
                canvas.xview_moveto(curr + diff * 0.22)
                self.after(10, smooth_scroll_step_x)
            else:
                canvas.xview_moveto(self._target_x)
                self._animating_x = False

        if not self._animating_x:
            self._animating_x = True
            smooth_scroll_step_x()
    else:
        curr_top, curr_bottom = canvas.yview()
        page_height = curr_bottom - curr_top
        if page_height >= 1.0:
            return

        if not hasattr(self, '_target_y'):
            self._target_y = curr_top
            self._animating_y = False

        direction = -1 if event.delta > 0 else 1
        step = 0.05
        self._target_y = max(0.0, min(1.0 - page_height, self._target_y + direction * step))

        def smooth_scroll_step_y():
            if not hasattr(self, '_target_y') or not canvas.winfo_exists():
                return
            curr = canvas.yview()[0]
            diff = self._target_y - curr
            if abs(diff) > 0.0001:
                canvas.yview_moveto(curr + diff * 0.22)
                self.after(10, smooth_scroll_step_y)
            else:
                canvas.yview_moveto(self._target_y)
                self._animating_y = False

        if not self._animating_y:
            self._animating_y = True
            smooth_scroll_step_y()

ctk.CTkScrollableFrame._mouse_wheel_all = smooth_mouse_wheel_all
