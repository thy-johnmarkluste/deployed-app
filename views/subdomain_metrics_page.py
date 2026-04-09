"""
Subdomain Metrics Page View — lists performance and health metrics per subdomain.
"""
import tkinter as tk
from tkinter import ttk

from models.config import COLORS
from views.widgets import ModernButton, RoundedFrame


def _lbl(parent, text, size=10, bold=False, color="text_secondary"):
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", size, "bold" if bold else "normal"),
        bg=parent.cget("bg"), fg=COLORS[color],
    )


class SubdomainMetricsPageView:
    """Page listing metrics for each subdomain."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self._all_rows = []
        self._sort_column = "domain"
        self._sort_desc = False
        self._sort_labels = {
            "domain": "Subdomain",
            "ssl": "SSL Expiry",
            "response": "Response (ms)",
            "uptime": "Uptime",
            "bandwidth": "Bandwidth (kbps)",
            "db_speed": "DB Speed (ms)",
            "cpu": "CPU %",
            "memory": "Memory %",
        }
        self._build()

    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)

        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_bar, text="Subdomain Metrics",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self.export_btn = ModernButton(
            title_bar, text="Export CSV", command=None,
            bg_color="#43A047", hover_color="#388E3C", border_color="#2E7D32",
            width=120, height=30,
        )
        self.export_btn.pack(side="right")

        self.refresh_btn = ModernButton(
            title_bar, text="\u21bb  Refresh", command=None,
            bg_color="#0288D1", hover_color="#0277BD", border_color="#01579B",
            width=110, height=30,
        )
        self.refresh_btn.pack(side="right", padx=(0, 8))

        self.clear_cache_btn = ModernButton(
            title_bar, text="Clear Cache", command=None,
            bg_color="#455A64", hover_color="#546E7A", border_color="#37474F",
            width=120, height=30,
        )
        self.clear_cache_btn.pack(side="right", padx=(0, 8))

        filter_row = tk.Frame(container, bg=COLORS["bg_primary"])
        filter_row.pack(fill="x", pady=(0, 10))

        _lbl(filter_row, "Filter:", 9, True).pack(side="left")
        self.filter_var = tk.StringVar()
        tk.Entry(
            filter_row, textvariable=self.filter_var,
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"], width=30,
        ).pack(side="left", padx=(6, 0), ipady=4)
        self.filter_var.trace_add("write", self._apply_filter)

        self.count_lbl = tk.Label(
            filter_row, text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        )
        self.count_lbl.pack(side="right")

        card = RoundedFrame(
            container, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        card.pack(fill="both", expand=True)
        inner = card.inner

        tree_frame = tk.Frame(inner, bg=COLORS["bg_secondary"])
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "Metrics.Treeview",
            background=COLORS["bg_primary"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_primary"],
            font=("Segoe UI", 9),
            rowheight=26,
            borderwidth=0,
        )
        style.configure(
            "Metrics.Treeview.Heading",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
            font=("Segoe UI", 9, "bold"),
            relief="flat",
            padding=(6, 4),
        )
        style.map(
            "Metrics.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "white")],
        )
        style.map(
            "Metrics.Treeview.Heading",
            background=[("active", COLORS["accent"])],
            foreground=[("active", "white")],
        )

        columns = (
            "domain",
            "ssl",
            "response",
            "uptime",
            "bandwidth",
            "db_speed",
            "cpu",
            "memory",
        )
        self.tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", style="Metrics.Treeview"
        )

        self.tree.heading("domain", text="Subdomain", command=lambda: self._toggle_sort("domain"), anchor="w")
        self.tree.heading("ssl", text="SSL Expiry", command=lambda: self._toggle_sort("ssl"), anchor="w")
        self.tree.heading("response", text="Response (ms)", command=lambda: self._toggle_sort("response"), anchor="center")
        self.tree.heading("uptime", text="Uptime", command=lambda: self._toggle_sort("uptime"), anchor="center")
        self.tree.heading("bandwidth", text="Bandwidth (kbps)", command=lambda: self._toggle_sort("bandwidth"), anchor="center")
        self.tree.heading("db_speed", text="DB Speed (ms)", command=lambda: self._toggle_sort("db_speed"), anchor="center")
        self.tree.heading("cpu", text="CPU %", command=lambda: self._toggle_sort("cpu"), anchor="center")
        self.tree.heading("memory", text="Memory %", command=lambda: self._toggle_sort("memory"), anchor="center")

        self.tree.column("domain", width=200, minwidth=150, anchor="w")
        self.tree.column("ssl", width=150, minwidth=120, anchor="w")
        self.tree.column("response", width=110, minwidth=90, anchor="center")
        self.tree.column("uptime", width=90, minwidth=70, anchor="center")
        self.tree.column("bandwidth", width=120, minwidth=100, anchor="center")
        self.tree.column("db_speed", width=110, minwidth=90, anchor="center")
        self.tree.column("cpu", width=80, minwidth=60, anchor="center")
        self.tree.column("memory", width=90, minwidth=70, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("ok", foreground=COLORS["success"])
        self.tree.tag_configure("warn", foreground=COLORS["warning"])
        self.tree.tag_configure("bad", foreground=COLORS["error"])
        self.tree.tag_configure("muted", foreground=COLORS["text_secondary"])
        self.tree.tag_configure("row_even", background=COLORS["bg_primary"])
        self.tree.tag_configure("row_odd", background=COLORS["bg_accent"])
        self.tree.tag_configure("empty", foreground=COLORS["text_secondary"])

        self._refresh_sort_headings()

    def set_loading(self, domains: list[str]):
        self.tree.delete(*self.tree.get_children())
        for d in domains:
            self.tree.insert(
                "", "end",
                values=(d, "…", "…", "…", "…", "…", "…", "…"),
                tags=("muted",),
            )
        self.count_lbl.configure(text=f"Loading {len(domains)} domains…")

    def populate(self, rows: list[dict]):
        self._all_rows = rows or []
        self._render(self._all_rows)

    def _toggle_sort(self, column: str):
        if self._sort_column == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = column
            self._sort_desc = False
        self._refresh_sort_headings()
        self._render(self._all_rows)

    def _refresh_sort_headings(self):
        for col, label in self._sort_labels.items():
            marker = ""
            if col == self._sort_column:
                marker = " ▼" if self._sort_desc else " ▲"
            self.tree.heading(col, text=f"{label}{marker}")

    def _sort_key(self, row: dict):
        col = self._sort_column
        if col == "domain":
            return str(row.get("domain", "")).lower()
        if col == "ssl":
            return str(row.get("ssl", "")).lower()
        if col == "uptime":
            return str(row.get("uptime", "")).lower()
        if col in {"response", "bandwidth", "db_speed", "cpu", "memory"}:
            try:
                return float(row.get(col, 0) or 0)
            except (TypeError, ValueError):
                return 0.0
        return str(row.get(col, "")).lower()

    def _render(self, rows: list[dict]):
        self.tree.delete(*self.tree.get_children())
        f = self.filter_var.get().lower()
        shown = [
            r for r in rows
            if not f
            or f in r.get("domain", "").lower()
            or f in r.get("ssl", "").lower()
        ]

        shown.sort(key=self._sort_key, reverse=self._sort_desc)

        if not shown:
            self.tree.insert(
                "", "end",
                values=("No matching subdomains", "-", "-", "-", "-", "-", "-", "-"),
                tags=("empty",),
            )
            full = len(rows)
            self.count_lbl.configure(
                text=f"0 of {full} domains" if f else "0 domains"
            )
            return

        for idx, r in enumerate(shown):
            status = r.get("status", "ok")
            tag = "ok" if status == "ok" else "warn" if status == "warn" else "bad"
            zebra_tag = "row_even" if idx % 2 == 0 else "row_odd"
            self.tree.insert(
                "", "end",
                values=(
                    r.get("domain", "—"),
                    r.get("ssl", "—"),
                    r.get("response", "—"),
                    r.get("uptime", "—"),
                    r.get("bandwidth", "—"),
                    r.get("db_speed", "—"),
                    r.get("cpu", "—"),
                    r.get("memory", "—"),
                ),
                tags=(zebra_tag, tag),
            )

        total = len(shown)
        full = len(rows)
        self.count_lbl.configure(text=f"{total} of {full}" if f else f"{full} domains")

    def _apply_filter(self, *_):
        self._render(self._all_rows)

    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()
