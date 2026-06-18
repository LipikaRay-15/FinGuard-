import tkinter as tk
from tkinter import ttk
from ui.widgets.theme import CARD_COLOR, TEXT_COLOR, SUBTEXT_COLOR, FONT_BODY

class SearchBar(ttk.Frame):
    """
    A premium search bar container with input placeholder support,
    a search button, and a clear button.
    """
    def __init__(self, parent, placeholder: str = "Search...", search_callback=None, **kwargs) -> None:
        super().__init__(parent, style="TFrame", **kwargs)
        self.placeholder = placeholder
        self.search_callback = search_callback

        # Styled wrapper frame to resemble a rounded, padded entry box
        self.input_frame = tk.Frame(self, bg=CARD_COLOR, padx=8, pady=4, bd=1, relief="flat")
        self.input_frame.pack(fill="x", expand=True, side="left")

        # Search Icon label
        self.icon_lbl = tk.Label(self.input_frame, text="🔍", bg=CARD_COLOR, fg=SUBTEXT_COLOR)
        self.icon_lbl.pack(side="left", padx=(4, 8))

        # Text input entry
        self.entry = tk.Entry(
            self.input_frame,
            bg=CARD_COLOR,
            fg=SUBTEXT_COLOR,
            bd=0,
            insertbackground=TEXT_COLOR,
            font=FONT_BODY,
            highlightthickness=0
        )
        self.entry.insert(0, self.placeholder)
        self.entry.pack(fill="x", expand=True, side="left")
        
        # Clear button (hidden by default)
        self.clear_btn = tk.Button(
            self.input_frame,
            text="✕",
            bg=CARD_COLOR,
            fg=SUBTEXT_COLOR,
            bd=0,
            activebackground=CARD_COLOR,
            activeforeground=TEXT_COLOR,
            cursor="hand2",
            command=self.clear_search,
            font=("Segoe UI", 9)
        )
        # Show/Hide clear button dynamically on keystroke
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Return>", self._on_submit)

        # Submit button
        self.submit_btn = ttk.Button(
            self,
            text="Search",
            command=self._on_submit,
            style="TButton"
        )
        self.submit_btn.pack(side="left", padx=(10, 0))

    def _on_key_release(self, event=None) -> None:
        val = self.entry.get()
        if val and val != self.placeholder:
            self.clear_btn.pack(side="right", padx=(4, 4))
        else:
            self.clear_btn.pack_forget()

    def _on_focus_in(self, event) -> None:
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end")
            self.entry.configure(fg=TEXT_COLOR)

    def _on_focus_out(self, event) -> None:
        if not self.entry.get():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=SUBTEXT_COLOR)
            self.clear_btn.pack_forget()

    def _on_submit(self, event=None) -> None:
        if self.search_callback:
            query = self.get_query()
            self.search_callback(query)

    def clear_search(self) -> None:
        self.entry.delete(0, "end")
        self.clear_btn.pack_forget()
        if self.entry != self.focus_get():
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=SUBTEXT_COLOR)
        if self.search_callback:
            self.search_callback("")

    def get_query(self) -> str:
        val = self.entry.get()
        if val == self.placeholder:
            return ""
        return val.strip()
