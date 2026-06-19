"""
FinGuard UI – Cases Page
Refactored to single-table layout resembling ServiceNow/Jira, with centered modal dossier overlay.
"""
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox, ttk

from ui.widgets.status_badges import StatusBadge
from ui.widgets.dialogs import CaseNotesDialog, CaseResolveDialog, AssignAnalystDialog
from ui.widgets.tables import TableWidget
from ui.widgets.searchbar import SearchBar
from ui.widgets.cards import CardWidget
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    SEVERITY_COLORS, STATUS_COLORS, FONT_FAMILY, SPACE_S, SPACE_XS, BasePage
)
from services import CaseService


class CaseDossierModal(ctk.CTkToplevel):
    """
    Lightweight, modern compliance dossier modal popup.
    Occupies 55-60% of screen width and 60-65% height, centered perfectly.
    Features a responsive 40% dimming overlay with fade-in/fade-out animations
    and a fixed action footer.
    """
    def __init__(self, parent, case_id: int, on_action_callback=None):
        super().__init__(parent)
        self.parent = parent
        self.case_id = case_id
        self.on_action_callback = on_action_callback
        self.service = CaseService()
        self.case_data = {}

        # Configure window frame
        self.title(f"Case File Dossier - Case #{case_id}")
        self.configure(fg_color="#0F172A")
        
        # Center the window and get screen size
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Modal size: 58% width, 63% height of screen
        mw = int(screen_w * 0.58)
        mh = int(screen_h * 0.63)
        mx = (screen_w - mw) // 2
        my = (screen_h - mh) // 2
        
        self.geometry(f"{mw}x{mh}+{mx}+{my}")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        
        # Dimming Overlay Setup
        self.overlay = ctk.CTkToplevel(parent.winfo_toplevel())
        self.overlay.overrideredirect(True)
        self.overlay.configure(fg_color="#000000")
        self.overlay.attributes("-alpha", 0.0)
        
        # Geometries matching the parent window
        root = parent.winfo_toplevel()
        rw = root.winfo_width()
        rh = root.winfo_height()
        rx = root.winfo_rootx()
        ry = root.winfo_rooty()
        self.overlay.geometry(f"{rw}x{rh}+{rx}+{ry}")
        
        # Handle close when clicking the overlay
        self.overlay.bind("<Button-1>", lambda e: self.close())
        
        # Layers ordering
        self.lift()
        self.overlay.lift()
        self.lift()
        
        # Non-blocking Fade In Overlay (targets 40% opacity)
        self.fade_steps = 5
        self.current_step = 0
        self._fade_in()
        
        # Grab focus without blocking event loop
        self.grab_set()
        self.focus_set()
        
        self.protocol("WM_DELETE_WINDOW", self.close)
        
        # Build UI layout
        self._build_ui()
        self._load_case_data()

    def _fade_in(self) -> None:
        if self.current_step < self.fade_steps:
            self.current_step += 1
            alpha = (self.current_step / self.fade_steps) * 0.40
            if self.overlay.winfo_exists():
                self.overlay.attributes("-alpha", alpha)
            self.after(12, self._fade_in)

    def close(self) -> None:
        self.grab_release()
        self.current_step = self.fade_steps
        self._fade_out()

    def _fade_out(self) -> None:
        if self.current_step > 0:
            self.current_step -= 1
            alpha = (self.current_step / self.fade_steps) * 0.40
            if self.overlay.winfo_exists():
                self.overlay.attributes("-alpha", alpha)
            self.after(12, self._fade_out)
        else:
            if self.overlay.winfo_exists():
                self.overlay.destroy()
            self.destroy()

    def _build_ui(self) -> None:
        # 1. Header Area (Fixed at top)
        header_frame = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header_frame.pack(fill="x", padx=24, pady=(16, 0))
        header_frame.pack_propagate(False)
        
        title_lbl = ctk.CTkLabel(
            header_frame, text=f"Case Dossier #{self.case_id}",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#F8FAFC"
        )
        title_lbl.pack(side="left", anchor="center")
        
        # Inline Badges in Header
        self.hdr_status_badge = StatusBadge(header_frame, "OPEN")
        self.hdr_status_badge.pack(side="left", padx=(16, 6), anchor="center")
        
        self.hdr_severity_badge = StatusBadge(header_frame, "HIGH")
        self.hdr_severity_badge.pack(side="left", padx=6, anchor="center")
        
        close_btn = ctk.CTkButton(
            header_frame, text="✕", width=32, height=32, corner_radius=16,
            fg_color="transparent", hover_color="#1E293B", text_color="#F8FAFC",
            font=ctk.CTkFont(family="Segoe UI", size=14), command=self.close
        )
        close_btn.pack(side="right", anchor="center")
        
        # Divider Line
        ctk.CTkFrame(self, fg_color="#2D3748", height=1).pack(fill="x", padx=24, pady=(8, 4))

        # 2. Fixed Footer Area (Fixed at bottom)
        footer_frame = ctk.CTkFrame(self, fg_color="#1E293B", height=60, corner_radius=0)
        footer_frame.pack(side="bottom", fill="x")
        footer_frame.pack_propagate(False)
        
        footer_inner = ctk.CTkFrame(footer_frame, fg_color="transparent")
        footer_inner.pack(fill="both", expand=True, padx=24, pady=12)
        
        self.btn_review = ctk.CTkButton(
            footer_inner, text="Review Case", fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._start_review, height=36, corner_radius=6
        )
        self.btn_review.pack(side="left", expand=True, fill="x", padx=4)
        
        self.btn_note = ctk.CTkButton(
            footer_inner, text="Add Note", fg_color="#334155", hover_color="#475569",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._open_note_dialog, height=36, corner_radius=6
        )
        self.btn_note.pack(side="left", expand=True, fill="x", padx=4)
        
        self.btn_resolve = ctk.CTkButton(
            footer_inner, text="Resolve Case", fg_color=SUCCESS_COLOR, hover_color="#059669",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._open_resolve_dialog, height=36, corner_radius=6
        )
        self.btn_resolve.pack(side="left", expand=True, fill="x", padx=4)
        
        self.btn_close = ctk.CTkButton(
            footer_inner, text="Close Case", fg_color=DANGER_COLOR, hover_color="#DC2626",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._close_case, height=36, corner_radius=6
        )
        self.btn_close.pack(side="left", expand=True, fill="x", padx=4)

        # 3. Middle Tabs and Content Area (Fills space, inner scrolling)
        self.tabview = ctk.CTkTabview(
            self,
            fg_color="#1E293B",
            segmented_button_fg_color="#0F172A",
            segmented_button_selected_color=PRIMARY_COLOR,
            segmented_button_selected_hover_color="#1D4ED8",
            segmented_button_unselected_color="#1E293B",
            segmented_button_unselected_hover_color="#334155"
        )
        self.tabview.pack(fill="both", expand=True, padx=24, pady=(4, 12))
        
        self.tab_overview = self.tabview.add("Overview")
        self.tab_timeline = self.tabview.add("Timeline")
        self.tab_notes = self.tabview.add("Notes")
        self.tab_actions = self.tabview.add("Actions")

        # Tab 1: Overview Content
        self._build_overview_tab()

        # Tab 2: Timeline Content (Scrollable)
        self.timeline_scroll = ctk.CTkScrollableFrame(self.tab_timeline, fg_color="transparent")
        self.timeline_scroll.pack(fill="both", expand=True, padx=12, pady=12)

        # Tab 3: Notes Content (Scrollable)
        self.notes_scroll = ctk.CTkScrollableFrame(self.tab_notes, fg_color="transparent")
        self.notes_scroll.pack(fill="both", expand=True, padx=12, pady=12)

        # Tab 4: Actions Content
        self._build_actions_tab()

    def _build_overview_tab(self) -> None:
        scroll = ctk.CTkScrollableFrame(self.tab_overview, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=12)

        grid_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        # Left Column: Risk Score & Badges
        left_col = ctk.CTkFrame(grid_frame, fg_color="#111827", corner_radius=12, border_width=1, border_color="#2D3748")
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)

        lbl_score_title = ctk.CTkLabel(left_col, text="RISK SCORE", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=SUBTEXT_COLOR)
        lbl_score_title.pack(anchor="w", padx=16, pady=(16, 2))
        
        self.lbl_score_val = ctk.CTkLabel(left_col, text="-- / 100", font=ctk.CTkFont(family="Segoe UI", size=32, weight="bold"), text_color="#EF4444")
        self.lbl_score_val.pack(anchor="w", padx=16, pady=(0, 8))
        
        self.risk_progress = ctk.CTkProgressBar(left_col, height=8, progress_color="#EF4444", fg_color="#1E293B")
        self.risk_progress.pack(fill="x", padx=16, pady=(0, 20))
        self.risk_progress.set(0.0)
        
        badges_title = ctk.CTkLabel(left_col, text="CLASSIFICATIONS", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=SUBTEXT_COLOR)
        badges_title.pack(anchor="w", padx=16, pady=(0, 6))
        
        badges_row = ctk.CTkFrame(left_col, fg_color="transparent")
        badges_row.pack(fill="x", padx=16, pady=(0, 16))
        
        self.status_badge = StatusBadge(badges_row, "OPEN")
        self.status_badge.pack(side="left", padx=(0, 8))
        
        self.severity_badge = StatusBadge(badges_row, "HIGH")
        self.severity_badge.pack(side="left")

        # Right Column: Metadata Details
        right_col = ctk.CTkFrame(grid_frame, fg_color="#111827", corner_radius=12, border_width=1, border_color="#2D3748")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)

        fields_frame = ctk.CTkFrame(right_col, fg_color="transparent")
        fields_frame.pack(fill="both", expand=True, padx=16, pady=16)

        self.detail_labels = {}
        fields = ["Case ID", "Customer ID", "Transaction ID", "Assigned Analyst", "Created Time"]
        for label_text in fields:
            row_frame = ctk.CTkFrame(fields_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=6)
            
            lbl = ctk.CTkLabel(row_frame, text=label_text, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=SUBTEXT_COLOR, width=130, anchor="w")
            lbl.pack(side="left")
            
            val = ctk.CTkLabel(row_frame, text="--", font=ctk.CTkFont(family="Segoe UI", size=12), text_color=TEXT_COLOR, anchor="w")
            val.pack(side="left", fill="x", expand=True)
            self.detail_labels[label_text] = val

    def _build_actions_tab(self) -> None:
        actions_container = ctk.CTkFrame(self.tab_actions, fg_color="transparent")
        actions_container.pack(expand=True, padx=40, pady=20)
        
        btn_assign = ctk.CTkButton(
            actions_container, text="Assign Analyst", width=280, height=44,
            corner_radius=8, fg_color="#334155", hover_color="#475569",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._open_assign
        )
        btn_assign.pack(pady=8)

    # ── Action Functions ──────────────────────────────────────────────────
    def _open_assign(self) -> None:
        AssignAnalystDialog(self, self.case_id, submit_callback=self._submit_assign)

    def _submit_assign(self, name: str) -> None:
        try:
            self.service.assign_case(self.case_id, name)
            self._load_case_data()
            if self.on_action_callback:
                self.on_action_callback()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _start_review(self) -> None:
        try:
            self.service.change_status(self.case_id, "UNDER_REVIEW")
            self._load_case_data()
            if self.on_action_callback:
                self.on_action_callback()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_note_dialog(self) -> None:
        CaseNotesDialog(self, self.case_id, submit_callback=self._submit_note)

    def _submit_note(self, text: str) -> None:
        try:
            self.service.add_analyst_note(self.case_id, text)
            self._load_case_data()
            if self.on_action_callback:
                self.on_action_callback()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_resolve_dialog(self) -> None:
        CaseResolveDialog(self, self.case_id, submit_callback=self._submit_resolve)

    def _submit_resolve(self, text: str) -> None:
        try:
            self.service.resolve_case(self.case_id, text)
            self._load_case_data()
            if self.on_action_callback:
                self.on_action_callback()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _close_case(self) -> None:
        if messagebox.askyesno("Close Case", f"Close case #{self.case_id}?"):
            try:
                self.service.close_case(self.case_id)
                self._load_case_data()
                if self.on_action_callback:
                    self.on_action_callback()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ── Loading Data ─────────────────────────────────────────────────────
    def _load_case_data(self) -> None:
        threading.Thread(target=self._load_data_worker, daemon=True).start()
        
    def _load_data_worker(self) -> None:
        try:
            sql = ("SELECT c.*, a.risk_score, a.severity, a.transaction_id, a.customer_id "
                   "FROM cases c JOIN alerts a ON c.alert_id = a.alert_id WHERE c.case_id=%s")
            row = self.service.db.fetch_one(sql, (self.case_id,))
            events = self.service.get_case_history(self.case_id)
            if row:
                self.after(0, lambda: self._populate_ui(row, events))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to load case details: {e}"))

    def _populate_ui(self, row: Dict, events: List) -> None:
        self.case_data = row
        score = row.get("risk_score") or 0
        self.lbl_score_val.configure(text=f"{score} / 100")
        self.risk_progress.set(score / 100.0)
        
        severity = (row.get("severity") or "LOW").upper()
        sev_color = SEVERITY_COLORS.get(severity, PRIMARY_COLOR)
        self.risk_progress.configure(progress_color=sev_color)
        
        self.status_badge.update_value(row.get("status") or "OPEN")
        self.severity_badge.update_value(severity)
        self.hdr_status_badge.update_value(row.get("status") or "OPEN")
        self.hdr_severity_badge.update_value(severity)
        
        self.detail_labels["Case ID"].configure(text=str(row.get("case_id")))
        self.detail_labels["Customer ID"].configure(text=str(row.get("customer_id")))
        self.detail_labels["Transaction ID"].configure(text=str(row.get("transaction_id")))
        
        assignee = row.get("assigned_to") or "Unassigned"
        self.detail_labels["Assigned Analyst"].configure(text=assignee)
        
        created = str(row.get("created_at") or "")[:16]
        self.detail_labels["Created Time"].configure(text=created)
        
        self._populate_timeline(events)
        self._populate_notes(row)

    def _populate_timeline(self, events: List) -> None:
        for w in self.timeline_scroll.winfo_children():
            w.destroy()
            
        if not events:
            ctk.CTkLabel(
                self.timeline_scroll, text="No events logged for this case.",
                font=ctk.CTkFont(family="Segoe UI", size=12), text_color=SUBTEXT_COLOR
            ).pack(pady=40)
            return
            
        for ev in events:
            event_frame = ctk.CTkFrame(self.timeline_scroll, fg_color="#111827", corner_radius=8, border_width=1, border_color="#2D3748")
            event_frame.pack(fill="x", pady=6, padx=2)
            
            accent_color = PRIMARY_COLOR
            if "CLOSED" in ev.event_type or "RESOLVED" in ev.event_type:
                accent_color = SUCCESS_COLOR
            elif "CREATED" in ev.event_type:
                accent_color = "#38BDF8"
            
            accent_line = ctk.CTkFrame(event_frame, fg_color=accent_color, width=4)
            accent_line.pack(side="left", fill="y")
            
            content_frame = ctk.CTkFrame(event_frame, fg_color="transparent")
            content_frame.pack(side="left", fill="both", expand=True, padx=12, pady=8)
            
            header_row = ctk.CTkFrame(content_frame, fg_color="transparent")
            header_row.pack(fill="x")
            
            lbl_type = ctk.CTkLabel(header_row, text=ev.event_type.replace("_", " "), font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color=TEXT_COLOR)
            lbl_type.pack(side="left")
            
            time_str = ev.created_at.strftime("%Y-%m-%d %H:%M:%S") if ev.created_at else ""
            lbl_time = ctk.CTkLabel(header_row, text=time_str, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=SUBTEXT_COLOR)
            lbl_time.pack(side="right")
            
            details_str = ""
            if ev.details:
                details_items = []
                for k, v in ev.details.items():
                    details_items.append(f"{k.replace('_', ' ').title()}: {v}")
                details_str = ", ".join(details_items)
            
            if details_str:
                lbl_details = ctk.CTkLabel(content_frame, text=details_str, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=SUBTEXT_COLOR, justify="left", anchor="w")
                lbl_details.pack(anchor="w", pady=(4, 0))

    def _populate_notes(self, data: Dict) -> None:
        for w in self.notes_scroll.winfo_children():
            w.destroy()
            
        sections = [
            ("Initial Case Notes", data.get("notes") or "No initial notes provided."),
            ("Analyst Investigation Notes", data.get("analyst_notes") or "No analyst notes added yet."),
            ("System Remarks / Timeline Audit", data.get("remarks") or "No system remarks recorded."),
            ("Case Resolution Metadata", data.get("resolution") or "Case is not yet resolved.")
        ]
        
        for title, content in sections:
            card = ctk.CTkFrame(self.notes_scroll, fg_color="#111827", corner_radius=10, border_width=1, border_color="#2D3748")
            card.pack(fill="x", pady=8, padx=4)
            
            header = ctk.CTkFrame(card, fg_color="#1F2937", height=32, corner_radius=0)
            header.pack(fill="x", padx=0, pady=0)
            
            lbl_title = ctk.CTkLabel(header, text=f"  {title}", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=TEXT_COLOR)
            lbl_title.pack(side="left", pady=4)
            
            txt = ctk.CTkTextbox(card, fg_color="transparent", text_color=TEXT_COLOR, font=ctk.CTkFont(family="Segoe UI", size=11), height=100)
            txt.pack(fill="x", padx=12, pady=8)
            txt.insert("1.0", content)
            txt.configure(state="disabled")


class CasesPage(BasePage):
    """
    Refactored single-table compliance cases board with dynamic filtering,
    case statistics KPI counters, and a centered pop-up dossier layout.
    """
    def __init__(self, parent) -> None:
        # Set has_right_panel to False to completely remove old Case Dossier panel and nested scrolling
        super().__init__(parent, title_text="Compliance & Cases Board", has_right_panel=False)
        self.service = CaseService()
        self.selected_case_id = None
        self._active_modal = None
        
        # Define specific dark Treeview styling for Cases
        style = ttk.Style()
        style.configure("Cases.Treeview",
            background=CARD_COLOR,
            fieldbackground=CARD_COLOR,
            foreground=TEXT_COLOR,
            rowheight=36,
            font=("Segoe UI", 11),
            borderwidth=0,
            relief="flat",
        )
        style.configure("Cases.Treeview.Heading",
            background="#0F172A",
            foreground=SUBTEXT_COLOR,
            font=("Segoe UI", 12, "bold"),
            padding=10,
            borderwidth=0,
            relief="flat",
        )
        style.map("Cases.Treeview",
            background=[("selected", PRIMARY_COLOR), ("active", "#1E3A5F")],
            foreground=[("selected", TEXT_COLOR)],
        )

        # ── 1. Header Action Button ──
        ctk.CTkButton(
            self.header_actions, text="⟳  Refresh Board", width=140, height=36,
            corner_radius=8, fg_color="#1E293B", hover_color="#334155",
            text_color=TEXT_COLOR, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            command=self._load_cases
        ).pack(side="right", pady=22)

        # ── 2. Toolbar ──
        self._search = SearchBar(self.toolbar, placeholder="Search Customer ID, Case ID, or Assigned Analyst…",
                                 search_callback=self._search_cases)
        self._search.pack(side="left", fill="x", expand=True, pady=6)

        self._status_cmb = ctk.CTkComboBox(
            self.toolbar, values=["All Status", "OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED"],
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, button_color="#334155",
            dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=150, height=36, corner_radius=8, state="readonly",
            command=self._on_status_changed
        )
        self._status_cmb.set("All Status")
        self._status_cmb.pack(side="left", padx=(8, 0), pady=6)

        # ── 3. Case Statistics Section (KPI Cards) ──
        stats_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 16))
        
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)
        stats_frame.columnconfigure(3, weight=1)

        self.card_total = CardWidget(stats_frame, title="Total Cases", value="0", trend_color=PRIMARY_COLOR)
        self.card_total.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.card_open = CardWidget(stats_frame, title="Open Cases", value="0", trend_color=WARNING_COLOR)
        self.card_open.grid(row=0, column=1, sticky="ew", padx=8)

        self.card_review = CardWidget(stats_frame, title="Under Review", value="0", trend_color="#38BDF8")
        self.card_review.grid(row=0, column=2, sticky="ew", padx=8)

        self.card_escalated = CardWidget(stats_frame, title="Escalated Cases", value="0", trend_color=DANGER_COLOR)
        self.card_escalated.grid(row=0, column=3, sticky="ew", padx=(8, 0))

        # ── 4. Main Section: Single Ledger Table ──
        self._table = TableWidget(
            self.main_content,
            columns=["case_id", "customer_id", "transaction_id", "risk_score", "status", "severity", "assigned_to", "created_time"],
            headers=["Case ID", "Customer ID", "Transaction ID", "Risk Score", "Status", "Severity", "Assigned To", "Created Time"],
            style="Cases.Treeview",
            column_alignments={
                "case_id": "center",
                "customer_id": "center",
                "transaction_id": "center",
                "risk_score": "center",
                "status": "center",
                "severity": "center",
                "assigned_to": "center",
                "created_time": "center"
            }
        )
        self._table.pack(fill="both", expand=True)

        self._table.bind_select(self._open_case_modal)
        self._table.bind_double_click(self._open_case_modal)

        self._load_cases()

    # ── Data & Filters Handlers ───────────────────────────────────────────
    def _load_cases(self) -> None:
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            sql = ("SELECT c.*, a.risk_score, a.severity, a.transaction_id, a.customer_id FROM cases c "
                   "JOIN alerts a ON c.alert_id = a.alert_id ORDER BY c.created_at DESC")
            rows = self.service.db.fetch_all(sql)
            self.after(0, self._populate_table, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("DB Error", str(e)))

    def _populate_table(self, rows: List[Dict]) -> None:
        self.all_rows = rows
        self._apply_filter_and_search()

    def _apply_filter_and_search(self) -> None:
        if not hasattr(self, "all_rows"):
            return
        
        status_filter = self._status_cmb.get()
        search_query = self._search.get().strip().lower()
        
        filtered = []
        for r in self.all_rows:
            # Filter status
            status = (r.get("status") or "").upper()
            if status_filter != "All Status" and status != status_filter:
                continue
                
            # Filter search
            if search_query:
                cust_id = str(r.get("customer_id") or "").lower()
                case_id = str(r.get("case_id") or "").lower()
                tx_id = str(r.get("transaction_id") or "").lower()
                assigned = str(r.get("assigned_to") or "").lower()
                if (search_query not in cust_id and 
                    search_query not in case_id and 
                    search_query not in tx_id and 
                    search_query not in assigned):
                    continue
            
            filtered.append(r)
            
        self._table.clear()
        for r in filtered:
            self._table.insert_row([
                r.get("case_id"),
                r.get("customer_id"),
                r.get("transaction_id"),
                r.get("risk_score"),
                r.get("status"),
                r.get("severity"),
                r.get("assigned_to") or "Unassigned",
                str(r.get("created_at") or "")[:16]
            ], item_id=r.get("case_id"))
            
        # Update statistics card values
        total = len(self.all_rows)
        open_c = sum(1 for r in self.all_rows if (r.get("status") or "").upper() == "OPEN")
        review_c = sum(1 for r in self.all_rows if (r.get("status") or "").upper() == "UNDER_REVIEW")
        escalated_c = sum(1 for r in self.all_rows if (r.get("status") or "").upper() == "ESCALATED")
        
        self.card_total.update_value(str(total))
        self.card_open.update_value(str(open_c))
        self.card_review.update_value(str(review_c))
        self.card_escalated.update_value(str(escalated_c))

    def _search_cases(self, query: str) -> None:
        self._apply_filter_and_search()

    def _on_status_changed(self, val: str) -> None:
        self._apply_filter_and_search()

    def _open_case_modal(self, case_id: int) -> None:
        # Check if modal is already open
        if hasattr(self, "_active_modal") and self._active_modal and self._active_modal.winfo_exists():
            self._active_modal.close()
            
        self._active_modal = CaseDossierModal(self, case_id, on_action_callback=self._load_cases)
