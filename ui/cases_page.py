import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading
from typing import Dict, Any, List

# Reusable widgets
from ui.widgets.status_badges import StatusBadge
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, WARNING_COLOR, DANGER_COLOR,
    FONT_HEADER, FONT_SUBHEADER, FONT_BODY, FONT_CAPTION
)
from ui.widgets.dialogs import CaseNotesDialog, CaseResolveDialog, AssignAnalystDialog

# Backend imports
from services import CaseService

class CasesPage(ttk.Frame):
    """
    Kanban Case Board. Separates cases into columns based on status:
    OPEN, UNDER_REVIEW, ESCALATED, RESOLVED, CLOSED.
    Provides overlays for assignments, note inputs, and closures.
    """
    def __init__(self, parent) -> None:
        super().__init__(parent, style="TFrame")
        self.service = CaseService()

        # Selection state reference
        self.selected_case_id = None
        self.selected_case_data = None

        # Header Frame
        self.header_frame = tk.Frame(self, bg=BG_COLOR)
        self.header_frame.pack(fill="x", pady=(10, 20))

        self.title_lbl = ttk.Label(self.header_frame, text="Compliance & Cases Board", style="HeaderTitle.TLabel")
        self.title_lbl.pack(side="left")
        
        self.refresh_btn = ttk.Button(self.header_frame, text="🔄 Refresh Board", command=self._load_cases)
        self.refresh_btn.pack(side="right")

        # Main Split panel
        self.main_split = tk.Frame(self, bg=BG_COLOR)
        self.main_split.pack(fill="both", expand=True)
        self.main_split.columnconfigure(0, weight=4) # Left: Kanban Board
        self.main_split.columnconfigure(1, weight=2) # Right: Details Panel

        # Left Kanban Scroll Container
        self.kanban_canvas = tk.Canvas(self.main_split, bg=BG_COLOR, highlightthickness=0, bd=0)
        self.kanban_scrollbar = ttk.Scrollbar(self.main_split, orient="horizontal", command=self.kanban_canvas.xview)
        
        self.board_frame = tk.Frame(self.kanban_canvas, bg=BG_COLOR)
        self.board_frame.bind(
            "<Configure>",
            lambda e: self.kanban_canvas.configure(scrollregion=self.kanban_canvas.bbox("all"))
        )
        self.kanban_canvas_win = self.kanban_canvas.create_window((0, 0), window=self.board_frame, anchor="nw")
        self.kanban_canvas.configure(xscrollcommand=self.kanban_scrollbar.set)
        self.board_frame.rowconfigure(0, weight=1)

        self.kanban_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        # Wait, grid horizontal scrollbar at row 1
        self.kanban_scrollbar.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.main_split.rowconfigure(0, weight=1)

        # Statuses list mapping columns
        self.statuses = ["OPEN", "UNDER_REVIEW", "ESCALATED", "RESOLVED", "CLOSED"]
        self.columns_frames = {}

        # Set up 5 columns
        for idx, status in enumerate(self.statuses):
            col_container = tk.Frame(self.board_frame, bg="#1E293B", width=200, padx=8, pady=8)
            col_container.pack_propagate(False)
            col_container.grid(row=0, column=idx, padx=5, sticky="ns")
            
            # Header
            lbl_title = tk.Label(col_container, text=status.replace("_", " "), bg="#1E293B", fg=TEXT_COLOR, font=FONT_SUBHEADER)
            lbl_title.pack(anchor="w", pady=(0, 10))

            # Vertical scroll frame for case cards
            scroll_c = tk.Canvas(col_container, bg="#1E293B", highlightthickness=0, bd=0)
            scroll_sb = ttk.Scrollbar(col_container, orient="vertical", command=scroll_c.yview)
            
            cards_list_frame = tk.Frame(scroll_c, bg="#1E293B")
            cards_list_frame.bind(
                "<Configure>",
                lambda e, sc=scroll_c: sc.configure(scrollregion=sc.bbox("all"))
            )
            
            win_item = scroll_c.create_window((0, 0), window=cards_list_frame, anchor="nw")
            scroll_c.configure(yscrollcommand=scroll_sb.set)
            
            scroll_c.bind("<Configure>", lambda e, sc=scroll_c, wi=win_item: sc.itemconfig(wi, width=e.width))

            scroll_c.pack(side="left", fill="both", expand=True)
            scroll_sb.pack(side="right", fill="y")
            
            self.columns_frames[status] = cards_list_frame

        # Right Column Frame (Case Details)
        self.right_frame = tk.Frame(self.main_split, bg=CARD_COLOR, padx=16, pady=16)
        self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=(10, 0))

        self.details_title = tk.Label(self.right_frame, text="Case File Dossier", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        self.details_title.pack(anchor="w", pady=(0, 15))

        self.details_container = tk.Frame(self.right_frame, bg=CARD_COLOR)
        self.details_container.pack(fill="both", expand=True)

        self.no_sel_lbl = tk.Label(self.details_container, text="Select a case card to load diagnostics.", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_BODY)
        self.no_sel_lbl.pack(pady=40)

        # Action Buttons frame (initially hidden)
        self.action_frame = tk.Frame(self.right_frame, bg=CARD_COLOR)
        
        self.assign_btn = ttk.Button(self.action_frame, text="Assign", command=self._open_assign_dialog)
        self.assign_btn.pack(side="left", padx=2)

        self.review_btn = ttk.Button(self.action_frame, text="Start Review", command=self._start_review)
        self.review_btn.pack(side="left", padx=2)

        self.note_btn = ttk.Button(self.action_frame, text="Add Note", command=self._open_note_dialog)
        self.note_btn.pack(side="left", padx=2)

        self.resolve_btn = ttk.Button(self.action_frame, text="Resolve", command=self._open_resolve_dialog, style="Success.TButton")
        self.resolve_btn.pack(side="left", padx=2)

        self.close_btn = ttk.Button(self.action_frame, text="Close Case", command=self._close_case, style="Danger.TButton")
        self.close_btn.pack(side="left", padx=2)

        # Load cases
        self._load_cases()

    def _load_cases(self) -> None:
        # Clear columns
        for status in self.statuses:
            for child in self.columns_frames[status].winfo_children():
                child.destroy()
                
        # Async load cases list
        threading.Thread(target=self._load_cases_worker, daemon=True).start()

    def _load_cases_worker(self) -> None:
        try:
            sql = "SELECT c.*, a.risk_score, a.severity FROM cases c JOIN alerts a ON c.alert_id = a.alert_id ORDER BY c.created_at DESC"
            rows = self.service.db.fetch_all(sql)
            self.after(0, self._populate_board, rows)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed to load cases: {e}"))

    def _populate_board(self, rows: List[Dict[str, Any]]) -> None:
        for r in rows:
            status = r["status"].upper()
            if status not in self.columns_frames:
                continue
            
            parent = self.columns_frames[status]
            
            # Case Card Frame
            card = tk.Frame(parent, bg="#0F172A", padx=10, pady=10, bd=0, highlightthickness=1, highlightbackground="#334155")
            card.pack(fill="x", pady=4, padx=2)
            
            case_id = r["case_id"]
            
            # Header ID & Severity indicator
            hdr = tk.Frame(card, bg="#0F172A")
            hdr.pack(fill="x")

            lbl_id = tk.Label(hdr, text=f"Case #{case_id}", bg="#0F172A", fg=TEXT_COLOR, font=FONT_SUBHEADER)
            lbl_id.pack(side="left")

            lbl_sev = tk.Label(hdr, text=r["severity"], bg="#0F172A", fg=self._get_severity_color(r["severity"]), font=FONT_CAPTION)
            lbl_sev.pack(side="right")

            # Assigned
            assignee = r["assigned_to"] or "Unassigned"
            lbl_assignee = tk.Label(card, text=f"Assignee: {assignee}", bg="#0F172A", fg=SUBTEXT_COLOR, font=FONT_CAPTION)
            lbl_assignee.pack(anchor="w", pady=(4, 0))

            # Bind selection click event
            for widget in (card, lbl_id, lbl_sev, lbl_assignee):
                widget.bind("<Button-1>", lambda event, cid=case_id: self._select_case(cid))

    def _get_severity_color(self, level: str) -> str:
        level = level.upper()
        if level == "CRITICAL" or level == "HIGH":
            return DANGER_COLOR
        elif level == "MEDIUM":
            return WARNING_COLOR
        return SUCCESS_COLOR

    def _select_case(self, case_id: int) -> None:
        self.selected_case_id = case_id
        # Fetch detailed properties in background
        threading.Thread(target=self._load_case_details_worker, args=(case_id,), daemon=True).start()

    def _load_case_details_worker(self, case_id: int) -> None:
        try:
            sql = "SELECT c.*, a.risk_score, a.severity, a.transaction_id, a.customer_id FROM cases c JOIN alerts a ON c.alert_id = a.alert_id WHERE c.case_id = %s"
            row = self.service.db.fetch_one(sql, (case_id,))
            if row:
                self.after(0, self._populate_details_panel, row)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Database Error", f"Failed retrieving case file details: {e}"))

    def _populate_details_panel(self, data: Dict[str, Any]) -> None:
        self.selected_case_data = data
        
        # Clear old details
        for child in self.details_container.winfo_children():
            child.destroy()
        self.no_sel_lbl.pack_forget()

        # Headings
        lbl_title = tk.Label(self.details_container, text=f"Case Dossier #{data['case_id']}", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        lbl_title.pack(anchor="w", pady=(0, 5))

        badge_frame = tk.Frame(self.details_container, bg=CARD_COLOR)
        badge_frame.pack(anchor="w", pady=(0, 15))

        status_b = StatusBadge(badge_frame, data["status"])
        status_b.pack(side="left", padx=(0, 10))

        priority_b = StatusBadge(badge_frame, data["priority"])
        priority_b.pack(side="left")

        # Table data rows
        fields = [
            ("Alert ID", data["alert_id"]),
            ("Customer ID", data["customer_id"]),
            ("Transaction ID", data["transaction_id"]),
            ("Assigned To", data["assigned_to"] or "System Queue (Unassigned)"),
            ("Priority Level", data["priority"]),
            ("Logged Date", data["created_at"]),
            ("Last Updated", data["updated_at"]),
            ("Resolution Notes", data["resolution"] or "None Recorded"),
        ]

        for k, v in fields:
            row = tk.Frame(self.details_container, bg=CARD_COLOR, pady=3)
            row.pack(fill="x")
            
            lbl_k = tk.Label(row, text=f"{k}:", bg=CARD_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION, width=15, anchor="w")
            lbl_k.pack(side="left")

            lbl_v = tk.Label(row, text=str(v), bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_BODY, anchor="w", justify="left", wraplength=180)
            lbl_v.pack(side="left", fill="x", expand=True)

        # Analyst Notes/Remarks Box
        lbl_notes = tk.Label(self.details_container, text="Audit Trail / Notes", bg=CARD_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER, pady=(15, 5))
        lbl_notes.pack(anchor="w")

        notes_box = tk.Text(
            self.details_container,
            bg="#0F172A",
            fg=TEXT_COLOR,
            bd=0,
            highlightthickness=0,
            font=FONT_BODY,
            height=4,
            wrap="word",
            padx=8,
            pady=8
        )
        notes_box.pack(fill="both", expand=True, pady=5)
        
        # Format text payload
        notes_payload = f"Notes:\n{data['notes'] or 'No analyst notes recorded.'}\n\nRemarks:\n{data['remarks'] or 'No remarks recorded.'}"
        notes_box.insert("1.0", notes_payload)
        notes_box.configure(state="disabled")

        # Display buttons frame
        self.action_frame.pack(fill="x", side="bottom", pady=10)

    def _open_assign_dialog(self) -> None:
        if self.selected_case_id:
            AssignAnalystDialog(self, self.selected_case_id, submit_callback=self._submit_assign)

    def _submit_assign(self, name: str) -> None:
        try:
            self.service.assign_case(self.selected_case_id, name)
            self._load_cases()
            self._load_case_details_worker(self.selected_case_id)
            messagebox.showinfo("Success", f"Case assigned to {name}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed assigning case: {e}")

    def _start_review(self) -> None:
        if not self.selected_case_id:
            return
        try:
            self.service.change_status(self.selected_case_id, "UNDER_REVIEW")
            self._load_cases()
            self._load_case_details_worker(self.selected_case_id)
            messagebox.showinfo("Success", "Case status changed to UNDER_REVIEW.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed status change: {e}")

    def _open_note_dialog(self) -> None:
        if self.selected_case_id:
            CaseNotesDialog(self, self.selected_case_id, submit_callback=self._submit_note)

    def _submit_note(self, text: str) -> None:
        try:
            self.service.add_analyst_note(self.selected_case_id, text)
            self._load_cases()
            self._load_case_details_worker(self.selected_case_id)
            messagebox.showinfo("Success", "Analyst note appended successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed appending note: {e}")

    def _open_resolve_dialog(self) -> None:
        if self.selected_case_id:
            CaseResolveDialog(self, self.selected_case_id, submit_callback=self._submit_resolve)

    def _submit_resolve(self, text: str) -> None:
        try:
            self.service.resolve_case(self.selected_case_id, text)
            self._load_cases()
            self._load_case_details_worker(self.selected_case_id)
            messagebox.showinfo("Success", "Case marked as RESOLVED.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed resolving: {e}")

    def _close_case(self) -> None:
        if not self.selected_case_id:
            return
        confirm = messagebox.askyesno("Close Case", "Mark case status as CLOSED?")
        if confirm:
            try:
                self.service.close_case(self.selected_case_id)
                self._load_cases()
                self._load_case_details_worker(self.selected_case_id)
                messagebox.showinfo("Success", "Case CLOSED.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed closing case: {e}")
