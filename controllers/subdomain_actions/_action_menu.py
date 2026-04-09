"""Action column popup menu for subdomain rows."""
import tkinter as tk


class ActionMenuMixin:
    """Popup context menu with Connect, Upload, Manage, and Delete actions."""


    def _show_action_menu(self, domain, event):
        """Show a popup context menu with Connect, Upload Project, and Delete actions."""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(
            label="\U0001f517  Connect to GitHub",
            command=lambda: self._open_connect_dialog(domain),
        )
        menu.add_separator()
        menu.add_command(
            label="\u2699  Manage Repository",
            command=lambda: self._manage_subdomain_repo(domain),
        )
        menu.add_separator()
        menu.add_command(
            label="\U0001f4c2  File Editor",
            command=lambda: self._open_file_manager_for(domain),
        )
        menu.add_separator()
        menu.add_command(
            label="\u2b06  Upload Project",
            command=lambda: self._open_upload_dialog(domain),
        )
        menu.add_separator()
        menu.add_command(
            label="\U0001f5d1  Delete Subdomain",
            command=lambda: self._delete_subdomain(domain),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()


    def _manage_subdomain_repo(self, domain):
        """Navigate to the Repository Setup page with the subdomain auto-selected."""
        self._refresh_repo_subdomains()
        rp = self.view.repo_setup_page

        values = list(rp.subdomain_dropdown["values"])
        if domain in values:
            rp.subdomain_var.set(domain)
        else:

            values.append(domain)
            rp.subdomain_dropdown["values"] = values
            rp.subdomain_var.set(domain)
        self.view.show_repo_setup_page()

        rp.reset_status()
        self.git_check_status()
