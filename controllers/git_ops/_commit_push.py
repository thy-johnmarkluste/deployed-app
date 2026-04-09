"""Git commit, push, pull, and quick-sync operations."""
import traceback


class GitCommitPushMixin:
    """Methods for committing, pushing, pulling, and quick-syncing."""

    def git_rollback_latest(self):
        """Rollback deployment to the most recent snapshot."""
        self.git_rollback_to_snapshot("")

    def git_rollback_to_snapshot(self, snapshot_id: str):
        """Rollback deployment to a snapshot id (or latest when empty)."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return

        self.submit_background_job(
            "Git Rollback",
            self._git_rollback_thread,
            args=(subdomain, (snapshot_id or "").strip()),
            dedupe_key=f"git_rollback:{subdomain}",
            source="git",
        )

    def _git_rollback_thread(self, subdomain: str, snapshot_id: str):
        """Thread worker for snapshot rollback."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log("Rolling back deployment from snapshot...")
            _ui_status("Rolling back deployment...")

            client = self.ssh.connect()
            if not client:
                _ui_log("ERROR: Could not connect to server via SSH.")
                _ui_status("SSH connection failed")
                return

            success, msg, meta = self.git_manager.rollback_to_snapshot(
                client,
                subdomain,
                snapshot_id=snapshot_id,
                log_callback=_ui_log,
            )
            _ui_log(msg)

            if not success:
                _ui_status("Rollback failed")
                return

            restored_id = meta.get("snapshot_id", "latest")
            _ui_status("Rollback complete")
            self._record_app_activity(subdomain, "rollback", f"Rollback restored snapshot {restored_id}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()


    def git_commit_push(self):
        """Commit local changes and push to remote."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return


        if not self._require_remote_connected():
            return

        commit_msg = self.view.repo_setup_page.get_commit_message()

        self.submit_background_job(
            "Git Commit & Push",
            self._git_commit_push_thread,
            args=(subdomain, commit_msg),
            dedupe_key=f"git_commit_push:{subdomain}",
            source="git",
        )

    def _git_commit_push_thread(self, subdomain, commit_msg):
        """Thread worker for commit and push."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log("Committing and pushing changes...")
            _ui_status("Committing and pushing...")

            client = self.ssh.connect()


            success, msg = self.git_manager.add_and_commit(client, subdomain, commit_msg, _ui_log)
            _ui_log(msg)

            if not success:
                return


            github_token = self.view.repo_setup_page.get_github_token()
            success, msg = self.git_manager.push_to_remote(
                client, subdomain, log_callback=_ui_log, github_token=github_token
            )
            _ui_log(msg)

            _ui_status("Changes pushed")
            self._record_app_activity(subdomain, "push", f"Commit & Push: {commit_msg}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()


    def git_pull(self):
        """Pull changes from remote repository."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return


        if not self._require_remote_connected():
            return

        self.submit_background_job(
            "Git Pull",
            self._git_pull_thread,
            args=(subdomain,),
            dedupe_key=f"git_pull:{subdomain}",
            source="git",
        )

    def _git_pull_thread(self, subdomain):
        """Thread worker for pulling changes.
        Uses force_remote=True so that merged branches on GitHub
        always overwrite the server folder (GitHub is source of truth).
        After pulling, auto-detects and rebuilds Vite/WordPress projects.
        """
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log("Pulling changes from remote...")
            _ui_status("Pulling changes...")

            client = self.ssh.connect()
            if not client:
                _ui_log("ERROR: Could not connect to server via SSH.")
                _ui_status("SSH connection failed")
                return

            selected_branch = self.view.repo_setup_page.get_selected_branch()
            allow_pull, preflight = self._run_preflight_checks(
                client,
                subdomain,
                operation="pull",
                selected_branch=selected_branch,
            )
            self._report_preflight("pull", preflight, _ui_log)
            if not allow_pull:
                _ui_status("Pull blocked by preflight checks")
                return


            github_token = self.view.repo_setup_page.get_github_token()
            success, msg = self.git_manager.pull_from_remote(
                client, subdomain, log_callback=_ui_log,
                branch=selected_branch,
                force_remote=True, github_token=github_token
            )
            _ui_log(msg)

            if not success:
                _ui_status("Pull failed")
                return


            _ui_log("\n--- Post-Pull: Checking for rebuild ---")
            _ui_status("Checking for rebuild...")
            path = self.git_manager.get_subdomain_path(subdomain)


            check_pkg = f"test -f '{path}/package.json' && echo 'YES' || echo 'NO'"
            _, stdout, _ = client.exec_command(check_pkg)
            has_pkg = stdout.read().decode().strip() == 'YES'


            check_wp = (
                f"test -f '{path}/wp-config.php' -o "
                f"-f '{path}/wp-config-sample.php' && echo 'YES' || echo 'NO'"
            )
            _, stdout, _ = client.exec_command(check_wp)
            has_wp = stdout.read().decode().strip() == 'YES'

            if has_pkg:
                _ui_log("Detected Node.js project — reinstalling dependencies & rebuilding...")
                _ui_status("Rebuilding project...")
                fw_success, fw_msg = self.git_manager.install_vite(
                    client, subdomain, _ui_log
                )
                _ui_log(fw_msg)
            elif has_wp:
                _ui_log("Detected WordPress project — setting permissions...")
                _ui_status("Setting up WordPress...")
                fw_success, fw_msg = self.git_manager.install_wordpress(
                    client, subdomain, _ui_log
                )
                _ui_log(fw_msg)
            else:
                _ui_log("Static site — no rebuild needed.")

            _ui_log(f"\n{'=' * 50}")
            _ui_log("Pull complete — live site updated.")
            _ui_status("Pull complete — changes broadcasted")
            self._record_app_activity(subdomain, "pull", f"Pulled changes from remote to {subdomain}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_log(traceback.format_exc())
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()


    def git_quick_sync(self):
        """Quick sync - pull, commit, and push."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return


        if not self._require_remote_connected():
            return

        self.submit_background_job(
            "Git Quick Sync",
            self._git_sync_thread,
            args=(subdomain,),
            dedupe_key=f"git_quick_sync:{subdomain}",
            source="git",
        )

    def _git_sync_thread(self, subdomain):
        """Thread worker for quick sync."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log(f"Quick syncing {subdomain}...")
            _ui_status("Syncing...")

            client = self.ssh.connect()

            github_token = self.view.repo_setup_page.get_github_token()
            success, msg = self.git_manager.sync_repo(
                client, subdomain, _ui_log, github_token=github_token
            )
            _ui_log(msg)

            if success:
                self._record_app_activity(subdomain, "sync", f"Quick Sync completed for {subdomain}")
            _ui_status("Sync complete" if success else "Sync failed")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()
