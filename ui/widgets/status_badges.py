"""
FinGuard UI – StatusBadge Widget
Colored pill badge for status / severity display.
"""
import customtkinter as ctk
from ui.widgets.theme import (
    STATUS_COLORS, SEVERITY_COLORS,
    TEXT_COLOR, SUBTEXT_COLOR, CARD_COLOR,
    FONT_FAMILY
)


class StatusBadge(ctk.CTkLabel):
    """
    A small colored pill label showing a status or severity string.
    Automatically selects color based on the value.
    """
    def __init__(self, parent, value: str, **kwargs):
        color = self._resolve_color(value)
        super().__init__(
            parent,
            text=f"  {value}  ",
            fg_color=color,
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            corner_radius=6,
            **kwargs
        )

    def _resolve_color(self, value: str) -> str:
        v = (value or "").upper()
        if v in STATUS_COLORS:
            return STATUS_COLORS[v]
        if v in SEVERITY_COLORS:
            return SEVERITY_COLORS[v]
        return SUBTEXT_COLOR

    def update_value(self, value: str) -> None:
        color = self._resolve_color(value)
        self.configure(text=f"  {value}  ", fg_color=color)
