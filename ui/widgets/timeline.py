"""
FinGuard UI – TimelineWidget
Vertical security audit timeline built with CustomTkinter.
"""
import customtkinter as ctk
from typing import List, Dict, Any
from ui.widgets.theme import (
    CARD_COLOR, BG_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, SUCCESS_COLOR, FONT_FAMILY
)


class TimelineWidget(ctk.CTkScrollableFrame):
    """
    Renders a vertical event timeline with dot-node markers,
    timestamps, and event title text.

    Usage:
        widget.set_events([{"time": "...", "title": "...", "details": "..."}, ...])
    """

    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color="transparent",
            scrollbar_fg_color="#0F172A",
            scrollbar_button_color=PRIMARY_COLOR,
            **kwargs
        )
        self._events: List[Dict[str, Any]] = []

    def set_events(self, events: List[Dict[str, Any]]) -> None:
        """Clear and re-render all timeline events."""
        # Clear old widgets
        for w in self.winfo_children():
            w.destroy()
        self._events = events
        self._render()

    def _render(self) -> None:
        if not self._events:
            ctk.CTkLabel(
                self,
                text="No timeline events recorded.",
                text_color=SUBTEXT_COLOR,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            ).pack(pady=20, anchor="w", padx=16)
            return

        for idx, event in enumerate(self._events):
            is_last = (idx == len(self._events) - 1)
            self._render_event(event, is_last)

    def _render_event(self, event: Dict[str, Any], is_last: bool) -> None:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=2)

        # Left: vertical line + dot
        left_col = ctk.CTkFrame(row, fg_color="transparent", width=32)
        left_col.pack(side="left", fill="y", padx=(8, 0))
        left_col.pack_propagate(False)

        # Dot
        dot = ctk.CTkFrame(
            left_col,
            width=12, height=12,
            fg_color=PRIMARY_COLOR,
            corner_radius=6,
        )
        dot.place(relx=0.5, y=10, anchor="center")

        # Line below (except for last event)
        if not is_last:
            line = ctk.CTkFrame(
                left_col,
                width=2, height=40,
                fg_color="#334155",
                corner_radius=0,
            )
            line.place(relx=0.5, y=22, anchor="n")

        # Right: content
        right_col = ctk.CTkFrame(row, fg_color=CARD_COLOR, corner_radius=8)
        right_col.pack(side="left", fill="x", expand=True, padx=(8, 8), pady=4)

        # Time
        time_str = event.get("time", "")
        if time_str:
            ctk.CTkLabel(
                right_col,
                text=time_str,
                font=ctk.CTkFont(family=FONT_FAMILY, size=9),
                text_color=SUBTEXT_COLOR,
                anchor="w"
            ).pack(anchor="w", padx=10, pady=(6, 0))

        # Title
        title_str = event.get("title", "")
        if title_str:
            ctk.CTkLabel(
                right_col,
                text=title_str,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11),
                text_color=TEXT_COLOR,
                anchor="w",
                wraplength=280,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(2, 0))

        # Details
        details_str = event.get("details", "")
        if details_str:
            ctk.CTkLabel(
                right_col,
                text=details_str,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=SUBTEXT_COLOR,
                anchor="w",
                wraplength=280,
                justify="left"
            ).pack(anchor="w", padx=10, pady=(2, 6))
        else:
            ctk.CTkFrame(right_col, fg_color="transparent", height=6).pack()
