"""
Shared helper for creating themed labels.
"""
import tkinter as tk

from models.config import COLORS


def _create_label(parent, text, font_size=10, bold=False, color="text_secondary"):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        bg=parent.cget("bg"), fg=COLORS[color],
    )
