"""
FinGuard UI – Investigation Page
Full customer dossier: KYC profile, devices, metrics cards, behavior summary, timeline.
Refactored to match Dashboard typography, compact vertical timeline, and unified vertical scrolling.
"""
import threading
import textwrap
from typing import Any, Dict, List, Optional
import customtkinter as ctk
from tkinter import messagebox, ttk

from ui.widgets.cards import CardWidget
from ui.widgets.tables import TableWidget
from ui.widgets.status_badges import StatusBadge
from ui.widgets.dialogs import InputDialog
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_FAMILY, format_inr
)
from services import InvestigationService, BlacklistService, WhitelistService
from database import DatabaseConnection


class CompactTimeline(ctk.CTkFrame):
    """
    Renders a vertical compact event timeline with centered dot-node markers,
    down arrows, and exact event text. No internal scrollbar.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

    def set_events(self, events: List[Dict[str, Any]]) -> None:
        # Clear old widgets
        for w in self.winfo_children():
            w.destroy()

        if not events:
            ctk.CTkLabel(
                self, text="No timeline events recorded.",
                text_color=SUBTEXT_COLOR,
                font=ctk.CTkFont(family="Segoe UI", size=11)
            ).pack(pady=20)
            return

        # Main vertical flow container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both")

        for idx, event in enumerate(events):
            time_str = event.get("time", "")
            title_str = event.get("title", "")

            # Event node frame
            node_frame = ctk.CTkFrame(container, fg_color="transparent")
            node_frame.pack(fill="x", pady=1)

            # Circle marker + timestamp
            lbl_time = ctk.CTkLabel(
                node_frame, text=f"●  {time_str}" if time_str else "●",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=PRIMARY_COLOR
            )
            lbl_time.pack(anchor="center")

            # Title / description
            lbl_title = ctk.CTkLabel(
                node_frame, text=title_str,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=TEXT_COLOR, justify="center"
            )
            lbl_title.pack(anchor="center", pady=(1, 2))

            # Vertical arrow connector
            if idx < len(events) - 1:
                lbl_arrow = ctk.CTkLabel(
                    container, text="↓",
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    text_color=SUBTEXT_COLOR
                )
                lbl_arrow.pack(anchor="center", pady=2)


class InvestigationPage(ctk.CTkFrame):
    """Customer Security Dossier & Investigation page subclass."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=BG_COLOR, corner_radius=0)
        self.investigation_service = InvestigationService()
        self.blacklist_service = BlacklistService()
        self.whitelist_service = WhitelistService()
        self.db = DatabaseConnection()
        self.current_customer_id = None
        self.current_customer_data = None

        # ── Header with search ────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent", height=52)
        hdr.pack(fill="x", padx=24, pady=(20, 0))
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="Customer Security Dossier",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        # Search cluster
        srch = ctk.CTkFrame(hdr, fg_color="transparent")
        srch.pack(side="right")

        self._id_entry = ctk.CTkEntry(
            srch, placeholder_text="Customer ID…",
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, placeholder_text_color=SUBTEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=160, height=34, corner_radius=8
        )
        self._id_entry.pack(side="left", padx=(0, 8))
        self._id_entry.bind("<Return>", lambda e: self.load_customer_investigation())

        self._search_btn = ctk.CTkButton(
            srch, text="🔍  Investigate",
            width=140, height=34, corner_radius=8,
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            command=self.load_customer_investigation
        )
        self._search_btn.pack(side="left")

        # ── Single Scroll Body (Preventing nested scrollbars) ─────────────
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=BG_COLOR, scrollbar_button_color="#334155"
        )
        self._scroll.pack(fill="both", expand=True, padx=24, pady=12)

        self._placeholder = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._placeholder.pack(fill="both", expand=True, pady=120)

        icon_lbl = ctk.CTkLabel(
            self._placeholder, text="🔍",
            font=ctk.CTkFont(family=FONT_FAMILY, size=64),
            text_color=SUBTEXT_COLOR
        )
        icon_lbl.pack(pady=(0, 16))

        msg_lbl = ctk.CTkLabel(
            self._placeholder,
            text="No Customer Selected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_COLOR, justify="center"
        )
        msg_lbl.pack()

        sub_msg_lbl = ctk.CTkLabel(
            self._placeholder,
            text="Enter a Customer ID in the search bar above\nto retrieve their KYC details, risk profile, and transaction timeline.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=SUBTEXT_COLOR, justify="center"
        )
        sub_msg_lbl.pack(pady=(4, 0))

        self._loading = ctk.CTkLabel(
            self._scroll, text="⏳  Assembling security dossier…",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=SUBTEXT_COLOR)

        self._dossier = ctk.CTkFrame(self._scroll, fg_color="transparent")

    # ── Public Entry Point ────────────────────────────────────────────────
    def load_customer(self, customer_id: int) -> None:
        self._id_entry.delete(0, "end")
        self._id_entry.insert(0, str(customer_id))
        self.load_customer_investigation()

    def load_customer_investigation(self) -> None:
        raw = self._id_entry.get().strip()
        if not raw:
            messagebox.showwarning("Required", "Enter a Customer ID.")
            return
        try:
            cid = int(raw)
        except ValueError:
            messagebox.showerror("Invalid", "Customer ID must be an integer.")
            return

        self._placeholder.pack_forget()
        self._dossier.pack_forget()
        self._loading.pack(pady=60)
        self._search_btn.configure(state="disabled", text="Loading…")

        self.current_customer_id = cid
        threading.Thread(target=self._fetch_worker, args=(cid,), daemon=True).start()

    def _fetch_worker(self, cid: int) -> None:
        try:
            dossier = self.investigation_service.investigate_customer(cid)
            is_bl, bl_r = self.blacklist_service.check_blacklist(customer_id=cid)
            is_wl, wl_r = self.whitelist_service.check_whitelist(customer_id=cid)
            dossier["blacklist_status"] = {"blacklisted": is_bl, "reason": bl_r}
            dossier["whitelist_status"] = {"whitelisted": is_wl, "reason": wl_r}
            self.after(0, self._render_dossier, dossier)
        except Exception as e:
            self.after(0, self._show_error, str(e))

    def _show_error(self, msg: str) -> None:
        self._loading.pack_forget()
        self._search_btn.configure(state="normal", text="🔍  Investigate")
        messagebox.showerror("Investigation Failed", msg)
        self._placeholder.pack(fill="both", expand=True, pady=120)

    def _render_dossier(self, dossier: Dict) -> None:
        self._loading.pack_forget()
        self._search_btn.configure(state="normal", text="🔍  Investigate")
        self.current_customer_data = dossier

        for w in self._dossier.winfo_children():
            w.destroy()
        self._dossier.pack(fill="both", expand=True)

        # Split Layout
        split = ctk.CTkFrame(self._dossier, fg_color="transparent")
        split.pack(fill="both", expand=True)
        split.columnconfigure(0, weight=3)
        split.columnconfigure(1, weight=2)

        left = ctk.CTkFrame(split, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        right = ctk.CTkFrame(split, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self._build_profile_card(left, dossier)
        self._build_devices_card(left, dossier)
        self._build_metrics_row(right, dossier)
        self._build_behavior_card(right, dossier)
        self._build_timeline_card(right, dossier)

    def _build_profile_card(self, parent, dossier: Dict) -> None:
        profile = dossier["customer_profile"]
        rp = dossier.get("risk_profile") or {}

        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        av_row = ctk.CTkFrame(card, fg_color="transparent")
        av_row.pack(fill="x", padx=16, pady=(14, 0))

        av = ctk.CTkLabel(
            av_row,
            text=f"{profile['first_name'][0]}{profile['last_name'][0]}".upper(),
            width=52, height=52, corner_radius=26,
            fg_color=PRIMARY_COLOR, text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
        )
        av.pack(side="left", padx=(0, 14))

        name_col = ctk.CTkFrame(av_row, fg_color="transparent")
        name_col.pack(side="left")

        ctk.CTkLabel(name_col,
                     text=f"{profile['first_name']} {profile['last_name']}",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w")

        badge_row = ctk.CTkFrame(name_col, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(4, 0))
        StatusBadge(badge_row, profile["status"]).pack(side="left", padx=(0, 6))

        if dossier["blacklist_status"]["blacklisted"]:
            ctk.CTkLabel(badge_row, text="  BLACKLISTED  ",
                         fg_color=DANGER_COLOR, text_color=TEXT_COLOR,
                         font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                         corner_radius=4).pack(side="left")
        elif dossier["whitelist_status"]["whitelisted"]:
            ctk.CTkLabel(badge_row, text="  WHITELISTED  ",
                         fg_color=SUCCESS_COLOR, text_color=TEXT_COLOR,
                         font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
                         corner_radius=4).pack(side="left")

        ctk.CTkFrame(card, fg_color="#2D3748", height=1).pack(fill="x", padx=16, pady=12)

        fields = [
            ("Customer ID", profile["customer_id"]),
            ("📧 Email",    profile["email"]),
            ("📱 Phone",    profile.get("phone") or "—"),
            ("🪪 PAN",      profile.get("pan") or "—"),
            ("🏦 Account",  profile.get("account_number") or "—"),
            ("🏙 City",     profile.get("city") or "—"),
            ("🌍 Country",  profile.get("country") or "—"),
            ("⚠ Risk",     f"{rp.get('risk_tier','LOW')} ({rp.get('current_risk_score',0)}/100)"),
        ]
        for label, val in fields:
            row = ctk.CTkFrame(card, fg_color="transparent", height=26)
            row.pack(fill="x", padx=16, pady=1)
            ctk.CTkLabel(row, text=f"{label}:", text_color=SUBTEXT_COLOR,
                         font=ctk.CTkFont(family="Segoe UI", size=10),
                         width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(val), text_color=TEXT_COLOR,
                         font=ctk.CTkFont(family="Segoe UI", size=10),
                         anchor="w").pack(side="left", fill="x", expand=True)

        act = ctk.CTkFrame(card, fg_color="transparent")
        act.pack(fill="x", padx=16, pady=(10, 14))

        if not dossier["blacklist_status"]["blacklisted"]:
            ctk.CTkButton(act, text="🚫  Blacklist", width=100, height=30,
                          corner_radius=8, fg_color=DANGER_COLOR, hover_color="#DC2626",
                          text_color=TEXT_COLOR,
                          font=ctk.CTkFont(family="Segoe UI", size=11),
                          command=self._blacklist_customer).pack(side="left", padx=(0, 8))

        if (not dossier["whitelist_status"]["whitelisted"] and
                not dossier["blacklist_status"]["blacklisted"]):
            ctk.CTkButton(act, text="⭐  Whitelist", width=100, height=30,
                          corner_radius=8, fg_color=SUCCESS_COLOR, hover_color="#059669",
                          text_color=TEXT_COLOR,
                          font=ctk.CTkFont(family="Segoe UI", size=11),
                          command=self._whitelist_customer).pack(side="left")

    def _build_devices_card(self, parent, dossier: Dict) -> None:
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        card.pack(fill="both", expand=True, pady=(0, 0))

        ctk.CTkLabel(card, text="🖥  Associated Device Fingerprints",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))

        # Device Table Styling
        style = ttk.Style()
        style.configure("Devices.Treeview",
            background=CARD_COLOR,
            fieldbackground=CARD_COLOR,
            foreground=TEXT_COLOR,
            rowheight=28,
            font=("Segoe UI", 11),
            borderwidth=0,
            relief="flat",
        )
        style.configure("Devices.Treeview.Heading",
            background="#0F172A",
            foreground=SUBTEXT_COLOR,
            font=("Segoe UI", 12, "bold"),
            padding=6,
            borderwidth=0,
            relief="flat",
        )
        style.map("Devices.Treeview",
            background=[("selected", PRIMARY_COLOR), ("active", "#1E3A5F")],
            foreground=[("selected", TEXT_COLOR)],
        )

        tbl = TableWidget(
            card,
            columns=["fingerprint", "ip_address", "operating_system", "last_seen"],
            headers=["Fingerprint", "IP Address", "OS", "Last Seen"],
            style="Devices.Treeview"
        )
        tbl.pack(fill="both", expand=True, padx=8, pady=(0, 12))

        # Proportionally Resize Columns dynamically on window size adjustments
        def _resize_cols(event) -> None:
            w = event.width - 20
            if w > 100:
                tbl._tree.column("fingerprint", width=int(w * 0.35))
                tbl._tree.column("ip_address", width=int(w * 0.20))
                tbl._tree.column("operating_system", width=int(w * 0.20))
                tbl._tree.column("last_seen", width=int(w * 0.25))

        tbl.bind("<Configure>", _resize_cols)

        # Do not truncate the fingerprint hash
        for dev in dossier.get("devices_used", []):
            tbl.insert_row([
                dev.get("device_fingerprint", ""),
                dev.get("ip_address", "—"),
                dev.get("operating_system") or "Unknown",
                str(dev.get("last_seen", ""))[:16]
            ])

    def _build_metrics_row(self, parent, dossier: Dict) -> None:
        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 12))
        grid.columnconfigure((0, 1), weight=1)

        trust = dossier.get("trust_score", 0)
        frauds = dossier.get("fraud_attempts", 0)
        avg_amt = dossier.get("average_amount", 0) or 0
        city = dossier.get("most_frequent_city") or "—"

        trust_c = SUCCESS_COLOR if trust >= 70 else WARNING_COLOR
        fraud_c = DANGER_COLOR if frauds > 0 else SUCCESS_COLOR

        CardWidget(grid, "Trust Score",     f"{trust}/100",   "Overall reliability", trust_c
                   ).grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=4)
        CardWidget(grid, "Fraud Attempts",  str(frauds),      "Flagged events", fraud_c
                   ).grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=4)
        CardWidget(grid, "Average Transaction Value", format_inr(avg_amt),"Mean spending", PRIMARY_COLOR
                   ).grid(row=1, column=0, sticky="nsew", padx=(0, 4), pady=4)
        CardWidget(grid, "Frequent City",   city,             "Top geo location", PRIMARY_COLOR
                   ).grid(row=1, column=1, sticky="nsew", padx=(4, 0), pady=4)

    def _build_behavior_card(self, parent, dossier: Dict) -> None:
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(card, text="🧠  Behavior Summary",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))

        # Format Behavior text with maximum width of 70 characters and paragraph line spacing
        raw_text = dossier.get("behaviour_summary") or "No behavioral data available."
        formatted_paragraphs = []
        for p in raw_text.split("\n"):
            if p.strip():
                formatted_paragraphs.append(textwrap.fill(p, width=70))
        formatted_text = "\n\n".join(formatted_paragraphs)

        txt = ctk.CTkTextbox(
            card, fg_color="transparent", text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Segoe UI", size=11), wrap="word"
        )
        txt.pack(fill="x", padx=16, pady=(0, 14))
        txt.insert("1.0", formatted_text)
        
        # Calculate dynamic size to prevent any scrollbars
        lines = formatted_text.count("\n") + 1
        txt_height = max(60, lines * 18 + 10)
        txt.configure(height=txt_height, state="disabled")

    def _build_timeline_card(self, parent, dossier: Dict) -> None:
        card = ctk.CTkFrame(parent, fg_color=CARD_COLOR, corner_radius=12)
        card.pack(fill="x", pady=(0, 0))

        ctk.CTkLabel(card, text="⏱  Security Audit Timeline",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", padx=16, pady=(14, 4))

        events = []
        for item in dossier.get("timeline", []):
            parts = str(item).split(" ", 2)
            if len(parts) >= 3:
                events.append({"time": f"{parts[0]} {parts[1]}", "title": parts[2]})
            else:
                events.append({"time": "", "title": str(item)})

        # Compact timeline centered vertically without internal scrollbars
        timeline = CompactTimeline(card)
        timeline.pack(expand=True, fill="both", padx=16, pady=(0, 16))
        timeline.set_events(events)

        # Enforce dynamic heights: minimum 250px, maximum 500px
        card_height = max(250, min(500, len(events) * 65 + 40))
        card.configure(height=card_height)
        card.pack_propagate(False)

    # ── Actions ───────────────────────────────────────────────────────────
    def _blacklist_customer(self) -> None:
        InputDialog(self, "Blacklist Customer",
                    f"Reason for blacklisting Customer #{self.current_customer_id}:",
                    submit_callback=self._do_blacklist)

    def _do_blacklist(self, reason: str) -> None:
        try:
            self.blacklist_service.blacklist_customer(self.current_customer_id, reason)
            messagebox.showinfo("Blacklisted", f"Customer #{self.current_customer_id} blocked.")
            self.load_customer_investigation()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _whitelist_customer(self) -> None:
        InputDialog(self, "Whitelist Customer",
                    f"Justification for whitelisting Customer #{self.current_customer_id}:",
                    submit_callback=self._do_whitelist)

    def _do_whitelist(self, reason: str) -> None:
        try:
            self.whitelist_service.whitelist_customer(self.current_customer_id, reason)
            messagebox.showinfo("Whitelisted", f"Customer #{self.current_customer_id} whitelisted.")
            self.load_customer_investigation()
        except Exception as e:
            messagebox.showerror("Error", str(e))
