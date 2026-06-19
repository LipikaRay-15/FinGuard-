"""
FinGuard UI – CardWidget
Premium metric card using CustomTkinter.
"""
import customtkinter as ctk
from ui.widgets.theme import (
    BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR,
    PRIMARY_COLOR, FONT_FAMILY
)


class CardWidget(ctk.CTkFrame):
    """
    A premium dark card displaying a metric title, large value, and subtitle.
    Optional accent color on the left edge strip.
    Public: update_value(val: str)
    """
    def __init__(self, parent, title: str, value: str, subtitle: str = "",
                 trend_color: str = PRIMARY_COLOR, **kwargs):
        super().__init__(
            parent,
            fg_color=CARD_COLOR,
            corner_radius=12,
            border_width=1,
            border_color="#2D3748",
            **kwargs
        )

        self.trend_color = trend_color
        self.grid_propagate(True)

        # Left accent strip
        self._accent = ctk.CTkFrame(
            self, fg_color=trend_color,
            width=4, corner_radius=0
        )
        self._accent.pack(side="left", fill="y", padx=(0, 12))
        self._accent.pack_propagate(False)

        # Content area
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=(0, 16), pady=16)

        # Title
        self._title_lbl = ctk.CTkLabel(
            content,
            text=title.upper(),
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
            text_color=SUBTEXT_COLOR,
            anchor="w"
        )
        self._title_lbl.pack(anchor="w", pady=(0, 6))

        # Value
        self._value_lbl = ctk.CTkLabel(
            content,
            text=value,
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_COLOR,
            anchor="w"
        )
        self._value_lbl.pack(anchor="w")

        # Subtitle
        if subtitle:
            self._sub_lbl = ctk.CTkLabel(
                content,
                text=subtitle,
                font=ctk.CTkFont(family=FONT_FAMILY, size=10),
                text_color=SUBTEXT_COLOR,
                anchor="w"
            )
            self._sub_lbl.pack(anchor="w", pady=(4, 0))

        # Hover effect
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.configure(border_color=self.trend_color)

    def _on_leave(self, e):
        self.configure(border_color="#2D3748")

    def update_value(self, val: str) -> None:
        """Update the displayed metric value."""
        self._value_lbl.configure(text=val)

    def update_accent(self, color: str) -> None:
        """Update accent strip color."""
        self.trend_color = color
        self._accent.configure(fg_color=color)
