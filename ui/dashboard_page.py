"""
FinGuard UI – Dashboard Page
Metric cards, top risky customers table, and Matplotlib charts.
"""
import threading
from typing import Any, Dict, List
import customtkinter as ctk

from ui.widgets.cards        import CardWidget
from ui.widgets.tables       import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY
)

from database import DatabaseConnection

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class DashboardPage(ctk.CTkFrame):
    """
    Landing dashboard: 5 KPI cards, risky customer list, and fraud rule frequency chart.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.db = DatabaseConnection()

        # ── Page Header ───────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=52)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        hdr.pack_propagate(False)

        ctk.CTkLabel(
            hdr, text="Operations Dashboard",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", anchor="w")

        self._refresh_btn = ctk.CTkButton(
            hdr, text="⟳  Refresh",
            width=110, height=34, corner_radius=8,
            fg_color="#1E293B", hover_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self.load_data
        )
        self._refresh_btn.pack(side="right", anchor="e")

        # ── Scrollable body ────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=BG_COLOR,
            scrollbar_button_color="#334155"
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=12)

        # Loading indicator
        self._loading = ctk.CTkLabel(
            self._scroll,
            text="⏳  Gathering system analytics…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=SUBTEXT_COLOR
        )
        self._loading.pack(pady=60)

        # Content frame (hidden while loading)
        self._content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._build_layout()
        self.load_data()

    def _build_layout(self) -> None:
        # ── Row 1: 5 KPI Cards ─────────────────────────────────────────────
        cards_row = ctk.CTkFrame(self._content, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, 16))

        self._card_cust  = CardWidget(cards_row, "Total Customers",    "—", "KYC profiles", PRIMARY_COLOR)
        self._card_tx    = CardWidget(cards_row, "Total Transactions",  "—", "Processed events", PRIMARY_COLOR)
        self._card_alert = CardWidget(cards_row, "Open Alerts",         "—", "Pending review", WARNING_COLOR)
        self._card_crit  = CardWidget(cards_row, "Critical Alerts",     "—", "Immediate action", DANGER_COLOR)
        self._card_case  = CardWidget(cards_row, "Open Cases",          "—", "Assigned queue", WARNING_COLOR)

        for i, card in enumerate([self._card_cust, self._card_tx, self._card_alert,
                                   self._card_crit, self._card_case]):
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            cards_row.columnconfigure(i, weight=1)

        # ── Row 2: Charts left, Risky Customers right ──────────────────────
        split = ctk.CTkFrame(self._content, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=3)
        split.columnconfigure(1, weight=2)

        # Charts panel
        self._charts_frame = ctk.CTkFrame(split, fg_color="transparent")
        self._charts_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Risky customers panel
        risk_panel = ctk.CTkFrame(split, fg_color=CARD_COLOR, corner_radius=12)
        risk_panel.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        risk_hdr = ctk.CTkFrame(risk_panel, fg_color="transparent", height=50)
        risk_hdr.pack(fill="x", padx=16, pady=(16, 0))
        risk_hdr.pack_propagate(False)

        ctk.CTkLabel(
            risk_hdr, text="🔥  Top Risky Customers",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left")

        self._risky_table = TableWidget(
            risk_panel,
            columns=["customer_id", "name", "risk_score", "tier"],
            headers=["ID", "Name", "Risk Score", "Tier"]
        )
        self._risky_table.pack(fill="both", expand=True, padx=8, pady=(8, 12))

        # ── Row 3: Recent Events section ───────────────────────────────────
        events_panel = ctk.CTkFrame(self._content, fg_color=CARD_COLOR, corner_radius=12)
        events_panel.pack(fill="x", pady=(16, 0))

        ctk.CTkLabel(
            events_panel, text="📋  Recent System Events",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=16, pady=(14, 4))

        self._events_table = TableWidget(
            events_panel,
            columns=["tx_id", "customer_id", "risk_score", "severity", "status", "time"],
            headers=["TX ID", "Customer ID", "Risk Score", "Severity", "Status", "Timestamp"]
        )
        self._events_table.pack(fill="x", padx=8, pady=(0, 12))

    def load_data(self) -> None:
        """Trigger async data reload."""
        self._loading.pack(pady=60)
        self._content.pack_forget()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            c_count    = self.db.fetch_one("SELECT COUNT(*) as cnt FROM customers")["cnt"]
            t_count    = self.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions")["cnt"]
            a_open     = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts WHERE status='OPEN'")["cnt"]
            a_crit     = self.db.fetch_one("SELECT COUNT(*) as cnt FROM alerts WHERE severity='CRITICAL'")["cnt"]
            case_open  = self.db.fetch_one("SELECT COUNT(*) as cnt FROM cases WHERE status='OPEN'")["cnt"]

            risky = self.db.fetch_all(
                "SELECT customer_id, customer_name, current_risk_score, risk_tier "
                "FROM v_customer_risk_summary WHERE current_risk_score > 0 "
                "ORDER BY current_risk_score DESC LIMIT 8"
            )
            rules = self.db.fetch_all(
                "SELECT rule_name, COUNT(*) as cnt FROM rule_execution_logs "
                "WHERE triggered = TRUE GROUP BY rule_name ORDER BY cnt DESC LIMIT 10"
            )
            recent = self.db.fetch_all(
                "SELECT a.transaction_id, a.customer_id, a.risk_score, a.severity, "
                "a.status, a.created_at FROM alerts a ORDER BY a.created_at DESC LIMIT 8"
            )
            self.after(0, self._update_ui, c_count, t_count, a_open, a_crit, case_open,
                       risky, rules, recent)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_ui(self, c_count, t_count, a_open, a_crit, case_open,
                   risky, rules, recent) -> None:
        self._loading.pack_forget()
        self._content.pack(fill="both", expand=True)

        self._card_cust.update_value(f"{c_count:,}")
        self._card_tx.update_value(f"{t_count:,}")
        self._card_alert.update_value(str(a_open))
        self._card_crit.update_value(str(a_crit))
        self._card_case.update_value(str(case_open))

        # Risky customers
        self._risky_table.clear()
        for r in risky:
            self._risky_table.insert_row([
                r["customer_id"], r["customer_name"],
                f"{r['current_risk_score']}/100", r["risk_tier"]
            ])

        # Recent events
        self._events_table.clear()
        for r in recent:
            self._events_table.insert_row([
                r["transaction_id"], r["customer_id"],
                f"{r['risk_score']}/100", r["severity"],
                r["status"], str(r["created_at"])[:16]
            ])

        self._render_charts(rules)

    def _render_charts(self, rules: List[Dict[str, Any]]) -> None:
        for w in self._charts_frame.winfo_children():
            w.destroy()

        panel = ctk.CTkFrame(self._charts_frame, fg_color=CARD_COLOR, corner_radius=12)
        panel.pack(fill="both", expand=True)

        ctk.CTkLabel(
            panel, text="📊  Triggered Fraud Rules Frequency",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=16, pady=(14, 4))

        if HAS_MATPLOTLIB and rules:
            fig = Figure(figsize=(6, 3.8), facecolor=CARD_COLOR, dpi=96)
            ax  = fig.add_subplot(111)
            ax.set_facecolor("#0F172A")

            names  = [r["rule_name"][:20] + "…" if len(r["rule_name"]) > 20
                      else r["rule_name"] for r in rules]
            counts = [r["cnt"] for r in rules]

            colors = [PRIMARY_COLOR] * len(counts)
            if counts:
                colors[0] = DANGER_COLOR   # Highlight most triggered

            bars = ax.barh(names, counts, color=colors, edgecolor="none", height=0.55)
            ax.tick_params(colors=TEXT_COLOR, labelsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color("#334155")
            ax.spines["bottom"].set_color("#334155")
            ax.invert_yaxis()

            for bar in bars:
                w_val = bar.get_width()
                if w_val > 0:
                    ax.text(w_val + 0.2, bar.get_y() + bar.get_height() / 2,
                            str(int(w_val)), va="center", ha="left",
                            color=TEXT_COLOR, fontsize=8)

            fig.tight_layout(pad=1.5)
            canvas = FigureCanvasTkAgg(fig, master=panel)
            canvas.draw()
            canvas.get_tk_widget().configure(bg=CARD_COLOR)
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=(0, 12))
        else:
            ctk.CTkLabel(
                panel,
                text="No rule execution data available yet.\nRun the Simulator to generate events.",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=SUBTEXT_COLOR, justify="center"
            ).pack(pady=40)

    def _show_error(self, msg: str) -> None:
        self._loading.configure(text=f"⚠  Failed to load dashboard: {msg}",
                                text_color=DANGER_COLOR)
