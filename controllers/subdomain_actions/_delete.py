"""Delete subdomain — server resources, vhost, DNS, and Vultr record."""
from tkinter import messagebox

from models.config import COLORS
from models.ssh_client import SSHClientManager
from models.vultr_api import delete_vultr_subdomain


class DeleteSubdomainMixin:
    """Methods to delete a subdomain and handle success / error callbacks."""


    def _delete_subdomain(self, domain):
        """Delete subdomain folder, vhost config, and Vultr DNS record with confirmation."""
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete the subdomain '{domain}'?\n\n"
            f"This will remove:\n"
            f"  \u2022 /var/www/{domain}/\n"
            f"  \u2022 Apache vhost config (sites-available & sites-enabled)\n"
            f"  \u2022 DNS entry from custom_dns.txt\n"
            f"  \u2022 Vultr DNS record (if registered)\n\n"
            f"This action cannot be undone.",
        )
        if not confirm:
            return

        v = self.view
        v.status_var.set(f"Deleting subdomain {domain}...")
        v.update_status_chip("Working", bg_color=COLORS["warning"], fg_color="#000000")

        def _worker():
            errors = []


            try:
                ssh_mgr = SSHClientManager(self.hostname, self.username, self.password)
                client = ssh_mgr.connect()
                try:
                    ssh_mgr.delete_subdomain(client, domain)
                finally:
                    client.close()
            except Exception as e:
                errors.append(f"Server: {e}")


            try:
                ok, msg = delete_vultr_subdomain(domain)
                if not ok:
                    errors.append(f"Vultr: {msg}")
            except Exception as e:
                errors.append(f"Vultr: {e}")

            if errors:
                self.root.after(0, lambda: self._on_delete_error(domain, "\n".join(errors)))
            else:
                self.root.after(0, lambda: self._on_delete_success(domain))

        self.submit_background_job(
            "Delete Subdomain",
            _worker,
            dedupe_key=f"delete_subdomain:{domain}",
            source="dns",
        )

    def _on_delete_success(self, domain):
        v = self.view
        v.status_var.set(f"Subdomain '{domain}' deleted successfully.")
        v.update_status_chip("Connected", bg_color=COLORS["success"], fg_color="white")

        self._git_status_cache.pop(domain, None)
        messagebox.showinfo("Deleted", f"Subdomain '{domain}' has been deleted successfully.")

        self.load_dns_entries()

    def _on_delete_error(self, domain, error):
        v = self.view
        v.status_var.set(f"Failed to delete '{domain}'.")
        v.update_status_chip("Error", bg_color=COLORS["error"], fg_color="white")
        messagebox.showerror("Delete Failed", f"Failed to delete subdomain '{domain}':\n\n{error}")

        self.load_dns_entries()
