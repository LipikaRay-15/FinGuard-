import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any
from ui.widgets.theme import BG_COLOR, CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR, PRIMARY_COLOR, FONT_CAPTION, FONT_BODY, FONT_SUBHEADER

class TimelineWidget(ttk.Frame):
    """
    A premium timeline list layout. Draws vertical connected line bars
    and status circles to represent analyst events chronologically.
    """
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, style="TFrame", **kwargs)

        # Scrollable container
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg=BG_COLOR)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas_frame = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Bind canvas size configuration to width resizing
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _on_canvas_configure(self, event) -> None:
        # Match scrollable frame width to canvas width
        self.canvas.itemconfig(self.canvas_frame, width=event.width)

    def set_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Populates the timeline.
        Expected event format: {"time": "10:15 AM", "title": "Case Closed", "details": "Analyst Bob, score: 75"}
        """
        # Clear existing items
        for child in self.scrollable_frame.winfo_children():
            child.destroy()

        if not events:
            empty_lbl = ttk.Label(self.scrollable_frame, text="No timeline events recorded.", style="TLabel")
            empty_lbl.pack(pady=20, padx=20)
            return

        for idx, event in enumerate(events):
            item_frame = tk.Frame(self.scrollable_frame, bg=BG_COLOR)
            item_frame.pack(fill="x", expand=True)

            # Left Timeline line-dot canvas
            indicator_canvas = tk.Canvas(item_frame, width=30, height=70, bg=BG_COLOR, highlightthickness=0, bd=0)
            indicator_canvas.pack(side="left", fill="y")

            # Draw lines and circles
            # Draw line connecting events (except last item)
            indicator_canvas.create_line(15, 0 if idx > 0 else 20, 15, 70, fill="#334155", width=2)
            
            # Circle marker
            indicator_canvas.create_oval(10, 15, 20, 25, fill=PRIMARY_COLOR, outline=BG_COLOR, width=2)

            # Right details container
            text_frame = tk.Frame(item_frame, bg=BG_COLOR, pady=10)
            text_frame.pack(side="left", fill="both", expand=True, padx=(10, 20))

            time_lbl = tk.Label(
                text_frame,
                text=event.get("time", ""),
                bg=BG_COLOR,
                fg=SUBTEXT_COLOR,
                font=FONT_CAPTION
            )
            time_lbl.pack(anchor="w")

            title_lbl = tk.Label(
                text_frame,
                text=event.get("title", ""),
                bg=BG_COLOR,
                fg=TEXT_COLOR,
                font=FONT_SUBHEADER
            )
            title_lbl.pack(anchor="w")

            if event.get("details"):
                details_lbl = tk.Label(
                    text_frame,
                    text=event.get("details", ""),
                    bg=BG_COLOR,
                    fg=SUBTEXT_COLOR,
                    font=FONT_CAPTION,
                    wraplength=400,
                    justify="left"
                )
                details_lbl.pack(anchor="w")
