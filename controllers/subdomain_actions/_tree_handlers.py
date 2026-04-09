"""Tree click handlers for subdomain management and open views."""
import re
import tkinter as tk


class TreeHandlersMixin:
    """Handle click events on the manage and open DNS tree views."""


    def handle_manage_click(self, event):
        tree = self.view.manage_dns_tree
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = tree.identify_column(event.x)
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        values = tree.item(row_id, "values")
        if len(values) < 2:
            return
        if values[0] == "No results for current filters":
            return
        ip = values[1]
        domain = values[0]

        if col == "#6":
            self._generate_report_for_row(domain, ip)
        elif col == "#7":
            self._show_action_menu(domain, event)

    def handle_open_click(self, event):
        tree = self.view.dns_tree
        region = tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = tree.identify_column(event.x)
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        values = tree.item(row_id, "values")
        if len(values) < 2:
            return
        ip = values[1]
        display_domain = values[0]
        domain = re.sub(r"\s*\((R|U|V)\)$", "", display_domain)

        if col == "#3":
            bbox = tree.bbox(row_id, column=col)
            if not bbox:
                return
            if ip:
                import webbrowser
                url = f"http://{ip}"
                try:
                    webbrowser.open(url)
                    self.view.status_var.set(f"Opened {url} in browser.")
                except Exception as e:
                    self.view.status_var.set(f"Failed to open {url}: {e}")
        elif col == "#4":
            self._generate_report_for_row(domain, ip)
