import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from decimal import Decimal
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
from services import TransactionService

class TransactionPage(ttk.Frame):
    """
    Transactions ledger and creations panel page. Handles paginated history scans
    and executes transaction engine risk assessments.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.service = TransactionService()
        
        # Paging configurations
        self.current_page = 0
        self.page_size = 15
        self.total_count = 0
        self.status_filter = ""
        self.search_query = ""

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Transactions Center", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        # Split Container
        self.main_split = tk.Frame(self, bg=BG_COLOR)
        self.main_split.pack(fill="both", expand=True)
        self.main_split.columnconfigure(0, weight=4) # Left Table
        self.main_split.columnconfigure(1, weight=2) # Right Transaction creation form

        # Left Column Frame (Table and controls)
        self.left_frame = tk.Frame(self.main_split, bg=BG_COLOR)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Filter Options Panel
        self.filter_frame = tk.Frame(self.left_frame, bg=BG_COLOR)
        self.filter_frame.pack(fill="x", pady=(0, 15))

        self.search_bar = SearchBar(self.filter_frame, placeholder="Search Customer ID...", search_callback=self._search_transactions)
        self.search_bar.pack(side="left", fill="x", expand=True)

        self.status_cmb = ttk.Combobox(self.filter_frame, values=["All Statuses", "APPROVED", "PENDING", "DECLINED", "FLAGGED"], style="TCombobox", state="readonly", width=15)
        self.status_cmb.set("All Statuses")
        self.status_cmb.pack(side="left", padx=(10, 0))
        self.status_cmb.bind("<<ComboboxSelected>>", self._on_status_filter_changed)

        # Transaction Table Grid
        self.table = TableWidget(
            self.left_frame,
            columns=["tx_id", "cust_id", "merchant", "amount", "type", "status", "time"],
            headers=["TX ID", "Cust ID", "Merchant", "Amount", "Type", "Status", "Timestamp"]
        )
        self.table.pack(fill="both", expand=True)

        # Pagination controls
        self.paging_frame = tk.Frame(self.left_frame, bg=BG_COLOR, pady=10)
        self.paging_frame.pack(fill="x")

        self.prev_btn = ttk.Button(self.paging_frame, text="◀ Previous", command=self._prev_page)
        self.prev_btn.pack(side="left")

        self.page_lbl = tk.Label(self.paging_frame, text="Page 1", bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION)
        self.page_lbl.pack(side="left", padx=15)

        self.next_btn = ttk.Button(self.paging_frame, text="Next ▶", command=self._next_page)
        self.next_btn.pack(side="left")

        # Right Column Frame (Form Panel)
        self.right_frame = tk.Frame(self.main_split, bg=CARD_COLOR, padx=16, pady=16)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        self.form_lbl = tk.Label(self.right_frame, text="Log New Transaction", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.form_lbl.pack(anchor="w", pady=(0, 15))

        self.form_container = tk.Frame(self.right_frame, bg=CARD_COLOR)
        self.form_container.pack(fill="both", expand=True)

        # Form fields
        self.fields = [
            ("cust_id", "Customer ID *", "entry", None),
            ("amount", "Amount ($) *", "entry", None),
            ("currency", "Currency", "combo", ["USD", "INR", "EUR", "GBP"]),
            ("type", "Transaction Type", "combo", ["PURCHASE", "WITHDRAWAL", "TRANSFER", "DEPOSIT"]),
            ("city", "City (Coordinates resolved)", "combo", ["MUMBAI", "NEW YORK", "LONDON", "TOKYO", "PARIS", "LAS VEGAS"]),
            ("merchant", "Merchant Category", "combo", ["SUPERMARKET", "GAMBLING", "CASINO"]),
            ("fingerprint", "Device Fingerprint", "entry", None)
        ]

        self.inputs = {}
        for key, label, f_type, choices in self.fields:
            row = tk.Frame(self.form_container, bg=CARD_COLOR, pady=6)
            row.pack(fill="x")

            lbl = tk.Label(row, text=label, bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION)
            lbl.pack(anchor="w")

            if f_type == "entry":
                ent = ttk.Entry(row, style="TEntry")
                ent.pack(fill="x", pady=2)
                self.inputs[key] = ent
            elif f_type == "combo":
                cmb = ttk.Combobox(row, values=choices, style="TCombobox", state="readonly")
                cmb.set(choices[0])
                cmb.pack(fill="x", pady=2)
                self.inputs[key] = cmb

        self.submit_btn = ttk.Button(self.right_frame, text="Submit Transaction", command=self._submit_transaction)
        self.submit_btn.pack(fill="x", pady=10)

        # Load initial transactions list
        self._load_transactions()

    def _load_transactions(self) -> None:
        self.table.clear()
        self.page_lbl.configure(text=f"Page {self.current_page + 1}")
        
        # Async load
        threading.Thread(target=self._load_transactions_worker, daemon=True).start()

    def _load_transactions_worker(self) -> None:
        try:
            sql_base = (
                "SELECT t.transaction_id, t.customer_id, m.merchant_name, t.amount, t.currency, t.transaction_type, t.status, t.transaction_time "
                "FROM transactions t LEFT JOIN merchant_profiles m ON t.merchant_id = m.merchant_id"
            )
            
            where_clauses = []
            params = []

            if self.search_query:
                where_clauses.append("t.customer_id = %s")
                params.append(self.search_query)

            if self.status_filter:
                where_clauses.append("t.status = %s")
                params.append(self.status_filter)

            if where_clauses:
                sql_base += " WHERE " + " AND ".join(where_clauses)

            # Order and Limit
            sql_base += " ORDER BY t.transaction_time DESC LIMIT %s OFFSET %s"
            params.extend([self.page_size, self.current_page * self.page_size])

            rows = self.service.db.fetch_all(sql_base, tuple(params))
            
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed loading transactions: {e}"))

    def _populate_table(self, rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            self.table.insert_row([
                r["transaction_id"],
                r["customer_id"],
                r["merchant_name"] or "None",
                f"{r['amount']} {r['currency']}",
                r["transaction_type"],
                r["status"],
                r["transaction_time"]
            ])

        # Enable/Disable pagination buttons
        if self.current_page == 0:
            self.prev_btn.configure(state="disabled")
        else:
            self.prev_btn.configure(state="normal")

        if len(rows) < self.page_size:
            self.next_btn.configure(state="disabled")
        else:
            self.next_btn.configure(state="normal")

    def _search_transactions(self, query: str) -> None:
        self.search_query = query
        self.current_page = 0
        self._load_transactions()

    def _on_status_filter_changed(self, event) -> None:
        val = self.status_cmb.get()
        if val == "All Statuses":
            self.status_filter = ""
        else:
            self.status_filter = val
            
        self.current_page = 0
        self._load_transactions()

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._load_transactions()

    def _next_page(self) -> None:
        self.current_page += 1
        self._load_transactions()

    def _submit_transaction(self) -> None:
        # Validate inputs
        cust_id_str = self.inputs["cust_id"].get().strip()
        amount_str = self.inputs["amount"].get().strip()
        
        if not cust_id_str or not amount_str:
            messagebox.showwarning("Form Incomplete", "Customer ID and Amount are required fields.")
            return

        try:
            cust_id = int(cust_id_str)
            amount = Decimal(amount_str)
        except Exception:
            messagebox.showwarning("Invalid Input", "Customer ID must be an integer, and Amount must be a decimal.")
            return

        # Fetch form values
        currency = self.inputs["currency"].get()
        tx_type = self.inputs["type"].get()
        city = self.inputs["city"].get()
        merchant = self.inputs["merchant"].get()
        fingerprint = self.inputs["fingerprint"].get().strip() or None

        # Call service creation in background
        self.submit_btn.configure(state="disabled")
        threading.Thread(target=self._submit_transaction_worker, args=(cust_id, amount, currency, tx_type, city, merchant, fingerprint), daemon=True).start()

    def _submit_transaction_worker(self, cust_id, amount, currency, tx_type, city, merchant, fingerprint) -> None:
        try:
            tx = self.service.create_transaction(
                customer_id=cust_id,
                amount=amount,
                city=city,
                merchant_category=merchant,
                device_fingerprint=fingerprint,
                currency=currency,
                transaction_type=tx_type
            )
            saved_tx = self.service.save_transaction(tx)
            
            # Show decision popup
            self.after(0, self._on_submit_success, saved_tx.status, saved_tx.transaction_id)
        except Exception as e:
            self.after(0, self._on_submit_failure, str(e))

    def _on_submit_success(self, status: str, tx_id: int) -> None:
        self.submit_btn.configure(state="normal")
        
        # Clear fields
        self.inputs["cust_id"].delete(0, "end")
        self.inputs["amount"].delete(0, "end")
        self.inputs["fingerprint"].delete(0, "end")
        
        # Reload
        self._load_transactions()
        
        # Display decision
        title = "Transaction Logged"
        msg = f"Transaction registered successfully.\nID: {tx_id}\nRisk Assessment: {status}"
        if status in ("DECLINED", "FLAGGED"):
            messagebox.showwarning(title, msg)
        else:
            messagebox.showinfo(title, msg)

    def _on_submit_failure(self, err_msg: str) -> None:
        self.submit_btn.configure(state="normal")
        messagebox.showerror("Engine Failure", f"Transaction registration failed: {err_msg}")
