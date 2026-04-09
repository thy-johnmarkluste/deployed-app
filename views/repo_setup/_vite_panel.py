"""
Repository Setup Page — Vite database setup panel (toggle, content, config getters).
"""
import tkinter as tk
from tkinter import filedialog

from models.config import COLORS
from views.repo_setup._helpers import _create_label


class VitePanelMixin:
    """Vite database setup panel: toggle, DB config form, SQL import, action buttons."""

    def _rebuild_vite_db_panel(self):
        """Show/hide the Vite Database Setup panel based on framework selection."""
        for w in self._vite_db_widgets:
            w.destroy()
        self._vite_db_widgets.clear()

        framework = self.framework_var.get()
        if framework != "Vite (Modern Frontend)":
            self._vite_db_frame.pack_forget()
            return

        self._vite_db_frame.pack(fill="x", pady=(10, 0))


        toggle_row = tk.Frame(self._vite_db_frame, bg=COLORS["bg_secondary"])
        toggle_row.pack(fill="x")
        self._vite_db_widgets.append(toggle_row)

        self._vite_db_expanded = False
        self._vite_db_content_frame = tk.Frame(self._vite_db_frame, bg=COLORS["bg_secondary"])
        self._vite_db_widgets.append(self._vite_db_content_frame)

        def _toggle():
            self._vite_db_expanded = not self._vite_db_expanded
            if self._vite_db_expanded:
                toggle_btn.configure(text="\u25BC  Database Setup  \u25BC",
                                     bg="#1565C0", activebackground="#1256A8")
                self._vite_db_content_frame.pack(fill="x", pady=(6, 0))
                self._build_vite_db_content()
            else:
                toggle_btn.configure(text="\u25B6  Database Setup (optional)",
                                     bg=COLORS["bg_accent"], activebackground="#0a2a4a")
                for child in self._vite_db_content_frame.winfo_children():
                    child.destroy()
                self._vite_db_content_frame.pack_forget()

        toggle_btn = tk.Button(
            toggle_row,
            text="\u25B6  Database Setup (optional)",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg="white",
            activebackground="#0a2a4a", activeforeground="white",
            anchor="w", padx=12,
            command=_toggle,
        )
        toggle_btn.pack(fill="x", ipady=6)

    def _build_vite_db_content(self):
        """Build the expandable Vite Database Setup content."""
        parent = self._vite_db_content_frame

        _create_label(
            parent,
            "Configure a MySQL database for this Vite application",
            8, False, "text_secondary",
        ).pack(anchor="w", pady=(4, 8))


        db_card = tk.Frame(parent, bg=COLORS["bg_accent"], padx=12, pady=10)
        db_card.pack(fill="x", pady=(0, 6))

        db_lbl = _create_label(db_card, "Database Credentials", 9, True, "text_primary")
        db_lbl.pack(anchor="w", pady=(0, 6))

        db_grid = tk.Frame(db_card, bg=COLORS["bg_accent"])
        db_grid.pack(fill="x")
        db_grid.columnconfigure(1, weight=1)
        db_grid.columnconfigure(3, weight=1)

        db_fields = [
            ("DB Name:",  self._vite_db_name_var, 0, 0),
            ("DB Host:",  self._vite_db_host_var, 0, 2),
            ("DB User:",  self._vite_db_user_var, 1, 0),
            ("DB Pass:",  self._vite_db_pass_var, 1, 2),
        ]
        for lbl_text, var, row, col in db_fields:
            tk.Label(db_grid, text=lbl_text, font=("Segoe UI", 9, "bold"),
                     bg=COLORS["bg_accent"], fg=COLORS["text_secondary"]
                     ).grid(row=row, column=col, sticky="w", padx=(0 if col == 0 else 12, 4), pady=3)
            show = "\u2022" if "Pass" in lbl_text else None
            e = tk.Entry(db_grid, textvariable=var, font=("Segoe UI", 9),
                         bg=COLORS.get("entry_bg", COLORS["bg_primary"]),
                         fg=COLORS["text_primary"],
                         insertbackground=COLORS["text_primary"],
                         relief="flat")
            if show:
                e.configure(show=show)
            e.grid(row=row, column=col + 1, sticky="ew", ipady=4, pady=3,
                   padx=(0, 0 if col == 0 else 0))


        sql_card = tk.Frame(parent, bg=COLORS["bg_accent"], padx=12, pady=10)
        sql_card.pack(fill="x", pady=(0, 6))

        sql_head = _create_label(sql_card, "Import SQL File (optional)", 9, True, "text_primary")
        sql_head.pack(anchor="w", pady=(0, 6))

        sql_row = tk.Frame(sql_card, bg=COLORS["bg_accent"])
        sql_row.pack(fill="x")

        self._vite_sql_label = tk.Label(
            sql_row, textvariable=self._vite_sql_file_label_var,
            font=("Segoe UI", 9), bg=COLORS["bg_accent"],
            fg=COLORS["text_secondary"], anchor="w",
        )
        self._vite_sql_label.pack(side="left", fill="x", expand=True)

        def _browse_sql():
            path = filedialog.askopenfilename(
                title="Select SQL File",
                filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
            )
            if path:
                import os
                self._vite_sql_path_var.set(path)
                self._vite_sql_file_label_var.set(os.path.basename(path))
                self._vite_sql_label.configure(fg=COLORS["text_primary"])

        tk.Button(
            sql_row, text="\U0001f4c2  Browse SQL File",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground=COLORS.get("accent", "#1a3a5c"),
            activeforeground="white",
            command=_browse_sql,
        ).pack(side="right", ipadx=8, ipady=3)


        btn_row = tk.Frame(parent, bg=COLORS["bg_secondary"])
        btn_row.pack(fill="x", pady=(4, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        vite_buttons = [
            ("vite_db_create_btn", "\U0001f5c4  Create Database",  "#1565C0", "#1256A8",
             "Create the MySQL database if it does not exist"),
            ("vite_db_import_btn", "\u2b06  Upload & Import SQL",  "#2E7D32", "#256B28",
             "Upload the SQL file to the server and import it"),
            ("vite_db_env_btn", "\U0001f4be  Save .env to Server",  "#E65100", "#CC4700",
             "Save DB credentials as .env in the project folder"),
        ]
        for idx, (attr, text, bg, hover, tip) in enumerate(vite_buttons):
            cell = tk.Frame(btn_row, bg=COLORS["bg_secondary"])
            cell.grid(row=idx // 2, column=idx % 2, sticky="ew",
                      padx=(0, 6) if idx % 2 == 0 else 0, pady=3)

            btn = tk.Button(
                cell, text=text,
                font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                bg=bg, fg="white",
                activebackground=hover, activeforeground="white",
            )
            btn.pack(fill="x", ipady=5)
            setattr(self, attr, btn)
            if attr in self._vite_db_btn_commands:
                cmd = self._vite_db_btn_commands[attr]
                btn.configure(command=lambda c=cmd: (self._mark_db_step_completed(), c()))

            tk.Label(cell, text=tip, font=("Segoe UI", 7),
                     bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
                     ).pack(anchor="w")

    def get_vite_db_config(self) -> dict:
        """Return the Vite DB config as a dict including the local SQL file path."""
        return {
            "db_name":    self._vite_db_name_var.get().strip(),
            "db_user":    self._vite_db_user_var.get().strip(),
            "db_pass":    self._vite_db_pass_var.get(),
            "db_host":    self._vite_db_host_var.get().strip(),
            "sql_path":   self._vite_sql_path_var.get()
                          if self._vite_sql_path_var.get() != "No file selected" else "",
        }

    def set_vite_db_button_commands(self, commands: dict):
        """Register commands for Vite DB buttons.
        commands: {"vite_db_create_btn": callable, "vite_db_import_btn": callable}
        """
        self._vite_db_btn_commands.update(commands)
        for attr, cmd in commands.items():
            btn = getattr(self, attr, None)
            if btn:
                btn.configure(command=lambda c=cmd: (self._mark_db_step_completed(), c()))
