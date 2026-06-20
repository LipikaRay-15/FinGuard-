import threading
import time
from typing import Any, Dict
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, format_inr
)
from simulator import FraudSimulator


class SimulatorPage(ctk.CTkFrame):
    """Transaction stream simulator console."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.simulator  = FraudSimulator()
        self._running   = False
        self._log_lines = []

        # ── Page Header (Fixed at the top, matching Dashboard exactly) ──
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=52)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Transaction Stream Simulator",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        # Live status indicator
        self._status_dot = ctk.CTkLabel(
            hdr, text="⬤  Idle",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=SUBTEXT_COLOR
        )
        self._status_dot.pack(side="right")

        # ── Scrollable Body (Matching Dashboard exactly) ──
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=BG_COLOR,
            scrollbar_button_color="#334155"
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=12)

        # Main content frame inside the scrollable container
        body = ctk.CTkFrame(self._scroll, fg_color="transparent")
        body.pack(fill="both", expand=True, pady=(0, 32))

        # Left Column: config form
        left = ctk.CTkFrame(body, fg_color=CARD_COLOR, corner_radius=12)
        self._build_config_panel(left)

        # Right Column: console + progress + results
        right = ctk.CTkFrame(body, fg_color="transparent")
        self._build_console_panel(right)

        # Responsive layout adjust: side-by-side (>850px) or stacked (<850px)
        def _adjust_layout(event=None) -> None:
            w = self._scroll.winfo_width()
            if w <= 100:
                return
            if w < 850:
                body.columnconfigure(0, weight=1)
                body.columnconfigure(1, weight=0)
                left.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 12))
                right.grid(row=1, column=0, sticky="nsew", padx=0, pady=(12, 0))
            else:
                body.columnconfigure(0, weight=2)
                body.columnconfigure(1, weight=3)
                left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
                right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        self._scroll.bind("<Configure>", _adjust_layout, add="+")

    # ── Config Panel ──────────────────────────────────────────────────────

    def _build_config_panel(self, parent) -> None:
        ctk.CTkLabel(parent, text="⚙️  Simulation Parameters",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(16, 4))
        ctk.CTkFrame(parent, fg_color="#2D3748", height=1).pack(fill="x", padx=16, pady=(0, 12))

        form = ctk.CTkFrame(parent, fg_color="transparent")
        form.pack(fill="x", padx=16)

        self._inputs: Dict[str, Any] = {}
        fields = [
            ("customers",    "Number of Customers",        "100"),
            ("transactions", "Transactions per Customer",  "5"),
            ("fraud_rate",   "Fraud Injection Rate (%)",   "15"),
            ("delay_ms",     "Delay Between TX (ms)",      "0"),
        ]

        for key, label, default in fields:
            wrap = ctk.CTkFrame(form, fg_color="transparent")
            wrap.pack(fill="x", pady=6)

            ctk.CTkLabel(wrap, text=label,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                         text_color=SUBTEXT_COLOR, anchor="w").pack(anchor="w", pady=(0, 3))

            ent = ctk.CTkEntry(wrap, fg_color=BG_COLOR, border_color="#334155",
                               text_color=TEXT_COLOR,
                               font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                               height=40, corner_radius=8)
            ent.insert(0, default)
            ent.pack(fill="x")
            self._inputs[key] = ent

        # Fraud mode switch row (vertically centered)
        switch_row = ctk.CTkFrame(form, fg_color="transparent")
        switch_row.pack(fill="x", pady=10)
        ctk.CTkLabel(switch_row, text="Enable Fraud Injection:",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                     text_color=SUBTEXT_COLOR).pack(side="left")
        self._fraud_switch = ctk.CTkSwitch(
            switch_row, text="",
            fg_color="#334155", progress_color=DANGER_COLOR,
            button_color=TEXT_COLOR,
            onvalue=True, offvalue=False
        )
        self._fraud_switch.select()
        self._fraud_switch.pack(side="right", padx=(0, 4))

        # Separator
        ctk.CTkFrame(parent, fg_color="#2D3748", height=1).pack(fill="x", padx=16, pady=16)

        # Warning label with wrapping
        self._warning_lbl = ctk.CTkLabel(
            parent,
            text="⚠  Simulator generates synthetic transaction data only. No real funds are affected.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color="#F59E0B", justify="center",
            wraplength=260
        )
        self._warning_lbl.pack(padx=16, pady=(0, 16))

        # Bind warning wraplength on left panel resize
        def _on_left_configure(event) -> None:
            w = event.width - 32
            if w > 50:
                self._warning_lbl.configure(wraplength=w)
        parent.bind("<Configure>", _on_left_configure, add="+")

        # Run button
        self._run_btn = ctk.CTkButton(
            parent, text="▶  Launch Simulation",
            height=44, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._start_simulation
        )
        self._run_btn.pack(fill="x", padx=16, pady=(0, 8))

        self._stop_btn = ctk.CTkButton(
            parent, text="⏹  Stop",
            height=36, corner_radius=8,
            fg_color=DANGER_COLOR, hover_color="#DC2626",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            command=self._stop_simulation,
            state="disabled"
        )
        self._stop_btn.pack(fill="x", padx=16, pady=(0, 16))

    # ── Console Panel ─────────────────────────────────────────────────────

    def _build_console_panel(self, parent) -> None:
        # Progress section
        prog_card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        prog_card.pack(fill="x", pady=(0, 12))

        prog_content = ctk.CTkFrame(prog_card, fg_color="transparent")
        prog_content.pack(fill="both", expand=True, padx=16, pady=16)

        prog_row = ctk.CTkFrame(prog_content, fg_color="transparent")
        prog_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(prog_row, text="Progress Status",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        self._pct_lbl = ctk.CTkLabel(prog_row, text="--",
                                      font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                                      text_color=PRIMARY_COLOR)
        self._pct_lbl.pack(side="right")

        self._progress = ctk.CTkProgressBar(
            prog_content, height=8,
            fg_color="#1E293B", progress_color=PRIMARY_COLOR, corner_radius=4
        )
        self._progress.set(0)
        self._progress.pack(fill="x", pady=(0, 12))

        # Dynamic details grid inside progress card
        details_frame = ctk.CTkFrame(prog_content, fg_color="transparent")
        details_frame.pack(fill="x")
        details_frame.columnconfigure((0, 1), weight=1)

        items = [
            ("Current Customer",      "cust"),
            ("Current Transaction",   "tx"),
            ("Transactions Generated", "gen"),
            ("Frauds Injected",       "frauds"),
            ("Elapsed Time",          "elapsed")
        ]

        self._progress_widgets = {}
        for idx, (label, key) in enumerate(items):
            row = idx // 2
            col = idx % 2
            
            cell = ctk.CTkFrame(details_frame, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
            
            ctk.CTkLabel(cell, text=label + ": ",
                         font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                         text_color=SUBTEXT_COLOR).pack(side="left")
                         
            val_lbl = ctk.CTkLabel(cell, text="--",
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                                    text_color=TEXT_COLOR)
            val_lbl.pack(side="left")
            self._progress_widgets[key] = val_lbl

        # Console log
        log_card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        log_card.pack(fill="x", pady=(0, 12))

        log_hdr = ctk.CTkFrame(log_card, fg_color="transparent")
        log_hdr.pack(fill="x", padx=16, pady=(12, 0))

        ctk.CTkLabel(log_hdr, text="🖥  Simulation Console",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        ctk.CTkButton(log_hdr, text="Clear", width=60, height=26,
                      corner_radius=6, fg_color="#334155", hover_color="#475569",
                      text_color=SUBTEXT_COLOR,
                      font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                      command=self._clear_log).pack(side="right")

        self._log_box = ctk.CTkTextbox(
            log_card, fg_color="#0A0F1E",
            text_color="#00FF88",  # Terminal green-on-dark
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=8,
            height=320
        )
        self._log_box.pack(fill="x", padx=8, pady=(8, 12))
        self._log_box.configure(state="disabled")
        self._log("FinGuard Simulator Console v3.0 — ready.")
        self._log("Configure parameters and click 'Launch Simulation'.")

        # Results summary statistics panel
        self._results_card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        self._results_card.pack(fill="x")
        
        ctk.CTkLabel(self._results_card, text="📊  Simulation Statistics",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkFrame(self._results_card, fg_color="#2D3748", height=1).pack(fill="x", padx=16, pady=(0, 12))

        self.stats_frame = ctk.CTkFrame(self._results_card, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=16, pady=(0, 12))
        self.stats_frame.columnconfigure((0, 1, 2), weight=1)

        self._stat_widgets = {}
        fields = [
            ("total",    "Total Transactions"),
            ("fraud",    "Fraud Transactions"),
            ("success",  "Success Rate"),
            ("declined", "Declined Transactions"),
            ("average",  "Average Amount"),
            ("alerts",   "Risk Alerts Generated"),
        ]

        for idx, (key, label) in enumerate(fields):
            row = idx // 3
            col = idx % 3
            cell = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="nsew", padx=8, pady=6)
            
            ctk.CTkLabel(cell, text=label,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                         text_color=SUBTEXT_COLOR).pack(anchor="center")
            
            val_lbl = ctk.CTkLabel(cell, text="--",
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                                    text_color=TEXT_COLOR)
            val_lbl.pack(anchor="center", pady=(2, 0))
            self._stat_widgets[key] = val_lbl

    # ── Logging helpers ───────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"> {msg}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")

    # ── Simulation Control ────────────────────────────────────────────────

    def _start_simulation(self) -> None:
        if self._running:
            return
        try:
            n_customers    = int(self._inputs["customers"].get().strip())
            n_tx_per_cust  = int(self._inputs["transactions"].get().strip())
            fraud_rate     = float(self._inputs["fraud_rate"].get().strip()) / 100
            inject_fraud   = self._fraud_switch.get()
        except ValueError:
            messagebox.showwarning("Invalid Config", "All parameter fields must be valid numbers.")
            return

        if n_customers <= 0 or n_tx_per_cust <= 0:
            messagebox.showwarning("Invalid", "Customers and Transactions must be > 0.")
            return

        total_tx = n_customers * n_tx_per_cust

        self._running = True
        self._run_btn.configure(state="disabled", text="Running…")
        self._stop_btn.configure(state="normal")
        self._status_dot.configure(text="⬤  RUNNING", text_color=SUCCESS_COLOR)
        self._progress.configure(mode="indeterminate")
        self._progress.start()
        self._pct_lbl.configure(text="Running…")

        # Reset statistics labels to "--"
        for lbl in self._stat_widgets.values():
            lbl.configure(text="--")

        self._log(f"Starting simulation: {n_customers} customers × {n_tx_per_cust} TX = "
                  f"{total_tx} total events")
        self._log(f"Fraud injection: {'ON' if inject_fraud else 'OFF'} "
                  f"({fraud_rate * 100:.0f}% rate)")
        self._log("─" * 50)

        # Initialize progress tracking parameters
        try:
            self._initial_tx_count = int(self.simulator.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions")["cnt"] or 0)
            self._initial_fraud_count = int(self.simulator.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions WHERE status = 'DECLINED'")["cnt"] or 0)
        except Exception:
            self._initial_tx_count = 0
            self._initial_fraud_count = 0
            
        self._start_time = time.time()
        self._total_tx = total_tx
        self._fraud_rate = fraud_rate
        
        self._update_progress_loop()

        threading.Thread(target=self._simulation_worker,
                         args=(n_customers, total_tx, fraud_rate if inject_fraud else 0.0),
                         daemon=True).start()

    def _update_progress_loop(self) -> None:
        if not self._running:
            return
            
        try:
            current_tx = int(self.simulator.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions")["cnt"] or 0)
            current_fraud = int(self.simulator.db.fetch_one("SELECT COUNT(*) as cnt FROM transactions WHERE status = 'DECLINED'")["cnt"] or 0)
        except Exception:
            current_tx = self._initial_tx_count
            current_fraud = self._initial_fraud_count
            
        generated = max(0, current_tx - self._initial_tx_count)
        frauds = max(0, current_fraud - self._initial_fraud_count)
        
        pct = min(1.0, generated / self._total_tx) if self._total_tx > 0 else 0.0
        elapsed = time.time() - self._start_time
        
        self._progress.set(pct)
        self._pct_lbl.configure(text=f"{int(pct * 100)}%")
        
        self._progress_widgets["gen"].configure(text=f"{generated:,} / {self._total_tx:,}")
        self._progress_widgets["frauds"].configure(text=f"{frauds:,}")
        self._progress_widgets["elapsed"].configure(text=f"{elapsed:.1f}s")
        
        if generated > 0:
            self._progress_widgets["cust"].configure(text=f"ID #{self._initial_tx_count + generated}")
            self._progress_widgets["tx"].configure(text=f"TX #{self._initial_tx_count + generated}")
        else:
            self._progress_widgets["cust"].configure(text="--")
            self._progress_widgets["tx"].configure(text="--")
            
        self.after(200, self._update_progress_loop)

    def _stop_simulation(self) -> None:
        self._running = False
        self._log("⏹  Simulation stop requested.")

    def _simulation_worker(self, n_customers: int, n_transactions: int,
                            fraud_ratio: float) -> None:
        try:
            self.after(0, lambda: self._log(f"Generating {n_customers} customers…"))
            results = self.simulator.run_simulation(
                num_customers=n_customers,
                num_transactions=n_transactions,
                fraud_ratio=fraud_ratio
            )
            if self._running:
                self.after(0, self._on_complete, results)
            else:
                self.after(0, self._on_stopped)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_complete(self, results: Dict) -> None:
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Launch Simulation")
        self._stop_btn.configure(state="disabled")
        self._status_dot.configure(text="⬤  Completed", text_color=SUCCESS_COLOR)
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._progress.set(1)
        self._pct_lbl.configure(text="100%")
        self._log("─" * 50)
        self._log("✅  Simulation complete.")

        # Update summary statistics labels
        try:
            total = results.get("transactions_simulated", 0)
            approved = results.get("transactions_approved", 0)
            declined = results.get("transactions_declined", 0)
            alerts = results.get("alerts_generated", 0)
            
            success_rate = f"{(approved / total * 100):.1f}%" if total > 0 else "--"
            
            # Fetch average amount
            avg_res = self.simulator.db.fetch_one("SELECT AVG(amount) as avg_amt FROM transactions")
            avg_amt = format_inr(avg_res["avg_amt"]) if avg_res and avg_res["avg_amt"] is not None else "--"
            
            self._stat_widgets["total"].configure(text=f"{total:,}")
            self._stat_widgets["fraud"].configure(text=f"{declined:,}")
            self._stat_widgets["success"].configure(text=success_rate)
            self._stat_widgets["declined"].configure(text=f"{declined:,}")
            self._stat_widgets["average"].configure(text=avg_amt)
            self._stat_widgets["alerts"].configure(text=f"{alerts:,}")
        except Exception:
            pass

        # Log summary
        for k, v in results.items():
            self._log(f"  {k}: {v}")

    def _on_stopped(self) -> None:
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Launch Simulation")
        self._stop_btn.configure(state="disabled")
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._status_dot.configure(text="⬤  Stopped", text_color=WARNING_COLOR)
        self._log("Simulation stopped by user.")

    def _on_error(self, msg: str) -> None:
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Launch Simulation")
        self._stop_btn.configure(state="disabled")
        self._progress.stop()
        self._progress.configure(mode="determinate")
        self._status_dot.configure(text="⬤  Error", text_color=DANGER_COLOR)
        self._log(f"⚠  Error: {msg}")
        messagebox.showerror("Simulation Error", msg)
