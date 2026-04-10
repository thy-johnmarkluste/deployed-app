"""
Main Controller — wires the View to the Models and handles all events.

The controller logic is split into focused mixins for readability:
  - DNSMixin             → DNS entry add/load, filtering, dropdowns
  - GitMixin             → Git init, sync, commit, push, pull, upload & push
  - MetricsMixin         → Charts, metrics collection, live server polling
  - ReportsMixin         → Reports page, PDF generation, CSV export
  - HelpMixin            → Help dialog windows
  - ActivityMixin        → Activity log loading, recording, display
  - SubdomainActionsMixin → Delete subdomain, action menus, upload dialog
"""
import socket
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from models.config import (
    COLORS,
    HAS_MATPLOTLIB,
    load_runtime_credentials,
    clear_credentials_file,
)
from models.ssh_client import SSHClientManager
from models.git_manager import GitManager
from models.job_queue import AsyncJobQueue
from models.logger import module_logger
from views.main_view import MainView


logger = module_logger(__name__)


from controllers.dns_mixin import DNSMixin
from controllers.git_mixin import GitMixin
from controllers.metrics_mixin import MetricsMixin
from controllers.reports_mixin import ReportsMixin
from controllers.help_mixin import HelpMixin
from controllers.activity_mixin import ActivityMixin
from controllers.subdomain_actions_mixin import SubdomainActionsMixin


class MainController(
    DNSMixin,
    GitMixin,
    MetricsMixin,
    ReportsMixin,
    HelpMixin,
    ActivityMixin,
    SubdomainActionsMixin,
):
    """Orchestrate models ↔ view interaction.

    All domain-specific methods live in the mixin classes listed above.
    This file contains only initialization, event binding, navigation,
    and a few simple actions (test connection, exit, close).
    """

    def __init__(self, root):
        self.root = root


        creds = load_runtime_credentials()
        self.hostname = creds.get("TARGET_HOSTNAME", "")
        self.username = creds.get("TARGET_USERNAME", "")
        self.password = creds.get("TARGET_PASSWORD", "")

        if not self.hostname or not self.username:
            # Launch setup silently first, then exit
            launched = self._launch_setup_application()
            if launched:
                self.root.after(100, self.root.destroy)
                return
            raise RuntimeError("Missing credentials and failed to launch setup application.")


        self.ssh = SSHClientManager(self.hostname, self.username, self.password)
        self.git_manager = GitManager(self.ssh)


        self.all_entries = []
        self.registered_entries = []
        self.unregistered_entries = []
        self.vultr_entries = []
        self.metrics_cache = {}
        self._metrics_table_cache = None
        self._metrics_table_cache_ts = 0.0
        self._metrics_table_ttl = 300.0
        self._branch_status_cache = None
        self._branch_status_cache_ts = 0.0
        self._branch_status_ttl = 300.0
        self.current_chart_mode = "overview"
        self._git_status_cache = {}
        self._manage_sort_column = "Domain"
        self._manage_sort_desc = False


        self.ssh_key_path = Path.home() / ".ssh" / "dns_manager_key"
        self.use_ssh_key = False


        self._live_polling = True
        self._live_poll_interval = 30_000


        self.job_queue = AsyncJobQueue(max_workers=4, on_event=self._on_job_event)
        self.job_timeline = []
        self._job_timeline_limit = 300


        self.view = MainView(root, self.hostname, self.username)


        self._bind_events()


        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.submit_background_job(
            "Initial DNS Load",
            self.load_dns_entries,
            dedupe_key="dns_load",
            source="dns",
        )


        self.root.after(2000, self._poll_live_metrics)


    def _bind_events(self):
        v = self.view

        v.test_btn.command = self.test_connection
        v.help_btn.command = self.show_help
        v.exit_btn.command = self.exit_to_setup
        v.refresh_metrics_btn.command = self.refresh_current_metrics
        v.refresh_activity_btn.command = self.refresh_activity_log


        for w in (v._nav_items["dashboard"], v._nav_items["dashboard"]._label, v._nav_items["dashboard"]._icon):
            w.bind("<Button-1>", lambda e: self._go_to_dashboard())
        # Subdomains nav is now a dropdown menu on the sidebar.
        for w in (v._nav_items["repo_setup"], v._nav_items["repo_setup"]._label, v._nav_items["repo_setup"]._icon):
            w.bind("<Button-1>", lambda e: self._go_to_repo_setup_page())
        for w in (v._nav_items["metrics"], v._nav_items["metrics"]._label, v._nav_items["metrics"]._icon):
            w.bind("<Button-1>", lambda e: self._go_to_metrics_page())
        for w in (v._nav_items["branch_status"], v._nav_items["branch_status"]._label, v._nav_items["branch_status"]._icon):
            w.bind("<Button-1>", lambda e: self._go_to_branch_status_page())


        v.branch_status_page.refresh_btn.command = lambda: self.load_branch_status(force=True)
        v.branch_status_page.clear_cache_btn.command = self.clear_branch_status_cache
        v.branch_status_page.export_btn.command = self._export_branch_status_csv


        v.reports_page.refresh_btn.command = self._refresh_reports_list
        v.reports_page.export_dns_btn.command = self._export_dns_csv
        v.reports_page.export_activity_btn.command = self._export_activity_csv
        v.reports_page.filter_var.trace_add("write", lambda *_: self._refresh_reports_list())
        v.reports_page.reports_tree.bind("<Double-1>", lambda e: self._open_selected_report())
        v.reports_page.reports_tree.bind("<Button-3>", self._reports_context_menu)


        v.add_btn.command = self.add_dns_entry
        v.refresh_btn.command = lambda: self.submit_background_job(
            "Load DNS Entries", self.load_dns_entries,
            dedupe_key="dns_load", source="dns"
        )
        v.clear_btn.command = v.clear_log
        v.subdomain_page.git_setup_btn.command = self._go_to_repo_setup_page


        v.manage_subdomain_page.refresh_btn.command = lambda: self.submit_background_job(
            "Load DNS Entries", self.load_dns_entries,
            dedupe_key="dns_load", source="dns"
        )


        v.repo_setup_page.sync_action_btn.command = self.git_sync
        v.repo_setup_page.commit_push_btn.command = self.git_commit_push
        v.repo_setup_page.editor_btn.configure(command=self._open_file_manager)
        v.repo_setup_page.check_status_btn.command = self.git_check_status
        v.repo_setup_page.clear_log_btn.command = v.repo_setup_page.clear_log
        v.repo_setup_page.refresh_branches_btn.configure(command=self.git_refresh_branches)
        v.repo_setup_page.subdomain_dropdown.bind("<<ComboboxSelected>>", self._on_repo_subdomain_selected)

        v.metrics_page.refresh_btn.command = lambda: self.load_subdomain_metrics_table(force=True)
        v.metrics_page.clear_cache_btn.command = self.clear_subdomain_metrics_cache
        v.metrics_page.export_btn.command = self._export_metrics_csv


        v.repo_setup_page.set_wp_button_commands({
            "wp_config_btn":   self.wp_generate_config,
            "wp_db_btn":       self.wp_check_database,
            "wp_sql_btn":      self.wp_upload_sql,
            "wp_perms_btn":    self.wp_fix_permissions,
            "wp_vhost_btn":    self.wp_fix_vhost,
        })


        v.repo_setup_page.set_vite_db_button_commands({
            "vite_db_create_btn": self.vite_create_db,
            "vite_db_import_btn": self.vite_upload_sql,
            "vite_db_env_btn": self.vite_generate_env,
        })

        v.subdomain_dropdown.bind("<<ComboboxSelected>>", self.on_subdomain_selected)


        v.manage_filter_var.trace_add("write", lambda *_: self.apply_manage_filter())
        v.manage_ip_filter_dropdown.bind("<<ComboboxSelected>>", lambda *_: self.apply_manage_filter())
        v.manage_dns_tree.bind("<ButtonRelease-1>", self.handle_manage_click)
        for col in ("Domain", "IP", "Type", "Git", "Remote"):
            v.manage_dns_tree.heading(
                col,
                command=lambda c=col: self.sort_manage_table(c),
            )

        if not HAS_MATPLOTLIB:
            v.chart_manager.chart_canvas.bind(
                "<Configure>", lambda e: self.update_chart()
            )


    def submit_background_job(
        self,
        name,
        target,
        args=(),
        kwargs=None,
        *,
        dedupe_key=None,
        source="system",
        silent=False,
    ):
        """Submit work to the centralized async queue."""
        job_id = self.job_queue.submit(
            name=name,
            func=target,
            args=args,
            kwargs=kwargs or {},
            dedupe_key=dedupe_key,
            source=source,
            silent=silent,
        )
        if job_id is None and not silent:
            self.view.log(f"[Job] Skipped duplicate: {name}")
        return job_id

    def _on_job_event(self, event, job, error=None):
        """Queue worker callback; marshals events onto Tk's main thread."""
        try:
            self.root.after(0, lambda: self._apply_job_event(event, job, error))
        except Exception:

            pass

    def _apply_job_event(self, event, job, error=None):
        """Update timeline and surface status changes for non-silent jobs."""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.job_timeline.append({
            "time": stamp,
            "event": event,
            "job_id": job.id,
            "name": job.name,
            "source": job.source,
            "status": job.status,
            "error": str(error) if error else job.error,
        })
        if len(self.job_timeline) > self._job_timeline_limit:
            self.job_timeline = self.job_timeline[-self._job_timeline_limit:]

        if job.silent:
            return

        if event == "queued":
            self.view.status_var.set(f"Queued: {job.name}")
            self.view.log(f"[Job queued] {job.name}")
            return

        if event == "running":
            self.view.status_var.set(f"Running: {job.name}")
            return

        if event == "succeeded":
            self.view.status_var.set(f"Completed: {job.name}")
            self.view.log(f"[Job done] {job.name}")
            return

        if event == "failed":
            err = str(error) if error else (job.error or "unknown error")
            self.view.status_var.set(f"Failed: {job.name}")
            self.view.log(f"[Job failed] {job.name}: {err}", "error")

    def get_recent_job_timeline(self, limit=50):
        """Return the most recent job events (newest last)."""
        limit = max(1, int(limit))
        return list(self.job_timeline[-limit:])


    def _go_to_subdomain_page(self):
        self.view.show_subdomain_page()

    def _go_to_manage_subdomain_page(self):
        self.view.show_manage_subdomain_page()

    def _go_to_dashboard(self):
        self.view.show_dashboard()

    def _go_to_repo_setup_page(self):
        self._refresh_repo_subdomains()
        self.view.show_repo_setup_page()

    def _go_to_reports_page(self):
        self.view.show_reports_page()

    def _go_to_branch_status_page(self):
        self.view.show_branch_status_page()
        self.load_branch_status(force=False)

    def _go_to_metrics_page(self):
        self.view.show_metrics_page()
        self.load_subdomain_metrics_table(force=False)


    def test_connection(self):
        v = self.view
        v.status_var.set("Testing connection...")
        v.update_status_chip("Testing", bg_color=COLORS["warning"], fg_color="#000000")
        try:
            s = socket.create_connection((self.hostname, 22), timeout=5)
            s.close()
            messagebox.showinfo(
                "Connection Test",
                f"Successfully connected to {self.hostname} on port 22.",
            )
            v.status_var.set("Connection successful!")
            v.update_status_chip("Online", bg_color=COLORS["success"], fg_color="#0b1d13")
        except Exception as e:
            messagebox.showerror("Connection Test", f"Failed to connect: {e}")
            v.status_var.set(f"Connection failed: {e}")
            v.update_status_chip("Error", bg_color=COLORS["error"])

    def exit_to_setup(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            clear_credentials_file()
            self.root.destroy()
            self._launch_setup_application()

    def on_close(self):
        self._live_polling = False
        self.job_queue.stop(timeout=0.5)
        self.root.destroy()

    def _launch_setup_application(self):
        """Launch setup flow in both source and packaged runs."""
        try:
            if getattr(sys, "frozen", False):
                main_exe = Path(sys.executable).resolve()
                if sys.platform == "darwin":
                    # Expected inside app bundle:
                    # ThyWeb.app/Contents/MacOS/ThyWeb
                    app_bundle = None
                    for parent in main_exe.parents:
                        if parent.suffix == ".app":
                            app_bundle = parent
                            break

                    if app_bundle is None:
                        raise FileNotFoundError("Could not resolve current .app bundle location.")

                    candidates = [
                        app_bundle.with_name("ThyWebSetup.app"),
                        app_bundle.with_name("ServerAppConfig.app"),
                    ]
                    setup_app = next((p for p in candidates if p.exists()), None)
                    if not setup_app:
                        raise FileNotFoundError("Could not find ThyWebSetup.app near installed app.")
                    subprocess.Popen(["open", str(setup_app)])
                else:
                    candidates = [
                        main_exe.with_name("ThyWebSetup.exe"),
                        main_exe.parent.parent / "ThyWebSetup" / "ThyWebSetup.exe",
                        main_exe.parent / "ThyWebSetup.exe",
                    ]
                    setup_exe = next((p for p in candidates if p.exists()), None)
                    if not setup_exe:
                        raise FileNotFoundError("Could not find ThyWebSetup.exe near installed app.")
                    subprocess.Popen([str(setup_exe)])
            else:
                subprocess.Popen([sys.executable, "setup_credentials.py"])
            return True
        except Exception as exc:
            messagebox.showerror(
                "Launch Failed",
                f"Could not open setup credentials window:\n{exc}",
            )
            return False
