"""
Spotlight Walkthrough — Creates an immersive onboarding experience with
a semi-transparent overlay that highlights specific UI elements in sequence.
The spotlight "cuts out" the highlighted area while dimming everything else.
"""
import tkinter as tk
from typing import Callable, List, Optional, Tuple

from models.config import COLORS


class SpotlightStep:
    """Defines a single step in the walkthrough."""

    def __init__(
        self,
        target_widget: tk.Widget,
        title: str,
        description: str,
        position: str = "right",  # "right", "left", "top", "bottom", "auto"
        padding: int = 8,
    ):
        self.target_widget = target_widget
        self.title = title
        self.description = description
        self.position = position
        self.padding = padding


class SpotlightWalkthrough:
    """
    Creates a spotlight-based onboarding walkthrough.
    Dims the entire UI except for the highlighted element.
    """

    OVERLAY_COLOR = "#000000"
    OVERLAY_ALPHA = 0.75  # 75% opacity for the dim effect
    SPOTLIGHT_BORDER_COLOR = COLORS["accent"]
    SPOTLIGHT_BORDER_WIDTH = 3
    BUBBLE_BG = COLORS["bg_secondary"]
    BUBBLE_RADIUS = 14

    def __init__(self, root: tk.Tk):
        self.root = root
        self.steps: List[SpotlightStep] = []
        self.current_step_index = 0
        self._active = False

        # Overlay windows (we use multiple to create the "cutout" effect)
        self._overlay_windows: List[tk.Toplevel] = []
        self._border_windows: List[tk.Toplevel] = []
        self._bubble_win: Optional[tk.Toplevel] = None
        self._pulse_job: Optional[str] = None
        self._reposition_job: Optional[str] = None

        # Callbacks
        self._on_complete: Optional[Callable] = None
        self._on_skip: Optional[Callable] = None

    def add_step(
        self,
        widget: tk.Widget,
        title: str,
        description: str,
        position: str = "right",
        padding: int = 8,
    ) -> "SpotlightWalkthrough":
        """Add a step to the walkthrough. Returns self for chaining."""
        self.steps.append(SpotlightStep(widget, title, description, position, padding))
        return self

    def set_steps(self, steps: List[SpotlightStep]) -> "SpotlightWalkthrough":
        """Set all steps at once."""
        self.steps = steps
        return self

    def on_complete(self, callback: Callable) -> "SpotlightWalkthrough":
        """Set callback for when walkthrough completes."""
        self._on_complete = callback
        return self

    def on_skip(self, callback: Callable) -> "SpotlightWalkthrough":
        """Set callback for when user skips."""
        self._on_skip = callback
        return self

    def start(self):
        """Begin the walkthrough from the first step."""
        if not self.steps:
            return
        self._active = True
        self.current_step_index = 0
        self._create_overlay_windows()
        self._show_current_step()
        self._schedule_reposition()

    def _create_overlay_windows(self):
        """Create the 4 overlay windows that form the dimmed background."""
        # We create 4 rectangles: top, bottom, left, right around the spotlight
        for _ in range(4):
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            # Use a dark frame as the overlay
            win.configure(bg=self.OVERLAY_COLOR)
            # Set transparency
            win.attributes("-alpha", self.OVERLAY_ALPHA)
            # Make click-through on Windows using transparent color trick
            win.attributes("-transparentcolor", "")
            win.withdraw()
            self._overlay_windows.append(win)
            # Disable focus to prevent stealing clicks
            win.bind("<Button-1>", lambda e: None)
            win.bind("<FocusIn>", lambda e: self.root.focus_force())

        # Spotlight border - we use 4 thin windows to form a border frame
        # This avoids covering the actual content
        self._border_windows: List[tk.Toplevel] = []
        for _ in range(4):  # top, bottom, left, right borders
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            win.configure(bg=self.SPOTLIGHT_BORDER_COLOR)
            win.withdraw()
            self._border_windows.append(win)
            # Disable focus on borders too
            win.bind("<Button-1>", lambda e: None)

        # Tooltip/instruction bubble
        self._bubble_win = tk.Toplevel(self.root)
        self._bubble_win.overrideredirect(True)
        self._bubble_win.attributes("-topmost", True)
        self._bubble_win.configure(bg=self.BUBBLE_BG)
        self._bubble_win.withdraw()
        self._build_bubble_content()

    def _build_bubble_content(self):
        """Build the instruction bubble UI."""
        # Main container with padding
        container = tk.Frame(self._bubble_win, bg=self.BUBBLE_BG, padx=16, pady=12)
        container.pack(fill="both", expand=True)

        # Step indicator
        self._step_indicator = tk.Label(
            container,
            text="Step 1 of 4",
            font=("Segoe UI", 9, "bold"),
            bg=self.BUBBLE_BG,
            fg=COLORS["accent"],
        )
        self._step_indicator.pack(anchor="w")

        # Title
        self._title_label = tk.Label(
            container,
            text="Welcome",
            font=("Segoe UI", 13, "bold"),
            bg=self.BUBBLE_BG,
            fg=COLORS["text_primary"],
        )
        self._title_label.pack(anchor="w", pady=(4, 2))

        # Description
        self._desc_label = tk.Label(
            container,
            text="Description goes here",
            font=("Segoe UI", 10),
            bg=self.BUBBLE_BG,
            fg=COLORS["text_secondary"],
            wraplength=280,
            justify="left",
        )
        self._desc_label.pack(anchor="w", pady=(0, 12))

        # Progress dots
        self._progress_frame = tk.Frame(container, bg=self.BUBBLE_BG)
        self._progress_frame.pack(fill="x", pady=(0, 10))

        # Navigation buttons
        nav_frame = tk.Frame(container, bg=self.BUBBLE_BG)
        nav_frame.pack(fill="x")

        self._skip_btn = tk.Label(
            nav_frame,
            text="Skip Tutorial",
            font=("Segoe UI", 9),
            bg=self.BUBBLE_BG,
            fg=COLORS["text_secondary"],
            cursor="hand2",
        )
        self._skip_btn.pack(side="left")
        self._skip_btn.bind("<Button-1>", lambda e: self._skip())
        self._skip_btn.bind("<Enter>", lambda e: self._skip_btn.config(fg=COLORS["accent"]))
        self._skip_btn.bind("<Leave>", lambda e: self._skip_btn.config(fg=COLORS["text_secondary"]))

        self._next_btn = tk.Frame(nav_frame, bg=COLORS["accent"], cursor="hand2")
        self._next_btn.pack(side="right")

        self._next_label = tk.Label(
            self._next_btn,
            text="  Next  →  ",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["accent"],
            fg=COLORS["bg_primary"],
            padx=12,
            pady=6,
        )
        self._next_label.pack()
        self._next_btn.bind("<Button-1>", lambda e: self._next_step())
        self._next_label.bind("<Button-1>", lambda e: self._next_step())
        self._next_btn.bind("<Enter>", lambda e: self._on_next_hover(True))
        self._next_btn.bind("<Leave>", lambda e: self._on_next_hover(False))

    def _on_next_hover(self, entering: bool):
        color = COLORS["button_hover"] if entering else COLORS["accent"]
        self._next_btn.config(bg=color)
        self._next_label.config(bg=color)

    def _update_progress_dots(self):
        """Update the progress indicator dots."""
        for widget in self._progress_frame.winfo_children():
            widget.destroy()

        for i in range(len(self.steps)):
            dot_color = COLORS["accent"] if i == self.current_step_index else COLORS["bg_accent"]
            dot = tk.Canvas(
                self._progress_frame,
                width=10,
                height=10,
                bg=self.BUBBLE_BG,
                highlightthickness=0,
            )
            dot.create_oval(2, 2, 8, 8, fill=dot_color, outline="")
            dot.pack(side="left", padx=2)

    def _show_current_step(self):
        """Display the current step's spotlight and instruction."""
        if self.current_step_index >= len(self.steps):
            self._complete()
            return

        step = self.steps[self.current_step_index]

        # Update bubble content
        self._step_indicator.config(text=f"Step {self.current_step_index + 1} of {len(self.steps)}")
        self._title_label.config(text=step.title)
        self._desc_label.config(text=step.description)
        self._update_progress_dots()

        # Update button text for last step
        if self.current_step_index == len(self.steps) - 1:
            self._next_label.config(text="  Finish  ✓  ")
        else:
            self._next_label.config(text="  Next  →  ")

        # Position everything
        self._position_spotlight(step)

    def _get_widget_bounds(self, widget: tk.Widget) -> Tuple[int, int, int, int]:
        """Get absolute screen coordinates of a widget."""
        widget.update_idletasks()
        x = widget.winfo_rootx()
        y = widget.winfo_rooty()
        w = widget.winfo_width()
        h = widget.winfo_height()
        return x, y, w, h

    def _position_spotlight(self, step: SpotlightStep):
        """Position the overlay windows to create the spotlight effect."""
        try:
            if not step.target_widget.winfo_exists():
                self._next_step()
                return
        except tk.TclError:
            self._next_step()
            return

        # Get widget bounds
        wx, wy, ww, wh = self._get_widget_bounds(step.target_widget)

        # Add padding
        pad = step.padding
        spot_x = wx - pad
        spot_y = wy - pad
        spot_w = ww + 2 * pad
        spot_h = wh + 2 * pad

        # Get screen dimensions
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Position the 4 overlay rectangles around the spotlight
        # Top overlay
        self._overlay_windows[0].geometry(f"{screen_w}x{max(0, spot_y)}+0+0")
        self._overlay_windows[0].deiconify()

        # Bottom overlay
        bottom_y = spot_y + spot_h
        bottom_h = max(0, screen_h - bottom_y)
        self._overlay_windows[1].geometry(f"{screen_w}x{bottom_h}+0+{bottom_y}")
        self._overlay_windows[1].deiconify()

        # Left overlay
        left_h = spot_h
        self._overlay_windows[2].geometry(f"{max(0, spot_x)}x{left_h}+0+{spot_y}")
        self._overlay_windows[2].deiconify()

        # Right overlay
        right_x = spot_x + spot_w
        right_w = max(0, screen_w - right_x)
        self._overlay_windows[3].geometry(f"{right_w}x{spot_h}+{right_x}+{spot_y}")
        self._overlay_windows[3].deiconify()

        # Position the 4 border windows to form a frame around the spotlight
        border = self.SPOTLIGHT_BORDER_WIDTH
        
        # Top border
        self._border_windows[0].geometry(
            f"{spot_w + 2*border}x{border}+{spot_x - border}+{spot_y - border}"
        )
        self._border_windows[0].deiconify()
        
        # Bottom border
        self._border_windows[1].geometry(
            f"{spot_w + 2*border}x{border}+{spot_x - border}+{spot_y + spot_h}"
        )
        self._border_windows[1].deiconify()
        
        # Left border
        self._border_windows[2].geometry(
            f"{border}x{spot_h}+{spot_x - border}+{spot_y}"
        )
        self._border_windows[2].deiconify()
        
        # Right border
        self._border_windows[3].geometry(
            f"{border}x{spot_h}+{spot_x + spot_w}+{spot_y}"
        )
        self._border_windows[3].deiconify()

        # Lift borders above overlays
        for win in self._border_windows:
            win.lift()

        # Position bubble
        self._position_bubble(step, spot_x, spot_y, spot_w, spot_h)

        # Start pulse animation
        self._start_pulse()

    def _position_bubble(self, step: SpotlightStep, sx: int, sy: int, sw: int, sh: int):
        """Position the instruction bubble near the spotlight."""
        self._bubble_win.update_idletasks()
        bw = max(320, self._bubble_win.winfo_reqwidth())
        bh = self._bubble_win.winfo_reqheight()

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        pos = step.position
        margin = 20

        # Auto-position if needed
        if pos == "auto":
            # Prefer right, then bottom, then left, then top
            if sx + sw + margin + bw < screen_w:
                pos = "right"
            elif sy + sh + margin + bh < screen_h:
                pos = "bottom"
            elif sx - margin - bw > 0:
                pos = "left"
            else:
                pos = "top"

        if pos == "right":
            bx = sx + sw + margin
            by = sy + (sh - bh) // 2
        elif pos == "left":
            bx = sx - bw - margin
            by = sy + (sh - bh) // 2
        elif pos == "bottom":
            bx = sx + (sw - bw) // 2
            by = sy + sh + margin
        else:  # top
            bx = sx + (sw - bw) // 2
            by = sy - bh - margin

        # Clamp to screen bounds
        bx = max(10, min(bx, screen_w - bw - 10))
        by = max(10, min(by, screen_h - bh - 10))

        self._bubble_win.geometry(f"{bw}x{bh}+{bx}+{by}")
        self._bubble_win.deiconify()
        self._bubble_win.lift()

    def _start_pulse(self):
        """Animate the spotlight border with a subtle pulse."""
        if self._pulse_job:
            self.root.after_cancel(self._pulse_job)
        self._pulse_phase = 0
        self._animate_pulse()

    def _animate_pulse(self):
        """Pulse animation for the spotlight border."""
        if not self._active:
            return

        # Alternate between accent and slightly lighter
        self._pulse_phase = (self._pulse_phase + 1) % 20
        if self._pulse_phase < 10:
            color = COLORS["accent"]
        else:
            color = COLORS["button_hover"]

        # Update all 4 border windows
        for win in self._border_windows:
            try:
                if win and win.winfo_exists():
                    win.configure(bg=color)
            except tk.TclError:
                pass

        self._pulse_job = self.root.after(100, self._animate_pulse)

    def _schedule_reposition(self):
        """Periodically reposition spotlight in case window moves."""
        if not self._active:
            return

        if self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]
            try:
                if step.target_widget.winfo_exists():
                    self._position_spotlight(step)
            except tk.TclError:
                pass

        self._reposition_job = self.root.after(500, self._schedule_reposition)

    def _next_step(self):
        """Advance to the next step."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self._complete()
        else:
            self._show_current_step()

    def _skip(self):
        """Skip the entire walkthrough."""
        self._cleanup()
        if self._on_skip:
            self._on_skip()

    def _complete(self):
        """Complete the walkthrough."""
        self._cleanup()
        if self._on_complete:
            self._on_complete()

    def _cleanup(self):
        """Clean up all overlay windows."""
        self._active = False

        if self._pulse_job:
            self.root.after_cancel(self._pulse_job)
            self._pulse_job = None

        if self._reposition_job:
            self.root.after_cancel(self._reposition_job)
            self._reposition_job = None

        for win in self._overlay_windows:
            try:
                if win and win.winfo_exists():
                    win.destroy()
            except tk.TclError:
                pass
        self._overlay_windows.clear()

        # Clean up border windows
        for win in getattr(self, '_border_windows', []):
            try:
                if win and win.winfo_exists():
                    win.destroy()
            except tk.TclError:
                pass
        self._border_windows = []

        # Clean up bubble window
        if self._bubble_win:
            try:
                if self._bubble_win.winfo_exists():
                    self._bubble_win.destroy()
            except tk.TclError:
                pass
            self._bubble_win = None

    def is_active(self) -> bool:
        """Check if walkthrough is currently running."""
        return self._active

    def stop(self):
        """Force stop the walkthrough."""
        self._cleanup()
