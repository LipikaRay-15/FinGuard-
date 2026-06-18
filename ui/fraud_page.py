import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.cards import CardWidget
from ui.widgets.status_badges import StatusBadge
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend imports
from engines import FraudDetectionEngine
from services.risk_explanation_service import RiskExplanationService

class FraudPage(ttk.Frame):
    """
    Live Fraud Scanning interface. Queries transaction IDs, executes
    rule checking, and generates explainable audit summaries.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.engine = FraudDetectionEngine()
        self.explanation_service = RiskExplanationService()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Live Fraud Scanning & Assessment", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        # Top Control Area (Input Transaction ID)
        self.control_frame = tk.Frame(self, bg=CARD_COLOR, padx=16, pady=16)
        self.control_frame.pack(fill="x", pady=(0, 20))

        self.input_lbl = tk.Label(self.control_frame, text="Enter Transaction ID to scan:", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER)
        self.input_lbl.pack(side="left", padx=(0, 15))

        self.tx_entry = ttk.Entry(self.control_frame, style="TEntry", width=20)
        self.tx_entry.pack(side="left", padx=(0, 15))
        self.tx_entry.focus_set()
        self.tx_entry.bind("<Return>", lambda e: self.scan_transaction())

        self.scan_btn = ttk.Button(self.control_frame, text="🛡️ Scan Transaction", command=self.scan_transaction)
        self.scan_btn.pack(side="left")

        # Scrollable container for scan results (initially hidden)
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

        # Main contents container inside scroll frame
        self.results_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)

        # Loading frame
        self.loading_lbl = tk.Label(self.scroll_frame, text="Analyzing transaction risk patterns...", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER)

    def scan_transaction(self) -> None:
        tx_id_str = self.tx_entry.get().strip()
        if not tx_id_str:
            messagebox.showwarning("Input Required", "Please enter a valid Transaction ID.")
            return

        try:
            tx_id = int(tx_id_str)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Transaction ID must be an integer.")
            return

        # Show loading indicator
        self.results_frame.pack_forget()
        self.canvas.pack_forget()
        self.scrollbar.pack_forget()
        
        self.loading_lbl.pack(pady=40)

        # Execute fraud assessment asynchronously
        threading.Thread(target=self._scan_worker, args=(tx_id,), daemon=True).start()

    def _scan_worker(self, tx_id: int) -> None:
        try:
            # Run scan engine
            result = self.engine.detect_fraud(tx_id)
            
            # Fetch explainable description
            explanation = self.explanation_service.generate_explanation(tx_id)
            
            self.after(0, self._render_results, result, explanation)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _render_results(self, result: Dict[str, Any], explanation: str) -> None:
        self.loading_lbl.pack_forget()
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.results_frame.pack(fill="both", expand=True)

        # Clear old result widgets
        for child in self.results_frame.winfo_children():
            child.destroy()

        # Score & Decision cards panel
        cards_grid = tk.Frame(self.results_frame, bg=BG_COLOR)
        cards_grid.pack(fill="x", pady=(0, 20))
        cards_grid.columnconfigure((0, 1, 2), weight=1, uniform="group2")

        # Score card
        score_val = result.get("risk_score", 0)
        c_score = CardWidget(cards_grid, "RISK SCORE", f"{score_val}/100", "Computed rating")
        c_score.grid(row=0, column=0, padx=6, sticky="nsew")

        # Level card
        level = result.get("severity", "LOW")
        c_level = CardWidget(cards_grid, "RISK LEVEL", level, "System category threshold", trend_color=self._get_severity_color(level))
        c_level.grid(row=0, column=1, padx=6, sticky="nsew")

        # Confidence card
        conf = result.get("confidence", 0.0)
        c_conf = CardWidget(cards_grid, "DECISION CONFIDENCE", f"{conf}%", "Profile completeness ratio")
        c_conf.grid(row=0, column=2, padx=6, sticky="nsew")

        # Summary Split panel
        split_panel = tk.Frame(self.results_frame, bg=BG_COLOR)
        split_panel.pack(fill="both", expand=True)
        split_panel.columnconfigure(0, weight=1) # Left (Checklist)
        split_panel.columnconfigure(1, weight=1) # Right (Explanation)

        # Left Column: Rules details
        rules_container = tk.Frame(split_panel, bg=CARD_COLOR, padx=16, pady=16)
        rules_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        rules_lbl = tk.Label(rules_container, text="Triggered Safety Rules", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        rules_lbl.pack(anchor="w", pady=(0, 15))

        triggered = result.get("triggered_rules", [])
        if triggered:
            for rule in triggered:
                row = tk.Frame(rules_container, bg=CARD_COLOR, pady=6)
                row.pack(fill="x")
                
                check_lbl = tk.Label(row, text="✓", bg=CARD_COLOR, fg=DANGER_COLOR, font=("Segoe UI", 12, "bold"))
                check_lbl.pack(side="left", padx=(0, 8))

                txt_frame = tk.Frame(row, bg=CARD_COLOR)
                txt_frame.pack(side="left", fill="x", expand=True)

                r_title = tk.Label(txt_frame, text=f"{rule['rule_name']} (+{rule['risk_points']} pts)", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER)
                r_title.pack(anchor="w")

                r_desc = tk.Label(txt_frame, text=rule.get("reason", ""), bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, wraplength=300, justify="left")
                r_desc.pack(anchor="w")
        else:
            ok_lbl = tk.Label(rules_container, text="No rules triggered. Clean transaction.", bg=CARD_COLOR, fg=SUCCESS_COLOR, font=FONT_BODY)
            ok_lbl.pack(pady=40)

        # Right Column: Explanation text
        exp_container = tk.Frame(split_panel, bg=CARD_COLOR, padx=16, pady=16)
        exp_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        exp_lbl = tk.Label(exp_container, text="Explainable Risk Narrative", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        exp_lbl.pack(anchor="w", pady=(0, 15))

        exp_txt = tk.Text(
            exp_container,
            bg="#0F172A",
            fg=TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=FONT_BODY,
            wrap="word",
            padx=10,
            pady=10
        )
        exp_txt.insert("1.0", explanation)
        exp_txt.configure(state="disabled")
        exp_txt.pack(fill="both", expand=True)

    def _get_severity_color(self, level: str) -> str:
        level = level.upper()
        if level == "CRITICAL":
            return DANGER_COLOR
        elif level == "HIGH":
            return "#F97316" # Orange color
        elif level == "MEDIUM":
            return WARNING_COLOR
        else:
            return SUCCESS_COLOR

    def _show_error(self, err_msg: str) -> None:
        self.loading_lbl.pack_forget()
        messagebox.showerror("Scan Failed", f"Could not perform scan: {err_msg}")
