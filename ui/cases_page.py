"""
FinGuard UI – Cases Page
Kanban-style case board with 5 status columns + detail panel.
"""
import threading
from typing import Any, Dict, List
import customtkinter as ctk
from tkinter import messagebox

from ui.widgets.status_badges import StatusBadge
from ui.widgets.dialogs import CaseNotesDialog, CaseResolveDialog, AssignAnalystDialog
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    SEVERITY_COLORS, STATUS_COLORS, FONT_FAMILY, SPACE_S, SPACE_XS, BasePage
)
from services import CaseService


COLUMN_COLORS = {
    "OPEN":         "#172554",
    "UNDER_REVIEW": "#422006",
    "ESCALATED":    "#450a0a",
    "RESOLVED":     "#052e16",
    "CLOSED":       "#1e1b4b",
}
COLUMN_ACCENT = {
    "OPEN":         PRIMARY_COLOR,
    "UNDER_REVIEW": WARNING_COLOR,
    "ESCALATED":    DANGER_COLOR,
    "RESOLVED":     SUCCESS_COLOR,
    "CLOSED":       "#6366F1",
}


class CasesPage(BasePage):
    """Kanban compliance case board subclassing standardized BasePage layout."""

    def __init__(self, parent) -> None:
        super().__init__(parent, title_text="Compliance & Cases Board", has_right_panel=True)
        self.service = CaseService()
        self.selected_case_id   = None
        self.selected_case_data = None
        self.statuses = ["OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED"]
        self._col_frames: Dict[str, ctk.CTkScrollableFrame] = {}

        # ── 1. Header Actions ──
        ctk.CTkButton(self.header_actions, text="⟳  Refresh Board", width=140, height=36,
                      corner_radius=8, fg_color="#1E293B", hover_color="#334155",
                      text_color=TEXT_COLOR, font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
                      command=self._load_cases).pack(side="right", pady=22)

        # ── 2. Toolbar ──
        # (We can pack a small descriptive label or leave it empty/hidden, since BasePage has it, we just pack a label)
        ctk.CTkLabel(self.toolbar, text="Review pending risk cases, escalate critical events, or resolve issues here.",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=13), text_color=SUBTEXT_COLOR).pack(side="left", pady=6)

        # ── 3. Main Content: Kanban board (horizontal scrollable) ──
        self._kanban_scroll = ctk.CTkScrollableFrame(
            self.main_content, fg_color="transparent",
            orientation="horizontal",
            scrollbar_fg_color=BG_COLOR, scrollbar_button_color="#334155"
        )
        self._kanban_scroll.pack(fill="both", expand=True)

        for status in self.statuses:
            self._build_column(self._kanban_scroll, status)

        # ── 4. Right Panel: Detail panel ──
        detail_header = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=40)
        detail_header.pack(fill="x", padx=SPACE_S, pady=(SPACE_S, 0))
        
        ctk.CTkLabel(detail_header, text="Case File Dossier",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left")

        ctk.CTkFrame(self.right_panel, fg_color="#2D3748", height=1).pack(fill="x", padx=SPACE_S, pady=(8, 0))

        self._details_scroll = ctk.CTkScrollableFrame(
            self.right_panel, fg_color="transparent",
            scrollbar_fg_color=CARD_COLOR, scrollbar_button_color="#334155"
        )
        self._details_scroll.pack(fill="both", expand=True, padx=SPACE_S, pady=SPACE_S)

        # Initial Empty State
        self._show_empty_state()

        # Action buttons row
        self._action_row = ctk.CTkFrame(self.right_panel, fg_color="transparent", height=60)
        self._action_row.pack_propagate(False)

        btns = [
            ("Assign",       "#334155", "#475569", self._open_assign),
            ("Review",       PRIMARY_COLOR, "#1D4ED8", self._start_review),
            ("Add Note",     "#334155", "#475569", self._open_note_dialog),
            ("Resolve",      SUCCESS_COLOR, "#059669", self._open_resolve_dialog),
            ("Close",        DANGER_COLOR, "#DC2626", self._close_case),
        ]
        for text, fg, hov, cmd in btns:
            ctk.CTkButton(self._action_row, text=text, width=72, height=36,
                          corner_radius=8, fg_color=fg, hover_color=hov,
                          text_color=TEXT_COLOR,
                          font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                          command=cmd).pack(side="left", padx=(SPACE_XS if text == "Assign" else 4, 4), pady=12)

        self._load_cases()

    def _show_empty_state(self) -> None:
        for w in self._details_scroll.winfo_children():
            w.destroy()
        if hasattr(self, "_action_row") and self._action_row:
            self._action_row.pack_forget()

        empty_container = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        empty_container.pack(fill="both", expand=True, pady=120)

        icon_lbl = ctk.CTkLabel(
            empty_container, text="📁",
            font=ctk.CTkFont(family=FONT_FAMILY, size=64),
            text_color=SUBTEXT_COLOR
        )
        icon_lbl.pack(pady=(0, SPACE_S))

        msg_lbl = ctk.CTkLabel(
            empty_container,
            text="No Case Selected",
            font=ctk.CTkFont(family=FONT_FAMILY, size=16, weight="bold"),
            text_color=TEXT_COLOR, justify="center"
        )
        msg_lbl.pack()

        sub_msg_lbl = ctk.CTkLabel(
            empty_container,
            text="Select a case card from the kanban board\nto inspect the compliance dossier & audit trail.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=SUBTEXT_COLOR, justify="center"
        )
        sub_msg_lbl.pack(pady=(4, 0))

    def _build_column(self, parent, status: str) -> None:
        accent = COLUMN_ACCENT.get(status, PRIMARY_COLOR)
        col = ctk.CTkFrame(parent, fg_color="#111827", corner_radius=10,
                            width=200, border_width=1, border_color="#2D3748")
        col.pack(side="left", fill="y", padx=5, pady=2)
        col.pack_propagate(False)

        # Column header
        ch = ctk.CTkFrame(col, fg_color="transparent", height=44)
        ch.pack(fill="x", padx=8, pady=(8, 0))
        ch.pack_propagate(False)

        ctk.CTkFrame(ch, fg_color=accent, width=3, corner_radius=2).pack(
            side="left", fill="y", padx=(0, 8))
        ctk.CTkLabel(ch, text=status.replace("_", " "),
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                     text_color=TEXT_COLOR).pack(side="left", anchor="w")

        ctk.CTkFrame(col, fg_color="#1F2937", height=1).pack(fill="x", padx=8, pady=4)

        cards_frame = ctk.CTkScrollableFrame(col, fg_color="transparent",
                                              scrollbar_fg_color="#111827",
                                              scrollbar_button_color="#334155")
        cards_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self._col_frames[status] = cards_frame

    # ── Data Loading ──────────────────────────────────────────────────────

    def _load_cases(self) -> None:
        for status in self.statuses:
            for w in self._col_frames[status].winfo_children():
                w.destroy()
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        try:
            sql = ("SELECT c.*, a.risk_score, a.severity FROM cases c "
                   "JOIN alerts a ON c.alert_id = a.alert_id ORDER BY c.created_at DESC")
            rows = self.service.db.fetch_all(sql)
            self.after(0, self._populate_board, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("DB Error", str(e)))

    def _populate_board(self, rows: List[Dict]) -> None:
        for r in rows:
            status = (r.get("status") or "OPEN").upper()
            if status not in self._col_frames:
                continue
            self._add_case_card(self._col_frames[status], r)

    def _add_case_card(self, parent, r: Dict) -> None:
        sev   = (r.get("severity") or "LOW").upper()
        accent = SEVERITY_COLORS.get(sev, PRIMARY_COLOR)
        case_id = r["case_id"]

        card = ctk.CTkFrame(parent, fg_color="#0F172A", corner_radius=8,
                             border_width=1, border_color="#2D3748")
        card.pack(fill="x", pady=4, padx=2)

        # Card top
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))

        id_lbl = ctk.CTkLabel(top, text=f"Case #{case_id}",
                               font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                               text_color=TEXT_COLOR)
        id_lbl.pack(side="left")

        sev_badge = ctk.CTkLabel(top, text=f"  {sev}  ",
                                  font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                                  fg_color=accent, text_color=TEXT_COLOR, corner_radius=4)
        sev_badge.pack(side="right")

        # Assignee
        assignee = r.get("assigned_to") or "Unassigned"
        assign_lbl = ctk.CTkLabel(card, text=f"👤  {assignee}",
                                   font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                                   text_color=SUBTEXT_COLOR, anchor="w")
        assign_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # Bind click
        for w in (card, top, id_lbl, sev_badge, assign_lbl):
            w.bind("<Button-1>", lambda e, cid=case_id: self._select_case(cid))
            w.bind("<Enter>",    lambda e, c=card: c.configure(border_color=PRIMARY_COLOR))
            w.bind("<Leave>",    lambda e, c=card: c.configure(border_color="#2D3748"))

    # ── Selection ─────────────────────────────────────────────────────────

    def _select_case(self, case_id: int) -> None:
        self.selected_case_id = case_id
        threading.Thread(target=self._load_details_worker,
                         args=(case_id,), daemon=True).start()

    def _load_details_worker(self, case_id: int) -> None:
        try:
            sql = ("SELECT c.*, a.risk_score, a.severity, a.transaction_id, a.customer_id "
                   "FROM cases c JOIN alerts a ON c.alert_id = a.alert_id WHERE c.case_id=%s")
            row = self.service.db.fetch_one(sql, (case_id,))
            if row:
                self.after(0, self._populate_details, row)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _populate_details(self, data: Dict) -> None:
        self.selected_case_data = data
        for w in self._details_scroll.winfo_children():
            w.destroy()

        ctk.CTkLabel(self._details_scroll,
                     text=f"Case Dossier #{data['case_id']}",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(4, 6))

        badge_row = ctk.CTkFrame(self._details_scroll, fg_color="transparent")
        badge_row.pack(anchor="w", pady=(0, 12))
        StatusBadge(badge_row, data["status"]).pack(side="left", padx=(0, 6))
        StatusBadge(badge_row, data.get("priority","MEDIUM")).pack(side="left")

        ctk.CTkFrame(self._details_scroll, fg_color="#2D3748", height=1).pack(
            fill="x", pady=(0, 8))

        fields = [
            ("Alert ID",       data["alert_id"]),
            ("Customer ID",    data["customer_id"]),
            ("Transaction ID", data["transaction_id"]),
            ("Assigned To",    data.get("assigned_to") or "Unassigned"),
            ("Priority",       data.get("priority","—")),
            ("Created",        str(data.get("created_at",""))[:16]),
            ("Updated",        str(data.get("updated_at",""))[:16]),
        ]
        for k, v in fields:
            row = ctk.CTkFrame(self._details_scroll, fg_color="transparent", height=26)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{k}:", text_color=SUBTEXT_COLOR,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                         width=110, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=str(v), text_color=TEXT_COLOR,
                         font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                         anchor="w").pack(side="left", fill="x", expand=True)

        # Notes/Remarks
        ctk.CTkFrame(self._details_scroll, fg_color="#2D3748", height=1).pack(
            fill="x", pady=(8, 4))
        ctk.CTkLabel(self._details_scroll, text="📋  Audit Trail",
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                     text_color=TEXT_COLOR).pack(anchor="w", pady=(4, 4))

        notes_txt = ctk.CTkTextbox(self._details_scroll, fg_color="#0F172A",
                                    text_color=TEXT_COLOR,
                                    font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                                    height=100, corner_radius=6)
        notes_txt.pack(fill="x", pady=(0, 8))
        content = (f"Notes:\n{data.get('notes') or 'None'}\n\n"
                   f"Remarks:\n{data.get('remarks') or 'None'}\n\n"
                   f"Resolution:\n{data.get('resolution') or 'Pending'}")
        notes_txt.insert("1.0", content)
        notes_txt.configure(state="disabled")

        self._action_row.pack(fill="x", pady=(8, 4))

    # ── Actions ───────────────────────────────────────────────────────────

    def _open_assign(self) -> None:
        if self.selected_case_id:
            AssignAnalystDialog(self, self.selected_case_id,
                                submit_callback=self._submit_assign)

    def _submit_assign(self, name: str) -> None:
        try:
            self.service.assign_case(self.selected_case_id, name)
            self._load_cases()
            self._load_details_worker(self.selected_case_id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _start_review(self) -> None:
        if not self.selected_case_id:
            return
        try:
            self.service.change_status(self.selected_case_id, "UNDER_REVIEW")
            self._load_cases()
            self._load_details_worker(self.selected_case_id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_note_dialog(self) -> None:
        if self.selected_case_id:
            CaseNotesDialog(self, self.selected_case_id,
                            submit_callback=self._submit_note)

    def _submit_note(self, text: str) -> None:
        try:
            self.service.add_analyst_note(self.selected_case_id, text)
            self._load_cases()
            self._load_details_worker(self.selected_case_id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _open_resolve_dialog(self) -> None:
        if self.selected_case_id:
            CaseResolveDialog(self, self.selected_case_id,
                              submit_callback=self._submit_resolve)

    def _submit_resolve(self, text: str) -> None:
        try:
            self.service.resolve_case(self.selected_case_id, text)
            self._load_cases()
            self._load_details_worker(self.selected_case_id)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _close_case(self) -> None:
        if not self.selected_case_id:
            return
        if messagebox.askyesno("Close Case", f"Close case #{self.selected_case_id}?"):
            try:
                self.service.close_case(self.selected_case_id)
                self._load_cases()
                self._load_details_worker(self.selected_case_id)
            except Exception as e:
                messagebox.showerror("Error", str(e))
