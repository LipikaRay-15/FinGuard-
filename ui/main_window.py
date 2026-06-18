import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

# Theme and Style configurations
from ui.widgets.theme import (
    setup_theme,
    BG_COLOR, CARD_COLOR, SIDEBAR_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Sidebar Menu Widget
from ui.widgets.sidebar import SidebarMenu

# Page Frames imports
from ui.dashboard_page import DashboardPage
from ui.customer_page import CustomerPage
from ui.transaction_page import TransactionPage
from ui.fraud_page import FraudPage
from ui.alerts_page import AlertsPage
from ui.cases_page import CasesPage
from ui.investigation_page import InvestigationPage
from ui.analytics_page import AnalyticsPage
from ui.reports_page import ReportsPage
from ui.simulator_page import SimulatorPage

class SplashScreen(tk.Toplevel):
    """
    Flat borderless loading splash screen. Resolves schema connections,
    seeds visual progress indicators, and exposes the primary workspace.
    """
    def __init__(self, root) -> None:
        super().__init__(root)
        self.root = root
        self.root.withdraw()  # Hide the main workspace window initially

        self.overrideredirect(True)
        self.configure(bg=BG_COLOR)

        # Center on screen
        width, height = 480, 280
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Draw UI
        self.logo_lbl = tk.Label(self, text="🛡️", bg=BG_COLOR, fg=PRIMARY_COLOR, font=("Segoe UI", 44))
        self.logo_lbl.pack(pady=(35, 5))

        self.title_lbl = tk.Label(self, text="FinGuard Platform", bg=BG_COLOR, fg=TEXT_COLOR, font=("Segoe UI", 18, "bold"))
        self.title_lbl.pack()

        self.sub_lbl = tk.Label(self, text="Enterprise Banking Fraud Monitoring & Analytics", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=("Segoe UI", 10))
        self.sub_lbl.pack(pady=(0, 25))

        self.status_lbl = tk.Label(self, text="Booting threat vectors database...", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=("Segoe UI", 9))
        self.status_lbl.pack(pady=(5, 5))

        # Progress style config
        self.progress = ttk.Progressbar(self, length=360, mode="determinate", style="Horizontal.TProgressbar")
        self.progress.pack()

        # Simple tasks pipeline simulation
        self.tasks = [
            ("Establishing secure SQL database link...", 25),
            ("Loading analytical modules and filters...", 50),
            ("Spawning fraud simulator workers...", 75),
            ("FinGuard workspace ready.", 100)
        ]
        self.task_idx = 0
        self._update_pipeline()

    def _update_pipeline(self) -> None:
        if self.task_idx < len(self.tasks):
            label_text, percentage = self.tasks[self.task_idx]
            self.status_lbl.configure(text=label_text)
            self.progress["value"] = percentage
            self.task_idx += 1
            self.after(400, self._update_pipeline)
        else:
            self.after(100, self._complete)

    def _complete(self) -> None:
        self.root.deiconify()  # Restore and show the main application window
        self.destroy()         # Clear and release the splash screen resources

class MainWindow(tk.Tk):
    """
    Main desktop window shell. Manages page switches, collates analyst profile cards,
    and bridges direct page navigation calls.
    """
    def __init__(self) -> None:
        super().__init__()
        self.title("FinGuard Security Workspace")
        self.configure(bg=BG_COLOR)

        # Set default sizing (1280x800) and center on desktop screen
        width, height = 1280, 800
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(1024, 720)

        # Setup ttk Styles
        setup_theme(self)

        # Store page frame instances
        self.pages: Dict[str, ttk.Frame] = {}
        self.active_page_id: str = ""

        # Layout Main Panels
        # Sidebar Menu
        self.sidebar = SidebarMenu(self, select_callback=self.switch_page)
        self.sidebar.pack(side="left", fill="y")

        # Workspace Area Container
        self.workspace_frame = tk.Frame(self, bg=BG_COLOR)
        self.workspace_frame.pack(side="right", fill="both", expand=True)

        # Header bar containing title and Analyst profile details
        self.header_bar = tk.Frame(self.workspace_frame, bg=SIDEBAR_COLOR, height=60)
        self.header_bar.pack_propagate(False)
        self.header_bar.pack(fill="x", side="top")

        # Dynamic Title in Header
        self.header_title = tk.Label(self.header_bar, text="Workspace Overview", bg=SIDEBAR_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.header_title.pack(side="left", padx=20)

        # Analyst Profile Card Widget
        self.profile_panel = tk.Frame(self.header_bar, bg=SIDEBAR_COLOR)
        self.profile_panel.pack(side="right", padx=20)

        self.prof_name = tk.Label(self.profile_panel, text="👤 Senior Fraud Officer", bg=SIDEBAR_COLOR, fg=TEXT_COLOR, font=FONT_BODY)
        self.prof_name.pack(anchor="e")

        self.prof_role = tk.Label(self.profile_panel, text="Role: Lead Compliance", bg=SIDEBAR_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION)
        self.prof_role.pack(anchor="e")

        # Container Frame for the active Page
        self.container = tk.Frame(self.workspace_frame, bg=BG_COLOR, padx=20, pady=15)
        self.container.pack(fill="both", expand=True)

        # Initialize all 10 views inside container
        self.pages["dashboard"] = DashboardPage(self.container)
        self.pages["customers"] = CustomerPage(self.container)
        self.pages["transactions"] = TransactionPage(self.container)
        self.pages["fraud"] = FraudPage(self.container)
        self.pages["alerts"] = AlertsPage(self.container)
        self.pages["cases"] = CasesPage(self.container)
        self.pages["investigation"] = InvestigationPage(self.container)
        self.pages["analytics"] = AnalyticsPage(self.container)
        self.pages["reports"] = ReportsPage(self.container)
        self.pages["simulator"] = SimulatorPage(self.container)

        # Default initialization page selection is dashboard
        self.switch_page("dashboard")

    def switch_page(self, page_id: str) -> None:
        """
        Lays out the target page frame inside the central container area,
        adjusts workspace header title details, and hides the old frame.
        """
        if page_id not in self.pages:
            return

        # Hide current page
        if self.active_page_id and self.active_page_id in self.pages:
            self.pages[self.active_page_id].pack_forget()

        # Show target page
        self.active_page_id = page_id
        target_page = self.pages[page_id]
        target_page.pack(fill="both", expand=True)

        # Update Header Title
        title_mapping = {
            "dashboard": "System Operations & Fraud Dashboard",
            "customers": "Customer KYC & Profiles Desk",
            "transactions": "Transactional Event Ledger",
            "fraud": "Live Fraud Detection Analyzer",
            "alerts": "Risk Security Alerts Queue",
            "cases": "Investigation Case Board",
            "investigation": "Customer Security Dossier",
            "analytics": "Threat Intelligence Analytics",
            "reports": "Compliance Reporting & Exports",
            "simulator": "Transaction Stream Simulator Console",
        }
        self.header_title.configure(text=title_mapping.get(page_id, "FinGuard Desktop Workspace"))

        # Synchronize collapsible sidebar selection highlights if triggered internally
        if self.sidebar.active_page != page_id:
            self.sidebar.select_page(page_id)

    def navigate_to_investigation(self, customer_id: int) -> None:
        """
        External routing endpoint. Allows other dashboard pages (like alerts, cases, or customers)
        to transition the view directly to the dossier of a target customer.
        """
        investigation_page: InvestigationPage = self.pages["investigation"]
        investigation_page.load_customer(customer_id)
        self.switch_page("investigation")
