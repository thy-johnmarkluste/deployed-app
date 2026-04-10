"""
Server Credentials Setup GUI
Professional interface built with CustomTkinter.
Features a numbered step indicator, real-time field validation,
animated gradient-sweep border, and a two-stage connect flow.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
import socket
import threading
import math
from pathlib import Path

from models.config import load_runtime_credentials, save_runtime_credentials
from models.paths import get_resource_path

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Paths & constants ────────────────────────────────────────────────────────
LOGO_PATH = get_resource_path("assets/logo.png")

# CustomTkinter global appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Palette
C = {
    "bg":          "#0f0f0f",
    "card":        "#1a1a2e",
    "card_inner":  "#16213e",
    "accent":      "#d4a843",
    "accent_hover":"#e0b84e",
    "danger":      "#e94560",
    "success":     "#4ecca3",
    "cyan":        "#58d4c8",
    "cyan_dim":    "#1a4a45",
    "gold":        "#d4a843",
    "gold_dim":    "#6b5520",
    "muted":       "#555555",
    "text":        "#e6edf3",
    "text_dim":    "#8b949e",
}

FORM_CONTAINER_WIDTH = 560
FIELD_WIDTH = 420


# ── Core helpers ─────────────────────────────────────────────────────────────

def _make_icon(window):
    try:
        if HAS_PIL and os.path.exists(LOGO_PATH):
            img = Image.open(LOGO_PATH).resize((32, 32), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            window.iconphoto(True, photo)
            window._icon_ref = photo
    except Exception:
        pass


def read_current_config():
    try:
        return load_runtime_credentials()
    except Exception as e:
        print(f"Warning: Could not read existing config: {e}")
        return {"TARGET_HOSTNAME": "", "TARGET_USERNAME": "", "TARGET_PASSWORD": ""}


def update_domain_connector(hostname, username, password):
    return save_runtime_credentials(hostname, username, password)


def test_connection(hostname, username, password):
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=hostname, username=username,
                       password=password, timeout=10)
        client.close()
        return True, "Connection successful!"
    except ImportError:
        try:
            s = socket.create_connection((hostname, 22), timeout=5)
            s.close()
            return True, "Connection successful! (SSH auth will be tested in main app)"
        except Exception as e:
            return False, f"Connection failed: {e}"
    except Exception as e:
        return False, f"Connection failed: {e}"


# ── Color interpolation ─────────────────────────────────────────────────────

def _lerp_color(c1, c2, t):
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Animated gradient-sweep border ──────────────────────────────────────────

class GradientSweepBorder(tk.Frame):
    """Animated gradient sweep that travels around the card border.

    Four side strips draw small rects whose color depends on proximity
    to a sweeping "hotspot" that moves clockwise, with a soft bloom.
    The inner content frame sits on top via place().
    """

    STRIPS = 24
    GLOW_PAD = 8
    BORDER_W = 2
    ANIM_MS = 30
    SPEED = 0.008

    # ─────────────────────────────────────────────────────────────────────────────
    # Drawing Helper Methods
    # ─────────────────────────────────────────────────────────────────────────────

    def _get_side_config(self, w, h):
        """Calculate side configurations for the border animation."""
        pad = self.GLOW_PAD
        ix1, iy1, ix2, iy2 = pad, pad, w - pad, h - pad
        
        return [
            (ix1, iy1 - self.BORDER_W, ix2, iy1, True,  0.0,  0.25),
            (ix2, iy1, ix2 + self.BORDER_W, iy2, False, 0.25, 0.5),
            (ix2, iy2, ix1, iy2 + self.BORDER_W, True,  0.5,  0.75),
            (ix1 - self.BORDER_W, iy2, ix1, iy1, False, 0.75, 1.0),
        ], (ix1, iy1, ix2, iy2)

    def _calculate_intensity(self, frac):
        """Calculate glow intensity based on phase fraction."""
        dist = min(abs(frac - self._phase),
                   1.0 - abs(frac - self._phase))
        trail = 0.30
        if dist < trail:
            return max(0.0, (1.0 - dist / trail) ** 1.5)
        return 0.0

    def _draw_horizontal_strip(self, c, sx1, sy1, sx2, sy2, i, n, fs, fe, bright, dim, bg, pad):
        """Draw a horizontal strip segment."""
        dx = abs(sx2 - sx1) / n
        xm = min(sx1, sx2)
        if sx2 > sx1:
            rx1 = xm + dx * i
            rx2 = rx1 + dx
        else:
            rx2 = max(sx1, sx2) - dx * i
            rx1 = rx2 - dx
        
        frac = fs + (fe - fs) * ((i + 0.5) / n)
        intensity = self._calculate_intensity(frac)
        final = 0.08 + 0.92 * intensity
        col = _lerp_color(dim, bright, final)
        
        c.create_rectangle(rx1, sy1, rx2, sy2,
                           fill=col, outline=col, tags="g")
        
        # Draw bloom effect
        if intensity > 0.15:
            bl = _lerp_color(bg, bright, intensity * 0.3)
            bh = int(3 * intensity) + 1
            if sy1 < pad:
                c.create_rectangle(rx1, sy1 - bh, rx2, sy1,
                                  fill=bl, outline=bl, tags="g")
            else:
                c.create_rectangle(rx1, sy2, rx2, sy2 + bh,
                                  fill=bl, outline=bl, tags="g")

    def _draw_vertical_strip(self, c, sx1, sy1, sx2, sy2, i, n, fs, fe, bright, dim, bg, pad):
        """Draw a vertical strip segment."""
        dy = abs(sy2 - sy1) / n
        ym = min(sy1, sy2)
        if sy2 > sy1:
            ry1 = ym + dy * i
            ry2 = ry1 + dy
        else:
            ry2 = max(sy1, sy2) - dy * i
            ry1 = ry2 - dy
        
        frac = fs + (fe - fs) * ((i + 0.5) / n)
        intensity = self._calculate_intensity(frac)
        final = 0.08 + 0.92 * intensity
        col = _lerp_color(dim, bright, final)
        
        c.create_rectangle(sx1, ry1, sx2, ry2,
                           fill=col, outline=col, tags="g")
        
        # Draw bloom effect
        if intensity > 0.15:
            bl = _lerp_color(bg, bright, intensity * 0.3)
            bw_ = int(3 * intensity) + 1
            if sx1 < pad:
                c.create_rectangle(sx1 - bw_, ry1, sx1, ry2,
                                  fill=bl, outline=bl, tags="g")
            else:
                c.create_rectangle(sx2, ry1, sx2 + bw_, ry2,
                                  fill=bl, outline=bl, tags="g")

    def __init__(self, parent, glow_color=C["gold"],
                 glow_dim=C["gold_dim"], **kwargs):
        bg = kwargs.pop("bg", C["bg"])
        super().__init__(parent, bg=bg, **kwargs)

        self.glow_color = glow_color
        self.glow_dim = glow_dim
        self._bg = bg
        self._phase = 0.0
        self._animating = True

        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self._canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        pad = self.GLOW_PAD
        self._pad = pad
        self._inner = ctk.CTkFrame(self, fg_color=C["card"],
                                   corner_radius=8)
        self._inner.pack_propagate(False)   # keep configured size, don't shrink-wrap
        self._inner.place(x=pad, y=pad)
        self._inner.lift()

        self.bind("<Configure>", self._on_resize)
        self._canvas.bind("<Configure>", lambda e: self._draw())
        self.after(100, self._tick)

    def _on_resize(self, event=None):
        """Manually resize the CTkFrame inner panel (CTk forbids width/height in place)."""
        w = self.winfo_width()
        h = self.winfo_height()
        pad = self._pad
        iw = max(1, w - pad * 2)
        ih = max(1, h - pad * 2)
        self._inner.configure(width=iw, height=ih)
        self._inner.place(x=pad, y=pad)

    @property
    def inner(self):
        return self._inner

    def _tick(self):
        if not self._animating:
            return
        self._phase = (self._phase + self.SPEED) % 1.0
        self._draw()
        self.after(self.ANIM_MS, self._tick)

    def _draw(self):
        c = self._canvas
        c.delete("g")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 30 or h < 30:
            return

        pad = self.GLOW_PAD
        n = self.STRIPS
        bg = self._bg
        bright = self.glow_color
        dim = self.glow_dim

        sides, (ix1, iy1, ix2, iy2) = self._get_side_config(w, h)

        for sx1, sy1, sx2, sy2, horiz, fs, fe in sides:
            for i in range(n):
                if horiz:
                    self._draw_horizontal_strip(c, sx1, sy1, sx2, sy2, i, n, fs, fe, bright, dim, bg, pad)
                else:
                    self._draw_vertical_strip(c, sx1, sy1, sx2, sy2, i, n, fs, fe, bright, dim, bg, pad)

        c.create_rectangle(ix1, iy1, ix2, iy2,
                           fill=C["card"], outline=C["card"], tags="g")

    def set_glow(self, color, dim):
        self.glow_color = color
        self.glow_dim = dim

    def stop_animation(self):
        self._animating = False

    def start_animation(self):
        if not self._animating:
            self._animating = True
            self._tick()


# ── Step Indicator ───────────────────────────────────────────────────────────

class StepIndicator(tk.Canvas):
    """Numbered circles (1)---(2) with labels."""

    R = 14
    ACTIVE = C["danger"]
    INACTIVE = "#333333"

    def __init__(self, parent, labels=("Credentials", "Connect"), **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("height", 56)
        super().__init__(parent, **kwargs)
        self._labels = labels
        self._active = 1
        self.bind("<Configure>", lambda e: self._draw())

    def set_active(self, step):
        self._active = step
        self._draw()

    def _draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 50:
            return
        r = self.R
        cx1, cx2 = w // 2 - 60, w // 2 + 60
        cy = h // 2 - 6

        self.create_line(cx1 + r, cy, cx2 - r, cy,
                         fill="#444", width=2, dash=(4, 3))

        for i, (cx, label) in enumerate(
                [(cx1, self._labels[0]), (cx2, self._labels[1])], 1):
            active = (i <= self._active)
            fill = self.ACTIVE if active else self.INACTIVE
            self.create_oval(cx - r, cy - r, cx + r, cy + r,
                             fill=fill, outline=fill)
            self.create_text(cx, cy, text=str(i), fill="#ffffff",
                             font=("Segoe UI", 10, "bold"))
            self.create_text(cx, cy + r + 14, text=label,
                             fill="#ffffff" if active else "#666",
                             font=("Segoe UI", 8))


# ── Validated Form Field (CustomTkinter) ─────────────────────────────────────

class ValidatedField(ctk.CTkFrame):
    """Rounded CTkEntry with label and optional show toggle."""

    def __init__(self, parent, label_text, textvariable,
                 show=None, show_toggle=False, placeholder=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._var = textvariable
        self._show_char = show or ""
        self._placeholder = placeholder or f"Enter {label_text.lower()}..."

        # Label row
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16)

        self._label = ctk.CTkLabel(top, text=label_text,
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=C["text_dim"])

        if show_toggle:
            self._show_var = ctk.BooleanVar(value=False)
            self._label.pack(side="left", expand=True, padx=(8, 10))
            ctk.CTkSwitch(top, text="Show", variable=self._show_var,
                          command=self._toggle_show,
                          onvalue=True, offvalue=False,
                          width=40, height=20,
                          font=ctk.CTkFont("Segoe UI", 11),
                          text_color=C["text_dim"],
                          progress_color=C["accent"],
                          ).pack(side="right", padx=(0, 8))
        else:
            self._label.pack(anchor="center")

        # Entry
        self._entry = ctk.CTkEntry(
            self, textvariable=textvariable,
            font=ctk.CTkFont("Segoe UI", 13),
            width=FIELD_WIDTH,
            height=42, corner_radius=8,
            border_width=2,
            justify="center",
            placeholder_text=self._placeholder,
        )
        if show:
            self._entry.configure(show=show)
        self._entry.pack(pady=(6, 0))

    def _toggle_show(self):
        self._entry.configure(
            show="" if self._show_var.get() else self._show_char)

    def focus_set(self):
        self._entry.focus()


# ── Stage Manager ────────────────────────────────────────────────────────────

class StageManager:
    """Animated transition between stage 1 (form) and stage 2 (progress)."""

    def __init__(self, border_card, step_ind, stage1, stage2):
        self.card = border_card
        self.step = step_ind
        self.s1 = stage1
        self.s2 = stage2
        self.current = 1
        self._n = 12
        self._ms = 22

    def go_to_stage2(self, callback=None):
        if self.current == 2:
            return
        self.current = 2
        self.step.set_active(2)
        self.card.set_glow(C["cyan"], C["cyan_dim"])
        self._fade_out(self.s1,
                       then=lambda: self._fade_in(self.s2, then=callback))

    def go_to_stage1(self, callback=None):
        if self.current == 1:
            return
        self.current = 1
        self.step.set_active(1)
        self.card.set_glow(C["gold"], C["gold_dim"])
        self._fade_out(self.s2,
                       then=lambda: self._fade_in(self.s1, then=callback))

    def _fade_out(self, f, then=None, step=0):
        if step < self._n:
            try:
                f.pack_configure(pady=(max(0, 16 - step * 2), 0))
            except tk.TclError:
                pass
            f.after(self._ms, lambda: self._fade_out(f, then, step + 1))
        else:
            f.pack_forget()
            if then:
                then()

    def _fade_in(self, f, then=None, step=0):
        if step == 0:
            f.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        if step < self._n:
            try:
                frac = step / self._n
                f.pack_configure(pady=(int(12 * (1 - frac)), 12))
            except tk.TclError:
                pass
            f.after(self._ms, lambda: self._fade_in(f, then, step + 1))
        else:
            f.pack_configure(pady=(0, 12))
            if then:
                then()


# ═══════════════════════════════════════════════════════════════════════════════
#  BUILD THE UI
# ═══════════════════════════════════════════════════════════════════════════════

root = ctk.CTk()
root.title("ThyWeb \u2014 Server Setup")
root.configure(fg_color=C["bg"])
_make_icon(root)

host_var = tk.StringVar()
user_var = tk.StringVar()
pass_var = tk.StringVar()

# ── Header ───────────────────────────────────────────────────────────────────
header = ctk.CTkFrame(root, fg_color="transparent")
header.pack(fill="x", padx=30, pady=(16, 0))

# Logo
logo_widget = None
if HAS_PIL and os.path.exists(LOGO_PATH):
    try:
        ctk_logo = ctk.CTkImage(
            light_image=Image.open(LOGO_PATH),
            dark_image=Image.open(LOGO_PATH),
            size=(56, 56),
        )
        logo_widget = ctk.CTkLabel(header, image=ctk_logo, text="")
        logo_widget.pack(pady=(0, 6))
    except Exception:
        pass
if logo_widget is None:
    ctk.CTkLabel(header, text="TW",
                 font=ctk.CTkFont("Segoe UI", 24, "bold"),
                 text_color=C["accent"]).pack(pady=(0, 6))

ctk.CTkLabel(header, text="Server Setup",
             font=ctk.CTkFont("Segoe UI", 20, "bold"),
             text_color=C["text"]).pack()
ctk.CTkLabel(header, text="Configure your SSH server credentials",
             font=ctk.CTkFont("Segoe UI", 11),
             text_color=C["text_dim"]).pack(pady=(2, 0))

# Step indicator
step_ind = StepIndicator(header, labels=("Credentials", "Connect"),
                         bg=C["bg"])
step_ind.pack(fill="x", padx=50, pady=(8, 0))

# ── Border card ──────────────────────────────────────────────────────────────
container = ctk.CTkFrame(root, fg_color="transparent")
container.pack(fill="both", expand=True, padx=30, pady=(10, 20))

border_card = GradientSweepBorder(container, bg=C["bg"])
border_card.pack(fill="both", expand=True)
card = border_card.inner

# ── Stage 1: Credential form ────────────────────────────────────────────────
stage1 = ctk.CTkFrame(card, fg_color="transparent")
stage1.pack(fill="both", expand=True, padx=8, pady=(10, 14))

form_container = ctk.CTkFrame(stage1, fg_color=C["card_inner"], corner_radius=10)
form_container.pack(pady=(4, 4), expand=True, fill="both", padx=20)

host_field = ValidatedField(form_container, "Hostname / IP Address", host_var,
                            placeholder="e.g. 192.168.1.100 or server.example.com")
host_field.pack(fill="x", padx=12, pady=(16, 8))

user_field = ValidatedField(form_container, "Username", user_var,
                            placeholder="e.g. root or deploy-user")
user_field.pack(fill="x", padx=12, pady=(0, 8))

pass_field = ValidatedField(form_container, "Password", pass_var,
                            show="\u2022", show_toggle=True,
                            placeholder="Enter your SSH password")
pass_field.pack(fill="x", padx=12, pady=(0, 16))

# ── Buttons (inside form) ────────────────────────────────────────────────────
btn_frame = ctk.CTkFrame(form_container, fg_color="transparent")
btn_frame.pack(fill="x", padx=12, pady=(8, 16))

test_btn = ctk.CTkButton(
    btn_frame, text="\u2713  Test & Save",
    command=lambda: on_test_and_save(),
    font=ctk.CTkFont("Segoe UI", 13, "bold"),
    fg_color=C["accent"], hover_color=C["accent_hover"],
    text_color="#0d0d0d",
    height=44, corner_radius=8,
)
test_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

cancel_btn = ctk.CTkButton(
    btn_frame, text="\u2717  Cancel",
    command=lambda: on_cancel(),
    font=ctk.CTkFont("Segoe UI", 13),
    fg_color="transparent",
    hover_color="#2a2a3e",
    border_width=2, border_color=C["muted"],
    text_color=C["text_dim"],
    height=44, corner_radius=8,
)
cancel_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

# ── Stage 2: Connection progress ────────────────────────────────────────────
stage2 = ctk.CTkFrame(card, fg_color="transparent")

s2_center = ctk.CTkFrame(stage2, fg_color="transparent")
s2_center.pack(expand=True)

# Progress bar
progress_bar = ctk.CTkProgressBar(s2_center, width=240, height=14,
                                  corner_radius=7,
                                  progress_color=C["cyan"],
                                  mode="indeterminate")
progress_bar.pack(pady=(20, 18))
progress_bar.set(0)

s2_title = ctk.CTkLabel(s2_center, text="Connecting to",
                        font=ctk.CTkFont("Segoe UI", 13),
                        text_color=C["text_dim"])
s2_title.pack()

s2_host = ctk.CTkLabel(s2_center, text="...",
                       font=ctk.CTkFont("Segoe UI", 15, "bold"),
                       text_color=C["text"])
s2_host.pack(pady=(2, 12))

s2_status = ctk.CTkLabel(s2_center, text="Initializing...",
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=C["accent"])
s2_status.pack()

s2_back = ctk.CTkButton(s2_center, text="\u2190  Back to credentials",
                        fg_color="transparent",
                        hover_color="#2a2a3e",
                        text_color=C["text_dim"],
                        font=ctk.CTkFont("Segoe UI", 11),
                        width=180, height=30,
                        corner_radius=6)
s2_back.pack(pady=(18, 0))

# ── Stage Manager ────────────────────────────────────────────────────────────
stage_mgr = StageManager(border_card, step_ind, stage1, stage2)

# ── Handlers ─────────────────────────────────────────────────────────────────

def on_test_and_save():
    h = host_var.get().strip()
    u = user_var.get().strip()
    p = pass_var.get()

    if not h or not u:
        messagebox.showerror("Missing Information",
                             "Please fill in Hostname/IP and Username.")
        return

    test_btn.configure(state="disabled")
    cancel_btn.configure(state="disabled")
    s2_host.configure(text=h)
    s2_status.configure(text="Initializing connection...",
                        text_color=C["accent"])
    progress_bar.configure(mode="indeterminate", progress_color=C["cyan"])
    progress_bar.start()

    stage_mgr.go_to_stage2(callback=lambda: _start_connection(h, u, p))


def _start_connection(hostname, username, password):
    s2_status.configure(text="Connecting to server...",
                        text_color=C["accent"])

    def do_test():
        ok, msg = test_connection(hostname, username, password)
        root.after(0, lambda: _handle_result(ok, msg, hostname,
                                             username, password))
    threading.Thread(target=do_test, daemon=True).start()


def _handle_result(success, message, hostname, username, password):
    progress_bar.stop()

    if success:
        progress_bar.configure(mode="determinate", progress_color=C["success"])
        progress_bar.set(1.0)
        s2_status.configure(text="Connected! Saving credentials...",
                            text_color=C["success"])
        border_card.set_glow(C["success"], "#0e3520")
        root.update()

        result = update_domain_connector(hostname, username, password)
        if result is True:
            s2_status.configure(text="Launching application...",
                                text_color=C["success"])
            root.update()
            _launch_main_application()
        else:
            _connection_failed(f"Failed to save: {result}")
    else:
        _connection_failed(message)


def _connection_failed(message):
    progress_bar.stop()
    progress_bar.configure(mode="determinate", progress_color=C["danger"])
    progress_bar.set(0)
    s2_status.configure(text="Connection failed", text_color=C["danger"])
    border_card.set_glow(C["danger"], "#4a1515")
    root.update()
    messagebox.showerror("Connection Failed", message)

    def restore():
        test_btn.configure(state="normal")
        cancel_btn.configure(state="normal")
        progress_bar.configure(progress_color=C["cyan"])
        progress_bar.set(0)
    stage_mgr.go_to_stage1(callback=restore)


def _manual_back():
    progress_bar.stop()
    progress_bar.set(0)
    test_btn.configure(state="normal")
    cancel_btn.configure(state="normal")
    stage_mgr.go_to_stage1()


s2_back.configure(command=_manual_back)


def on_cancel():
    root.destroy()


def _launch_main_application():
    """Launch the main app for both source and packaged runs."""
    import subprocess
    import sys

    try:
        if getattr(sys, "frozen", False):
            setup_exe = Path(sys.executable).resolve()
            if sys.platform == "darwin":
                app_bundle = None
                for parent in setup_exe.parents:
                    if parent.suffix == ".app":
                        app_bundle = parent
                        break

                if app_bundle is None:
                    raise FileNotFoundError("Could not resolve setup .app bundle location.")

                candidates = [
                    app_bundle.with_name("ThyWeb.app"),
                ]
                main_app = next((p for p in candidates if p.exists()), None)
                if not main_app:
                    raise FileNotFoundError("Could not find ThyWeb.app near setup app.")
                subprocess.Popen(["open", str(main_app)])
            else:
                candidates = [
                    setup_exe.with_name("ThyWeb.exe"),
                    setup_exe.parent.parent / "ThyWeb" / "ThyWeb.exe",
                    setup_exe.parent / "ThyWeb.exe",
                ]
                main_exe = next((p for p in candidates if p.exists()), None)
                if not main_exe:
                    raise FileNotFoundError("Could not find ThyWeb.exe near setup executable.")
                subprocess.Popen([str(main_exe)])
        else:
            subprocess.Popen([sys.executable, "app.py"])

        root.after(800, root.destroy)
    except Exception as exc:
        messagebox.showerror(
            "Launch Failed",
            f"Credentials were saved, but the main app could not be launched:\n{exc}",
        )


# ── Init ─────────────────────────────────────────────────────────────────────
current = read_current_config()
if current["TARGET_HOSTNAME"]:
    host_var.set(current["TARGET_HOSTNAME"])
if current["TARGET_USERNAME"]:
    user_var.set(current["TARGET_USERNAME"])

host_field.focus_set()

# Make window responsive
root.update_idletasks()
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()

# Scale window based on screen size
W = min(650, int(sw * 0.45))
H = min(720, int(sh * 0.85))

# Center the window
x = max(0, (sw - W) // 2)
y = max(0, (sh - H) // 2)
root.geometry(f"{W}x{H}+{x}+{y}")
root.minsize(480, 580)
root.resizable(True, True)

root.mainloop()
