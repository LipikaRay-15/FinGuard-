import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.tables import TableWidget
from ui.widgets.searchbar import SearchBar
from ui.widgets.status_badges import StatusBadge
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend imports
from services import AlertService

class AlertsPage(ttk.Frame):
    """
    Risk Alerts Queue page. Displays raised alert records,
    filters by severity/status, and updates alert state properties.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.service = AlertService()

        # Selection state
        self.selected_alert_id = None
        self.selected_alert_data = None

        # Filter properties
        self.status_filter = "All Statuses"
        self.severity_filter = "All Severities"
        self.search_query = ""

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Security Alerts Queue", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        # Split Container
        self.main_split = tk.Frame(self, bg=BG_COLOR)
        self.main_split.pack(fill="both", expand=True)
        self.main_split.columnconfigure(0, weight=4) # Left Table
        self.main_split.columnconfigure(1, weight=2) # Right Detail Panel

        # Left Column Frame (Table and controls)
        self.left_frame = tk.Frame(self.main_split, bg=BG_COLOR)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Filter Options Panel
        self.filter_frame = tk.Frame(self.left_frame, bg=BG_COLOR)
        self.filter_frame.pack(fill="x", pady=(0, 15))

        self.search_bar = SearchBar(self.filter_frame, placeholder="Search Customer or TX ID...", search_callback=self._search_alerts)
        self.search_bar.pack(side="left", fill="x", expand=True)

        self.status_cmb = ttk.Combobox(self.filter_frame, values=["All Statuses", "OPEN", "UNDER_REVIEW", "RESOLVED", "FALSE_POSITIVE", "CLOSED"], style="TCombobox", state="readonly", width=15)
        self.status_cmb.set("All Statuses")
        self.status_cmb.pack(side="left", padx=(10, 0))
        self.status_cmb.bind("<<ComboboxSelected>>", self._on_status_filter_changed)

        self.sev_cmb = ttk.Combobox(self.filter_frame, values=["All Severities", "LOW", "MEDIUM", "HIGH", "CRITICAL"], style="TCombobox", state="readonly", width=15)
        self.sev_cmb.set("All Severities")
        self.sev_cmb.pack(side="left", padx=(10, 0))
        self.sev_cmb.bind("<<ComboboxSelected>>", self._on_severity_filter_changed)

        # Alert Table Grid
        self.table = TableWidget(
            self.left_frame,
            columns=["alert_id", "tx_id", "cust_id", "score", "severity", "status", "time"],
            headers=["Alert ID", "TX ID", "Cust ID", "Risk Score", "Severity", "Status", "Timestamp"]
        )
        self.table.pack(fill="both", expand=True)
        self.table.bind_select(self._on_alert_selected)

        # Right Column Frame (Detail Panel)
        self.right_frame = tk.Frame(self.main_split, bg=CARD_COLOR, padx=16, pady=16)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.detail_title_lbl = tk.Label(self.right_frame, text="Alert Details", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.detail_title_lbl.pack(anchor="w", pady=(0, 15))

        self.details_container = tk.Frame(self.right_frame, bg=CARD_COLOR)
        self.details_container.pack(fill="both", expand=True)

        self.no_sel_lbl = tk.Label(self.details_container, text="Select an alert to inspect workflow controls.", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_BODY)
        self.no_sel_lbl.pack(pady=40)

        # Action Buttons frame (initially hidden)
        self.action_frame = tk.Frame(self.right_frame, bg=CARD_COLOR)
        
        self.review_btn = ttk.Button(self.action_frame, text="Investigate", command=self._start_review)
        self.review_btn.pack(side="left", padx=3)

        self.escalate_btn = ttk.Button(self.action_frame, text="Escalate", command=self._escalate_alert, style="Warning.TButton")
        self.escalate_btn.pack(side="left", padx=3)

        self.close_btn = ttk.Button(self.action_frame, text="Resolve / Close", command=self._close_alert, style="Success.TButton")
        self.close_btn.pack(side="left", padx=3)

        # Initial Load
        self._load_alerts()

    def _load_alerts(self) -> None:
        self.table.clear()
        
        # Async query
        threading.Thread(target=self._load_alerts_worker, daemon=True).start()

    def _load_alerts_worker(self) -> None:
        try:
            sql = "SELECT * FROM alerts"
            where_clauses = []
            params = []

            if self.search_query:
                where_clauses.append("(customer_id = %s OR transaction_id = %s)")
                params.extend([self.search_query, self.search_query])

            if self.status_filter != "All Statuses":
                where_clauses.append("status = %s")
                params.append(self.status_filter)

            if self.severity_filter != "All Severities":
                where_clauses.append("severity = %s")
                params.append(self.severity_filter)

            if where_clauses:
                sql += " WHERE " + " AND ".join(where_clauses)
                
            sql += " ORDER BY created_at DESC LIMIT 50"

            rows = self.service.db.fetch_all(sql, tuple(params))
            
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed loading alerts: {e}"))

    def _populate_table(self, rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            self.table.insert_row([
                r["alert_id"],
                r["transaction_id"],
                r["customer_id"],
                f"{r['risk_score']}/100",
                r["severity"],
                r["status"],
                r["created_at"]
            ], item_id=r["alert_id"])

    def _search_alerts(self, query: str) -> None:
        self.search_query = query
        self._load_alerts()

    def _on_status_filter_changed(self, event) -> None:
        self.status_filter = self.status_cmb.get()
        self._load_alerts()

    def _on_severity_filter_changed(self, event) -> None:
        self.severity_filter = self.sev_cmb.get()
        self._load_alerts()

    def _on_alert_selected(self, item_id: Any) -> None:
        if not item_id:
            return
        
        self.selected_alert_id = int(item_id)
        # Fetch alert record details in background
        threading.Thread(target=self._load_alert_details_worker, args=(self.selected_alert_id,), daemon=True).start()

    def _load_alert_details_worker(self, alert_id: int) -> None:
        try:
            row = self.service.db.fetch_one("SELECT * FROM alerts WHERE alert_id = %s", (alert_id,))
            if row:
                self.after(0, self._populate_details_panel, row)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed to retrieve alert details: {e}"))

    def _populate_details_panel(self, data: Dict[str, Any]) -> None:
        self.selected_alert_data = data
        
        # Clear details panel
        for child in self.details_container.winfo_children():
            child.destroy()
        self.no_sel_lbl.pack_forget()

        # Highlight Alert Header
        lbl_id = tk.Label(self.details_container, text=f"Alert #{data['alert_id']}", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        lbl_id.pack(anchor="w", pady=(0, 5))

        # Status badge
        badge_frame = tk.Frame(self.details_container, bg=CARD_COLOR)
        badge_frame.pack(anchor="w", pady=(0, 15))
        
        status_b = StatusBadge(badge_frame, data["status"])
        status_b.pack(side="left", padx=(0, 10))

        sev_b = StatusBadge(badge_frame, data["severity"])
        sev_b.pack(side="left")

        # Key details
        fields = [
            ("Transaction ID", data["transaction_id"]),
            ("Customer ID", data["customer_id"]),
            ("Risk Score", f"{data['risk_score']}/100"),
            ("Logged Date", data["created_at"])
        ]

        for k, v in fields:
            row = tk.Frame(self.details_container, bg=CARD_COLOR, pady=4)
            row.pack(fill="x")

            lbl_key = tk.Label(row, text=f"{k}:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, width=15, anchor="w")
            lbl_key.pack(side="left")

            lbl_val = tk.Label(row, text=str(v), bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY, anchor="w")
            lbl_val.pack(side="left")

        # Show action frame buttons
        self.action_frame.pack(fill="x", side="bottom", pady=10)

    def _start_review(self) -> None:
        if not self.selected_alert_id:
            return
        try:
            self.service.update_alert_status(self.selected_alert_id, "UNDER_REVIEW")
            self._load_alerts()
            self._load_alert_details_worker(self.selected_alert_id)
            messagebox.showinfo("Status Updated", f"Alert #{self.selected_alert_id} transition set to UNDER_REVIEW.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed updating alert status: {e}")

    def _escalate_alert(self) -> None:
        if not self.selected_alert_id:
            return
        
        # Escalate alert takes a note argument
        confirm = messagebox.askyesno("Escalate Alert", "Escalate alert to compliance/investigators queue?")
        if confirm:
            try:
                self.service.escalate_alert(self.selected_alert_id, "Escalated from desktop monitoring dashboard panel.")
                self._load_alerts()
                self._load_alert_details_worker(self.selected_alert_id)
                messagebox.showinfo("Status Updated", f"Alert #{self.selected_alert_id} successfully escalated.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to escalate: {e}")

    def _close_alert(self) -> None:
        if not self.selected_alert_id:
            return
            
        confirm = messagebox.askyesno("Resolve Alert", "Mark this alert as RESOLVED and close the case?")
        if confirm:
            try:
                self.service.close_alert(self.selected_alert_id, "Legitimate transaction verified by manual analyst check.")
                self._load_alerts()
                self._load_alert_details_worker(self.selected_alert_id)
                messagebox.showinfo("Resolved", f"Alert #{self.selected_alert_id} closed and resolved.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed resolving: {e}")
