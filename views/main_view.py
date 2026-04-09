"""
Main View — two-page layout with sidebar navigation: Dashboard (overview /
metrics) and Subdomain management page.  The controller binds callbacks
after construction.
"""
import tkinter as tk
from tkinter import ttk

from models.config import COLORS, HAS_THEMES, HAS_MATPLOTLIB
from views.widgets import ModernButton, RoundedFrame, LiveMetricCard, LiveProgressBar
from views.charts import ChartManager, StatsPieChart
from views.subdomain_page import SubdomainPageView
from views.manage_subdomain_page import ManageSubdomainPageView
from views.repo_setup_page import RepoSetupPageView
from views.reports_page import ReportsPageView
from views.branch_status_page import BranchStatusPageView
from views.subdomain_metrics_page import SubdomainMetricsPageView

if HAS_THEMES:
    from ttkthemes import ThemedStyle

SIDEBAR_BG = "#0f0f0f"
SIDEBAR_HOVER = "#1a1a2e"
SIDEBAR_EXPANDED_W = 200
SIDEBAR_COLLAPSED_W = 52


NAV_ICONS = {
    "dashboard":      "\u25A3",
    "subdomains":     "\u2630",
    "repo_setup":     "\u2B21",
    "metrics":        "\u25A6",
    "branch_status":  "\U0001f333",
}


def _create_label(parent, text, font_size=10, bold=False, color="text_secondary"):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        bg=parent.cget("bg"), fg=COLORS[color],
    )


class MainView:
    """Two-page UI: a *dashboard* page and a *subdomain-management* page.
    Pages are plain frames shown/hidden inside a shared container.
    The controller wires all callbacks."""

    def __init__(self, root, hostname, username):
        self.root = root
        self.root.title("Server Configuration App - Manage Subdomain Entries")
        self.root.geometry("1100x700")
        self.root.minsize(1000, 600)
        self.root.resizable(True, True)
        self.root.configure(bg=COLORS["bg_primary"])

        style = ttk.Style()
        if HAS_THEMES:
            themed_style = ThemedStyle(self.root)
            themed_style.set_theme("arc")
        style.theme_use("clam")


        self.status_var = tk.StringVar(value="Ready")
        tk.Label(
            self.root, textvariable=self.status_var,
            relief=tk.FLAT, anchor="w",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            font=("Segoe UI", 9),
        ).pack(fill="x", side="bottom")


        content_wrapper = tk.Frame(self.root, bg=COLORS["bg_primary"])
        content_wrapper.pack(fill="both", expand=True)


        self._build_sidebar(content_wrapper)


        right_area = tk.Frame(content_wrapper, bg=COLORS["bg_primary"])
        right_area.pack(side="left", fill="both", expand=True)


        self._build_top_bar(right_area, hostname, username)


        self._page_container = tk.Frame(right_area, bg=COLORS["bg_primary"])
        self._page_container.pack(fill="both", expand=True)


        self._build_dashboard(hostname, username)
        self._build_subdomain_hub()
        self.subdomain_page = SubdomainPageView(self._subdomain_hub_content)
        self.manage_subdomain_page = ManageSubdomainPageView(self._subdomain_hub_content)
        self.reports_page = ReportsPageView(self._subdomain_hub_content)
        self.repo_setup_page = RepoSetupPageView(self._page_container)
        self.metrics_page = SubdomainMetricsPageView(self._page_container)
        self.branch_status_page = BranchStatusPageView(self._page_container)


        self.domain_entry = self.subdomain_page.domain_entry
        self.ip_entry = self.subdomain_page.ip_entry
        self.add_btn = self.subdomain_page.add_btn
        self.refresh_btn = self.subdomain_page.refresh_btn
        self.clear_btn = self.subdomain_page.clear_btn


        self.filter_var = self.manage_subdomain_page.filter_var
        self.ip_filter_var = self.manage_subdomain_page.ip_filter_var
        self.ip_filter_dropdown = self.manage_subdomain_page.ip_filter_dropdown
        self.dns_tree = self.manage_subdomain_page.dns_tree


        self.manage_filter_var = self.manage_subdomain_page.filter_var
        self.manage_ip_filter_var = self.manage_subdomain_page.ip_filter_var
        self.manage_ip_filter_dropdown = self.manage_subdomain_page.ip_filter_dropdown
        self.manage_dns_tree = self.manage_subdomain_page.dns_tree


        self.current_page = "dashboard"


        self.show_dashboard()


    def _build_top_bar(self, parent, hostname, username):
        """Status / action bar shown above every page."""
        top_bar_frame = tk.Frame(parent, bg=COLORS["bg_accent"], pady=0)
        top_bar_frame.pack(fill="x", side="top")

        tk.Frame(parent, bg="#555555", height=1).pack(fill="x", side="top")

        inner = tk.Frame(top_bar_frame, bg=COLORS["bg_accent"], padx=16, pady=6)
        inner.pack(fill="x")


        self.connection_label = tk.Label(
            inner,
            text=f"Connected to {username}@{hostname}",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["success"],
        )
        self.connection_label.pack(side="left")

        self.status_chip = tk.Label(
            inner, text="Ready",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            padx=10, pady=4,
        )
        self.status_chip.pack(side="left", padx=(12, 0))

        self.page_title_var = tk.StringVar(value="Dashboard")
        self.page_title_label = tk.Label(
            inner, textvariable=self.page_title_var,
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
        )
        self.page_title_label.pack(side="left", padx=(12, 0))


        self.exit_btn = ModernButton(
            inner, text="Exit", command=None,
            bg_color=COLORS["error"], hover_color="#c73e54", border_color="#b33248",
            width=90, height=28,
        )
        self.exit_btn.pack(side="right", padx=(8, 0))

        self.help_btn = ModernButton(
            inner, text="Help", command=None,
            bg_color="#d4a843", hover_color="#e0b84e", border_color="#b8922e",
            width=90, height=28,
        )
        self.help_btn.pack(side="right", padx=8)

        self.test_btn = ModernButton(
            inner, text="Test Connection", command=None,
            bg_color="#4ecca3", hover_color="#3db892", border_color="#3da17f",
            width=150, height=28,
        )
        self.test_btn.pack(side="right")


    def _build_sidebar(self, parent):
        self._sidebar_expanded = True
        self._sidebar = tk.Frame(parent, bg=SIDEBAR_BG, width=SIDEBAR_EXPANDED_W)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)


        toggle_frame = tk.Frame(self._sidebar, bg=SIDEBAR_BG)
        toggle_frame.pack(fill="x", padx=0, pady=(8, 0))

        self._toggle_btn = tk.Label(
            toggle_frame, text="\u276E",
            font=("Segoe UI", 12, "bold"),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
            cursor="hand2", padx=6,
        )
        self._toggle_btn.pack(side="right", padx=(0, 10))
        self._toggle_btn.bind("<Button-1>", lambda e: self.toggle_sidebar())
        self._toggle_btn.bind("<Enter>", lambda e: self._toggle_btn.config(fg=COLORS["text_primary"]))
        self._toggle_btn.bind("<Leave>", lambda e: self._toggle_btn.config(fg=COLORS["text_secondary"]))


        self._brand_label = tk.Label(
            self._sidebar, text="Server Config App",
            font=("Segoe UI", 12, "bold"),
            bg=SIDEBAR_BG, fg=COLORS["text_primary"],
        )
        self._brand_label.pack(padx=14, pady=(6, 1), anchor="w")


        self._sidebar_divider = tk.Frame(self._sidebar, bg=COLORS["bg_accent"], height=1)
        self._sidebar_divider.pack(fill="x", padx=10, pady=(10, 10))


        self._nav_heading = tk.Label(
            self._sidebar, text="SERVER CONFIG",
            font=("Segoe UI", 7, "bold"),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
        )
        self._nav_heading.pack(padx=14, anchor="w", pady=(0, 6))


        self._nav_items = {}
        self._nav_items["dashboard"] = self._make_nav_btn("dashboard", "Dashboard")
        self._nav_items["subdomains"] = self._make_nav_menu_btn(
            "subdomains",
            "Subdomains",
            [
                ("add", "Add Subdomain", "+", lambda: self.show_subdomain_hub("add")),
                ("manage", "Manage Subdomains", "\u2630", lambda: self.show_subdomain_hub("manage")),
                ("reports", "Reports", "\u2261", lambda: self.show_subdomain_hub("reports")),
            ],
        )
        self._nav_items["repo_setup"] = self._make_nav_btn("repo_setup", "Repo Setup")
        self._nav_items["metrics"] = self._make_nav_btn("metrics", "Subdomain Metrics")
        self._nav_items["branch_status"] = self._make_nav_btn("branch_status", "Branch Status")

        self.set_active_nav("dashboard")

    def _make_nav_btn(self, key, text):
        """Create a sidebar nav button with icon. Returns the outer frame."""
        icon_char = NAV_ICONS.get(key, "\u25CF")
        frame = tk.Frame(self._sidebar, bg=SIDEBAR_BG, cursor="hand2")
        frame.pack(fill="x", padx=4, pady=2, ipady=5)

        icon_label = tk.Label(
            frame, text=icon_char,
            font=("Segoe UI", 11),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
            width=2, anchor="center",
        )
        icon_label.pack(side="left", padx=(8, 4))

        text_label = tk.Label(
            frame, text=text,
            font=("Segoe UI", 10),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
            anchor="w",
        )
        text_label.pack(side="left", fill="x", expand=True)

        frame._icon = icon_label
        frame._label = text_label
        frame._is_active = False

        for w in (frame, icon_label, text_label):
            w.bind("<Enter>", lambda e, f=frame: self._on_nav_hover(f, True))
            w.bind("<Leave>", lambda e, f=frame: self._on_nav_hover(f, False))
        return frame

    def _make_nav_menu_btn(self, key, text, menu_items):
        """Create a sidebar nav button with a collapsible submenu below it."""
        icon_char = NAV_ICONS.get(key, "\u25CF")
        wrapper = tk.Frame(self._sidebar, bg=SIDEBAR_BG)
        wrapper.pack(fill="x", padx=4, pady=2)

        frame = tk.Frame(wrapper, bg=SIDEBAR_BG, cursor="hand2")
        frame.pack(fill="x", ipady=5)

        icon_label = tk.Label(
            frame, text=icon_char,
            font=("Segoe UI", 11),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
            width=2, anchor="center",
        )
        icon_label.pack(side="left", padx=(8, 4))

        header_btn = tk.Button(
            frame, text=f"{text}  \u25BE",
            font=("Segoe UI", 10, "bold"),
            bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
            activebackground=SIDEBAR_HOVER, activeforeground=COLORS["text_primary"],
            relief="flat", borderwidth=0, highlightthickness=0,
            padx=6, pady=2,
            anchor="w",
        )
        header_btn.pack(side="left", fill="x", expand=True)

        submenu = tk.Frame(wrapper, bg=SIDEBAR_BG)

        def _toggle_submenu():
            if submenu.winfo_ismapped():
                submenu.pack_forget()
                header_btn.config(text=f"{text}  \u25BE")
            else:
                submenu.pack(fill="x", padx=24, pady=(0, 4))
                header_btn.config(text=f"{text}  \u25B4")

        header_btn.configure(command=_toggle_submenu)

        submenu_buttons = {}
        for item in menu_items:
            if len(item) == 4:
                key_id, label, icon, callback = item
            else:
                key_id, label, callback = item
                icon = ""
            label_text = f"{icon}  {label}" if icon else label
            btn = tk.Button(
                submenu, text=label_text,
                font=("Segoe UI", 10),
                bg=SIDEBAR_BG, fg=COLORS["text_secondary"],
                activebackground=SIDEBAR_HOVER, activeforeground=COLORS["text_primary"],
                relief="flat", borderwidth=0, highlightthickness=0,
                anchor="w", padx=6, pady=2,
                command=callback,
            )
            btn.pack(fill="x", padx=(6, 0), pady=1)
            submenu_buttons[key_id] = btn

        frame._icon = icon_label
        frame._label = header_btn
        frame._submenu = submenu
        frame._submenu_buttons = submenu_buttons
        frame._is_active = False
        frame._wrapper = wrapper

        for w in (frame, icon_label, header_btn):
            w.bind("<Enter>", lambda e, f=frame: self._on_nav_hover(f, True))
            w.bind("<Leave>", lambda e, f=frame: self._on_nav_hover(f, False))

        return frame

    @staticmethod
    def _on_nav_hover(frame, entering):
        if getattr(frame, "_is_active", False):
            return
        bg = SIDEBAR_HOVER if entering else SIDEBAR_BG
        frame.config(bg=bg)
        frame._label.config(bg=bg)
        frame._icon.config(bg=bg)

    def set_active_nav(self, name):
        """Highlight the given sidebar item, dim the rest."""
        for key, frame in self._nav_items.items():
            if key == name:
                frame._is_active = True
                frame.config(bg=COLORS["bg_accent"])
                frame._label.config(
                    bg=COLORS["bg_accent"],
                    fg=COLORS["text_primary"],
                    font=("Segoe UI", 10, "bold"),
                )
                frame._icon.config(
                    bg=COLORS["bg_accent"],
                    fg=COLORS["text_primary"],
                )
            else:
                frame._is_active = False
                frame.config(bg=SIDEBAR_BG)
                frame._label.config(
                    bg=SIDEBAR_BG,
                    fg=COLORS["text_secondary"],
                    font=("Segoe UI", 10),
                )
                frame._icon.config(
                    bg=SIDEBAR_BG,
                    fg=COLORS["text_secondary"],
                )

    def toggle_sidebar(self):
        """Collapse or expand the sidebar."""
        self._sidebar_expanded = not self._sidebar_expanded
        if self._sidebar_expanded:

            self._sidebar.config(width=SIDEBAR_EXPANDED_W)
            self._toggle_btn.config(text="\u276E")
            self._brand_label.config(text="Server Config App")
            self._nav_heading.pack(padx=14, anchor="w", pady=(0, 6))
            for frame in self._nav_items.values():
                frame._label.pack(side="left", fill="x", expand=True)
        else:

            self._sidebar.config(width=SIDEBAR_COLLAPSED_W)
            self._toggle_btn.config(text="\u276F")
            self._brand_label.config(text="\u25A3")
            self._nav_heading.pack_forget()
            for frame in self._nav_items.values():
                frame._label.pack_forget()


    def _build_subdomain_hub(self):
        self._subdomain_hub_frame = tk.Frame(self._page_container, bg=COLORS["bg_primary"])

        tab_bar = tk.Frame(self._subdomain_hub_frame, bg=COLORS["bg_primary"])
        tab_bar.pack(fill="x", padx=24, pady=(16, 8))

        tk.Label(
            tab_bar, text="Subdomains",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(side="left")

        self._subdomain_tab_var = tk.StringVar(value="Add Subdomain")
        self._subdomain_tab_dropdown = ttk.Combobox(
            tab_bar,
            textvariable=self._subdomain_tab_var,
            state="readonly",
            font=("Segoe UI", 9),
            width=22,
        )
        self._subdomain_tab_dropdown["values"] = [
            "Add Subdomain",
            "Manage Subdomains",
            "Reports",
        ]
        self._subdomain_tab_dropdown.pack(side="left", padx=(8, 0))
        self._subdomain_tab_dropdown.bind(
            "<<ComboboxSelected>>",
            lambda e: self._set_subdomain_tab(self._subdomain_tab_var.get()),
        )

        self._subdomain_hub_content = tk.Frame(self._subdomain_hub_frame, bg=COLORS["bg_primary"])
        self._subdomain_hub_content.pack(fill="both", expand=True)

    def _set_subdomain_tab(self, tab):
        self.subdomain_page.hide()
        self.manage_subdomain_page.hide()
        self.reports_page.hide()

        label = tab
        if tab == "add" or tab == "Add Subdomain":
            label = "Add Subdomain"
            self.subdomain_page.show()
            self.set_page_title("Subdomains - Add")
            active_key = "add"
        elif tab == "manage" or tab == "Manage Subdomains":
            label = "Manage Subdomains"
            self.manage_subdomain_page.show()
            self.set_page_title("Subdomains - Manage")
            active_key = "manage"
        else:
            label = "Reports"
            self.reports_page.show()
            self.reports_page.load_reports()
            self.set_page_title("Subdomains - Reports")
            active_key = "reports"

        if self._subdomain_tab_var.get() != label:
            self._subdomain_tab_var.set(label)

        self._highlight_subdomain_menu(active_key)

    def _highlight_subdomain_menu(self, active_key):
        subdomains_nav = self._nav_items.get("subdomains")
        if not subdomains_nav or not hasattr(subdomains_nav, "_submenu_buttons"):
            return
        for key_id, btn in subdomains_nav._submenu_buttons.items():
            if key_id == active_key:
                btn.config(
                    bg=COLORS["bg_accent"],
                    fg=COLORS["text_primary"],
                    font=("Segoe UI", 10, "bold"),
                )
            else:
                btn.config(
                    bg=SIDEBAR_BG,
                    fg=COLORS["text_secondary"],
                    font=("Segoe UI", 10),
                )


    def _build_dashboard(self, hostname, username):
        self._dashboard_frame = tk.Frame(self._page_container, bg=COLORS["bg_primary"])


        self._dashboard_canvas = tk.Canvas(
            self._dashboard_frame, bg=COLORS["bg_primary"],
            highlightthickness=0, bd=0,
        )
        self._dashboard_scrollbar = ttk.Scrollbar(
            self._dashboard_frame, orient="vertical",
            command=self._dashboard_canvas.yview,
        )
        self._dashboard_canvas.configure(yscrollcommand=self._dashboard_scrollbar.set)

        self._dashboard_scrollbar.pack(side="right", fill="y")
        self._dashboard_canvas.pack(side="left", fill="both", expand=True)


        main_container = tk.Frame(self._dashboard_canvas, bg=COLORS["bg_primary"], padx=24, pady=16)
        self._dashboard_window = self._dashboard_canvas.create_window(
            (0, 0), window=main_container, anchor="nw",
        )


        def _on_frame_configure(event):
            self._dashboard_canvas.configure(scrollregion=self._dashboard_canvas.bbox("all"))

        def _on_canvas_configure(event):

            self._dashboard_canvas.itemconfig(self._dashboard_window, width=event.width)

        main_container.bind("<Configure>", _on_frame_configure)
        self._dashboard_canvas.bind("<Configure>", _on_canvas_configure)


        self._build_live_metrics(main_container)


        charts_area = tk.Frame(main_container, bg=COLORS["bg_primary"])
        charts_area.pack(fill="both", expand=False, pady=(0, 6))
        charts_area.configure(height=300)
        charts_area.pack_propagate(False)
        charts_area.columnconfigure(0, weight=3)
        charts_area.columnconfigure(1, weight=1)
        charts_area.rowconfigure(0, weight=1)


        main_chart_card = RoundedFrame(
            charts_area, bg_color=COLORS["bg_accent"],
            radius=16, padding=(20, 14),
        )
        main_chart_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        main_chart_card.grid_propagate(False)
        chart_inner = main_chart_card.inner
        chart_inner.columnconfigure(0, weight=1)
        chart_inner.rowconfigure(0, weight=0)
        chart_inner.rowconfigure(1, weight=1)


        top_bar = tk.Frame(chart_inner, bg=COLORS["bg_accent"])
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        tk.Label(
            top_bar, text="Subdomain:",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        ).pack(side="left")

        self.subdomain_var = tk.StringVar(value="-- Overview --")
        self.subdomain_dropdown = ttk.Combobox(
            top_bar, textvariable=self.subdomain_var, state="readonly",
            font=("Segoe UI", 9), width=28,
        )
        self.subdomain_dropdown["values"] = ["-- Overview --"]
        self.subdomain_dropdown.pack(side="left", padx=(6, 8))

        self.refresh_metrics_btn = ModernButton(
            top_bar, text="Refresh Metrics", command=None,
            bg_color="#d4a843", hover_color="#e0b84e", border_color="#b8922e",
            width=130, height=26,
        )
        self.refresh_metrics_btn.pack(side="left", padx=(0, 12))


        chart_frame = tk.Frame(chart_inner, bg=COLORS["bg_accent"])
        chart_frame.grid(row=1, column=0, sticky="nsew")
        self.chart_manager = ChartManager(chart_frame)

        if not HAS_MATPLOTLIB:
            self.chart_manager.chart_canvas.bind("<Configure>", lambda e: None)


        stats_chart_card = RoundedFrame(
            charts_area, bg_color=COLORS["bg_accent"],
            radius=16, padding=(14, 14),
        )
        stats_chart_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        stats_chart_card.grid_propagate(False)
        self.stats_chart = StatsPieChart(stats_chart_card.inner)


        self._build_activity_log(main_container)


    def _build_live_metrics(self, parent):
        """Build the live-updating metrics row above the charts."""
        outer = tk.Frame(parent, bg=COLORS["bg_secondary"])
        outer.pack(fill="x", pady=(0, 6))


        cards_frame = tk.Frame(outer, bg=COLORS["bg_secondary"])
        cards_frame.pack(fill="x")
        for i in range(5):
            cards_frame.columnconfigure(i, weight=1)

        metric_shell_1 = RoundedFrame(
            cards_frame, bg_color=COLORS["bg_accent"],
            radius=12, padding=(0, 0),
        )
        metric_shell_1.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.metric_subdomains = LiveMetricCard(
            metric_shell_1.inner, title="Subdomains", unit="total",
            icon="\U0001F310", bg_color=COLORS["bg_secondary"],
            accent_color=COLORS["success"],
        )
        self.metric_subdomains.pack(fill="both", expand=True)

        metric_shell_2 = RoundedFrame(
            cards_frame, bg_color=COLORS["bg_accent"],
            radius=12, padding=(0, 0),
        )
        metric_shell_2.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.metric_repos = LiveMetricCard(
            metric_shell_2.inner, title="Git Repos", unit="repos",
            icon="\U0001F4E6", bg_color=COLORS["bg_secondary"],
            accent_color="#58d4c8",
        )
        self.metric_repos.pack(fill="both", expand=True)

        metric_shell_3 = RoundedFrame(
            cards_frame, bg_color=COLORS["bg_accent"],
            radius=12, padding=(0, 0),
        )
        metric_shell_3.grid(row=0, column=2, sticky="nsew", padx=4, pady=4)
        self.metric_registered = LiveMetricCard(
            metric_shell_3.inner, title="Registered", unit="active",
            icon="\u2705", bg_color=COLORS["bg_secondary"],
            accent_color=COLORS["success"],
        )
        self.metric_registered.pack(fill="both", expand=True)

        metric_shell_4 = RoundedFrame(
            cards_frame, bg_color=COLORS["bg_accent"],
            radius=12, padding=(0, 0),
        )
        metric_shell_4.grid(row=0, column=3, sticky="nsew", padx=4, pady=4)
        self.metric_unregistered = LiveMetricCard(
            metric_shell_4.inner, title="Unregistered", unit="pending",
            icon="\u26A0\uFE0F", bg_color=COLORS["bg_secondary"],
            accent_color=COLORS["warning"],
        )
        self.metric_unregistered.pack(fill="both", expand=True)

        metric_shell_5 = RoundedFrame(
            cards_frame, bg_color=COLORS["bg_accent"],
            radius=12, padding=(0, 0),
        )
        metric_shell_5.grid(row=0, column=4, sticky="nsew", padx=4, pady=4)
        self.metric_vultr = LiveMetricCard(
            metric_shell_5.inner, title="Vultr DNS", unit="records",
            icon="\u2601\uFE0F", bg_color=COLORS["bg_secondary"],
            accent_color="#58d4c8",
        )
        self.metric_vultr.pack(fill="both", expand=True)


        res_shell = RoundedFrame(
            outer, bg_color=COLORS["bg_accent"],
            radius=12, padding=(14, 10),
        )
        res_shell.configure(height=130)
        res_shell.pack_propagate(False)
        res_shell.pack(fill="x", pady=(6, 0))
        res_frame = res_shell.inner

        tk.Label(
            res_frame, text="Server Resources (Live)",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 6))

        bars_grid = tk.Frame(res_frame, bg=COLORS["bg_secondary"])
        bars_grid.pack(fill="x")
        bars_grid.columnconfigure(0, weight=1)
        bars_grid.columnconfigure(1, weight=1)
        bars_grid.columnconfigure(2, weight=1)

        self.cpu_bar = LiveProgressBar(
            bars_grid, title="CPU", max_value=100,
            bar_color=COLORS["cpu"],
        )
        self.cpu_bar.grid(row=0, column=0, sticky="ew", padx=(0, 10), pady=2)

        self.mem_bar = LiveProgressBar(
            bars_grid, title="Memory", max_value=100,
            bar_color=COLORS["memory"],
        )
        self.mem_bar.grid(row=0, column=1, sticky="ew", padx=10, pady=2)

        self.disk_bar = LiveProgressBar(
            bars_grid, title="Disk", max_value=100,
            bar_color=COLORS["uptime"],
        )
        self.disk_bar.grid(row=0, column=2, sticky="ew", padx=(10, 0), pady=2)


    def _build_activity_log(self, parent):
        """Git activity log table — shown on the dashboard."""
        activity_shell = RoundedFrame(
            parent, bg_color=COLORS["bg_accent"],
            radius=14, padding=(14, 10),
        )
        activity_shell.pack(fill="both", expand=True, pady=(6, 0))

        activity_inner = activity_shell.inner


        header_row = tk.Frame(activity_inner, bg=COLORS["bg_secondary"])
        header_row.pack(fill="x", pady=(0, 6))

        tk.Label(
            header_row, text="Git Activity Log",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        ).pack(side="left")

        self.activity_status_label = tk.Label(
            header_row, text="Select a subdomain to view activity",
            font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self.activity_status_label.pack(side="left", padx=(12, 0))

        self.refresh_activity_btn = ModernButton(
            header_row, text="Refresh", command=None,
            bg_color="#d4a843", hover_color="#e0b84e", border_color="#b8922e",
            width=90, height=24,
        )
        self.refresh_activity_btn.pack(side="right")


        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "ActivityLog.Treeview",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_accent"],
            font=("Segoe UI", 9),
            rowheight=24,
        )
        style.configure(
            "ActivityLog.Treeview.Heading",
            background=COLORS["bg_secondary"],
            foreground=COLORS["text_primary"],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "ActivityLog.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#0f0f0f")],
        )

        tree_frame = tk.Frame(activity_inner, bg=COLORS["bg_accent"])
        tree_frame.pack(fill="both", expand=True)

        columns = ("date", "action", "author", "hash", "message")
        self.activity_tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            style="ActivityLog.Treeview", height=8,
        )

        self.activity_tree.heading("date", text="Date")
        self.activity_tree.heading("action", text="Action")
        self.activity_tree.heading("author", text="Author")
        self.activity_tree.heading("hash", text="Hash")
        self.activity_tree.heading("message", text="Message")

        self.activity_tree.column("date", width=140, minwidth=120)
        self.activity_tree.column("action", width=70, minwidth=60, anchor="center")
        self.activity_tree.column("author", width=120, minwidth=80)
        self.activity_tree.column("hash", width=70, minwidth=60, anchor="center")
        self.activity_tree.column("message", width=300, minwidth=150)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=scrollbar.set)

        self.activity_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        self.activity_tree.tag_configure("commit", foreground=COLORS["text_primary"])
        self.activity_tree.tag_configure("push", foreground=COLORS["success"])
        self.activity_tree.tag_configure("pull", foreground=COLORS["uptime"])
        self.activity_tree.tag_configure("merge", foreground=COLORS["warning"])

        self.activity_tree.tag_configure("init", foreground="#9b59b6")
        self.activity_tree.tag_configure("connect", foreground="#58d4c8")
        self.activity_tree.tag_configure("upload", foreground="#d4a843")
        self.activity_tree.tag_configure("sync", foreground="#4ecca3")

    def update_activity_log(self, entries):
        """Populate the activity log table.
        *entries* is a list of dicts with keys: hash, date, author, action, message."""
        self.activity_tree.delete(*self.activity_tree.get_children())
        for entry in entries:
            action = entry.get("action", "commit")
            action_display = action.capitalize()
            self.activity_tree.insert(
                "", "end",
                values=(
                    entry.get("date", ""),
                    action_display,
                    entry.get("author", ""),
                    entry.get("hash", ""),
                    entry.get("message", ""),
                ),
                tags=(action,),
            )
        count = len(entries)
        self.activity_status_label.config(
            text=f"{count} activit{'y' if count == 1 else 'ies'} found" if count else "No activity found"
        )

    def clear_activity_log(self):
        """Clear the activity log table."""
        self.activity_tree.delete(*self.activity_tree.get_children())
        self.activity_status_label.config(text="Select a subdomain to view activity")


    def show_dashboard(self):
        self._subdomain_hub_frame.pack_forget()
        self.subdomain_page.hide()
        self.manage_subdomain_page.hide()
        self.repo_setup_page.hide()
        self.reports_page.hide()
        self.metrics_page.hide()
        self.branch_status_page.hide()
        self._dashboard_frame.pack(fill="both", expand=True)
        self.set_active_nav("dashboard")
        self.current_page = "dashboard"
        self.set_page_title("Dashboard")

        self._dashboard_canvas.bind_all("<MouseWheel>", self._on_dashboard_scroll)

    def show_subdomain_hub(self, tab="add"):
        self._dashboard_frame.pack_forget()
        self.repo_setup_page.hide()
        self.branch_status_page.hide()
        self.metrics_page.hide()
        self._subdomain_hub_frame.pack(fill="both", expand=True)
        self.set_active_nav("subdomains")
        self.current_page = "subdomains"
        self._set_subdomain_tab(tab)

        self._dashboard_canvas.unbind_all("<MouseWheel>")

    def show_subdomain_page(self):
        self.show_subdomain_hub(tab="add")

    def show_manage_subdomain_page(self):
        self.show_subdomain_hub(tab="manage")

    def show_repo_setup_page(self):
        self._dashboard_frame.pack_forget()
        self._subdomain_hub_frame.pack_forget()
        self.subdomain_page.hide()
        self.manage_subdomain_page.hide()
        self.reports_page.hide()
        self.metrics_page.hide()
        self.branch_status_page.hide()
        self.repo_setup_page.show()
        self.set_active_nav("repo_setup")
        self.current_page = "repo_setup"
        self.set_page_title("Repo Setup")

        self._dashboard_canvas.unbind_all("<MouseWheel>")

    def show_reports_page(self):
        self.show_subdomain_hub(tab="reports")

    def show_branch_status_page(self):
        self._dashboard_frame.pack_forget()
        self._subdomain_hub_frame.pack_forget()
        self.subdomain_page.hide()
        self.manage_subdomain_page.hide()
        self.repo_setup_page.hide()
        self.reports_page.hide()
        self.metrics_page.hide()
        self.branch_status_page.show()
        self.set_active_nav("branch_status")
        self.current_page = "branch_status"
        self.set_page_title("Branch Status")
        self._dashboard_canvas.unbind_all("<MouseWheel>")

    def show_metrics_page(self):
        self._dashboard_frame.pack_forget()
        self._subdomain_hub_frame.pack_forget()
        self.subdomain_page.hide()
        self.manage_subdomain_page.hide()
        self.repo_setup_page.hide()
        self.reports_page.hide()
        self.branch_status_page.hide()
        self.metrics_page.show()
        self.set_active_nav("metrics")
        self.current_page = "metrics"
        self.set_page_title("Subdomain Metrics")
        self._dashboard_canvas.unbind_all("<MouseWheel>")

    def _on_dashboard_scroll(self, event):
        """Handle mousewheel scrolling for dashboard canvas."""
        widget = getattr(event, "widget", None)
        focus_widget = self.root.focus_get() if hasattr(self, "root") else None

        def _class_name(w):
            try:
                return w.winfo_class()
            except Exception:
                return ""

        widget_class = _class_name(widget)
        focus_class = _class_name(focus_widget)

        # Let combobox popdowns and other direct input widgets consume wheel events.
        skip_classes = {
            "TCombobox",
            "Combobox",
            "Listbox",
            "Entry",
            "Text",
            "Treeview",
        }
        if widget_class in skip_classes or focus_class in skip_classes:
            return

        self._dashboard_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


    def update_status_chip(self, text, bg_color=None, fg_color=None):
        if bg_color:
            self.status_chip.config(bg=bg_color)
        if fg_color:
            self.status_chip.config(fg=fg_color)
        self.status_chip.config(text=text)

    def set_page_title(self, text):
        self.page_title_var.set(text)

    def update_stats(self, registered, unregistered, vultr):
        self.stats_chart.draw(registered, unregistered, vultr)

    def log(self, message, tag="info"):
        """Write to the subdomain page activity log."""
        self.subdomain_page.log(message, tag)

    def clear_log(self):
        self.subdomain_page.clear_log()