import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.cards        import CardWidget
from ui.widgets.tables       import TableWidget
from ui.widgets.searchbar    import SearchBar
from ui.widgets.status_badges import StatusBadge
from ui.widgets.dialogs      import CustomerFormDialog
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, FONT_TITLE, FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_BUTTON,
    SPACE_XS, SPACE_S, SPACE_M, SPACE_L, SPACE_XL, format_inr, BasePage
)

from services import CustomerService


class CustomerPage(BasePage):
    """Customer KYC management page subclassing standardized BasePage layout."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Customer KYC Profiles", has_right_panel=True)
        self.service = CustomerService()
        self.selected_customer_id = None
        self.selected_customer_data = None

        # ── 1. Header Action Button ──
        ctk.CTkButton(
            self.header_actions, text="＋  Add Customer",
            width=160, height=36, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            command=self._open_add_dialog
        ).pack(side="right", pady=22)

        # ── 2. Toolbar (Search Bar) ──
        self._search = SearchBar(self.toolbar, placeholder="Search name, email, PAN…",
                                 search_callback=self._search_customers)
        self._search.pack(fill="x", pady=6)

        # ── 3. Main Content (Ledger Table) ──
        self._table = TableWidget(
            self.main_content,
            columns=["customer_id", "first_name", "last_name", "email", "phone", "status"],
            headers=["ID", "First Name", "Last Name", "Email", "Phone", "Status"]
        )
        self._table.pack(fill="both", expand=True)
        self._table.bind_select(self._on_select)
        self._table.bind_double_click(self._open_edit_dialog)

        # ── 4. Right Panel (Details Scroll & Actions) ──
        # Details Scroll Container
        self._details_scroll = ctk.CTkScrollableFrame(
            self.right_panel, fg_color="transparent",
            scrollbar_fg_color=CARD_COLOR,
            scrollbar_button_color="#334155"
        )
        self._details_scroll.pack(fill="both", expand=True, padx=SPACE_S, pady=SPACE_S)

        # Empty State
        self._show_empty_state()

        # Action buttons row (hidden by default, packed on select)
        self._action_row = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=60)
        self._action_row.pack_propagate(False)

        self._edit_btn = ctk.CTkButton(
            self._action_row, text="✏  Edit Profile",
            width=120, height=36, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._open_edit_dialog_btn
        )
        self._edit_btn.pack(side="left", padx=(SPACE_S, SPACE_XS), pady=12)

        self._del_btn = ctk.CTkButton(
            self._action_row, text="🗑  Remove",
            width=100, height=36, corner_radius=8,
            fg_color=DANGER_COLOR, hover_color="#DC2626",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._delete_customer
        )
        self._del_btn.pack(side="left", padx=SPACE_XS, pady=12)

        # ── 5. Footer (Statistics) ──
        self._stats_lbl = ctk.CTkLabel(self.footer, text="",
                                        font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                                        text_color=SUBTEXT_COLOR, anchor="w")
        self._stats_lbl.pack(side="left", pady=10)

        self._load_customers()

    def _show_empty_state(self) -> None:
        for w in self._details_scroll.winfo_children():
            w.destroy()
        
        empty_container = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        empty_container.pack(fill="both", expand=True, pady=120)

        icon_lbl = ctk.CTkLabel(
            empty_container, text="👤",
            font=ctk.CTkFont(family=FONT_FAMILY, size=64),
            text_color=SUBTEXT_COLOR
        )
        icon_lbl.pack(pady=(0, SPACE_S))

        msg_lbl = ctk.CTkLabel(
            empty_container,
            text="No customer selected.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_COLOR, justify="center"
        )
        msg_lbl.pack()

        sub_msg_lbl = ctk.CTkLabel(
            empty_container,
            text="Select a profile from the ledger table\nto view full KYC & risk audits.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=SUBTEXT_COLOR, justify="center"
        )
        sub_msg_lbl.pack(pady=(4, 0))

    # ── Data Loading ──────────────────────────────────────────────────────

    def _load_customers(self, query: str = None) -> None:
        self._table.clear()
        threading.Thread(target=self._load_worker, args=(query,), daemon=True).start()

    def _load_worker(self, query: str = None) -> None:
        try:
            if query:
                sql = ("SELECT * FROM customers WHERE first_name LIKE %s "
                       "OR last_name LIKE %s OR email LIKE %s OR pan LIKE %s LIMIT 200")
                p = f"%{query}%"
                rows = self.service.db.fetch_all(sql, (p, p, p, p))
            else:
                rows = [r.to_dict() for r in self.service.customer_repo.find_all()]
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", str(e)))

    def _populate_table(self, rows: List[Dict]) -> None:
        for r in rows:
            self._table.insert_row(
                [r["customer_id"], r["first_name"], r["last_name"],
                 r["email"], r.get("phone") or "—", r["status"]],
                item_id=r["customer_id"]
            )
        self._stats_lbl.configure(text=f"{len(rows)} records loaded")

    def _search_customers(self, query: str) -> None:
        self._load_customers(query if query else None)

    # ── Selection ─────────────────────────────────────────────────────────

    def _on_select(self, item_id: Any) -> None:
        self.selected_customer_id = int(item_id)
        threading.Thread(target=self._load_details_worker,
                          args=(self.selected_customer_id,), daemon=True).start()

    def _load_details_worker(self, cid: int) -> None:
        try:
            cust = self.service.customer_repo.find_by_id(cid)
            if cust:
                data = cust.to_dict()
                risk = self.service.db.fetch_one(
                    "SELECT current_risk_score, risk_tier FROM risk_profiles WHERE customer_id=%s", (cid,))
                data["risk_score"] = risk["current_risk_score"] if risk else 0
                data["risk_tier"]  = risk["risk_tier"] if risk else "LOW"

                # Stored Procedure details
                tx_info = self.service.db.fetch_one(
                    "SELECT COUNT(*) as total_tx, MAX(transaction_time) as last_tx, MAX(amount) as last_amt "
                    "FROM transactions WHERE customer_id=%s", (cid,))
                data["total_tx"] = tx_info["total_tx"] if tx_info else 0
                data["last_tx_time"] = tx_info["last_tx"] if tx_info and tx_info["last_tx"] else "—"
                data["last_tx_amt"] = tx_info["last_amt"] if tx_info and tx_info["last_amt"] else None

                self.after(0, self._populate_profile, data)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _populate_profile(self, data: Dict) -> None:
        self.selected_customer_data = data
        for w in self._details_scroll.winfo_children():
            w.destroy()

        # Avatar Container
        av_frame = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        av_frame.pack(fill="x", pady=(SPACE_S, SPACE_S))

        av = ctk.CTkLabel(
            av_frame,
            text=f"{data['first_name'][0].upper()}{data['last_name'][0].upper()}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=24, weight="bold"),
            text_color=TEXT_COLOR, width=64, height=64,
            fg_color=PRIMARY_COLOR, corner_radius=32
        )
        av.pack(pady=(0, SPACE_XS))

        name_lbl = ctk.CTkLabel(
            av_frame,
            text=f"{data['first_name']} {data['last_name']}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
            text_color=TEXT_COLOR
        )
        name_lbl.pack()

        # Badges row
        badge_row = ctk.CTkFrame(av_frame, fg_color="transparent")
        badge_row.pack(pady=SPACE_XS)
        
        StatusBadge(badge_row, data["status"]).pack(side="left", padx=4)
        
        tier = data["risk_tier"]
        tier_color = DANGER_COLOR if tier in ("CRITICAL", "HIGH") else WARNING_COLOR if tier == "MEDIUM" else SUCCESS_COLOR
        StatusBadge(badge_row, f"{tier} RISK", bg_color=tier_color).pack(side="left", padx=4)

        # Profile details cards
        self._build_info_card("🔑 ACCOUNT DATA", [
            ("Customer ID", f"#{data['customer_id']}"),
            ("PAN Card", data.get("pan") or "—"),
            ("Account No.", data.get("account_number") or "—"),
            ("Customer Since", str(data.get("created_at") or "—")[:10]),
        ])

        self._build_info_card("📞 CONTACT DETAILS", [
            ("Email", data.get("email") or "—"),
            ("Phone", data.get("phone") or "—"),
            ("Location", f"{data.get('city') or '—'}, {data.get('state') or '—'}")
        ])

        last_amt = format_inr(data["last_tx_amt"]) if data.get("last_tx_amt") else "—"
        self._build_info_card("📊 TRANSACTION AUDIT", [
            ("Risk Score", f"{data['risk_score']}/100"),
            ("Total Events", f"{data['total_tx']} transactions"),
            ("Last Event", f"{last_amt}"),
            ("Last Active", str(data.get("last_tx_time") or "—")[:16])
        ])

        # Pack action buttons row
        self._action_row.pack(fill="x", side="bottom")

    def _build_info_card(self, title: str, fields: List[tuple]) -> None:
        card = ctk.CTkFrame(self._details_scroll, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#1E293B")
        card.pack(fill="x", pady=SPACE_XS)

        # Title
        ctk.CTkLabel(
            card, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=SUBTEXT_COLOR
        ).pack(anchor="w", padx=SPACE_S, pady=(SPACE_S, SPACE_XS))

        # Divider
        ctk.CTkFrame(card, fg_color="#1E293B", height=1).pack(fill="x", padx=SPACE_S, pady=(0, SPACE_XS))

        # Fields
        for lbl, val in fields:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=SPACE_S, pady=4)

            ctk.CTkLabel(
                row, text=lbl,
                font=ctk.CTkFont(family=FONT_FAMILY, size=13),
                text_color=SUBTEXT_COLOR, anchor="w", width=120
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=str(val),
                font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                text_color=TEXT_COLOR, anchor="w"
            ).pack(side="left", fill="x", expand=True)

    # ── Dialogs ───────────────────────────────────────────────────────────

    def _open_add_dialog(self) -> None:
        CustomerFormDialog(self, "Add New Customer Profile",
                           submit_callback=self._submit_add)

    def _submit_add(self, data: Dict) -> None:
        self.service.create_customer(**{k: v for k, v in data.items()
                                        if k not in ("risk_score","risk_tier")})
        self._load_customers()

    def _open_edit_dialog_btn(self) -> None:
        if self.selected_customer_data:
            self._open_edit_dialog(self.selected_customer_id)

    def _open_edit_dialog(self, customer_id: Any) -> None:
        if not customer_id:
            return
        cid = int(customer_id)
        threading.Thread(target=self._open_edit_worker, args=(cid,), daemon=True).start()

    def _open_edit_worker(self, cid: int) -> None:
        try:
            cust = self.service.customer_repo.find_by_id(cid)
            if cust:
                data = cust.to_dict()
                self.after(0, lambda: CustomerFormDialog(
                    self, "Update Customer Profile",
                    customer_data=data,
                    submit_callback=lambda d: self._submit_edit(cid, d)
                ))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _submit_edit(self, cid: int, data: Dict) -> None:
        self.service.update_customer(customer_id=cid,
                                     **{k: v for k, v in data.items()
                                        if k not in ("risk_score","risk_tier")})
        self._load_customers()
        self._load_details_worker(cid)

    def _delete_customer(self) -> None:
        if not self.selected_customer_id:
            return
        if messagebox.askyesno("Confirm Deletion",
                               f"Remove customer #{self.selected_customer_id}?"):
            try:
                self.service.delete_customer(self.selected_customer_id)
                self.selected_customer_id = None
                self._action_row.pack_forget()
                self._show_empty_state()
                self._load_customers()
                messagebox.showinfo("Deleted", "Customer removed successfully.")
            except Exception as e:
                messagebox.showerror("Error", str(e))
