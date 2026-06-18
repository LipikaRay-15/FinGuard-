import tkinter as tk
from tkinter import ttk
from ui.widgets.theme import (
    SUCCESS_COLOR,
    WARNING_COLOR,
    DANGER_COLOR,
    SUBTEXT_COLOR,
    FONT_CAPTION
)

class StatusBadge(tk.Frame):
    """
    A premium flat badge that highlights system status fields with specific color palettes.
    Uses tk.Frame/tk.Label directly for fine-grained background color padding settings.
    """
    def __init__(self, parent, text: str, **kwargs) -> None:
        # Resolve status color
        self.text_val = str(text).strip().upper()
        
        bg_color, fg_color = self._get_status_colors(self.text_val)
        
        super().__init__(parent, bg=bg_color, padx=8, pady=4, bd=0, highlightthickness=0, **kwargs)
        
        self.label = tk.Label(
            self,
            text=self.text_val,
            bg=bg_color,
            fg=fg_color,
            font=FONT_CAPTION,
            bd=0,
            highlightthickness=0
        )
        self.label.pack()

    def _get_status_colors(self, status: str) -> tuple:
        """
        Maps a state/status flag to a matching (Background, Foreground) color pair.
        """
        # Default colors
        bg = "#334155" # Slate 700
        fg = "#F8FAFC" # White
        
        # Success Green indicators
        if status in ("ACTIVE", "RESOLVED", "APPROVED", "LOW", "SUCCESS", "TRUE"):
            bg = "#065F46" # Deep Green
            fg = "#A7F3D0" # Light Green
            
        # Warning Yellow-Orange indicators
        elif status in ("SUSPENDED", "UNDER_REVIEW", "ESCALATED", "MEDIUM", "WARNING", "FLAGGED"):
            bg = "#78350F" # Deep Amber
            fg = "#FDE68A" # Light Amber
            
        # Danger Red indicators
        elif status in ("BLOCKED", "CRITICAL", "DANGER", "HIGH", "FAILED", "DECLINED"):
            bg = "#7F1D1D" # Deep Red
            fg = "#FECACA" # Light Red
            
        # Muted indicators
        elif status in ("INACTIVE", "CLOSED", "FALSE_POSITIVE", "OPEN", "SYSTEM", "NONE"):
            bg = "#1E293B" # Dark Slate
            fg = "#94A3B8" # Soft Gray
            
        return bg, fg

    def update_status(self, text: str) -> None:
        self.text_val = str(text).strip().upper()
        bg_color, fg_color = self._get_status_colors(self.text_val)
        self.configure(bg=bg_color)
        self.label.configure(text=self.text_val, bg=bg_color, fg=fg_color)
