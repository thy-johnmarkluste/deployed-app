"""
Custom Tkinter widgets — ModernEntry, ModernButton, RoundedFrame,
LiveMetricCard, LiveProgressBar, SparklineCanvas.
"""
import tkinter as tk
from tkinter import ttk

from models.config import COLORS


class ModernEntry(ttk.Entry):
    """Custom modern entry widget with styling."""

    def __init__(self, parent, **kwargs):
        style = ttk.Style()
        style.configure(
            "Modern.TEntry",
            fieldbackground=COLORS["entry_bg"],
            background=COLORS["entry_bg"],
            foreground=COLORS["text_primary"],
            borderwidth=1,
            focuscolor=COLORS["accent"],
        )
        super().__init__(parent, style="Modern.TEntry", **kwargs)


class ModernButton(tk.Canvas):
    """Custom modern button with rounded corners and border."""

    def __init__(
        self,
        parent,
        text="",
        command=None,
        bg_color=COLORS["accent"],
        hover_color=COLORS["button_hover"],
        text_color=COLORS["text_primary"],
        border_color=None,
        **kwargs,
    ):
        super().__init__(parent, bg=parent.cget("bg"), highlightthickness=0, **kwargs)

        self.command = command
        self.text = text
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_color = border_color if border_color else bg_color
        self._draw_button(bg_color)

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw_button(self, color):
        """Draw button with rounded corners and border."""
        self.delete("all")
        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()
        border_width = 2

        self.create_arc(0, 0, border_width * 2, border_width * 2, start=90, extent=90, fill=self.border_color, outline=self.border_color)
        self.create_arc(width - border_width * 2, 0, width, border_width * 2, start=0, extent=90, fill=self.border_color, outline=self.border_color)
        self.create_arc(0, height - border_width * 2, border_width * 2, height, start=180, extent=90, fill=self.border_color, outline=self.border_color)
        self.create_arc(width - border_width * 2, height - border_width * 2, width, height, start=270, extent=90, fill=self.border_color, outline=self.border_color)
        self.create_rectangle(border_width, 0, width - border_width, height, fill=self.border_color, outline=self.border_color)
        self.create_rectangle(0, border_width, width, height - border_width, fill=self.border_color, outline=self.border_color)

        inner_x = border_width
        inner_y = border_width
        inner_width = width - border_width * 2
        inner_height = height - border_width * 2

        self.create_arc(inner_x, inner_y, inner_x + 16, inner_y + 16, start=90, extent=90, fill=color, outline=color)
        self.create_arc(inner_x + inner_width - 16, inner_y, inner_x + inner_width, inner_y + 16, start=0, extent=90, fill=color, outline=color)
        self.create_arc(inner_x, inner_y + inner_height - 16, inner_x + 16, inner_y + inner_height, start=180, extent=90, fill=color, outline=color)
        self.create_arc(inner_x + inner_width - 16, inner_y + inner_height - 16, inner_x + inner_width, inner_y + inner_height, start=270, extent=90, fill=color, outline=color)
        self.create_rectangle(inner_x + 8, inner_y, inner_x + inner_width - 8, inner_y + inner_height, fill=color, outline=color)
        self.create_rectangle(inner_x, inner_y + 8, inner_x + inner_width, inner_y + inner_height - 8, fill=color, outline=color)

        self.create_text(width // 2, height // 2, text=self.text, fill=self.text_color, font=("Segoe UI", 10, "bold"))

    def _on_enter(self, event):
        self._draw_button(self.hover_color)

    def _on_leave(self, event):
        self._draw_button(self.bg_color)

    def _on_click(self, event):
        if self.command:
            self.command()

    def config(self, **kwargs):
        if "bg" in kwargs:
            self.bg_color = kwargs.pop("bg")
        super().config(**kwargs)


class RoundedFrame(tk.Frame):
    """Canvas-backed frame that draws rounded borders."""

    def __init__(self, parent, bg_color, radius=12, padding=(0, 0)):
        super().__init__(parent, bg=parent.cget("bg"))
        self.radius = radius
        self.bg_color = bg_color
        self.padding = padding

        self.canvas = tk.Canvas(self, bg=self.cget("bg"), bd=0, highlightthickness=0, relief="flat")
        self.canvas.pack(fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg_color)
        self.inner_window = self.canvas.create_window(
            radius + padding[0], radius + padding[1], anchor="nw", window=self.inner
        )

        self.canvas.bind("<Configure>", self._on_configure)

    def _draw_round_rect(self, width, height, radius):
        points = [
            radius, 0,
            width - radius, 0,
            width, 0,
            width, radius,
            width, height - radius,
            width, height,
            width - radius, height,
            radius, height,
            0, height,
            0, height - radius,
            0, radius,
            0, 0,
            radius, 0,
        ]
        self.canvas.create_polygon(points, smooth=True, fill=self.bg_color, outline="", tags="round_rect")

    def _on_configure(self, event):
        width, height = event.width, event.height
        radius = min(self.radius, width / 2, height / 2)
        self.canvas.delete("round_rect")
        self._draw_round_rect(width, height, radius)

        inner_x = radius + self.padding[0]
        inner_y = radius + self.padding[1]
        inner_width = max(0, width - 2 * (radius + self.padding[0]))
        inner_height = max(0, height - 2 * (radius + self.padding[1]))

        self.canvas.coords(self.inner_window, inner_x, inner_y)
        self.canvas.itemconfig(self.inner_window, width=inner_width, height=inner_height)


class LiveMetricCard(tk.Frame):
    """Animated metric card with real-time value updates and trend sparkline."""

    def __init__(self, parent, title="", unit="", icon="📊",
                 bg_color=None, accent_color=None, info_text=""):
        bg = bg_color or COLORS["bg_secondary"]
        super().__init__(parent, bg=bg, padx=14, pady=10,
                         highlightbackground=bg,
                         highlightthickness=0)

        self._bg = bg
        self._accent = accent_color or COLORS["accent"]
        self._title = title
        self._info_text = info_text
        self.current_value = 0.0
        self.target_value = 0.0
        self.unit = unit
        self._animating = False


        header = tk.Frame(self, bg=bg)
        header.pack(fill="x")

        tk.Label(
            header, text=icon, font=("Segoe UI Emoji", 16),
            bg=bg, fg=self._accent,
        ).pack(side="left", padx=(0, 6))

        tk.Label(
            header, text=title,
            font=("Segoe UI", 9, "bold"),
            bg=bg, fg=COLORS["text_secondary"],
        ).pack(side="left", anchor="w")

        if info_text:
            info_btn = tk.Label(
                header, text="ℹ", font=("Segoe UI", 11, "bold"),
                bg=bg, fg=COLORS["accent"], cursor="hand2",
            )
            info_btn.pack(side="right", padx=(4, 0))
            info_btn.bind("<Button-1>", lambda e: self._show_info())


        self.value_label = tk.Label(
            self, text="0",
            font=("Segoe UI", 28, "bold"),
            bg=bg, fg=COLORS["text_primary"],
        )
        self.value_label.pack(pady=(4, 0))


        bottom = tk.Frame(self, bg=bg)
        bottom.pack(fill="x")

        self.unit_label = tk.Label(
            bottom, text=unit,
            font=("Segoe UI", 8),
            bg=bg, fg=COLORS["text_secondary"],
        )
        self.unit_label.pack(side="left")

        self.change_label = tk.Label(
            bottom, text="",
            font=("Segoe UI", 8, "bold"),
            bg=bg, fg=COLORS["text_secondary"],
        )
        self.change_label.pack(side="right")


        self.sparkline = SparklineCanvas(self, width=120, height=26, bg_color=bg)
        self.sparkline.pack(fill="x", pady=(4, 0))

    def update_value(self, new_value, animate=True):
        """Set a new target value. Optionally animate the transition."""
        old_target = self.target_value
        self.target_value = float(new_value)
        self.sparkline.add_value(self.target_value)


        diff = self.target_value - old_target
        if abs(diff) > 0.01:
            sign = "▲" if diff > 0 else "▼"
            color = COLORS["success"] if diff > 0 else COLORS["error"]
            self.change_label.config(text=f"{sign} {abs(diff):.0f}", fg=color)
            self._pulse()
        else:
            self.change_label.config(text="—", fg=COLORS["text_secondary"])

        if animate and not self._animating:
            self._animating = True
            self._animate()
        elif not animate:
            self.current_value = self.target_value
            self._render_value()

    def _animate(self):
        """Smoothly animate current_value → target_value."""
        diff = self.target_value - self.current_value
        if abs(diff) < 0.5:
            self.current_value = self.target_value
            self._render_value()
            self._animating = False
            return
        self.current_value += diff * 0.18
        self._render_value()
        self.after(30, self._animate)

    def _render_value(self):
        val = self.current_value
        if val >= 10_000:
            txt = f"{val / 1000:.1f}K"
        elif val >= 1000:
            txt = f"{val / 1000:.1f}K"
        elif val == int(val):
            txt = str(int(val))
        else:
            txt = f"{val:.1f}"
        self.value_label.config(text=txt)

    def _pulse(self):
        """Quick flash when value changes."""
        orig = self._bg
        self.config(bg=COLORS["bg_accent"])
        self.value_label.config(bg=COLORS["bg_accent"])
        self.after(180, lambda: self._restore(orig))

    def _restore(self, color):
        self.config(bg=color)
        self.value_label.config(bg=color)

    def _show_info(self):
        """Show an info dialog describing this metric."""
        from tkinter import messagebox
        messagebox.showinfo(self._title, self._info_text)


class SparklineCanvas(tk.Canvas):
    """Miniature line chart showing value history."""

    def __init__(self, parent, width=120, height=26, bg_color=None, max_points=20):
        bg = bg_color or COLORS["bg_secondary"]
        super().__init__(parent, width=width, height=height,
                         bg=bg, highlightthickness=0)
        self.history = []
        self.max_points = max_points
        self._line_color = "#d4a843"

    def add_value(self, value):
        self.history.append(value)
        if len(self.history) > self.max_points:
            self.history.pop(0)
        self._draw()

    def _draw(self):
        self.delete("all")
        if len(self.history) < 2:
            return
        w = self.winfo_width() or 120
        h = self.winfo_height() or 26
        pad = 2

        max_v = max(self.history)
        min_v = min(self.history)
        rng = max_v - min_v or 1

        points = []
        n = len(self.history)
        for i, v in enumerate(self.history):
            x = pad + (i / (n - 1)) * (w - 2 * pad)
            y = pad + (1 - (v - min_v) / rng) * (h - 2 * pad)
            points.extend([x, y])

        if len(points) >= 4:
            self.create_line(points, fill=self._line_color, width=1.5, smooth=True)


class LiveProgressBar(tk.Frame):
    """Animated progress bar with percentage label."""

    def __init__(self, parent, title="", max_value=100,
                 bar_color=None, height=16):
        bg = parent.cget("bg")
        super().__init__(parent, bg=bg)

        self.max_value = max_value
        self._target_pct = 0.0
        self._current_pct = 0.0
        self._bar_color = bar_color or COLORS["accent"]
        self._animating = False


        top = tk.Frame(self, bg=bg)
        top.pack(fill="x")

        self.title_label = tk.Label(
            top, text=title,
            font=("Segoe UI", 9, "bold"),
            bg=bg, fg=COLORS["text_primary"],
        )
        self.title_label.pack(side="left")

        self.pct_label = tk.Label(
            top, text="0 %",
            font=("Segoe UI", 9),
            bg=bg, fg=COLORS["text_secondary"],
        )
        self.pct_label.pack(side="right")


        track = tk.Frame(self, bg=COLORS["bg_accent"], height=height)
        track.pack(fill="x", pady=(3, 0))
        track.pack_propagate(False)

        self.fill = tk.Frame(track, bg=self._bar_color, height=height)
        self.fill.place(x=0, y=0, relwidth=0, relheight=1)

    def update_value(self, value, animate=True):
        pct = max(0, min(value / self.max_value, 1.0)) * 100
        self._target_pct = pct


        if pct < 50:
            color = COLORS["success"]
        elif pct < 80:
            color = COLORS["warning"]
        else:
            color = COLORS["error"]
        self.fill.config(bg=color)

        if animate and not self._animating:
            self._animating = True
            self._animate()
        elif not animate:
            self._current_pct = pct
            self._apply()

    def _animate(self):
        diff = self._target_pct - self._current_pct
        if abs(diff) < 0.5:
            self._current_pct = self._target_pct
            self._apply()
            self._animating = False
            return
        self._current_pct += diff * 0.2
        self._apply()
        self.after(30, self._animate)

    def _apply(self):
        self.fill.place(relwidth=self._current_pct / 100)
        self.pct_label.config(text=f"{self._current_pct:.0f} %")
