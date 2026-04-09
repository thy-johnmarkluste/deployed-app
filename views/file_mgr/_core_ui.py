"""
File Manager — core UI construction, init, and cleanup.
"""
import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from models.config import COLORS


class FileManagerCoreMixin:
    """Modal SFTP file browser + inline editor dialog.

    Parameters
    ----------
    parent      : tk.Widget — parent window
    domain      : str — the subdomain (e.g. neo.veryapp.info)
    ssh_manager : SSHClientManager — used to open SSH/SFTP sessions
    git_manager : GitManager — used to resolve the server path
    """

    def __init__(self, parent, domain: str, ssh_manager, git_manager):
        self.domain      = domain
        self.ssh         = ssh_manager
        self.git_mgr     = git_manager
        self._subdomain_path = git_manager.get_subdomain_path(domain)
        self.root_path   = self._subdomain_path
        self._dirty      = False
        self._cur_path   = None
        self._sftp       = None
        self._client     = None
        self._connected  = False
        self._filter_pattern = None


        self._path_options = {
            "Subdomain Files": (self._subdomain_path, False),
            "Apache Sites Config": ("/etc/apache2/sites-available", True),
            "Apache Sites Enabled": ("/etc/apache2/sites-enabled", True),
            "Nginx Sites Available": ("/etc/nginx/sites-available", True),
            "Nginx Sites Enabled": ("/etc/nginx/sites-enabled", True),
            "Let's Encrypt Certs": ("/etc/letsencrypt/live", True),
            "Web Root": ("/var/www", True),
            "MySQL Databases": ("/var/lib/mysql", False),
        }


        self.win = tk.Toplevel(parent)
        self.win.title(f"\U0001f4c2  File Manager — {domain}")
        self.win.geometry("1100x680")
        self.win.minsize(800, 500)
        self.win.configure(bg=COLORS["bg_primary"])
        self.win.grab_set()


        self.win.update_idletasks()
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        self.win.geometry(f"1100x680+{(sw-1100)//2}+{(sh-680)//2}")

        self._build_ui()
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)


        threading.Thread(target=self._connect_and_load, daemon=True).start()


    def _build_ui(self):

        top_bar = tk.Frame(self.win, bg=COLORS["bg_secondary"], pady=8)
        top_bar.pack(fill="x")

        tk.Label(
            top_bar,
            text=f"\U0001f4c2  File Manager — {self.domain}",
            font=("Segoe UI", 13, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        ).pack(side="left", padx=16)


        self._status_lbl = tk.Label(
            top_bar, text="Connecting...",
            font=("Segoe UI", 9),
            bg=COLORS["warning"], fg="#000",
            padx=8, pady=2,
        )
        self._status_lbl.pack(side="left", padx=8)


        tk.Button(
            top_bar, text="\u26a1  Restart Apache",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg="#c0392b", fg="white",
            activebackground="#e74c3c", activeforeground="white",
            command=self._restart_apache,
        ).pack(side="right", padx=(0, 8), ipadx=8, ipady=3)


        tk.Button(
            top_bar, text="\u21bb  Refresh",
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            activebackground=COLORS["accent"],
            command=self._refresh_tree,
        ).pack(side="right", padx=(0, 6), ipadx=8, ipady=3)


        path_bar = tk.Frame(self.win, bg=COLORS["bg_primary"], pady=4)
        path_bar.pack(fill="x", padx=12)

        tk.Label(
            path_bar, text="Browse:",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(side="left")


        self._path_choice_var = tk.StringVar(value="Subdomain Files")
        path_dropdown = ttk.Combobox(
            path_bar,
            textvariable=self._path_choice_var,
            values=list(self._path_options.keys()),
            state="readonly",
            font=("Segoe UI", 9),
            width=22,
        )
        path_dropdown.pack(side="left", padx=(8, 12))
        path_dropdown.bind("<<ComboboxSelected>>", self._on_path_choice_changed)

        tk.Label(
            path_bar, text="\u2192",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(side="left")

        self._path_var = tk.StringVar(value=self.root_path)
        tk.Label(
            path_bar, textvariable=self._path_var,
            font=("Consolas", 9),
            bg=COLORS["bg_primary"], fg=COLORS["accent"],
            anchor="w",
        ).pack(side="left", padx=(6, 0))


        paned = tk.PanedWindow(
            self.win, orient="horizontal",
            bg=COLORS["bg_primary"], sashwidth=5,
            sashrelief="flat",
        )
        paned.pack(fill="both", expand=True, padx=12, pady=(0, 6))


        tree_frame = tk.Frame(paned, bg=COLORS["bg_secondary"])

        tree_hdr = tk.Frame(tree_frame, bg=COLORS["bg_secondary"])
        tree_hdr.pack(fill="x", padx=6, pady=(6, 2))
        tk.Label(
            tree_hdr, text="Files",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
        ).pack(side="left")

        tree_scroll = tk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll.pack(side="right", fill="y")

        self.tree = ttk.Treeview(
            tree_frame,
            yscrollcommand=tree_scroll.set,
            selectmode="browse",
            show="tree",
        )
        self.tree.pack(fill="both", expand=True, padx=(4, 0), pady=(0, 4))
        tree_scroll.config(command=self.tree.yview)


        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=COLORS["bg_secondary"],
            foreground=COLORS["text_primary"],
            fieldbackground=COLORS["bg_secondary"],
            rowheight=22,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["bg_accent"],
            foreground=COLORS["text_primary"],
        )
        style.map("Treeview", background=[("selected", COLORS["accent"])])

        self.tree.bind("<<TreeviewOpen>>",   self._on_expand)
        self.tree.bind("<Double-Button-1>",  self._on_double_click)
        self.tree.bind("<Button-3>",         self._on_right_click)

        paned.add(tree_frame, minsize=220, width=270)


        editor_panel = tk.Frame(paned, bg=COLORS["bg_primary"])


        editor_toolbar = tk.Frame(editor_panel, bg=COLORS["bg_secondary"], pady=5)
        editor_toolbar.pack(fill="x")

        self._editor_title = tk.Label(
            editor_toolbar, text="No file open",
            font=("Segoe UI", 10, "bold"),
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
        )
        self._editor_title.pack(side="left", padx=10)


        btn_cfg = dict(font=("Segoe UI", 9), relief="flat", cursor="hand2",
                       activebackground=COLORS["bg_accent"])

        self._save_btn = tk.Button(
            editor_toolbar, text="\U0001f4be  Save",
            bg=COLORS["success"], fg="white",
            activeforeground="white",
            state="disabled",
            command=self._save_file,
            **btn_cfg,
        )
        self._save_btn.pack(side="right", padx=(0, 10), ipadx=8, ipady=3)

        self._dl_btn = tk.Button(
            editor_toolbar, text="\u2b07  Download",
            bg=COLORS["accent"], fg="white",
            activeforeground="white",
            state="disabled",
            command=self._download_file,
            **btn_cfg,
        )
        self._dl_btn.pack(side="right", padx=(0, 6), ipadx=8, ipady=3)

        self._fmt_btn = tk.Button(
            editor_toolbar, text="\u2728  Format",
            bg="#6C3FC5", fg="white",
            activeforeground="white",
            state="disabled",
            command=self._format_file,
            **btn_cfg,
        )
        self._fmt_btn.pack(side="right", padx=(0, 6), ipadx=8, ipady=3)

        self._del_btn = tk.Button(
            editor_toolbar, text="\U0001f5d1  Delete",
            bg=COLORS["error"], fg="white",
            activeforeground="white",
            state="disabled",
            command=self._delete_selected,
            **btn_cfg,
        )
        self._del_btn.pack(side="right", padx=(0, 6), ipadx=8, ipady=3)


        editor_area = tk.Frame(editor_panel, bg=COLORS["bg_primary"])
        editor_area.pack(fill="both", expand=True, padx=8, pady=(4, 0))

        self._editor = scrolledtext.ScrolledText(
            editor_area,
            font=("Consolas", 10),
            bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#ffffff",
            relief="flat", wrap="none",
            undo=True, maxundo=200,
            state="disabled",
        )
        self._editor.pack(fill="both", expand=True)
        self._editor.bind("<<Modified>>", self._on_editor_modified)


        h_scroll = tk.Scrollbar(editor_area, orient="horizontal",
                                command=self._editor.xview)
        h_scroll.pack(fill="x")
        self._editor.configure(xscrollcommand=h_scroll.set)

        paned.add(editor_panel, minsize=400)


        self._status_bar = tk.Label(
            self.win, text="Ready",
            font=("Segoe UI", 8),
            bg=COLORS["bg_accent"], fg=COLORS["text_secondary"],
            anchor="w", padx=10, pady=3,
        )
        self._status_bar.pack(fill="x", side="bottom")


    def _on_close(self):
        from tkinter import messagebox
        if self._dirty and not messagebox.askyesno(
            "Unsaved Changes",
            "You have unsaved changes. Close anyway?",
            parent=self.win,
        ):
            return
        self._cleanup()
        self.win.destroy()

    def _cleanup(self):
        try:
            if self._sftp:
                self._sftp.close()
        except Exception:
            pass
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
