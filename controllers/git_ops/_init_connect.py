"""Git init, sync, and remote connection operations."""
from tkinter import messagebox

from models.config import COLORS


class GitInitConnectMixin:
    """Methods for initializing Git repos, smart sync, and connecting remotes."""


    def git_init_repo(self):
        """Initialize a Git repository for the selected subdomain."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return

        self.submit_background_job(
            "Initialize Git Repo",
            self._git_init_thread,
            args=(subdomain,),
            dedupe_key=f"git_init:{subdomain}",
            source="git",
        )

    def _git_init_thread(self, subdomain):
        """Thread worker for initializing Git repo."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log(f"Initializing Git repository for {subdomain}...")
            _ui_status("Initializing Git repository...")

            client = self.ssh.connect()


            success, msg = self.git_manager.create_subdomain_folder(client, subdomain, _ui_log)
            if not success:
                _ui_log(f"ERROR: {msg}")
                return


            success, msg = self.git_manager.init_git_repo(client, subdomain, _ui_log)
            _ui_log(msg)

            if success:

                success, msg = self.git_manager.add_and_commit(
                    client, subdomain, "Initial commit", _ui_log
                )
                _ui_log(msg)

            _ui_status("Git repository initialized")
            self._record_app_activity(subdomain, "init", f"Initialized Git repo for {subdomain}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()


    def git_sync(self):
        """Sync: auto-detect server state, commit local changes,
        connect remote, pull, push, rebuild — all in one click."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return

        repo_url = self.view.repo_setup_page.get_repo_url()
        github_token = self.view.repo_setup_page.get_github_token()


        if repo_url and repo_url.startswith("https://") and not github_token:
            proceed = messagebox.askyesno(
                "GitHub Token Missing",
                "You entered a Repository URL but no GitHub Token.\n\n"
                "Without a token:\n"
                "  • Public repos  — sync will work fine.\n"
                "  • Private repos — pull/push will fail.\n\n"
                "Before clicking Sync, make sure to:\n"
                "  1. Paste your GitHub Personal Access Token\n"
                "     in the 'GitHub Token' field.\n"
                "  2. The token needs the 'repo' scope.\n\n"
                "Continue without a token?",
            )
            if not proceed:
                return

        self.submit_background_job(
            "Git Smart Sync",
            self._git_sync_smart_thread,
            args=(subdomain, repo_url, github_token),
            dedupe_key=f"git_smart_sync:{subdomain}",
            source="git",
        )

    def _git_sync_smart_thread(self, subdomain, repo_url, github_token):
        """Smart sync: auto-detect state, commit local, pull, push, rebuild."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log(f"Syncing {subdomain}...")
            _ui_status("Checking server state...")

            client = self.ssh.connect()
            if not client:
                _ui_log("ERROR: Could not connect to server via SSH.")
                _ui_status("SSH connection failed")
                return


            is_repo = self.git_manager.is_git_repo(client, subdomain)
            self.root.after(0, lambda: v.update_git_status(is_repo))

            if not is_repo:
                _ui_log("Git is not initialized for this subdomain.")
                _ui_status("Git not initialized")
                self.root.after(0, lambda: messagebox.showwarning(
                    "Git Not Initialized",
                    "The subdomain folder does not have a Git repository yet.\n\n"
                    "Please click  'Initialize Git Repo'  first,\n"
                    "then try Sync again.",
                ))
                return


            has_remote, existing_url = self.git_manager.get_remote_info(client, subdomain)
            self.root.after(0, lambda: v.update_remote_status(has_remote, existing_url))

            if has_remote and existing_url:
                _ui_log(f"Remote already connected: {existing_url}")
                if not repo_url:
                    repo_url = existing_url
                    clean = self.git_manager._clean_remote_url(existing_url)
                    self.root.after(0, lambda u=clean: self._fill_repo_url(u))

            if not repo_url:
                _ui_log("No remote URL found on server and none entered.")
                _ui_status("No repository URL")
                self.root.after(0, lambda: messagebox.showwarning(
                    "Repository URL Required",
                    "No remote repository is connected to this subdomain\n"
                    "and the Repository URL field is empty.\n\n"
                    "Before clicking Sync, please fill in:\n"
                    "  1. Repository URL  — your GitHub HTTPS URL\n"
                    "     (e.g. https://github.com/user/repo.git)\n"
                    "  2. GitHub Token    — your Personal Access Token\n"
                    "     (needed for private repos)\n\n"
                    "Then click Sync again.",
                ))
                return


            if not github_token and repo_url.startswith("https://"):
                _ui_log("No GitHub token provided — public repos will work, private repos will fail.")
                _ui_log("Tip: Paste your GitHub Token in the field above if this is a private repo.")


            _ui_log("Ensuring remote is connected...")
            _ui_status("Connecting remote...")
            success, msg = self.git_manager.add_remote(
                client, subdomain, repo_url, "origin", _ui_log
            )
            _ui_log(msg)

            path = self.git_manager.get_subdomain_path(subdomain)


            gi_cmd = (
                f"cd '{path}' && "
                f"(test -f .gitignore && grep -q 'node_modules' .gitignore) || "
                f"echo -e 'node_modules/\\n.env' >> .gitignore"
            )
            _, stdout, _ = client.exec_command(gi_cmd)
            stdout.read()


            _ui_log("\nChecking for local changes on server...")
            _ui_status("Committing local changes...")
            commit_ok, commit_msg = self.git_manager.add_and_commit(
                client, subdomain,
                "Auto-sync: commit local changes before pull",
                log_callback=_ui_log,
            )
            _ui_log(commit_msg)

            if not self._capture_predeploy_snapshot(client, subdomain, "sync", _ui_log):
                _ui_status("Sync blocked: snapshot failed")
                return


            _ui_log("\nPulling latest changes from remote...")
            _ui_status("Pulling changes...")
            selected_branch = self.view.repo_setup_page.get_selected_branch()
            pull_ok, pull_msg = self.git_manager.pull_from_remote(
                client, subdomain, log_callback=_ui_log,
                branch=selected_branch,
                force_remote=False, github_token=github_token,
            )
            _ui_log(pull_msg)

            if not pull_ok:
                _ui_status("Sync failed — see log")
                return


            _ui_log("\nPushing synced state to remote...")
            _ui_status("Pushing to remote...")
            push_ok, push_msg = self.git_manager.push_to_remote(
                client, subdomain, log_callback=_ui_log,
                github_token=github_token,
            )
            _ui_log(push_msg)
            if not push_ok:
                _ui_log("Note: Pull succeeded but push failed — server is up to date locally.")


            _ui_log("\n--- Post-Pull: Checking for rebuild ---")
            _ui_status("Checking for rebuild...")


            diff_cmd = f"cd '{path}' && git diff --name-only HEAD@{{1}} HEAD 2>/dev/null || echo ''"
            _, stdout, _ = client.exec_command(diff_cmd)
            changed_files = stdout.read().decode().strip()

            check_pkg = f"test -f '{path}/package.json' && echo 'YES' || echo 'NO'"
            _, stdout, _ = client.exec_command(check_pkg)
            has_pkg = stdout.read().decode().strip() == 'YES'

            check_wp = (
                f"test -f '{path}/wp-config.php' -o "
                f"-f '{path}/wp-config-sample.php' && echo 'YES' || echo 'NO'"
            )
            _, stdout, _ = client.exec_command(check_wp)
            has_wp = stdout.read().decode().strip() == 'YES'

            needs_rebuild = False
            if has_pkg:
                rebuild_triggers = ['package.json', 'package-lock.json', 'yarn.lock',
                                    'vite.config', 'tsconfig', 'src/', 'public/']
                if any(trigger in changed_files for trigger in rebuild_triggers):
                    needs_rebuild = True
                    _ui_log("Detected changes in source/dependencies — rebuilding...")
                    _ui_status("Rebuilding project...")
                    fw_ok, fw_msg = self.git_manager.install_vite(client, subdomain, _ui_log)
                    _ui_log(fw_msg)
                else:
                    _ui_log("No dependency or source changes — skipping rebuild.")
            elif has_wp:
                wp_triggers = ['wp-config', 'wp-content/', 'wp-includes/', 'wp-admin/']
                if any(trigger in changed_files for trigger in wp_triggers):
                    needs_rebuild = True
                    _ui_log("Detected WordPress changes — updating permissions...")
                    _ui_status("Setting up WordPress...")
                    fw_ok, fw_msg = self.git_manager.install_wordpress(client, subdomain, _ui_log)
                    _ui_log(fw_msg)
                else:
                    _ui_log("No WordPress core changes — skipping setup.")
            else:
                _ui_log("Static site — no rebuild needed.")


            if needs_rebuild:
                _ui_log("\nCommitting post-build changes...")
                _ui_status("Committing build artifacts...")
                pb_ok, pb_msg = self.git_manager.add_and_commit(
                    client, subdomain,
                    "Auto-sync: commit build artifacts",
                    log_callback=_ui_log,
                )
                _ui_log(pb_msg)
                if pb_ok and pb_msg != "No changes to commit":
                    _ui_log("Pushing post-build changes...")
                    pb_push_ok, pb_push_msg = self.git_manager.push_to_remote(
                        client, subdomain, log_callback=_ui_log,
                        github_token=github_token,
                    )
                    _ui_log(pb_push_msg)

            _ui_log(f"\n{'=' * 50}")
            _ui_log("Sync complete — local & remote are in sync, live site updated.")
            _ui_status("Sync complete")
            self._record_app_activity(
                subdomain, "sync",
                f"Synced {subdomain}: committed local, pulled remote, pushed back",
            )
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            import traceback
            _ui_log(f"ERROR: {str(e)}")
            _ui_log(traceback.format_exc())
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()

    def _fill_repo_url(self, url):
        """Fill the repo URL entry field with the detected URL."""
        entry = self.view.repo_setup_page.repo_url_entry
        entry.delete(0, "end")
        entry.insert(0, url)


    def git_connect_remote(self):
        """Connect a remote repository to the subdomain folder."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return


        if not self._require_git_initialized():
            return

        repo_url = self.view.repo_setup_page.get_repo_url()
        if not repo_url:
            messagebox.showwarning(
                "No Repository URL",
                "Please enter a repository URL to connect."
            )
            return

        self.submit_background_job(
            "Connect Git Remote",
            self._git_connect_thread,
            args=(subdomain, repo_url),
            dedupe_key=f"git_connect:{subdomain}",
            source="git",
        )

    def _git_connect_thread(self, subdomain, repo_url):
        """Thread worker for connecting remote repository."""
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log("Connecting remote repository...")
            _ui_status("Connecting remote...")

            client = self.ssh.connect()

            success, msg = self.git_manager.add_remote(client, subdomain, repo_url, "origin", _ui_log)
            _ui_log(msg)

            _ui_status("Remote connected")
            self._record_app_activity(subdomain, "connect", f"Connected remote: {repo_url}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()
