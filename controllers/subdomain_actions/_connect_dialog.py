"""Connect to GitHub dialog — init .git and link a remote repository."""
import tkinter as tk
from tkinter import messagebox, scrolledtext

from models.config import COLORS, get_github_token as _get_saved_token


class ConnectDialogMixin:
    """Provides _open_connect_dialog and _do_connect_git."""


    def _open_connect_dialog(self, domain):
        """Modal dialog: initialize .git on the subdomain and connect a GitHub remote.

        The subdomain is auto-populated and read-only.  The user provides
        a GitHub repository URL and (optionally) a Personal Access Token.
        """
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Connect to GitHub \u2014 {domain}")
        dialog.geometry("560x520")
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.configure(bg=COLORS["bg_primary"])
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 560) // 2
        y = (dialog.winfo_screenheight() - 520) // 2
        dialog.geometry(f"560x520+{x}+{y}")


        tk.Label(
            dialog, text="\U0001f517  Connect to GitHub",
            font=("Segoe UI", 14, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(pady=(18, 2))
        tk.Label(
            dialog,
            text="Initialize Git and link a GitHub repository",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(pady=(0, 14))


        fields = tk.Frame(dialog, bg=COLORS["bg_primary"])
        fields.pack(fill="x", padx=24)


        tk.Label(
            fields, text="Subdomain", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        subdomain_var = tk.StringVar(value=domain)
        tk.Entry(
            fields, textvariable=subdomain_var, state="readonly",
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            readonlybackground=COLORS["bg_secondary"],
        ).pack(fill="x", ipady=6, pady=(0, 10))


        tk.Label(
            fields, text="GitHub Repository URL", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        url_var = tk.StringVar()
        url_entry = tk.Entry(
            fields, textvariable=url_var,
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        url_entry.pack(fill="x", ipady=6, pady=(0, 2))

        url_hint_row = tk.Frame(fields, bg=COLORS["bg_primary"])
        url_hint_row.pack(fill="x", pady=(0, 10))
        tk.Label(
            url_hint_row, text="e.g. https://github.com/user/repo.git", anchor="w",
            font=("Segoe UI", 8), bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(side="left")
        prefill_lbl = tk.Label(
            url_hint_row, text="",
            font=("Segoe UI", 8, "italic"),
            bg=COLORS["bg_primary"], fg=COLORS["success"],
            anchor="e",
        )
        prefill_lbl.pack(side="right")


        def _prefill_remote():
            try:
                client = self.ssh.connect()
                if not client:
                    return
                is_repo = self.git_manager.is_git_repo(client, domain)
                if is_repo:
                    has_remote, remote_url = self.git_manager.get_remote_info(client, domain)
                    if has_remote and remote_url:
                        clean = self.git_manager._clean_remote_url(remote_url)
                        def _apply(u=clean):
                            try:
                                url_var.set(u)
                                prefill_lbl.configure(text="\u2713 Pre-filled from existing remote")
                            except tk.TclError:
                                pass
                        dialog.after(0, _apply)
                client.close()
            except Exception:
                pass

        self.submit_background_job(
            "Prefill Remote URL",
            _prefill_remote,
            dedupe_key=f"connect_prefill:{domain}",
            source="git",
            silent=True,
        )


        tk.Label(
            fields, text="GitHub Access Token", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))
        token_frame = tk.Frame(fields, bg=COLORS["bg_primary"])
        token_frame.pack(fill="x", pady=(0, 2))
        token_var = tk.StringVar(value=_get_saved_token())
        token_entry = tk.Entry(
            token_frame, textvariable=token_var, show="\u2022",
            font=("Segoe UI", 10), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        token_entry.pack(side="left", fill="x", expand=True, ipady=6)

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
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            command=_toggle_token,
        )
        toggle_btn.pack(side="right", padx=(6, 0), ipady=4, ipadx=6)

        tk.Label(
            fields, text="Required for private repos (needs 'repo' scope)", anchor="w",
            font=("Segoe UI", 8), bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 6))


        log_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        log_frame.pack(fill="both", expand=True, padx=24, pady=(8, 0))

        log_box = scrolledtext.ScrolledText(
            log_frame, height=8, state="disabled",
            font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            relief="flat", wrap="word",
        )
        log_box.pack(fill="both", expand=True)

        def append_log(msg):
            log_box.configure(state="normal")
            log_box.insert("end", msg + "\n")
            log_box.see("end")
            log_box.configure(state="disabled")


        btn_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        btn_frame.pack(fill="x", padx=24, pady=14)

        connect_btn = tk.Button(
            btn_frame, text="\U0001f517  Connect",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["accent"], fg="white",
            activebackground=COLORS["accent"],
        )
        connect_btn.pack(side="left", ipadx=14, ipady=6)

        tk.Button(
            btn_frame, text="Close",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            command=dialog.destroy,
        ).pack(side="right", ipadx=14, ipady=6)

        def start_connect():
            repo_url = url_var.get().strip()
            github_token = token_var.get().strip()
            if not repo_url:
                messagebox.showwarning(
                    "Repository URL Required",
                    "Please enter the GitHub repository URL.",
                    parent=dialog,
                )
                return
            connect_btn.configure(state="disabled", text="Connecting\u2026")
            self.submit_background_job(
                "Connect GitHub Remote",
                self._do_connect_git,
                args=(
                    domain,
                    repo_url,
                    github_token,
                    append_log,
                    lambda: connect_btn.configure(state="normal", text="\U0001f517  Connect"),
                ),
                dedupe_key=f"connect_remote:{domain}",
                source="git",
            )

        connect_btn.configure(command=start_connect)

    def _do_connect_git(self, domain, repo_url, github_token, log_fn, done_fn):
        """Worker thread: initialize .git (if needed) and connect the GitHub remote."""
        client = None
        try:
            log_fn(f"Connecting to {self.hostname}\u2026")
            client = self.ssh.connect()
            if not client:
                log_fn("ERROR: SSH connection failed.")
                return


            log_fn(f"Ensuring /var/www/{domain} exists\u2026")
            success, msg = self.git_manager.create_subdomain_folder(client, domain, log_fn)
            if not success:
                log_fn(f"ERROR: {msg}")
                return


            is_repo = self.git_manager.is_git_repo(client, domain)
            if not is_repo:
                log_fn("Initializing Git repository\u2026")
                ok, msg = self.git_manager.init_git_repo(client, domain, log_fn)
                log_fn(msg)
                if not ok:
                    return

                ok, msg = self.git_manager.add_and_commit(
                    client, domain, "Initial commit", log_fn
                )
                log_fn(msg)
            else:
                log_fn("Git repository already initialized.")


            log_fn(f"Setting remote origin to {repo_url}\u2026")
            ok, msg = self.git_manager.add_remote(
                client, domain, repo_url, "origin", log_fn
            )
            log_fn(msg)
            if not ok:
                return


            log_fn("Pulling latest changes from remote\u2026")
            ok, msg = self.git_manager.pull_from_remote(
                client, domain, log_callback=log_fn,
                force_remote=False, github_token=github_token,
            )
            log_fn(msg)


            self._git_status_cache[domain] = {
                "git": "Initialized",
                "remote": "Connected",
            }
            self.root.after(0, self._update_tree_git_status)

            log_fn(f"\n\u2713 Done \u2014 {domain} is now connected to GitHub.")
            self._record_app_activity(
                domain, "connect",
                f"Connected {domain} to {repo_url}",
            )
        except Exception as exc:
            log_fn(f"\nERROR: {exc}")
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
            self.root.after(0, done_fn)
