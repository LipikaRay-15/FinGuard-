import threading
from decimal import Decimal
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.tables    import TableWidget
from ui.widgets.searchbar import SearchBar
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BUTTON,
    SPACE_XS, SPACE_S, SPACE_M, SPACE_L, SPACE_XL, format_inr, BasePage
)
from services import TransactionService


class TransactionPage(BasePage):
    """Transaction ledger page subclassing standardized BasePage layout."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Transaction Event Ledger", has_right_panel=True)
        self.service = TransactionService()
        self.current_page = 0
        self.page_size    = 20
        self.status_filter = ""
        self.search_query  = ""

        # ── 1. Toolbar (Filters & Search) ──
        self._search = SearchBar(self.toolbar, placeholder="Search by Customer ID…",
                                 search_callback=self._search_tx)
        self._search.pack(side="left", fill="x", expand=True)

        self._status_cmb = ctk.CTkComboBox(
            self.toolbar,
            values=["All Statuses", "APPROVED", "PENDING", "DECLINED", "FLAGGED"],
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, button_color="#334155",
            dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            width=160, height=36, corner_radius=8, state="readonly",
            command=self._on_status_changed
        )
        self._status_cmb.set("All Statuses")
        self._status_cmb.pack(side="left", padx=(SPACE_XS, 0))

        # ── 2. Main Content (Ledger Table) ──
        self._table = TableWidget(
            self.main_content,
            columns=["tx_id", "cust_id", "merchant", "amount", "type", "status", "time"],
            headers=["TX ID", "Cust ID", "Merchant", "Amount", "Type", "Status", "Timestamp"]
        )
        self._table.pack(fill="both", expand=True)

        # ── 3. Right Panel (Log Form) ──
        self._build_form(self.right_panel)

        # ── 4. Footer (Pagination) ──
        self._prev_btn = ctk.CTkButton(
            self.footer, text="◀  Previous", width=120, height=36,
            corner_radius=8, fg_color="#1E293B", hover_color="#334155",
            text_color=SUBTEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._prev_page
        )
        self._prev_btn.pack(side="left")

        self._page_lbl = ctk.CTkLabel(self.footer, text="Page 1",
                                       font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                                       text_color=SUBTEXT_COLOR, width=100)
        self._page_lbl.pack(side="left", padx=SPACE_S)

        self._next_btn = ctk.CTkButton(
            self.footer, text="Next  ▶", width=120, height=36,
            corner_radius=8, fg_color="#1E293B", hover_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._next_page
        )
        self._next_btn.pack(side="left")

        self._load_transactions()

    def _build_form(self, parent) -> None:
        ctk.CTkLabel(parent, text="Log New Transaction",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))
        ctk.CTkFrame(parent, fg_color="#2D3748", height=1).pack(fill="x", padx=SPACE_S, pady=(0, SPACE_S))

        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent",
                                         scrollbar_fg_color=CARD_COLOR,
                                         scrollbar_button_color="#334155")
        scroll.pack(fill="both", expand=True, padx=SPACE_XS)

        self._inputs: Dict[str, Any] = {}
        # Form fields specified by requirements
        fields = [
            ("cust_id",     "Customer ID *",            "entry",  None),
            ("amount",      "Amount (₹) *",             "entry",  None),
            ("merchant",    "Merchant Category",         "combo",  ["SUPERMARKET","GAMBLING","CASINO","ELECTRONICS","TRAVEL","FUEL"]),
            ("city",        "City",                      "combo",  ["MUMBAI","NEW YORK","LONDON","TOKYO","PARIS","LAS VEGAS","DUBAI"]),
            ("device",      "Device (Fingerprint) *",   "entry",  None),
            ("type",        "Transaction Type",          "combo",  ["PURCHASE","WITHDRAWAL","TRANSFER","DEPOSIT"]),
            ("status",      "Status",                    "combo",  ["PENDING","APPROVED","DECLINED","FLAGGED"]),
        ]

        for key, label, ftype, choices in fields:
            wrap = ctk.CTkFrame(scroll, fg_color="transparent")
            wrap.pack(fill="x", pady=6, padx=SPACE_XS)
            ctk.CTkLabel(wrap, text=label,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                         text_color=SUBTEXT_COLOR, anchor="w").pack(anchor="w", pady=(0, 4))

            if ftype == "entry":
                w = ctk.CTkEntry(wrap, fg_color=BG_COLOR, border_color="#334155",
                                  text_color=TEXT_COLOR,
                                  font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                                  height=38, corner_radius=8)
                w.pack(fill="x")
            else:
                w = ctk.CTkComboBox(wrap, values=choices,
                                     fg_color=BG_COLOR, border_color="#334155",
                                     text_color=TEXT_COLOR, button_color="#334155",
                                     dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
                                     font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                                     height=38, corner_radius=8, state="readonly")
                w.set(choices[0])
                w.pack(fill="x")
            self._inputs[key] = w

        self._submit_btn = ctk.CTkButton(
            parent, text="🚀  Submit Transaction",
            width=200, height=44, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            command=self._submit_transaction
        )
        self._submit_btn.pack(pady=SPACE_S, padx=SPACE_S, fill="x")

    # ── Data Loading ──────────────────────────────────────────────────────

    def _load_transactions(self) -> None:
        self._table.clear()
        self._page_lbl.configure(text=f"Page {self.current_page + 1}")
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            sql = ("SELECT t.transaction_id, t.customer_id, m.merchant_name, t.amount, "
                   "t.currency, t.transaction_type, t.status, t.transaction_time "
                   "FROM transactions t LEFT JOIN merchant_profiles m ON t.merchant_id = m.merchant_id")
            clauses, params = [], []
            if self.search_query:
                clauses.append("t.customer_id = %s"); params.append(self.search_query)
            if self.status_filter:
                clauses.append("t.status = %s"); params.append(self.status_filter)
            if clauses:
                sql += " WHERE " + " AND ".join(clauses)
            sql += " ORDER BY t.transaction_time DESC LIMIT %s OFFSET %s"
            params += [self.page_size, self.current_page * self.page_size]
            rows = self.service.db.fetch_all(sql, tuple(params))
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("DB Error", str(e)))

    def _populate_table(self, rows: List[Dict]) -> None:
        for r in rows:
            amt_display = format_inr(r['amount']) if r['currency'] == 'INR' or r['currency'] == 'USD' else f"{r['amount']} {r['currency']}"
            self._table.insert_row([
                r["transaction_id"], r["customer_id"],
                r.get("merchant_name") or "—",
                amt_display,
                r["transaction_type"], r["status"],
                str(r["transaction_time"])[:16]
            ])
        self._prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self._next_btn.configure(state="disabled" if len(rows) < self.page_size else "normal")

    # ── Filters & Pagination ──────────────────────────────────────────────

    def _search_tx(self, q: str) -> None:
        self.search_query = q
        self.current_page = 0
        self._load_transactions()

    def _on_status_changed(self, val: str) -> None:
        self.status_filter = "" if val == "All Statuses" else val
        self.current_page = 0
        self._load_transactions()

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._load_transactions()

    def _next_page(self) -> None:
        self.current_page += 1
        self._load_transactions()

    # ── Submit ────────────────────────────────────────────────────────────

    def _submit_transaction(self) -> None:
        cust_str   = self._inputs["cust_id"].get().strip()
        amount_str = self._inputs["amount"].get().strip()
        device_str = self._inputs["device"].get().strip()
        if not cust_str or not amount_str or not device_str:
            messagebox.showwarning("Incomplete", "Customer ID, Amount, and Device fingerprint are required.")
            return
        try:
            cid    = int(cust_str)
            amount = Decimal(amount_str)
        except Exception:
            messagebox.showwarning("Invalid", "Customer ID must be integer, Amount must be decimal.")
            return

        self._submit_btn.configure(state="disabled", text="Processing…")
        threading.Thread(target=self._submit_worker, args=(
            cid, amount,
            "INR", # Standardize to INR currency
            self._inputs["type"].get(),
            self._inputs["city"].get(),
            self._inputs["merchant"].get(),
            device_str,
            self._inputs["status"].get()
        ), daemon=True).start()

    def _submit_worker(self, cid, amount, currency, tx_type, city, merchant, fp, status) -> None:
        try:
            tx = self.service.create_transaction(
                customer_id=cid, amount=amount, city=city,
                merchant_category=merchant, device_fingerprint=fp,
                currency=currency, transaction_type=tx_type
            )
            # Override generated status if specified in UI form
            tx.status = status
            saved = self.service.save_transaction(tx)
            self.after(0, self._on_success, saved.status, saved.transaction_id)
        except Exception as e:
            self.after(0, self._on_failure, str(e))

    def _on_success(self, status: str, tx_id: int) -> None:
        self._submit_btn.configure(state="normal", text="🚀  Submit Transaction")
        self._inputs["cust_id"].delete(0, "end")
        self._inputs["amount"].delete(0, "end")
        self._inputs["device"].delete(0, "end")
        self._load_transactions()
        msg = f"Transaction #{tx_id} registered.\nRisk Decision: {status}"
        if status in ("DECLINED", "FLAGGED"):
            messagebox.showwarning("Transaction Logged", msg)
        else:
            messagebox.showinfo("Transaction Logged", msg)

    def _on_failure(self, err: str) -> None:
        self._submit_btn.configure(state="normal", text="🚀  Submit Transaction")
        messagebox.showerror("Submission Failed", err)
