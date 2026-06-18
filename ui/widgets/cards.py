import tkinter as tk
from tkinter import ttk
from ui.widgets.theme import CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR, FONT_CAPTION, FONT_HEADER, FONT_BODY

class CardWidget(ttk.Frame):
    """
    A premium card container widget showing a metrics category, numerical value,
    and supplementary status or percentage changes.
    """
    def __init__(self, parent, title: str, value: str, subtext: str = "", trend_color: str = None, **kwargs) -> None:
        super().__init__(parent, style="Card.TFrame", **kwargs)
        
        # Internal styling & packing
        # Standard padding frame for card contents
        self.pad_frame = tk.Frame(self, bg=CARD_COLOR, padx=16, pady=16)
        self.pad_frame.pack(fill="both", expand=True)

        self.title_lbl = ttk.Label(self.pad_frame, text=title, style="CardTitle.TLabel")
        self.title_lbl.pack(anchor="w", pady=(0, 6))

        self.value_lbl = ttk.Label(self.pad_frame, text=value, style="CardVal.TLabel")
        self.value_lbl.pack(anchor="w", pady=(0, 4))
        
        self.sub_lbl = ttk.Label(self.pad_frame, text=subtext, style="Card.TLabel", font=FONT_CAPTION)
        if trend_color:
            self.sub_lbl.configure(foreground=trend_color)
        else:
            self.sub_lbl.configure(foreground=SUBTEXT_COLOR)
        self.sub_lbl.pack(anchor="w")

    def update_value(self, new_val: str, new_subtext: str = None) -> None:
        self.value_lbl.configure(text=new_val)
        if new_subtext is not None:
            self.sub_lbl.configure(text=new_subtext)
