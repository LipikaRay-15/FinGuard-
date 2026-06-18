import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import threading
import os
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
from reports.report_generator import ReportGenerator

class ReportsPage(ttk.Frame):
    """
    Operations Reporting & CSV Export page.
    Compiles daily/weekly/monthly aggregated statistics, displays
    lists of high-risk customers, and triggers file-write exports to local storage.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.generator = ReportGenerator()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Operations Reporting & Exports", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

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

        # Layout UI parts
        self._build_layout()

        # Load default report (Daily)
        self.set_active_report("daily")

    def _build_layout(self) -> None:
        # 1. Periodical Reports Selector Frame
        selector_frame = tk.Frame(self.scroll_frame, bg=CARD_COLOR, padx=14, pady=10)
        selector_frame.pack(fill="x", pady=(0, 15))

        tk.Label(selector_frame, text="Operational Report Window:", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER).pack(side="left", padx=(0, 15))

        self.report_period_var = tk.StringVar(value="daily")
        
        for text, value in [("Daily Ops (24h)", "daily"), ("Weekly Summary (7d)", "weekly"), ("Monthly Digest (30d)", "monthly")]:
            rb = tk.Radiobutton(
                selector_frame,
                text=text,
                value=value,
                variable=self.report_period_var,
                bg=CARD_COLOR,
                fg=TEXT_COLOR,
                selectcolor=BG_COLOR,
                activebackground=CARD_COLOR,
                activeforeground=TEXT_COLOR,
                font=FONT_BODY,
                command=self._on_period_changed
            )
            rb.pack(side="left", padx=10)

        # 2. Performance Metrics Cards
        self.cards_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)
        self.cards_frame.pack(fill="x", pady=(0, 15))
        self.cards_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform="group_report")

        self.card_tx = CardWidget(self.cards_frame, "TX COUNT", "0", "Total transactions")
        self.card_tx.grid(row=0, column=0, padx=4, sticky="nsew")

        self.card_fraud_count = CardWidget(self.cards_frame, "FRAUD COUNT", "0", "Declined events", trend_color=DANGER_COLOR)
        self.card_fraud_count.grid(row=0, column=1, padx=4, sticky="nsew")

        self.card_fraud_rate = CardWidget(self.cards_frame, "FRAUD RATE", "0.00%", "Percentage rate", trend_color=DANGER_COLOR)
        self.card_fraud_rate.grid(row=0, column=2, padx=4, sticky="nsew")

        self.card_total_amount = CardWidget(self.cards_frame, "TOTAL VOLUME", "$0.00", "Sum processed")
        self.card_total_amount.grid(row=0, column=3, padx=4, sticky="nsew")

        self.card_avg_amount = CardWidget(self.cards_frame, "AVG TX TICKET", "$0.00", "Average volume")
        self.card_avg_amount.grid(row=0, column=4, padx=4, sticky="nsew")

        self.card_alerts = CardWidget(self.cards_frame, "ALERTS OPENED", "0", "Security logs created", trend_color=WARNING_COLOR)
        self.card_alerts.grid(row=0, column=5, padx=4, sticky="nsew")

        # 3. Two column details section: Left (Threat reports), Right (Export logs)
        self.split_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)
        self.split_frame.pack(fill="both", expand=True)
        self.split_frame.columnconfigure(0, weight=4) # High Risk Lists
        self.split_frame.columnconfigure(1, weight=2) # CSV Exporter

        # Left: High Risk Customers List
        left_frame = tk.Frame(self.split_frame, bg=CARD_COLOR, padx=16, pady=16)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(left_frame, text="Critical High-Risk Customers Report", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER).pack(anchor="w", pady=(0, 10))

        self.risk_table = TableWidget(
            left_frame,
            columns=["customer_id", "name", "email", "risk_score", "tier"],
            headers=["ID", "Name", "Email", "Risk Score", "Risk Tier"]
        )
        self.risk_table.pack(fill="both", expand=True)

        # Right: CSV Export Console
        right_frame = tk.Frame(self.split_frame, bg=CARD_COLOR, padx=16, pady=16)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        tk.Label(right_frame, text="Data Export Desk", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER).pack(anchor="w", pady=(0, 15))
        tk.Label(right_frame, text="Download ledger tables as standard spreadsheet CSV logs.", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, wraplength=200, justify="left").pack(anchor="w", pady=(0, 15))

        tk.Label(right_frame, text="Select Table to Export:", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(0, 5))
        self.export_var = tk.StringVar(value="TRANSACTIONS")
        
        for text, val in [("Transactions Log", "TRANSACTIONS"), ("Alerts Queue Log", "ALERTS"), ("Cases Dossier Log", "CASES")]:
            rb = tk.Radiobutton(
                right_frame,
                text=text,
                value=val,
                variable=self.export_var,
                bg=CARD_COLOR,
                fg=TEXT_COLOR,
                selectcolor=BG_COLOR,
                activebackground=CARD_COLOR,
                activeforeground=TEXT_COLOR,
                font=FONT_BODY
            )
            rb.pack(anchor="w", pady=4)

        export_btn = ttk.Button(right_frame, text="📥 Generate & Export CSV", command=self._export_csv)
        export_btn.pack(fill="x", pady=(20, 0))

    def _on_period_changed(self) -> None:
        period = self.report_period_var.get()
        self.set_active_report(period)

    def set_active_report(self, period: str) -> None:
        # Load report in background
        threading.Thread(target=self._load_report_worker, args=(period,), daemon=True).start()

    def _load_report_worker(self, period: str) -> None:
        try:
            # 1. Fetch Boundary statistics
            if period == "weekly":
                stats = self.generator.generate_weekly_report()
            elif period == "monthly":
                stats = self.generator.generate_monthly_report()
            else:
                stats = self.generator.generate_daily_report()

            # 2. Fetch High Risk Customers
            risk_cust = self.generator.generate_high_risk_customer_report()

            self.after(0, self._update_ui, stats, risk_cust)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Reporting Error", f"Failed to compile reports: {e}"))

    def _update_ui(self, stats: Dict[str, Any], risk_cust: List[Dict[str, Any]]) -> None:
        # Update metrics cards
        self.card_tx.update_value(str(stats["total_transactions"]))
        self.card_fraud_count.update_value(str(stats["fraud_count"]))
        self.card_fraud_rate.update_value(f"{stats['fraud_rate_percentage']:.2f}%")
        self.card_total_amount.update_value(f"${stats['total_transaction_amount']:,.2f}")
        self.card_avg_amount.update_value(f"${stats['average_transaction_amount']:,.2f}")
        self.card_alerts.update_value(str(stats["alerts_generated"]))

        # Populate high risk customers list
        self.risk_table.clear()
        for c in risk_cust:
            self.risk_table.insert_row([
                c["customer_id"],
                c["customer_name"],
                c["email"],
                f"{c['risk_score']}/100",
                c["risk_tier"]
            ])

    def _export_csv(self) -> None:
        entity = self.export_var.get()
        
        # Save file dialog
        default_name = f"finguard_{entity.lower()}_export.csv"
        file_path = filedialog.asksaveasfilename(
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        
        if not file_path:
            return

        threading.Thread(target=self._export_worker, args=(entity, file_path), daemon=True).start()

    def _export_worker(self, entity: str, file_path: str) -> None:
        try:
            csv_data = self.generator.generate_csv_export(entity)
            
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_data)

            self.after(0, lambda: messagebox.showinfo("Export Success", f"Successfully exported {entity.lower()} list to {os.path.basename(file_path)}."))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Export Failed", f"Failed to save CSV export file: {e}"))
