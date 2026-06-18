import tkinter as tk
from tkinter import ttk
from typing import Any, List, Dict
from ui.widgets.theme import CARD_COLOR, SIDEBAR_COLOR, TEXT_COLOR, SUBTEXT_COLOR, PRIMARY_COLOR

class TableWidget(ttk.Frame):
    """
    A premium scrollable grid table widget wrapping ttk.Treeview.
    Supports column sorting, custom scrollbars, and alternating row colors.
    """
    def __init__(self, parent, columns: List[str], headers: List[str], **kwargs) -> None:
        super().__init__(parent, style="TFrame", **kwargs)
        
        self.columns = columns
        self.headers = headers
        self.sort_states: Dict[str, bool] = {col: False for col in columns}

        # Grid container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Scrollbars
        self.vsb = ttk.Scrollbar(self, orient="vertical")
        self.vsb.grid(row=0, column=1, sticky="ns")

        self.hsb = ttk.Scrollbar(self, orient="horizontal")
        self.hsb.grid(row=1, column=0, sticky="ew")

        # Treeview
        self.tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
            selectmode="browse"
        )
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.vsb.configure(command=self.tree.yview)
        self.hsb.configure(command=self.tree.xview)

        # Setup column headers and sorting hooks
        for col, head in zip(columns, headers):
            self.tree.heading(col, text=head, command=lambda c=col: self._sort_column(c))
            self.tree.column(col, anchor="w", width=120)

        # Alternating row colors styling tags
        self.tree.tag_configure("even", background="#1E293B")
        self.tree.tag_configure("odd", background="#151F32")

    def _sort_column(self, col: str) -> None:
        """
        Sorts the Treeview rows by a specific column ascending or descending.
        """
        reverse = self.sort_states[col]
        self.sort_states[col] = not reverse

        # Read items
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children("")]
        
        # Try sorting as numbers if conversion is clean
        try:
            data.sort(key=lambda t: float(str(t[0]).replace("$", "").replace("%", "").strip()), reverse=reverse)
        except ValueError:
            data.sort(reverse=reverse)

        # Re-pack rows in sorted order
        for idx, (val, child) in enumerate(data):
            self.tree.move(child, "", idx)
            # Re-apply alternating tags
            tag = "even" if idx % 2 == 0 else "odd"
            self.tree.item(child, tags=(tag,))

    def clear(self) -> None:
        """
        Removes all rows.
        """
        for child in self.tree.get_children():
            self.tree.delete(child)

    def insert_row(self, values: List[Any], item_id: Any = None) -> str:
        """
        Inserts a row into the grid table.
        """
        idx = len(self.tree.get_children())
        tag = "even" if idx % 2 == 0 else "odd"
        
        row_id = self.tree.insert("", "end", iid=item_id, values=values, tags=(tag,))
        return row_id

    def get_selected_item(self) -> Any:
        """
        Returns the ID or values of the currently selected row.
        """
        sel = self.tree.selection()
        if not sel:
            return None
        return sel[0]

    def get_row_values(self, item_id: str) -> List[Any]:
        return self.tree.item(item_id, "values")

    def bind_double_click(self, callback) -> None:
        self.tree.bind("<Double-1>", lambda event: callback(self.get_selected_item()))

    def bind_select(self, callback) -> None:
        self.tree.bind("<<TreeviewSelect>>", lambda event: callback(self.get_selected_item()))
