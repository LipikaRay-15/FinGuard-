import os
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk

from ui.widgets.cards import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, BasePage, SPACE_S, SPACE_XS, format_inr
)
from reports.report_generator import ReportGenerator


def get_tier_badge(tier: str) -> str:
    """Helper to convert tier levels to color badge icons."""
    t = (tier or "").upper()
    if t == "CRITICAL":
        return "🔴 CRITICAL"
    elif t == "HIGH":
        return "🟠 HIGH"
    elif t == "MEDIUM":
        return "🟡 MEDIUM"
    elif t == "LOW":
        return "🟢 LOW"
    return t


class ReportsPage(BasePage):
    """Operations Reporting & CSV Export page subclass."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Compliance Reporting & Exports", has_right_panel=True)
        self.generator = ReportGenerator()
        self._period = "daily"

        # Re-grid main_content and right_panel as separate vertical columns from BasePage layout
        self.main_content.grid_forget()
        self.right_panel.grid_forget()

        # Balance left report area (weight=1) and right export area (fixed 320px)
        self.content_container.columnconfigure(0, weight=1)
        self.content_container.columnconfigure(1, weight=0, minsize=320)
        self.content_container.rowconfigure(0, weight=1)

        self.main_content.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        # Define Reports.Treeview style matching Dashboard exactly
        style = ttk.Style()
        style.configure("Reports.Treeview",
            background=CARD_COLOR,
            fieldbackground=CARD_COLOR,
            foreground=TEXT_COLOR,
            rowheight=28,  # Row height reduced by ~20% (from default 36)
            font=("Segoe UI", 11),
            borderwidth=0,
            relief="flat",
        )
        style.configure("Reports.Treeview.Heading",
            background="#0F172A",
            foreground=SUBTEXT_COLOR,
            font=("Segoe UI", 12, "bold"),
            padding=8,
            borderwidth=0,
            relief="flat",
        )
        style.map("Reports.Treeview",
            background=[("selected", PRIMARY_COLOR), ("active", "#1E3A5F")],
            foreground=[("selected", TEXT_COLOR)],
        )

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

        # ── 2. Main Content (Metrics Cards Wrapping Grid & High-Risk Table) ──
        self.grid_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.grid_container.pack(fill="x", pady=(0, SPACE_S))

        self._c_tx      = CardWidget(self.grid_container, "TX Count",      "—", "Total transactions")
        self._c_fraud_n = CardWidget(self.grid_container, "Fraud Count",   "—", "Declined events", DANGER_COLOR)
        self._c_fraud_r = CardWidget(self.grid_container, "Fraud Rate",    "—", "Percentage rate", DANGER_COLOR)
        self._c_volume  = CardWidget(self.grid_container, "Total Volume",  "—", "Sum processed")
        self._c_avg_tx  = CardWidget(self.grid_container, "Average Transaction Value", "—", "Average amount")
        self._c_alerts  = CardWidget(self.grid_container, "Alerts Opened", "—", "Security logs", WARNING_COLOR)

        cards = [self._c_tx, self._c_fraud_n, self._c_fraud_r,
                 self._c_volume, self._c_avg_tx, self._c_alerts]

        for c in cards:
            c.configure(width=165, height=85)
            c.pack_propagate(False)
            children = c.winfo_children()
            if len(children) >= 2:
                content_frame = children[1]
                content_frame.pack_configure(pady=8)

        # Flow wrap KPI cards dynamically inside self.grid_container depending on available width
        def _wrap_cards(event=None) -> None:
            w = self.grid_container.winfo_width()
            if w <= 100:
                return
            cols = max(1, min(6, w // 173))
            for col_idx in range(6):
                if col_idx < cols:
                    self.grid_container.columnconfigure(col_idx, weight=1, minsize=165)
                else:
                    self.grid_container.columnconfigure(col_idx, weight=0, minsize=0)
            for idx, c in enumerate(cards):
                row = idx // cols
                col = idx % cols
                c.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

        self.grid_container.bind("<Configure>", _wrap_cards)

        # High-risk customer table label
        table_label_row = ctk.CTkFrame(self.main_content, fg_color="transparent")
        table_label_row.pack(fill="x", pady=(SPACE_XS, 4))
        ctk.CTkLabel(table_label_row, text="🔴  Critical High-Risk Customers Report",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        # TableWidget Initialization
        self._risk_table = TableWidget(
            self.main_content,
            columns=["cust_id", "name", "email", "score", "tier"],
            headers=["ID", "Customer Name", "Email", "Risk Score", "Tier"],
            style="Reports.Treeview",
            column_alignments={
                "cust_id": "center",
                "name": "w",
                "email": "w",
                "score": "center",
                "tier": "center"
            }
        )
        self._risk_table.pack(fill="both", expand=True)

        # Dynamic column scaling listener (ID = 8%, Name = 24%, Email = 42%, Risk Score = 14%, Tier = 12%)
        def _resize_cols(event) -> None:
            w = event.width - 20
            if w > 100:
                self._risk_table._tree.column("cust_id", width=int(w * 0.08), minwidth=50)
                self._risk_table._tree.column("name", width=int(w * 0.24), minwidth=120)
                self._risk_table._tree.column("email", width=int(w * 0.42), minwidth=180)
                self._risk_table._tree.column("score", width=int(w * 0.14), minwidth=80)
                self._risk_table._tree.column("tier", width=int(w * 0.12), minwidth=80)

        self._risk_table.bind("<Configure>", _resize_cols)

        # ── 3. Right Panel (CSV/Excel Export Desk Card) ──
        self._build_export_panel(self.right_panel)

        self._set_period("daily")

    def _build_export_panel(self, parent) -> None:
        # Style parent panel directly as a card
        parent.configure(fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        parent.pack_propagate(False)

        # Content container with 24px padding
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=24, pady=24)

        # Section Title
        ctk.CTkLabel(content_frame, text="DATA EXPORT",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="center", pady=(0, 16))

        # Dataset Label
        ctk.CTkLabel(content_frame, text="Select Table",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack(anchor="w", padx=4, pady=(0, 8))

        # Dataset Radio Buttons
        self._export_var = ctk.StringVar(value="TRANSACTIONS")
        options = [
            ("Transactions Log",   "TRANSACTIONS"),
            ("Alerts Queue Log",   "ALERTS"),
            ("Cases Dossier Log",  "CASES"),
        ]

        rb_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        rb_frame.pack(fill="x", padx=4, pady=(0, 16))

        for text, val in options:
            dot = ctk.CTkRadioButton(
                rb_frame, text=text, variable=self._export_var, value=val,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_COLOR,
                fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
                border_color="#334155"
            )
            dot.pack(anchor="w", pady=4)

        # Format Label
        ctk.CTkLabel(content_frame, text="Export Format",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack(anchor="w", padx=4, pady=(0, 8))

        # Format Radio Buttons
        self._format_var = ctk.StringVar(value="CSV")
        formats = [
            ("CSV",   "CSV"),
            ("Excel", "EXCEL"),
        ]

        format_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        format_frame.pack(fill="x", padx=4, pady=(0, 4))

        for text, val in formats:
            dot = ctk.CTkRadioButton(
                format_frame, text=text, variable=self._format_var, value=val,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_COLOR,
                fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
                border_color="#334155"
            )
            dot.pack(anchor="w", pady=4)

        # Pin status label and export button at the bottom of the card
        self._export_status = ctk.CTkLabel(content_frame, text="",
                                            font=ctk.CTkFont(family="Segoe UI", size=11),
                                            text_color=SUBTEXT_COLOR)
        self._export_status.pack(side="bottom", fill="x", pady=(0, 4))

        self.btn_export = ctk.CTkButton(
            content_frame, text="Generate Export",
            height=48, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._export_csv
        )
        self.btn_export.pack(side="bottom", fill="x")

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
            # Format Risk Score to centered badge style: "XX / 100"
            score_badge = f"{c['risk_score']} / 100"

            self._risk_table.insert_row([
                c["customer_id"],
                c["customer_name"],
                c["email"],
                score_badge,
                get_tier_badge(c["risk_tier"])
            ])

    # ── CSV Export ────────────────────────────────────────────────────────
    def _export_csv(self) -> None:
        entity  = self._export_var.get()
        fmt = self._format_var.get()
        ext = ".csv" if fmt == "CSV" else ".xlsx"
        default = f"finguard_{entity.lower()}_export{ext}"
        path = filedialog.asksaveasfilename(
            initialfile=default,
            defaultextension=ext,
            filetypes=[("CSV Files" if fmt == "CSV" else "Excel Files", f"*{ext}"), ("All Files", "*.*")]
        )
        if not path:
            return

        # Loading state: disable button and update label indicators
        self.btn_export.configure(state="disabled", text="⏳  Exporting...")
        self._export_status.configure(text="⏳  Generating export...", text_color=SUBTEXT_COLOR)

        threading.Thread(target=self._export_worker,
                         args=(entity, path, fmt), daemon=True).start()

    def _export_worker(self, entity: str, path: str, fmt: str) -> None:
        try:
            csv_data = self.generator.generate_csv_export(entity)
            with open(path, "w", newline="", encoding="utf-8") as f:
                f.write(csv_data)
            self.after(0, lambda: self._on_export_success(path))
        except Exception as e:
            self.after(0, lambda: self._on_export_failure(str(e)))

    def _on_export_success(self, path: str) -> None:
        self.btn_export.configure(state="normal", text="Generate Export")
        self._export_status.configure(
            text=f"✅  Exported to {os.path.basename(path)}",
            text_color=SUCCESS_COLOR
        )

    def _on_export_failure(self, err_msg: str) -> None:
        self.btn_export.configure(state="normal", text="Generate Export")
        self._export_status.configure(text="⚠  Export failed", text_color=DANGER_COLOR)
        messagebox.showerror("Export Failed", err_msg)
