import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, Optional
from ui.widgets.theme import (
    BG_COLOR,
    CARD_COLOR,
    TEXT_COLOR,
    SUBTEXT_COLOR,
    PRIMARY_COLOR,
    SUCCESS_COLOR,
    DANGER_COLOR,
    FONT_HEADER,
    FONT_SUBHEADER,
    FONT_BODY,
    FONT_CAPTION
)

class DialogWidget(tk.Toplevel):
    """
    A premium dark-themed top-level dialog wrapper.
    Blocks parent interaction using grab_set().
    """
    def __init__(self, parent, title: str, width: int = 400, height: int = 300, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.title(title)
        self.configure(bg=BG_COLOR)
        
        # Center in parent window
        parent_x = parent.winfo_rootx()
        parent_y = parent.winfo_rooty()
        parent_w = parent.winfo_width()
        parent_h = parent.winfo_height()
        
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        self.transient(parent)
        self.grab_set()
        
        # Focus on first widget
        self.focus_set()
        
        # Grid container
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        # Style standard widgets
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self) -> None:
        self.grab_release()
        self.destroy()

class CustomerFormDialog(DialogWidget):
    """
    Form dialog to capture Customer fields. Runs a submit callback on submit.
    Displays aggregated formatting errors on top if raised.
    """
    def __init__(self, parent, title: str, customer_data: Optional[Dict[str, Any]] = None, submit_callback=None) -> None:
        super().__init__(parent, title, width=500, height=600)
        self.submit_callback = submit_callback
        self.customer_data = customer_data or {}
        
        # Main container
        self.main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        # Header Label
        lbl = tk.Label(self.main_frame, text=title, bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_HEADER)
        lbl.pack(anchor="w", pady=(0, 15))

        # Scrollable Form
        self.canvas = tk.Canvas(self.main_frame, bg=BG_COLOR, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        
        self.form_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.form_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas_win = self.canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_win, width=e.width))

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Fields Definitions
        self.fields = [
            ("first_name", "First Name *", "entry", None),
            ("last_name", "Last Name *", "entry", None),
            ("email", "Email *", "entry", None),
            ("date_of_birth", "Date of Birth (YYYY-MM-DD)", "entry", None),
            ("gender", "Gender", "combo", ["Male", "Female", "Other", "Prefer not to say"]),
            ("phone", "Phone Number", "entry", None),
            ("pan", "PAN (ABCDE1234F)", "entry", None),
            ("account_number", "Account Number", "entry", None),
            ("pincode", "Pincode *", "entry", None),
            ("city", "City", "entry_readonly", None),
            ("state", "State", "entry_readonly", None),
            ("country", "Country", "entry_readonly", None),
            ("address", "Address", "entry", None),
            ("status", "Status", "combo", ["ACTIVE", "BLOCKED", "SUSPENDED", "INACTIVE"]),
        ]

        self.inputs = {}
        for key, label, f_type, choices in self.fields:
            row = tk.Frame(self.form_frame, bg=BG_COLOR, pady=6)
            row.pack(fill="x")

            lbl = tk.Label(row, text=label, bg=BG_COLOR, fg=SUBTEXT_COLOR, font=FONT_CAPTION)
            lbl.pack(anchor="w")

            default_val = self.customer_data.get(key, "")
            if default_val is None:
                default_val = ""
                
            if f_type == "entry":
                ent = ttk.Entry(row, style="TEntry")
                ent.insert(0, str(default_val))
                ent.pack(fill="x", pady=2)
                self.inputs[key] = ent
            elif f_type == "entry_readonly":
                ent = ttk.Entry(row, style="TEntry")
                ent.insert(0, str(default_val))
                ent.configure(state="readonly")
                ent.pack(fill="x", pady=2)
                self.inputs[key] = ent
            elif f_type == "combo":
                cmb = ttk.Combobox(row, values=choices, style="TCombobox", state="readonly")
                if str(default_val) in choices:
                    cmb.set(str(default_val))
                elif key == "status" and not default_val:
                    cmb.set("ACTIVE")
                elif key == "gender" and not default_val:
                    cmb.set("Male")
                cmb.pack(fill="x", pady=2)
                self.inputs[key] = cmb

        self.inputs["pincode"].bind("<KeyRelease>", self._on_pincode_changed)

    def _on_pincode_changed(self, event=None) -> None:
        pincode = self.inputs["pincode"].get().strip()
        if len(pincode) == 6 and pincode.isdigit():
            from services.pincode_service import PincodeService
            loc = PincodeService.fetch_location_from_pincode(pincode)
            if loc:
                for k in ["city", "state", "country"]:
                    ent = self.inputs[k]
                    ent.configure(state="normal")
                    ent.delete(0, tk.END)
                    ent.insert(0, loc[k])
                    ent.configure(state="readonly")
        else:
            for k in ["city", "state", "country"]:
                ent = self.inputs[k]
                ent.configure(state="normal")
                ent.delete(0, tk.END)
                ent.configure(state="readonly")

        # Action Buttons frame
        self.btn_frame = tk.Frame(self.main_frame, bg=BG_COLOR, pady=10)
        self.btn_frame.pack(fill="x", side="bottom")

        # Error text frame (initially hidden)
        self.error_lbl = tk.Label(self.main_frame, text="", bg=BG_COLOR, fg=DANGER_COLOR, font=FONT_CAPTION, justify="left")

        self.submit_btn = ttk.Button(self.btn_frame, text="Save Customer", command=self._submit)
        self.submit_btn.pack(side="right", padx=(10, 0))

        self.cancel_btn = ttk.Button(self.btn_frame, text="Cancel", command=self.close)
        self.cancel_btn.pack(side="right")

    def _submit(self) -> None:
        # Hide previous errors
        self.error_lbl.pack_forget()
        
        # Read form values
        data = {}
        for key, entry in self.inputs.items():
            val = entry.get().strip()
            # Convert empty values back to None
            data[key] = val if val else None

        if self.submit_callback:
            try:
                self.submit_callback(data)
                self.close()
            except Exception as e:
                # Show errors aggregated
                self.error_lbl.configure(text=str(e))
                self.error_lbl.pack(fill="x", side="top", pady=10)

class CaseNotesDialog(DialogWidget):
    """
    Popup to prompt note stream additions.
    """
    def __init__(self, parent, case_id: int, submit_callback) -> None:
        super().__init__(parent, "Append Analyst Note", width=400, height=250)
        self.submit_callback = submit_callback

        self.main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        lbl = tk.Label(self.main_frame, text=f"Append Note for Case #{case_id}", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER)
        lbl.pack(anchor="w", pady=(0, 10))

        self.txt = tk.Text(
            self.main_frame,
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            bd=1,
            relief="flat",
            insertbackground=TEXT_COLOR,
            font=FONT_BODY,
            height=5
        )
        self.txt.pack(fill="both", expand=True, pady=10)
        self.txt.focus_set()

        btn_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        btn_frame.pack(fill="x", side="bottom")

        self.save_btn = ttk.Button(btn_frame, text="Append Note", command=self._submit)
        self.save_btn.pack(side="right", padx=(10, 0))

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.close)
        self.cancel_btn.pack(side="right")

    def _submit(self) -> None:
        val = self.txt.get("1.0", "end").strip()
        if val:
            self.submit_callback(val)
            self.close()

class CaseResolveDialog(DialogWidget):
    """
    Popup to prompt resolution text input.
    """
    def __init__(self, parent, case_id: int, submit_callback) -> None:
        super().__init__(parent, "Resolve Case", width=400, height=250)
        self.submit_callback = submit_callback

        self.main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        lbl = tk.Label(self.main_frame, text=f"Resolution Details for Case #{case_id}", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER)
        lbl.pack(anchor="w", pady=(0, 10))

        self.txt = tk.Text(
            self.main_frame,
            bg=CARD_COLOR,
            fg=TEXT_COLOR,
            bd=1,
            relief="flat",
            insertbackground=TEXT_COLOR,
            font=FONT_BODY,
            height=5
        )
        self.txt.pack(fill="both", expand=True, pady=10)
        self.txt.focus_set()

        btn_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        btn_frame.pack(fill="x", side="bottom")

        self.save_btn = ttk.Button(btn_frame, text="Resolve Case", command=self._submit)
        self.save_btn.pack(side="right", padx=(10, 0))

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.close)
        self.cancel_btn.pack(side="right")

    def _submit(self) -> None:
        val = self.txt.get("1.0", "end").strip()
        if val:
            self.submit_callback(val)
            self.close()

class AssignAnalystDialog(DialogWidget):
    """
    Popup to assign analyst.
    """
    def __init__(self, parent, case_id: int, submit_callback) -> None:
        super().__init__(parent, "Assign Analyst", width=350, height=200)
        self.submit_callback = submit_callback

        self.main_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.main_frame.pack(fill="both", expand=True)

        lbl = tk.Label(self.main_frame, text=f"Assign Analyst for Case #{case_id}", bg=BG_COLOR, fg=TEXT_COLOR, font=FONT_SUBHEADER)
        lbl.pack(anchor="w", pady=(0, 10))

        # Analyst choices
        self.cmb = ttk.Combobox(
            self.main_frame,
            values=["Analyst James", "Analyst Sarah", "Analyst Bob", "Analyst James", "System Queue"],
            style="TCombobox",
            state="readonly"
        )
        self.cmb.set("Analyst James")
        self.cmb.pack(fill="x", pady=15)
        self.cmb.focus_set()

        btn_frame = tk.Frame(self.main_frame, bg=BG_COLOR)
        btn_frame.pack(fill="x", side="bottom")

        self.save_btn = ttk.Button(btn_frame, text="Assign", command=self._submit)
        self.save_btn.pack(side="right", padx=(10, 0))

        self.cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.close)
        self.cancel_btn.pack(side="right")

    def _submit(self) -> None:
        val = self.cmb.get().strip()
        if val:
            self.submit_callback(val)
            self.close()
