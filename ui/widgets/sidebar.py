import customtkinter as ctk
from ui.widgets.theme import (
    SIDEBAR_COLOR,
    PRIMARY_COLOR,
    TEXT_COLOR,
    SUBTEXT_COLOR,
    FONT_HEADER,
    FONT_BODY
)

class SidebarMenu(ctk.CTkFrame):
    """
    A premium navigation sidebar menu built with CustomTkinter.
    Supports expanding/collapsing on user command.
    """
    def __init__(self, parent, select_callback, **kwargs) -> None:
        super().__init__(
            parent,
            fg_color=SIDEBAR_COLOR,
            corner_radius=0,
            width=240,
            **kwargs
        )
        self.select_callback = select_callback
        self.expanded = True
        
        # Prevent children from resizing the frame
        self.pack_propagate(False)
        
        # Header/Toggle Area
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=60, corner_radius=0)
        self.header_frame.pack_propagate(False)
        self.header_frame.pack(fill="x", side="top", pady=(10, 20))
        
        # Logo Label (Shown only when expanded)
        self.logo_lbl = ctk.CTkLabel(
            self.header_frame,
            text="🛡️ FinGuard",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=TEXT_COLOR
        )
        self.logo_lbl.pack(side="left", padx=16)
        
        # Collapse Toggle Button
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="☰",
            width=36, height=36,
            fg_color="transparent",
            hover_color="#1F2937",
            text_color=SUBTEXT_COLOR,
            font=("Segoe UI", 14, "bold"),
            command=self.toggle_sidebar
        )
        self.toggle_btn.pack(side="right", padx=16)
        
        # Navigation Items Definition (Page Key, Icon, Label)
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
        
        self.btn_container = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_container.pack(fill="both", expand=True, side="top")
        
        for page_id, icon, label in self.menu_items:
            btn_frame = ctk.CTkFrame(self.btn_container, fg_color="transparent")
            btn_frame.pack(fill="x", pady=2, padx=12)
            
            btn = ctk.CTkButton(
                btn_frame,
                text=f"  {icon}   {label}",
                anchor="w",
                fg_color="transparent",
                hover_color="#1F2937",
                text_color=SUBTEXT_COLOR,
                height=40,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=lambda p=page_id: self.select_page(p)
            )
            btn.pack(fill="x")
            
            self.buttons[page_id] = {
                "btn": btn,
                "icon": icon,
                "label": label,
                "frame": btn_frame
            }
            
        # Help Button
        self.btn_help_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_help_frame.pack(fill="x", side="bottom", pady=(10, 20), padx=12)
        
        self.btn_help = ctk.CTkButton(
            self.btn_help_frame,
            text="  ❓   Help",
            anchor="w",
            fg_color="transparent",
            hover_color="#1F2937",
            text_color=SUBTEXT_COLOR,
            height=40,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            command=self.show_help_menu
        )
        self.btn_help.pack(fill="x")

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
                info["btn"].configure(text=f"  {info['icon']}   {info['label']}", anchor="w")
            self.btn_help.configure(text="  ❓   Help", anchor="w")
            self.configure(width=240)
            if hasattr(self.master, "columnconfigure"):
                self.master.columnconfigure(0, minsize=240)
        else:
            self.logo_lbl.pack_forget()
            for page_id, info in self.buttons.items():
                info["btn"].configure(text=info["icon"], anchor="center")
            self.btn_help.configure(text="❓", anchor="center")
            self.configure(width=70)
            if hasattr(self.master, "columnconfigure"):
                self.master.columnconfigure(0, minsize=70)

    def select_page(self, page_id: str) -> None:
        """
        Switches navigation states, highlighting the selected button.
        """
        if self.active_page:
            self.buttons[self.active_page]["btn"].configure(
                fg_color="transparent",
                text_color=SUBTEXT_COLOR
            )
            
        self.active_page = page_id
        
        # Set highlight styles
        self.buttons[page_id]["btn"].configure(
            fg_color="#1E293B",  # Highlighted slate card background
            text_color=TEXT_COLOR
        )
        
        # Fire select callback
        self.select_callback(page_id)

    def show_help_menu(self) -> None:
        from ui.widgets.tour_overlay import HelpDropdown
        
        # Calculate dropdown coordinates relative to the help button
        self.update_idletasks()
        bx = self.btn_help.winfo_rootx()
        by = self.btn_help.winfo_rooty()
        bw = self.btn_help.winfo_width()
        bh = self.btn_help.winfo_height()
        
        # Position dropdown above/next to the help button
        drop_x = bx + bw + 10
        drop_y = by + bh - 184  # 184 is dropdown height
        
        # Bounds check
        if drop_y < 10: drop_y = 10
        
        # Show dropdown
        dropdown = HelpDropdown(
            self.master,
            guide_cb=getattr(self.master, "show_user_guide", lambda: None),
            start_cb=getattr(self.master, "show_getting_started", lambda: None),
            keys_cb=getattr(self.master, "show_keyboard_shortcuts", lambda: None),
            about_cb=getattr(self.master, "show_about_finguard", lambda: None),
            docs_cb=getattr(self.master, "show_documentation", lambda: None)
        )
        dropdown.geometry(f"180x184+{drop_x}+{drop_y}")
