import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.cards import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend imports
from services import AnalyticsService

# Optional Matplotlib imports
try:
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class AnalyticsPage(ttk.Frame):
    """
    Analytics and system threat intelligence page.
    Displays metrics cards, maps hourly trends, rules hits,
    and alert severity splits. Uses background threads to query database.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.service = AnalyticsService()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="System Analytics & Threat Intel", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        self.refresh_btn = ttk.Button(self.header_frame, text="🔄 Refresh", command=self.load_analytics)
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
        self.loading_lbl = tk.Label(self.scroll_frame, text="Aggregating threat metrics across tables...", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER)
        self.loading_lbl.pack(pady=40)

        # Content frame (Hidden while loading)
        self.content_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)
        self._build_layout()

        # Load initial values
        self.load_analytics()

    def _build_layout(self) -> None:
        # 1. Cards Grid
        self.cards_frame = tk.Frame(self.content_frame, bg=BG_COLOR)
        self.cards_frame.pack(fill="x", pady=(0, 20))
        self.cards_frame.columnconfigure((0, 1, 2, 3), weight=1, uniform="group_analytics")

        self.card_fraud_pct = CardWidget(self.cards_frame, "FRAUD DECLINE RATE", "0.00%", "Ratio of declines", trend_color=DANGER_COLOR)
        self.card_fraud_pct.grid(row=0, column=0, padx=6, sticky="nsew")

        self.card_fp_ratio = CardWidget(self.cards_frame, "FALSE POSITIVE RATE", "0.00%", "Alert overrides ratio", trend_color=SUCCESS_COLOR)
        self.card_fp_ratio.grid(row=0, column=1, padx=6, sticky="nsew")

        self.card_avg_val = CardWidget(self.cards_frame, "AVG TRANSACTION SIZE", "$0.00", "Volume per ticket")
        self.card_avg_val.grid(row=0, column=2, padx=6, sticky="nsew")

        self.card_res_time = CardWidget(self.cards_frame, "AVG RESOLUTION TIME", "0.0s", "Alert to close cycle time")
        self.card_res_time.grid(row=0, column=3, padx=6, sticky="nsew")

        # 2. Main split area: Left (tables), Right (charts)
        self.split_frame = tk.Frame(self.content_frame, bg=BG_COLOR)
        self.split_frame.pack(fill="both", expand=True)
        self.split_frame.columnconfigure(0, weight=3) # Left lists
        self.split_frame.columnconfigure(1, weight=3) # Right charts

        # Left Column: Lists Frame
        self.left_frame = tk.Frame(self.split_frame, bg=BG_COLOR)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Rules Hits List
        rules_container = tk.Frame(self.left_frame, bg=CARD_COLOR, padx=14, pady=14)
        rules_container.pack(fill="both", expand=True, pady=(0, 15))
        tk.Label(rules_container, text="Most Triggered Rules", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER).pack(anchor="w", pady=(0, 10))
        
        self.rules_table = TableWidget(
            rules_container,
            columns=["rule_name", "count"],
            headers=["Rule Name", "Trigger Count"]
        )
        self.rules_table.pack(fill="both", expand=True)

        # Risky Cities List
        cities_container = tk.Frame(self.left_frame, bg=CARD_COLOR, padx=14, pady=14)
        cities_container.pack(fill="both", expand=True)
        tk.Label(cities_container, text="Risky Geographic Locations", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER).pack(anchor="w", pady=(0, 10))

        self.cities_table = TableWidget(
            cities_container,
            columns=["city", "total", "fraud"],
            headers=["City", "Total Transactions", "Decline Volume"]
        )
        self.cities_table.pack(fill="both", expand=True)

        # Right Column: Charts Frame
        self.charts_frame = tk.Frame(self.split_frame, bg=BG_COLOR)
        self.charts_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

    def load_analytics(self) -> None:
        self.loading_lbl.pack(pady=40)
        self.content_frame.pack_forget()
        
        threading.Thread(target=self._query_worker, daemon=True).start()

    def _query_worker(self) -> None:
        try:
            data = self.service.get_system_analytics()
            self.after(0, self._update_ui, data)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _show_error(self, err_msg: str) -> None:
        self.loading_lbl.configure(text=f"Failed to load analytics metrics: {err_msg}", fg=DANGER_COLOR)

    def _update_ui(self, data: Dict[str, Any]) -> None:
        self.loading_lbl.pack_forget()
        self.content_frame.pack(fill="both", expand=True)

        # Update Cards
        self.card_fraud_pct.update_value(f"{data['fraud_percentage']:.2f}%")
        self.card_fp_ratio.update_value(f"{data['false_positive_ratio']:.2f}%")
        self.card_avg_val.update_value(f"${data['average_transaction_amount']:,.2f}")
        
        res_time = data["case_resolution_time"]
        if res_time >= 3600:
            res_str = f"{res_time/3600:.1f} hrs"
        elif res_time >= 60:
            res_str = f"{res_time/60:.1f} mins"
        else:
            res_str = f"{res_time:.1f} secs"
        self.card_res_time.update_value(res_str)

        # Update Rules hit Table
        self.rules_table.clear()
        for r in data["most_triggered_rules"]:
            self.rules_table.insert_row([r["rule_name"], r["trigger_count"]])

        # Update Cities Table
        self.cities_table.clear()
        for c in data["top_risky_cities"]:
            self.cities_table.insert_row([c["city"], c["total_count"], c["fraud_count"]])

        # Render Charts
        self._render_charts(data)

    def _render_charts(self, data: Dict[str, Any]) -> None:
        # Clear old chart frames
        for child in self.charts_frame.winfo_children():
            child.destroy()

        if HAS_MATPLOTLIB:
            # Layout hourly trends and severity charts using Matplotlib
            fig = Figure(figsize=(5, 5), facecolor=BG_COLOR)
            
            # Subplot 1: Hourly Trends
            ax1 = fig.add_subplot(211)
            ax1.set_facecolor(CARD_COLOR)
            
            hours = [h["hour"] for h in data["hourly_trends"]]
            counts = [h["transaction_count"] for h in data["hourly_trends"]]
            
            ax1.plot(hours, counts, color=PRIMARY_COLOR, marker="o", linewidth=2, markersize=4)
            ax1.fill_between(hours, counts, color=PRIMARY_COLOR, alpha=0.15)
            ax1.tick_params(colors=TEXT_COLOR, labelsize=8)
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            ax1.spines['left'].set_color(SUBTEXT_COLOR)
            ax1.spines['bottom'].set_color(SUBTEXT_COLOR)
            ax1.set_title("Hourly Scan Volume (24h)", color=TEXT_COLOR, fontsize=10, weight="bold")
            ax1.set_xlabel("Hour of Day", color=SUBTEXT_COLOR, fontsize=8)
            ax1.set_ylabel("Tx Count", color=SUBTEXT_COLOR, fontsize=8)

            # Subplot 2: Alert Severity pie chart
            ax2 = fig.add_subplot(212)
            ax2.set_facecolor(CARD_COLOR)
            
            severity_dist = data["alert_distribution"]["severity_distribution"]
            labels = list(severity_dist.keys())
            sizes = list(severity_dist.values())
            
            if not sizes:
                labels = ["No Alerts"]
                sizes = [1]
                colors = [CARD_COLOR]
            else:
                color_map = {
                    "CRITICAL": DANGER_COLOR,
                    "HIGH": WARNING_COLOR,
                    "MEDIUM": PRIMARY_COLOR,
                    "LOW": SUCCESS_COLOR
                }
                colors = [color_map.get(lbl, SUBTEXT_COLOR) for lbl in labels]
            
            wedges, texts, autotexts = ax2.pie(
                sizes,
                labels=labels,
                autopct='%1.1f%%',
                colors=colors,
                textprops=dict(color=TEXT_COLOR, size=8),
                wedgeprops=dict(edgecolor=BG_COLOR, width=0.6) # donut style
            )
            ax2.set_title("Alert Severities Split", color=TEXT_COLOR, fontsize=10, weight="bold")

            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=self.charts_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            # Fallback canvas charts
            fallback_container = tk.Frame(self.charts_frame, bg=CARD_COLOR, padx=14, pady=14)
            fallback_container.pack(fill="both", expand=True)
            
            tk.Label(fallback_container, text="Hourly Scan Volume (Canvas Fallback)", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(0, 5))
            chart_canvas = tk.Canvas(fallback_container, bg=BG_COLOR, height=180, highlightthickness=0, bd=0)
            chart_canvas.pack(fill="x", expand=True, pady=(0, 15))

            trends = data["hourly_trends"]
            max_val = max([h["transaction_count"] for h in trends]) if trends else 1
            if max_val == 0:
                max_val = 1
            
            # Draw simple bar chart of hour points
            width = 350
            height = 140
            dx = width / 24
            for h in trends:
                x = 10 + h["hour"] * dx
                val_h = (h["transaction_count"] / max_val) * height
                chart_canvas.create_rectangle(x, height - val_h + 10, x + dx - 2, height + 10, fill=PRIMARY_COLOR, outline="")
                if h["hour"] % 4 == 0:
                    chart_canvas.create_text(x + dx/2, height + 20, text=f"{h['hour']}h", fill=SUBTEXT_COLOR, font=FONT_CAPTION)

            # Severity Fallback
            tk.Label(fallback_container, text="Alert Severities Distribution", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(0, 5))
            sev_canvas = tk.Canvas(fallback_container, bg=BG_COLOR, height=120, highlightthickness=0, bd=0)
            sev_canvas.pack(fill="x", expand=True)

            sev_dict = data["alert_distribution"]["severity_distribution"]
            y_off = 15
            for idx, (severity, count) in enumerate(sev_dict.items()):
                color_map = {"CRITICAL": DANGER_COLOR, "HIGH": WARNING_COLOR, "MEDIUM": PRIMARY_COLOR, "LOW": SUCCESS_COLOR}
                color = color_map.get(severity, SUBTEXT_COLOR)
                sev_canvas.create_rectangle(15, y_off - 6, 25, y_off + 4, fill=color, outline="")
                sev_canvas.create_text(35, y_off, text=f"{severity}: {count} alerts", fill=TEXT_COLOR, anchor="w", font=FONT_BODY)
                y_off += 25
