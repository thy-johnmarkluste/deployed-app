"""Upload-project dialog â€” modal SFTP upload with optional GitHub push."""
import os
import re
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, scrolledtext, ttk

from models.config import COLORS, get_github_token as _get_saved_token


class UploadDialogMixin:
    """Provides the _open_upload_dialog method (modal upload UI)."""


    def _build_upload_dialog_header(self, dialog, domain, title_bar):
        """Build the title bar with settings button."""
        from models.config import COLORS

        tk.Label(
            title_bar, text=f"\u2b06  Upload Project to {domain}",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")

        return {
            "dialog": dialog,
            "domain": domain,
        }

    def _build_settings_toggle(self, title_bar, dialog, settings_container, dest_label, _update_dialog_geometry):
        """Build the settings gear button."""
        from models.config import COLORS

        _settings_visible = {"val": False}

        def _toggle_settings():
            if _settings_visible["val"]:
                settings_container.pack_forget()
                _settings_visible["val"] = False
            else:
                settings_container.pack(fill="both", expand=True, padx=22, pady=(0, 2),
                                        after=dest_label)
                _settings_visible["val"] = True
            _update_dialog_geometry()

        settings_btn = tk.Button(
            title_bar, text="\u2699",
            font=("Segoe UI", 14), relief="flat", cursor="hand2",
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_primary"],
            activeforeground=COLORS["text_primary"],
            bd=0, highlightthickness=0,
            command=_toggle_settings,
        )
        settings_btn.pack(side="right")

        return _settings_visible

    def _build_framework_deps_ui(self, settings_pad, _framework_deps, dep_vars):
        """Build the framework dependencies checkboxes."""
        from models.config import COLORS

        dep_frame = tk.Frame(settings_pad, bg=COLORS["bg_accent"])
        dep_frame.pack(fill="both", expand=True)


        for framework, deps in _framework_deps.items():
            header = tk.Label(
                dep_frame, text=framework,
                font=("Segoe UI", 10, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            )
            header.pack(anchor="w", pady=(8, 4))

            for key, label in deps:
                var = tk.BooleanVar(value=False)
                dep_vars[key] = var
                tk.Checkbutton(
                    dep_frame, text=label, variable=var,
                    font=("Segoe UI", 9),
                    bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                    selectcolor=COLORS["bg_primary"],
                    activebackground=COLORS["bg_accent"],
                    activeforeground=COLORS["text_primary"],
                    anchor="w",
                ).pack(anchor="w", padx=12, pady=1)

        return dep_frame

    def _build_vite_db_section(self, right_inner, domain, _get_vite_db_config, append_log):
        """Build the Vite database setup section."""
        from models.config import COLORS

        vite_db_frame = tk.Frame(right_inner, bg=COLORS["bg_accent"])


        tk.Label(
            vite_db_frame, text="Database Name",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 2))

        vite_db_name_var = tk.StringVar()
        tk.Entry(
            vite_db_frame, textvariable=vite_db_name_var,
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        ).pack(fill="x", ipady=4, pady=(0, 6))


        tk.Label(
            vite_db_frame, text="Database User",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 2))

        vite_db_user_var = tk.StringVar(value="root")
        tk.Entry(
            vite_db_frame, textvariable=vite_db_user_var,
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        ).pack(fill="x", ipady=4, pady=(0, 6))


        tk.Label(
            vite_db_frame, text="Database Password",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 2))

        vite_db_pass_var = tk.StringVar()
        tk.Entry(
            vite_db_frame, textvariable=vite_db_pass_var, show="\u2022",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        ).pack(fill="x", ipady=4, pady=(0, 6))


        btn_row = tk.Frame(vite_db_frame, bg=COLORS["bg_accent"])
        btn_row.pack(fill="x", pady=(8, 0))

        def _create_vite_db():
            db_cfg = _get_vite_db_config()

            self.vite_create_db(domain, db_cfg, append_log)

        def _upload_vite_sql():
            db_cfg = _get_vite_db_config()
            self.vite_upload_sql(domain, db_cfg, append_log)

        tk.Button(
            btn_row, text="\U0001f5c4  Create Database",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            bg="#6A1B9A", fg="white",
            activebackground="#5C1789", activeforeground="white",
            command=_create_vite_db,
        ).pack(side="left", fill="x", expand=True, padx=(0, 4), ipady=5)

        tk.Button(
            btn_row, text="\U0001f4e4  Upload SQL",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            bg="#1565C0", fg="white",
            activebackground="#1256A8", activeforeground="white",
            command=_upload_vite_sql,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0), ipady=5)

        return vite_db_frame, {
            "db_name": vite_db_name_var,
            "db_user": vite_db_user_var,
            "db_pass": vite_db_pass_var,
        }


    def _open_upload_dialog(self, domain):
        """Modal dialog: upload a local project folder via SFTP, then commit & push to GitHub."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Upload Project \u2014 {domain}")
        dialog.geometry("620x460")
        dialog.resizable(False, True)
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_primary"])
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 620) // 2
        y = (dialog.winfo_screenheight() - 460) // 2
        dialog.geometry(f"620x460+{x}+{y}")


        title_bar = tk.Frame(dialog, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", padx=22, pady=(16, 0))

        tk.Label(
            title_bar, text=f"\u2b06  Upload Project to {domain}",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")


        _settings_visible = {"val": True}
        _framework_expanded = {"val": False}
        wizard_step = {"value": 1}


        _default_width = 620
        _expanded_width = 900
        _collapsed_height = 460
        _settings_height = 620

        def _update_dialog_geometry():
            """Recompute dialog geometry based on current settings and framework state."""
            w = _expanded_width if _framework_expanded["val"] else _default_width
            h = _settings_height if _settings_visible["val"] else _collapsed_height
            x = (dialog.winfo_screenwidth() - w) // 2
            y = dialog.winfo_y() or (dialog.winfo_screenheight() - h) // 2
            dialog.geometry(f"{w}x{h}+{x}+{y}")

        def _toggle_settings():
            if _settings_visible["val"]:
                settings_container.pack_forget()
                _settings_visible["val"] = False
            else:
                settings_container.pack(fill="both", expand=True, padx=22, pady=(0, 2),
                                        after=dest_label)
                _settings_visible["val"] = True
            _update_dialog_geometry()

        settings_btn = tk.Button(
            title_bar, text="\u2699",
            font=("Segoe UI", 14), relief="flat", cursor="hand2",
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_primary"],
            activeforeground=COLORS["text_primary"],
            bd=0, highlightthickness=0,
            command=_toggle_settings,
        )
        settings_btn.pack(side="right")

        dest_label = tk.Label(
            dialog,
            text=f"Destination: /var/www/{domain}/public_html/",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        )
        dest_label.pack(anchor="w", padx=22, pady=(0, 8))


        settings_container = tk.Frame(dialog, bg=COLORS["bg_secondary"],
                                      highlightbackground=COLORS["accent"],
                                      highlightthickness=1)
        settings_container.pack(fill="both", expand=True, padx=22, pady=(0, 2), after=dest_label)


        _settings_canvas = tk.Canvas(
            settings_container, bg=COLORS["bg_secondary"],
            highlightthickness=0, bd=0,
        )
        _settings_sb = tk.Scrollbar(
            settings_container, orient="vertical",
            command=_settings_canvas.yview,
            bg=COLORS["bg_secondary"], troughcolor=COLORS["bg_accent"],
            activebackground=COLORS["accent"], highlightthickness=0,
            bd=0, width=8,
        )
        _settings_canvas.configure(yscrollcommand=_settings_sb.set)
        _settings_sb.pack(side="right", fill="y")
        _settings_canvas.pack(side="left", fill="both", expand=True)

        settings_inner = tk.Frame(_settings_canvas, bg=COLORS["bg_secondary"])
        _settings_win = _settings_canvas.create_window(
            (0, 0), window=settings_inner, anchor="nw",
        )

        def _on_settings_inner_cfg(event):
            _settings_canvas.configure(scrollregion=_settings_canvas.bbox("all"))

            needed = settings_inner.winfo_reqheight()
            current_step = wizard_step.get("value", 1)
            if current_step <= 2:
                max_h = 220
            elif current_step == 3:
                max_h = 260
            elif current_step in (4, 5):
                max_h = 360
            else:
                max_h = 300
            _settings_canvas.configure(height=min(needed, max_h))

        def _on_settings_canvas_cfg(event):
            _settings_canvas.itemconfig(_settings_win, width=event.width)

        settings_inner.bind("<Configure>", _on_settings_inner_cfg)
        _settings_canvas.bind("<Configure>", _on_settings_canvas_cfg)

        def _on_settings_wheel(event):
            _settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        _settings_canvas.bind(
            "<Enter>",
            lambda e: _settings_canvas.bind_all("<MouseWheel>", _on_settings_wheel),
        )
        _settings_canvas.bind(
            "<Leave>",
            lambda e: _settings_canvas.unbind_all("<MouseWheel>"),
        )


        _settings_pad = tk.Frame(settings_inner, bg=COLORS["bg_secondary"])
        _settings_pad.pack(fill="x", padx=12, pady=10)


        tk.Label(
            _settings_pad, text="\u2699  Upload Settings",
            font=("Segoe UI", 11, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 8))

        db_step_state = {"vite": False, "wordpress": False, "vite_skipped": False}

        step1_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        step2_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        step3_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        step4_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        step5_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        step6_frame = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])

        for frm in (step1_frame, step2_frame, step3_frame, step4_frame, step5_frame, step6_frame):
            frm.pack(fill="x", pady=(0, 6))


        tk.Label(
            step1_frame, text="Step 1: GitHub URL", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        url_var = tk.StringVar()
        url_entry = tk.Entry(
            step1_frame, textvariable=url_var,
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        url_entry.pack(fill="x", ipady=5, pady=(0, 2))
        tk.Label(
            step1_frame,
            text="Leave empty to upload to server only (no GitHub push)",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 6))


        tk.Label(
            step1_frame, text="GitHub Access Token", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        token_frame = tk.Frame(step1_frame, bg=COLORS["bg_secondary"])
        token_frame.pack(fill="x", pady=(0, 2))
        token_var = tk.StringVar(value=_get_saved_token())
        token_entry = tk.Entry(
            token_frame, textvariable=token_var, show="\u2022",
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        token_entry.pack(side="left", fill="x", expand=True, ipady=5)

        def _toggle_token():
            if token_entry.cget("show") == "\u2022":
                token_entry.configure(show="")
                toggle_btn.configure(text="Hide")
            else:
                token_entry.configure(show="\u2022")
                toggle_btn.configure(text="Show")

        toggle_btn = tk.Button(
            token_frame, text="Show",
            font=("Segoe UI", 8), relief="flat", cursor="hand2",
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
            command=_toggle_token,
        )
        toggle_btn.pack(side="right", padx=(6, 0), ipady=4, ipadx=6)
        tk.Label(
            step1_frame,
            text="Required for private repos (needs 'repo' scope)",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 6))


        tk.Label(
            step2_frame, text="Step 2: Upload Options and Branch", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))

        options_frame = tk.Frame(step2_frame, bg=COLORS["bg_secondary"])
        options_frame.pack(fill="x", pady=(0, 6))

        clean_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame, text="Clean upload (remove old files first)",
            variable=clean_var,
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
        ).pack(side="left")

        force_push_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame, text="Force push (overwrite remote)",
            variable=force_push_var,
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
        ).pack(side="left", padx=(12, 0))


        tk.Label(
            step2_frame, text="Branch Name", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(4, 2))

        _default_branch = "main"
        try:
            _default_branch = self.view.manage_subdomain_page.branch_var.get().strip() or "main"
        except Exception:
            pass
        branch_var = tk.StringVar(value=_default_branch)
        tk.Entry(
            step2_frame, textvariable=branch_var,
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        ).pack(fill="x", ipady=5, pady=(0, 2))
        tk.Label(
            step2_frame,
            text="Branch to push to (e.g. main, master, develop)",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 6))


        tk.Label(
            step3_frame, text="Step 3: Select Framework", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(4, 2))

        framework_var = tk.StringVar(value="None")
        framework_dropdown = ttk.Combobox(
            step3_frame, textvariable=framework_var, state="readonly",
            font=("Segoe UI", 9), width=30,
        )
        framework_dropdown["values"] = [
            "None",
            "Vite (Modern Frontend)",
            "WordPress (CMS)",
        ]
        framework_dropdown.pack(fill="x", ipady=3, pady=(0, 4))
        tk.Label(
            step3_frame,
            text="Note: Server runs Node.js v18. Ensure your framework and dependencies are compatible with v18 or below.",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_secondary"], fg=COLORS["warning"],
        ).pack(fill="x", pady=(0, 6))

        wp_mode_var = tk.StringVar(value="upload_existing")
        wp_mode_box = tk.Frame(step3_frame, bg=COLORS["bg_secondary"])
        tk.Label(
            wp_mode_box,
            text="WordPress Mode",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 2))
        tk.Radiobutton(
            wp_mode_box,
            text="Upload Existing Project",
            variable=wp_mode_var,
            value="upload_existing",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
        ).pack(anchor="w")
        tk.Radiobutton(
            wp_mode_box,
            text="Install Fresh WordPress",
            variable=wp_mode_var,
            value="install_fresh",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            selectcolor=COLORS["bg_primary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
        ).pack(anchor="w")


        columns_container = tk.Frame(_settings_pad, bg=COLORS["bg_secondary"])
        columns_container.columnconfigure(0, weight=1)
        columns_container.columnconfigure(1, weight=1)


        left_column = tk.Frame(
            columns_container, bg=COLORS["bg_accent"],
            highlightbackground=COLORS.get("accent", "#1a3a5c"),
            highlightthickness=1,
        )
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 6))


        left_inner = tk.Frame(left_column, bg=COLORS["bg_accent"])
        left_inner.pack(fill="both", expand=True, padx=12, pady=10)


        tk.Label(
            left_inner, text="Dependencies / Plugins",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 8))


        right_column = tk.Frame(
            columns_container, bg=COLORS["bg_accent"],
            highlightbackground=COLORS.get("accent", "#1a3a5c"),
            highlightthickness=1,
        )
        right_column.grid(row=0, column=1, sticky="nsew", padx=(6, 0))


        right_inner = tk.Frame(right_column, bg=COLORS["bg_accent"])
        right_inner.pack(fill="both", expand=True, padx=12, pady=10)


        tk.Label(
            right_inner, text="Setup & Database",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
        ).pack(anchor="w", pady=(0, 8))


        _framework_deps = {
            "Vite (Modern Frontend)": [
                ("tailwindcss",    "Tailwind CSS"),
                ("typescript",     "TypeScript"),
                ("sass",           "Sass / SCSS"),
                ("eslint",         "ESLint"),
                ("prettier",       "Prettier"),
                ("axios",          "Axios"),
                ("react",          "React"),
                ("vue",            "Vue"),
            ],
            "WordPress (CMS)": {
                "themes": [
                    ("theme-astra", "Astra"),
                    ("theme-generatepress", "GeneratePress"),
                    ("theme-kadence", "Kadence"),
                    ("theme-neve", "Neve"),
                    ("theme-blocksy", "Blocksy"),
                    ("theme-hello-elementor", "Hello Elementor"),
                ],
                "plugins": [
                    ("wp-cli", "WP-CLI"),
                    ("woocommerce", "WooCommerce"),
                    ("elementor", "Elementor"),
                    ("yoast-seo", "Yoast SEO"),
                    ("rank-math", "Rank Math SEO"),
                    ("wordfence", "Wordfence"),
                    ("contact-form-7", "Contact Form 7"),
                    ("advanced-custom-fields", "Advanced Custom Fields"),
                    ("all-in-one-wp-migration", "All-in-One WP Migration"),
                    ("updraftplus", "UpdraftPlus"),
                    ("wp-super-cache", "WP Super Cache"),
                    ("query-monitor", "Query Monitor"),
                ],
            },
        }
        dep_vars: dict[str, tk.BooleanVar] = {}
        dep_frame = tk.Frame(left_inner, bg=COLORS["bg_accent"])
        dep_frame.pack(fill="both", expand=True)


        wp_setup_frame = tk.Frame(right_inner, bg=COLORS["bg_accent"])
        wp_db_name_var = tk.StringVar()
        wp_db_user_var = tk.StringVar(value="root")
        wp_db_pass_var = tk.StringVar()
        wp_db_host_var = tk.StringVar(value="localhost")
        wp_sql_path_var = tk.StringVar(value="")
        wp_sql_label_var = tk.StringVar(value="No file selected")

        wp_prereq_vars = {}
        wp_prereqs = [
            ("php-mysql", "PHP MySQLi (Required for WP-CLI)"),
            ("wp-cli", "WP-CLI (WordPress command-line tool)"),
        ]
        wp_content_frame = tk.Frame(wp_setup_frame, bg=COLORS["bg_accent"])
        wp_expanded = {"val": False}

        def _build_mysql_auth(db_cfg):
            auth = f"-u '{db_cfg['db_user']}'"
            if db_cfg["db_pass"]:
                auth += f" -p'{db_cfg['db_pass']}'"
            if db_cfg["db_host"] and db_cfg["db_host"] != "localhost":
                auth += f" -h '{db_cfg['db_host']}'"
            return auth

        def _get_wp_db_config():
            return {
                "db_name": wp_db_name_var.get().strip(),
                "db_user": wp_db_user_var.get().strip(),
                "db_pass": wp_db_pass_var.get(),
                "db_host": wp_db_host_var.get().strip(),
                "sql_path": wp_sql_path_var.get(),
            }

        def _get_wp_selected_prereqs():
            return [k for k, v in wp_prereq_vars.items() if v.get()]

        def _build_wp_section():

            prereq_frame = tk.Frame(wp_content_frame, bg=COLORS["bg_accent"], padx=12, pady=8)
            prereq_frame.pack(fill="x", pady=(0, 6))

            prereq_grid = tk.Frame(prereq_frame, bg=COLORS["bg_accent"])
            prereq_grid.pack(fill="x")
            prereq_grid.columnconfigure(0, weight=1)
            prereq_grid.columnconfigure(1, weight=1)

            for idx, (key, label) in enumerate(wp_prereqs):
                var = tk.BooleanVar(value=True)
                wp_prereq_vars[key] = var
                tk.Checkbutton(
                    prereq_grid, text=label, variable=var,
                    font=("Segoe UI", 9),
                    bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                    selectcolor=COLORS["bg_primary"],
                    activebackground=COLORS["bg_accent"],
                    activeforeground=COLORS["text_primary"],
                    anchor="w",
                ).grid(row=0, column=idx, sticky="w", padx=(0, 12))


            tk.Label(
                wp_content_frame, text="Setup Tools",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 4))


            btn_grid = tk.Frame(wp_content_frame, bg=COLORS["bg_accent"])
            btn_grid.pack(fill="x", pady=(0, 6))
            btn_grid.columnconfigure(0, weight=1)
            btn_grid.columnconfigure(1, weight=1)

            wp_buttons = [
                ("\U0001f4c4  Generate wp-config", "#1565C0", "#1256A8",
                 lambda: self.wp_generate_config(domain, _get_wp_db_config(), append_log)),
                ("\U0001f5c4  Check / Create DB", "#6A1B9A", "#5C1789",
                  lambda: (_mark_db_completed("wordpress"), self.wp_check_database(domain, _get_wp_db_config(), append_log))),
                ("\U0001f512  Fix Permissions", "#2E7D32", "#256B28",
                 lambda: self.wp_fix_permissions(domain, None, append_log)),
                ("\u2699\ufe0f  Fix Apache Vhost", "#E65100", "#CC4700",
                 lambda: self.wp_fix_vhost(domain, None, append_log)),
            ]

            for idx, (text, bg, hover, cmd) in enumerate(wp_buttons):
                btn = tk.Button(
                    btn_grid, text=text,
                    font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                    bg=bg, fg="white",
                    activebackground=hover, activeforeground="white",
                    command=cmd,
                )
                btn.grid(row=idx // 2, column=idx % 2, sticky="ew",
                         padx=(0, 6), pady=3, ipady=5)


            db_card = tk.Frame(wp_content_frame, bg=COLORS["bg_accent"], padx=12, pady=10)
            db_card.pack(fill="x", pady=(6, 6))

            tk.Label(
                db_card, text="Database Configuration",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 6))

            db_grid = tk.Frame(db_card, bg=COLORS["bg_accent"])
            db_grid.pack(fill="x")
            db_grid.columnconfigure(1, weight=1)
            for row_idx, (label_text, var) in enumerate([
                ("DB Name:", wp_db_name_var),
                ("DB User:", wp_db_user_var),
                ("DB Pass:", wp_db_pass_var),
                ("DB Host:", wp_db_host_var),
            ]):
                tk.Label(
                    db_grid, text=label_text,
                    font=("Segoe UI", 9, "bold"),
                    bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
                ).grid(row=row_idx, column=0, sticky="w", padx=(0, 8), pady=2)
                show = "\u2022" if "Pass" in label_text else None
                fe = tk.Entry(
                    db_grid, textvariable=var,
                    font=("Segoe UI", 9), relief="flat",
                    bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
                    insertbackground=COLORS["text_primary"],
                )
                if show:
                    fe.configure(show=show)
                fe.grid(row=row_idx, column=1, sticky="ew", ipady=4, pady=2)


            sql_card = tk.Frame(wp_content_frame, bg=COLORS["bg_accent"], padx=12, pady=8)
            sql_card.pack(fill="x", pady=(0, 6))

            tk.Label(
                sql_card, text="Import SQL File (optional)",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 6))

            db_select_row = tk.Frame(sql_card, bg=COLORS["bg_accent"])
            db_select_row.pack(fill="x", pady=(0, 6))

            tk.Label(
                db_select_row, text="Target DB:",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
            ).pack(side="left", padx=(0, 8))

            wp_db_dropdown = ttk.Combobox(
                db_select_row,
                textvariable=wp_db_name_var,
                values=[],
                state="normal",
                font=("Segoe UI", 9),
                width=28,
            )
            wp_db_dropdown.pack(side="left", fill="x", expand=True)

            def _load_wp_databases():
                db_cfg = _get_wp_db_config()
                if not db_cfg["db_user"]:
                    messagebox.showwarning("Missing Info", "Please fill in DB User first.", parent=dialog)
                    return

                append_log("Loading MySQL databases...")

                def _worker():
                    client = None
                    try:
                        client = self.ssh.connect()
                        if not client:
                            self.root.after(0, lambda: append_log("ERROR: SSH connection failed."))
                            return

                        auth = _build_mysql_auth(db_cfg)
                        cmd = f"mysql {auth} -N -e \"SHOW DATABASES;\" 2>&1"
                        _, stdout, _ = client.exec_command(cmd)
                        out = stdout.read().decode().strip()

                        if "ERROR" in out.upper() or "Access denied" in out:
                            self.root.after(0, lambda: append_log(f"ERROR loading databases: {out}"))
                            return

                        dbs = [d.strip() for d in out.splitlines() if d.strip()]

                        def _apply():
                            wp_db_dropdown["values"] = dbs
                            if dbs and not wp_db_name_var.get().strip():
                                wp_db_name_var.set(dbs[0])
                            append_log(f"Loaded {len(dbs)} database(s).")

                        self.root.after(0, _apply)
                    except Exception as e:
                        self.root.after(0, lambda: append_log(f"ERROR loading databases: {e}"))
                    finally:
                        if client:
                            client.close()

                threading.Thread(target=_worker, daemon=True).start()

            tk.Button(
                db_select_row, text="Refresh DBs",
                font=("Segoe UI", 8), relief="flat", cursor="hand2",
                bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                activebackground=COLORS.get("accent", "#1a3a5c"),
                activeforeground="white",
                command=_load_wp_databases,
            ).pack(side="left", padx=(6, 0), ipady=2)

            sql_row = tk.Frame(sql_card, bg=COLORS["bg_accent"])
            sql_row.pack(fill="x")

            sql_name_lbl = tk.Label(
                sql_row, textvariable=wp_sql_label_var,
                font=("Segoe UI", 9), bg=COLORS["bg_accent"],
                fg=COLORS["text_secondary"], anchor="w",
            )
            sql_name_lbl.pack(side="left", fill="x", expand=True)

            def _browse_wp_sql():
                path = filedialog.askopenfilename(
                    title="Select WordPress SQL File",
                    filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
                    parent=dialog,
                )
                if path:
                    wp_sql_path_var.set(path)
                    wp_sql_label_var.set(os.path.basename(path))
                    sql_name_lbl.configure(fg=COLORS["text_primary"])

            tk.Button(
                sql_row, text="\U0001f4c2  Browse SQL",
                font=("Segoe UI", 9), relief="flat", cursor="hand2",
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                activebackground=COLORS.get("accent", "#1a3a5c"),
                activeforeground="white",
                command=_browse_wp_sql,
            ).pack(side="right", ipadx=8, ipady=3)

            def _upload_wp_sql_now():
                db_cfg = _get_wp_db_config()
                sql_path = db_cfg.get("sql_path", "").strip()

                missing = []
                if not db_cfg["db_name"]:
                    missing.append("Database Name")
                if not db_cfg["db_user"]:
                    missing.append("Database User")
                if not sql_path:
                    missing.append("SQL File")

                if missing:
                    messagebox.showwarning(
                        "Missing Information",
                        f"Please fill in: {', '.join(missing)}",
                        parent=dialog,
                    )
                    return

                if not os.path.isfile(sql_path):
                    messagebox.showwarning(
                        "Invalid SQL File",
                        "Selected SQL file path is invalid on this machine.",
                        parent=dialog,
                    )
                    return

                append_log(f"Uploading SQL dump to database '{db_cfg['db_name']}'...")
                set_status("Uploading database SQL...")

                def _worker():
                    client = None
                    try:
                        client = self.ssh.connect()
                        if not client:
                            self.root.after(0, lambda: append_log("ERROR: SSH connection failed."))
                            return

                        remote_sql = f"/tmp/{domain.replace('.', '_')}_manual_import.sql"
                        sftp = client.open_sftp()
                        sftp.put(sql_path, remote_sql)
                        sftp.close()

                        auth = _build_mysql_auth(db_cfg)
                        db_name_sql = db_cfg["db_name"].replace("'", "''")
                        append_log(f"Replacing existing tables in '{db_cfg['db_name']}' before import...")
                        reset_cmd = (
                            f"mysql {auth} -N -e \""
                            f"SET FOREIGN_KEY_CHECKS=0; "
                            f"USE \`{db_cfg['db_name']}\`; "
                            f"SET @tables = NULL; "
                            f"SELECT GROUP_CONCAT(CONCAT(CHAR(96), table_name, CHAR(96))) INTO @tables "
                            f"FROM information_schema.tables "
                            f"WHERE table_schema='{db_name_sql}' AND table_type='BASE TABLE'; "
                            f"SET @tables = IFNULL(@tables, ''); "
                            f"SET @tsql = IF(@tables='', 'SELECT 1', CONCAT('DROP TABLE ', @tables)); "
                            f"PREPARE tstmt FROM @tsql; EXECUTE tstmt; DEALLOCATE PREPARE tstmt; "
                            f"SET @views = NULL; "
                            f"SELECT GROUP_CONCAT(CONCAT(CHAR(96), table_name, CHAR(96))) INTO @views "
                            f"FROM information_schema.tables "
                            f"WHERE table_schema='{db_name_sql}' AND table_type='VIEW'; "
                            f"SET @views = IFNULL(@views, ''); "
                            f"SET @vsql = IF(@views='', 'SELECT 1', CONCAT('DROP VIEW ', @views)); "
                            f"PREPARE vstmt FROM @vsql; EXECUTE vstmt; DEALLOCATE PREPARE vstmt; "
                            f"SET FOREIGN_KEY_CHECKS=1;\" 2>&1"
                        )
                        _, stdout, _ = client.exec_command(reset_cmd, timeout=180)
                        reset_out = stdout.read().decode().strip()
                        if reset_out and ("ERROR" in reset_out.upper() or "Access denied" in reset_out):
                            client.exec_command(f"rm -f '{remote_sql}'")
                            self.root.after(0, lambda: append_log(f"ERROR resetting database tables: {reset_out}"))
                            self.root.after(0, lambda: set_status("SQL import failed"))
                            return

                        import_cmd = f"mysql {auth} '{db_cfg['db_name']}' < '{remote_sql}' 2>&1"
                        _, stdout, _ = client.exec_command(import_cmd, timeout=300)
                        import_out = stdout.read().decode().strip()

                        client.exec_command(f"rm -f '{remote_sql}'")

                        def _done():
                            if import_out and ("ERROR" in import_out.upper() or "Access denied" in import_out):
                                append_log(f"ERROR importing SQL: {import_out}")
                                set_status("SQL import failed")
                            else:
                                _mark_db_completed("wordpress")
                                append_log(f"SQL import complete: {os.path.basename(sql_path)} -> {db_cfg['db_name']}")
                                set_status("SQL import complete")

                        self.root.after(0, _done)
                    except Exception as e:
                        self.root.after(0, lambda: append_log(f"ERROR importing SQL: {e}"))
                        self.root.after(0, lambda: set_status("SQL import failed"))
                    finally:
                        if client:
                            client.close()

                threading.Thread(target=_worker, daemon=True).start()

            tk.Button(
                sql_card, text="\u2b06  Upload Database",
                font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
                bg="#2E7D32", fg="white",
                activebackground="#256B28", activeforeground="white",
                command=_upload_wp_sql_now,
            ).pack(anchor="e", pady=(6, 0), ipadx=10, ipady=4)

            tk.Button(
                sql_card, text="Skip WordPress Database Setup",
                font=("Segoe UI", 9), relief="flat", cursor="hand2",
                bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
                command=lambda: (_mark_db_completed("wordpress"), append_log("WordPress database setup marked as skipped.")),
            ).pack(anchor="e", pady=(6, 0), ipadx=10, ipady=4)


            _load_wp_databases()

        def _run_wp_install():
            """Run fresh WordPress installation."""
            db_cfg = _get_wp_db_config()
            plugins = [
                key for key, var in dep_vars.items()
                if var.get() and key not in {"wp-cli", "php-mysql"}
            ]
            prereqs = _get_wp_selected_prereqs()

            repo_url = url_var.get().strip()
            github_token = token_var.get().strip()


            missing = []
            if not db_cfg["db_name"]:
                missing.append("Database Name")
            if not db_cfg["db_user"]:
                missing.append("Database User")

            if missing:
                messagebox.showwarning(
                    "Missing Information",
                    f"Please fill in: {', '.join(missing)}",
                    parent=dialog,
                )
                return

            def _worker():
                client = None
                try:
                    append_log(f"\n{'=' * 50}")
                    append_log(f"Installing Fresh WordPress for {domain}")
                    append_log(f"{'=' * 50}")
                    set_status("Installing WordPress...")
                    client = self.ssh.connect()
                    if not client:
                        append_log("ERROR: SSH connection failed.")
                        return

                    path = self.git_manager.get_subdomain_path(domain)


                    append_log("\n[1/10] Installing server prerequisites...")
                    set_status("Installing prerequisites...")

                    if "php-mysql" in prereqs:
                        append_log("  Checking PHP MySQLi extension...")
                        php_check = "php -m 2>/dev/null | grep -i mysqli || echo 'NOT_FOUND'"
                        _, stdout, _ = client.exec_command(php_check)
                        php_result = stdout.read().decode().strip()

                        if "NOT_FOUND" in php_result or not php_result:
                            append_log("  PHP MySQLi not found â€” installing php-mysql...")
                            install_cmd = "sudo apt-get update && sudo apt-get install -y php-mysql 2>&1"
                            _, stdout, _ = client.exec_command(install_cmd, timeout=120)
                            output = stdout.read().decode().strip()
                            if "error" in output.lower() and "unable" in output.lower():
                                append_log(f"  Warning: {output[-200:]}")
                            else:
                                append_log("  PHP MySQLi installed!")

                                append_log("  Restarting Apache...")
                                restart_cmd = "sudo systemctl restart apache2 2>&1"
                                _, stdout, _ = client.exec_command(restart_cmd)
                                stdout.read()
                                append_log("  Apache restarted!")
                        else:
                            append_log("  PHP MySQLi already installed!")
                    else:
                        append_log("  PHP MySQLi skipped (not selected)")


                    append_log("\n[2/10] Checking WP-CLI...")
                    wp_check = "which wp 2>/dev/null || echo 'NOT_FOUND'"
                    _, stdout, _ = client.exec_command(wp_check)
                    wp_path = stdout.read().decode().strip()

                    if "wp-cli" in prereqs and wp_path == "NOT_FOUND":
                        append_log("WP-CLI not found â€” installing...")
                        wp_install = (
                            "curl -O https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && "
                            "chmod +x wp-cli.phar && "
                            "sudo mv wp-cli.phar /usr/local/bin/wp"
                        )
                        _, stdout, stderr = client.exec_command(wp_install)
                        stdout.read()
                        err = stderr.read().decode().strip()
                        if err and "error" in err.lower():
                            append_log(f"ERROR installing WP-CLI: {err}")
                            return
                        append_log("  WP-CLI installed!")
                    else:
                        append_log(f"  WP-CLI found at {wp_path}")


                    append_log("\n[3/10] Creating database...")
                    set_status("Creating database...")
                    auth = _build_mysql_auth(db_cfg)

                    create_db = (
                        f"mysql {auth} -e \""
                        f"CREATE DATABASE IF NOT EXISTS \\`{db_cfg['db_name']}\\` "
                        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\" 2>&1"
                    )
                    _, stdout, _ = client.exec_command(create_db)
                    result = stdout.read().decode().strip()
                    if result and "ERROR" in result:
                        append_log(f"  Warning: {result}")
                    else:
                        append_log(f"  Database '{db_cfg['db_name']}' ready")


                    append_log("\n[4/10] Downloading WordPress...")
                    set_status("Downloading WordPress...")


                    download_cmd = (
                        f"cd '{path}' && "
                        f"find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {{}} + 2>/dev/null; "
                        f"wp core download --allow-root 2>&1"
                    )
                    _, stdout, _ = client.exec_command(download_cmd, timeout=120)
                    output = stdout.read().decode().strip()
                    if "Success" in output or "already present" in output.lower():
                        append_log("  WordPress downloaded!")
                    else:
                        for line in output.split('\n')[-3:]:
                            append_log(f"  {line}")


                    append_log("\n[5/10] Generating wp-config.php...")
                    set_status("Generating config...")


                    config_cmd = (
                        f"cd '{path}' && "
                        f"cp wp-config-sample.php wp-config.php && "
                        f"sed -i \"s/database_name_here/{db_cfg['db_name']}/g\" wp-config.php && "
                        f"sed -i \"s/username_here/{db_cfg['db_user']}/g\" wp-config.php && "
                        f"sed -i \"s/password_here/{db_cfg['db_pass']}/g\" wp-config.php && "
                        f"sed -i \"s/localhost/{db_cfg['db_host']}/g\" wp-config.php && "
                        f"echo 'OK' 2>&1"
                    )
                    _, stdout, _ = client.exec_command(config_cmd, timeout=30)
                    output = stdout.read().decode().strip()
                    if "OK" in output:
                        append_log("  wp-config.php created!")
                    else:
                        append_log(f"  {output}")


                    append_log("  Fetching security salt keys...")
                    salt_cmd = (
                        f"cd '{path}' && "
                        f"SALT=$(curl -s https://api.wordpress.org/secret-key/1.1/salt/) && "
                        f"if [ -n \"$SALT\" ]; then "
                        f"  sed -i \"/define( 'AUTH_KEY'/,/define( 'NONCE_SALT'/d\" wp-config.php && "
                        f"  echo \"$SALT\" >> wp-config.php && "
                        f"  echo 'SALT_OK'; "
                        f"else echo 'SALT_SKIP'; fi 2>&1"
                    )
                    _, stdout, _ = client.exec_command(salt_cmd, timeout=30)
                    salt_output = stdout.read().decode().strip()
                    if "SALT_OK" in salt_output:
                        append_log("  Security keys added!")
                    else:
                        append_log("  Using default keys (update recommended)")


                    sql_path = db_cfg.get("sql_path", "").strip()
                    if sql_path:
                        append_log("\n[6/10] Uploading and importing SQL dump...")
                        set_status("Importing SQL dump...")
                        if os.path.isfile(sql_path):
                            remote_sql = f"/tmp/{domain.replace('.', '_')}_wp_import.sql"
                            try:
                                sftp = client.open_sftp()
                                sftp.put(sql_path, remote_sql)
                                sftp.close()

                                db_name_sql = db_cfg["db_name"].replace("'", "''")
                                append_log(f"  Replacing existing tables in '{db_cfg['db_name']}'...")
                                reset_cmd = (
                                    f"mysql {auth} -N -e \""
                                    f"SET FOREIGN_KEY_CHECKS=0; "
                                    f"USE \`{db_cfg['db_name']}\`; "
                                    f"SET @tables = NULL; "
                                    f"SELECT GROUP_CONCAT(CONCAT(CHAR(96), table_name, CHAR(96))) INTO @tables "
                                    f"FROM information_schema.tables "
                                    f"WHERE table_schema='{db_name_sql}' AND table_type='BASE TABLE'; "
                                    f"SET @tables = IFNULL(@tables, ''); "
                                    f"SET @tsql = IF(@tables='', 'SELECT 1', CONCAT('DROP TABLE ', @tables)); "
                                    f"PREPARE tstmt FROM @tsql; EXECUTE tstmt; DEALLOCATE PREPARE tstmt; "
                                    f"SET @views = NULL; "
                                    f"SELECT GROUP_CONCAT(CONCAT(CHAR(96), table_name, CHAR(96))) INTO @views "
                                    f"FROM information_schema.tables "
                                    f"WHERE table_schema='{db_name_sql}' AND table_type='VIEW'; "
                                    f"SET @views = IFNULL(@views, ''); "
                                    f"SET @vsql = IF(@views='', 'SELECT 1', CONCAT('DROP VIEW ', @views)); "
                                    f"PREPARE vstmt FROM @vsql; EXECUTE vstmt; DEALLOCATE PREPARE vstmt; "
                                    f"SET FOREIGN_KEY_CHECKS=1;\" 2>&1"
                                )
                                _, stdout, _ = client.exec_command(reset_cmd, timeout=180)
                                reset_out = stdout.read().decode().strip()
                                if reset_out and ("ERROR" in reset_out.upper() or "Access denied" in reset_out):
                                    append_log(f"  Warning: Could not reset existing tables: {reset_out}")
                                else:
                                    append_log("  Existing tables cleared.")

                                import_cmd = f"mysql {auth} '{db_cfg['db_name']}' < '{remote_sql}' 2>&1"
                                _, stdout, _ = client.exec_command(import_cmd, timeout=180)
                                import_out = stdout.read().decode().strip()

                                client.exec_command(f"rm -f '{remote_sql}'")

                                if import_out and "ERROR" in import_out.upper():
                                    append_log(f"  Warning: SQL import reported errors: {import_out}")
                                else:
                                    append_log(f"  SQL import complete: {os.path.basename(sql_path)}")
                            except Exception as e:
                                append_log(f"  Warning: Could not import SQL file: {e}")
                        else:
                            append_log("  Warning: SQL file path is invalid on this machine; skipping import")
                    else:
                        append_log("\n[6/10] No SQL dump selected â€” skipping import")


                    if plugins:
                        append_log(f"\n[7/10] Plugins to install after setup:")
                        for plugin in plugins:
                            append_log(f"  â€¢ {plugin}")
                        append_log("  (Install these via Plugins â†’ Add New in wp-admin)")
                    else:
                        append_log("\n[7/10] No plugins selected â€” skipping")


                    append_log("\n[8/10] Setting permissions...")
                    set_status("Setting permissions...")
                    perm_cmd = (
                        f"chown -R www-data:www-data '{path}' && "
                        f"find '{path}' -type d -exec chmod 755 {{}} \\; && "
                        f"find '{path}' -type f -exec chmod 644 {{}} \\;"
                    )
                    _, stdout, _ = client.exec_command(perm_cmd)
                    stdout.read()
                    append_log("  Permissions set!")


                    append_log("\n[9/10] WordPress ready for browser setup...")
                    set_status("WordPress ready...")
                    url = f"https://{domain}"
                    setup_url = f"{url}/wp-admin/install.php"
                    append_log(f"  \u2713 Files deployed!")
                    append_log(f"  \u2192 Complete setup at: {setup_url}")


                    append_log("\n[10/10] Committing to Git repository...")
                    set_status("Committing to Git...")


                    is_repo = self.git_manager.is_git_repo(client, domain)
                    if not is_repo:
                        append_log("  Initializing Git repository...")
                        init_ok, init_msg = self.git_manager.init_git_repo(client, domain, append_log)
                        if not init_ok:
                            append_log(f"  Warning: {init_msg}")
                        else:
                            append_log("  Git repository initialized!")


                    gitignore_cmd = (
                        f"cd '{path}' && "
                        f"echo -e 'wp-content/uploads/\nwp-content/cache/\n.htaccess\nwp-config.php\n*.log' > .gitignore"
                    )
                    _, stdout, _ = client.exec_command(gitignore_cmd)
                    stdout.read()
                    append_log("  Created .gitignore for WordPress")


                    commit_ok, commit_msg = self.git_manager.add_and_commit(
                        client, domain,
                        "WordPress installation via subdomain manager",
                        log_callback=append_log,
                    )
                    if commit_ok:
                        append_log("  WordPress files committed!")
                    else:
                        append_log(f"  {commit_msg}")


                    has_remote, existing_remote = self.git_manager.get_remote_info(client, domain)

                    if repo_url:
                        append_log(f"  Setting remote origin to {repo_url}...")
                        ok, msg = self.git_manager.add_remote(
                            client, domain, repo_url, "origin", append_log
                        )
                        append_log(f"  {msg}")
                        has_remote = ok

                    if has_remote:
                        append_log("  Pushing to remote repository...")
                        set_status("Pushing to Git...")
                        push_ok, push_msg = self.git_manager.push_to_remote(
                            client, domain, log_callback=append_log,
                            github_token=github_token or _get_saved_token() or "",
                        )
                        if push_ok:
                            append_log("  Pushed to remote!")
                        else:
                            append_log(f"  Push note: {push_msg}")
                    else:
                        append_log("  No remote connected â€” skipping push")
                        append_log("  Tip: Enter a GitHub URL in settings to push changes")

                    append_log(f"\n{'=' * 50}")
                    append_log(f"\u2713  WordPress files deployed!")
                    append_log(f"")
                    append_log(f"   COMPLETE SETUP IN BROWSER:")
                    append_log(f"   \u2192 {url}/wp-admin/install.php")
                    append_log(f"{'=' * 50}")
                    set_status("WordPress ready â€” complete setup in browser!")

                except Exception as e:
                    append_log(f"ERROR: {e}")
                    set_status(f"Error: {e}")
                finally:
                    if client:
                        client.close()

            threading.Thread(target=_worker, daemon=True).start()

        def _toggle_wp():
            wp_expanded["val"] = not wp_expanded["val"]
            if wp_expanded["val"]:
                wp_toggle_btn.configure(
                    text="\u25BC  WordPress Setup Tools  \u25BC",
                    bg="#1565C0", activebackground="#1256A8",
                )
                wp_content_frame.pack(fill="x", pady=(6, 0))
                if not wp_content_frame.winfo_children():
                    _build_wp_section()
            else:
                wp_toggle_btn.configure(
                    text="\u25B6  WordPress Setup Tools",
                    bg=COLORS["bg_secondary"], activebackground="#0a2a4a",
                )
                wp_content_frame.pack_forget()

        wp_toggle_btn = tk.Button(
            wp_setup_frame,
            text="\u25B6  WordPress Setup Tools",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg="white",
            activebackground="#0a2a4a", activeforeground="white",
            anchor="w", padx=12,
            command=_toggle_wp,
        )
        wp_toggle_btn.pack(fill="x", ipady=6)


        vite_db_frame = tk.Frame(right_inner, bg=COLORS["bg_accent"])
        vite_db_name_var = tk.StringVar()
        vite_db_user_var = tk.StringVar(value="root")
        vite_db_pass_var = tk.StringVar()
        vite_db_host_var = tk.StringVar(value="localhost")
        vite_sql_path_var = tk.StringVar(value="")
        vite_sql_label_var = tk.StringVar(value="No file selected")
        vite_db_content_frame = tk.Frame(vite_db_frame, bg=COLORS["bg_accent"])
        vite_db_expanded = {"val": False}

        def _get_vite_db_config():
            return {
                "db_name": vite_db_name_var.get().strip(),
                "db_user": vite_db_user_var.get().strip(),
                "db_pass": vite_db_pass_var.get(),
                "db_host": vite_db_host_var.get().strip(),
                "sql_path": vite_sql_path_var.get(),
            }

        def _mark_db_completed(kind: str):
            db_step_state[kind] = True
            if kind == "vite":
                db_step_state["vite_skipped"] = False
            _update_next_button_state()

        def _skip_vite_db():
            db_step_state["vite"] = True
            db_step_state["vite_skipped"] = True
            append_log("Vite database setup marked as skipped.")
            _update_next_button_state()

        def _build_vite_db_section():

            db_card = tk.Frame(vite_db_content_frame, bg=COLORS["bg_accent"], padx=12, pady=10)
            db_card.pack(fill="x", pady=(0, 6))

            tk.Label(
                db_card, text="Database Credentials",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 6))

            db_grid = tk.Frame(db_card, bg=COLORS["bg_accent"])
            db_grid.pack(fill="x")
            db_grid.columnconfigure(1, weight=1)
            db_grid.columnconfigure(3, weight=1)

            for lbl_text, var, row, col in [
                ("DB Name:",  vite_db_name_var, 0, 0),
                ("DB Host:",  vite_db_host_var, 0, 2),
                ("DB User:",  vite_db_user_var, 1, 0),
                ("DB Pass:",  vite_db_pass_var, 1, 2),
            ]:
                tk.Label(
                    db_grid, text=lbl_text,
                    font=("Segoe UI", 9, "bold"),
                    bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
                ).grid(row=row, column=col, sticky="w",
                       padx=(12 if col == 2 else 0, 4), pady=3)
                e = tk.Entry(
                    db_grid, textvariable=var,
                    font=("Segoe UI", 9), relief="flat",
                    bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
                    insertbackground=COLORS["text_primary"],
                )
                if "Pass" in lbl_text:
                    e.configure(show="\u2022")
                e.grid(row=row, column=col + 1, sticky="ew", ipady=4, pady=3)


            sql_card = tk.Frame(vite_db_content_frame, bg=COLORS["bg_accent"], padx=12, pady=10)
            sql_card.pack(fill="x", pady=(0, 6))

            tk.Label(
                sql_card, text="Import SQL File (optional)",
                font=("Segoe UI", 9, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            ).pack(anchor="w", pady=(0, 6))

            sql_row = tk.Frame(sql_card, bg=COLORS["bg_accent"])
            sql_row.pack(fill="x")

            sql_name_lbl = tk.Label(
                sql_row, textvariable=vite_sql_label_var,
                font=("Segoe UI", 9), bg=COLORS["bg_accent"],
                fg=COLORS["text_secondary"], anchor="w",
            )
            sql_name_lbl.pack(side="left", fill="x", expand=True)

            def _browse_sql():
                path = filedialog.askopenfilename(
                    title="Select SQL File",
                    filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
                    parent=dialog,
                )
                if path:
                    vite_sql_path_var.set(path)
                    vite_sql_label_var.set(os.path.basename(path))
                    sql_name_lbl.configure(fg=COLORS["text_primary"])

            tk.Button(
                sql_row, text="\U0001f4c2  Browse SQL",
                font=("Segoe UI", 9), relief="flat", cursor="hand2",
                bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                activebackground=COLORS.get("accent", "#1a3a5c"),
                activeforeground="white",
                command=_browse_sql,
            ).pack(side="right", ipadx=8, ipady=3)


            btn_row = tk.Frame(vite_db_content_frame, bg=COLORS["bg_accent"])
            btn_row.pack(fill="x", pady=(4, 4))
            btn_row.columnconfigure(0, weight=1)
            btn_row.columnconfigure(1, weight=1)

            vite_actions = [
                (
                    "\U0001f5c4  Create Database",
                    "#1565C0",
                    "#1256A8",
                    lambda: (_mark_db_completed("vite"), self.vite_create_db(domain, _get_vite_db_config(), append_log)),
                ),
                (
                    "\u2b06  Upload & Import SQL",
                    "#2E7D32",
                    "#256B28",
                    lambda: (_mark_db_completed("vite"), self.vite_upload_sql(domain, _get_vite_db_config(), append_log)),
                ),
                (
                    "\U0001f4be  Save .env to Server",
                    "#E65100",
                    "#CC4700",
                    lambda: self.vite_generate_env(domain, _get_vite_db_config(), append_log),
                ),
            ]
            for idx, (text, bg, hover, cmd) in enumerate(vite_actions):
                tk.Button(
                    btn_row,
                    text=text,
                    font=("Segoe UI", 9, "bold"),
                    relief="flat",
                    cursor="hand2",
                    bg=bg,
                    fg="white",
                    activebackground=hover,
                    activeforeground="white",
                    command=cmd,
                ).grid(
                    row=idx // 2,
                    column=idx % 2,
                    sticky="ew",
                    padx=(0, 6) if idx % 2 == 0 else 0,
                    pady=3,
                    ipady=5,
                )

            tk.Button(
                vite_db_content_frame,
                text="Skip Vite Database Setup",
                font=("Segoe UI", 9), relief="flat", cursor="hand2",
                bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
                command=_skip_vite_db,
            ).pack(anchor="e", pady=(4, 0), ipadx=8, ipady=4)

        def _toggle_vite_db():
            vite_db_expanded["val"] = not vite_db_expanded["val"]
            if vite_db_expanded["val"]:
                vite_db_toggle_btn.configure(
                    text="\u25BC  Database Setup  \u25BC",
                    bg="#1565C0", activebackground="#1256A8",
                )
                vite_db_content_frame.pack(fill="x", pady=(6, 0))
                if not vite_db_content_frame.winfo_children():
                    _build_vite_db_section()
            else:
                vite_db_toggle_btn.configure(
                    text="\u25B6  Database Setup (optional)",
                    bg=COLORS["bg_secondary"], activebackground="#0a2a4a",
                )
                vite_db_content_frame.pack_forget()

        vite_db_toggle_btn = tk.Button(
            vite_db_frame,
            text="\u25B6  Database Setup (optional)",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg="white",
            activebackground="#0a2a4a", activeforeground="white",
            anchor="w", padx=12,
            command=_toggle_vite_db,
        )
        vite_db_toggle_btn.pack(fill="x", ipady=6)

        def _resize_dialog(expand: bool):
            """Update framework-expanded state and recompute dialog geometry."""
            _framework_expanded["val"] = expand
            _update_dialog_geometry()

        def _reset_wp_panel():
            wp_setup_frame.pack_forget()
            for child in wp_content_frame.winfo_children():
                child.destroy()
            wp_content_frame.pack_forget()
            wp_expanded["val"] = False
            wp_toggle_btn.configure(
                text="\u25B6  WordPress Setup Tools",
                bg=COLORS["bg_secondary"], activebackground="#0a2a4a",
            )

        def _reset_vite_panel():
            vite_db_frame.pack_forget()
            for child in vite_db_content_frame.winfo_children():
                child.destroy()
            vite_db_content_frame.pack_forget()
            vite_db_expanded["val"] = False
            vite_db_toggle_btn.configure(
                text="\u25B6  Database Setup (optional)",
                bg=COLORS["bg_secondary"], activebackground="#0a2a4a",
            )

        def _rebuild_deps(event=None):
            for w in dep_frame.winfo_children():
                w.destroy()
            dep_vars.clear()
            fw = framework_var.get()
            deps = _framework_deps.get(fw, [])


            if fw == "None":
                _resize_dialog(expand=False)
                _reset_wp_panel()
                _reset_vite_panel()
            elif fw == "WordPress (CMS)":
                _resize_dialog(expand=True)
                _reset_vite_panel()
                wp_setup_frame.pack(fill="both", expand=True)
            elif fw == "Vite (Modern Frontend)":
                _resize_dialog(expand=True)
                _reset_wp_panel()
                vite_db_frame.pack(fill="both", expand=True)

            if not deps:
                return

            if fw == "WordPress (CMS)" and isinstance(deps, dict):
                plugin_list = deps.get("plugins", [])
                theme_list = deps.get("themes", [])

                if plugin_list:
                    tk.Label(
                        dep_frame, text="Plugins",
                        font=("Segoe UI", 9, "bold"),
                        bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                    ).pack(anchor="w", pady=(0, 4))

                    plugin_grid = tk.Frame(dep_frame, bg=COLORS["bg_accent"])
                    plugin_grid.pack(fill="x", pady=(0, 8))
                    plugin_grid.columnconfigure(0, weight=1)
                    for idx, (key, label) in enumerate(plugin_list):
                        var = tk.BooleanVar(value=False)
                        dep_vars[key] = var
                        tk.Checkbutton(
                            plugin_grid, text=label, variable=var,
                            font=("Segoe UI", 9),
                            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                            selectcolor=COLORS["bg_primary"],
                            activebackground=COLORS["bg_accent"],
                            activeforeground=COLORS["text_primary"],
                            anchor="w",
                        ).grid(row=idx, column=0, sticky="w", padx=(0, 6), pady=2)

                if theme_list:
                    tk.Label(
                        dep_frame, text="Themes",
                        font=("Segoe UI", 9, "bold"),
                        bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                    ).pack(anchor="w", pady=(0, 4))

                    theme_grid = tk.Frame(dep_frame, bg=COLORS["bg_accent"])
                    theme_grid.pack(fill="x")
                    theme_grid.columnconfigure(0, weight=1)
                    for idx, (key, label) in enumerate(theme_list):
                        var = tk.BooleanVar(value=False)
                        dep_vars[key] = var
                        tk.Checkbutton(
                            theme_grid, text=label, variable=var,
                            font=("Segoe UI", 9),
                            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                            selectcolor=COLORS["bg_primary"],
                            activebackground=COLORS["bg_accent"],
                            activeforeground=COLORS["text_primary"],
                            anchor="w",
                        ).grid(row=idx, column=0, sticky="w", padx=(0, 6), pady=2)
                return

            grid = tk.Frame(dep_frame, bg=COLORS["bg_accent"])
            grid.pack(fill="x")
            grid.columnconfigure(0, weight=1)
            for idx, (key, label) in enumerate(deps):
                var = tk.BooleanVar(value=False)
                dep_vars[key] = var
                tk.Checkbutton(
                    grid, text=label, variable=var,
                    font=("Segoe UI", 9),
                    bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
                    selectcolor=COLORS["bg_primary"],
                    activebackground=COLORS["bg_accent"],
                    activeforeground=COLORS["text_primary"],
                    anchor="w",
                ).grid(row=idx, column=0, sticky="w", padx=(0, 6), pady=2)

        framework_dropdown.bind("<<ComboboxSelected>>", _rebuild_deps)

        wizard_status_var = tk.StringVar(value="Step 1 of 6 - Git Repository")
        wizard_status_lbl = tk.Label(
            _settings_pad,
            textvariable=wizard_status_var,
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"],
            fg=COLORS["text_secondary"],
            anchor="w",
        )
        wizard_status_lbl.pack(fill="x", pady=(6, 0))

        wizard_progress = tk.Frame(_settings_pad, bg=COLORS["bg_primary"])
        wizard_progress.pack(fill="x", pady=(6, 6))
        wizard_dots = []
        for idx in range(1, 7):
            dot = tk.Label(
                wizard_progress,
                text=str(idx),
                font=("Segoe UI", 8, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
                width=3, height=1,
            )
            dot.pack(side="left", padx=(0, 6))
            wizard_dots.append(dot)


        fields = tk.Frame(step6_frame, bg=COLORS["bg_secondary"])
        fields.pack(fill="x", padx=0)
        fields.pack_forget()

        step6_note = tk.Label(
            step6_frame,
            text="Fresh WordPress install does not require a local upload folder.",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"],
            fg=COLORS["text_secondary"],
            anchor="w",
            justify="left",
            wraplength=560,
        )


        tk.Label(
            fields, text="Project Folder", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        folder_row = tk.Frame(fields, bg=COLORS["bg_primary"])
        folder_row.pack(fill="x", pady=(0, 10))

        folder_var = tk.StringVar(value="No folder selected")
        tk.Entry(
            folder_row, textvariable=folder_var, state="readonly",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            readonlybackground=COLORS["bg_secondary"],
        ).pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))

        def browse():
            path = filedialog.askdirectory(
                title="Select project folder to upload", parent=dialog,
            )
            if path:
                folder_var.set(path)

        tk.Button(
            folder_row, text="Browse\u2026",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["accent"],
            command=browse,
        ).pack(side="right", ipady=5, ipadx=10)


        tk.Label(
            fields, text="Commit Message", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        commit_var = tk.StringVar(value="Upload project files")
        tk.Entry(
            fields, textvariable=commit_var,
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        ).pack(fill="x", ipady=6, pady=(0, 6))


        def _prefill_remote():
            """Background: check if the subdomain already has a remote and fill URL."""
            try:
                client = self.ssh.connect()
                if not client:
                    return
                is_repo = self.git_manager.is_git_repo(client, domain)
                if is_repo:
                    has_remote, remote_url = self.git_manager.get_remote_info(client, domain)
                    if has_remote and remote_url:
                        clean = self.git_manager._clean_remote_url(remote_url)
                        self.root.after(0, lambda u=clean: url_var.set(u))
                client.close()
            except Exception:
                pass

        threading.Thread(target=_prefill_remote, daemon=True).start()


        log_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        log_frame.pack(fill="x", expand=False, padx=22, pady=(8, 0))

        log_box = scrolledtext.ScrolledText(
            log_frame, height=4, state="disabled",
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            relief="flat", wrap="word",
        )
        log_box.pack(fill="x", expand=False)

        def set_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        def append_log(msg):
            def _apply():
                log_box.configure(state="normal")
                log_box.insert("end", msg + "\n")
                log_box.see("end")
                log_box.configure(state="disabled")
            self.root.after(0, _apply)


        btn_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        btn_frame.pack(fill="x", padx=22, pady=12)

        upload_btn = tk.Button(
            btn_frame, text="\u2b06  Upload & Push",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["success"], fg="white",
            activebackground=COLORS["success"],
        )
        upload_btn.pack(side="left", ipadx=14, ipady=6)
        upload_btn.pack_forget()

        back_btn = tk.Button(
            btn_frame, text="Back",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
        )
        back_btn.pack(side="left", ipadx=14, ipady=6, padx=(0, 8))

        next_btn = tk.Button(
            btn_frame, text="Next",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["accent"], activeforeground="white",
        )
        next_btn.pack(side="left", ipadx=14, ipady=6)

        tk.Button(
            btn_frame, text="Close",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            command=dialog.destroy,
        ).pack(side="right", ipadx=14, ipady=6)

        def start_upload():
            local_path = folder_var.get()
            if not local_path or local_path == "No folder selected":
                messagebox.showwarning(
                    "No Folder Selected", "Please choose a folder first.",
                    parent=dialog,
                )
                return
            if not os.path.isdir(local_path):
                messagebox.showerror(
                    "Invalid Folder",
                    f"The folder does not exist:\n{local_path}",
                    parent=dialog,
                )
                return

            fw_mapping = {
                "None": "none",
                "Vite (Modern Frontend)": "vite",
                "WordPress (CMS)": "wordpress",
            }
            selected_fw = fw_mapping.get(framework_var.get(), "none")
            selected_deps = [k for k, v in dep_vars.items() if v.get()]

            upload_btn.configure(state="disabled", text="Uploading\u2026")
            threading.Thread(
                target=self._do_upload_project,
                args=(
                    domain,
                    local_path,
                    url_var.get().strip(),
                    token_var.get().strip(),
                    commit_var.get().strip() or "Upload project files",
                    append_log,
                    lambda: upload_btn.configure(
                        state="normal", text="\u2b06  Upload & Push"
                    ),
                ),
                kwargs={
                    "clean_first": clean_var.get(),
                    "force_push": force_push_var.get(),
                    "framework": selected_fw,
                    "dependencies": selected_deps,
                    "branch": branch_var.get().strip() or "main",
                },
                daemon=True,
            ).start()

        def _can_advance(step: int) -> bool:
            fw = framework_var.get()

            if step == 3 and fw == "WordPress (CMS)" and wp_mode_var.get() not in {"upload_existing", "install_fresh"}:
                messagebox.showwarning(
                    "WordPress Mode Required",
                    "Select whether you are uploading an existing WordPress project or installing fresh.",
                    parent=dialog,
                )
                return False

            if step == 5:
                if fw == "WordPress (CMS)" and not db_step_state.get("wordpress"):
                    messagebox.showwarning(
                        "Database Step Required",
                        "Run at least one WordPress database action in Step 5 or click Skip WordPress Database Setup.",
                        parent=dialog,
                    )
                    return False
                if fw == "Vite (Modern Frontend)" and not db_step_state.get("vite"):
                    messagebox.showwarning(
                        "Database Step Required",
                        "Run a Vite database action or click Skip Vite Database Setup in Step 5.",
                        parent=dialog,
                    )
                    return False
            return True

        def _is_step_valid(step: int) -> bool:
            fw = framework_var.get()
            if step == 3 and fw == "WordPress (CMS)" and wp_mode_var.get() not in {"upload_existing", "install_fresh"}:
                return False
            if step == 5:
                if fw == "WordPress (CMS)" and not db_step_state.get("wordpress"):
                    return False
                if fw == "Vite (Modern Frontend)" and not db_step_state.get("vite"):
                    return False
            return True

        def _update_wizard_progress():
            step = wizard_step["value"]
            for idx, dot in enumerate(wizard_dots, start=1):
                if idx == step:
                    dot.config(bg=COLORS["accent"], fg="white")
                else:
                    dot.config(bg=COLORS["bg_accent"], fg=COLORS["text_secondary"])

        def _update_next_button_state():
            step = wizard_step["value"]
            if step >= 6:
                next_btn.configure(state="disabled")
                return
            next_btn.configure(state="normal" if _is_step_valid(step) else "disabled")

        def _apply_step_layout(step: int):
            for frame in (step1_frame, step2_frame, step3_frame, step4_frame, step5_frame, step6_frame):
                frame.pack_forget()

            fields.pack_forget()
            columns_container.pack_forget()

            if step == 1:
                step1_frame.pack(fill="x", pady=(0, 8))
            elif step == 2:
                step2_frame.pack(fill="x", pady=(0, 8))
            elif step == 3:
                step3_frame.pack(fill="x", pady=(0, 8))
            elif step == 4:
                step4_frame.pack(fill="x", pady=(0, 8))
                if framework_var.get() != "None":
                    columns_container.pack(fill="x", pady=(8, 0))
                    right_column.grid_remove()
                    left_column.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=(0, 0))
            elif step == 5:
                step5_frame.pack(fill="x", pady=(0, 8))
                if framework_var.get() != "None":
                    columns_container.pack(fill="x", pady=(8, 0))
                left_column.grid_remove()
                right_column.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=(0, 0))
            elif step == 6:
                step6_frame.pack(fill="x", pady=(0, 8))
                fields.pack(fill="x", padx=0)

        def _refresh_step_ui():
            step = wizard_step["value"]
            total = 6
            step_titles = {
                1: "Git Repository",
                2: "Upload Options",
                3: "Framework Mode",
                4: "Dependencies",
                5: "Database Setup",
                6: "Final Upload",
            }
            wizard_status_var.set(f"Step {step} of {total} - {step_titles.get(step, '')}")
            _apply_step_layout(step)

            if step <= 2:
                log_box.configure(height=3)
                log_frame.pack(fill="x", expand=False, padx=22, pady=(8, 0), before=btn_frame)
                log_box.pack(fill="x", expand=False)
            elif step in (3, 4, 5):
                log_box.configure(height=4)
                log_frame.pack(fill="x", expand=False, padx=22, pady=(8, 0), before=btn_frame)
                log_box.pack(fill="x", expand=False)
            else:
                log_box.configure(height=8)
                log_frame.pack(fill="both", expand=True, padx=22, pady=(8, 0), before=btn_frame)
                log_box.pack(fill="both", expand=True)

            _on_settings_inner_cfg(None)
            btn_frame.lift()

            fw = framework_var.get()
            wp_mode_box.pack_forget()
            if fw == "WordPress (CMS)":
                wp_mode_box.pack(fill="x", pady=(4, 0))

            if step == 6 and fw == "WordPress (CMS)" and wp_mode_var.get() == "install_fresh":
                fields.pack_forget()
                step6_note.pack(fill="x", pady=(2, 6))
            else:
                step6_note.pack_forget()

            back_btn.configure(state="normal" if step > 1 else "disabled")

            if step < 6:
                next_btn.pack(side="left", ipadx=14, ipady=6)
                next_btn.configure(text="Next")
                upload_btn.pack_forget()
            else:
                next_btn.pack_forget()
                upload_btn.pack(side="left", ipadx=14, ipady=6)

                if fw == "WordPress (CMS)" and wp_mode_var.get() == "install_fresh":
                    upload_btn.configure(
                        text="Install WordPress",
                        command=_run_wp_install,
                    )
                else:
                    upload_btn.configure(
                        text="\u2b06  Upload & Push",
                        command=start_upload,
                    )

            _update_wizard_progress()
            _update_next_button_state()

        def _go_next():
            step = wizard_step["value"]
            if step >= 6:
                return
            if not _can_advance(step):
                return
            wizard_step["value"] += 1
            _refresh_step_ui()

        def _go_back():
            if wizard_step["value"] <= 1:
                return
            wizard_step["value"] -= 1
            _refresh_step_ui()

        back_btn.configure(command=_go_back)
        next_btn.configure(command=_go_next)

        def _on_framework_changed(event=None):
            _rebuild_deps(event)
            _refresh_step_ui()

        framework_dropdown.bind("<<ComboboxSelected>>", _on_framework_changed)
        wp_mode_var.trace_add("write", lambda *_: _refresh_step_ui())
        _rebuild_deps()
        _refresh_step_ui()

