"""
FinGuard UI – Welcome Center & Interactive User Guide
Module 23: Standing Guide window, Welcome dialog, and Help integrations.
"""
import customtkinter as ctk
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, PRIMARY_COLOR, SUCCESS_COLOR, TEXT_COLOR,
    SUBTEXT_COLOR, FONT_FAMILY, make_font
)

class WelcomeModal(ctk.CTkFrame):
    """
    Centered onboarding welcome dialog. Prompts the user to open the Quick Guide or skip.
    """
    def __init__(self, parent, start_callback, skip_callback):
        # Semi-transparent background dim/blur simulation
        self.dim_bg = ctk.CTkFrame(parent, fg_color="#020617")
        self.dim_bg.place(relwidth=1, relheight=1)
        self.dim_bg.bind("<Button-1>", lambda e: "break")

        super().__init__(
            self.dim_bg,
            fg_color="#1E293B",
            border_color="#2563EB",
            border_width=2,
            corner_radius=16,
            width=500,
            height=320
        )
        self.place(relx=0.5, rely=0.5, anchor="center")
        self.pack_propagate(False)

        # Shield Logo Icon
        ctk.CTkLabel(
            self, text="🛡️",
            font=make_font(48),
            text_color="#2563EB"
        ).pack(pady=(24, 8))

        # Title
        ctk.CTkLabel(
            self, text="Welcome to FinGuard",
            font=make_font(22, "bold"),
            text_color=TEXT_COLOR
        ).pack()

        # Subtitle
        ctk.CTkLabel(
            self, text="Intelligent Financial Fraud & Risk Monitoring Platform",
            font=make_font(11),
            text_color=SUBTEXT_COLOR
        ).pack(pady=(2, 12))

        # Message
        ctk.CTkLabel(
            self,
            text="Welcome to FinGuard.\nThis guide takes less than two minutes and will help you understand the platform.",
            font=make_font(12),
            text_color=TEXT_COLOR,
            justify="center",
            wraplength=420
        ).pack(pady=(0, 24))

        # Buttons Panel
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", padx=40, pady=(0, 24))

        # Skip Button
        ctk.CTkButton(
            btn_frame, text="Skip",
            width=120, height=36,
            fg_color="transparent",
            border_color="#475569",
            border_width=1,
            text_color=SUBTEXT_COLOR,
            hover_color="#334155",
            command=lambda: [self.dim_bg.destroy(), skip_callback()]
        ).pack(side="left")

        # Open Quick Guide Button
        ctk.CTkButton(
            btn_frame, text="Open Quick Guide",
            width=260, height=36,
            fg_color=PRIMARY_COLOR,
            text_color=TEXT_COLOR,
            hover_color="#1D4ED8",
            command=lambda: [self.dim_bg.destroy(), start_callback()]
        ).pack(side="right")


class WelcomeCenterWindow(ctk.CTkToplevel):
    """
    Dedicated Interactive User Guide & Welcome Center window.
    Completely modeless - does NOT block dashboard interactions.
    """
    def __init__(self, parent, on_close_callback=None):
        super().__init__(parent)
        self.title("FinGuard - Quick Start & User Guide")
        self.configure(fg_color="#0F172A")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        self.on_close_callback = on_close_callback

        # Window positioning: Center on parent
        self.update_idletasks()
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
        except Exception:
            px, py, pw, ph = 0, 0, 1920, 1080
        x = px + (pw - 1200) // 2
        y = py + (ph - 800) // 2
        self.geometry(f"1200x800+{max(0, x)}+{max(0, y)}")

        self.current_page = 0
        self.sidebar_buttons = {}

        # Page definitions
        self.pages_data = [
            {
                "id": "dashboard",
                "icon": "🏠",
                "title": "Dashboard",
                "desc": "Monitor customers, alerts, recent events and system health from the centralized platform controller.",
                "kpis": [("Total Customers", "54"), ("Open Cases", "12"), ("Critical Alerts", "0")],
                "tips": "Double-click any graph point to inspect specific fraud rule spikes.",
                "practices": "Keep the dashboard open on secondary monitoring screens to track live transaction generators.",
                "cases": "Daily system operational oversight, security compliance tracking, and database status checks."
            },
            {
                "id": "customers",
                "icon": "👤",
                "title": "Customer Management",
                "desc": "Create, search, update and inspect customer KYC profiles and risk tier assignments.",
                "kpis": [("KYC Verified", "48"), ("High Risk Profiles", "8"), ("Whitelist Entries", "32")],
                "tips": "Use wildcard filters (e.g. first characters) to query customer names rapidly.",
                "practices": "Regularly audit customers flagged as MEDIUM risk to check PAN/Aadhaar mismatch updates.",
                "cases": "KYC onboarding, manual whitelist exemptions, and risk category remediation."
            },
            {
                "id": "transactions",
                "icon": "💳",
                "title": "Transactions",
                "desc": "Track credit card, ACH, and terminal events ledger. Query historic transactional records.",
                "kpis": [("Total Volume", "$24,500"), ("Approval Rate", "98.2%"), ("Active Ledgers", "1")],
                "tips": "Click column headers to sort transactions by amount or timestamp.",
                "practices": "Verify event timestamps match simulated UTC sequences during multi-scenario runs.",
                "cases": "Auditing transaction exceptions, dispute verification, and trace tracking."
            },
            {
                "id": "fraud",
                "icon": "🛡",
                "title": "Fraud Detection",
                "desc": "Analyze transactions, adjust risk threshold metrics, and toggle custom detection rules.",
                "kpis": [("Active Rules", "6"), ("Blocked Rate", "1.4%"), ("Avg Risk Score", "12/100")],
                "tips": "Disabling 'Extreme Amount Halt' allows larger transaction loads without immediate bypass execution.",
                "practices": "Always run simulation scripts to verify rules are loaded before adjusting limits.",
                "cases": "Updating velocity parameters, fraud model backtesting, and rule adjustment."
            },
            {
                "id": "alerts",
                "icon": "🚨",
                "title": "Alerts",
                "desc": "Monitor real-time system alerts triggered by risk models. Assign flags by severity and status.",
                "kpis": [("Critical Alerts", "0"), ("High Severity", "4"), ("Pending Review", "12")],
                "tips": "Alerts queue is auto-refreshed every 5 seconds when transaction streams are active.",
                "practices": "Review high severity alerts first to prevent malicious card velocity runs.",
                "cases": "Triage security exceptions, investigate suspicious activities, and trigger alerts."
            },
            {
                "id": "cases",
                "icon": "📁",
                "title": "Cases",
                "desc": "Assign investigators, track case workflows, and manage case resolution status.",
                "kpis": [("Open Investigations", "12"), ("Unassigned Cases", "2"), ("Resolved Today", "5")],
                "tips": "Use the Case Board Kanban columns to drag and drop cases from OPEN to UNDER_REVIEW.",
                "practices": "Ensure detailed case notes are logged before changing the case status to RESOLVED.",
                "cases": "Managing compliance queues, assigning investigators, and audits."
            },
            {
                "id": "investigation",
                "icon": "🔍",
                "title": "Investigation",
                "desc": "Inspect comprehensive customer profiles: timelines, rules, devices, and risk scores.",
                "kpis": [("Dossier Checks", "100%"), ("Linked Devices", "4"), ("PAN Matches", "Valid")],
                "tips": "The timeline view compiles KYC details, transactions, and alert triggers in one chronological desk.",
                "practices": "Compare IP shifting history to identify location anomalies or proxy networks.",
                "cases": "Detailed forensic audit, compliance reports preparation, and final action approval."
            },
            {
                "id": "analytics",
                "icon": "📈",
                "title": "Analytics",
                "desc": "Evaluate system fraud trends, risk level spreads, and compile insights via visual charts.",
                "kpis": [("Data Coverage", "30 Days"), ("Chart Modules", "3"), ("Accuracy Rating", "99.8%")],
                "tips": "Export charts directly by right-clicking the analytical canvas plot.",
                "practices": "Compare fraud rules frequency monthly to identify shifts in customer transaction patterns.",
                "cases": "Quarterly compliance briefings, ML model performance monitoring, and risk trends."
            },
            {
                "id": "reports",
                "icon": "📄",
                "title": "Reports",
                "desc": "Generate compliance logs, risk digests, and export tabular summaries.",
                "kpis": [("Export Formats", "PDF/CSV"), ("Generated Logs", "14"), ("Compliance Score", "100%")],
                "tips": "Reports can be customized by filtering target dates before compiling exports.",
                "practices": "Schedule weekly report exports to keep local archive logs up to date.",
                "cases": "Filing suspicious activity reports, external auditing, and team status digests."
            },
            {
                "id": "simulator",
                "icon": "⚙",
                "title": "Simulator",
                "desc": "Configure live data streams, customer registration bursts, and custom transaction velocity testing.",
                "kpis": [("Simulator Status", "Idle"), ("Transactions/Sec", "0.0"), ("Failure Rate", "0%")],
                "tips": "Starting simulator logs output to the embedded console screen at the bottom of the simulator page.",
                "practices": "Run fraud tests on isolated transaction counts before launching continuous streams.",
                "cases": "Simulating high load testing, testing rule configurations, and training dashboard operators."
            }
        ]

        self._build_layout()
        self.show_page(0)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build_layout(self) -> None:
        # Left Sidebar (Navigation)
        self.sidebar_frame = ctk.CTkFrame(self, width=260, fg_color="#111827", corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        # Title/Branding Header
        header_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=60)
        header_frame.pack(fill="x", pady=(10, 10))
        
        ctk.CTkLabel(
            header_frame, text="📖 FinGuard Guide",
            font=make_font(18, "bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", padx=20)

        # Search Bar
        search_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=40)
        search_frame.pack(fill="x", padx=14, pady=(0, 10))
        
        self.search_val = ctk.StringVar()
        self.search_val.trace_add("write", self._filter_sidebar)
        self.search_bar = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_val,
            placeholder_text="Search guide...",
            font=make_font(11),
            fg_color="#1E293B",
            border_color="#334155",
            corner_radius=6,
            height=28
        )
        self.search_bar.pack(fill="x")

        # Scrollable Sidebar Buttons List
        self.nav_scroll = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            fg_color="transparent",
            corner_radius=0
        )
        self.nav_scroll.pack(fill="both", expand=True, padx=4)

        # Create sidebar buttons
        for idx, page in enumerate(self.pages_data):
            label = f"{page['icon']}  {page['title']}"
            btn = ctk.CTkButton(
                self.nav_scroll,
                text=label,
                anchor="w",
                font=make_font(11),
                text_color=SUBTEXT_COLOR,
                fg_color="transparent",
                hover_color="#1E293B",
                corner_radius=8,
                height=36,
                command=lambda i=idx: self.show_page(i)
            )
            btn.pack(fill="x", pady=2, padx=6)
            self.sidebar_buttons[idx] = btn

        # Final Page Button
        self.finish_nav_btn = ctk.CTkButton(
            self.nav_scroll,
            text="🎉  You're All Set!",
            anchor="w",
            font=make_font(11, "bold"),
            text_color=SUBTEXT_COLOR,
            fg_color="transparent",
            hover_color="#1E293B",
            corner_radius=8,
            height=36,
            command=lambda: self.show_page(len(self.pages_data))
        )
        self.finish_nav_btn.pack(fill="x", pady=2, padx=6)
        self.sidebar_buttons[len(self.pages_data)] = self.finish_nav_btn

        # Separator line in sidebar footer
        ctk.CTkFrame(self.sidebar_frame, fg_color="#1F2937", height=1).pack(fill="x", pady=10)

        # Modeless Indicator Label
        indicator_lbl = ctk.CTkLabel(
            self.sidebar_frame,
            text="💡 Dashboard remains fully active",
            font=make_font(9),
            text_color="#64748B",
            anchor="center"
        )
        indicator_lbl.pack(fill="x", pady=(0, 16))

        # Main Content Frame (Right side)
        self.main_content = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.main_content.pack(side="right", fill="both", expand=True)

        # Right Scrollable Area
        self.content_scroll = ctk.CTkScrollableFrame(
            self.main_content,
            fg_color="transparent",
            corner_radius=0
        )
        self.content_scroll.pack(fill="both", expand=True, padx=40, pady=24)

        # Bottom Controls bar
        self.controls_bar = ctk.CTkFrame(self.main_content, fg_color="#111827", height=60, corner_radius=0)
        self.controls_bar.pack(side="bottom", fill="x")
        self.controls_bar.pack_propagate(False)

        # Top border line of bottom bar
        ctk.CTkFrame(self.controls_bar, fg_color="#1F2937", height=1).pack(fill="x", side="top")

        # Controls padding frame
        ctrl_pad = ctk.CTkFrame(self.controls_bar, fg_color="transparent")
        ctrl_pad.pack(fill="both", expand=True, padx=30)

        # Progress Indicator Text
        self.progress_lbl = ctk.CTkLabel(
            ctrl_pad, text="Page 1 / 11",
            font=make_font(11, "bold"),
            text_color="#64748B"
        )
        self.progress_lbl.pack(side="left", fill="y")

        # Buttons
        self.btn_next = ctk.CTkButton(
            ctrl_pad, text="Next",
            width=80, height=30,
            fg_color=PRIMARY_COLOR,
            hover_color="#1D4ED8",
            font=make_font(11, "bold"),
            command=self.next_page
        )
        self.btn_next.pack(side="right", padx=(10, 0), pady=14)

        self.btn_prev = ctk.CTkButton(
            ctrl_pad, text="Previous",
            width=80, height=30,
            fg_color="transparent",
            border_color="#475569",
            border_width=1,
            text_color=SUBTEXT_COLOR,
            hover_color="#334155",
            font=make_font(11),
            command=self.prev_page
        )
        self.btn_prev.pack(side="right", pady=14)

    def show_page(self, page_idx: int) -> None:
        if page_idx < 0 or page_idx > len(self.pages_data):
            return
        self.current_page = page_idx

        # Update sidebar highlight
        for idx, btn in self.sidebar_buttons.items():
            if idx == page_idx:
                btn.configure(fg_color="#1E293B", text_color=TEXT_COLOR)
            else:
                btn.configure(fg_color="transparent", text_color=SUBTEXT_COLOR)

        # Clear scrollable content view
        for child in self.content_scroll.winfo_children():
            child.destroy()

        total_pages = len(self.pages_data) + 1
        self.progress_lbl.configure(text=f"Page {page_idx + 1} / {total_pages}")

        # Previous button state
        if page_idx == 0:
            self.btn_prev.configure(state="disabled", border_color="#1E293B", text_color="#1E293B")
        else:
            self.btn_prev.configure(state="normal", border_color="#475569", text_color=SUBTEXT_COLOR)

        # Next / Finish button config
        if page_idx == total_pages - 1:
            self.btn_next.configure(text="Finish Guide", fg_color=SUCCESS_COLOR, hover_color="#059669")
        else:
            self.btn_next.configure(text="Next", fg_color=PRIMARY_COLOR, hover_color="#1D4ED8")

        # Build Page Contents
        if page_idx < len(self.pages_data):
            data = self.pages_data[page_idx]
            self._render_guide_page(data)
        else:
            self._render_final_page()

    def _render_guide_page(self, data: dict) -> None:
        # Title
        ctk.CTkLabel(
            self.content_scroll, text=data["title"],
            font=make_font(24, "bold"),
            text_color=TEXT_COLOR,
            anchor="w"
        ).pack(fill="x", pady=(10, 8))

        # Explanation
        ctk.CTkLabel(
            self.content_scroll, text=data["desc"],
            font=make_font(12),
            text_color=SUBTEXT_COLOR,
            justify="left",
            wraplength=800,
            anchor="w"
        ).pack(fill="x", pady=(0, 20))

        # Screenshot Placeholder Card (A nice mockup blueprint layout)
        ctk.CTkLabel(
            self.content_scroll, text="SYSTEM DESK PREVIEW",
            font=make_font(10, "bold"),
            text_color="#64748B",
            anchor="w"
        ).pack(fill="x", pady=(0, 4))
        
        screenshot_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color="#1E293B",
            border_color="#2563EB",
            border_width=1.5,
            corner_radius=12,
            height=260
        )
        screenshot_card.pack(fill="x", pady=(0, 24))
        screenshot_card.pack_propagate(False)

        # Draw blueprint mock elements inside card
        inner_box = ctk.CTkFrame(screenshot_card, fg_color="transparent")
        inner_box.pack(fill="both", expand=True, padx=24, pady=20)

        # Mock top KPI grid
        kpi_grid = ctk.CTkFrame(inner_box, fg_color="transparent", height=60)
        kpi_grid.pack(fill="x", pady=(0, 20))
        kpi_grid.pack_propagate(False)

        for label, val in data["kpis"]:
            kpi_box = ctk.CTkFrame(kpi_grid, fg_color="#0F172A", border_color="#334155", border_width=1, corner_radius=6, width=220)
            kpi_box.pack(side="left", padx=(0, 15), fill="both", expand=True)
            kpi_lbl = ctk.CTkLabel(kpi_box, text=label, font=make_font(9), text_color=SUBTEXT_COLOR)
            kpi_lbl.pack(pady=(6, 2))
            kpi_val = ctk.CTkLabel(kpi_box, text=val, font=make_font(14, "bold"), text_color=TEXT_COLOR)
            kpi_val.pack()

        # Mock body graphics (diagram simulation)
        graphics_box = ctk.CTkFrame(inner_box, fg_color="#0F172A", border_color="#2563EB", border_width=1, corner_radius=8)
        graphics_box.pack(fill="both", expand=True)

        ctk.CTkLabel(
            graphics_box,
            text=f"📊 [ FinGuard {data['title']} Interactive Display Blueprint ]",
            font=make_font(11, "bold"),
            text_color="#2563EB"
        ).place(relx=0.5, rely=0.4, anchor="center")

        ctk.CTkLabel(
            graphics_box,
            text="Query Analyzer Active  ·  Audit Ledger Loaded  ·  Risk Engine Online",
            font=make_font(9),
            text_color="#475569"
        ).place(relx=0.5, rely=0.65, anchor="center")

        # Two Column Layout for Tips, Best Practices, Cases
        detail_grid = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        detail_grid.pack(fill="x", pady=10)

        # Left Column (Tips & Best Practices)
        left_col = ctk.CTkFrame(detail_grid, fg_color="transparent", width=380)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # Tips Panel
        ctk.CTkLabel(left_col, text="💡 Quick Tip", font=make_font(12, "bold"), text_color="#F59E0B", anchor="w").pack(fill="x", pady=(0, 4))
        tips_box = ctk.CTkFrame(left_col, fg_color="#1E293B", corner_radius=8)
        tips_box.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(tips_box, text=data["tips"], font=make_font(11), text_color=TEXT_COLOR, justify="left", wraplength=360).pack(padx=14, pady=10, anchor="w")

        # Best Practices Panel
        ctk.CTkLabel(left_col, text="🛡️ Best Practice", font=make_font(12, "bold"), text_color="#10B981", anchor="w").pack(fill="x", pady=(0, 4))
        pract_box = ctk.CTkFrame(left_col, fg_color="#1E293B", corner_radius=8)
        pract_box.pack(fill="x")
        ctk.CTkLabel(pract_box, text=data["practices"], font=make_font(11), text_color=TEXT_COLOR, justify="left", wraplength=360).pack(padx=14, pady=10, anchor="w")

        # Right Column (Common Use Cases)
        right_col = ctk.CTkFrame(detail_grid, fg_color="transparent", width=380)
        right_col.pack(side="right", fill="both", expand=True, padx=(15, 0))

        ctk.CTkLabel(right_col, text="🔑 Common Use Cases", font=make_font(12, "bold"), text_color=PRIMARY_COLOR, anchor="w").pack(fill="x", pady=(0, 4))
        cases_box = ctk.CTkFrame(right_col, fg_color="#1E293B", corner_radius=8)
        cases_box.pack(fill="both", expand=True)
        ctk.CTkLabel(cases_box, text=data["cases"], font=make_font(11), text_color=TEXT_COLOR, justify="left", wraplength=360).pack(padx=14, pady=14, anchor="w")

    def _render_final_page(self) -> None:
        # Centered celebration layout
        container = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        container.pack(pady=100)

        # Checkmark Icon
        ctk.CTkLabel(
            container, text="🎉",
            font=make_font(72),
            text_color="#10B981"
        ).pack(pady=10)

        # Title
        ctk.CTkLabel(
            container, text="You're All Set!",
            font=make_font(28, "bold"),
            text_color=TEXT_COLOR
        ).pack()

        # Message
        ctk.CTkLabel(
            container,
            text="FinGuard is ready.\nExplore the platform with confidence.",
            font=make_font(13),
            text_color=TEXT_COLOR,
            justify="center"
        ).pack(pady=(16, 32))

        # Close/Finish button
        ctk.CTkButton(
            container, text="Go To Dashboard",
            width=280, height=38,
            fg_color=SUCCESS_COLOR,
            text_color=TEXT_COLOR,
            hover_color="#059669",
            font=make_font(12, "bold"),
            command=self.close
        ).pack()

    def _filter_sidebar(self, *args) -> None:
        query = self.search_val.get().lower().strip()
        for idx, btn in self.sidebar_buttons.items():
            if idx < len(self.pages_data):
                page = self.pages_data[idx]
                match = query in page["title"].lower() or query in page["desc"].lower()
                if match or not query:
                    btn.pack(fill="x", pady=2, padx=6)
                else:
                    btn.pack_forget()
            else:
                # Finish page button
                if query in "you're all set! finish" or not query:
                    btn.pack(fill="x", pady=2, padx=6)
                else:
                    btn.pack_forget()

    def next_page(self) -> None:
        total_pages = len(self.pages_data) + 1
        if self.current_page == total_pages - 1:
            self.close()
        else:
            self.show_page(self.current_page + 1)

    def prev_page(self) -> None:
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def close(self) -> None:
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()


class HelpDropdown(ctk.CTkToplevel):
    """
    Modeless popup contextual Help menu list.
    """
    def __init__(self, parent, guide_cb, start_cb, keys_cb, about_cb, docs_cb):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(fg_color="#000001")
        self.wm_attributes("-transparentcolor", "#000001")
        self.attributes("-topmost", True)

        outer = ctk.CTkFrame(
            self,
            fg_color="#1E293B",
            border_color="#2563EB",
            border_width=1.5,
            corner_radius=10,
            width=180,
            height=184
        )
        outer.pack(fill="both", expand=True)
        outer.pack_propagate(False)

        items = [
            ("User Guide", guide_cb),
            ("Getting Started", start_cb),
            ("Keyboard Shortcuts", keys_cb),
            ("About FinGuard", about_cb),
            ("Documentation", docs_cb)
        ]

        for label, cmd in items:
            btn = ctk.CTkButton(
                outer, text=label,
                anchor="w",
                font=make_font(11),
                text_color=TEXT_COLOR,
                fg_color="transparent",
                hover_color="#334155",
                corner_radius=6,
                height=30,
                command=lambda c=cmd: [self.destroy(), c()]
            )
            btn.pack(fill="x", padx=6, pady=2)

        # Self-destruct popup if focus shifts away
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.after(50, lambda: self.focus_set())
