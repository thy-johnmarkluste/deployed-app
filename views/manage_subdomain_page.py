"""
Manage Subdomain Page View — displays a table list of all subdomains found
on the server. Lives on its own page (frame) that the controller can show/hide.
"""
import tkinter as tk
from tkinter import ttk

from models.config import COLORS
from views.widgets import ModernEntry, ModernButton, RoundedFrame, LiveMetricCard
from views.spotlight_walkthrough import SpotlightWalkthrough


def _create_label(parent, text, font_size=10, bold=False, color="text_secondary"):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        bg=parent.cget("bg"), fg=COLORS[color],
    )


class ManageSubdomainPageView:
    """Self-contained page frame for displaying subdomain table.
    The controller binds button callbacks after construction."""

    def __init__(self, parent):

        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self._walkthrough: SpotlightWalkthrough = None
        self._walkthrough_shown = False
        self._build()


    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)
        self._container = container  # Store reference for walkthrough


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        self._title_label = tk.Label(
            title_bar, text="Manage Subdomains",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        )
        self._title_label.pack(side="left")

        self.tutorial_btn = ModernButton(
            title_bar, text="🎯 Guide", command=self.start_tutorial,
            bg_color="#607D8B", hover_color="#546E7A", border_color="#455A64",
            width=110, height=30,
        )
        self.tutorial_btn.pack(side="right", padx=(8, 0))


        cards_frame = tk.Frame(container, bg=COLORS["bg_primary"])
        cards_frame.pack(fill="x", pady=(0, 10))
        self._cards_frame = cards_frame  # Store reference for walkthrough
        for i in range(5):
            cards_frame.columnconfigure(i, weight=1)

        self.metric_ssl_expiring = LiveMetricCard(
            cards_frame, title="SSL Expiring", unit="< 30 days",
            icon="\U0001F512", bg_color=COLORS["bg_secondary"],
            accent_color="#FF6B6B",
            info_text="Number of subdomains whose SSL/TLS certificate will expire within the next 30 days. Renew them promptly to avoid downtime.",
        )
        self.metric_ssl_expiring.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self.metric_down = LiveMetricCard(
            cards_frame, title="Down", unit="unreachable",
            icon="\u274C", bg_color=COLORS["bg_secondary"],
            accent_color=COLORS["error"],
            info_text="Subdomains that returned a 5xx error or timed out when probed via HTTP. These sites may be down or misconfigured.",
        )
        self.metric_down.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)

        self.metric_connections = LiveMetricCard(
            cards_frame, title="Connections", unit="active",
            icon="\U0001F50C", bg_color=COLORS["bg_secondary"],
            accent_color="#26C6DA",
            info_text="Current number of established TCP connections on the server (sourced from 'ss' socket statistics).",
        )
        self.metric_connections.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)

        self.metric_load_avg = LiveMetricCard(
            cards_frame, title="Load Avg", unit="1 min",
            icon="\u26A1", bg_color=COLORS["bg_secondary"],
            accent_color="#FFA726",
            info_text="1-minute load average from /proc/loadavg. Represents the average number of processes waiting to run. Values above your CPU core count may indicate high load.",
        )
        self.metric_load_avg.grid(row=0, column=3, sticky="nsew", padx=4, pady=4)

        self.metric_processes = LiveMetricCard(
            cards_frame, title="Processes", unit="running",
            icon="\u2699", bg_color=COLORS["bg_secondary"],
            accent_color="#AB47BC",
            info_text="Total number of running processes on the server (from 'ps aux'). A sudden spike may indicate runaway processes.",
        )
        self.metric_processes.grid(row=0, column=4, sticky="nsew", padx=4, pady=4)


        content_frame = tk.Frame(container, bg=COLORS["bg_primary"])
        content_frame.pack(fill="both", expand=True)


        table_card = RoundedFrame(
            content_frame, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        table_card.pack(fill="both", expand=True)
        self._table_card = table_card  # Store reference for walkthrough

        table_section = table_card.inner


        header_frame = tk.Frame(table_section, bg=COLORS["bg_secondary"])
        header_frame.pack(fill="x", pady=(0, 10))

        _create_label(header_frame, "All Subdomain Entries", 11, True).pack(side="left")


        filter_frame = tk.Frame(table_section, bg=COLORS["bg_secondary"])
        filter_frame.pack(fill="x", pady=(0, 8))
        self._filter_frame = filter_frame  # Store reference for walkthrough

        filter_col = tk.Frame(filter_frame, bg=COLORS["bg_secondary"])
        filter_col.pack(side="left", fill="x", expand=True)

        _create_label(filter_col, "Filter (domain or IP)", 9, True).pack(anchor="w")

        filter_row = tk.Frame(filter_col, bg=COLORS["bg_secondary"])
        filter_row.pack(fill="x", pady=(4, 0))

        self.filter_var = tk.StringVar()
        self._filter_entry = ModernEntry(
            filter_row, textvariable=self.filter_var, font=("Segoe UI", 10),
        )
        self._filter_entry.pack(side="left", fill="x", expand=True, ipady=4)


        ip_filter_col = tk.Frame(filter_frame, bg=COLORS["bg_secondary"])
        ip_filter_col.pack(side="right", padx=(8, 0))

        self.ip_filter_var = tk.StringVar(value="All IPs")
        self.ip_filter_dropdown = ttk.Combobox(
            ip_filter_col, textvariable=self.ip_filter_var, state="readonly",
            font=("Segoe UI", 9), width=18,
        )
        self.ip_filter_dropdown["values"] = ["All IPs"]
        self.ip_filter_dropdown.pack()

        self.filter_summary_label = tk.Label(
            table_section,
            text="Showing 0 entries",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"],
            fg=COLORS["text_secondary"],
            anchor="w",
        )
        self.filter_summary_label.pack(fill="x", pady=(0, 6))


        button_frame = tk.Frame(table_section, bg=COLORS["bg_secondary"])
        button_frame.pack(fill="x", pady=(0, 10))

        self.refresh_btn = ModernButton(
            button_frame, text="Refresh", command=None,
            bg_color="#F57C00", hover_color="#ff8c00",
            border_color="#cc6600", width=100, height=30,
        )
        self.refresh_btn.pack(side="left", padx=8)


        branch_frame = tk.Frame(button_frame, bg=COLORS["bg_secondary"])
        branch_frame.pack(side="right", padx=8)

        _create_label(branch_frame, "Branch:", 9, True).pack(side="left", padx=(0, 4))

        self.branch_var = tk.StringVar(value="main")
        self.branch_entry = ModernEntry(
            branch_frame, textvariable=self.branch_var,
            font=("Segoe UI", 9), width=18,
        )
        self.branch_entry.pack(side="left", ipady=3)


        tree_frame = tk.Frame(table_section, bg=COLORS["bg_secondary"])
        tree_frame.pack(fill="both", expand=True, pady=(4, 0))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Subdomain.Treeview",
            background=COLORS["bg_primary"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_primary"],
            font=("Segoe UI", 10),
            rowheight=26,
            borderwidth=0,
        )
        style.configure(
            "Subdomain.Treeview.Heading",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=(6, 4),
        )
        style.map(
            "Subdomain.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "white")],
        )
        style.map(
            "Subdomain.Treeview.Heading",
            background=[("active", COLORS["accent"])],
            foreground=[("active", "white")],
        )

        self.dns_tree = ttk.Treeview(
            tree_frame,
            columns=("Domain", "IP", "Type", "Git", "Remote", "PDF", "Action"),
            show="headings", selectmode="browse",
            style="Subdomain.Treeview",
        )
        self.dns_tree.heading("Domain", text="Domain Name", anchor="w")
        self.dns_tree.heading("IP", text="IP Address", anchor="w")
        self.dns_tree.heading("Type", text="Type", anchor="center")
        self.dns_tree.heading("Git", text="Git", anchor="center")
        self.dns_tree.heading("Remote", text="Remote", anchor="center")
        self.dns_tree.heading("PDF", text="PDF", anchor="center")
        self.dns_tree.heading("Action", text="Action", anchor="center")
        self.dns_tree.column("Domain", width=220, anchor="w")
        self.dns_tree.column("IP", width=110, anchor="w")
        self.dns_tree.column("Type", width=95, anchor="center")
        self.dns_tree.column("Git", width=90, anchor="center")
        self.dns_tree.column("Remote", width=90, anchor="center")
        self.dns_tree.column("PDF", width=60, anchor="center")
        self.dns_tree.column("Action", width=80, anchor="center")
        self.dns_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.dns_tree.yview,
        )
        self.dns_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.dns_tree.tag_configure("git_yes", foreground=COLORS["success"])
        self.dns_tree.tag_configure("git_no", foreground=COLORS["error"])
        self.dns_tree.tag_configure("checking", foreground=COLORS["text_secondary"])
        self.dns_tree.tag_configure("row_even", background=COLORS["bg_primary"])
        self.dns_tree.tag_configure("row_odd", background=COLORS["bg_accent"])
        self.dns_tree.tag_configure(
            "buttons", foreground=COLORS["accent"], font=("Segoe UI", 9, "bold"),
        )

    def update_filter_summary(self, total: int, registered: int, unregistered: int, vultr: int):
        self.filter_summary_label.config(
            text=(
                f"Showing {total} entries | "
                f"Registered: {registered} | Unregistered: {unregistered} | Vultr: {vultr}"
            )
        )

    def start_tutorial(self):
        """Launch the spotlight-based onboarding walkthrough."""
        if self._walkthrough and self._walkthrough.is_active():
            return

        root = self.frame.winfo_toplevel()
        self._walkthrough = SpotlightWalkthrough(root)

        # Step 1: Metric Cards
        self._walkthrough.add_step(
            widget=self._cards_frame,
            title="Live Server Metrics",
            description=(
                "These cards show real-time server health at a glance:\n\n"
                "• SSL Expiring — certificates expiring within 30 days\n"
                "• Down — unreachable subdomains\n"
                "• Connections — active TCP connections\n"
                "• Load Avg — system load (1 min average)\n"
                "• Processes — running process count\n\n"
                "Hover over ℹ icons for detailed explanations."
            ),
            position="bottom",
            padding=12,
        )

        # Step 2: Filter Controls
        self._walkthrough.add_step(
            widget=self._filter_frame,
            title="Search & Filter",
            description=(
                "Quickly find subdomains using the filter controls:\n\n"
                "• Type in the search box to filter by domain name or IP\n"
                "• Use the dropdown to filter by specific IP address\n"
                "• The summary below shows filtered counts\n\n"
                "Filters apply instantly as you type."
            ),
            position="bottom",
            padding=10,
        )

        # Step 3: Subdomain Table
        self._walkthrough.add_step(
            widget=self.dns_tree,
            title="Subdomain Table",
            description=(
                "Your complete subdomain inventory:\n\n"
                "• Domain — full subdomain name\n"
                "• IP Address — server IP assignment\n"
                "• Type — registration status\n"
                "• Git — repository connection status\n"
                "• Remote — remote server connectivity\n"
                "• PDF — documentation availability\n\n"
                "Click any row to select it for actions."
            ),
            position="left",
            padding=8,
        )

        # Step 4: Action Column
        self._walkthrough.add_step(
            widget=self.dns_tree,
            title="Taking Action",
            description=(
                "The Action column is your command center:\n\n"
                "1. Select a subdomain row first\n"
                "2. Click 'Connect' to establish an SSH connection\n"
                "3. Once connected, use 'Upload' to transfer files\n"
                "4. Or open 'File Editor' to edit server files directly\n\n"
                "💡 Tip: Always connect before uploading or editing!"
            ),
            position="left",
            padding=8,
        )

        # Set callbacks
        self._walkthrough.on_complete(self._on_walkthrough_complete)
        self._walkthrough.on_skip(self._on_walkthrough_skip)

        # Start the walkthrough
        self._walkthrough.start()

    def _on_walkthrough_complete(self):
        """Called when walkthrough finishes successfully."""
        self._walkthrough_shown = True
        self._walkthrough = None

    def _on_walkthrough_skip(self):
        """Called when user skips the walkthrough."""
        self._walkthrough_shown = True
        self._walkthrough = None

    def _stop_walkthrough(self):
        """Stop the walkthrough if active."""
        if self._walkthrough:
            self._walkthrough.stop()
            self._walkthrough = None

    def show(self):
        self.frame.pack(fill="both", expand=True)
        # Auto-start walkthrough on first visit (after brief delay for layout)
        if not self._walkthrough_shown:
            self.frame.after(300, self.start_tutorial)

    def hide(self):
        self._stop_walkthrough()
        self.frame.pack_forget()
