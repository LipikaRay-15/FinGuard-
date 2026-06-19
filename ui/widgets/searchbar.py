"""
FinGuard UI – SearchBar Widget
Premium CTkFrame search bar with icon button and placeholder text.
"""
import customtkinter as ctk
from typing import Callable, Optional
from ui.widgets.theme import (
    CARD_COLOR, BG_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, BORDER_COLOR, FONT_FAMILY
)


class SearchBar(ctk.CTkFrame):
    """
    A styled search input with magnifier button and placeholder text.
    Fires search_callback(query: str) on Enter or button click.
    """
    def __init__(self, parent, placeholder: str = "Search...",
                 search_callback: Optional[Callable[[str], None]] = None, **kwargs):
        super().__init__(parent, fg_color=CARD_COLOR, corner_radius=8, **kwargs)

        self._callback = search_callback
        self._placeholder = placeholder
        self._has_placeholder = True

        # Search icon label
        icon_lbl = ctk.CTkLabel(
            self,
            text="🔍",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=SUBTEXT_COLOR,
            width=30,
            fg_color="transparent"
        )
        icon_lbl.pack(side="left", padx=(10, 0))

        # Entry field
        self._entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            fg_color="transparent",
            border_width=0,
            text_color=TEXT_COLOR,
            placeholder_text_color=SUBTEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        self._entry.bind("<Return>", self._on_search)

        # Clear button
        self._clear_btn = ctk.CTkButton(
            self,
            text="✕",
            width=28,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#334155",
            text_color=SUBTEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            command=self._clear
        )
        self._clear_btn.pack(side="right", padx=(0, 6))

        # Search button
        search_btn = ctk.CTkButton(
            self,
            text="Search",
            width=72,
            height=28,
            corner_radius=6,
            fg_color=PRIMARY_COLOR,
            hover_color="#1D4ED8",
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            command=self._on_search
        )
        search_btn.pack(side="right", padx=(0, 6))

    def _on_search(self, event=None) -> None:
        query = self._entry.get().strip()
        if self._callback:
            self._callback(query)

    def _clear(self) -> None:
        self._entry.delete(0, "end")
        if self._callback:
            self._callback("")

    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, text: str) -> None:
        self._entry.delete(0, "end")
        self._entry.insert(0, text)
