"""
Chart rendering — overview doughnut and per-subdomain bar chart.
"""
from models.config import COLORS, HAS_MATPLOTLIB

if HAS_MATPLOTLIB:
    import matplotlib.style as mplstyle
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure


class ChartManager:
    """Wraps all matplotlib chart drawing for the dashboard header."""


    BAR_LABELS = [
        "SSL\nDays", "Response\n(ms)", "Uptime\n(%)", "BW\n(kbps)",
        "DB\n(ms)", "CPU\n(%)", "Mem\n(%)",
    ]
    BAR_MAX_VALUES = [365, 3000, 100, 5000, 500, 100, 100]
    BAR_COLORS = {
        "ssl_valid": COLORS["ssl_valid"],
        "ssl_expired": COLORS["ssl_expired"],
        "ssl_none": COLORS["ssl_none"],
        "uptime": COLORS["uptime"],
        "success": COLORS["success"],
        "bandwidth": COLORS["bandwidth"],
        "db_speed": COLORS["db_speed"],
        "cpu": COLORS["cpu"],
        "memory": COLORS["memory"],
    }


    def __init__(self, parent_frame):
        """
        *parent_frame* is the tk Frame where the chart will be placed.
        After init, ``self.chart_canvas`` is either a matplotlib canvas
        or a plain tk.Canvas fallback.
        """
        import tkinter as tk

        self.parent = parent_frame
        self.fig = None
        self.ax = None

        if HAS_MATPLOTLIB:
            mplstyle.use("default")

            self.fig = Figure(figsize=(5.8, 3.8), dpi=100, facecolor=COLORS["bg_accent"])
            self.ax = self.fig.add_subplot(111)
            self.wedges = None
            self._wedge_labels = []
            self._hover_annot = None
            self._last_hover_idx = None
            self.chart_canvas = FigureCanvasTkAgg(self.fig, parent_frame)
            self.chart_canvas.get_tk_widget().pack(fill="both", expand=True)
            self.setup_chart_style()

            self.fig.canvas.mpl_connect("motion_notify_event", self._on_hover)
        else:
            self.chart_canvas = tk.Canvas(
                parent_frame,
                bg=COLORS["bg_primary"],
                height=140,
                highlightthickness=1,
                highlightbackground=COLORS["text_secondary"],
            )
            self.chart_canvas.pack(fill="both", expand=True, pady=(6, 0))


    def _get_bar_colors(self, metrics):
        """Get colors for bar chart based on metrics."""
        ssl_status = metrics.get("ssl_status", "Unknown")
        ssl_color = self.BAR_COLORS["ssl_valid"] if ssl_status == "Valid" else (
            self.BAR_COLORS["ssl_expired"] if ssl_status == "Expired" else self.BAR_COLORS["ssl_none"]
        )
        return [
            ssl_color,
            self.BAR_COLORS["uptime"],
            self.BAR_COLORS["success"],
            self.BAR_COLORS["bandwidth"],
            self.BAR_COLORS["db_speed"],
            self.BAR_COLORS["cpu"],
            self.BAR_COLORS["memory"],
        ]

    def _get_raw_metrics(self, metrics):
        """Extract raw metric values from metrics dict."""
        return [
            metrics.get("ssl_expiry_days", 0),
            metrics.get("response_time_ms", 0),
            metrics.get("uptime_pct", 0),
            metrics.get("bandwidth_kbps", 0),
            metrics.get("db_speed_ms", 0),
            metrics.get("cpu_pct", 0),
            metrics.get("memory_pct", 0),
        ]

    def _configure_bar_chart_axes(self):
        """Configure bar chart axes and styling."""
        self.ax.set_xticks(range(len(self.BAR_LABELS)))
        self.ax.set_xticklabels(self.BAR_LABELS, fontsize=8, color=COLORS["text_secondary"])
        self.ax.set_yticks([])
        self.ax.set_ylim(0, 115)
        for spine in ("top", "right", "left"):
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["bottom"].set_color(COLORS["text_secondary"])
        self.ax.tick_params(axis="x", colors=COLORS["text_secondary"], length=0)

    def _create_bar_hover_annotation(self):
        """Create hover annotation for bar chart."""
        annot = self.ax.annotate(
            "", xy=(0, 0),
            fontsize=9, fontweight="bold",
            color=COLORS["text_primary"],
            ha="center", va="center",
            bbox=dict(
                boxstyle="round,pad=0.4",
                fc=COLORS["bg_secondary"],
                ec=COLORS["accent"],
                lw=1.5,
                alpha=0.95,
            ),
        )
        annot.set_visible(False)
        return annot


    def setup_chart_style(self):
        if not HAS_MATPLOTLIB or not self.ax:
            return
        self.ax.set_facecolor(COLORS["bg_accent"])
        self.fig.patch.set_facecolor(COLORS["bg_accent"])
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        self.ax.set_aspect("equal")

        self.fig.subplots_adjust(left=0.06, right=0.74, top=0.89, bottom=0.11)

    def _tighten_layout(self):
        """Apply consistent tight layout with small padding."""
        if HAS_MATPLOTLIB and self.fig:
            self.fig.tight_layout(pad=0.7)

    def _on_hover(self, event):
        """Show tooltip when hovering over a doughnut wedge or bar chart bar."""

        if hasattr(self, '_bar_data') and self._bar_data:

            self._on_bar_hover(event)
            return


        if not self.wedges or not self._hover_annot or event.inaxes != self.ax:
            if self._hover_annot and self._hover_annot.get_visible():
                self._hover_annot.set_visible(False)
                self._last_hover_idx = None
                self.chart_canvas.draw_idle()
            return

        for i, wedge in enumerate(self.wedges):
            hit, _ = wedge.contains(event)
            if hit:
                if self._last_hover_idx == i:
                    return

                import math
                theta1 = math.radians(wedge.theta1)
                theta2 = math.radians(wedge.theta2)
                mid = (theta1 + theta2) / 2
                r = 0.7
                x = r * math.cos(mid)
                y = r * math.sin(mid)
                self._hover_annot.xy = (x, y)
                self._hover_annot.set_text(self._wedge_labels[i])
                self._hover_annot.set_visible(True)
                self._last_hover_idx = i
                self.chart_canvas.draw_idle()
                return


        if self._hover_annot.get_visible():
            self._hover_annot.set_visible(False)
            self._last_hover_idx = None
            self.chart_canvas.draw_idle()


    def show_loading(self, domain):
        if not HAS_MATPLOTLIB or not self.ax:
            return
        self.ax.clear()
        self.setup_chart_style()
        self.ax.text(
            0.5, 0.5, f"Loading metrics\nfor {domain}...",
            ha="center", va="center", fontsize=11,
            color=COLORS["text_secondary"],
            transform=self.ax.transAxes,
        )
        self.ax.set_title(
            "Fetching...", color=COLORS["text_primary"],
            fontsize=11, fontweight="bold", pad=14,
        )
        self._tighten_layout()
        self.chart_canvas.draw()


    def draw_subdomain_metrics(self, domain, metrics):
        if not HAS_MATPLOTLIB or not self.ax:
            return

        self.ax.clear()
        self.ax.set_facecolor(COLORS["bg_accent"])
        self.fig.patch.set_facecolor(COLORS["bg_accent"])
        self.ax.set_aspect("auto")

        self.fig.subplots_adjust(left=0.11, right=0.97, top=0.86, bottom=0.24)

        labels = [
            "SSL\nDays", "Response\n(ms)", "Uptime\n(%)", "BW\n(kbps)",
            "DB\n(ms)", "CPU\n(%)", "Mem\n(%)",
        ]
        raw = [
            metrics["ssl_expiry_days"],
            metrics["response_time_ms"],
            metrics["uptime_pct"],
            metrics["bandwidth_kbps"],
            metrics["db_speed_ms"],
            metrics["cpu_pct"],
            metrics["memory_pct"],
        ]
        bar_colors = [
            COLORS["ssl_valid"] if metrics["ssl_status"] == "Valid"
            else (COLORS["ssl_expired"] if metrics["ssl_status"] == "Expired" else COLORS["ssl_none"]),
            COLORS["uptime"],
            COLORS["success"],
            COLORS["bandwidth"],
            COLORS["db_speed"],
            COLORS["cpu"],
            COLORS["memory"],
        ]

        max_vals = [365, 3000, 100, 5000, 500, 100, 100]
        normed = [min(v / m * 100, 100) if m else 0 for v, m in zip(raw, max_vals)]

        x_pos = range(len(labels))
        bars = self.ax.bar(
            x_pos, normed, color=bar_colors, width=0.55,
            edgecolor="#0f0f0f", linewidth=0.8, zorder=3,
        )


        self._bar_data = []
        for i, (bar, val, label) in enumerate(zip(bars, raw, labels)):
            display = f"{val:g}" if isinstance(val, float) else str(val)
            self.ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                display, ha="center", va="bottom", fontsize=8,
                color=COLORS["text_primary"], fontweight="bold",
            )

            self._bar_data.append({
                'bar': bar,
                'value': val,
                'label': label.replace('\n', ' '),
                'max': max_vals[i],
            })


        self._bar_hover_annot = self.ax.annotate(
            "", xy=(0, 0),
            fontsize=9, fontweight="bold",
            color=COLORS["text_primary"],
            ha="center", va="center",
            bbox=dict(
                boxstyle="round,pad=0.4",
                fc=COLORS["bg_secondary"],
                ec=COLORS["accent"],
                lw=1.5,
                alpha=0.95,
            ),
        )
        self._bar_hover_annot.set_visible(False)
        self._last_hover_bar = None

        self.ax.set_xticks(x_pos)
        self.ax.set_xticklabels(labels, fontsize=8, color=COLORS["text_secondary"])
        self.ax.set_yticks([])
        self.ax.set_ylim(0, 115)
        for spine in ("top", "right", "left"):
            self.ax.spines[spine].set_visible(False)
        self.ax.spines["bottom"].set_color(COLORS["text_secondary"])
        self.ax.tick_params(axis="x", colors=COLORS["text_secondary"], length=0)

        ssl_badge = metrics["ssl_status"]
        self.ax.set_title(
            f"{domain}   [SSL: {ssl_badge}]",
            color=COLORS["text_primary"], fontsize=11, fontweight="bold", pad=14,
        )

        self._tighten_layout()
        self.chart_canvas.draw()

    def _on_bar_hover(self, event):
        """Show detailed tooltip when hovering over a bar in the bar chart.
        Tooltip appears at top-right corner of the chart."""
        if not hasattr(self, '_bar_data') or not self._bar_hover_annot:
            return

        if event.inaxes != self.ax:
            if self._bar_hover_annot.get_visible():
                self._bar_hover_annot.set_visible(False)
                self._last_hover_bar = None
                self.chart_canvas.draw_idle()
            return


        for i, data in enumerate(self._bar_data):
            bar = data['bar']
            x = bar.get_x()
            width = bar.get_width()
            height = bar.get_height()

            if x <= event.xdata <= x + width and 0 <= event.ydata <= height:
                if self._last_hover_bar == i:
                    return

                value = data['value']
                label = data['label']
                max_val = data['max']

                if label == "SSL Days":
                    status = "Valid" if value > 30 else ("Expiring" if value > 0 else "Expired")
                    tooltip = f"SSL: {value} days\nStatus: {status}"
                elif label == "Response (ms)":
                    status = "Good" if value < 500 else ("Slow" if value < 2000 else "Very Slow")
                    tooltip = f"Response: {value} ms\nStatus: {status}"
                elif label == "Uptime (%)":
                    status = "Excellent" if value >= 99 else ("Good" if value >= 95 else "Poor")
                    tooltip = f"Uptime: {value}%\nStatus: {status}"
                elif label == "BW (kbps)":
                    tooltip = f"Bandwidth: {value} kbps\nMax scale: {max_val} kbps"
                elif label == "DB (ms)":
                    status = "Fast" if value < 100 else ("Slow" if value < 300 else "Very Slow")
                    tooltip = f"DB Speed: {value} ms\nStatus: {status}"
                elif label == "CPU (%)":
                    status = "Normal" if value < 50 else ("High" if value < 80 else "Critical")
                    tooltip = f"CPU: {value}%\nStatus: {status}"
                elif label == "Mem (%)":
                    status = "Normal" if value < 60 else ("High" if value < 85 else "Critical")
                    tooltip = f"Memory: {value}%\nStatus: {status}"
                else:
                    tooltip = f"{label}: {value}"


                self._bar_hover_annot.xy = (0.98, 0.98)
                self._bar_hover_annot.xycoords = 'axes fraction'
                self._bar_hover_annot.set_text(tooltip)
                self._bar_hover_annot.set_visible(True)
                self._last_hover_bar = i
                self.chart_canvas.draw_idle()
                return


        if self._bar_hover_annot.get_visible():
            self._bar_hover_annot.set_visible(False)
            self._last_hover_bar = None
            self.chart_canvas.draw_idle()


    def draw_overview(self, registered_count, unregistered_count):
        total_count = registered_count + unregistered_count

        if HAS_MATPLOTLIB and self.ax:
            self.ax.clear()
            self.setup_chart_style()
            self._hover_annot = None
            self._last_hover_idx = None

            self._bar_data = []
            self._bar_hover_annot = None
            self._last_hover_bar = None
            self.fig.subplots_adjust(left=0.05, right=0.95, top=0.90, bottom=0.08)

            if total_count == 0:
                labels, values, colors = ["No Subdomains"], [1], [COLORS["bg_secondary"]]
                self._wedge_labels = ["No data available"]
            elif registered_count > 0 and unregistered_count > 0:
                labels, values = ["", ""], [registered_count, unregistered_count]
                colors = [COLORS["success_light"], COLORS["unregistered_light"]]
                self._wedge_labels = [
                    f"Registered: {registered_count}",
                    f"Unregistered: {unregistered_count}",
                ]
            elif registered_count > 0:
                labels, values = [""], [registered_count]
                colors = [COLORS["success_light"]]
                self._wedge_labels = [f"Registered: {registered_count}"]
            else:
                labels, values = [""], [unregistered_count]
                colors = [COLORS["unregistered_light"]]
                self._wedge_labels = [f"Unregistered: {unregistered_count}"]

            wedges, _ = self.ax.pie(
                values, labels=labels, colors=colors,
                startangle=90, counterclock=False,
                wedgeprops=dict(width=0.6, edgecolor="#0f0f0f", linewidth=4),
                labeldistance=None,
            )
            self.wedges = wedges


            self._hover_annot = self.ax.annotate(
                "", xy=(0, 0),
                fontsize=10, fontweight="bold",
                color=COLORS["text_primary"],
                ha="center", va="center",
                bbox=dict(
                    boxstyle="round,pad=0.4",
                    fc=COLORS["bg_secondary"],
                    ec=COLORS["accent"],
                    lw=1.5,
                    alpha=0.95,
                ),
            )
            self._hover_annot.set_visible(False)

            chart_title = "Subdomain Overview" if total_count > 0 else "No Subdomains"
            self.ax.set_title(
                chart_title, color=COLORS["text_primary"],
                fontsize=12, fontweight="bold", pad=16,
            )

            self.chart_canvas.draw()
        else:

            self.chart_canvas.delete("all")
            canvas_width = self.chart_canvas.winfo_width()
            canvas_height = self.chart_canvas.winfo_height()
            if canvas_width <= 1:
                return

            padding = 8
            bar_height = 12
            bar_y = (canvas_height - bar_height) // 2
            max_display = max(total_count, 10)
            bg_bar_width = canvas_width - 2 * padding

            self.chart_canvas.create_rectangle(
                padding, bar_y,
                padding + bg_bar_width, bar_y + bar_height,
                fill=COLORS["bg_secondary"], outline=COLORS["text_secondary"], width=1,
            )

            if total_count > 0:
                reg_width = int(bg_bar_width * min(registered_count / max_display, 1.0))
                if reg_width > 0:
                    self.chart_canvas.create_rectangle(
                        padding + 1, bar_y + 1,
                        padding + reg_width, bar_y + bar_height - 1,
                        fill=COLORS["success_light"], outline="",
                    )
                unreg_width = int(bg_bar_width * min(unregistered_count / max_display, 1.0))
                if unreg_width > 0:
                    self.chart_canvas.create_rectangle(
                        padding + reg_width + 1, bar_y + 1,
                        padding + reg_width + unreg_width, bar_y + bar_height - 1,
                        fill=COLORS["unregistered_light"], outline="",
                    )


class StatsPieChart:
    """Small pie chart showing subdomain category breakdown."""

    def __init__(self, parent_frame):
        import tkinter as tk

        self.parent = parent_frame
        self.fig = None
        self.ax = None
        self.wedges = None
        self._wedge_labels = []
        self._hover_annot = None
        self._last_hover_idx = None

        if HAS_MATPLOTLIB:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from matplotlib.figure import Figure


            self.fig = Figure(figsize=(4.2, 4.2), dpi=100, facecolor=COLORS["bg_accent"])
            self.ax = self.fig.add_subplot(111)
            self.canvas = FigureCanvasTkAgg(self.fig, parent_frame)
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self._setup()
            self.fig.canvas.mpl_connect("motion_notify_event", self._on_hover)
        else:
            self.canvas = tk.Canvas(
                parent_frame, bg=COLORS["bg_primary"],
                height=140, highlightthickness=0,
            )
            self.canvas.pack(fill="both", expand=True)

    def _setup(self):
        if not self.ax:
            return
        self.ax.set_facecolor(COLORS["bg_accent"])
        self.fig.patch.set_facecolor(COLORS["bg_accent"])
        self.ax.set_aspect("equal")
        self.fig.subplots_adjust(left=0.04, right=0.96, top=0.89, bottom=0.18)

    def _tighten_layout(self):
        if HAS_MATPLOTLIB and self.fig:
            self.fig.tight_layout(pad=0.7)

    def _on_hover(self, event):
        """Show tooltip when hovering over a pie wedge."""
        if not self.wedges or not self._hover_annot or event.inaxes != self.ax:
            if self._hover_annot and self._hover_annot.get_visible():
                self._hover_annot.set_visible(False)
                self._last_hover_idx = None
                self.canvas.draw_idle()
            return

        for i, wedge in enumerate(self.wedges):
            hit, _ = wedge.contains(event)
            if hit:
                if self._last_hover_idx == i:
                    return
                import math
                theta1 = math.radians(wedge.theta1)
                theta2 = math.radians(wedge.theta2)
                mid = (theta1 + theta2) / 2
                r = 0.7
                x = r * math.cos(mid)
                y = r * math.sin(mid)
                self._hover_annot.xy = (x, y)
                self._hover_annot.set_text(self._wedge_labels[i])
                self._hover_annot.set_visible(True)
                self._last_hover_idx = i
                self.canvas.draw_idle()
                return

        if self._hover_annot.get_visible():
            self._hover_annot.set_visible(False)
            self._last_hover_idx = None
            self.canvas.draw_idle()

    def draw(self, registered, unregistered, vultr):
        """Redraw the stats pie chart with current counts."""
        if not HAS_MATPLOTLIB or not self.ax:
            return

        self.ax.clear()
        self._setup()
        self._hover_annot = None
        self._last_hover_idx = None

        total = registered + unregistered + vultr
        if total == 0:
            self.ax.text(
                0.5, 0.5, "No Data",
                ha="center", va="center", fontsize=11,
                color=COLORS["text_secondary"],
                transform=self.ax.transAxes,
            )
            self.ax.set_title(
                "Stats", color=COLORS["text_primary"],
                fontsize=11, fontweight="bold", pad=12,
            )
            self._tighten_layout()
            self.canvas.draw()
            return

        values, labels, colors = [], [], []
        self._wedge_labels = []
        if registered > 0:
            values.append(registered)
            labels.append(f"Registered ({registered})")
            colors.append(COLORS["success"])
            self._wedge_labels.append(f"Registered: {registered}")
        if unregistered > 0:
            values.append(unregistered)
            labels.append(f"Unregistered ({unregistered})")
            colors.append(COLORS["unregistered_light"])
            self._wedge_labels.append(f"Unregistered: {unregistered}")
        if vultr > 0:
            values.append(vultr)
            labels.append(f"Vultr ({vultr})")
            colors.append(COLORS["uptime"])
            self._wedge_labels.append(f"Vultr: {vultr}")

        wedges, texts, autotexts = self.ax.pie(
            values, colors=colors,
            startangle=90, counterclock=False,
            wedgeprops=dict(width=0.55, edgecolor="white", linewidth=2),
            autopct=lambda p: f"{p:.0f}%" if p >= 8 else "",
            pctdistance=0.72,
        )
        self.wedges = wedges
        for t in autotexts:
            t.set_color(COLORS["text_primary"])
            t.set_fontsize(8.5)
            t.set_fontweight("bold")


        self._hover_annot = self.ax.annotate(
            "", xy=(0, 0),
            fontsize=10, fontweight="bold",
            color=COLORS["text_primary"],
            ha="center", va="center",
            bbox=dict(
                boxstyle="round,pad=0.4",
                fc=COLORS["bg_secondary"],
                ec=COLORS["accent"],
                lw=1.5,
                alpha=0.95,
            ),
        )
        self._hover_annot.set_visible(False)

        self.ax.set_title(
            f"Subdomain Stats ({total})",
            color=COLORS["text_primary"],
            fontsize=11, fontweight="bold", pad=12,
        )

        self._tighten_layout()
        self.canvas.draw()