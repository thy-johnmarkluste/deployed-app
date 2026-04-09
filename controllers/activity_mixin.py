"""
Activity Mixin — Activity log loading, recording, and display.
"""

from models.activity_store import append_entry, load_entries


class ActivityMixin:
    """Methods for managing the git / app activity log."""


    def refresh_activity_log(self):
        """Refresh the git activity log for the currently selected subdomain."""
        selected = self.view.subdomain_var.get()
        if selected == "-- Overview --":
            self.view.clear_activity_log()
            return
        self._load_activity_for_subdomain(selected)

    def _load_activity_for_subdomain(self, subdomain):
        """Kick off a background thread to fetch git activity."""
        self.view.activity_status_label.config(text=f"Loading activity for {subdomain}...")
        self.submit_background_job(
            "Load Activity",
            self._fetch_activity_thread,
            args=(subdomain,),
            dedupe_key=f"activity:{subdomain}",
            source="activity",
            silent=True,
        )

    def _fetch_activity_thread(self, subdomain):
        """Thread worker: fetch git log entries for a subdomain."""
        try:
            client = self.ssh.connect()
            if not client:
                app_entries = load_entries(subdomain)
                app_entries.sort(key=lambda e: e.get("date", ""), reverse=True)
                self.root.after(0, lambda ents=app_entries: self.view.update_activity_log(ents[:50]))
                return
            entries = self.git_manager.get_git_activity_log(client, subdomain, limit=50)
            client.close()
            self.root.after(0, lambda: self._on_activity_ready(subdomain, entries))
        except Exception as exc:
            err_msg = str(exc)
            self.root.after(
                0, lambda msg=err_msg: self.view.activity_status_label.config(
                    text=f"Error loading activity: {msg}"
                )
            )
            app_entries = load_entries(subdomain)
            if app_entries:
                app_entries.sort(key=lambda e: e.get("date", ""), reverse=True)
                self.root.after(0, lambda ents=app_entries: self.view.update_activity_log(ents[:50]))

    def _record_app_activity(self, subdomain, action, message):
        """Record an application-level activity for a subdomain.
        Persists to the subdomain's JSON file on disk.  If the file
        already exists it inserts into it — no new file is created."""
        from datetime import datetime
        entry = {
            "hash": "\u2014",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "author": "App",
            "action": action,
            "message": message,
        }

        append_entry(subdomain, entry)

    def _on_activity_ready(self, subdomain, entries):
        """Callback on main thread when activity data is ready.
        Merges git log entries with persisted app-level activity entries."""

        if self.view.subdomain_var.get() != subdomain:
            return


        app_entries = load_entries(subdomain)
        combined = list(entries) + list(app_entries)

        combined.sort(key=lambda e: e.get("date", ""), reverse=True)
        self.view.update_activity_log(combined[:50])
