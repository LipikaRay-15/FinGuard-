import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any

# Theme references
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend simulator imports
from simulator.fraud_simulator import FraudSimulator

class SimulatorPage(ttk.Frame):
    """
    Simulator Console interface page.
    Exposes fields to define customer size, transaction volumes, and fraud ratio.
    Executes simulator loops asynchronously inside a daemon background thread
    and displays status outputs smoothly without blocking the main event loop.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.simulator = FraudSimulator()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Transaction & Fraud Simulator Console", style="HeaderTitle.TLabel")
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

        self.running_simulation = False
        self._build_layout()

    def _build_layout(self) -> None:
        # Two Columns Split Panel
        self.split_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)
        self.split_frame.pack(fill="both", expand=True)
        self.split_frame.columnconfigure(0, weight=1) # Form panel
        self.split_frame.columnconfigure(1, weight=1) # Results & Status panel

        # Left Column: Configuration Form
        form_card = tk.Frame(self.split_frame, bg=CARD_COLOR, padx=20, pady=20)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        tk.Label(form_card, text="Simulator Configuration", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER).pack(anchor="w", pady=(0, 15))

        # 1. Customers count
        tk.Label(form_card, text="New Customer Profiles Pool:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(5, 2))
        self.cust_entry = tk.Entry(form_card, bg=BG_COLOR, fg=TEXT_COLOR, bd=0, highlightthickness=1, highlightcolor=PRIMARY_COLOR, highlightbackground="#334155", font=FONT_BODY)
        self.cust_entry.insert(0, "10") # low default for fast GUI simulation testing
        self.cust_entry.pack(fill="x", pady=(0, 15), ipady=4)

        # 2. Transactions count
        tk.Label(form_card, text="Transactional Scan Volume:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(5, 2))
        self.tx_entry = tk.Entry(form_card, bg=BG_COLOR, fg=TEXT_COLOR, bd=0, highlightthickness=1, highlightcolor=PRIMARY_COLOR, highlightbackground="#334155", font=FONT_BODY)
        self.tx_entry.insert(0, "50") # low default for fast GUI simulation testing
        self.tx_entry.pack(fill="x", pady=(0, 15), ipady=4)

        # 3. Fraud ratio
        tk.Label(form_card, text="Target Fraud Ratio (Declines %):", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_SUBHEADER).pack(anchor="w", pady=(5, 2))
        self.ratio_combo = ttk.Combobox(form_card, values=["1%", "5%", "10%", "25%", "50%"], state="readonly")
        self.ratio_combo.set("5%")
        self.ratio_combo.pack(fill="x", pady=(0, 25))

        # Launch Button
        self.launch_btn = ttk.Button(form_card, text="🚀 Launch Simulation Run", command=self.start_simulation)
        self.launch_btn.pack(fill="x", ipady=6)

        # Right Column: Status & Run results
        self.right_frame = tk.Frame(self.split_frame, bg=BG_COLOR)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Progress / Status Card
        self.status_card = tk.Frame(self.right_frame, bg=CARD_COLOR, padx=20, pady=20)
        self.status_card.pack(fill="x", pady=(0, 15))

        self.status_title = tk.Label(self.status_card, text="Simulator Status: Idle", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_HEADER)
        self.status_title.pack(anchor="w", pady=(0, 10))

        self.progressbar = ttk.Progressbar(self.status_card, style="Horizontal.TProgressbar", orient="horizontal", mode="indeterminate")
        
        self.status_detail = tk.Label(self.status_card, text="Configure params and launch simulation to seed tables.", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_BODY)
        self.status_detail.pack(anchor="w")

        # Results Summary Card (Hidden initially)
        self.results_card = tk.Frame(self.right_frame, bg=CARD_COLOR, padx=20, pady=20)
        self.results_title = tk.Label(self.results_card, text="Latest Run Results Summary", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.results_title.pack(anchor="w", pady=(0, 15))

        self.results_container = tk.Frame(self.results_card, bg=CARD_COLOR)
        self.results_container.pack(fill="both", expand=True)

    def start_simulation(self) -> None:
        if self.running_simulation:
            return

        # Validate entries
        cust_str = self.cust_entry.get().strip()
        tx_str = self.tx_entry.get().strip()

        try:
            num_cust = int(cust_str)
            num_tx = int(tx_str)
            if num_cust <= 0 or num_tx <= 0:
                raise ValueError("Values must be positive numbers.")
        except ValueError:
            messagebox.showerror("Invalid Parameters", "Customers and Transactions must be positive integers.")
            return

        # Parse ratio
        ratio_str = self.ratio_combo.get().replace("%", "")
        fraud_ratio = float(ratio_str) / 100.0

        # Update UI state
        self.running_simulation = True
        self.launch_btn.configure(state="disabled")
        self.status_title.configure(text="Simulator Status: Running...", fg=WARNING_COLOR)
        self.status_detail.configure(text="Spawning synthetic thread... streaming transactions into event store.")
        self.progressbar.pack(fill="x", pady=10)
        self.progressbar.start(10)
        
        # Hide previous results
        self.results_card.pack_forget()

        # Run thread
        threading.Thread(target=self._run_simulation_worker, args=(num_cust, num_tx, fraud_ratio), daemon=True).start()

    def _run_simulation_worker(self, num_cust: int, num_tx: int, fraud_ratio: float) -> None:
        try:
            summary = self.simulator.run_simulation(
                num_customers=num_cust,
                num_transactions=num_tx,
                fraud_ratio=fraud_ratio
            )
            self.after(0, self._simulation_completed, summary)
        except Exception as e:
            self.after(0, self._simulation_failed, str(e))

    def _simulation_completed(self, summary: Dict[str, Any]) -> None:
        self.running_simulation = False
        self.launch_btn.configure(state="normal")
        self.progressbar.stop()
        self.progressbar.pack_forget()

        self.status_title.configure(text="Simulator Status: Completed Successfully!", fg=SUCCESS_COLOR)
        self.status_detail.configure(text=f"Generated {summary.get('customers_generated', 0)} accounts & {summary.get('transactions_simulated', 0)} event transactions.")

        # Clear old results
        for child in self.results_container.winfo_children():
            child.destroy()

        # Render new results
        fields = [
            ("Customers Generated", summary.get("customers_generated", 0)),
            ("Transactions Simulated", summary.get("transactions_simulated", 0)),
            ("   Approved Volume", summary.get("transactions_approved", 0)),
            ("   Declined Volume", summary.get("transactions_declined", 0)),
            ("   Flagged Volume", summary.get("transactions_flagged", 0)),
            ("Alerts Created", summary.get("alerts_generated", 0)),
            ("Cases Created", summary.get("cases_created", 0)),
            ("Rule Executions", summary.get("rule_executions_logged", 0)),
            ("Audit Logs", summary.get("audit_logs_recorded", 0)),
        ]

        for label, val in fields:
            row = tk.Frame(self.results_container, bg=CARD_COLOR, pady=4)
            row.pack(fill="x")
            
            lbl_key = tk.Label(row, text=label, bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_BODY, width=25, anchor="w")
            lbl_key.pack(side="left")

            lbl_val = tk.Label(row, text=str(val), bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER, anchor="w")
            lbl_val.pack(side="left")

        # Show results
        self.results_card.pack(fill="both", expand=True, pady=(15, 0))
        messagebox.showinfo("Simulation Complete", "FinGuard synthetic simulator run completed successfully!")

    def _simulation_failed(self, error_msg: str) -> None:
        self.running_simulation = False
        self.launch_btn.configure(state="normal")
        self.progressbar.stop()
        self.progressbar.pack_forget()

        self.status_title.configure(text="Simulator Status: Failed", fg=DANGER_COLOR)
        self.status_detail.configure(text=f"Simulation failed with error: {error_msg}")
        messagebox.showerror("Simulation Error", f"Simulator run crashed: {error_msg}")
