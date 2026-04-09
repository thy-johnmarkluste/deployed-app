"""Branch status page and file manager helpers."""

import csv
import time
from tkinter import filedialog, messagebox

from models.config import COLORS


class BranchStatusMixin:
    """Methods for loading branch status and opening the file manager."""


    def load_branch_status(self, *, force=False):
        """Fetch the live-deployed branch for every subdomain and populate
        the Branch Status page table."""
        if not force and self._branch_status_cache:
            age = time.time() - self._branch_status_cache_ts
            if age < self._branch_status_ttl:
                self.view.branch_status_page.populate(self._branch_status_cache)
                self.view.status_var.set("Branch status loaded from cache")
                self.view.update_status_chip(
                    "Ready",
                    bg_color=COLORS["bg_accent"],
                    fg_color=COLORS["text_primary"],
                )
                return

        subdomains = self.get_fast_table_subdomains()
        if not subdomains:
            self.view.branch_status_page.populate([])
            self.view.status_var.set("No subdomains to load")
            self.view.update_status_chip("Ready", bg_color=COLORS["bg_accent"], fg_color=COLORS["text_primary"])
            return

        page = self.view.branch_status_page
        page.set_loading(subdomains)
        self.view.status_var.set("Loading branch status...")
        self.view.update_status_chip("Working", bg_color=COLORS["warning"], fg_color="#000000")

        def _worker():
            results = []
            client = None
            try:
                client = self.ssh.connect()
                if not client:
                    for sd in subdomains:
                        results.append({
                            "subdomain": sd, "branch": "—",
                            "git_ok": False, "date": "—", "action": "—",
                            "status": "SSH Error",
                        })
                    self.root.after(0, lambda: page.populate(results))
                    return

                for sd in subdomains:
                    try:
                        git_ok = self.git_manager.is_git_repo(client, sd)
                        if not git_ok:
                            results.append({
                                "subdomain": sd, "branch": "—",
                                "git_ok": False, "date": "—", "action": "—",
                                "status": "No Git",
                            })
                            continue

                        branch = self.git_manager.get_current_branch(client, sd)
                        has_remote, _ = self.git_manager.get_remote_info(client, sd)


                        log_entries = self.git_manager.get_git_activity_log(client, sd, limit=1)
                        if log_entries:
                            last = log_entries[0]
                            date_val   = last.get("date", "—")
                            action_val = last.get("action", "commit")
                        else:
                            date_val   = "—"
                            action_val = "—"

                        results.append({
                            "subdomain": sd,
                            "branch":    branch or "—",
                            "git_ok":    True,
                            "date":      date_val,
                            "action":    action_val,
                            "status":    "Connected" if has_remote else "No Remote",
                        })
                    except Exception:
                        results.append({
                            "subdomain": sd, "branch": "—",
                            "git_ok": False, "date": "—", "action": "—",
                            "status": "Error",
                        })

            except Exception as exc:
                for sd in subdomains:
                    results.append({
                        "subdomain": sd, "branch": "—",
                        "git_ok": False, "date": "—", "action": "—",
                        "status": "Error",
                    })
            finally:
                if client:
                    try:
                        client.close()
                    except Exception:
                        pass

            def _apply_results():
                page.populate(results)
                self._branch_status_cache = results
                self._branch_status_cache_ts = time.time()
                self.view.status_var.set("Branch status updated")
                self.view.update_status_chip(
                    "Ready",
                    bg_color=COLORS["bg_accent"],
                    fg_color=COLORS["text_primary"],
                )
            self.root.after(0, _apply_results)

        self.submit_background_job(
            "Load Branch Status",
            _worker,
            dedupe_key="branch_status",
            source="git",
            silent=True,
        )

    def clear_branch_status_cache(self):
        self._branch_status_cache = None
        self._branch_status_cache_ts = 0.0
        self.view.status_var.set("Branch status cache cleared")
        self.view.update_status_chip(
            "Ready",
            bg_color=COLORS["bg_accent"],
            fg_color=COLORS["text_primary"],
        )

    def _export_branch_status_csv(self):
        rows = self._branch_status_cache or []
        if not rows:
            messagebox.showinfo("No Data", "No branch status to export. Please refresh first.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Branch Status",
            initialfile="branch_status.csv",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Subdomain",
                    "Branch",
                    "Last Commit",
                    "Action",
                    "Status",
                    "Git OK",
                ])
                for r in rows:
                    writer.writerow([
                        r.get("subdomain", ""),
                        r.get("branch", ""),
                        r.get("date", ""),
                        r.get("action", ""),
                        r.get("status", ""),
                        "Yes" if r.get("git_ok") else "No",
                    ])
            messagebox.showinfo("Success", f"Exported {len(rows)} rows to:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not export branch status:\n{exc}")


    def _open_file_manager(self):
        """Open the SFTP File Manager/Editor dialog for the selected subdomain."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return
        from views.file_manager import FileManagerDialog
        FileManagerDialog(self.root, subdomain, self.ssh, self.git_manager)

    def _open_file_manager_for(self, domain: str):
        """Open the SFTP File Manager/Editor dialog for a specific domain."""
        from views.file_manager import FileManagerDialog
        FileManagerDialog(self.root, domain, self.ssh, self.git_manager)
