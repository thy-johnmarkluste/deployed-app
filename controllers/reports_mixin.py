"""
Reports Mixin — Reports page actions, PDF generation, and CSV export.
"""
import csv
import os
import tkinter as tk
from tkinter import messagebox, filedialog

from models.config import COLORS, HAS_FPDF
from models.paths import get_reports_dir, open_path_cross_platform
from models.metrics import collect_subdomain_metrics
from controllers.pdf_report import build_pdf_report


class ReportsMixin:
    """Methods for the Reports page, PDF report generation, and CSV export."""


    def _refresh_reports_list(self):
        v = self.view
        v.status_var.set("Refreshing reports...")
        v.update_status_chip("Working", bg_color=COLORS["warning"], fg_color="#000000")
        filt = v.reports_page.filter_var.get()
        v.reports_page.load_reports(filt)
        v.status_var.set("Reports refreshed")
        v.update_status_chip("Ready", bg_color=COLORS["bg_accent"], fg_color=COLORS["text_primary"])

    def _open_selected_report(self):
        path = self.view.reports_page.get_selected_report()
        if path and os.path.isfile(path):
            if not open_path_cross_platform(path):
                messagebox.showerror("Open Failed", "Could not open the selected report.")
        else:
            messagebox.showwarning("Not Found", "Report file was not found.")

    def _open_reports_folder(self):
        reports_dir = str(get_reports_dir())
        if os.path.isdir(reports_dir):
            if not open_path_cross_platform(reports_dir):
                messagebox.showerror("Open Failed", "Could not open the reports folder.")
        else:
            messagebox.showinfo("Info", "Reports folder does not exist yet.")

    def _delete_all_reports(self):
        reports_dir = str(get_reports_dir())
        if not os.path.isdir(reports_dir):
            return
        pdfs = [f for f in os.listdir(reports_dir) if f.lower().endswith(".pdf")]
        if not pdfs:
            messagebox.showinfo("Info", "No reports to delete.")
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete all {len(pdfs)} report(s)?\nThis cannot be undone."
        ):
            return
        for f in pdfs:
            try:
                os.remove(os.path.join(reports_dir, f))
            except OSError:
                pass
        self._refresh_reports_list()

    def _reports_context_menu(self, event):
        """Right-click menu on a report row."""
        row = self.view.reports_page.reports_tree.identify_row(event.y)
        if not row:
            return
        self.view.reports_page.reports_tree.selection_set(row)
        menu = tk.Menu(self.view.root, tearoff=0)
        menu.add_command(label="Open PDF", command=self._open_selected_report)
        menu.add_command(label="Delete", command=self._delete_selected_report)
        menu.post(event.x_root, event.y_root)

    def _delete_selected_report(self):
        path = self.view.reports_page.get_selected_report()
        if path and os.path.isfile(path):
            if messagebox.askyesno("Confirm", f"Delete {os.path.basename(path)}?"):
                os.remove(path)
                self._refresh_reports_list()
        else:
            messagebox.showwarning("Not Found", "Report file was not found.")


    def _export_dns_csv(self):
        """Export all DNS entries to a CSV file."""
        if not self.all_entries:
            messagebox.showinfo("No Data", "No DNS entries to export. Please refresh first.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export DNS Entries",
            initialfile="dns_entries.csv",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Domain", "IP Address", "Status", "Source"])
                for entry in self.all_entries:
                    domain = entry[0] if len(entry) > 0 else ""
                    ip = entry[1] if len(entry) > 1 else ""
                    status = entry[2] if len(entry) > 2 else ""
                    source = entry[3] if len(entry) > 3 else ""
                    writer.writerow([domain, ip, status, source])
            messagebox.showinfo("Success", f"Exported {len(self.all_entries)} DNS entries to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export DNS entries:\n{e}")

    def _export_activity_csv(self):
        """Export activity logs for all subdomains to a CSV file."""
        from models.activity_store import get_all_subdomains, load_entries as load_activity_entries

        all_subdomains = get_all_subdomains()
        if not all_subdomains:
            messagebox.showinfo("No Data", "No activity logs found.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Activity Logs",
            initialfile="activity_logs.csv",
        )
        if not filepath:
            return

        try:
            total_entries = 0
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Subdomain", "Date", "Action", "Details", "Status"])
                for subdomain in all_subdomains:
                    entries = load_activity_entries(subdomain)
                    for entry in entries:
                        writer.writerow([
                            entry.get("subdomain", subdomain),
                            entry.get("date", ""),
                            entry.get("action", ""),
                            entry.get("details", ""),
                            entry.get("status", ""),
                        ])
                        total_entries += 1
            messagebox.showinfo(
                "Success",
                f"Exported {total_entries} activity entries from {len(all_subdomains)} subdomain(s) to:\n{filepath}"
            )
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export activity logs:\n{e}")


    def _generate_report_for_row(self, domain, ip):
        if not HAS_FPDF:
            messagebox.showerror(
                "Missing Library",
                "fpdf2 is required for PDF reports.\n\nInstall it with: pip install fpdf2",
            )
            return
        v = self.view
        v.status_var.set(f"Generating report for {domain}...")
        v.update_status_chip("Working", bg_color=COLORS["warning"], fg_color="#000000")

        def _worker():

            if domain not in self.metrics_cache:
                metrics = collect_subdomain_metrics(domain, self.ssh)
                self.metrics_cache[domain] = metrics
            else:
                metrics = self.metrics_cache[domain]


            repo_info = {"has_git": False}
            activities = []
            try:
                client = self.ssh.connect()
                if client:

                    has_git = self.git_manager.is_git_repo(client, domain)
                    repo_info["has_git"] = has_git

                    if has_git:

                        has_remote, remote_url = self.git_manager.get_remote_info(client, domain)
                        repo_info["remote_url"] = remote_url if has_remote else "Not configured"


                        path = self.git_manager.get_subdomain_path(domain)
                        _, stdout, _ = client.exec_command(f"cd '{path}' && git branch --show-current 2>/dev/null")
                        branch = stdout.read().decode().strip()
                        repo_info["branch"] = branch or "main"


                        _, stdout, _ = client.exec_command(
                            f"cd '{path}' && git log -1 --format='%h - %s (%ar)' 2>/dev/null"
                        )
                        last_commit = stdout.read().decode().strip()
                        repo_info["last_commit"] = last_commit or "No commits"


                        activities = self.git_manager.get_git_activity_log(client, domain, limit=20)

                    client.close()
            except Exception:
                pass


            from models.activity_store import load_entries
            app_activities = load_entries(domain)

            all_activities = activities + app_activities

            all_activities.sort(key=lambda x: x.get("date", ""), reverse=True)

            self.root.after(0, lambda: self._finish_report(domain, ip, metrics, repo_info, all_activities))
        self.submit_background_job(
            "Generate PDF Report",
            _worker,
            dedupe_key=f"report:{domain}",
            source="reports",
        )

    def _finish_report(self, domain, ip, metrics, repo_info=None, activities=None):
        v = self.view
        build_pdf_report(domain, ip, metrics, log_callback=v.log,
                         repo_info=repo_info, activities=activities)
        v.status_var.set(f"Report saved for {domain}")
        v.update_status_chip("Ready", bg_color=COLORS["bg_accent"], fg_color=COLORS["text_primary"])
