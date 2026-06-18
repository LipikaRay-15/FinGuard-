import tkinter as tk
from tkinter import ttk
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.cards import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_CAPTION
)

# Backend imports
from database import DatabaseConnection
from services import CustomerService, AlertService, CaseService

# Optional Matplotlib imports
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class DashboardPage(ttk.Frame):
    """
    Dashboard page framing core statistics, risky customer summaries,
    and analytical chart widgets. Loads database metrics asynchronously.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.db = DatabaseConnection()

        # Page Header
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))
        
        self.title_lbl = ttk.Label(self.header_frame, text="Operations Dashboard", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")
        
        self.refresh_btn = ttk.Button(self.header_frame, text="🔄 Refresh", command=self.load_data)
        self.refresh_btn.pack(side="right")

        # Scrollable container
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        self.scroll_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.scroll_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas_win = self.canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_win, width=e.width))
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Loading Label
        self.loading_lbl = tk.Label(self.scroll_frame, text="Gathering system analytics...", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER)
        self.loading_lbl.pack(pady=40)

        # Build UI layout (initially hidden)
        self.content_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)
        self._build_layout()

        # Load data in background thread
        self.load_data()

    def _build_layout(self) -> None:
        # 1. Cards Grid Frame
        self.cards_frame = tk.Frame(self.content_frame, bg=BG_COLOR)
        self.cards_frame.pack(fill="x", pady=(0, 20))
        self.cards_frame.columnconfigure((0, 1, 2, 3, 4), weight=1, uniform="group1")

        self.card_cust = CardWidget(self.cards_frame, "TOTAL CUSTOMERS", "0", "Standard KYC profiles")
        self.card_cust.grid(row=0, column=0, padx=6, sticky="nsew")

        self.card_tx = CardWidget(self.cards_frame, "TOTAL TRANSACTIONS", "0", "Scanned in Event Store")
        self.card_tx.grid(row=0, column=1, padx=6, sticky="nsew")

        self.card_alert = CardWidget(self.cards_frame, "OPEN ALERTS", "0", "Pending review", trend_color=WARNING_COLOR)
        self.card_alert.grid(row=0, column=2, padx=6, sticky="nsew")

        self.card_case = CardWidget(self.cards_frame, "OPEN CASES", "0", "Assigned queue", trend_color=WARNING_COLOR)
        self.card_case.grid(row=0, column=3, padx=6, sticky="nsew")

        self.card_crit = CardWidget(self.cards_frame, "CRITICAL ALERTS", "0", "Action required", trend_color=DANGER_COLOR)
        self.card_crit.grid(row=0, column=4, padx=6, sticky="nsew")

        # 2. Charts and Lists Split Layout
        self.split_frame = tk.Frame(self.content_frame, bg=BG_COLOR)
        self.split_frame.pack(fill="both", expand=True)
        self.split_frame.columnconfigure(0, weight=3) # Left (Charts)
        self.split_frame.columnconfigure(1, weight=2) # Right (Risky Customers)

        # Left Column: Charts Container
        self.charts_frame = tk.Frame(self.split_frame, bg=BG_COLOR)
        self.charts_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Right Column: Risky Customers Container
        self.risky_frame = tk.Frame(self.split_frame, bg=CARD_COLOR, padx=16, pady=16)
        self.risky_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        risky_lbl = tk.Label(self.risky_frame, text="Top Risky Customers", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        risky_lbl.pack(anchor="w", pady=(0, 10))

        self.risky_table = TableWidget(
            self.risky_frame,
            columns=["customer_id", "name", "risk_score", "tier"],
            headers=["ID", "Name", "Risk Score", "Risk Tier"]
        )
        self.risky_table.pack(fill="both", expand=True)

    def load_data(self) -> None:
        """
        Launches async query worker.
        """
        self.loading_lbl.pack(pady=40)
        self.content_frame.pack_forget()
        
        thread = threading.Thread(target=self._query_database_worker, daemon=True)
        thread.start()

    def _query_database_worker(self) -> None:
        try:
            # 1. Total statistics
            c_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM customers")["cnt"]
            t_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions")["cnt"]
            a_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts WHERE status = 'OPEN'")["cnt"]
            case_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM cases WHERE status = 'OPEN'")["cnt"]
            crit_count = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts WHERE severity = 'CRITICAL'")["cnt"]
            
            # 2. Risky Customers
            risky_rows = self.db.fetch_all(
                "SELECT customer_id, customer_name, current_risk_score, risk_tier "
                "FROM v_customer_risk_summary WHERE current_risk_score > 0 "
                "ORDER BY current_risk_score DESC LIMIT 5"
            )

            # 3. Chart statistics (Rules triggered and severities)
            rules_triggered = self.db.fetch_all(
                "SELECT rule_name, COUNT(*) as cnt FROM rule_execution_logs WHERE triggered = TRUE GROUP BY rule_name"
            )
            
            self.after(0, self._update_ui, c_count, t_count, a_count, case_count, crit_count, risky_rows, rules_triggered)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_ui(self, c_count, t_count, a_count, case_count, crit_count, risky_rows, rules_triggered) -> None:
        self.loading_lbl.pack_forget()
        self.content_frame.pack(fill="both", expand=True)

        self.card_cust.update_value(str(c_count))
        self.card_tx.update_value(str(t_count))
        self.card_alert.update_value(str(a_count))
        self.card_case.update_value(str(case_count))
        self.card_crit.update_value(str(crit_count))

        self.risky_table.clear()
        for r in risky_rows:
            self.risky_table.insert_row([
                r["customer_id"],
                r["customer_name"],
                f"{r['current_risk_score']}/100",
                r["risk_tier"]
            ])

        # Render Charts
        self._render_charts(rules_triggered, crit_count, a_count)

    def _show_error(self, err_msg: str) -> None:
        self.loading_lbl.configure(text=f"Failed to load dashboard metrics: {err_msg}", fg=DANGER_COLOR)

    def _render_charts(self, rules_triggered: List[Dict[str, Any]], crit_count: int, open_alerts: int) -> None:
        # Clear old chart frames
        for child in self.charts_frame.winfo_children():
            child.destroy()

        if HAS_MATPLOTLIB:
            # Set stylesheet configs
            fig = Figure(figsize=(5, 3.5), facecolor=BG_COLOR)
            ax = fig.add_subplot(111)
            ax.set_facecolor(CARD_COLOR)
            
            # Prepare rule metrics
            names = [r["rule_name"][:15] + ".." if len(r["rule_name"]) > 15 else r["rule_name"] for r in rules_triggered]
            counts = [r["cnt"] for r in rules_triggered]
            
            if not counts:
                names = ["No Rules Hit"]
                counts = [0]
                
            bars = ax.barh(names, counts, color=PRIMARY_COLOR, edgecolor="none", height=0.5)
            ax.tick_params(colors=TEXT_COLOR, labelsize=8)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color(SUBTEXT_COLOR)
            ax.spines['bottom'].set_color(SUBTEXT_COLOR)
            ax.set_title("Triggered Fraud Rules Frequency", color=TEXT_COLOR, fontsize=10, weight="bold")
            
            # Add values inside bars
            for bar in bars:
                width = bar.get_width()
                ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{int(width)}', 
                        va='center', ha='left', color=TEXT_COLOR, fontsize=8)

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            # Native Canvas bar chart fallback
            fallback_lbl = tk.Label(self.charts_frame, text="Analytics Visuals (Canvas Fallback)", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER)
            fallback_lbl.pack(anchor="w", pady=(0, 10))

            chart_canvas = tk.Canvas(self.charts_frame, bg=CARD_COLOR, height=200, highlightthickness=0, bd=0)
            chart_canvas.pack(fill="both", expand=True)

            # Draw simple bar metrics
            y_offset = 30
            for idx, r in enumerate(rules_triggered or [{"rule_name": "Mock Rule Alpha", "cnt": 15}, {"rule_name": "Mock Rule Beta", "cnt": 8}]):
                chart_canvas.create_text(15, y_offset, text=r["rule_name"][:18], fill=TEXT_COLOR, anchor="w", font=FONT_CAPTION)
                # Draw bar
                width = min(200, r["cnt"] * 10)
                chart_canvas.create_rectangle(150, y_offset - 8, 150 + width, y_offset + 8, fill=PRIMARY_COLOR, outline="")
                chart_canvas.create_text(150 + width + 10, y_offset, text=str(r["cnt"]), fill=TEXT_COLOR, anchor="w", font=FONT_CAPTION)
                y_offset += 35
