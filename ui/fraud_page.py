import threading
import tkinter as tk
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


RULE_DETAILS = {
    "LOCATION JUMP": {
        "desc": "Transfers detected at impossible speeds between distant locations.",
        "level": "CRITICAL"
    },
    "RAPID VELOCITY": {
        "desc": "Multiple transactions detected within a short period.",
        "level": "HIGH"
    },
    "RAPID VELOCITY LIMIT": {
        "desc": "Multiple transactions detected within a short period.",
        "level": "HIGH"
    },
    "FAILED ATTEMPTS": {
        "desc": "Multiple consecutive transaction declines recently.",
        "level": "HIGH"
    },
    "HIGH TRANSACTION AMOUNT": {
        "desc": "Transaction amount is unusually high for standard accounts.",
        "level": "HIGH"
    },
    "AMOUNT DEVIATION": {
        "desc": "Amount deviates significantly from customer's historical average.",
        "level": "MEDIUM"
    },
    "DORMANT ACCOUNT": {
        "desc": "Sudden activity on an account inactive for 90+ days.",
        "level": "MEDIUM"
    },
    "HIGH-RISK MERCHANT": {
        "desc": "Transaction routed to high-risk merchant category (e.g. gambling).",
        "level": "HIGH"
    },
    "HIGH-RISK MERCHANT CATEGORY": {
        "desc": "Transaction routed to high-risk merchant category (e.g. gambling).",
        "level": "HIGH"
    },
    "UNUSUAL FREQUENCY": {
        "desc": "Transaction frequency exceeds the customer's average volume.",
        "level": "MEDIUM"
    },
    "NEW DEVICE": {
        "desc": "Transaction originated from an unknown or unregistered device.",
        "level": "MEDIUM"
    },
    "NEW DEVICE DETECTED": {
        "desc": "Transaction originated from an unknown or unregistered device.",
        "level": "MEDIUM"
    },
    "DIFFERENT CITY": {
        "desc": "Transaction completed in a new or unusual city.",
        "level": "LOW"
    },
    "NIGHT TRANSACTION": {
        "desc": "Transaction initiated late at night (between 10 PM and 6 AM).",
        "level": "LOW"
    }
}


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


class CircularGauge(ctk.CTkCanvas):
    """Circular animated risk gauge meter (0-100 score)."""
    def __init__(self, parent, size=150, bg_color=CARD_COLOR, **kwargs):
        super().__init__(parent, width=size, height=size, bg=bg_color, highlightthickness=0, **kwargs)
        self.size = size
        self.score = 0
        self.target_score = 0
        self.color = SUCCESS_COLOR
        self.draw_gauge()

    def draw_gauge(self):
        self.delete("all")
        # Draw background arc
        self.create_arc(15, 15, self.size - 15, self.size - 15, start=-40, extent=260,
                        outline="#1E293B", width=12, style="arc")
        
        # Draw progress arc (drawn counterclockwise from start=220)
        extent = (self.score / 100.0) * 260
        self.create_arc(15, 15, self.size - 15, self.size - 15, start=220, extent=-extent,
                        outline=self.color, width=12, style="arc")
        
        # Draw score text
        self.create_text(self.size // 2, self.size // 2 - 10, text=f"{self.score}",
                         font=(FONT_FAMILY, 24, "bold"), fill=TEXT_COLOR)
        self.create_text(self.size // 2, self.size // 2 + 18, text="Risk Score",
                         font=(FONT_FAMILY, 9, "bold"), fill=SUBTEXT_COLOR)

    def set_score(self, score, color):
        self.target_score = score
        self.color = color
        self.animate(0)

    def animate(self, step):
        if step <= 15:
            current = int((self.target_score * step) / 15.0)
            self.score = current
            self.draw_gauge()
            self.after(15, lambda: self.animate(step + 1))


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

        # Redesigned scan button with Stripe-like professional layout
        self._scan_btn = ctk.CTkButton(
            self.toolbar, text="🛡️  Scan Transaction",
            width=200, height=38, corner_radius=8,
            fg_color="#2563EB", hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self.scan_transaction
        )
        self._scan_btn.pack(side="left", padx=SPACE_S)

        self._last_scan_lbl = ctk.CTkLabel(self.toolbar, text="",
                                            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                            text_color=SUBTEXT_COLOR)
        self._last_scan_lbl.pack(side="right", padx=SPACE_S)

        # ── 2. Empty State ──
        self._render_empty_state()
        self._load_default_transaction()

    def _render_empty_state(self) -> None:
        for w in self.main_content.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        # Left side empty state
        empty_box = ctk.CTkFrame(self.main_content, fg_color="transparent")
        empty_box.pack(expand=True, fill="both", pady=80)

        icon_lbl = ctk.CTkLabel(
            empty_box, text="🔍",
            font=ctk.CTkFont(family=FONT_FAMILY, size=64),
            text_color=SUBTEXT_COLOR
        )
        icon_lbl.pack(pady=(0, SPACE_S))

        msg_lbl = ctk.CTkLabel(
            empty_box, text="No transaction analyzed yet.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_COLOR
        )
        msg_lbl.pack(pady=4)

        sub_lbl = ctk.CTkLabel(
            empty_box, text="Enter a Transaction ID above and click Scan to perform live fraud analysis.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=SUBTEXT_COLOR
        )
        sub_lbl.pack()

        # Right side empty state
        right_empty = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        right_empty.pack(expand=True, fill="both", pady=80)
        ctk.CTkLabel(right_empty, text="🛡️  Awaiting Scan", font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"), text_color=SUBTEXT_COLOR).pack()

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
        
        # Left pane loading
        left_loader = ctk.CTkFrame(self.main_content, fg_color="transparent")
        left_loader.pack(expand=True, fill="both", pady=100)
        ctk.CTkLabel(left_loader, text="⏳  Analyzing transaction...",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack()
        ctk.CTkLabel(left_loader, text="Assessing security checkpoints & historical pattern checks",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                     text_color=SUBTEXT_COLOR).pack(pady=(4, 0))

        # Right pane loading
        right_loader = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        right_loader.pack(expand=True, fill="both", pady=100)
        ctk.CTkLabel(right_loader, text="🛡️  Generating Summary...",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=SUBTEXT_COLOR).pack()

        self._scan_btn.configure(state="disabled", text="⏳  Scanning…")
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
        self._scan_btn.configure(state="normal", text="🛡️  Scan Transaction")
        self._last_scan_lbl.configure(text=f"Last scan: TX #{result.get('transaction_id','?')}")

        # Clear panels
        for w in self.main_content.winfo_children(): w.destroy()
        for w in self.right_panel.winfo_children(): w.destroy()

        score = result.get("risk_score", 0)
        level = result.get("severity", "LOW")
        conf  = result.get("confidence", 0.0)
        color = _severity_color(level)

        # ── Left Pane (Main Content - 70%) ──
        # Metrics cards row
        metrics_row = ctk.CTkFrame(self.main_content, fg_color="transparent")
        metrics_row.pack(fill="x", pady=(0, SPACE_S))
        metrics_row.columnconfigure((0, 1, 2), weight=1)

        # Large Score Card
        score_val = f"{score} / 100"
        CardWidget(metrics_row, "Risk Score", score_val, "Computed risk rating", color).grid(row=0, column=0, sticky="nsew", padx=4)
        
        # Risk Level Card
        CardWidget(metrics_row, "Risk Level", level, "System severity tier", color).grid(row=0, column=1, sticky="nsew", padx=4)
        
        # Confidence Rate Card
        CardWidget(metrics_row, "Confidence Rate", f"{conf}%", "Model accuracy ratio", PRIMARY_COLOR).grid(row=0, column=2, sticky="nsew", padx=4)

        # Triggered Rules Card (With static explanations and risk badges)
        rules_card = ctk.CTkFrame(self.main_content, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        rules_card.pack(fill="x", pady=(0, SPACE_S))

        ctk.CTkLabel(rules_card, text="⚠️  Triggered Safety Rules", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkFrame(rules_card, fg_color="#1E293B", height=1).pack(fill="x", padx=16, pady=(0, 6))

        triggered = result.get("triggered_rules", [])
        if triggered:
            for i, rule in enumerate(triggered):
                if i > 0:
                    # Divider between rules
                    ctk.CTkFrame(rules_card, fg_color="#1E293B", height=1).pack(fill="x", padx=16, pady=4)

                r_row = ctk.CTkFrame(rules_card, fg_color="transparent")
                r_row.pack(fill="x", padx=16, pady=6)
                
                # Container for rule name and description
                left_col = ctk.CTkFrame(r_row, fg_color="transparent")
                left_col.pack(side="left", fill="both", expand=True)

                raw_name = rule.get('rule_name', 'Rule')
                norm_name = raw_name.upper().strip()
                details = RULE_DETAILS.get(norm_name, {
                    "desc": "Safety rule triggered by live risk scoring analysis.",
                    "level": "MEDIUM"
                })

                # Checkmarked Rule Name
                ctk.CTkLabel(
                    left_col, text=f"✓  {raw_name}",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                    text_color=TEXT_COLOR, anchor="w"
                ).pack(anchor="w")

                # Subtitle description
                ctk.CTkLabel(
                    left_col, text=details["desc"],
                    font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                    text_color=SUBTEXT_COLOR, anchor="w"
                ).pack(anchor="w", pady=(2, 0))

                # Right container for Risk Impact colored badge
                badge_colors = {
                    "LOW": "#10B981",
                    "MEDIUM": "#F59E0B",
                    "HIGH": "#F97316",
                    "CRITICAL": "#EF4444"
                }
                badge_bg = badge_colors.get(details["level"], "#F59E0B")
                
                badge_frame = ctk.CTkFrame(r_row, fg_color="transparent")
                badge_frame.pack(side="right", padx=(10, 0), anchor="center")

                ctk.CTkLabel(
                    badge_frame, text=details["level"],
                    font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="bold"),
                    text_color="#FFFFFF",
                    fg_color=badge_bg,
                    corner_radius=6,
                    width=70,
                    height=20
                ).pack()
        else:
            ctk.CTkLabel(rules_card, text="No rules triggered. Clean transaction.", font=ctk.CTkFont(family=FONT_FAMILY, size=11), text_color=SUCCESS_COLOR).pack(pady=12, anchor="w", padx=16)

        # Recent Transactions
        if recent_txs:
            recent_panel = ctk.CTkFrame(self.main_content, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
            recent_panel.pack(fill="both", expand=True)

            ctk.CTkLabel(recent_panel, text="📋  Recent Transactions Ledger", font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"), text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))
            table = TableWidget(recent_panel, columns=["tx_id", "amt", "type", "status", "time"], headers=["TX ID", "Amount", "Type", "Status", "Timestamp"])
            table.pack(fill="both", expand=True, padx=8, pady=(0, 12))

            for tx in recent_txs:
                amt_str = format_inr(tx["amount"])
                table.insert_row([tx["transaction_id"], amt_str, tx["transaction_type"], tx["status"], str(tx["transaction_time"])[:16]])

        # ── Right Pane (Fraud Summary Panel - 30%) ──
        summary_panel = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent",
                                              scrollbar_fg_color=CARD_COLOR,
                                              scrollbar_button_color="#334155")
        summary_panel.pack(fill="both", expand=True, padx=SPACE_XS, pady=SPACE_XS)

        # 1. Circular Risk Meter Gauge
        gauge_card = ctk.CTkFrame(summary_panel, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        gauge_card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            gauge_card, text="📊  Risk Meter",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=16, pady=(14, 4))
        
        gauge_container = ctk.CTkFrame(gauge_card, fg_color="transparent")
        gauge_container.pack(pady=(4, 16))
        
        gauge = CircularGauge(gauge_container, size=150, bg_color=CARD_COLOR)
        gauge.pack()
        gauge.set_score(score, color)

        # 2. Decision Card
        rec_card = ctk.CTkFrame(summary_panel, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        rec_card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            rec_card, text="Decision",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=16, pady=(14, 4))
        
        # Divider line
        ctk.CTkFrame(rec_card, fg_color="#1E293B", height=1).pack(fill="x", padx=16, pady=(0, 6))

        raw_rec = result.get("recommended_action", "REVIEW").upper()
        if "APPROVE" in raw_rec:
            header_text = "Transaction Approved"
            badge_text = "APPROVE"
            badge_bg = "#10B981"
            line1 = "Transaction risk is within the acceptable threshold."
            line2 = "No further security checks are required."
        elif "BLOCK" in raw_rec or "DECLINE" in raw_rec:
            header_text = "Transaction Blocked"
            badge_text = "BLOCK"
            badge_bg = "#EF4444"
            line1 = "Transaction exhibits severe fraudulent pattern matching."
            line2 = "Account suspension and immediate freeze recommended."
        else:
            header_text = "Requires Analyst Review"
            badge_text = "REVIEW"
            badge_bg = "#F59E0B" # Amber/Orange
            line1 = "Transaction risk exceeded the automated approval threshold."
            line2 = "Forward to Fraud Operations team for investigation."

        content_inner = ctk.CTkFrame(rec_card, fg_color="transparent")
        content_inner.pack(fill="x", padx=16, pady=(4, 16))

        # Show: Requires Analyst Review
        ctk.CTkLabel(
            content_inner, text=header_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_COLOR, anchor="w"
        ).pack(anchor="w", pady=(0, 6))

        # Status row with a compact pill badge (11pt Bold, White on Amber/Red/Green)
        status_row = ctk.CTkFrame(content_inner, fg_color="transparent")
        status_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            status_row, text="Status",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w"
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            status_row, text=badge_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=badge_bg,
            corner_radius=12,
            width=70,
            height=22
        ).pack(side="left")

        # Paragraph text lines (11pt Segoe UI)
        ctk.CTkLabel(
            content_inner, text=line1,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w", justify="left"
        ).pack(anchor="w", pady=(0, 2))

        ctk.CTkLabel(
            content_inner, text=line2,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w", justify="left"
        ).pack(anchor="w")

        # 3. Investigation Status Card
        alert_card = ctk.CTkFrame(summary_panel, fg_color=CARD_COLOR, corner_radius=12, border_width=1, border_color="#2D3748")
        alert_card.pack(fill="x", pady=(0, 16))
        
        ctk.CTkLabel(
            alert_card, text="Investigation Status",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(anchor="w", padx=16, pady=(14, 4))

        # Divider line
        ctk.CTkFrame(alert_card, fg_color="#1E293B", height=1).pack(fill="x", padx=16, pady=(0, 6))

        raw_status = result.get("status", "OPEN").upper()
        if "CLOSED" in raw_status or "RESOLVED" in raw_status:
            badge_text = "CLOSED"
            badge_bg = "#10B981"
            desc_text = "Case investigation has been finalized and closed."
        elif "REVIEW" in raw_status:
            badge_text = "UNDER REVIEW"
            badge_bg = "#F59E0B"
            desc_text = "Case is actively being assessed by an assigned fraud analyst."
        else:
            badge_text = "OPEN"
            badge_bg = "#2563EB" # Blue
            desc_text = "Case has been generated and is waiting for analyst assignment."

        alert_inner = ctk.CTkFrame(alert_card, fg_color="transparent")
        alert_inner.pack(fill="x", padx=16, pady=(4, 16))

        # Row for Current State and Badge
        state_row = ctk.CTkFrame(alert_inner, fg_color="transparent")
        state_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            state_row, text="Current State",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_COLOR, anchor="w"
        ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            state_row, text=badge_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color="#FFFFFF",
            fg_color=badge_bg,
            corner_radius=12,
            width=90,
            height=22
        ).pack(side="left")

        # Description text
        ctk.CTkLabel(
            alert_inner, text=desc_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR, anchor="w", justify="left",
            wraplength=230
        ).pack(anchor="w", pady=(0, 12))

        # Optional: Vertical Timeline Style
        timeline_frame = ctk.CTkFrame(alert_inner, fg_color="transparent")
        timeline_frame.pack(fill="x", pady=(8, 0))

        stages = [
            ("Alert Generated", ["OPEN", "UNDER REVIEW", "CLOSED"]),
            ("OPEN", ["OPEN", "UNDER REVIEW", "CLOSED"]),
            ("Awaiting Assignment", ["OPEN", "UNDER REVIEW", "CLOSED"]),
            ("Under Review", ["UNDER REVIEW", "CLOSED"]),
            ("Closed", ["CLOSED"])
        ]

        # Determine current stage name
        if badge_text == "CLOSED":
            current_stage_name = "Closed"
        elif badge_text == "UNDER REVIEW":
            current_stage_name = "Under Review"
        else:
            current_stage_name = "OPEN"

        for idx, (stage_name, active_for_badges) in enumerate(stages):
            is_active = (stage_name == current_stage_name)
            is_completed = (badge_text in active_for_badges) and not is_active

            if is_active:
                bullet_color = badge_bg
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

            step_row = ctk.CTkFrame(timeline_frame, fg_color="transparent")
            step_row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                step_row, text=bullet_char,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=bullet_color, width=15
            ).pack(side="left", padx=(4, 8))

            ctk.CTkLabel(
                step_row, text=stage_name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight=font_weight),
                text_color=text_color
            ).pack(side="left")

            if idx < len(stages) - 1:
                line_color = "#10B981" if is_completed else "#475569"
                ctk.CTkLabel(
                    timeline_frame, text="│",
                    font=ctk.CTkFont(family=FONT_FAMILY, size=8),
                    text_color=line_color, width=15, height=8
                ).pack(anchor="w", padx=(4, 8))

    def _show_error(self, msg: str) -> None:
        self._scan_btn.configure(state="normal", text="🛡️  Scan Transaction")
        self._render_empty_state()
        messagebox.showerror("Scan Failed", f"Could not perform scan:\n{msg}")
