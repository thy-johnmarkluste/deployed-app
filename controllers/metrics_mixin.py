"""
Metrics Mixin — Chart updates, metrics collection, and live server polling.
"""

import csv
import time
from tkinter import filedialog, messagebox

from models.config import COLORS
from models.metrics import collect_subdomain_metrics


class MetricsMixin:
    """Methods for chart rendering, metrics fetching, and live dashboard polling."""


    def update_chart(self):
        self._populate_dropdown()
        self._populate_ip_dropdown()

        sel = self.view.subdomain_var.get()
        if sel != "-- Overview --" and sel in self.metrics_cache:
            self.view.chart_manager.draw_subdomain_metrics(sel, self.metrics_cache[sel])
        else:

            empty_metrics = {
                "ssl_expiry_days": 0,
                "response_time_ms": 0,
                "uptime_pct": 0,
                "bandwidth_kbps": 0,
                "db_speed_ms": 0,
                "cpu_pct": 0,
                "memory_pct": 0,
                "ssl_status": "None",
            }
            self.view.chart_manager.draw_subdomain_metrics("", empty_metrics)


    def on_subdomain_selected(self, event=None):
        selected = self.view.subdomain_var.get()
        if selected == "-- Overview --":
            self.current_chart_mode = "overview"
            self.update_chart()
            self.view.clear_activity_log()
            return

        self.current_chart_mode = "subdomain"
        if selected in self.metrics_cache:
            self.view.chart_manager.draw_subdomain_metrics(selected, self.metrics_cache[selected])
        else:
            self.view.chart_manager.show_loading(selected)
            self.submit_background_job(
                "Fetch Subdomain Metrics",
                self._fetch_metrics_thread,
                args=(selected,),
                dedupe_key=f"metrics:{selected}",
                source="metrics",
                silent=True,
            )


        self._load_activity_for_subdomain(selected)

    def refresh_current_metrics(self):
        selected = self.view.subdomain_var.get()
        if selected == "-- Overview --":
            self.update_chart()
            return
        self.metrics_cache.pop(selected, None)
        self.view.chart_manager.show_loading(selected)
        self.submit_background_job(
            "Refresh Subdomain Metrics",
            self._fetch_metrics_thread,
            args=(selected,),
            dedupe_key=f"metrics:{selected}",
            source="metrics",
            silent=True,
        )

    def _fetch_metrics_thread(self, domain):
        self.root.after(0, lambda d=domain: self.view.log(f"Collecting metrics for {d}..."))
        try:
            metrics = collect_subdomain_metrics(domain, self.ssh)
            self.metrics_cache[domain] = metrics
            self.root.after(0, lambda: self._on_metrics_ready(domain, metrics))
        except Exception as exc:
            self.root.after(0, lambda d=domain, e=exc: self.view.log(f"Error collecting metrics for {d}: {e}"))

    def _on_metrics_ready(self, domain, metrics):
        self.view.log(
            f"Metrics for {domain}: SSL={metrics['ssl_status']}, "
            f"Resp={metrics['response_time_ms']}ms, "
            f"CPU={metrics['cpu_pct']}%, Mem={metrics['memory_pct']}%"
        )
        if self.view.subdomain_var.get() == domain:
            self.view.chart_manager.draw_subdomain_metrics(domain, metrics)
        self.view.status_var.set(f"Metrics loaded for {domain}")

    def load_subdomain_metrics_table(self, *, force=False):
        if not force and self._metrics_table_cache:
            age = time.time() - self._metrics_table_cache_ts
            if age < self._metrics_table_ttl:
                self.view.metrics_page.populate(self._metrics_table_cache)
                self.view.status_var.set("Subdomain metrics loaded from cache")
                self.view.update_status_chip(
                    "Ready",
                    bg_color=COLORS["bg_accent"],
                    fg_color=COLORS["text_primary"],
                )
                return

        subdomains = self.get_fast_table_subdomains()
        page = self.view.metrics_page
        if not subdomains:
            page.populate([])
            return

        page.set_loading(subdomains)
        self.view.status_var.set("Loading subdomain metrics...")
        self.view.update_status_chip("Working", bg_color=COLORS["warning"], fg_color="#000000")

        def _worker():
            rows = []
            for sd in subdomains:
                try:
                    m = collect_subdomain_metrics(sd, self.ssh)
                except Exception:
                    m = {}
                ssl_status = m.get("ssl_status", "Unknown")
                ssl_date = m.get("ssl_expiry_date", "")
                ssl_days = m.get("ssl_expiry_days", 0)
                if ssl_date:
                    ssl_text = f"{ssl_date} ({ssl_days}d)"
                elif ssl_status == "No SSL":
                    ssl_text = "No SSL"
                else:
                    ssl_text = f"{ssl_status} ({ssl_days}d)" if ssl_days else ssl_status

                uptime = "Up" if m.get("uptime_pct", 0) >= 100 else "Down"
                status = "ok" if uptime == "Up" and ssl_status == "Valid" else "warn"
                if uptime == "Down":
                    status = "bad"

                rows.append({
                    "domain": sd,
                    "ssl": ssl_text,
                    "response": m.get("response_time_ms", 0),
                    "uptime": uptime,
                    "bandwidth": m.get("bandwidth_kbps", 0),
                    "db_speed": m.get("db_speed_ms", 0),
                    "cpu": m.get("cpu_pct", 0),
                    "memory": m.get("memory_pct", 0),
                    "status": status,
                })

            def _apply():
                page.populate(rows)
                self._metrics_table_cache = rows
                self._metrics_table_cache_ts = time.time()
                self.view.status_var.set("Subdomain metrics updated")
                self.view.update_status_chip("Ready", bg_color=COLORS["bg_accent"], fg_color=COLORS["text_primary"])

            self.root.after(0, _apply)

        self.submit_background_job(
            "Load Subdomain Metrics",
            _worker,
            dedupe_key="metrics_table",
            source="metrics",
        )

    def clear_subdomain_metrics_cache(self):
        self._metrics_table_cache = None
        self._metrics_table_cache_ts = 0.0
        self.view.status_var.set("Subdomain metrics cache cleared")
        self.view.update_status_chip(
            "Ready",
            bg_color=COLORS["bg_accent"],
            fg_color=COLORS["text_primary"],
        )

    def _export_metrics_csv(self):
        rows = self._metrics_table_cache or []
        if not rows:
            messagebox.showinfo("No Data", "No metrics to export. Please refresh first.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Subdomain Metrics",
            initialfile="subdomain_metrics.csv",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "Subdomain",
                    "SSL Expiry",
                    "Response (ms)",
                    "Uptime",
                    "Bandwidth (kbps)",
                    "DB Speed (ms)",
                    "CPU %",
                    "Memory %",
                    "Status",
                ])
                for r in rows:
                    writer.writerow([
                        r.get("domain", ""),
                        r.get("ssl", ""),
                        r.get("response", ""),
                        r.get("uptime", ""),
                        r.get("bandwidth", ""),
                        r.get("db_speed", ""),
                        r.get("cpu", ""),
                        r.get("memory", ""),
                        r.get("status", ""),
                    ])
            messagebox.showinfo("Success", f"Exported {len(rows)} rows to:\n{filepath}")
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Could not export metrics:\n{exc}")


    def _poll_live_metrics(self):
        """Schedule a background fetch for server-wide live metrics."""
        if not self._live_polling:
            return
        self.submit_background_job(
            "Live Metrics Poll",
            self._fetch_live_metrics_thread,
            dedupe_key="live_metrics_poll",
            source="metrics",
            silent=True,
        )

        self.root.after(self._live_poll_interval, self._poll_live_metrics)

    def _fetch_live_metrics_thread(self):
        """Worker: SSH into server, grab CPU/Mem/Disk/Git-repo count + new metrics."""
        try:
            client = self.ssh.connect()
            cpu = self.ssh.get_server_cpu(client)
            mem = self.ssh.get_server_memory(client)
            disk = self.ssh.get_server_disk(client)
            git_count = self.ssh.count_git_repos(client)


            load_1, _load_5, _load_15 = self.ssh.get_server_load_avg(client)
            connections = self.ssh.get_active_connections(client)
            processes = self.ssh.get_process_count(client)
            ssl_expiring = self.ssh.get_ssl_expiring_count(client)
            down_count = self.ssh.get_subdomains_down_count(client)

            client.close()


            total = len(self.all_entries)
            registered = len(self.registered_entries)
            unregistered = len(self.unregistered_entries)
            vultr = len(self.vultr_entries)

            self.root.after(0, lambda: self._apply_live_metrics(
                total, git_count, registered, unregistered, vultr,
                cpu, mem, disk,
                load_avg=load_1, connections=connections,
                processes=processes, ssl_expiring=ssl_expiring,
                down_count=down_count,
            ))
        except Exception:
            pass

    def _apply_live_metrics(self, total, git_count, registered, unregistered,
                            vultr, cpu, mem, disk, *,
                            load_avg=0.0, connections=0,
                            processes=0, ssl_expiring=0, down_count=0):
        """Push new numbers into the dashboard widgets (main thread)."""
        v = self.view
        v.metric_subdomains.update_value(total)
        v.metric_repos.update_value(git_count)
        v.metric_registered.update_value(registered)
        v.metric_unregistered.update_value(unregistered)
        v.metric_vultr.update_value(vultr)


        mp = v.manage_subdomain_page
        mp.metric_ssl_expiring.update_value(ssl_expiring)
        mp.metric_down.update_value(down_count)
        mp.metric_connections.update_value(connections)
        mp.metric_load_avg.update_value(load_avg)
        mp.metric_processes.update_value(processes)

        v.cpu_bar.update_value(cpu)
        v.mem_bar.update_value(mem)
        v.disk_bar.update_value(disk)
