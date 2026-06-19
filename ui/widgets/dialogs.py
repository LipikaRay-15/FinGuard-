"""
FinGuard UI – Dialog Widgets
All modal dialogs built with CTkToplevel.
Backward-compatible names: DialogWidget, CustomerFormDialog,
CaseNotesDialog, CaseResolveDialog, AssignAnalystDialog.
"""
import customtkinter as ctk
from typing import Any, Callable, Dict, Optional
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, DANGER_COLOR,
    FONT_FAMILY
)


# ── Base Dialog ───────────────────────────────────────────────────────────────

class DialogWidget(ctk.CTkToplevel):
    """
    Base modal dialog. Centered on parent, blocks parent interaction.
    """
    def __init__(self, parent, title: str, width: int = 480, height: int = 360, **kwargs):
        super().__init__(parent, **kwargs)
        self.title(title)
        self.configure(fg_color=BG_COLOR)
        self.resizable(False, False)

        # Center on parent or screen
        self.update_idletasks()
        try:
            scaling = self._get_window_scaling()
        except Exception:
            scaling = 1.0

        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            if pw <= 1 or ph <= 1:
                raise ValueError
        except Exception:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            px, py, pw, ph = 0, 0, sw, sh

        x = px + (pw - int(width * scaling)) // 2
        y = py + (ph - int(height * scaling)) // 2
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self.protocol("WM_DELETE_WINDOW", self.close)

    def close(self) -> None:
        self.grab_release()
        self.destroy()


# ── Customer Form Dialog ──────────────────────────────────────────────────────

class CustomerFormDialog(DialogWidget):
    """
    Add / Edit Customer form dialog with validation.
    Fires submit_callback(data: dict) on successful submit.
    """
    FIELDS = [
        ("first_name",      "First Name *",             "entry",    None),
        ("last_name",       "Last Name *",              "entry",    None),
        ("email",           "Email *",                  "entry",    None),
        ("date_of_birth",   "Date of Birth (YYYY-MM-DD)","entry",   None),
        ("gender",          "Gender",                   "combo",    ["Male","Female","Other","Prefer not to say"]),
        ("phone",           "Phone Number",             "entry",    None),
        ("pan",             "PAN (ABCDE1234F)",         "entry",    None),
        ("account_number",  "Account Number",           "entry",    None),
        ("pincode",         "Pincode *",                "entry",    None),
        ("city",            "City",                     "readonly", None),
        ("state",           "State",                    "readonly", None),
        ("country",         "Country",                  "readonly", None),
        ("address",         "Address",                  "entry",    None),
        ("status",          "Status",                   "combo",    ["ACTIVE","BLOCKED","SUSPENDED","INACTIVE"]),
    ]

    def __init__(self, parent, title: str,
                 customer_data: Optional[Dict[str, Any]] = None,
                 submit_callback: Optional[Callable] = None, **kwargs):
        super().__init__(parent, title, width=520, height=640, **kwargs)
        self.submit_callback = submit_callback
        self.customer_data = customer_data or {}
        self.inputs: Dict[str, Any] = {}

        self._build_ui(title)

    def _build_ui(self, title: str) -> None:
        # Title bar
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=title,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", padx=20, pady=15)

        # Error label
        self._error_lbl = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=DANGER_COLOR,
            wraplength=440,
            justify="left"
        )

        # Scrollable form
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_fg_color=BG_COLOR,
            scrollbar_button_color="#334155"
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(12, 0))

        for key, label, f_type, choices in self.FIELDS:
            self._add_field(scroll, key, label, f_type, choices)

        # Pincode auto-resolve
        if "pincode" in self.inputs:
            self.inputs["pincode"].bind("<KeyRelease>", self._on_pincode_changed)

        # Buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=56)
        btn_row.pack(fill="x", padx=20, pady=12)
        btn_row.pack_propagate(False)

        ctk.CTkButton(
            btn_row, text="Cancel",
            fg_color="#334155", hover_color="#475569",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            width=100, height=36, corner_radius=8,
            command=self.close
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            btn_row, text="💾  Save Customer",
            fg_color=PRIMARY_COLOR, hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            width=160, height=36, corner_radius=8,
            command=self._submit
        ).pack(side="right")

    def _add_field(self, parent, key: str, label: str, f_type: str, choices) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.pack(fill="x", pady=5)

        ctk.CTkLabel(
            wrap, text=label,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            text_color=SUBTEXT_COLOR,
            anchor="w"
        ).pack(anchor="w", pady=(0, 2))

        default = self.customer_data.get(key, "") or ""

        if f_type == "entry":
            ent = ctk.CTkEntry(
                wrap, fg_color=CARD_COLOR, border_color="#334155",
                text_color=TEXT_COLOR, placeholder_text_color=SUBTEXT_COLOR,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                height=34, corner_radius=6
            )
            ent.insert(0, str(default))
            ent.pack(fill="x")
            self.inputs[key] = ent

        elif f_type == "readonly":
            ent = ctk.CTkEntry(
                wrap, fg_color="#0F172A", border_color="#1E293B",
                text_color=SUBTEXT_COLOR, state="disabled",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                height=34, corner_radius=6
            )
            if default:
                ent.configure(state="normal")
                ent.insert(0, str(default))
                ent.configure(state="disabled")
            ent.pack(fill="x")
            self.inputs[key] = ent

        elif f_type == "combo":
            cmb = ctk.CTkComboBox(
                wrap, values=choices or [],
                fg_color=CARD_COLOR, border_color="#334155",
                text_color=TEXT_COLOR, button_color="#334155",
                dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                height=34, corner_radius=6, state="readonly"
            )
            if str(default) in (choices or []):
                cmb.set(str(default))
            elif choices:
                cmb.set(choices[0])
            cmb.pack(fill="x")
            self.inputs[key] = cmb

    def _on_pincode_changed(self, event=None) -> None:
        if "pincode" not in self.inputs:
            return
        pincode = self.inputs["pincode"].get().strip()
        if len(pincode) == 6 and pincode.isdigit():
            try:
                from services.pincode_service import PincodeService
                loc = PincodeService.fetch_location_from_pincode(pincode)
                if loc:
                    for k in ["city", "state", "country"]:
                        if k in self.inputs:
                            e = self.inputs[k]
                            e.configure(state="normal")
                            e.delete(0, "end")
                            e.insert(0, loc[k])
                            e.configure(state="disabled")
            except Exception:
                pass

    def _submit(self) -> None:
        self._error_lbl.pack_forget()
        data = {}
        for key, widget in self.inputs.items():
            try:
                val = widget.get().strip()
                data[key] = val if val else None
            except Exception:
                data[key] = None

        if self.submit_callback:
            try:
                self.submit_callback(data)
                self.close()
            except Exception as exc:
                self._error_lbl.configure(text=f"⚠  {exc}")
                self._error_lbl.pack(fill="x", padx=20, pady=(4, 0))


# ── Case Notes Dialog ─────────────────────────────────────────────────────────

class CaseNotesDialog(DialogWidget):
    def __init__(self, parent, case_id: int, submit_callback: Callable, **kwargs):
        super().__init__(parent, f"Add Note — Case #{case_id}", width=440, height=280, **kwargs)
        self.submit_callback = submit_callback
        self._build_ui(case_id)

    def _build_ui(self, case_id: int) -> None:
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=f"📝  Append Analyst Note — Case #{case_id}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", padx=16, pady=14)

        self._txt = ctk.CTkTextbox(
            self, fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            corner_radius=8, height=120
        )
        self._txt.pack(fill="both", expand=True, padx=16, pady=12)
        self._txt.focus_set()

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=48)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        btn_row.pack_propagate(False)

        ctk.CTkButton(btn_row, text="Cancel", fg_color="#334155",
                      hover_color="#475569", width=90, height=34, corner_radius=8,
                      command=self.close).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Append Note", fg_color=PRIMARY_COLOR,
                      hover_color="#1D4ED8", width=130, height=34, corner_radius=8,
                      command=self._submit).pack(side="right")

    def _submit(self) -> None:
        val = self._txt.get("1.0", "end").strip()
        if val:
            self.submit_callback(val)
            self.close()


# ── Case Resolve Dialog ───────────────────────────────────────────────────────

class CaseResolveDialog(DialogWidget):
    def __init__(self, parent, case_id: int, submit_callback: Callable, **kwargs):
        super().__init__(parent, f"Resolve Case #{case_id}", width=440, height=280, **kwargs)
        self.submit_callback = submit_callback
        self._build_ui(case_id)

    def _build_ui(self, case_id: int) -> None:
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=f"✅  Resolution Notes — Case #{case_id}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", padx=16, pady=14)

        self._txt = ctk.CTkTextbox(
            self, fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            corner_radius=8, height=120
        )
        self._txt.pack(fill="both", expand=True, padx=16, pady=12)
        self._txt.focus_set()

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=48)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        btn_row.pack_propagate(False)

        ctk.CTkButton(btn_row, text="Cancel", fg_color="#334155",
                      hover_color="#475569", width=90, height=34, corner_radius=8,
                      command=self.close).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Resolve Case", fg_color=SUCCESS_COLOR,
                      hover_color="#059669", width=130, height=34, corner_radius=8,
                      command=self._submit).pack(side="right")

    def _submit(self) -> None:
        val = self._txt.get("1.0", "end").strip()
        if val:
            self.submit_callback(val)
            self.close()


# ── Assign Analyst Dialog ─────────────────────────────────────────────────────

class AssignAnalystDialog(DialogWidget):
    ANALYSTS = [
        "Analyst James", "Analyst Sarah", "Analyst Bob",
        "Analyst Priya", "Analyst Chen", "System Queue"
    ]

    def __init__(self, parent, case_id: int, submit_callback: Callable, **kwargs):
        super().__init__(parent, f"Assign Analyst — Case #{case_id}", width=400, height=220, **kwargs)
        self.submit_callback = submit_callback
        self._build_ui(case_id)

    def _build_ui(self, case_id: int) -> None:
        header = ctk.CTkFrame(self, fg_color=CARD_COLOR, corner_radius=0, height=52)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text=f"👥  Assign Investigator — Case #{case_id}",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_COLOR
        ).pack(side="left", padx=16, pady=14)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(body, text="Select Analyst:",
                     text_color=SUBTEXT_COLOR,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=11)).pack(anchor="w", pady=(0, 6))

        self._cmb = ctk.CTkComboBox(
            body, values=self.ANALYSTS,
            fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR, button_color="#334155",
            dropdown_fg_color=CARD_COLOR, dropdown_text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            height=34, corner_radius=6, state="readonly"
        )
        self._cmb.set(self.ANALYSTS[0])
        self._cmb.pack(fill="x")

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=48)
        btn_row.pack(fill="x", padx=16, pady=(0, 12))
        btn_row.pack_propagate(False)

        ctk.CTkButton(btn_row, text="Cancel", fg_color="#334155",
                      hover_color="#475569", width=90, height=34, corner_radius=8,
                      command=self.close).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Assign", fg_color=PRIMARY_COLOR,
                      hover_color="#1D4ED8", width=100, height=34, corner_radius=8,
                      command=self._submit).pack(side="right")

    def _submit(self) -> None:
        val = self._cmb.get().strip()
        if val:
            self.submit_callback(val)
            self.close()


# ── Generic Input Dialog (replaces simpledialog.askstring) ────────────────────

class InputDialog(DialogWidget):
    """
    Simple single-field text input dialog.
    Returns the entered value via callback.
    """
    def __init__(self, parent, title: str, prompt: str,
                 submit_callback: Callable[[str], None], **kwargs):
        super().__init__(parent, title, width=400, height=200, **kwargs)
        self.submit_callback = submit_callback

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(body, text=prompt,
                     text_color=TEXT_COLOR,
                     font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                     wraplength=360, justify="left").pack(anchor="w", pady=(0, 10))

        self._ent = ctk.CTkEntry(
            body, fg_color=CARD_COLOR, border_color="#334155",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            height=34, corner_radius=6
        )
        self._ent.pack(fill="x")
        self._ent.focus_set()
        self._ent.bind("<Return>", lambda e: self._submit())

        btn_row = ctk.CTkFrame(self, fg_color="transparent", height=48)
        btn_row.pack(fill="x", padx=20, pady=(0, 12))
        btn_row.pack_propagate(False)

        ctk.CTkButton(btn_row, text="Cancel", fg_color="#334155",
                      hover_color="#475569", width=90, height=34, corner_radius=8,
                      command=self.close).pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_row, text="Confirm", fg_color=PRIMARY_COLOR,
                      hover_color="#1D4ED8", width=100, height=34, corner_radius=8,
                      command=self._submit).pack(side="right")

    def _submit(self) -> None:
        val = self._ent.get().strip()
        if val:
            self.submit_callback(val)
            self.close()
