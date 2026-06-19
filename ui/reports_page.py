import os
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox, filedialog

from ui.widgets.cards  import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BUTTON,
    SPACE_XS, SPACE_S, SPACE_M, SPACE_L, SPACE_XL, format_inr, BasePage
)
from reports.report_generator import ReportGenerator


class ReportsPage(BasePage):
    """Operations Reporting & CSV Export page subclassing standardized BasePage."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Compliance Reporting & Exports", has_right_panel=True)
        self.generator = ReportGenerator()
        self._period   = "daily"

        # ── 1. Toolbar (Period Segmented Button) ──
        ctk.CTkLabel(self.toolbar, text="Report Window:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack(side="left", padx=(SPACE_S, SPACE_XS))

        self._period_seg = ctk.CTkSegmentedButton(
            self.toolbar,
            values=["Daily  (24h)", "Weekly  (7d)", "Monthly  (30d)"],
            command=self._on_period_changed,
            fg_color="#0F172A",
            selected_color=PRIMARY_COLOR,
            selected_hover_color="#1D4ED8",
            unselected_color="#1E293B",
            unselected_hover_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            height=36
        )
        self._period_seg.set("Daily  (24h)")
        self._period_seg.pack(side="left", padx=4)

        # ── 2. Main Content (Metrics Cards & High-Risk Table) ──
        # Equal Height Metrics Grid
        self.grid_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.grid_container.pack(fill="x", pady=(0, SPACE_S))
        self.grid_container.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        self.grid_container.rowconfigure(0, weight=1)

        self._c_tx      = CardWidget(self.grid_container, "TX Count",      "—", "Total transactions")
        self._c_fraud_n = CardWidget(self.grid_container, "Fraud Count",   "—", "Declined events", DANGER_COLOR)
        self._c_fraud_r = CardWidget(self.grid_container, "Fraud Rate",    "—", "Percentage rate", DANGER_COLOR)
        self._c_volume  = CardWidget(self.grid_container, "Total Volume",  "—", "Sum processed")
        self._c_avg_tx  = CardWidget(self.grid_container, "Average Transaction Value", "—", "Average amount")
        self._c_alerts  = CardWidget(self.grid_container, "Alerts Opened", "—", "Security logs", WARNING_COLOR)

        for i, c in enumerate([self._c_tx, self._c_fraud_n, self._c_fraud_r,
                                self._c_volume, self._c_avg_tx, self._c_alerts]):
            c.grid(row=0, column=i, sticky="nsew", padx=4)

        # High-risk customer table below metrics
        table_label_row = ctk.CTkFrame(self.main_content, fg_color="transparent")
        table_label_row.pack(fill="x", pady=(SPACE_XS, 4))
        ctk.CTkLabel(table_label_row, text="🔴  Critical High-Risk Customers Report",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        self._risk_table = TableWidget(
            self.main_content,
            columns=["cust_id","name","email","score","tier"],
            headers=["ID","Name","Email","Risk Score","Tier"]
        )
        self._risk_table.pack(fill="both", expand=True)

        # ── 3. Right Panel (CSV Export Desk) ──
        self._build_export_panel(self.right_panel)

        self._set_period("daily")

    def _build_export_panel(self, parent) -> None:
        ctk.CTkLabel(parent, text="Data Export Desk",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))

        ctk.CTkLabel(parent,
                     text="Download ledger tables as standard\nspreadsheet CSV exports.",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                     text_color=SUBTEXT_COLOR, justify="left").pack(anchor="w", padx=SPACE_S, pady=(0, SPACE_S))

        ctk.CTkFrame(parent, fg_color="#2D3748", height=1).pack(fill="x", padx=SPACE_S, pady=(0, SPACE_S))

        ctk.CTkLabel(parent, text="Select Table to Export:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(0, SPACE_XS))

        self._export_var = ctk.StringVar(value="TRANSACTIONS")
        options = [
            ("Transactions Log",   "TRANSACTIONS"),
            ("Alerts Queue Log",   "ALERTS"),
            ("Cases Dossier Log",  "CASES"),
        ]
        for text, val in options:
            rb_frame = ctk.CTkFrame(parent, fg_color="transparent", height=36)
            rb_frame.pack(fill="x", padx=SPACE_S, pady=3)

            dot = ctk.CTkRadioButton(
                rb_frame, text=text, variable=self._export_var, value=val,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=TEXT_COLOR,
                fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
                border_color="#334155"
            )
            dot.pack(anchor="w")

        ctk.CTkButton(
            parent, text="⬇  Generate & Export CSV",
            height=40, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            command=self._export_csv
        ).pack(fill="x", padx=SPACE_S, pady=(SPACE_M, 0))

        self._export_status = ctk.CTkLabel(parent, text="",
                                            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                            text_color=SUBTEXT_COLOR)
        self._export_status.pack(padx=SPACE_S, pady=(SPACE_XS, SPACE_S))

    def _on_period_changed(self, value: str) -> None:
        if "Weekly" in value:
            self._set_period("weekly")
        elif "Monthly" in value:
            self._set_period("monthly")
        else:
            self._set_period("daily")

    # ── Data Loading ──────────────────────────────────────────────────────

    def _set_period(self, period: str) -> None:
        self._period = period
        threading.Thread(target=self._load_worker, args=(period,), daemon=True).start()

    def _load_worker(self, period: str) -> None:
        try:
            if period == "weekly":
                stats = self.generator.generate_weekly_report()
            elif period == "monthly":
                stats = self.generator.generate_monthly_report()
            else:
                stats = self.generator.generate_daily_report()
            risk_cust = self.generator.generate_high_risk_customer_report()
            self.after(0, self._update_ui, stats, risk_cust)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Reporting Error",
                                                       f"Failed to compile report: {e}"))

    def _update_ui(self, stats: Dict, risk_cust: List[Dict]) -> None:
        self._c_tx.update_value(f"{stats['total_transactions']:,}")
        self._c_fraud_n.update_value(str(stats["fraud_count"]))
        self._c_fraud_r.update_value(f"{stats['fraud_rate_percentage']:.2f}%")
        self._c_volume.update_value(format_inr(stats['total_transaction_amount']))
        self._c_avg_tx.update_value(format_inr(stats['average_transaction_amount']))
        self._c_alerts.update_value(str(stats["alerts_generated"]))

        self._risk_table.clear()
        for c in risk_cust:
            self._risk_table.insert_row([
                c["customer_id"], c["customer_name"], c["email"],
                f"{c['risk_score']}/100", c["risk_tier"]
            ])

    # ── CSV Export ────────────────────────────────────────────────────────

    def _export_csv(self) -> None:
        entity  = self._export_var.get()
        default = f"finguard_{entity.lower()}_export.csv"
        path = filedialog.asksaveasfilename(
            initialfile=default,
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not path:
            return
        self._export_status.configure(text="⏳  Generating export…", text_color=SUBTEXT_COLOR)
        threading.Thread(target=self._export_worker,
                         args=(entity, path), daemon=True).start()

    def _export_worker(self, entity: str, path: str) -> None:
        try:
            csv_data = self.generator.generate_csv_export(entity)
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_data)
            self.after(0, lambda: self._export_status.configure(
                text=f"✅  Exported to {os.path.basename(path)}",
                text_color=SUCCESS_COLOR
            ))
        except Exception as e:
            self.after(0, lambda: (
                self._export_status.configure(text=f"⚠  Export failed", text_color=DANGER_COLOR),
                messagebox.showerror("Export Failed", str(e))
            ))
