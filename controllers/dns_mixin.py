"""
DNS Mixin — DNS entry management, filtering, dropdowns, and batch git status checks.
"""
import re
import threading

from models.config import (
    COLORS,
    FAST_TABLE_TARGET_IP,
    VULTR_TARGET_DOMAIN,
    VULTR_API_KEY,
)
from models.security import validate_domain_name, validate_ip_address, sanitize_log_output
from models.vultr_api import fetch_vultr_subdomains, register_vultr_subdomain
from models.logger import module_logger


logger = module_logger(__name__)


class DNSMixin:
    """Methods for adding/loading DNS entries, filtering the tree, and
    populating dropdowns."""


    def add_dns_entry(self):
        from tkinter import messagebox


        domain = self.view.subdomain_page.get_full_domain()
        ip = self.view.ip_entry.get().strip()


        is_valid, error = validate_domain_name(domain)
        if not is_valid:
            messagebox.showwarning("Validation Error", f"Invalid domain: {error}")
            return

        is_valid, error = validate_ip_address(ip)
        if not is_valid:
            messagebox.showwarning("Validation Error", f"Invalid IP: {error}")
            return

        if not domain or not ip:
            messagebox.showwarning("Missing Data", "Please enter both subdomain name and IP address")
            return
        self.submit_background_job(
            "Add DNS Entry",
            self._add_dns_entry,
            args=(domain, ip),
            dedupe_key=f"dns_add:{domain}",
            source="dns",
        )

    def _add_dns_entry(self, domain, ip):
        from tkinter import messagebox

        v = self.view
        client = None

        def _ui_log(msg, tag="info"):
            self.root.after(0, lambda m=msg, t=tag: v.log(m, t))

        def _ui_status(text, *, chip_text=None, chip_bg=None, chip_fg=None):
            def _apply():
                v.status_var.set(text)
                if chip_text:
                    v.update_status_chip(chip_text, bg_color=chip_bg, fg_color=chip_fg)
            self.root.after(0, _apply)

        try:
            _ui_status(
                "Adding DNS entry...",
                chip_text="Working",
                chip_bg=COLORS["warning"],
                chip_fg="#000000",
            )
            _ui_log(f"\n{'=' * 60}")
            _ui_log(f"Adding DNS entry: {domain} -> {ip}")

            vultr_result = {"success": False, "message": ""}
            server_error = {"error": None}

            def _vultr_register():
                _ui_log(f"Registering {domain} on Vultr DNS...")
                ok, msg = register_vultr_subdomain(domain, ip)
                vultr_result["success"] = ok
                vultr_result["message"] = msg

            def _server_setup():
                nonlocal client
                try:
                    client = self.ssh.connect()
                    self.ssh.add_dns_entry(client, domain, ip)
                    _ui_log("DNS entry added to custom_dns.txt")
                    exit_status = self.ssh.execute_server_sh(client, domain, log_callback=_ui_log)
                    if exit_status == 0:
                        _ui_log(f"\nSuccessfully configured {domain}!")
                except Exception as e:
                    server_error["error"] = str(e)

            t_vultr = threading.Thread(target=_vultr_register)
            t_server = threading.Thread(target=_server_setup)
            t_vultr.daemon = True
            t_server.daemon = True
            t_vultr.start()
            t_server.start()
            t_vultr.join()
            t_server.join()

            if vultr_result["success"]:
                _ui_log(f"[Vultr] {vultr_result['message']}")
            else:
                _ui_log(f"[Vultr] ERROR: {vultr_result['message']}", "error")

            if server_error["error"]:
                _ui_log(f"[Server] ERROR: {server_error['error']}", "error")

            if vultr_result["success"] and not server_error["error"]:
                _ui_status(
                    "DNS entry added & registered on Vultr",
                    chip_text="Updated",
                    chip_bg=COLORS["success"],
                    chip_fg="#0b1d13",
                )
                _ui_log("Successfully registered subdomain on Vultr and configured server.")
            elif vultr_result["success"]:
                _ui_status(
                    "Vultr OK, server setup had errors",
                    chip_text="Partial",
                    chip_bg=COLORS["warning"],
                    chip_fg="#000000",
                )
            elif not server_error["error"]:
                _ui_status(
                    "Server OK, Vultr registration failed",
                    chip_text="Partial",
                    chip_bg=COLORS["warning"],
                    chip_fg="#000000",
                )
            else:
                _ui_status(
                    "Both Vultr and server setup failed",
                    chip_text="Error",
                    chip_bg=COLORS["error"],
                )

            def _after_success():
                v.domain_entry.delete(0, "end")
                v.ip_entry.delete(0, "end")
                self.submit_background_job(
                    "Load DNS Entries",
                    self.load_dns_entries,
                    dedupe_key="dns_load",
                    source="dns",
                )

            self.root.after(0, _after_success)

        except Exception as e:
            _ui_log(f"\nERROR: {str(e)}", "error")
            _ui_status(
                f"Error: {str(e)}",
                chip_text="Error",
                chip_bg=COLORS["error"],
            )
        finally:
            if client:
                client.close()


    def load_dns_entries(self):
        v = self.view
        client = None
        try:
            v.status_var.set("Loading DNS entries...")
            v.update_status_chip("Syncing", bg_color=COLORS["warning"], fg_color="#000000")
            client = self.ssh.connect()

            registered_domains = self.ssh.load_registered_entries(client)
            self.registered_entries = [(d, self.hostname, "registered") for d in registered_domains]

            unregistered_domains = self.ssh.load_unregistered_entries(client)
            registered_set = {e[0] for e in self.registered_entries}
            self.unregistered_entries = [
                (d, self.hostname, "unregistered")
                for d in unregistered_domains
                if d not in registered_set
            ]


            # Check if Vultr API is configured before trying to fetch
            if not VULTR_API_KEY or VULTR_API_KEY == "your_vultr_api_key_here":
                v.log("Warning: VULTR_API_KEY not configured - skipping Vultr DNS fetch", "warning")
            else:
                v.log(f"Fetching subdomains from Vultr DNS for domain: {VULTR_TARGET_DOMAIN}...")
            vultr_subdomains = fetch_vultr_subdomains(VULTR_TARGET_DOMAIN)
            self._vultr_dns_subdomains_cache = vultr_subdomains
            existing = {e[0] for e in self.registered_entries + self.unregistered_entries}
            self.vultr_entries = [
                (sub["subdomain"], sub["data"], f"vultr-{sub['type']}")
                for sub in vultr_subdomains
                if sub["subdomain"] not in existing
            ]
            v.log(f"Fetched {len(self.vultr_entries)} unique subdomains from Vultr DNS")

            self.all_entries = self.registered_entries + self.unregistered_entries + self.vultr_entries
            self.view.subdomain_page.set_known_domains([e[0] for e in self.all_entries])
            self.apply_manage_filter()
            self.update_chart()

            v.log(
                f"Loaded {len(self.registered_entries)} registered, "
                f"{len(self.unregistered_entries)} unregistered, "
                f"{len(self.vultr_entries)} Vultr subdomains"
            )
            v.status_var.set("DNS entries loaded")
            v.update_status_chip("Ready", bg_color=COLORS["bg_accent"], fg_color=COLORS["text_primary"])
            v.update_stats(
                len(self.registered_entries),
                len(self.unregistered_entries),
                len(self.vultr_entries),
            )

            v.metric_subdomains.update_value(len(self.all_entries), animate=True)
            v.metric_registered.update_value(len(self.registered_entries), animate=True)
            v.metric_unregistered.update_value(len(self.unregistered_entries), animate=True)
            v.metric_vultr.update_value(len(self.vultr_entries), animate=True)


            self.submit_background_job(
                "Batch Git Status Check",
                self._batch_check_git_status,
                dedupe_key="batch_git_status",
                source="git",
                silent=True,
            )

        except Exception as e:
            v.log(f"ERROR loading DNS entries: {str(e)}", "error")
            v.status_var.set(f"Error: {str(e)}")
            v.update_status_chip("Error", bg_color=COLORS["error"])
        finally:
            if client:
                client.close()

    def get_fast_table_subdomains(self):
        """Return only domains targeted by the heavy tables.

        Criteria:
        - FQDN under configured Vultr domain (e.g. *.veryapp.info)
        - A record points to FAST_TABLE_TARGET_IP
        """
        target_domain = (VULTR_TARGET_DOMAIN or "veryapp.info").strip().lower()
        target_suffix = f".{target_domain}"

        records = getattr(self, "_vultr_dns_subdomains_cache", None)
        if not records:
            records = fetch_vultr_subdomains(VULTR_TARGET_DOMAIN)
            self._vultr_dns_subdomains_cache = records

        filtered = sorted({
            str(r.get("subdomain", "")).strip()
            for r in (records or [])
            if str(r.get("type", "")).upper() == "A"
            and str(r.get("data", "")).strip() == FAST_TABLE_TARGET_IP
            and str(r.get("subdomain", "")).strip().lower().endswith(target_suffix)
        })
        if filtered:
            return filtered

        # Fallback: if Vultr DNS data is unavailable, use loaded entries with the
        # same strict suffix + IP filter.
        fallback = sorted({
            str(domain).strip()
            for domain, ip, _stype in self.all_entries
            if str(domain).strip().lower().endswith(target_suffix)
            and str(ip).strip() == FAST_TABLE_TARGET_IP
        })
        return fallback


    def apply_filter(self):
        """Delegate to apply_manage_filter (same tree) and refresh chart."""
        self.apply_manage_filter()
        self.update_chart()

    def _is_manage_table_target_entry(self, domain: str, ip: str) -> bool:
        """True only for entries that belong in Manage Subdomains table scope."""
        target_domain = (VULTR_TARGET_DOMAIN or "veryapp.info").strip().lower()
        suffix = f".{target_domain}"
        return str(domain).strip().lower().endswith(suffix) and str(ip).strip() == FAST_TABLE_TARGET_IP

    def apply_manage_filter(self):
        v = self.view
        term = v.manage_filter_var.get().strip().lower() if hasattr(v, "manage_filter_var") else ""
        ip_filter = v.manage_ip_filter_var.get() if hasattr(v, "manage_ip_filter_var") else "All IPs"

        filtered = []
        for domain, ip, stype in self.all_entries:
            if not self._is_manage_table_target_entry(domain, ip):
                continue

            safe_domain = sanitize_log_output(domain, max_length=100)
            safe_ip = sanitize_log_output(ip, max_length=50)

            if term and term not in safe_domain.lower() and term not in safe_ip.lower():
                continue
            if ip_filter != "All IPs" and ip != ip_filter:
                continue
            filtered.append((domain, ip, stype))

        sort_col = getattr(self, "_manage_sort_column", "Domain")
        sort_desc = getattr(self, "_manage_sort_desc", False)

        def _sort_key(item):
            domain, ip, stype = item
            git_status = self._git_status_cache.get(domain, {})
            if sort_col == "Domain":
                return domain.lower()
            if sort_col == "IP":
                return ip.lower()
            if sort_col == "Type":
                return stype.lower()
            if sort_col == "Git":
                return git_status.get("git", "...").lower()
            if sort_col == "Remote":
                return git_status.get("remote", "...").lower()
            return domain.lower()

        filtered.sort(key=_sort_key, reverse=sort_desc)

        reg_count = sum(1 for _, _, st in filtered if st == "registered")
        unreg_count = sum(1 for _, _, st in filtered if st == "unregistered")
        vultr_count = sum(1 for _, _, st in filtered if st.startswith("vultr"))
        self.view.manage_subdomain_page.update_filter_summary(
            len(filtered), reg_count, unreg_count, vultr_count,
        )

        for item in v.manage_dns_tree.get_children():
            v.manage_dns_tree.delete(item)

        if not filtered:
            v.manage_dns_tree.insert(
                "", "end",
                values=("No results for current filters", "-", "-", "-", "-", "-", "-"),
                tags=("row_even",),
            )
            return

        for idx, (domain, ip, stype) in enumerate(filtered):
            if stype == "registered":
                type_text = "Registered"
            elif stype == "unregistered":
                type_text = "Unregistered"
            elif stype.startswith("vultr"):
                type_text = "Vultr"
            else:
                type_text = "Unknown"


            git_status = self._git_status_cache.get(domain, {})
            git_text = git_status.get("git", "...")
            remote_text = git_status.get("remote", "...")

            row_tag = "row_even" if idx % 2 == 0 else "row_odd"

            v.manage_dns_tree.insert(
                "", "end",
                values=(domain, ip, type_text, git_text, remote_text, "PDF", "⋯ Actions"),
                tags=(row_tag, "buttons"),
            )

    def sort_manage_table(self, column_name: str):
        """Sort manage table by selected column; toggle desc when clicking same column."""
        current = getattr(self, "_manage_sort_column", "Domain")
        if current == column_name:
            self._manage_sort_desc = not getattr(self, "_manage_sort_desc", False)
        else:
            self._manage_sort_column = column_name
            self._manage_sort_desc = False
        self.apply_manage_filter()


    def _batch_check_git_status(self):
        """Check git init + remote status for every subdomain in background.
        Updates _git_status_cache and refreshes the tree row-by-row."""
        client = None
        try:
            client = self.ssh.connect()
            if not client:
                return

            target = VULTR_TARGET_DOMAIN.lower()
            domains = [d for d, _, _ in self.all_entries if d.lower().endswith(target)]

            for domain in domains:
                try:
                    is_repo = self.git_manager.is_git_repo(client, domain)
                    has_remote = False
                    if is_repo:
                        has_remote, _ = self.git_manager.get_remote_info(client, domain)

                    self._git_status_cache[domain] = {
                        "git": "Initialized" if is_repo else "Not Init",
                        "remote": "Connected" if has_remote else "Not Connected",
                    }
                except Exception:
                    self._git_status_cache[domain] = {
                        "git": "Error",
                        "remote": "Error",
                    }


            self.root.after(0, self._update_tree_git_status)

        except Exception:
            pass
        finally:
            if client:
                client.close()

    def _update_tree_git_status(self):
        """Update the Git and Remote columns in the tree with cached status + colors."""
        tree = self.view.manage_dns_tree
        for idx, item in enumerate(tree.get_children()):
            values = list(tree.item(item, "values"))
            if len(values) < 7:
                continue
            domain = values[0]
            if domain == "No results for current filters":
                continue
            status = self._git_status_cache.get(domain, {})

            git_text = status.get("git", "...")
            remote_text = status.get("remote", "...")
            values[3] = git_text
            values[4] = remote_text


            if git_text == "Initialized" and remote_text == "Connected":
                color_tag = "git_yes"
            elif git_text in ("Not Init", "Error") or remote_text in ("Not Connected", "Error"):
                color_tag = "git_no"
            else:
                color_tag = "checking"

            row_tag = "row_even" if idx % 2 == 0 else "row_odd"
            tree.item(item, values=values, tags=(row_tag, "buttons", color_tag))

    def _populate_ip_dropdown(self):
        seen = set()
        ips = []
        for domain_name, ip, _ in self.all_entries:
            if self._is_manage_table_target_entry(domain_name, ip) and ip not in seen:
                seen.add(ip)
                ips.append(ip)
        values = ["All IPs"] + sorted(ips)
        self.view.ip_filter_dropdown["values"] = values
        if self.view.ip_filter_var.get() not in values:
            self.view.ip_filter_var.set("All IPs")

        self.view.manage_ip_filter_dropdown["values"] = values
        if self.view.manage_ip_filter_var.get() not in values:
            self.view.manage_ip_filter_var.set("All IPs")

    def _populate_dropdown(self):
        all_domains = [
            domain
            for domain, ip, _stype in self.all_entries
            if self._is_manage_table_target_entry(domain, ip)
        ]
        seen = set()
        unique = []
        for d in all_domains:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        domains = ["-- Overview --"] + unique
        self.view.subdomain_dropdown["values"] = domains
        if self.view.subdomain_var.get() not in domains:
            self.view.subdomain_var.set("-- Overview --")
