"""
FinGuard UI – Main Window & Splash Screen
CustomTkinter root window replacing the Tkinter MainWindow.
Backward-compatible: same class names and constructor signatures.
"""
import customtkinter as ctk
from typing import Dict
from ui.widgets.theme import (
    BG_COLOR, SIDEBAR_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, FONT_FAMILY, setup_theme
)
from ui.widgets.sidebar import SidebarMenu

# Page imports
from ui.dashboard_page    import DashboardPage
from ui.customer_page     import CustomerPage
from ui.transaction_page  import TransactionPage
from ui.fraud_page        import FraudPage
from ui.alerts_page       import AlertsPage
from ui.cases_page        import CasesPage
from ui.investigation_page import InvestigationPage
from ui.analytics_page    import AnalyticsPage
from ui.reports_page      import ReportsPage
from ui.simulator_page    import SimulatorPage

# ── Page title mapping ────────────────────────────────────────────────────────
PAGE_TITLES = {
    "dashboard":    "System Operations & Fraud Dashboard",
    "customers":    "Customer KYC & Profiles Desk",
    "transactions": "Transactional Event Ledger",
    "fraud":        "Live Fraud Detection Analyzer",
    "alerts":       "Risk Security Alerts Queue",
    "cases":        "Investigation Case Board",
    "investigation":"Customer Security Dossier",
    "analytics":    "Threat Intelligence Analytics",
    "reports":      "Compliance Reporting & Exports",
    "simulator":    "Transaction Stream Simulator Console",
}


# ── Splash Screen ─────────────────────────────────────────────────────────────

class SplashScreen(ctk.CTkToplevel):
    """
    Borderless animated splash screen shown on startup.
    Fades progress through 4 loading stages then reveals main window.
    """
    TASKS = [
        ("Establishing secure database link…",      22),
        ("Loading analytical modules & filters…",   48),
        ("Spawning fraud detection workers…",        76),
        ("FinGuard platform ready.",                100),
    ]

    def __init__(self, root: "MainWindow") -> None:
        super().__init__(root)
        self.main_win = root
        self.main_win.withdraw()   # hide main window while splash shows

        self.overrideredirect(True)
        self.configure(fg_color=BG_COLOR)
        self.attributes("-topmost", True)

        # Force idle tasks to update to ensure scaling and winfo metrics are correct
        self.update_idletasks()
        scaling = self._get_window_scaling()

        W, H = 540, 340
        # Convert physical screen width/height to scaled coordinate space
        sw = int(self.winfo_screenwidth() / scaling)
        sh = int(self.winfo_screenheight() / scaling)

        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H) // 2)
        self.geometry(f"{W}x{H}+{x}+{y}")

        self._build_ui()
        self._task_idx = 0
        self.after(300, self._advance)

    def _build_ui(self) -> None:
        # Outer glow border
        outer = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=16,
                             border_width=1, border_color=PRIMARY_COLOR)
        outer.pack(fill="both", expand=True, padx=2, pady=2)

        # Logo
        ctk.CTkLabel(
            outer, text="🛡️",
            font=ctk.CTkFont(family=FONT_FAMILY, size=54),
            text_color=PRIMARY_COLOR
        ).pack(pady=(40, 0))

        # Brand title
        ctk.CTkLabel(
            outer, text="FinGuard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=30, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(pady=(6, 0))

        # Tagline
        ctk.CTkLabel(
            outer,
            text="Intelligent Financial Fraud & Risk Monitoring Platform",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR
        ).pack(pady=(4, 24))

        # Progress bar
        self._progress = ctk.CTkProgressBar(
            outer, width=360, height=6,
            fg_color="#1E293B",
            progress_color=PRIMARY_COLOR,
            corner_radius=3
        )
        self._progress.set(0)
        self._progress.pack(pady=(0, 10))

        # Status label
        self._status_lbl = ctk.CTkLabel(
            outer,
            text="Initializing…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=SUBTEXT_COLOR
        )
        self._status_lbl.pack()

        # Version badge
        ctk.CTkLabel(
            outer,
            text="v3.0 · Enterprise Edition",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color="#475569"
        ).pack(side="bottom", pady=16)

    def _advance(self) -> None:
        if self._task_idx < len(self.TASKS):
            label, pct = self.TASKS[self._task_idx]
            self._status_lbl.configure(text=label)
            self._progress.set(pct / 100)
            self._task_idx += 1
            self.after(420, self._advance)
        else:
            self.after(200, self._complete)

    def _complete(self) -> None:
        self.main_win.deiconify()
        self.destroy()


# ── Main Window ───────────────────────────────────────────────────────────────

class MainWindow(ctk.CTk):
    """
    Primary application window. Hosts the sidebar and page container.
    """
    def __init__(self) -> None:
        # HiDPI awareness (Windows) - set before constructing the window
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        super().__init__()
        self.title("FinGuard Security Workspace")
        self.configure(fg_color=BG_COLOR)

        # Force idle tasks to update to ensure scaling and winfo metrics are correct
        self.update_idletasks()
        scaling = self._get_window_scaling()

        # Convert physical screen width/height to scaled coordinate space
        sw = int(self.winfo_screenwidth() / scaling)
        sh = int(self.winfo_screenheight() / scaling)

        # Default size in scaled coordinates
        W, H = 1600, 900
        
        # Scale window to fit screen size if screen is smaller than default W/H
        if sw < W:
            W = sw
        if sh < H:
            H = sh

        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H) // 2)
        self.geometry(f"{W}x{H}+{x}+{y}")
        self.minsize(min(1400, sw), min(800, sh))

        # Apply dark treeview styles
        setup_theme(self)

        # Page registry (lazy: constructed on first visit)
        self.pages: Dict[str, ctk.CTkFrame] = {}
        self._page_classes = {
            "dashboard":     DashboardPage,
            "customers":     CustomerPage,
            "transactions":  TransactionPage,
            "fraud":         FraudPage,
            "alerts":        AlertsPage,
            "cases":         CasesPage,
            "investigation": InvestigationPage,
            "analytics":     AnalyticsPage,
            "reports":       ReportsPage,
            "simulator":     SimulatorPage,
        }
        self.active_page_id: str = ""

        self._build_layout()
        self.switch_page("dashboard")

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=0, minsize=240)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ── Workspace (right side) ──────────────────────────────────────────
        self.workspace = ctk.CTkFrame(self, fg_color=BG_COLOR, corner_radius=0)
        self.workspace.grid(row=0, column=1, sticky="nsew")

        # Header bar
        self._build_header()

        # Page container
        self.container = ctk.CTkFrame(self.workspace, fg_color=BG_COLOR, corner_radius=0)
        self.container.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Sidebar ────────────────────────────────────────────────────────
        self.sidebar = SidebarMenu(self, select_callback=self.switch_page)
        self.sidebar.grid(row=0, column=0, sticky="nsew")

    def _build_header(self) -> None:
        header = ctk.CTkFrame(
            self.workspace,
            fg_color=SIDEBAR_COLOR, corner_radius=0,
            height=80,
            border_width=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)

        # Bottom border line
        ctk.CTkFrame(header, fg_color="#1F2937", height=1, corner_radius=0).pack(
            side="bottom", fill="x"
        )

        # Page title (left)
        self.header_title = ctk.CTkLabel(
            header,
            text="System Operations & Fraud Dashboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_COLOR,
            anchor="w"
        )
        self.header_title.pack(side="left", padx=24, pady=24)

        # Right cluster: date/time + analyst badge
        right_cluster = ctk.CTkFrame(header, fg_color="transparent")
        right_cluster.pack(side="right", padx=20)

        # Status dot + online label
        status_row = ctk.CTkFrame(right_cluster, fg_color="transparent")
        status_row.pack(anchor="e", pady=(8, 0))

        ctk.CTkFrame(status_row, fg_color=SUCCESS_COLOR,
                     width=8, height=8, corner_radius=4).pack(side="left", padx=(0, 5))
        ctk.CTkLabel(
            status_row, text="System Online",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=SUCCESS_COLOR
        ).pack(side="left")

        # Analyst name
        ctk.CTkLabel(
            right_cluster,
            text="👤  Senior Fraud Officer  ·  Lead Compliance",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=SUBTEXT_COLOR,
            anchor="e"
        ).pack(anchor="e", pady=(2, 8))

    def _get_page(self, page_id: str) -> ctk.CTkFrame:
        """Lazily construct and cache a page on first access."""
        if page_id not in self.pages:
            cls = self._page_classes[page_id]
            self.pages[page_id] = cls(self.container)
        return self.pages[page_id]

    def switch_page(self, page_id: str) -> None:
        """Show the target page, hide the current one. Pages are lazily created."""
        if page_id not in self._page_classes:
            return

        # Hide current
        if self.active_page_id and self.active_page_id in self.pages:
            self.pages[self.active_page_id].pack_forget()

        self.active_page_id = page_id
        page = self._get_page(page_id)
        page.pack(fill="both", expand=True)

        # Update header title
        self.header_title.configure(text=PAGE_TITLES.get(page_id, "FinGuard"))

        # Sync sidebar
        if hasattr(self, "sidebar") and self.sidebar.active_page != page_id:
            self.sidebar.select_page(page_id)

    def navigate_to_investigation(self, customer_id: int) -> None:
        """External routing: navigate to investigation page for a given customer."""
        inv_page: InvestigationPage = self._get_page("investigation")
        inv_page.load_customer(customer_id)
        self.switch_page("investigation")
        self.switch_page("investigation")
