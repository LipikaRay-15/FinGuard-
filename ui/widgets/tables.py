import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from typing import Any, Callable, List, Optional

from ui.widgets.theme import (
    CARD_COLOR, BG_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, FONT_BODY, FONT_SUBHEADER
)


class TableWidget(ctk.CTkFrame):
    """
    A production-quality dark-themed table widget.
    Wraps ttk.Treeview (dark-styled) inside a CTkFrame with styled scrollbars.
    """

    def __init__(self, parent, columns: List[str], headers: List[str],
                 row_height: int = 36, style: str = "Dark.Treeview",
                 column_widths: Optional[dict] = None,
                 column_alignments: Optional[dict] = None, **kwargs):
        super().__init__(parent, fg_color="transparent", corner_radius=10, **kwargs)

        self._select_callback: Optional[Callable] = None
        self._dbl_callback: Optional[Callable] = None
        self._columns = columns
        self._item_id_map = {}

        # Outer border frame
        border = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10, border_width=1, border_color="#2D3748")
        border.pack(fill="both", expand=True)

        # Treeview + scrollbars container (using grid for exact alignments)
        tree_frame = tk.Frame(border, bg=CARD_COLOR)
        tree_frame.pack(fill="both", expand=True, padx=1, pady=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            style=style,
            selectmode="browse"
        )

        # Map common fields to proportional widths
        width_map = {
            "customer_id": 80,
            "cust_id": 80,
            "tx_id": 100,
            "first_name": 120,
            "last_name": 120,
            "name": 160,
            "email": 220,
            "phone": 140,
            "status": 100,
            "amount": 120,
            "merchant": 160,
            "type": 120,
            "time": 160,
            "score": 100,
            "tier": 100
        }

        # Configure columns and headers using native Treeview mechanism
        for i, col in enumerate(columns):
            heading_text = headers[i] if i < len(headers) else col
            
            # Use custom alignments if provided, otherwise default to "w" (left-aligned)
            align = "w"
            if column_alignments and col in column_alignments:
                align = column_alignments[col]
            
            self._tree.heading(col, text=heading_text, anchor=align)
            
            # Use custom widths if provided, otherwise fallback to default maps
            if column_widths and col in column_widths:
                col_width = column_widths[col]
            else:
                col_width = width_map.get(col.lower(), 120)
                
            self._tree.column(col, anchor=align, width=col_width, minwidth=70, stretch=True)

        # Scrollbars configured via Grid to prevent overlaps and alignment issues
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical",
                                command=self._tree.yview, style="Dark.Vertical.TScrollbar")
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal",
                                command=self._tree.xview, style="Dark.Horizontal.TScrollbar")
        
        self._tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Grid placement
        self._tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        # Tag configuration for alternating rows
        self._tree.tag_configure("odd",  background=CARD_COLOR)
        self._tree.tag_configure("even", background="#172033")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", self._on_double_click)

        self._row_count = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Remove all rows."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._item_id_map.clear()
        self._row_count = 0

    def insert_row(self, values: List[Any], item_id: Any = None) -> None:
        """Insert a single row. item_id is the custom logical ID (e.g., DB primary key)."""
        tag = "even" if self._row_count % 2 == 0 else "odd"
        str_values = [str(v) if v is not None else "" for v in values]
        iid = self._tree.insert("", "end", values=str_values, tags=(tag,))
        if item_id is not None:
            self._item_id_map[iid] = item_id
        self._row_count += 1

    def bind_select(self, callback: Callable[[Any], None]) -> None:
        """Register a callback fired with the selected item_id."""
        self._select_callback = callback

    def bind_double_click(self, callback: Callable[[Any], None]) -> None:
        """Register a callback fired on double-click with the selected item_id."""
        self._dbl_callback = callback

    def get_selected_id(self) -> Optional[Any]:
        sel = self._tree.selection()
        if not sel:
            return None
        iid = sel[0]
        return self._item_id_map.get(iid, iid)

    # ── Internal Handlers ────────────────────────────────────────────────────

    def _on_select(self, event) -> None:
        if self._select_callback:
            item_id = self.get_selected_id()
            if item_id is not None:
                self._select_callback(item_id)

    def _on_double_click(self, event) -> None:
        if self._dbl_callback:
            item_id = self.get_selected_id()
            if item_id is not None:
                self._dbl_callback(item_id)
