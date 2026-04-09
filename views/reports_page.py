"""
Reports Page View — lists all generated PDF reports with subdomain name,
generation date, file size, and actions (open / delete).
Includes an embedded PDF preview panel.
"""
import os
import re
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

from models.config import COLORS, HAS_PYMUPDF
from models.paths import get_reports_dir, open_path_cross_platform
from views.widgets import ModernButton, RoundedFrame

if HAS_PYMUPDF:
    import fitz
    from PIL import Image, ImageTk

REPORTS_DIR = get_reports_dir()


def _create_label(parent, text, font_size=10, bold=False, color="text_secondary"):
    weight = "bold" if bold else "normal"
    return tk.Label(
        parent, text=text,
        font=("Segoe UI", font_size, weight),
        bg=parent.cget("bg"), fg=COLORS[color],
    )


class ReportsPageView:
    """Self-contained page frame that lists all generated PDF reports."""

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])
        self._current_pdf = None
        self._current_page = 0
        self._total_pages = 0
        self._preview_images = []
        self._sort_column = "date"
        self._sort_desc = True
        self._sort_labels = {
            "subdomain": "Subdomain",
            "date": "Date",
            "size": "Size",
            "status": "Status",
        }
        self._build()


    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_bar, text="Generated Reports",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")


        btn_frame = tk.Frame(title_bar, bg=COLORS["bg_primary"])
        btn_frame.pack(side="right")

        self.export_dns_btn = ModernButton(
            btn_frame, text="Export DNS CSV", command=None,
            bg_color="#43A047", hover_color="#388E3C", border_color="#2E7D32",
            width=130, height=28,
        )
        self.export_dns_btn.pack(side="left", padx=(0, 8))

        self.export_activity_btn = ModernButton(
            btn_frame, text="Export Activity CSV", command=None,
            bg_color="#7B1FA2", hover_color="#6A1B9A", border_color="#4A148C",
            width=150, height=28,
        )
        self.export_activity_btn.pack(side="left", padx=(0, 8))

        self.refresh_btn = ModernButton(
            btn_frame, text="Refresh", command=None,
            bg_color="#0288D1", hover_color="#0277BD", border_color="#01579B",
            width=100, height=28,
        )
        self.refresh_btn.pack(side="left")


        filter_frame = tk.Frame(container, bg=COLORS["bg_secondary"], padx=12, pady=8)
        filter_frame.pack(fill="x", pady=(0, 8))

        tk.Label(
            filter_frame, text="Filter:",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(side="left")

        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(
            filter_frame, textvariable=self.filter_var,
            font=("Segoe UI", 9), width=30,
        )
        filter_entry.pack(side="left", padx=(6, 12))


        self.count_label = tk.Label(
            filter_frame, text="0 reports",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self.count_label.pack(side="right")


        content_pane = tk.PanedWindow(
            container, orient=tk.HORIZONTAL,
            bg=COLORS["bg_primary"], sashwidth=6, sashrelief=tk.FLAT,
        )
        content_pane.pack(fill="both", expand=True, pady=(0, 8))


        left_frame = tk.Frame(content_pane, bg=COLORS["bg_primary"])
        self._build_reports_table(left_frame)
        content_pane.add(left_frame, minsize=350, stretch="always")


        right_frame = tk.Frame(content_pane, bg=COLORS["bg_primary"])
        self._build_preview_panel(right_frame)
        content_pane.add(right_frame, minsize=300, stretch="always")


        info_bar = tk.Frame(container, bg=COLORS["bg_secondary"], padx=12, pady=6)
        info_bar.pack(fill="x")

        self.info_label = tk.Label(
            info_bar,
            text="Select a report to preview. Double-click to open externally.",
            font=("Segoe UI", 8, "italic"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self.info_label.pack(side="left")

        self.total_size_label = tk.Label(
            info_bar, text="Total: 0 KB",
            font=("Segoe UI", 8, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        )
        self.total_size_label.pack(side="right")

    def _build_reports_table(self, parent):
        """Build the reports table (left pane)."""
        table_frame = RoundedFrame(
            parent, bg_color=COLORS["bg_accent"],
            radius=12, padding=(10, 10),
        )
        table_frame.pack(fill="both", expand=True)

        inner = table_frame.inner
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(0, weight=1)


        style = ttk.Style()
        style.configure(
            "Reports.Treeview",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_accent"],
            font=("Segoe UI", 9),
            rowheight=28,
        )
        style.configure(
            "Reports.Treeview.Heading",
            background=COLORS["bg_secondary"],
            foreground=COLORS["text_primary"],
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Reports.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", "#ffffff")],
        )

        tree_container = tk.Frame(inner, bg=COLORS["bg_accent"])
        tree_container.grid(row=0, column=0, sticky="nsew")

        columns = ("subdomain", "date", "size", "status")
        self.reports_tree = ttk.Treeview(
            tree_container, columns=columns, show="headings",
            style="Reports.Treeview", height=12,
        )

        self.reports_tree.heading("subdomain", text="Subdomain", command=lambda: self._toggle_sort("subdomain"))
        self.reports_tree.heading("date", text="Date", command=lambda: self._toggle_sort("date"))
        self.reports_tree.heading("size", text="Size", command=lambda: self._toggle_sort("size"))
        self.reports_tree.heading("status", text="Status", command=lambda: self._toggle_sort("status"))

        self.reports_tree.column("subdomain", width=150, minwidth=100)
        self.reports_tree.column("date", width=140, minwidth=100, anchor="center")
        self.reports_tree.column("size", width=60, minwidth=50, anchor="center")
        self.reports_tree.column("status", width=70, minwidth=50, anchor="center")

        scrollbar = ttk.Scrollbar(
            tree_container, orient="vertical",
            command=self.reports_tree.yview,
        )
        self.reports_tree.configure(yscrollcommand=scrollbar.set)

        self.reports_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


        self.reports_tree.tag_configure("recent", foreground=COLORS["success"])
        self.reports_tree.tag_configure("old", foreground=COLORS["text_secondary"])
        self.reports_tree.tag_configure("zebra_even", background=COLORS["bg_accent"])
        self.reports_tree.tag_configure("zebra_odd", background=COLORS["bg_secondary"])
        self.reports_tree.tag_configure("empty", foreground=COLORS["text_secondary"])


        self.reports_tree.bind("<<TreeviewSelect>>", self._on_report_selected)
        self._refresh_sort_headings()

    def _toggle_sort(self, column):
        """Toggle sort settings and reload reports."""
        if self._sort_column == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = column
            self._sort_desc = False if column in ("subdomain", "status") else True

        self._refresh_sort_headings()
        self.load_reports(self.filter_var.get().strip())

    def _refresh_sort_headings(self):
        """Refresh heading labels with sort indicators."""
        for col, label in self._sort_labels.items():
            marker = ""
            if col == self._sort_column:
                marker = " ▼" if self._sort_desc else " ▲"
            self.reports_tree.heading(col, text=f"{label}{marker}")

    def _build_preview_panel(self, parent):
        """Build the PDF preview panel (right pane)."""
        preview_card = RoundedFrame(
            parent, bg_color=COLORS["bg_accent"],
            radius=12, padding=(10, 10),
        )
        preview_card.pack(fill="both", expand=True)

        inner = preview_card.inner
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(1, weight=1)


        header = tk.Frame(inner, bg=COLORS["bg_accent"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.preview_title = tk.Label(
            header, text="PDF Preview",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
        )
        self.preview_title.pack(side="left")


        nav_frame = tk.Frame(header, bg=COLORS["bg_accent"])
        nav_frame.pack(side="right")

        self.prev_page_btn = ModernButton(
            nav_frame, text="◀", command=self._prev_page,
            bg_color=COLORS["bg_secondary"], hover_color="#0a2a4a",
            border_color="#0a2540", width=32, height=24,
        )
        self.prev_page_btn.pack(side="left", padx=(0, 4))

        self.page_label = tk.Label(
            nav_frame, text="0 / 0",
            font=("Segoe UI", 9),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
            width=8,
        )
        self.page_label.pack(side="left", padx=4)

        self.next_page_btn = ModernButton(
            nav_frame, text="▶", command=self._next_page,
            bg_color=COLORS["bg_secondary"], hover_color="#0a2a4a",
            border_color="#0a2540", width=32, height=24,
        )
        self.next_page_btn.pack(side="left", padx=(4, 0))

        self.open_external_btn = ModernButton(
            nav_frame, text="Open", command=self._open_external,
            bg_color="#F57C00", hover_color="#ff8c00",
            border_color="#cc6600", width=60, height=24,
        )
        self.open_external_btn.pack(side="left", padx=(12, 0))


        canvas_frame = tk.Frame(inner, bg=COLORS["bg_secondary"])
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            canvas_frame, bg=COLORS["bg_secondary"],
            highlightthickness=0, bd=0,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew")

        preview_scrollbar = ttk.Scrollbar(
            canvas_frame, orient="vertical",
            command=self.preview_canvas.yview,
        )
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_canvas.configure(yscrollcommand=preview_scrollbar.set)


        self._show_preview_placeholder()

    def _show_preview_placeholder(self, message="Select a report to preview"):
        """Show placeholder text in preview area."""
        self.preview_canvas.delete("all")
        self.preview_canvas.update_idletasks()
        w = self.preview_canvas.winfo_width() or 300
        h = self.preview_canvas.winfo_height() or 400
        self.preview_canvas.create_text(
            w // 2, h // 2,
            text=message,
            font=("Segoe UI", 11),
            fill=COLORS["text_secondary"],
            anchor="center",
        )
        self.page_label.config(text="0 / 0")

    def _on_report_selected(self, event=None):
        """Handle report selection — load preview."""
        filepath = self.get_selected_report()
        if filepath and os.path.isfile(filepath):
            self._load_pdf_preview(filepath)
        else:
            self._show_preview_placeholder()

    def _load_pdf_preview(self, filepath):
        """Load and display the first page of the PDF."""
        if not HAS_PYMUPDF:
            self._show_preview_placeholder("PDF preview requires PyMuPDF.\nInstall with: pip install PyMuPDF")
            return

        try:
            doc = fitz.open(filepath)
            self._current_pdf = filepath
            self._total_pages = len(doc)
            self._current_page = 0


            filename = os.path.basename(filepath)
            self.preview_title.config(text=filename[:30] + "..." if len(filename) > 30 else filename)

            self._render_page(doc, 0)
            doc.close()
        except Exception as e:
            self._show_preview_placeholder(f"Error loading PDF:\n{e}")

    def _render_page(self, doc_or_path, page_num):
        """Render a specific page of the PDF."""
        if not HAS_PYMUPDF:
            return

        try:
            if isinstance(doc_or_path, str):
                doc = fitz.open(doc_or_path)
                close_doc = True
            else:
                doc = doc_or_path
                close_doc = False

            if page_num < 0 or page_num >= len(doc):
                return

            page = doc[page_num]


            self.preview_canvas.update_idletasks()
            canvas_width = self.preview_canvas.winfo_width() or 300


            rect = page.rect
            zoom = (canvas_width - 20) / rect.width
            zoom = min(zoom, 2.0)

            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)


            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            photo = ImageTk.PhotoImage(img)


            self._preview_images = [photo]


            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                (canvas_width // 2), 10,
                image=photo, anchor="n",
            )
            self.preview_canvas.configure(scrollregion=(0, 0, canvas_width, pix.height + 20))


            self.page_label.config(text=f"{page_num + 1} / {len(doc)}")

            if close_doc:
                doc.close()

        except Exception as e:
            self._show_preview_placeholder(f"Render error:\n{e}")

    def _prev_page(self):
        """Go to previous page."""
        if self._current_pdf and self._current_page > 0:
            self._current_page -= 1
            self._render_page(self._current_pdf, self._current_page)

    def _next_page(self):
        """Go to next page."""
        if self._current_pdf and self._current_page < self._total_pages - 1:
            self._current_page += 1
            self._render_page(self._current_pdf, self._current_page)

    def _open_external(self):
        """Open current PDF in external viewer."""
        if self._current_pdf and os.path.isfile(self._current_pdf):
            open_path_cross_platform(self._current_pdf)


    def load_reports(self, filter_text=""):
        """Scan the reports/ directory and populate the table."""
        previous_selection = self.get_selected_report()
        self.reports_tree.delete(*self.reports_tree.get_children())

        if not os.path.isdir(REPORTS_DIR):
            self.reports_tree.insert(
                "", "end", iid="__empty__",
                values=("No reports found", "-", "-", "-"),
                tags=("empty",),
            )
            self.count_label.config(text="0 reports")
            self.total_size_label.config(text="Total: 0 KB")
            self._show_preview_placeholder()
            return []

        reports = []
        for filename in sorted(os.listdir(REPORTS_DIR)):
            if not filename.lower().endswith(".pdf"):
                continue

            filepath = os.path.join(REPORTS_DIR, filename)
            stat = os.stat(filepath)


            subdomain = re.sub(r"_report\.pdf$", "", filename, flags=re.IGNORECASE)
            subdomain = subdomain.replace("_", ".")


            mod_time = datetime.datetime.fromtimestamp(stat.st_mtime)
            date_str = mod_time.strftime("%Y-%m-%d %H:%M:%S")


            size_kb = stat.st_size / 1024
            if size_kb >= 1024:
                size_str = f"{size_kb / 1024:.1f} MB"
            else:
                size_str = f"{size_kb:.0f} KB"


            age_days = (datetime.datetime.now() - mod_time).days
            if age_days == 0:
                status = "Today"
                tag = "recent"
            elif age_days <= 7:
                status = f"{age_days}d ago"
                tag = "recent"
            elif age_days <= 30:
                status = f"{age_days}d ago"
                tag = "old"
            else:
                status = mod_time.strftime("%Y-%m-%d")
                tag = "old"

            reports.append({
                "subdomain": subdomain,
                "date": date_str,
                "date_epoch": stat.st_mtime,
                "size": size_str,
                "size_bytes": stat.st_size,
                "status": status,
                "filename": filename,
                "filepath": filepath,
                "tag": tag,
            })


        if filter_text:
            term = filter_text.lower()
            reports = [r for r in reports if term in r["subdomain"].lower()
                       or term in r["date"].lower()]


        if self._sort_column == "subdomain":
            sort_key = lambda r: r["subdomain"].lower()
        elif self._sort_column == "size":
            sort_key = lambda r: r["size_bytes"]
        elif self._sort_column == "status":
            sort_key = lambda r: r["status"].lower()
        else:
            sort_key = lambda r: r["date_epoch"]

        reports.sort(key=sort_key, reverse=self._sort_desc)

        for idx, r in enumerate(reports):
            zebra_tag = "zebra_even" if idx % 2 == 0 else "zebra_odd"
            self.reports_tree.insert(
                "", "end",
                iid=r["filename"],
                values=(
                    r["subdomain"],
                    r["date"],
                    r["size"],
                    r["status"],
                ),
                tags=(zebra_tag, r["tag"]),
            )

        if not reports:
            self.reports_tree.insert(
                "", "end", iid="__empty__",
                values=("No matching reports", "-", "-", "-"),
                tags=("empty",),
            )
            self._show_preview_placeholder("No reports to preview")
        elif previous_selection:
            selected_name = os.path.basename(previous_selection)
            if self.reports_tree.exists(selected_name):
                self.reports_tree.selection_set(selected_name)
                self.reports_tree.focus(selected_name)
                self.reports_tree.see(selected_name)
                self._on_report_selected()


        self.count_label.config(text=f"{len(reports)} report{'s' if len(reports) != 1 else ''}")
        total_bytes = sum(r["size_bytes"] for r in reports)
        if total_bytes >= 1024 * 1024:
            self.total_size_label.config(text=f"Total: {total_bytes / 1024 / 1024:.1f} MB")
        else:
            self.total_size_label.config(text=f"Total: {total_bytes / 1024:.0f} KB")

        return reports

    def get_selected_report(self):
        """Return the filepath of the currently selected report, or None."""
        sel = self.reports_tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if iid == "__empty__":
            return None
        return os.path.join(REPORTS_DIR, iid)

    def show(self):
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        self.frame.pack_forget()
