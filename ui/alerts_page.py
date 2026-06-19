"""
FinGuard UI – Alerts Page
Risk alert queue with filters, detail panel, and status actions.
"""
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.tables       import TableWidget
from ui.widgets.searchbar    import SearchBar
from ui.widgets.status_badges import StatusBadge
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, SPACE_S, SPACE_XS, BasePage
)
from services import AlertService


class AlertsPage(BasePage):
    """Risk Alerts Queue page subclassing standardized BasePage layout."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Security Alerts Queue", has_right_panel=True)
        self.service = AlertService()
        self.selected_alert_id   = None
        self.selected_alert_data = None
        self.status_filter   = ""
        self.severity_filter = ""
        self.search_query    = ""

        # ── 1. Header Action Button ──
        ctk.CTkButton(self.header_actions, text="⟳  Refresh Queue", width=120, height=36, corner_radius=8,
                      fg_color="#1E293B", hover_color="#334155", text_color=TEXT_COLOR,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      command=self._load_alerts).pack(side="right", pady=22)

        # ── 2. Toolbar ──
        self._search = SearchBar(self.toolbar, placeholder="Search Customer ID or TX ID…",
                                 search_callback=self._search_alerts)
        self._search.pack(side="left", fill="x", expand=True, pady=6)

        self._status_cmb = ctk.CTkComboBox(
            self.toolbar, values=["All Status","OPEN","UNDER_REVIEW","RESOLVED","FALSE_POSITIVE","CLOSED"],
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, button_color="#334155",
            dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=145, height=36, corner_radius=8, state="readonly",
            command=self._on_status_changed
        )
        self._status_cmb.set("All Status")
        self._status_cmb.pack(side="left", padx=(8, 0), pady=6)

        self._sev_cmb = ctk.CTkComboBox(
            self.toolbar, values=["All Severity","LOW","MEDIUM","HIGH","CRITICAL"],
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, button_color="#334155",
            dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=140, height=36, corner_radius=8, state="readonly",
            command=self._on_severity_changed
        )
        self._sev_cmb.set("All Severity")
        self._sev_cmb.pack(side="left", padx=(8, 0), pady=6)

        # ── 3. Main Content: Table ──
        self._table = TableWidget(
            self.main_content,
            columns=["alert_id","tx_id","cust_id","score","severity","status","time"],
            headers=["Alert ID","TX ID","Cust ID","Risk Score","Severity","Status","Timestamp"]
        )
        self._table.pack(fill="both", expand=True)
        self._table.bind_select(self._on_alert_selected)

        # ── 4. Right column: detail panel ──
        detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=40)
        detail_header.pack(fill="x", padx=SPACE_S, pady=(SPACE_S, 0))
        
        ctk.CTkLabel(detail_header, text="Alert Details",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        ctk.CTkFrame(self.right_panel, fg_color="#2D3748", height=1).pack(fill="x", padx=SPACE_S, pady=(8, 0))

        self._details_scroll = ctk.CTkScrollableFrame(
            self.right_panel, fg_color="transparent",
            scrollbar_fg_color=CARD_COLOR, scrollbar_button_color="#334155"
        )
        self._details_scroll.pack(fill="both", expand=True, padx=SPACE_S, pady=SPACE_S)

        # Initial Empty State
        self._show_empty_state()

        # Action buttons row
        self._action_row = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=60)
        self._action_row.pack_propagate(False)

        ctk.CTkButton(self._action_row, text="Review",
                      width=76, height=36, corner_radius=8,
                      fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      command=self._start_review).pack(side="left", padx=(SPACE_S, 4), pady=12)

        ctk.CTkButton(self._action_row, text="Escalate",
                      width=76, height=36, corner_radius=8,
                      fg_color=WARNING_COLOR, hover_color="#D97706",
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      command=self._escalate_alert).pack(side="left", padx=4, pady=12)

        ctk.CTkButton(self._action_row, text="Resolve",
                      width=76, height=36, corner_radius=8,
                      fg_color=SUCCESS_COLOR, hover_color="#059669",
                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                      command=self._close_alert).pack(side="left", padx=4, pady=12)

        # ── 5. Footer Frame ──
        self._stats_lbl = ctk.CTkLabel(self.footer, text="",
                                        font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                        text_color=SUBTEXT_COLOR, anchor="w")
        self._stats_lbl.pack(side="left", pady=10)

        self._load_alerts()

    def _show_empty_state(self) -> None:
        for w in self._details_scroll.winfo_children():
            w.destroy()
        if hasattr(self, "_action_row") and self._action_row:
            self._action_row.pack_forget()

        empty_container = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        empty_container.pack(fill="both", expand=True, pady=120)

        icon_lbl = ctk.CTkLabel(
            empty_container, text="🚨",
            font=ctk.CTkFont(family=FONT_FAMILY, size=64),
            text_color=SUBTEXT_COLOR
        )
        icon_lbl.pack(pady=(0, SPACE_S))

        msg_lbl = ctk.CTkLabel(
            empty_container,
            text="No Alert Selected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_COLOR, justify="center"
        )
        msg_lbl.pack()

        sub_msg_lbl = ctk.CTkLabel(
            empty_container,
            text="Select a security alert from the queue\nto inspect details and take actions.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=SUBTEXT_COLOR, justify="center"
        )
        sub_msg_lbl.pack(pady=(4, 0))

    # ── Data Loading ──────────────────────────────────────────────────────

    def _load_alerts(self) -> None:
        self._table.clear()
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            sql = "SELECT * FROM alerts"
            clauses, params = [], []
            if self.search_query:
                clauses.append("(customer_id = %s OR transaction_id = %s)")
                params += [self.search_query, self.search_query]
            if self.status_filter:
                clauses.append("status = %s"); params.append(self.status_filter)
            if self.severity_filter:
                clauses.append("severity = %s"); params.append(self.severity_filter)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY created_at DESC LIMIT 100"
            rows = self.service.db.fetch_all(sql, tuple(params))
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("DB Error", str(e)))

    def _populate_table(self, rows: List[Dict]) -> None:
        for r in rows:
            self._table.insert_row([
                r["alert_id"], r["transaction_id"], r["customer_id"],
                f"{r['risk_score']}/100", r["severity"], r["status"],
                str(r["created_at"])[:16]
            ], item_id=r["alert_id"])
        self._stats_lbl.configure(text=f"{len(rows)} alerts loaded")

    # ── Filters ───────────────────────────────────────────────────────────

    def _search_alerts(self, q: str) -> None:
        self.search_query = q
        self._load_alerts()

    def _on_status_changed(self, val: str) -> None:
        self.status_filter = "" if val.startswith("All") else val
        self._load_alerts()

    def _on_severity_changed(self, val: str) -> None:
        self.severity_filter = "" if val.startswith("All") else val
        self._load_alerts()

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_alert_selected(self, item_id: Any) -> None:
        self.selected_alert_id = int(item_id)
        threading.Thread(target=self._load_details_worker,
                         args=(self.selected_alert_id,), daemon=True).start()

    def _load_details_worker(self, alert_id: int) -> None:
        try:
            row = self.service.db.fetch_one(
                "SELECT * FROM alerts WHERE alert_id = %s", (alert_id,))
            if row:
                self.after(0, self._populate_details, row)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _populate_details(self, data: Dict) -> None:
        self.selected_alert_data = data
        for w in self._details_scroll.winfo_children():
            w.destroy()

        # Alert ID heading
        ctk.CTkLabel(
            self._details_scroll,
            text=f"Alert #{data['alert_id']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=15, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", pady=(4, 6))

        # Status + severity badges
        badge_row = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(0, 12))
        StatusBadge(badge_row, data["status"]).pack(side="left", padx=(0, 6))
        StatusBadge(badge_row, data["severity"]).pack(side="left")

        # Risk score bar
        score = data.get("risk_score", 0)
        ctk.CTkLabel(self._details_scroll, text=f"Risk Score: {score}/100",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                     text_color=SUBTEXT_COLOR).pack(anchor="w", pady=(0, 4))
        bar = ctk.CTkProgressBar(self._details_scroll, height=6,
                                  fg_color="#1E293B", corner_radius=3)
        bar.set(score / 100)
        from ui.widgets.theme import SEVERITY_COLORS
        bar.configure(progress_color=SEVERITY_COLORS.get(data["severity"], PRIMARY_COLOR))
        bar.pack(fill="x", padx=2, pady=(0, 12))

        # Detail fields
        fields = [
            ("Transaction ID", data["transaction_id"]),
            ("Customer ID",    data["customer_id"]),
            ("Logged Date",    str(data["created_at"])[:16]),
        ]
        ctk.CTkFrame(self._details_scroll, fg_color="#2D3748", height=1).pack(
            fill="x", pady=(0, 8))
        for k, v in fields:
            row = ctk.CTkFrame(self._details_scroll, fg_color="transparent", height=26)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{k}:", text_color=SUBTEXT_COLOR,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                         width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(v), text_color=TEXT_COLOR,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                         anchor="w").pack(side="left", fill="x", expand=True)

        self._action_row.pack(fill="x", pady=(8, 4))

    # ── Actions ───────────────────────────────────────────────────────────

    def _start_review(self) -> None:
        if not self.selected_alert_id:
            return
        try:
            self.service.update_alert_status(self.selected_alert_id, "UNDER_REVIEW")
            self._load_alerts()
            self._load_details_worker(self.selected_alert_id)
            messagebox.showinfo("Updated", f"Alert #{self.selected_alert_id} → UNDER_REVIEW")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _escalate_alert(self) -> None:
        if not self.selected_alert_id:
            return
        if messagebox.askyesno("Escalate", "Escalate alert to compliance queue?"):
            try:
                self.service.escalate_alert(self.selected_alert_id,
                                            "Escalated from desktop monitoring dashboard.")
                self._load_alerts()
                self._load_details_worker(self.selected_alert_id)
                messagebox.showinfo("Escalated", f"Alert #{self.selected_alert_id} escalated.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def _close_alert(self) -> None:
        if not self.selected_alert_id:
            return
        if messagebox.askyesno("Resolve", "Mark this alert as RESOLVED?"):
            try:
                self.service.close_alert(self.selected_alert_id,
                                         "Legitimate transaction verified by analyst.")
                self._load_alerts()
                self._load_details_worker(self.selected_alert_id)
                messagebox.showinfo("Resolved", f"Alert #{self.selected_alert_id} resolved.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
