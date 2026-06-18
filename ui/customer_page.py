import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.tables import TableWidget
from ui.widgets.searchbar import SearchBar
from ui.widgets.status_badges import StatusBadge
from ui.widgets.dialogs import CustomerFormDialog
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend imports
from services import CustomerService
from exceptions import CustomerValidationException

class CustomerPage(ttk.Frame):
    """
    KYC Customer Profile Management page. Lists profiles,
    contains dynamic search inputs, and exposes add/edit/delete dialogs.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.service = CustomerService()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Customer Accounts KYC", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        self.add_btn = ttk.Button(self.header_frame, text="➕ Add Customer", command=self._open_add_dialog)
        self.add_btn.pack(side="right")

        # Split Container
        self.main_split = tk.Frame(self, bg=BG_COLOR)
        self.main_split.pack(fill="both", expand=True)
        self.main_split.columnconfigure(0, weight=4) # Left Table
        self.main_split.columnconfigure(1, weight=2) # Right Profile summary

        # Left Column Frame
        self.left_frame = tk.Frame(self.main_split, bg=BG_COLOR)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Search Bar
        self.search_bar = SearchBar(self.left_frame, placeholder="Search by name, email, PAN...", search_callback=self._search_customers)
        self.search_bar.pack(fill="x", pady=(0, 15))

        # Customer List Grid
        self.table = TableWidget(
            self.left_frame,
            columns=["customer_id", "first_name", "last_name", "email", "phone", "status"],
            headers=["ID", "First Name", "Last Name", "Email", "Phone", "Status"]
        )
        self.table.pack(fill="both", expand=True)
        self.table.bind_select(self._on_customer_selected)
        self.table.bind_double_click(self._open_edit_dialog)

        # Right Column Frame (Profile Panel)
        self.right_frame = tk.Frame(self.main_split, bg=CARD_COLOR, padx=16, pady=16)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Profile details
        self.profile_lbl = tk.Label(self.right_frame, text="Selected Profile Summary", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.profile_lbl.pack(anchor="w", pady=(0, 15))

        self.details_container = tk.Frame(self.right_frame, bg=CARD_COLOR)
        self.details_container.pack(fill="both", expand=True)

        self.no_sel_lbl = tk.Label(self.details_container, text="Select a customer to inspect detail metrics.", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_BODY)
        self.no_sel_lbl.pack(pady=40)

        # Action Buttons for details panel (initially hidden)
        self.action_frame = tk.Frame(self.right_frame, bg=CARD_COLOR)

        self.edit_btn = ttk.Button(self.action_frame, text="Update Profile", command=self._open_edit_dialog_btn)
        self.edit_btn.pack(side="left", padx=5)

        self.del_btn = ttk.Button(self.action_frame, text="Remove", command=self._delete_customer, style="Danger.TButton")
        self.del_btn.pack(side="left", padx=5)

        # Active Customer selected reference
        self.selected_customer_id = None
        self.selected_customer_data = None

        # Load initial customers list
        self._load_customers()

    def _load_customers(self, query: str = None) -> None:
        self.table.clear()
        
        # Async load of customer list
        threading.Thread(target=self._load_customers_worker, args=(query,), daemon=True).start()

    def _load_customers_worker(self, query: str = None) -> None:
        try:
            # Query backend
            if query:
                # Basic wildcard matching
                sql = "SELECT * FROM customers WHERE first_name LIKE %s OR last_name LIKE %s OR email LIKE %s OR pan LIKE %s"
                param = f"%{query}%"
                rows = self.service.db.fetch_all(sql, (param, param, param, param))
            else:
                rows = self.service.customer_repo.find_all()
                rows = [r.to_dict() for r in rows]

            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed to retrieve customers: {e}"))

    def _populate_table(self, rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            self.table.insert_row(
                [r["customer_id"], r["first_name"], r["last_name"], r["email"], r["phone"] or "", r["status"]],
                item_id=r["customer_id"]
            )

    def _search_customers(self, query: str) -> None:
        self._load_customers(query)

    def _on_customer_selected(self, item_id: Any) -> None:
        if not item_id:
            return
        
        self.selected_customer_id = int(item_id)
        # Load detailed customer values in background
        threading.Thread(target=self._load_customer_details_worker, args=(self.selected_customer_id,), daemon=True).start()

    def _load_customer_details_worker(self, customer_id: int) -> None:
        try:
            # Retrieve from repository
            cust = self.service.customer_repo.find_by_id(customer_id)
            if cust:
                c_data = cust.to_dict()
                
                # Fetch risk level if exists
                risk_row = self.service.db.fetch_one("SELECT current_risk_score, risk_tier FROM risk_profiles WHERE customer_id = %s", (customer_id,))
                if risk_row:
                    c_data["risk_score"] = risk_row["current_risk_score"]
                    c_data["risk_tier"] = risk_row["risk_tier"]
                else:
                    c_data["risk_score"] = 0
                    c_data["risk_tier"] = "LOW"
                    
                self.after(0, self._populate_details_panel, c_data)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed loading profile details: {e}"))

    def _populate_details_panel(self, data: Dict[str, Any]) -> None:
        self.selected_customer_data = data
        
        # Clear container
        for child in self.details_container.winfo_children():
            child.destroy()
            
        self.no_sel_lbl.pack_forget()

        # Lay out profile records
        # Name
        lbl_name = tk.Label(self.details_container, text=f"{data['first_name']} {data['last_name']}", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        lbl_name.pack(anchor="w", pady=(0, 10))

        # Status badge
        badge_frame = tk.Frame(self.details_container, bg=CARD_COLOR)
        badge_frame.pack(anchor="w", pady=(0, 15))
        
        status_badge = StatusBadge(badge_frame, data["status"])
        status_badge.pack(side="left")

        # Details list
        details = [
            ("Email", data["email"]),
            ("Phone", data["phone"] or "Not Provided"),
            ("DOB", data["date_of_birth"] or "Not Provided"),
            ("Gender", data["gender"] or "Not Provided"),
            ("PAN", data["pan"] or "Not Provided"),
            ("Account Number", data["account_number"] or "Not Provided"),
            ("Pincode", data["pincode"] or "Not Provided"),
            ("City", data["city"] or "Not Provided"),
            ("State", data["state"] or "Not Provided"),
            ("Country", data["country"] or "Not Provided"),
            ("Address", data["address"] or "Not Provided"),
            ("Risk Score", f"{data['risk_score']}/100 ({data['risk_tier']})"),
        ]

        for label, val in details:
            row = tk.Frame(self.details_container, bg=CARD_COLOR, pady=3)
            row.pack(fill="x")
            
            lbl_key = tk.Label(row, text=f"{label}:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, width=15, anchor="w")
            lbl_key.pack(side="left")

            lbl_val = tk.Label(row, text=str(val), bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY, anchor="w", justify="left")
            lbl_val.pack(side="left", fill="x", expand=True)

        self.action_frame.pack(fill="x", side="bottom", pady=10)

    def _open_add_dialog(self) -> None:
        CustomerFormDialog(self, "Add New Customer Profile", submit_callback=self._submit_add_customer)

    def _submit_add_customer(self, data: Dict[str, Any]) -> None:
        # Business logical creation
        self.service.create_customer(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            phone=data["phone"],
            status=data["status"],
            pan=data["pan"],
            account_number=data["account_number"],
            pincode=data["pincode"],
            city=data["city"],
            state=data["state"],
            country=data["country"],
            address=data["address"]
        )
        self._load_customers()

    def _open_edit_dialog_btn(self) -> None:
        if self.selected_customer_data:
            self._open_edit_dialog(self.selected_customer_id)

    def _open_edit_dialog(self, customer_id: Any) -> None:
        if not customer_id:
            return
        
        # Async fetch and open edit
        threading.Thread(target=self._open_edit_dialog_worker, args=(int(customer_id),), daemon=True).start()

    def _open_edit_dialog_worker(self, customer_id: int) -> None:
        try:
            cust = self.service.customer_repo.find_by_id(customer_id)
            if cust:
                c_data = cust.to_dict()
                self.after(0, lambda: CustomerFormDialog(
                    self,
                    "Update Customer Profile",
                    customer_data=c_data,
                    submit_callback=lambda d: self._submit_edit_customer(customer_id, d)
                ))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed retrieving profile details: {e}"))

    def _submit_edit_customer(self, customer_id: int, data: Dict[str, Any]) -> None:
        self.service.update_customer(
            customer_id=customer_id,
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            date_of_birth=data["date_of_birth"],
            gender=data["gender"],
            phone=data["phone"],
            status=data["status"],
            pan=data["pan"],
            account_number=data["account_number"],
            pincode=data["pincode"],
            city=data["city"],
            state=data["state"],
            country=data["country"],
            address=data["address"]
        )
        self._load_customers()
        # Refresh current details panel
        self._load_customer_details_worker(customer_id)

    def _delete_customer(self) -> None:
        if not self.selected_customer_id:
            return
        
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to remove customer #{self.selected_customer_id}?")
        if confirm:
            try:
                self.service.delete_customer(self.selected_customer_id)
                self.selected_customer_id = None
                self.selected_customer_data = None
                # Clear details panel
                for child in self.details_container.winfo_children():
                    child.destroy()
                self.no_sel_lbl.pack(pady=40)
                self.action_frame.pack_forget()
                
                self._load_customers()
                messagebox.showinfo("Success", "Customer removed successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete customer: {e}")
