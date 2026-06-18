import tkinter as tk
from tkinter import ttk
from ui.widgets.theme import (
    SIDEBAR_COLOR,
    PRIMARY_COLOR,
    TEXT_COLOR,
    SUBTEXT_COLOR,
    FONT_HEADER,
    FONT_BODY
)

class SidebarMenu(ttk.Frame):
    """
    A premium navigation sidebar menu. Supports expanding/collapsing.
    Toggles between showing (Icon + Label) and showing only the (Icon)
    to optimize screen real estate.
    """
    def __init__(self, parent, select_callback, **kwargs) -> None:
        super().__init__(parent, style="Sidebar.TFrame", **kwargs)
        self.select_callback = select_callback
        self.expanded = True
        
        # Configure layout configurations
        self.columnconfigure(0, weight=1)
        
        # Header/Toggle Area
        self.header_frame = tk.Frame(self, bg=SIDEBAR_COLOR, height=60)
        self.header_frame.pack_propagate(False)
        self.header_frame.pack(fill="x", side="top", pady=(10, 20))
        
        # Logo Label (Shown only when expanded)
        self.logo_lbl = tk.Label(
            self.header_frame,
            text="🛡️ FinGuard",
            bg=SIDEBAR_COLOR,
            fg=TEXT_COLOR,
            font=FONT_HEADER
        )
        self.logo_lbl.pack(side="left", padx=16)
        
        # Collapse Toggle Button
        self.toggle_btn = tk.Button(
            self.header_frame,
            text="☰",
            bg=SIDEBAR_COLOR,
            fg=SUBTEXT_COLOR,
            activebackground="#1F2937",
            activeforeground=TEXT_COLOR,
            bd=0,
            cursor="hand2",
            command=self.toggle_sidebar,
            font=("Segoe UI", 12, "bold")
        )
        self.toggle_btn.pack(side="right", padx=16)
        
        # Navigation Items Definition
        # (Page Key, Icon, Label)
        self.menu_items = [
            ("dashboard", "🏠", "Dashboard"),
            ("customers", "👤", "Customers"),
            ("transactions", "💳", "Transactions"),
            ("fraud", "🛡️", "Fraud Detection"),
            ("alerts", "🚨", "Alerts"),
            ("cases", "📁", "Cases"),
            ("investigation", "🔍", "Investigation"),
            ("analytics", "📈", "Analytics"),
            ("reports", "📄", "Reports"),
            ("simulator", "⚙️", "Simulator"),
        ]
        
        # Create buttons
        self.buttons = {}
        self.active_page = None
        
        self.btn_container = tk.Frame(self, bg=SIDEBAR_COLOR)
        self.btn_container.pack(fill="both", expand=True, side="top")
        
        for page_id, icon, label in self.menu_items:
            btn_frame = tk.Frame(self.btn_container, bg=SIDEBAR_COLOR)
            btn_frame.pack(fill="x", pady=2)
            
            btn = tk.Button(
                btn_frame,
                text=f"{icon}   {label}",
                anchor="w",
                bg=SIDEBAR_COLOR,
                fg=SUBTEXT_COLOR,
                activebackground="#1F2937",
                activeforeground=TEXT_COLOR,
                bd=0,
                cursor="hand2",
                padx=16,
                pady=10,
                font=FONT_BODY,
                command=lambda p=page_id: self.select_page(p)
            )
            btn.pack(fill="x")
            
            self.buttons[page_id] = {
                "btn": btn,
                "icon": icon,
                "label": label,
                "frame": btn_frame
            }
            
        # Select dashboard by default
        self.select_page("dashboard")

    def toggle_sidebar(self) -> None:
        """
        Collapses or expands sidebar widths and toggles button labels.
        """
        self.expanded = not self.expanded
        
        if self.expanded:
            self.logo_lbl.pack(side="left", padx=16)
            for page_id, info in self.buttons.items():
                info["btn"].configure(text=f"{info['icon']}   {info['label']}", anchor="w")
            self.configure(width=200)
        else:
            self.logo_lbl.pack_forget()
            for page_id, info in self.buttons.items():
                info["btn"].configure(text=info["icon"], anchor="center")
            self.configure(width=60)

    def select_page(self, page_id: str) -> None:
        """
        Switches navigation states, highlighting the selected button.
        """
        if self.active_page:
            # Revert old button color
            self.buttons[self.active_page]["btn"].configure(
                bg=SIDEBAR_COLOR,
                fg=SUBTEXT_COLOR
            )
            
        self.active_page = page_id
        
        # Set highlight styles
        self.buttons[page_id]["btn"].configure(
            bg="#1E293B",  # Highlighted slate card background
            fg=TEXT_COLOR
        )
        
        # Fire select callback
        self.select_callback(page_id)
