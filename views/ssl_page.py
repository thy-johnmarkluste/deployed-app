"""
SSL Certificate Manager Page — shows SSL/TLS cert status for all Apache vhosts.
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


class SSLPageView:
    """Page listing SSL/TLS certificates for all Apache-configured subdomains."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self._all_rows: list = []
        self._build()

    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 6))

        tk.Label(
            title_bar, text="\U0001F512  SSL Certificate Manager",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self.refresh_btn = ModernButton(
            title_bar, text="\u21bb  Refresh", command=None,
            bg_color="#0288D1", hover_color="#0277BD", border_color="#01579B",
            width=110, height=30,
        )
        self.refresh_btn.pack(side="right")

        tk.Label(
            container,
            text="SSL/TLS certificate status for all Apache-configured subdomains on the server.",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", pady=(0, 10))


        summary_row = tk.Frame(container, bg=COLORS["bg_primary"])
        summary_row.pack(fill="x", pady=(0, 10))

        def _chip(parent, text, color):
            f = tk.Frame(parent, bg=color, padx=10, pady=4)
            f.pack(side="left", padx=(0, 8))
            lbl = tk.Label(f, text=text, font=("Segoe UI", 9, "bold"), bg=color, fg="white")
            lbl.pack()
            return lbl

        self._chip_valid    = _chip(summary_row, "\u2714 Valid: 0",    "#2E7D32")
        self._chip_expiring = _chip(summary_row, "\u26A0 Expiring: 0", "#E65100")
        self._chip_expired  = _chip(summary_row, "\u2716 Expired: 0",  "#B71C1C")
        self._chip_no_ssl   = _chip(summary_row, "\u2014 No SSL: 0",   "#37474F")


        card = RoundedFrame(
            container, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        card.pack(fill="both", expand=True)
        inner = card.inner


        filter_row = tk.Frame(inner, bg=COLORS["bg_secondary"])
        filter_row.pack(fill="x", pady=(0, 8))

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
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self.count_lbl.pack(side="right")


        tree_frame = tk.Frame(inner, bg=COLORS["bg_secondary"])
        tree_frame.pack(fill="both", expand=True)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "SSL.Treeview",
            background=COLORS["bg_primary"], foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_primary"], font=("Segoe UI", 10),
            rowheight=26, borderwidth=0,
        )
        style.configure(
            "SSL.Treeview.Heading",
            background=COLORS["bg_accent"], foreground=COLORS["text_primary"],
            font=("Segoe UI", 10, "bold"), relief="flat", padding=(6, 4),
        )
        style.map("SSL.Treeview",
                  background=[("selected", COLORS["accent"])],
                  foreground=[("selected", "white")])
        style.map("SSL.Treeview.Heading",
                  background=[("active", COLORS["accent"])],
                  foreground=[("active", "white")])

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("domain", "issuer", "issued", "expires", "days", "status"),
            show="headings", style="SSL.Treeview",
        )
        self.tree.heading("domain",  text="Domain",      anchor="w")
        self.tree.heading("issuer",  text="Issuer",      anchor="w")
        self.tree.heading("issued",  text="Issue Date",  anchor="w")
        self.tree.heading("expires", text="Expiry Date", anchor="w")
        self.tree.heading("days",    text="Days Left",   anchor="center")
        self.tree.heading("status",  text="Status",      anchor="center")

        self.tree.column("domain",  width=220, minwidth=150, anchor="w")
        self.tree.column("issuer",  width=180, minwidth=120, anchor="w")
        self.tree.column("issued",  width=130, minwidth=100, anchor="w")
        self.tree.column("expires", width=130, minwidth=100, anchor="w")
        self.tree.column("days",    width=80,  minwidth=60,  anchor="center")
        self.tree.column("status",  width=120, minwidth=90,  anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")


        self.tree.tag_configure("valid",    foreground=COLORS["success"])
        self.tree.tag_configure("expiring", foreground="#FFA726")
        self.tree.tag_configure("expired",  foreground=COLORS["error"])
        self.tree.tag_configure("no_ssl",   foreground=COLORS["text_secondary"])
        self.tree.tag_configure("loading",  foreground=COLORS["text_secondary"])


    def populate(self, rows: list):
        self._all_rows = rows
        self._render(rows)
        self._update_summary(rows)

    def set_loading(self, domains: list):
        self.tree.delete(*self.tree.get_children())
        for d in domains:
            self.tree.insert("", "end",
                             values=(d, "—", "—", "—", "—", "Checking\u2026"),
                             tags=("loading",))
        self.count_lbl.configure(text=f"Checking {len(domains)} domains\u2026")

    def _render(self, rows: list):
        self.tree.delete(*self.tree.get_children())
        f = self.filter_var.get().lower()
        shown = [r for r in rows
                 if not f
                 or f in r.get("domain", "").lower()
                 or f in r.get("issuer", "").lower()
                 or f in r.get("status", "").lower()]
        for r in shown:
            status = r.get("status", "Unknown")
            sl = status.lower()
            if "expired" in sl and "expiring" not in sl:
                tag = "expired"
            elif "expiring" in sl:
                tag = "expiring"
            elif "valid" in sl:
                tag = "valid"
            else:
                tag = "no_ssl"
            days = r.get("days_remaining", "—")
            self.tree.insert(
                "", "end",
                values=(
                    r.get("domain", "—"),
                    r.get("issuer", "—"),
                    r.get("not_before", "—"),
                    r.get("not_after", "—"),
                    str(days) if isinstance(days, int) else "—",
                    status,
                ),
                tags=(tag,),
            )
        total = len(shown)
        full  = len(rows)
        self.count_lbl.configure(
            text=f"{total} of {full}" if f else f"{full} domains"
        )

    def _update_summary(self, rows: list):
        v = sum(1 for r in rows if r.get("status") == "Valid")
        e = sum(1 for r in rows if r.get("status") == "Expiring Soon")
        x = sum(1 for r in rows if r.get("status") == "Expired")
        n = sum(1 for r in rows if r.get("status") == "No SSL")
        self._chip_valid.config(text=f"\u2714 Valid: {v}")
        self._chip_expiring.config(text=f"\u26A0 Expiring: {e}")
        self._chip_expired.config(text=f"\u2716 Expired: {x}")
        self._chip_no_ssl.config(text=f"\u2014 No SSL: {n}")

    def _apply_filter(self, *_):
        if self._all_rows:
            self._render(self._all_rows)

    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()
