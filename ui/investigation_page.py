import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
import threading
from typing import Dict, Any, List, Optional

# Reusable widgets
from ui.widgets.tables import TableWidget
from ui.widgets.timeline import TimelineWidget
from ui.widgets.status_badges import StatusBadge
from ui.widgets.cards import CardWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)

# Backend imports
from services import InvestigationService, BlacklistService, WhitelistService
from database import DatabaseConnection

class InvestigationPage(ttk.Frame):
    """
    Customer Dossier & Investigation Page.
    Fetches full profile metrics, whitelist/blacklist status, transaction averages,
    known device fingerprints, and logs them to a custom vertical timeline.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.investigation_service = InvestigationService()
        self.blacklist_service = BlacklistService()
        self.whitelist_service = WhitelistService()
        self.db = DatabaseConnection()

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Customer Dossier & Investigation", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")

        # Search Bar inside Header
        self.search_frame = tk.Frame(self.header_frame, bg=BG_COLOR)
        self.search_frame.pack(side="right")

        self.search_entry = tk.Entry(
            self.search_frame,
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            bd=0,
            insertbackground=TEXT_COLOR,
            font=FONT_BODY,
            highlightthickness=1,
            highlightcolor=PRIMARY_COLOR,
            highlightbackground="#334155",
            width=25
        )
        self.search_entry.pack(side="left", padx=5, ipady=4)
        self.search_entry.insert(0, "Enter Customer ID...")
        self.search_entry.bind("<FocusIn>", self._clear_placeholder)
        self.search_entry.bind("<FocusOut>", self._add_placeholder)
        self.search_entry.bind("<Return>", lambda e: self.load_customer_investigation())

        self.search_btn = ttk.Button(self.search_frame, text="🔍 Investigate", command=self.load_customer_investigation)
        self.search_btn.pack(side="left", padx=5)

        # Main Scrollable Area
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

        # Placeholder label
        self.placeholder_lbl = tk.Label(
            self.scroll_frame,
            text="Provide a Customer ID at the top right to start a deep investigation profile.",
            bg=BG_COLOR,
            fg=SUBTEXT_COLOR,
            font=FONT_SUBHEADER
        )
        self.placeholder_lbl.pack(pady=100)

        # Loading Label
        self.loading_lbl = tk.Label(
            self.scroll_frame,
            text="Gathering security events and assembling timeline...",
            bg=BG_COLOR,
            fg=SUBTEXT_COLOR,
            font=FONT_SUBHEADER
        )
        # Dossier Area (Hidden by default)
        self.dossier_frame = tk.Frame(self.scroll_frame, bg=BG_COLOR)

        self.current_customer_id = None
        self.current_customer_data = None

    def _clear_placeholder(self, event) -> None:
        if self.search_entry.get() == "Enter Customer ID...":
            self.search_entry.delete(0, tk.END)

    def _add_placeholder(self, event) -> None:
        if not self.search_entry.get().strip():
            self.search_entry.insert(0, "Enter Customer ID...")

    def load_customer(self, customer_id: int) -> None:
        """
        Public method to trigger loading a specific customer dossier directly.
        """
        self.search_entry.delete(0, tk.END)
        self.search_entry.insert(0, str(customer_id))
        self.load_customer_investigation()

    def load_customer_investigation(self) -> None:
        raw_val = self.search_entry.get().strip()
        if not raw_val or raw_val == "Enter Customer ID...":
            messagebox.showwarning("Input Required", "Please enter a valid Customer ID.")
            return

        try:
            customer_id = int(raw_val)
        except ValueError:
            messagebox.showerror("Invalid ID", "Customer ID must be a numeric integer.")
            return

        # Show loading indicator, hide dossier & placeholder
        self.placeholder_lbl.pack_forget()
        self.dossier_frame.pack_forget()
        self.loading_lbl.pack(pady=100)
        
        self.current_customer_id = customer_id
        threading.Thread(target=self._fetch_investigation_worker, args=(customer_id,), daemon=True).start()

    def _fetch_investigation_worker(self, customer_id: int) -> None:
        try:
            dossier = self.investigation_service.investigate_customer(customer_id)
            
            # Query Whitelist/Blacklist custom status
            is_bl, bl_reason = self.blacklist_service.check_blacklist(customer_id=customer_id)
            is_wl, wl_reason = self.whitelist_service.check_whitelist(customer_id=customer_id)
            
            dossier["blacklist_status"] = {"blacklisted": is_bl, "reason": bl_reason}
            dossier["whitelist_status"] = {"whitelisted": is_wl, "reason": wl_reason}

            self.after(0, self._render_dossier, dossier)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _show_error(self, err_msg: str) -> None:
        self.loading_lbl.pack_forget()
        self.placeholder_lbl.configure(text=f"Error compiling dossier: {err_msg}", fg=DANGER_COLOR)
        self.placeholder_lbl.pack(pady=100)

    def _render_dossier(self, dossier: Dict[str, Any]) -> None:
        self.loading_lbl.pack_forget()
        self.current_customer_data = dossier

        # Clear old content
        for child in self.dossier_frame.winfo_children():
            child.destroy()

        self.dossier_frame.pack(fill="both", expand=True)

        # 2-column layout (Split Frame)
        split_frame = tk.Frame(self.dossier_frame, bg=BG_COLOR)
        split_frame.pack(fill="both", expand=True)
        split_frame.columnconfigure(0, weight=3) # Left (KYC + Devices)
        split_frame.columnconfigure(1, weight=2) # Right (Metrics + Summary + Timeline)

        # --- LEFT COLUMN ---
        left_col = tk.Frame(split_frame, bg=BG_COLOR)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # 1. Profile Info Card
        profile_card = tk.Frame(left_col, bg=CARD_COLOR, padx=16, pady=16)
        profile_card.pack(fill="x", pady=(0, 15))

        profile = dossier["customer_profile"]
        risk_profile = dossier["risk_profile"] or {}
        
        name_lbl = tk.Label(profile_card, text=f"{profile['first_name']} {profile['last_name']}", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        name_lbl.pack(anchor="w", pady=(0, 10))

        badge_frame = tk.Frame(profile_card, bg=CARD_COLOR)
        badge_frame.pack(anchor="w", pady=(0, 15))

        status_badge = StatusBadge(badge_frame, profile["status"])
        status_badge.pack(side="left")

        # Custom tag badges for Whitelisted / Blacklisted
        if dossier["blacklist_status"]["blacklisted"]:
            bl_tag = tk.Label(badge_frame, text="BLACKLISTED", bg=DANGER_COLOR, fg=TEXT_COLOR, font=FONT_CAPTION, padx=6, pady=2)
            bl_tag.pack(side="left", padx=(10, 0))
        elif dossier["whitelist_status"]["whitelisted"]:
            wl_tag = tk.Label(badge_frame, text="WHITELISTS MATCH", bg=SUCCESS_COLOR, fg=TEXT_COLOR, font=FONT_CAPTION, padx=6, pady=2)
            wl_tag.pack(side="left", padx=(10, 0))

        details = [
            ("Customer ID", profile["customer_id"]),
            ("Email", profile["email"]),
            ("Phone", profile["phone"] or "N/A"),
            ("PAN", profile["pan"] or "N/A"),
            ("Account Number", profile["account_number"] or "N/A"),
            ("Pincode", profile["pincode"] or "N/A"),
            ("City", profile["city"] or "N/A"),
            ("State", profile["state"] or "N/A"),
            ("Country", profile["country"] or "N/A"),
            ("Risk Level", f"{risk_profile.get('risk_tier', 'LOW')} (Score: {risk_profile.get('current_risk_score', 0)}/100)"),
        ]

        for label, val in details:
            row = tk.Frame(profile_card, bg=CARD_COLOR, pady=3)
            row.pack(fill="x")
            lbl_key = tk.Label(row, text=f"{label}:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, width=15, anchor="w")
            lbl_key.pack(side="left")
            lbl_val = tk.Label(row, text=str(val), bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY, anchor="w")
            lbl_val.pack(side="left", fill="x", expand=True)

        # Action Buttons inside Profile
        act_row = tk.Frame(profile_card, bg=CARD_COLOR, pady=(15, 0))
        act_row.pack(fill="x")

        # Disable buttons depending on status
        if not dossier["blacklist_status"]["blacklisted"]:
            bl_btn = ttk.Button(act_row, text="🚫 Blacklist", style="Danger.TButton", command=self._blacklist_customer)
            bl_btn.pack(side="left", padx=(0, 10))
        else:
            bl_info_lbl = tk.Label(act_row, text=f"Block reason: {dossier['blacklist_status']['reason']}", bg=CARD_COLOR, fg=DANGER_COLOR, font=FONT_CAPTION, wraplength=200, justify="left")
            bl_info_lbl.pack(side="left", padx=(0, 10))

        if not dossier["whitelist_status"]["whitelisted"] and not dossier["blacklist_status"]["blacklisted"]:
            wl_btn = ttk.Button(act_row, text="⭐ Whitelist", style="Success.TButton", command=self._whitelist_customer)
            wl_btn.pack(side="left")
        elif dossier["whitelist_status"]["whitelisted"]:
            wl_info_lbl = tk.Label(act_row, text=f"Whitelist justification: {dossier['whitelist_status']['reason']}", bg=CARD_COLOR, fg=SUCCESS_COLOR, font=FONT_CAPTION, wraplength=200, justify="left")
            wl_info_lbl.pack(side="left")

        # 2. Associated Devices Card
        devices_card = tk.Frame(left_col, bg=CARD_COLOR, padx=16, pady=16)
        devices_card.pack(fill="both", expand=True)

        dev_lbl = tk.Label(devices_card, text="Associated Device Fingerprints", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        dev_lbl.pack(anchor="w", pady=(0, 10))

        self.device_table = TableWidget(
            devices_card,
            columns=["fingerprint", "ip_address", "operating_system", "last_seen"],
            headers=["Fingerprint", "IP Address", "OS", "Last Seen"]
        )
        self.device_table.pack(fill="both", expand=True)

        for dev in dossier["devices_used"]:
            fp = dev["device_fingerprint"]
            short_fp = fp[:12] + "..." if len(fp) > 12 else fp
            self.device_table.insert_row([
                short_fp,
                dev["ip_address"],
                dev["operating_system"] or "Unknown",
                dev["last_seen"][:16] if dev["last_seen"] else "N/A"
            ])

        # --- RIGHT COLUMN ---
        right_col = tk.Frame(split_frame, bg=BG_COLOR)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # 1. 2x2 Metrics Cards
        metrics_frame = tk.Frame(right_col, bg=BG_COLOR)
        metrics_frame.pack(fill="x", pady=(0, 15))
        metrics_frame.columnconfigure((0, 1), weight=1, uniform="group2")

        # Row 0
        trust_card = CardWidget(metrics_frame, "TRUST SCORE", f"{dossier['trust_score']}/100", "Overall reliability rating", trend_color=SUCCESS_COLOR if dossier['trust_score'] >= 70 else WARNING_COLOR)
        trust_card.grid(row=0, column=0, padx=4, pady=4, sticky="nsew")

        attempts_card = CardWidget(metrics_frame, "FRAUD ATTEMPTS", str(dossier['fraud_attempts']), "Flagged events in database", trend_color=DANGER_COLOR if dossier['fraud_attempts'] > 0 else SUCCESS_COLOR)
        attempts_card.grid(row=0, column=1, padx=4, pady=4, sticky="nsew")

        # Row 1
        avg_amt_val = f"${dossier['average_amount']:,.2f}" if dossier['average_amount'] else "$0.00"
        avg_amt_card = CardWidget(metrics_frame, "AVG TX AMOUNT", avg_amt_val, "Mean spending scale")
        avg_amt_card.grid(row=1, column=0, padx=4, pady=4, sticky="nsew")

        city_card = CardWidget(metrics_frame, "FREQUENT CITY", dossier['most_frequent_city'] or "N/A", "Top geo location")
        city_card.grid(row=1, column=1, padx=4, pady=4, sticky="nsew")

        # 2. Behavior Summary Card
        summary_card = tk.Frame(right_col, bg=CARD_COLOR, padx=16, pady=16)
        summary_card.pack(fill="x", pady=(0, 15))

        sum_lbl = tk.Label(summary_card, text="Behavior Summary Diagnostics", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        sum_lbl.pack(anchor="w", pady=(0, 10))

        sum_body = tk.Label(
            summary_card,
            text=dossier["behaviour_summary"] or "No transactional metrics exist to compute behavioral patterns.",
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            font=FONT_BODY,
            justify="left",
            wraplength=350
        )
        sum_body.pack(anchor="w")

        # 3. Timeline Events Card
        timeline_card = tk.Frame(right_col, bg=CARD_COLOR, padx=16, pady=16)
        timeline_card.pack(fill="both", expand=True)

        time_header_lbl = tk.Label(timeline_card, text="Security Audit Timeline", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        time_header_lbl.pack(anchor="w", pady=(0, 10))

        self.timeline_widget = TimelineWidget(timeline_card)
        self.timeline_widget.pack(fill="both", expand=True)

        # Parse timeline string items
        formatted_events = []
        for item in dossier["timeline"]:
            parts = item.split(" ", 2)
            if len(parts) >= 3:
                time_part = f"{parts[0]} {parts[1]}"
                title_part = parts[2]
            else:
                time_part = ""
                title_part = item
            formatted_events.append({
                "time": time_part,
                "title": title_part,
                "details": ""
            })

        self.timeline_widget.set_events(formatted_events)

    def _blacklist_customer(self) -> None:
        reason = simpledialog.askstring("Blacklist Customer", f"Reason for blacklisting Customer ID #{self.current_customer_id}:")
        if reason:
            try:
                self.blacklist_service.blacklist_customer(self.current_customer_id, reason)
                messagebox.showinfo("Blacklisted", f"Customer #{self.current_customer_id} has been blocked.")
                # Reload dossier
                self.load_customer_investigation()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to blacklist customer: {e}")

    def _whitelist_customer(self) -> None:
        reason = simpledialog.askstring("Whitelist Justification", f"Justification for whitelisting Customer ID #{self.current_customer_id}:")
        if reason:
            try:
                self.whitelist_service.whitelist_customer(self.current_customer_id, reason)
                messagebox.showinfo("Whitelisted", f"Customer #{self.current_customer_id} whitelisted successfully.")
                # Reload dossier
                self.load_customer_investigation()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to whitelist customer: {e}")
