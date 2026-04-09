"""Git status checking — check repo status, refresh branches."""


class GitStatusMixin:
    """Methods for checking Git status and branch information."""

    def schedule_git_status_check(self, subdomain, *, silent=True):
        """Queue a status refresh for the given subdomain."""
        self.submit_background_job(
            "Check Git Status",
            self._git_check_status_thread,
            args=(subdomain,),
            dedupe_key=f"git_status:{subdomain}",
            source="git",
            silent=silent,
        )


    def git_check_status(self):
        """Check the Git status for the selected subdomain."""
        subdomain = self.view.repo_setup_page.get_selected_subdomain()
        if not subdomain:
            return
        self.schedule_git_status_check(subdomain, silent=False)

    def git_refresh_branches(self):
        """Fetch and populate the branch dropdown for the selected subdomain."""
        subdomain = self.view.repo_setup_page.get_selected_subdomain()
        if not subdomain:
            return

        def _worker():
            v = self.view.repo_setup_page
            client = None

            def _ui_log(msg):
                self.root.after(0, lambda m=msg: v.log(m))

            try:
                _ui_log("Fetching branches...")
                client = self.ssh.connect()
                if not client:
                    _ui_log("ERROR: SSH connection failed.")
                    return
                github_token = v.get_github_token()
                branches, current = self.git_manager.list_remote_branches(
                    client, subdomain, github_token=github_token,
                    log_callback=_ui_log,
                )
                self.root.after(
                    0, lambda b=branches, c=current: v.set_branches(b, c)
                )
            except Exception as e:
                _ui_log(f"Error fetching branches: {e}")
            finally:
                if client:
                    client.close()

        self.submit_background_job(
            "Refresh Branch List",
            _worker,
            dedupe_key=f"git_branches:{subdomain}",
            source="git",
            silent=True,
        )

    def _git_check_status_thread(self, subdomain):
        """Thread worker for checking Git status."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        try:
            _ui_log(f"Checking Git status for {subdomain}...")
            client = self.ssh.connect()


            folder_exists = self.git_manager.folder_exists(client, subdomain)
            if not folder_exists:
                _ui_log("Subdomain folder does not exist yet.")
                self.root.after(0, lambda: v.update_git_status(False))
                self.root.after(0, lambda: v.update_remote_status(False))
                self.root.after(0, lambda: v.update_sync_status(True, "No folder"))
                self.root.after(0, lambda: v.update_files_status(0))
                return


            is_repo = self.git_manager.is_git_repo(client, subdomain)
            self.root.after(0, lambda: v.update_git_status(is_repo))

            if not is_repo:
                _ui_log("Not a Git repository.")
                self.root.after(0, lambda: v.update_remote_status(False))
                self.root.after(0, lambda: v.update_sync_status(False, "No Git"))
                self.root.after(0, lambda: v.update_files_status(0))
                return


            has_remote, remote_url = self.git_manager.get_remote_info(client, subdomain)
            self.root.after(0, lambda: v.update_remote_status(has_remote, remote_url))


            if has_remote:
                github_token = v.get_github_token()
                branches, current_branch = self.git_manager.list_remote_branches(
                    client, subdomain, github_token=github_token,
                )
                self.root.after(
                    0, lambda b=branches, c=current_branch: v.set_branches(b, c)
                )
            else:
                current_branch = self.git_manager.get_current_branch(client, subdomain)
                self.root.after(
                    0, lambda c=current_branch: v.set_branches([c], c)
                )


            success, msg, changes = self.git_manager.get_git_status(client, subdomain)
            self.root.after(0, lambda: v.update_files_status(len(changes)))

            if has_remote:

                success, sync_msg, result = self.git_manager.compare_with_remote(client, subdomain)
                self.root.after(0, lambda: v.update_sync_status(result.get("synced", False), sync_msg))
                _ui_log(f"Sync status: {sync_msg}")
            else:
                self.root.after(0, lambda: v.update_sync_status(False, "No remote"))

            _ui_log(f"Status check complete for {subdomain}")

        except Exception as e:
            _ui_log(f"Error checking status: {str(e)}")
        finally:
            if client:
                client.close()
