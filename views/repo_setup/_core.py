"""
Repository Setup Page — base class with layout, getters, setters, and lifecycle.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog

from models.config import COLORS, get_github_token
from views.widgets import ModernEntry, ModernButton, RoundedFrame
from views.repo_setup._helpers import _create_label


class RepoSetupPageViewBase:
    """Self-contained page frame for repository setup and Git sync operations.
    The controller binds button callbacks after construction."""

    def __init__(self, parent):

        self.frame = tk.Frame(parent, bg=COLORS["bg_primary"])


        self._git_initialized = False
        self._remote_connected = False
        self._status_checked = False

        self._build()


    def _build(self):
        container = tk.Frame(self.frame, bg=COLORS["bg_primary"], padx=24, pady=16)
        container.pack(fill="both", expand=True)


        title_bar = tk.Frame(container, bg=COLORS["bg_primary"])
        title_bar.pack(fill="x", pady=(0, 12))

        tk.Label(
            title_bar, text="Repository Setup & Git Sync",
            font=("Segoe UI", 16, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(side="left")


        content_frame = tk.Frame(container, bg=COLORS["bg_primary"])
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=2, minsize=450)
        content_frame.columnconfigure(1, weight=1, minsize=300)
        content_frame.rowconfigure(0, weight=1)


        self._build_setup_section(content_frame)


        self._build_status_section(content_frame)

    def _build_setup_section(self, parent):
        """Build the repository setup form section."""
        setup_card = RoundedFrame(
            parent, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        setup_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))


        _card_inner = setup_card.inner

        self._setup_canvas = tk.Canvas(
            _card_inner, bg=COLORS["bg_secondary"],
            highlightthickness=0, bd=0,
        )
        self._setup_scrollbar = tk.Scrollbar(
            _card_inner, orient="vertical",
            command=self._setup_canvas.yview,
            bg=COLORS["bg_secondary"], troughcolor=COLORS["bg_accent"],
            activebackground=COLORS["accent"], highlightthickness=0,
            bd=0, width=8,
        )
        self._setup_canvas.configure(yscrollcommand=self._setup_scrollbar.set)
        self._setup_scrollbar.pack(side="right", fill="y")
        self._setup_canvas.pack(side="left", fill="both", expand=True)

        setup_section = tk.Frame(self._setup_canvas, bg=COLORS["bg_secondary"])
        self._setup_canvas_window = self._setup_canvas.create_window(
            (0, 0), window=setup_section, anchor="nw",
        )

        def _on_inner_configure(event):
            self._setup_canvas.configure(scrollregion=self._setup_canvas.bbox("all"))

        def _on_canvas_configure(event):
            self._setup_canvas.itemconfig(self._setup_canvas_window, width=event.width)

        setup_section.bind("<Configure>", _on_inner_configure)
        self._setup_canvas.bind("<Configure>", _on_canvas_configure)


        def _on_mousewheel(event):
            self._setup_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self._setup_canvas.bind(
            "<Enter>",
            lambda e: self._setup_canvas.bind_all("<MouseWheel>", _on_mousewheel),
        )
        self._setup_canvas.bind(
            "<Leave>",
            lambda e: self._setup_canvas.unbind_all("<MouseWheel>"),
        )


        header_row = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        header_row.pack(fill="x", pady=(0, 10))

        _create_label(header_row, "Repository Configuration", 12, True, "text_primary").pack(side="left")

        self._settings_btn = tk.Button(
            header_row, text="\u2699",
            font=("Segoe UI", 14), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
            bd=0, highlightthickness=0,
            command=self._open_token_settings,
        )
        self._settings_btn.pack(side="right")

        self._setup_step = 1
        self._deps_skipped = False
        self._db_skipped = False
        self._db_step_done = False

        self._step_indicator_label = tk.Label(
            setup_section,
            text="Step 1 of 5: Subdomain & Branch",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_secondary"],
            fg=COLORS["warning"],
            anchor="w",
        )
        self._step_indicator_label.pack(fill="x", pady=(0, 8))

        self._progress_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        self._progress_frame.pack(fill="x", pady=(0, 10))
        self._progress_dots = []
        for idx in range(1, 6):
            dot = tk.Label(
                self._progress_frame,
                text=str(idx),
                font=("Segoe UI", 8, "bold"),
                bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
                width=3, height=1,
            )
            dot.pack(side="left", padx=(0, 6))
            self._progress_dots.append(dot)

        self._step1_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        self._step2_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        self._step3_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        self._step4_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        self._step5_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        for frm in (self._step1_frame, self._step2_frame, self._step3_frame, self._step4_frame, self._step5_frame):
            frm.pack(fill="x", pady=(0, 6))


        subdomain_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        subdomain_frame.pack(fill="x", pady=(0, 10))

        _create_label(subdomain_frame, "Select Subdomain", 10, True).pack(anchor="w")

        self.subdomain_var = tk.StringVar(value="-- Select Subdomain --")
        self.subdomain_dropdown = ttk.Combobox(
            subdomain_frame, textvariable=self.subdomain_var, state="readonly",
            font=("Segoe UI", 10), width=35,
        )
        self.subdomain_dropdown["values"] = ["-- Select Subdomain --"]
        self.subdomain_dropdown.pack(fill="x", pady=(4, 0), ipady=4)
        self.subdomain_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_next_button_state())


        row1 = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        row1.pack(fill="x", pady=(10, 10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)


        repo_url_frame = tk.Frame(row1, bg=COLORS["bg_secondary"])
        repo_url_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        _create_label(repo_url_frame, "Repository URL (GitHub)", 10, True).pack(anchor="w")
        _create_label(
            repo_url_frame,
            "e.g., https://github.com/user/repo.git",
            8, False, "text_secondary"
        ).pack(anchor="w")

        self.repo_url_entry = ModernEntry(repo_url_frame, font=("Segoe UI", 11), width=30)
        self.repo_url_entry.pack(fill="x", pady=(4, 0), ipady=4)
        self.repo_url_entry.bind("<KeyRelease>", lambda e: self._update_next_button_state())


        token_status_frame = tk.Frame(row1, bg=COLORS["bg_secondary"])
        token_status_frame.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        _create_label(token_status_frame, "GitHub Token", 10, True).pack(anchor="w")

        self._token_status_label = tk.Label(
            token_status_frame,
            text="",
            font=("Segoe UI", 9),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            anchor="w",
        )
        self._token_status_label.pack(anchor="w", pady=(4, 0))
        self._refresh_token_status()


        branch_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        branch_frame.pack(fill="x", pady=(0, 10))

        _create_label(branch_frame, "Branch", 10, True).pack(anchor="w")
        _create_label(
            branch_frame,
            "Select branch for pull / sync operations",
            8, False, "text_secondary"
        ).pack(anchor="w")

        branch_row = tk.Frame(branch_frame, bg=COLORS["bg_secondary"])
        branch_row.pack(fill="x", pady=(4, 0))

        self.branch_var = tk.StringVar(value="main")
        self.branch_dropdown = ttk.Combobox(
            branch_row, textvariable=self.branch_var, state="readonly",
            font=("Segoe UI", 10), width=20,
        )
        self.branch_dropdown["values"] = ["main"]
        self.branch_dropdown.pack(side="left", fill="x", expand=True, ipady=4)
        self.branch_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_next_button_state())

        self.refresh_branches_btn = tk.Button(
            branch_row, text="\u21bb",
            font=("Segoe UI", 12), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            activebackground=COLORS["bg_secondary"],
            activeforeground=COLORS["text_primary"],
            bd=0, highlightthickness=0,
        )
        self.refresh_branches_btn.pack(side="left", padx=(6, 0))


        framework_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        framework_frame.pack(fill="x", pady=(10, 0))

        _create_label(framework_frame, "Install Framework (Optional)", 10, True).pack(anchor="w")
        _create_label(
            framework_frame,
            "Select a framework and its dependencies to install during setup",
            8, False, "text_secondary"
        ).pack(anchor="w")


        self.framework_var = tk.StringVar(value="None")
        self.framework_dropdown = ttk.Combobox(
            framework_frame, textvariable=self.framework_var, state="readonly",
            font=("Segoe UI", 10), width=35,
        )
        self.framework_dropdown["values"] = [
            "None",
            "Vite (Modern Frontend)",
            "WordPress (CMS)",
        ]
        self.framework_dropdown.pack(fill="x", pady=(6, 0), ipady=4)
        self.framework_dropdown.bind("<<ComboboxSelected>>", self._on_framework_changed)


        self._dep_frame = tk.Frame(framework_frame, bg=COLORS["bg_secondary"])
        self._dep_frame.pack(fill="x", pady=(6, 0))


        self._wp_setup_frame = tk.Frame(framework_frame, bg=COLORS["bg_secondary"])
        self._wp_setup_widgets: list[tk.Widget] = []
        self._wp_btn_commands: dict[str, object] = {}


        self._wp_db_name_var = tk.StringVar()
        self._wp_db_user_var = tk.StringVar(value="root")
        self._wp_db_pass_var = tk.StringVar()
        self._wp_db_host_var = tk.StringVar(value="localhost")
        self._wp_sql_path_var = tk.StringVar(value="No file selected")
        self._wp_sql_file_label_var = tk.StringVar(value="No file selected")


        self._vite_db_frame = tk.Frame(framework_frame, bg=COLORS["bg_secondary"])
        self._vite_db_widgets: list[tk.Widget] = []
        self._vite_db_btn_commands: dict[str, object] = {}


        self._vite_db_name_var = tk.StringVar()
        self._vite_db_user_var = tk.StringVar(value="root")
        self._vite_db_pass_var = tk.StringVar()
        self._vite_db_host_var = tk.StringVar(value="localhost")
        self._vite_sql_path_var = tk.StringVar(value="No file selected")
        self._vite_sql_file_label_var = tk.StringVar(value="No file selected")


        self._framework_deps = {
            "Vite (Modern Frontend)": [
                ("tailwindcss",    "Tailwind CSS",  "Utility-first CSS framework"),
                ("typescript",     "TypeScript",     "Typed JavaScript superset"),
                ("sass",           "Sass / SCSS",    "CSS pre-processor"),
                ("eslint",         "ESLint",         "JavaScript linter"),
                ("prettier",       "Prettier",       "Code formatter"),
                ("axios",          "Axios",          "HTTP client library"),
                ("react",          "React",          "UI component library"),
                ("vue",            "Vue",            "Progressive JS framework"),
            ],
            "WordPress (CMS)": {
                "themes": [
                    ("theme-astra", "Astra", "Lightweight multipurpose theme"),
                    ("theme-generatepress", "GeneratePress", "Performance-focused theme"),
                    ("theme-kadence", "Kadence", "Flexible modern theme"),
                    ("theme-neve", "Neve", "Fast starter theme"),
                ],
                "plugins": [
                    ("wp-cli", "WP-CLI", "WordPress command-line tool"),
                    ("woocommerce", "WooCommerce", "E-commerce plugin"),
                    ("elementor", "Elementor", "Page builder plugin"),
                    ("yoast-seo", "Yoast SEO", "SEO optimization plugin"),
                    ("wordfence", "Wordfence", "Security plugin"),
                    ("contact-form-7", "Contact Form 7", "Form management plugin"),
                ],
            },
        }


        self._dep_vars: dict[str, tk.BooleanVar] = {}
        self._dep_widgets: list[tk.Widget] = []


        self._rebuild_dep_checkboxes()


        button_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        button_frame.pack(fill="x", pady=(20, 10))

        self.sync_action_btn = ModernButton(
            button_frame, text="Pull & Sync", command=None,
            bg_color="#7B1FA2", hover_color="#6A1B9A",
            border_color="#4A148C", width=150, height=34,
        )
        self.sync_action_btn.pack(side="left", padx=(0, 10))

        self.commit_push_btn = ModernButton(
            button_frame, text="Commit & Push", command=None,
            bg_color=COLORS["success"], hover_color="#3db892",
            border_color="#3da17f", width=150, height=34,
        )
        self.commit_push_btn.pack(side="left")


        editor_row = tk.Frame(setup_section, bg=COLORS["bg_secondary"])

        self.editor_btn = tk.Button(
            editor_row, text="\U0001f4c2  File Editor",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg="#455A64", fg="white",
            activebackground="#546E7A", activeforeground="white",
            state="disabled",
        )
        self.editor_btn.pack(side="left", ipadx=10, ipady=6)


        commit_frame = tk.Frame(setup_section, bg=COLORS["bg_secondary"])
        commit_frame.pack(fill="x", pady=(10, 0))

        _create_label(commit_frame, "Commit Message", 10, True).pack(anchor="w")

        self.commit_msg_entry = ModernEntry(commit_frame, font=("Segoe UI", 11), width=50)
        self.commit_msg_entry.insert(0, "Update from server")
        self.commit_msg_entry.pack(fill="x", pady=(4, 0), ipady=4)

        self._deps_skip_btn = tk.Button(
            self._step3_frame,
            text="Skip Dependencies",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
            command=self._skip_dependencies_step,
        )

        self._db_skip_btn = tk.Button(
            self._step4_frame,
            text="Skip Database Setup",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
            command=self._skip_database_step,
        )

        self._wizard_nav_row = tk.Frame(_card_inner, bg=COLORS["bg_secondary"], padx=12, pady=8)
        self._wizard_nav_row.pack(side="bottom", fill="x")

        self._prev_step_btn = tk.Button(
            self._wizard_nav_row, text="\u2190 Back",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground="#0a2a4a", activeforeground=COLORS["text_primary"],
            command=lambda: self._go_setup_step(self._setup_step - 1),
        )
        self._prev_step_btn.pack(side="left", ipadx=8, ipady=5)

        self._next_step_btn = tk.Button(
            self._wizard_nav_row, text="Next \u2192",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["button_hover"], activeforeground="white",
            command=self._go_next_setup_step,
        )
        self._next_step_btn.pack(side="left", padx=(8, 0), ipadx=8, ipady=5)

        self._setup_blocks = {
            1: [
                (subdomain_frame, {"fill": "x", "pady": (0, 10)}),
                (row1, {"fill": "x", "pady": (10, 10)}),
                (branch_frame, {"fill": "x", "pady": (0, 10)}),
                (editor_row, {"fill": "x", "pady": (10, 0)}),
            ],
            2: [
                (framework_frame, {"fill": "x", "pady": (10, 0)}),
            ],
            3: [
                (framework_frame, {"fill": "x", "pady": (10, 0)}),
            ],
            4: [
                (framework_frame, {"fill": "x", "pady": (10, 0)}),
            ],
            5: [
                (button_frame, {"fill": "x", "pady": (20, 10)}),
                (editor_row, {"fill": "x", "pady": (0, 8)}),
                (commit_frame, {"fill": "x", "pady": (10, 0)}),
            ],
        }

        self._go_setup_step(1)

    def _mark_db_step_completed(self):
        """Mark database setup step as completed by an explicit DB action."""
        self._db_step_done = True
        self._db_skipped = False
        self._update_next_button_state()

    def _skip_dependencies_step(self):
        """Allow advancing from dependencies step without selections."""
        self._deps_skipped = True
        self._go_setup_step(4)

    def _skip_database_step(self):
        """Allow advancing from database step without DB actions."""
        self._db_skipped = True
        self._db_step_done = False
        self._go_setup_step(5)

    def _go_next_setup_step(self):
        self._go_setup_step(self._setup_step + 1)

    def _can_advance_setup_step(self, step: int) -> bool:
        if step == 1:
            if self.get_selected_subdomain() == "":
                self.log("Please select a subdomain before continuing.", "warning")
                return False
            if not self.get_selected_branch():
                self.log("Please select a branch before continuing.", "warning")
                return False

        if step == 3:
            if self.framework_var.get() != "None":
                has_dep = any(v.get() for v in self._dep_vars.values())
                if not has_dep and not self._deps_skipped:
                    self.log("Select at least one dependency/theme/plugin or click Skip Dependencies.", "warning")
                    return False

        if step == 4:
            if self.framework_var.get() != "None":
                if not (self._db_step_done or self._db_skipped):
                    self.log("Run a database action or click Skip Database Setup before continuing.", "warning")
                    return False

        return True

    def _is_step_valid(self, step: int) -> bool:
        if step == 1:
            if self.get_selected_subdomain() == "":
                return False
            if not self.get_selected_branch():
                return False
            # Repo URL is optional; do not block Next if empty.

        if step == 3:
            if self.framework_var.get() != "None":
                has_dep = any(v.get() for v in self._dep_vars.values())
                if not has_dep and not self._deps_skipped:
                    return False

        if step == 4:
            if self.framework_var.get() != "None":
                if not (self._db_step_done or self._db_skipped):
                    return False

        return True

    def _update_progress_indicator(self):
        for idx, dot in enumerate(self._progress_dots, start=1):
            if idx == self._setup_step:
                dot.config(bg=COLORS["accent"], fg="white")
            else:
                dot.config(bg=COLORS["bg_accent"], fg=COLORS["text_secondary"])

    def _update_next_button_state(self):
        if not hasattr(self, "_next_step_btn"):
            return
        if self._setup_step >= 5:
            self._next_step_btn.configure(state="disabled")
            return
        self._next_step_btn.configure(state="normal" if self._is_step_valid(self._setup_step) else "disabled")

    def _refresh_setup_step_ui(self):
        step_titles = {
            1: "Step 1 of 5: Subdomain & Branch",
            2: "Step 2 of 5: Install Framework",
            3: "Step 3 of 5: Dependencies / Themes / Plugins",
            4: "Step 4 of 5: Database Setup",
            5: "Step 5 of 5: Pull with Logs",
        }
        self._step_indicator_label.configure(text=step_titles.get(self._setup_step, ""))

        for frame in (self._step1_frame, self._step2_frame, self._step3_frame, self._step4_frame, self._step5_frame):
            frame.pack_forget()
        active_frame = {
            1: self._step1_frame,
            2: self._step2_frame,
            3: self._step3_frame,
            4: self._step4_frame,
            5: self._step5_frame,
        }[self._setup_step]
        active_frame.pack(fill="x", pady=(0, 6))

        for blocks in self._setup_blocks.values():
            for widget, _opts in blocks:
                widget.pack_forget()

        for widget, opts in self._setup_blocks[self._setup_step]:
            widget.pack(in_=active_frame, **opts)

        if self._setup_step == 2:
            self._dep_frame.pack_forget()
            self._wp_setup_frame.pack_forget()
            self._vite_db_frame.pack_forget()

        if self._setup_step == 3:
            self._rebuild_dep_checkboxes()
            self._dep_frame.pack(fill="x", pady=(6, 0))
            self._wp_setup_frame.pack_forget()
            self._vite_db_frame.pack_forget()
            if self.framework_var.get() != "None":
                self._deps_skip_btn.pack(anchor="e", pady=(8, 0), ipadx=8, ipady=4)
            else:
                self._deps_skip_btn.pack_forget()
        else:
            self._deps_skip_btn.pack_forget()

        if self._setup_step == 4:
            self._dep_frame.pack_forget()
            self._rebuild_wp_setup_panel()
            self._rebuild_vite_db_panel()
            if self.framework_var.get() != "None":
                self._db_skip_btn.pack(anchor="e", pady=(8, 0), ipadx=8, ipady=4)
            else:
                self._db_skip_btn.pack_forget()
        else:
            self._db_skip_btn.pack_forget()

        self._prev_step_btn.configure(state="disabled" if self._setup_step == 1 else "normal")
        self._update_progress_indicator()
        self._update_next_button_state()

    def _go_setup_step(self, step: int):
        step = max(1, min(5, int(step)))
        if step > self._setup_step and not self._can_advance_setup_step(self._setup_step):
            return
        self._setup_step = step
        self._refresh_setup_step_ui()

    def _build_status_section(self, parent):
        """Build the sync status and log section."""
        status_card = RoundedFrame(
            parent, bg_color=COLORS["bg_secondary"],
            radius=14, padding=(12, 12),
        )
        status_card.grid(row=0, column=1, sticky="nsew")
        status_section = status_card.inner


        _create_label(status_section, "Sync Status", 12, True, "text_primary").pack(anchor="w", pady=(0, 10))


        status_frame = RoundedFrame(
            status_section, bg_color=COLORS["bg_accent"],
            radius=10, padding=(10, 10),
        )
        status_frame.pack(fill="x", pady=(0, 10))
        status_inner = status_frame.inner


        git_status_row = tk.Frame(status_inner, bg=COLORS["bg_accent"])
        git_status_row.pack(fill="x", pady=4)
        _create_label(git_status_row, "Git Repository:", 9, True).pack(side="left")
        self.git_status_label = tk.Label(
            git_status_row, text="Not checked",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        )
        self.git_status_label.pack(side="right")


        remote_status_row = tk.Frame(status_inner, bg=COLORS["bg_accent"])
        remote_status_row.pack(fill="x", pady=(6, 2))
        _create_label(remote_status_row, "Remote Connected:", 9, True).pack(anchor="w")
        self.remote_status_label = tk.Label(
            remote_status_row, text="Not checked",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
            anchor="w", justify="left", wraplength=280,
        )
        self.remote_status_label.pack(fill="x", pady=(2, 0))


        sync_status_row = tk.Frame(status_inner, bg=COLORS["bg_accent"])
        sync_status_row.pack(fill="x", pady=4)
        _create_label(sync_status_row, "Sync Status:", 9, True).pack(side="left")
        self.sync_status_label = tk.Label(
            sync_status_row, text="Not checked",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        )
        self.sync_status_label.pack(side="right")


        files_status_row = tk.Frame(status_inner, bg=COLORS["bg_accent"])
        files_status_row.pack(fill="x", pady=4)
        _create_label(files_status_row, "Local Changes:", 9, True).pack(side="left")
        self.files_status_label = tk.Label(
            files_status_row, text="Not checked",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
        )
        self.files_status_label.pack(side="right")


        status_btn_frame = tk.Frame(status_section, bg=COLORS["bg_secondary"])
        status_btn_frame.pack(fill="x", pady=(5, 10))

        self.check_status_btn = ModernButton(
            status_btn_frame, text="Check Status", command=None,
            bg_color="#0288D1", hover_color="#0277BD",
            border_color="#01579B", width=130, height=30,
        )
        self.check_status_btn.pack(side="left", padx=(0, 10))


        _create_label(status_section, "Git Activity Log:", 10, True).pack(anchor="w", pady=(10, 0))

        self.output_text = scrolledtext.ScrolledText(
            status_section, font=("Consolas", 9),
            bg="white", fg="black", wrap=tk.WORD, height=14,
        )
        self.output_text.pack(fill="both", expand=True, pady=(6, 0))


        self.clear_log_btn = ModernButton(
            status_section, text="Clear Log", command=None,
            bg_color=COLORS["bg_accent"], hover_color="#0a2a4a",
            border_color="#0a2540", width=100, height=26,
        )
        self.clear_log_btn.pack(pady=(6, 0))


    def log(self, message, tag="info"):
        """Write a message to the activity log."""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def clear_log(self):
        """Clear the activity log."""
        self.output_text.delete(1.0, tk.END)

    def set_subdomains(self, subdomains):
        """Update the subdomain dropdown with available subdomains."""
        values = ["-- Select Subdomain --"] + list(subdomains)
        self.subdomain_dropdown["values"] = values
        if self.subdomain_var.get() not in values:
            self.subdomain_var.set("-- Select Subdomain --")

    def update_git_status(self, initialized: bool):
        """Update the Git initialization status indicator."""
        self._git_initialized = initialized
        self._status_checked = True

        self.editor_btn.configure(state="normal")
        if initialized:
            self.git_status_label.config(text="Initialized", fg=COLORS["success"])
        else:
            self.git_status_label.config(text="Not Initialized", fg=COLORS["error"])

    def update_remote_status(self, connected: bool, url: str = ""):
        """Update the remote connection status indicator."""
        self._remote_connected = connected
        if connected:
            display_url = url[:30] + "..." if len(url) > 30 else url
            self.remote_status_label.config(text=display_url, fg=COLORS["success"])
        else:
            self.remote_status_label.config(text="Not Connected", fg=COLORS["error"])

    def update_sync_status(self, synced: bool, message: str = ""):
        """Update the sync status indicator."""
        if synced:
            self.sync_status_label.config(text="In Sync", fg=COLORS["success"])
        else:
            display_msg = message[:25] + "..." if len(message) > 25 else message
            self.sync_status_label.config(text=display_msg or "Out of Sync", fg=COLORS["warning"])

    def update_files_status(self, count: int):
        """Update the local changes count indicator."""
        if count == 0:
            self.files_status_label.config(text="No changes", fg=COLORS["success"])
        else:
            self.files_status_label.config(text=f"{count} file(s)", fg=COLORS["warning"])

    def reset_status(self):
        """Reset all status indicators to default state."""
        self._git_initialized = False
        self._remote_connected = False
        self._status_checked = False
        self.editor_btn.configure(state="disabled")
        self.git_status_label.config(text="Not checked", fg=COLORS["text_secondary"])
        self.remote_status_label.config(text="Not checked", fg=COLORS["text_secondary"])
        self.sync_status_label.config(text="Not checked", fg=COLORS["text_secondary"])
        self.files_status_label.config(text="Not checked", fg=COLORS["text_secondary"])

    def get_repo_url(self) -> str:
        """Get the repository URL from the input field."""
        return self.repo_url_entry.get().strip()

    def get_repo_name(self) -> str:
        """Get the repository name — no longer used, kept for compatibility."""
        return ""

    def get_selected_branch(self) -> str:
        """Get the currently selected branch from the dropdown."""
        return self.branch_var.get().strip() or "main"

    def set_branches(self, branches: list, current: str = ""):
        """Populate the branch dropdown with available branches."""
        if not branches:
            branches = ["main"]
        self.branch_dropdown["values"] = branches
        if current and current in branches:
            self.branch_var.set(current)
        elif self.branch_var.get() not in branches:
            self.branch_var.set(branches[0])

    def get_selected_subdomain(self) -> str:
        """Get the selected subdomain."""
        selected = self.subdomain_var.get()
        if selected == "-- Select Subdomain --":
            return ""
        return selected

    def get_selected_framework(self) -> str:
        """Get the selected framework key for installation.

        Returns 'none', 'vite', or 'wordpress'.
        """
        mapping = {
            "None": "none",
            "Vite (Modern Frontend)": "vite",
            "WordPress (CMS)": "wordpress",
        }
        return mapping.get(self.framework_var.get(), "none")

    def get_selected_dependencies(self) -> list[str]:
        """Return a list of dependency keys the user has checked."""
        return [key for key, var in self._dep_vars.items() if var.get()]

    def get_commit_message(self) -> str:
        """Get the commit message from the input field."""
        msg = self.commit_msg_entry.get().strip()
        return msg if msg else "Update from server"

    def get_github_token(self) -> str:
        """Get the GitHub Personal Access Token from .env."""
        return get_github_token()

    def get_upload_folder(self) -> str:
        """Get the upload folder path via a folder picker dialog."""
        folder = filedialog.askdirectory(title="Select Project Folder to Upload")
        return folder if folder else ""

    def show(self):
        """Show this page."""
        self.frame.pack(fill="both", expand=True)

    def hide(self):
        """Hide this page."""
        self.frame.pack_forget()
