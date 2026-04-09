"""Git validation helpers — subdomain selection and state guards."""
from tkinter import messagebox


class GitValidationMixin:
    """Validation helpers for Git operations."""

    _PREFLIGHT_MIN_FREE_KB = 512 * 1024
    _PREFLIGHT_SSL_WARN_DAYS = 14


    def _refresh_repo_subdomains(self):
        """Update the repo setup page subdomain dropdown."""
        subdomains = [e[0] for e in self.all_entries]
        self.view.repo_setup_page.set_subdomains(subdomains)

    def _on_repo_subdomain_selected(self, event=None):
        """Handle subdomain selection in repo setup page."""
        self.view.repo_setup_page.reset_status()
        selected = self.view.repo_setup_page.get_selected_subdomain()
        if selected:
            self.git_check_status()


    def _validate_subdomain_selected(self) -> str:
        """Validate a subdomain is selected, return subdomain or empty string."""
        subdomain = self.view.repo_setup_page.get_selected_subdomain()
        if not subdomain:
            messagebox.showwarning(
                "No Subdomain Selected",
                "Please select a subdomain first."
            )
            return ""
        return subdomain

    def _require_status_checked(self) -> bool:
        """Ensure the user ran Check Status at least once after selecting a subdomain."""
        if not self.view.repo_setup_page._status_checked:
            messagebox.showinfo(
                "Check Status First",
                "Please click  'Check Status'  first so the app can\n"
                "detect whether Git is initialized and a remote is connected.\n\n"
                "Steps:\n"
                "  1. Select a subdomain from the dropdown.\n"
                "  2. Click  'Check Status'  on the right panel.",
            )
            return False
        return True

    def _require_git_initialized(self) -> bool:
        """Check cached state — Git must be initialized before this action."""
        if not self._require_status_checked():
            return False
        if not self.view.repo_setup_page._git_initialized:
            messagebox.showwarning(
                "Git Not Initialized",
                "The Git repository has not been initialized yet.\n\n"
                "Please click  'Initialize Git Repo'  first, then try again.",
            )
            return False
        return True

    def _require_remote_connected(self) -> bool:
        """Check cached state — a remote must be connected before this action."""
        if not self._require_git_initialized():
            return False
        if not self.view.repo_setup_page._remote_connected:
            messagebox.showwarning(
                "Remote Not Connected",
                "No remote repository is connected yet.\n\n"
                "Please do the following first:\n"
                "  1. Enter a  Repository URL  (GitHub HTTPS URL).\n"
                "  2. Click  'Sync'.\n\n"
                "Then try this action again.",
            )
            return False
        return True


    def _run_preflight_checks(
        self,
        client,
        subdomain: str,
        *,
        operation: str,
        selected_branch: str = "",
    ):
        """Run remote preflight checks.

        Returns:
            tuple[bool, dict] => (is_allowed, {"blockers": [...], "warnings": [...], "info": [...]})
        """
        report = {"blockers": [], "warnings": [], "info": []}

        if not client:
            report["blockers"].append("SSH connection is not available.")
            return False, report


        try:
            _, stdout, _ = client.exec_command("echo PRECHECK_OK", timeout=8)
            probe = stdout.read().decode().strip()
            if "PRECHECK_OK" not in probe:
                report["blockers"].append("Server preflight probe failed.")
            else:
                report["info"].append("Connectivity check passed.")
        except Exception as exc:
            report["blockers"].append(f"Connectivity check failed: {exc}")

        path = self.git_manager.get_subdomain_path(subdomain)


        try:
            cmd = f"df -Pk '{path}' 2>/dev/null | tail -1 | awk '{{print $4}}'"
            _, stdout, _ = client.exec_command(cmd, timeout=8)
            free_kb_raw = stdout.read().decode().strip()
            free_kb = int(free_kb_raw) if free_kb_raw.isdigit() else 0
            free_mb = free_kb // 1024
            report["info"].append(f"Disk free: {free_mb} MB")
            if free_kb and free_kb < self._PREFLIGHT_MIN_FREE_KB:
                report["blockers"].append(
                    f"Low disk space on server path ({free_mb} MB free; minimum 512 MB required)."
                )
        except Exception as exc:
            report["warnings"].append(f"Could not verify disk space: {exc}")


        try:
            current_branch = self.git_manager.get_current_branch(client, subdomain)
            if selected_branch and current_branch and selected_branch != current_branch:
                report["warnings"].append(
                    f"Branch mismatch: server '{current_branch}' vs selected '{selected_branch}'."
                )
        except Exception as exc:
            report["warnings"].append(f"Could not verify branch alignment: {exc}")


        try:
            if self.git_manager.is_git_repo(client, subdomain):
                _ok, _msg, changes = self.git_manager.get_git_status(client, subdomain)
                change_count = len(changes or [])
                if change_count > 0:
                    if operation == "pull":
                        report["blockers"].append(
                            f"Pending local changes detected ({change_count} file(s)); pull is blocked to prevent overwrite."
                        )
                    else:
                        report["warnings"].append(
                            f"Pending local changes detected ({change_count} file(s))."
                        )
        except Exception as exc:
            report["warnings"].append(f"Could not verify local git changes: {exc}")


        try:
            certs = self.ssh.get_all_ssl_certs(client, [subdomain])
            if certs:
                cert = certs[0]
                status = cert.get("status", "Unknown")
                days = cert.get("days_remaining", "—")
                if status == "Expired":
                    report["warnings"].append("SSL certificate is expired for this domain.")
                elif status == "Expiring Soon":
                    report["warnings"].append(
                        f"SSL certificate expires soon ({days} days remaining)."
                    )
                elif isinstance(days, int) and days <= self._PREFLIGHT_SSL_WARN_DAYS:
                    report["warnings"].append(
                        f"SSL certificate is near expiry ({days} days remaining)."
                    )
        except Exception as exc:
            report["warnings"].append(f"Could not verify SSL status: {exc}")

        return len(report["blockers"]) == 0, report

    def _report_preflight(self, operation: str, report: dict, log_fn):
        """Write preflight report to operation log and show user message when needed."""
        if report["info"]:
            for line in report["info"]:
                log_fn(f"[Preflight] {line}")

        if report["warnings"]:
            for line in report["warnings"]:
                log_fn(f"[Preflight Warning] {line}")

        if report["blockers"]:
            for line in report["blockers"]:
                log_fn(f"[Preflight Blocked] {line}")
            details = "\n".join(f"- {line}" for line in report["blockers"])
            self.root.after(
                0,
                lambda: messagebox.showwarning(
                    "Preflight Checks Failed",
                    f"The {operation} operation was blocked by preflight checks:\n\n{details}",
                ),
            )

    def _capture_predeploy_snapshot(self, client, subdomain: str, operation: str, log_fn) -> bool:
        """Create a safety snapshot before risky Git operations.

        Returns True when snapshot capture succeeded; False blocks the operation.
        """
        success, msg, meta = self.git_manager.create_deployment_snapshot(
            client,
            subdomain,
            operation=operation,
            reason=f"Auto snapshot before {operation}",
            log_callback=log_fn,
        )
        log_fn(f"[Snapshot] {msg}")

        if success:
            snapshot_id = meta.get("snapshot_id", "")
            if snapshot_id:
                log_fn(f"[Snapshot] ID: {snapshot_id}")
            return True

        self.root.after(
            0,
            lambda: messagebox.showwarning(
                "Snapshot Failed",
                "A deployment safety snapshot could not be created.\n"
                "The operation was blocked to avoid irreversible changes.",
            ),
        )
        return False
