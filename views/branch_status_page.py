"""
Branch Status Page — shows the currently deployed branch for every subdomain
that has a Git repo initialized on the server.
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


class BranchStatusPageView:
    """Page that lists each subdomain alongside its live-deployed branch."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self._sort_column = "subdomain"
        self._sort_desc = False
        self._sort_labels = {
            "subdomain": "Subdomain",
            "branch": "Deployed Branch",
            "date": "Last Commit",
            "action": "Action",
            "status": "Status",
        }
        self._all_rows: list[dict] = []
        self._build()

    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_bar, text="\U0001f333  Branch Deployment Status",
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


        tk.Label(
            container,
            text="Shows the git branch currently checked out on the server for each subdomain.",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
            anchor="w",
        ).pack(fill="x", pady=(0, 10))


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
        filter_entry = tk.Entry(
            filter_row, textvariable=self.filter_var,
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
            width=28,
        )
        filter_entry.pack(side="left", padx=(6, 0), ipady=4)
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
        style.theme_use("default")
        style.configure(
            "Branch.Treeview",
            background=COLORS["bg_primary"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_primary"],
            font=("Segoe UI", 10),
            rowheight=26,
            borderwidth=0,
        )
        style.configure(
            "Branch.Treeview.Heading",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 4),
        )
        style.map(
            "Branch.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "white")],
        )
        style.map(
            "Branch.Treeview.Heading",
            background=[("active", COLORS["accent"])],
            foreground=[("active", "white")],
        )

        self.tree = ttk.Treeview(
            tree_frame,
            columns=("subdomain", "branch", "date", "action", "status"),
            show="headings",
            style="Branch.Treeview",
        )
        self.tree.heading("subdomain", text="Subdomain", command=lambda: self._toggle_sort("subdomain"), anchor="w")
        self.tree.heading("branch", text="Deployed Branch", command=lambda: self._toggle_sort("branch"), anchor="w")
        self.tree.heading("date", text="Last Commit", command=lambda: self._toggle_sort("date"), anchor="w")
        self.tree.heading("action", text="Action", command=lambda: self._toggle_sort("action"), anchor="center")
        self.tree.heading("status", text="Status", command=lambda: self._toggle_sort("status"), anchor="center")

        self.tree.column("subdomain", width=220, minwidth=150, anchor="w")
        self.tree.column("branch",    width=160, minwidth=100, anchor="w")
        self.tree.column("date",      width=145, minwidth=110, anchor="w")
        self.tree.column("action",    width=90,  minwidth=70,  anchor="center")
        self.tree.column("status",    width=120, minwidth=80,  anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")


        self.tree.tag_configure("main",    foreground=COLORS["success"])
        self.tree.tag_configure("develop", foreground=COLORS["warning"])
        self.tree.tag_configure("feature", foreground="#ab47bc")
        self.tree.tag_configure("push",    foreground="#26c6da")
        self.tree.tag_configure("merge",   foreground=COLORS["warning"])
        self.tree.tag_configure("no_git",  foreground=COLORS["text_secondary"])
        self.tree.tag_configure("error",   foreground=COLORS["error"])
        self.tree.tag_configure("row_even", background=COLORS["bg_primary"])
        self.tree.tag_configure("row_odd", background=COLORS["bg_accent"])
        self.tree.tag_configure("empty", foreground=COLORS["text_secondary"])

        self._refresh_sort_headings()


    def populate(self, rows: list[dict]):
        """Fill the table.

        Each dict: {subdomain, branch, git_ok, date, action, status}
        status: 'Connected' | 'No Git' | 'No Remote' | 'Error' | 'Loading...'
        """
        self._all_rows = rows or []
        self._render(self._all_rows)

    def set_loading(self, subdomain_list: list[str]):
        """Insert placeholder rows with 'Loading...' while fetching."""
        self._all_rows = []
        self.tree.delete(*self.tree.get_children())
        for sd in subdomain_list:
            self.tree.insert(
                "", "end",
                values=(sd, "—", "—", "—", "Loading…"),
                tags=("no_git",),
            )
        self.count_lbl.configure(text=f"{len(subdomain_list)} subdomains")

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
        if col == "subdomain":
            return str(row.get("subdomain", "")).lower()
        if col == "branch":
            return str(row.get("branch", "")).lower()
        if col == "date":
            return str(row.get("date", "")).lower()
        if col == "action":
            return str(row.get("action", "")).lower()
        return str(row.get("status", "")).lower()

    def _render(self, rows: list[dict]):
        self.tree.delete(*self.tree.get_children())
        f = self.filter_var.get().lower()
        shown = [r for r in rows if not f or f in r.get("subdomain", "").lower() or f in r.get("branch", "").lower()]
        shown.sort(key=self._sort_key, reverse=self._sort_desc)

        if not shown:
            self.tree.insert(
                "", "end",
                values=("No matching subdomains", "-", "-", "-", "-"),
                tags=("empty",),
            )
            full = len(rows)
            self.count_lbl.configure(
                text=f"0 of {full} subdomains" if f else "0 subdomains"
            )
            return

        for idx, r in enumerate(shown):
            branch    = r.get("branch", "—")
            git_ok    = r.get("git_ok", False)
            date_txt  = r.get("date", "—") or "—"
            action_txt = r.get("action", "—") or "—"
            status    = r.get("status", "—")


            bl = branch.lower()
            if not git_ok:
                tag = "no_git"
            elif status == "Error":
                tag = "error"
            elif action_txt == "push":
                tag = "push"
            elif action_txt == "merge":
                tag = "merge"
            elif bl in ("main", "master"):
                tag = "main"
            elif "develop" in bl or "dev" in bl:
                tag = "develop"
            elif any(bl.startswith(p) for p in ("feature", "feat", "fix", "hotfix")):
                tag = "feature"
            else:
                tag = "main"

            zebra_tag = "row_even" if idx % 2 == 0 else "row_odd"

            self.tree.insert(
                "", "end",
                values=(r["subdomain"], branch, date_txt, action_txt, status),
                tags=(zebra_tag, tag),
            )
        total = len(shown)
        full  = len(rows)
        self.count_lbl.configure(
            text=f"{total} of {full} subdomains" if f else f"{full} subdomains"
        )

    def _apply_filter(self, *_):
        self._render(self._all_rows)

    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()
