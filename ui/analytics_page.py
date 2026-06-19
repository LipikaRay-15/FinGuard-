"""
FinGuard UI – Analytics Page
Threat intelligence: KPI cards, rules/cities tables, Matplotlib charts.
"""
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.cards  import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, format_inr
)
from services import AnalyticsService

try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class AnalyticsPage(ctk.CTkFrame):
    """System Analytics & Threat Intelligence page."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.service = AnalyticsService()

        # ── Header ────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=52)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Threat Intelligence Analytics",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")
        ctk.CTkButton(hdr, text="⟳  Refresh", width=100, height=32,
                      corner_radius=8, fg_color="#1E293B", hover_color="#334155",
                      text_color=TEXT_COLOR, font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                      command=self.load_analytics).pack(side="right")

        # ── Scrollable body ────────────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=BG_COLOR, scrollbar_button_color="#334155"
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=12)

        self._loading = ctk.CTkLabel(
            self._scroll, text="⏳  Aggregating threat metrics…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=SUBTEXT_COLOR)
        self._loading.pack(pady=60)

        self._content = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._build_layout()
        self.load_analytics()

    def _build_layout(self) -> None:
        # ── Row 1: 4 KPI Cards ──────────────────────────────────────────────
        cards_row = ctk.CTkFrame(self._content, fg_color="transparent")
        cards_row.pack(fill="x", pady=(0, 16))
        cards_row.columnconfigure((0, 1, 2, 3), weight=1)

        self._c_fraud_rate = CardWidget(cards_row, "Fraud Decline Rate",    "0.00%", "Decline ratio", DANGER_COLOR)
        self._c_fp_ratio   = CardWidget(cards_row, "False Positive Rate",   "0.00%", "Override ratio", SUCCESS_COLOR)
        self._c_avg_tx     = CardWidget(cards_row, "Average Transaction Value",  "₹0", "Volume per ticket", PRIMARY_COLOR)
        self._c_res_time   = CardWidget(cards_row, "Avg Resolution Time",   "—", "Case close time", WARNING_COLOR)

        for i, c in enumerate([self._c_fraud_rate, self._c_fp_ratio, self._c_avg_tx, self._c_res_time]):
            c.grid(row=0, column=i, sticky="nsew", padx=6)

        # ── Row 2: Tables left, Charts right ─────────────────────────────
        split = ctk.CTkFrame(self._content, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=2)
        split.columnconfigure(1, weight=3)

        # Left: tables
        left = ctk.CTkFrame(split, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Rules table
        rules_panel = ctk.CTkFrame(left, fg_color=CARD_COLOR, corner_radius=12)
        rules_panel.pack(fill="both", expand=True, pady=(0, 12))
        ctk.CTkLabel(rules_panel, text="🔴  Most Triggered Rules",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))
        self._rules_table = TableWidget(rules_panel,
                                         columns=["rule","count"],
                                         headers=["Rule Name","Trigger Count"])
        self._rules_table.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        # Cities table
        cities_panel = ctk.CTkFrame(left, fg_color=CARD_COLOR, corner_radius=12)
        cities_panel.pack(fill="both", expand=True)
        ctk.CTkLabel(cities_panel, text="🌍  Risky Geographic Locations",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))
        self._cities_table = TableWidget(cities_panel,
                                          columns=["city","total","fraud"],
                                          headers=["City","Total Transactions","Decline Volume"])
        self._cities_table.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        # Right: charts
        self._charts_frame = ctk.CTkFrame(split, fg_color="transparent")
        self._charts_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

    # ── Data ──────────────────────────────────────────────────────────────

    def load_analytics(self) -> None:
        self._loading.pack(pady=60)
        self._content.pack_forget()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self) -> None:
        try:
            data = self.service.get_system_analytics()
            self.after(0, self._update_ui, data)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _update_ui(self, data: Dict) -> None:
        self._loading.pack_forget()
        self._content.pack(fill="both", expand=True)

        self._c_fraud_rate.update_value(f"{data['fraud_percentage']:.2f}%")
        self._c_fp_ratio.update_value(f"{data['false_positive_ratio']:.2f}%")
        self._c_avg_tx.update_value(format_inr(data['average_transaction_amount']))

        rt = data["case_resolution_time"]
        res_str = (f"{rt/3600:.1f} hrs" if rt >= 3600 else
                   f"{rt/60:.1f} mins"  if rt >= 60 else
                   f"{rt:.1f} secs")
        self._c_res_time.update_value(res_str)

        self._rules_table.clear()
        for r in data["most_triggered_rules"]:
            self._rules_table.insert_row([r["rule_name"], r["trigger_count"]])

        self._cities_table.clear()
        for c in data["top_risky_cities"]:
            self._cities_table.insert_row([c["city"], c["total_count"], c["fraud_count"]])

        self._render_charts(data)

    def _render_charts(self, data: Dict) -> None:
        for w in self._charts_frame.winfo_children():
            w.destroy()

        if HAS_MATPLOTLIB:
            fig = Figure(figsize=(6, 6), facecolor=BG_COLOR, dpi=92)

            # ── Subplot 1: Hourly line chart ─────────────────────────────
            ax1 = fig.add_subplot(211)
            ax1.set_facecolor(CARD_COLOR)
            hours  = [h["hour"] for h in data["hourly_trends"]]
            counts = [h["transaction_count"] for h in data["hourly_trends"]]
            ax1.plot(hours, counts, color=PRIMARY_COLOR, linewidth=2,
                     marker="o", markersize=3)
            ax1.fill_between(hours, counts, color=PRIMARY_COLOR, alpha=0.12)
            ax1.tick_params(colors=TEXT_COLOR, labelsize=8)
            ax1.spines["top"].set_visible(False)
            ax1.spines["right"].set_visible(False)
            ax1.spines["left"].set_color("#334155")
            ax1.spines["bottom"].set_color("#334155")
            ax1.set_title("Hourly Scan Volume (24h)", color=TEXT_COLOR,
                          fontsize=10, weight="bold")
            ax1.set_xlabel("Hour of Day", color=SUBTEXT_COLOR, fontsize=8)
            ax1.set_ylabel("TX Count", color=SUBTEXT_COLOR, fontsize=8)

            # ── Subplot 2: Alert severity donut ──────────────────────────
            ax2 = fig.add_subplot(212)
            ax2.set_facecolor(CARD_COLOR)
            sev_dist = data["alert_distribution"].get("severity_distribution", {})
            labels = list(sev_dist.keys())
            sizes  = list(sev_dist.values())
            if not sizes:
                labels, sizes = ["No Alerts"], [1]
                colors = [CARD_COLOR]
            else:
                color_map = {"CRITICAL": DANGER_COLOR, "HIGH": "#F97316",
                             "MEDIUM": WARNING_COLOR, "LOW": SUCCESS_COLOR}
                colors = [color_map.get(l, SUBTEXT_COLOR) for l in labels]

            wedges, texts, autos = ax2.pie(
                sizes, labels=labels, autopct="%1.1f%%",
                colors=colors, startangle=90,
                textprops=dict(color=TEXT_COLOR, size=8),
                wedgeprops=dict(edgecolor=BG_COLOR, width=0.55)
            )
            ax2.set_title("Alert Severity Distribution", color=TEXT_COLOR,
                          fontsize=10, weight="bold")

            fig.tight_layout(pad=1.6)
            canvas = FigureCanvasTkAgg(fig, master=self._charts_frame)
            canvas.draw()
            canvas.get_tk_widget().configure(bg=BG_COLOR)
            canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            ctk.CTkLabel(self._charts_frame,
                         text="Matplotlib not available.\nInstall matplotlib to see charts.",
                         font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                         text_color=SUBTEXT_COLOR, justify="center").pack(pady=40)

    def _show_error(self, msg: str) -> None:
        self._loading.configure(text=f"⚠  Failed to load analytics: {msg}",
                                text_color=DANGER_COLOR)
