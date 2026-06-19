"""
FinGuard UI – Alerts Page
Risk alert queue with filters, detail panel, and status actions.
"""
import threading
import tkinter as tk
from tkinter import ttk
import os
import traceback
import time
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.tables       import TableWidget
from ui.widgets.searchbar    import SearchBar
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, SPACE_S, SPACE_XS, BasePage
)
from services import AlertService


class PillBadge(ctk.CTkLabel):
    """A small custom rounded pill badge with consistent sizing."""
    def __init__(self, parent, text: str, bg_color: str, text_color: str = "#FFFFFF", **kwargs):
        super().__init__(
            parent,
            text=text,
            fg_color=bg_color,
            text_color=text_color,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            corner_radius=12,
            width=110,
            height=24,
            **kwargs
        )


class ToolTip:
    """A professional dark-themed tooltip with fade-in animation and auto-hide."""
    def __init__(self, widget, text_func) -> None:
        self.widget = widget
        self.text_func = text_func if callable(text_func) else lambda: text_func
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")

    def show_tip(self, event=None) -> None:
        text = self.text_func()
        if self.tip_window or not text:
            return
        
        # Calculate coordinate to align centered under the widget
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2 - 125
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg="#0F172A")
        tw.attributes("-alpha", 0.0)
        
        frame = tk.Frame(tw, bg="#1E293B", padx=10, pady=6, highlightthickness=1, highlightbackground="#334155")
        frame.pack()
        
        lbl = tk.Label(frame, text=text, justify="left",
                       font=("Segoe UI", 11), bg="#1E293B", fg="#F8FAFC",
                       wraplength=230)
        lbl.pack()
        
        def fade():
            for i in range(1, 11):
                if tw.winfo_exists():
                    tw.attributes("-alpha", (i / 10.0) * 0.98)
                    tw.update()
                    time.sleep(0.01)
        tw.after(10, fade)

    def hide_tip(self, event=None) -> None:
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()


class ToastNotification:
    """Non-blocking dark theme toast notification in the bottom-right corner."""
    def __init__(self, parent_widget, message: str) -> None:
        self.parent = parent_widget.winfo_toplevel()
        self.message = message
        self.window = tk.Toplevel(self.parent)
        self.window.wm_overrideredirect(True)
        self.window.configure(bg="#0F172A")
        self.window.attributes("-alpha", 0.0)
        
        self.parent.bind("<Configure>", self.update_position, add="+")
        
        frame = tk.Frame(self.window, bg="#1E293B", padx=16, pady=10, highlightthickness=1, highlightbackground="#10B981")
        frame.pack()
        
        lbl = tk.Label(frame, text=message, font=("Segoe UI", 11, "bold"), bg="#1E293B", fg="#F8FAFC")
        lbl.pack()
        
        self.update_position()
        self.fade_in()
        self.window.after(2500, self.fade_out)

    def update_position(self, event=None) -> None:
        if not self.window.winfo_exists():
            return
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        
        tw = 300
        th = 45
        x = px + pw - tw - 24
        y = py + ph - th - 24
        self.window.wm_geometry(f"{tw}x{th}+{x}+{y}")

    def fade_in(self) -> None:
        def fade():
            for i in range(1, 11):
                if self.window.winfo_exists():
                    self.window.attributes("-alpha", i / 10.0)
                    self.window.update()
                    time.sleep(0.01)
        self.window.after(10, fade)

    def fade_out(self) -> None:
        def fade():
            for i in range(10, -1, -1):
                if self.window.winfo_exists():
                    self.window.attributes("-alpha", i / 10.0)
                    self.window.update()
                    time.sleep(0.01)
            if self.window.winfo_exists():
                self.window.destroy()
        threading.Thread(target=fade, daemon=True).start()


class ProcessingOverlay:
    """Dims the page, blocks interaction, and shows a centered loading spinner modal."""
    def __init__(self, parent_widget, text: str) -> None:
        self.parent = parent_widget.winfo_toplevel()
        self.text = text
        
        self.overlay = tk.Toplevel(self.parent)
        self.overlay.wm_overrideredirect(True)
        self.overlay.configure(bg="#020617")
        self.overlay.attributes("-alpha", 0.0)
        
        self.modal = tk.Toplevel(self.parent)
        self.modal.wm_overrideredirect(True)
        self.modal.configure(bg="#0F172A")
        
        modal_frame = tk.Frame(self.modal, bg="#0F172A", padx=24, pady=20, highlightthickness=1, highlightbackground="#334155")
        modal_frame.pack()
        
        self.spinner_lbl = tk.Label(modal_frame, text="⏳", font=("Segoe UI", 24), bg="#0F172A", fg="#3B82F6")
        self.spinner_lbl.pack(pady=(0, 10))
        
        self.text_lbl = tk.Label(modal_frame, text=text, font=("Segoe UI", 12, "bold"), bg="#0F172A", fg="#F8FAFC")
        self.text_lbl.pack()
        
        self.parent.bind("<Configure>", self.update_position, add="+")
        self.update_position()
        
        self.spinner_chars = ["⏳", "⌛"]
        self.spinner_idx = 0
        self.animate_spinner()
        self.fade_in()

    def update_position(self, event=None) -> None:
        if not self.overlay.winfo_exists() or not self.modal.winfo_exists():
            return
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        
        self.overlay.wm_geometry(f"{pw}x{ph}+{px}+{py}")
        
        mw = 250
        mh = 120
        mx = px + (pw - mw) // 2
        my = py + (ph - mh) // 2
        self.modal.wm_geometry(f"{mw}x{mh}+{mx}+{my}")

    def animate_spinner(self) -> None:
        if not self.modal.winfo_exists():
            return
        self.spinner_idx = (self.spinner_idx + 1) % len(self.spinner_chars)
        self.spinner_lbl.configure(text=self.spinner_chars[self.spinner_idx])
        self.modal.after(400, self.animate_spinner)

    def fade_in(self) -> None:
        def fade():
            for i in range(1, 7):
                if self.overlay.winfo_exists():
                    self.overlay.attributes("-alpha", i * 0.1)
                    self.overlay.update()
                    time.sleep(0.01)
        self.overlay.after(10, fade)

    def dismiss(self) -> None:
        def fade():
            for i in range(6, -1, -1):
                if self.overlay.winfo_exists():
                    self.overlay.attributes("-alpha", i * 0.1)
                    self.overlay.update()
                    time.sleep(0.01)
            if self.overlay.winfo_exists():
                self.overlay.destroy()
            if self.modal.winfo_exists():
                self.modal.destroy()
        threading.Thread(target=fade, daemon=True).start()


def show_non_blocking_error(parent, message: str) -> None:
    top = tk.Toplevel(parent)
    top.title("Error")
    top.geometry("300x120")
    top.configure(bg="#0F172A")
    top.wm_attributes("-topmost", True)
    
    px = parent.winfo_rootx() + (parent.winfo_width() - 300) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - 120) // 2
    top.geometry(f"+{px}+{py}")
    
    frame = tk.Frame(top, bg="#0F172A", padx=16, pady=16)
    frame.pack(fill="both", expand=True)
    
    tk.Label(frame, text="⚠️  Error", font=("Segoe UI", 12, "bold"), bg="#0F172A", fg="#EF4444").pack(anchor="w", pady=(0, 6))
    tk.Label(frame, text=message, font=("Segoe UI", 10), bg="#0F172A", fg="#F8FAFC").pack(anchor="w", pady=(0, 10))
    
    ctk.CTkButton(
        frame, text="OK", width=80, height=28, corner_radius=6,
        fg_color="#3B82F6", hover_color="#2563EB",
        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
        command=top.destroy
    ).pack(anchor="e")


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

        # Define custom treeview style matching Dashboard
        style = ttk.Style()
        style.configure("Alerts.Treeview",
            background=CARD_COLOR,
            fieldbackground=CARD_COLOR,
            foreground=TEXT_COLOR,
            rowheight=30,
            font=(FONT_FAMILY, 11),
            borderwidth=0,
            relief="flat",
        )
        style.configure("Alerts.Treeview.Heading",
            background="#0F172A",
            foreground=SUBTEXT_COLOR,
            font=(FONT_FAMILY, 12, "bold"),
            padding=6,
            borderwidth=0,
            relief="flat",
        )
        style.map("Alerts.Treeview",
            background=[("selected", PRIMARY_COLOR), ("active", "#1E3A5F")],
            foreground=[("selected", TEXT_COLOR)],
        )

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
            headers=["Alert ID","TX ID","Cust ID","Risk Score","Severity","Status","Timestamp"],
            style="Alerts.Treeview",
            column_alignments={
                "alert_id": "center",
                "tx_id": "center",
                "cust_id": "center",
                "score": "center",
                "severity": "center",
                "status": "center",
                "time": "center"
            }
        )
        self._table.pack(fill="both", expand=True)
        self._table.bind_select(self._on_alert_selected)

        def resize_cols(event):
            w = event.width
            usable_w = max(800, w - 25)
            self._table._tree.column("alert_id", width=int(usable_w * 0.10), minwidth=60, stretch=False)
            self._table._tree.column("tx_id", width=int(usable_w * 0.10), minwidth=60, stretch=False)
            self._table._tree.column("cust_id", width=int(usable_w * 0.10), minwidth=60, stretch=False)
            self._table._tree.column("score", width=int(usable_w * 0.15), minwidth=90, stretch=False)
            self._table._tree.column("severity", width=int(usable_w * 0.15), minwidth=90, stretch=False)
            self._table._tree.column("status", width=int(usable_w * 0.20), minwidth=110, stretch=False)
            self._table._tree.column("time", width=int(usable_w * 0.20), minwidth=120, stretch=False)

        self._table.bind("<Configure>", resize_cols)

        # ── 4. Right column: detail panel ──
        detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=40)
        detail_header.pack(fill="x", padx=SPACE_S, pady=(SPACE_S, 0))
        
        ctk.CTkLabel(detail_header, text="Alert Details",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        ctk.CTkFrame(self.right_panel, fg_color="#2D3748", height=1).pack(fill="x", padx=SPACE_S, pady=(8, 0))

        self._details_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self._details_frame.pack(fill="both", expand=True, padx=SPACE_S, pady=SPACE_S)

        # Initial Empty State
        self._show_empty_state()

        # Tooltip messages state values (populated dynamically in populate_details)
        self._review_tooltip_text = ""
        self._escalate_tooltip_text = ""
        self._resolve_tooltip_text = ""

        # ── 5. Footer Frame ──
        self._stats_lbl = ctk.CTkLabel(self.footer, text="",
                                        font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                        text_color=SUBTEXT_COLOR, anchor="w")
        self._stats_lbl.pack(side="left", pady=10)

        self._load_alerts()

    def _show_empty_state(self) -> None:
        for w in self._details_frame.winfo_children():
            w.destroy()

        empty_container = ctk.CTkFrame(self._details_frame, fg_color="transparent")
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
        for w in self._details_frame.winfo_children():
            w.destroy()

        # ── SECTION 1. Alert Summary ──
        summary_frame = ctk.CTkFrame(self._details_frame, fg_color="transparent")
        summary_frame.pack(fill="x", pady=(4, 8))

        # Risk Score Section
        ctk.CTkLabel(
            summary_frame, text="Risk Score",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w"
        ).pack(anchor="w", pady=(0, 2))

        score = data.get("risk_score", 0)
        ctk.CTkLabel(
            summary_frame, text=f"{score} / 100",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR, anchor="w"
        ).pack(anchor="w", pady=(0, 4))

        bar = ctk.CTkProgressBar(summary_frame, height=6, fg_color="#1E293B", corner_radius=3)
        bar.set(score / 100)
        from ui.widgets.theme import SEVERITY_COLORS
        bar.configure(progress_color=SEVERITY_COLORS.get(data["severity"], PRIMARY_COLOR))
        bar.pack(fill="x", pady=(0, 10))

        # Divider
        ctk.CTkFrame(summary_frame, fg_color="#2D3748", height=1).pack(fill="x", pady=(0, 10))

        # Metadata rows (Stacked vertically: label on top, value below)
        metadata_list = [
            ("Transaction ID", data["transaction_id"]),
            ("Customer ID", data["customer_id"]),
        ]
        for lbl, val in metadata_list:
            ctk.CTkLabel(
                summary_frame, text=lbl,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=SUBTEXT_COLOR, anchor="w"
            ).pack(anchor="w", pady=(2, 0))
            
            ctk.CTkLabel(
                summary_frame, text=str(val),
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_COLOR, anchor="w"
            ).pack(anchor="w", pady=(0, 8))

        # Status Badge Row (Stacked vertically)
        ctk.CTkLabel(
            summary_frame, text="Status",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        status_val = (data["status"] or "").upper()
        if "CLOSED" in status_val or "RESOLVED" in status_val or "FALSE_POSITIVE" in status_val:
            status_bg = "#10B981"
            status_lbl = "CLOSED"
        elif "ESCALATED" in status_val:
            status_bg = "#F97316"
            status_lbl = "ESCALATED"
        elif "UNDER_REVIEW" in status_val:
            status_bg = "#F59E0B"
            status_lbl = "UNDER REVIEW"
        else:
            status_bg = "#2563EB"
            status_lbl = "OPEN"
        
        PillBadge(summary_frame, status_lbl, bg_color=status_bg).pack(anchor="w", fill="x", pady=(0, 8))

        # Severity Badge Row (Stacked vertically)
        ctk.CTkLabel(
            summary_frame, text="Severity",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        sev_val = (data["severity"] or "").upper()
        if "CRITICAL" in sev_val:
            sev_bg = "#EF4444"
        elif "HIGH" in sev_val:
            sev_bg = "#F97316"
        elif "MEDIUM" in sev_val:
            sev_bg = "#F59E0B"
        else:
            sev_bg = "#10B981"
            
        PillBadge(summary_frame, sev_val, bg_color=sev_bg).pack(anchor="w", fill="x", pady=(0, 4))

        # Divider
        ctk.CTkFrame(self._details_frame, fg_color="#2D3748", height=1).pack(fill="x", pady=(0, 8))

        # ── SECTION 2. Workflow Status ──
        workflow_frame = ctk.CTkFrame(self._details_frame, fg_color="transparent")
        workflow_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            workflow_frame, text="ALERT WORKFLOW",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", pady=(0, 6))

        stages = [
            ("OPEN", ["OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED", "FALSE_POSITIVE"]),
            ("UNDER REVIEW", ["UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED", "FALSE_POSITIVE"]),
            ("ESCALATED", ["ESCALATED", "RESOLVED", "CLOSED", "FALSE_POSITIVE"]),
            ("CLOSED", ["RESOLVED", "CLOSED", "FALSE_POSITIVE"])
        ]

        db_status = (data["status"] or "").upper()
        if db_status in ["RESOLVED", "CLOSED", "FALSE_POSITIVE"]:
            current_stage = "CLOSED"
        elif db_status == "UNDER_REVIEW":
            current_stage = "UNDER REVIEW"
        else:
            current_stage = db_status

        for idx, (stage_name, active_for_badges) in enumerate(stages):
            is_active = (stage_name == current_stage)
            is_completed = (db_status in active_for_badges) and not is_active

            if is_active:
                bullet_color = "#2563EB" if current_stage == "OPEN" else ("#F59E0B" if current_stage == "UNDER REVIEW" else ("#F97316" if current_stage == "ESCALATED" else "#10B981"))
                text_color = TEXT_COLOR
                font_weight = "bold"
                bullet_char = "●"
            elif is_completed:
                bullet_color = "#10B981"
                text_color = SUBTEXT_COLOR
                font_weight = "normal"
                bullet_char = "✓"
            else:
                bullet_color = "#475569"
                text_color = "#475569"
                font_weight = "normal"
                bullet_char = "○"

            step_row = ctk.CTkFrame(workflow_frame, fg_color="transparent")
            step_row.pack(fill="x", pady=1)

            ctk.CTkLabel(
                step_row, text=f"{bullet_char} {stage_name}",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight=font_weight),
                text_color=text_color, anchor="w"
            ).pack(anchor="w", padx=4)

            if idx < len(stages) - 1:
                line_color = "#10B981" if is_completed else "#475569"
                ctk.CTkLabel(
                    workflow_frame, text="↓",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                    text_color=line_color, anchor="w"
                ).pack(anchor="w", padx=8, pady=2)

        # Divider
        ctk.CTkFrame(self._details_frame, fg_color="#2D3748", height=1).pack(fill="x", pady=(0, 8))

        # ── SECTION 3. Action Descriptions Card ──
        expl_frame = ctk.CTkFrame(self._details_frame, fg_color="transparent")
        expl_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            expl_frame, text="ACTION EXPLANATIONS",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", pady=(0, 6))

        explanations = [
            ("Review", "Assign this alert to a fraud analyst."),
            ("Escalate", "Forward this alert to senior fraud operations."),
            ("Resolve", "Close investigation after completion.")
        ]
        for title, desc in explanations:
            ctk.CTkLabel(
                expl_frame, text=title,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                text_color=TEXT_COLOR, anchor="w"
            ).pack(anchor="w", pady=(2, 0))
            
            ctk.CTkLabel(
                expl_frame, text=desc,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=SUBTEXT_COLOR, anchor="w", justify="left", wraplength=230
            ).pack(anchor="w", pady=(0, 6))

        # Divider
        ctk.CTkFrame(self._details_frame, fg_color="#2D3748", height=1).pack(fill="x", pady=(0, 8))

        # ── SECTION 4. Action Buttons ──
        buttons_container = ctk.CTkFrame(self._details_frame, fg_color="transparent")
        buttons_container.pack(fill="x", side="bottom", pady=(4, 0))

        self._review_btn = ctk.CTkButton(
            buttons_container, text="👁  REVIEW",
            height=38, corner_radius=12,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._start_review
        )
        self._review_btn.pack(fill="x", pady=(0, 12))

        self._escalate_btn = ctk.CTkButton(
            buttons_container, text="↑  ESCALATE",
            height=38, corner_radius=12,
            fg_color=WARNING_COLOR, hover_color="#D97706",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._escalate_alert
        )
        self._escalate_btn.pack(fill="x", pady=(0, 12))

        self._resolve_btn = ctk.CTkButton(
            buttons_container, text="✓  RESOLVE",
            height=38, corner_radius=12,
            fg_color=SUCCESS_COLOR, hover_color="#059669",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self._close_alert
        )
        self._resolve_btn.pack(fill="x")

        # Dynamic Button states & tooltips setup (enabled explanations vs disabled block messages)
        if db_status == "OPEN":
            self._review_btn.configure(state="normal")
            self._escalate_btn.configure(state="normal")
            self._resolve_btn.configure(state="disabled")
            
            self._review_tooltip_text = ""
            self._escalate_tooltip_text = ""
            self._resolve_tooltip_text = "Resolve becomes available after investigation."
        elif db_status == "UNDER_REVIEW":
            self._review_btn.configure(state="disabled")
            self._escalate_btn.configure(state="normal")
            self._resolve_btn.configure(state="normal")
            
            self._review_tooltip_text = "Action already completed."
            self._escalate_tooltip_text = ""
            self._resolve_tooltip_text = ""
        elif db_status == "ESCALATED":
            self._review_btn.configure(state="disabled")
            self._escalate_btn.configure(state="disabled")
            self._resolve_btn.configure(state="normal")
            
            self._review_tooltip_text = "Action already completed."
            self._escalate_tooltip_text = "Action already completed."
            self._resolve_tooltip_text = ""
        else: # CLOSED / RESOLVED / FALSE_POSITIVE
            self._review_btn.configure(state="disabled")
            self._escalate_btn.configure(state="disabled")
            self._resolve_btn.configure(state="disabled")
            
            self._review_tooltip_text = "Action already completed."
            self._escalate_tooltip_text = "Action already completed."
            self._resolve_tooltip_text = "Action already completed."

        ToolTip(self._review_btn, lambda: self._review_tooltip_text)
        ToolTip(self._escalate_btn, lambda: self._escalate_tooltip_text)
        ToolTip(self._resolve_btn, lambda: self._resolve_tooltip_text)

    # ── Actions ───────────────────────────────────────────────────────────

    def _start_review(self) -> None:
        if not self.selected_alert_id:
            return
        overlay = ProcessingOverlay(self, "Assigning Alert...")
        def run():
            try:
                self.service.update_alert_status(self.selected_alert_id, "UNDER_REVIEW")
                self.after(0, lambda: self._on_action_success("Alert assigned for investigation.", overlay))
            except Exception as e:
                self.after(0, lambda: self._on_action_error(e, overlay))
        threading.Thread(target=run, daemon=True).start()

    def _escalate_alert(self) -> None:
        if not self.selected_alert_id:
            return
        if messagebox.askyesno("Escalate", "Escalate alert to compliance queue?"):
            overlay = ProcessingOverlay(self, "Escalating Alert...")
            def run():
                try:
                    self.service.escalate_alert(self.selected_alert_id,
                                                "Escalated from desktop monitoring dashboard.")
                    self.after(0, lambda: self._on_action_success("Alert escalated successfully.", overlay))
                except Exception as e:
                    self.after(0, lambda: self._on_action_error(e, overlay))
            threading.Thread(target=run, daemon=True).start()

    def _close_alert(self) -> None:
        if not self.selected_alert_id:
            return
        if messagebox.askyesno("Resolve", "Mark this alert as RESOLVED?"):
            overlay = ProcessingOverlay(self, "Resolving Alert...")
            def run():
                try:
                    self.service.close_alert(self.selected_alert_id,
                                             "Legitimate transaction verified by analyst.")
                    self.after(0, lambda: self._on_action_success("Alert closed successfully.", overlay))
                except Exception as e:
                    self.after(0, lambda: self._on_action_error(e, overlay))
            threading.Thread(target=run, daemon=True).start()

    def _on_action_success(self, success_msg: str, overlay: ProcessingOverlay) -> None:
        overlay.dismiss()
        self._load_alerts()
        self._load_details_worker(self.selected_alert_id)
        ToastNotification(self, success_msg)

    def _on_action_error(self, exc: Exception, overlay: ProcessingOverlay) -> None:
        overlay.dismiss()
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/application.log", "a") as f:
                f.write(f"Exception during action execution: {str(exc)}\n")
                traceback.print_exc(file=f)
                f.write("="*60 + "\n")
        except Exception:
            pass
        show_non_blocking_error(self, "Operation failed. Please retry.")
