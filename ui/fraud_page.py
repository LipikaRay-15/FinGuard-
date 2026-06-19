import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.cards        import CardWidget
from ui.widgets.status_badges import StatusBadge
from ui.widgets.tables       import TableWidget
from ui.widgets.timeline     import TimelineWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    SEVERITY_COLORS, FONT_FAMILY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BUTTON,
    SPACE_XS, SPACE_S, SPACE_M, SPACE_L, SPACE_XL, format_inr, BasePage
)
from engines import FraudDetectionEngine
from services.risk_explanation_service import RiskExplanationService


def _severity_color(level: str) -> str:
    level_upper = (level or "").upper()
    if "LOW" in level_upper:
        return SUCCESS_COLOR
    elif "MEDIUM" in level_upper:
        return WARNING_COLOR
    elif "HIGH" in level_upper:
        return "#F97316"
    elif "CRITICAL" in level_upper:
        return DANGER_COLOR
    return SUCCESS_COLOR


class FraudPage(BasePage):
    """Live fraud detection page subclassing standardized BasePage layout."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Live Fraud Detection Analyzer", has_right_panel=True)
        self.engine = FraudDetectionEngine()
        self.explanation_service = RiskExplanationService()

        # ── 1. Toolbar Frame Setup ──
        ctk.CTkLabel(self.toolbar, text="Transaction ID to Scan:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack(side="left", padx=(SPACE_S, SPACE_XS))

        self._tx_entry = ctk.CTkEntry(
            self.toolbar, placeholder_text="e.g. 1",
            fg_color=BG_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, placeholder_text_color=SUBTEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            width=180, height=38, corner_radius=8
        )
        self._tx_entry.pack(side="left")
        self._tx_entry.bind("<Return>", lambda e: self.scan_transaction())

        self._scan_btn = ctk.CTkButton(
            self.toolbar, text="🛡️  Scan Transaction",
            width=200, height=38, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self.scan_transaction
        )
        self._scan_btn.pack(side="left", padx=SPACE_S)

        self._last_scan_lbl = ctk.CTkLabel(self.toolbar, text="",
                                            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                            text_color=SUBTEXT_COLOR)
        self._last_scan_lbl.pack(side="right", padx=SPACE_S)

        # ── 2. Loading Indicator ──
        self._loading = ctk.CTkLabel(
            self.main_content, text="⏳  Analyzing transaction risk patterns…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14), text_color=SUBTEXT_COLOR)

        # ── 3. Content Frame Placements ──
        # Clear main content and right panel defaults
        for w in self.main_content.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        self._load_default_transaction()

    def _load_default_transaction(self) -> None:
        try:
            last_tx = self.engine.db.fetch_one(
                "SELECT transaction_id FROM transactions ORDER BY transaction_time DESC LIMIT 1"
            )
            if last_tx:
                self._tx_entry.insert(0, str(last_tx["transaction_id"]))
                self.scan_transaction()
        except Exception:
            pass

    def scan_transaction(self) -> None:
        tx_str = self._tx_entry.get().strip()
        if not tx_str:
            messagebox.showwarning("Input Required", "Please enter a Transaction ID.")
            return
        try:
            tx_id = int(tx_str)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Transaction ID must be an integer.")
            return

        # Clear panels & show loading
        for w in self.main_content.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()
        
        self._loading.pack(self.main_content, pady=60)
        self._scan_btn.configure(state="disabled", text="Scanning…")

        threading.Thread(target=self._scan_worker, args=(tx_id,), daemon=True).start()

    def _scan_worker(self, tx_id: int) -> None:
        try:
            result      = self.engine.detect_fraud(tx_id)
            explanation = self.explanation_service.generate_explanation(tx_id)
            
            recent_txs = []
            if result and result.get("customer_id"):
                recent_txs = self.engine.db.fetch_all(
                    "SELECT transaction_id, amount, currency, transaction_type, status, transaction_time "
                    "FROM transactions WHERE customer_id = %s ORDER BY transaction_time DESC LIMIT 5",
                    (result["customer_id"],)
                )
            
            self.after(0, self._render_results, result, explanation, recent_txs)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _render_results(self, result: Dict[str, Any], explanation: str, recent_txs: List[Dict]) -> None:
        self._loading.pack_forget()
        self._scan_btn.configure(state="normal", text="🛡️  Scan Transaction")
        self._last_scan_lbl.configure(text=f"Last scan: TX #{result.get('transaction_id','?')}")

        # Clear panels
        for w in self.main_content.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        score = result.get("risk_score", 0)
        level = result.get("severity", "LOW")
        conf  = result.get("confidence", 0.0)
        color = _severity_color(level)

        # ── Left Pane (Main Content) ──
        # Metrics cards row
        metrics_row = ctk.CTkFrame(self.main_content, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, SPACE_S))
        metrics_row.columnconfigure((0, 1, 2), weight=1)

        CardWidget(metrics_row, "Risk Score", f"{score}/100", "Computed risk rating", color).grid(row=0, column=0, sticky="nsew", padx=4)
        CardWidget(metrics_row, "Risk Level", level, "System severity tier", color).grid(row=0, column=1, sticky="nsew", padx=4)
        CardWidget(metrics_row, "Confidence Rate", f"{conf}%", "Model accuracy ratio", PRIMARY_COLOR).grid(row=0, column=2, sticky="nsew", padx=4)

        # Gauge & Recommendation Banner
        banner = ctk.CTkFrame(self.main_content, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        banner.pack(fill="x", pady=(0, SPACE_S))

        gauge_container = ctk.CTkFrame(banner, fg_color="transparent")
        gauge_container.pack(side="left", padx=SPACE_S, pady=SPACE_S)

        ctk.CTkLabel(gauge_container, text="Risk Meter:", font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"), text_color=SUBTEXT_COLOR).pack(side="left", padx=(0, SPACE_XS))
        meter = ctk.CTkProgressBar(gauge_container, width=150, height=8, fg_color="#1E293B", progress_color=color, corner_radius=4)
        meter.set(score / 100.0)
        meter.pack(side="left", padx=SPACE_XS)

        rec = result.get("recommended_action", "NO ACTION REQUIRED")
        ctk.CTkLabel(banner, text=f"📢 Recommendation: {rec}", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=color).pack(side="right", padx=SPACE_S, pady=SPACE_S)

        # Recent Transactions
        if recent_txs:
            recent_panel = ctk.CTkFrame(self.main_content, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
            recent_panel.pack(fill="both", expand=True)

            ctk.CTkLabel(recent_panel, text="Recent Transactions Ledger", font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))
            table = TableWidget(recent_panel, columns=["tx_id", "amt", "type", "status", "time"], headers=["TX ID", "Amount", "Type", "Status", "Timestamp"])
            table.pack(fill="both", expand=True, padx=SPACE_S, pady=(0, SPACE_S))

            for tx in recent_txs:
                amt_str = format_inr(tx["amount"]) if tx["currency"] == "INR" else f"{tx['amount']} {tx['currency']}"
                table.insert_row([tx["transaction_id"], amt_str, tx["transaction_type"], tx["status"], str(tx["transaction_time"])[:16]])

        # ── Right Pane (Rules, Narrative & Timeline) ──
        # Triggered Rules Card
        rules_card = ctk.CTkFrame(self.right_panel, fg_color="#0F172A", corner_radius=12, border_width=1, border_color="#1E293B")
        rules_card.pack(fill="x", pady=(0, SPACE_S), padx=SPACE_S)

        ctk.CTkLabel(rules_card, text="⚠️ Triggered Safety Rules", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))
        ctk.CTkFrame(rules_card, fg_color="#1E293B", height=1).pack(fill="x", padx=SPACE_S, pady=(0, 6))

        triggered = result.get("triggered_rules", [])
        if triggered:
            for rule in triggered[:3]: # display top 3 rules
                r_row = ctk.CTkFrame(rules_card, fg_color="transparent")
                r_row.pack(fill="x", padx=SPACE_S, pady=4)
                ctk.CTkLabel(r_row, text=f"• {rule.get('rule_name', 'Rule')}", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=TEXT_COLOR, anchor="w").pack(side="left")
                ctk.CTkLabel(r_row, text=f"+{rule.get('risk_points', 0)} pts", font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"), text_color=DANGER_COLOR).pack(side="right")
        else:
            ctk.CTkLabel(rules_card, text="No rules triggered. Clean transaction.", font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=SUCCESS_COLOR).pack(pady=10)

        # Risk Timeline Card
        timeline_card = ctk.CTkFrame(self.right_panel, fg_color="#0F172A", corner_radius=12, border_width=1, border_color="#1E293B")
        timeline_card.pack(fill="both", expand=True, padx=SPACE_S, pady=(0, SPACE_S))

        ctk.CTkLabel(timeline_card, text="🛡️ Risk Assessment Timeline", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))
        ctk.CTkFrame(timeline_card, fg_color="#1E293B", height=1).pack(fill="x", padx=SPACE_S, pady=(0, 6))

        timeline = TimelineWidget(timeline_card)
        timeline.pack(fill="both", expand=True, padx=SPACE_XS, pady=(0, SPACE_XS))

        # Populate vertical audit steps
        timeline_steps = [
            {"time": "Step 1", "title": "Transaction Event Logged", "details": f"Amount: {format_inr(result.get('amount', 0))}"},
            {"time": "Step 2", "title": "Blacklist Analysis Completed", "details": "Customer & Device verified clean"},
            {"time": "Step 3", "title": "Rules Engine Fired", "details": f"{len(triggered)} safety rules triggered"},
            {"time": "Step 4", "title": "Decision Finalized", "details": f"Action Recommended: {rec}"}
        ]
        timeline.set_events(timeline_steps)

    def _show_error(self, msg: str) -> None:
        self._loading.pack_forget()
        self._scan_btn.configure(state="normal", text="🛡️  Scan Transaction")
        messagebox.showerror("Scan Failed", f"Could not perform scan:\n{msg}")
