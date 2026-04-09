"""Git upload-and-push — SFTP upload, commit, and push to remote."""
import os
import traceback
from tkinter import messagebox


class GitUploadPushMixin:
    """Methods for uploading local folders to server, committing, and pushing."""


    def git_upload_and_push(self):
        """Upload local folder to server, commit, and push to remote."""
        subdomain = self._validate_subdomain_selected()
        if not subdomain:
            return


        if not self._require_git_initialized():
            return

        upload_folder = self.view.repo_setup_page.get_upload_folder()
        if not upload_folder:
            messagebox.showwarning(
                "No Upload Folder",
                "Please select a local folder to upload.\n\n"
                "Use the 'Browse...' button to pick your project folder."
            )
            return

        if not os.path.isdir(upload_folder):
            messagebox.showerror(
                "Invalid Folder",
                f"The folder does not exist:\n{upload_folder}"
            )
            return

        commit_msg = self.view.repo_setup_page.get_commit_message()
        framework = self.view.repo_setup_page.get_selected_framework()
        dependencies = self.view.repo_setup_page.get_selected_dependencies()

        framework_label = {"vite": "Vite", "wordpress": "WordPress"}.get(framework, "")
        framework_note = f"\n\nFramework to install: {framework_label}" if framework_label else ""
        if dependencies:
            dep_list = ", ".join(dependencies)
            framework_note += f"\nDependencies: {dep_list}"

        if not messagebox.askyesno(
            "Confirm Upload & Push",
            f"Upload files from:\n  {upload_folder}\n\n"
            f"To subdomain folder on server:\n"
            f"  /var/www/{subdomain}/public_html\n\n"
            f"Then commit and push to remote.{framework_note}\n\nContinue?"
        ):
            return

        self.submit_background_job(
            "Upload & Push",
            self._git_upload_push_thread,
            args=(subdomain, upload_folder, commit_msg, framework, dependencies),
            dedupe_key=f"git_upload_push:{subdomain}",
            source="git",
        )

    def _git_upload_push_thread(self, subdomain, upload_folder, commit_msg, framework="none", dependencies=None):
        """Thread worker for upload, commit, push, and optional framework install."""
        if dependencies is None:
            dependencies = []
        v = self.view.repo_setup_page
        client = None

        def _ui_log(msg):
            self.root.after(0, lambda m=msg: v.log(m))

        def _ui_status(text):
            self.root.after(0, lambda t=text: self.view.status_var.set(t))

        class _LogAdapter:
            def log(self_inner, msg, tag="info"):
                _ui_log(msg)

        try:
            _ui_log(f"\n{'=' * 50}")
            _ui_log(f"Upload & Push: {upload_folder}")
            _ui_log(f"  -> /var/www/{subdomain}/public_html")
            if framework and framework != "none":
                _ui_log(f"  Framework: {framework}")
                if dependencies:
                    _ui_log(f"  Dependencies: {', '.join(dependencies)}")
            _ui_status("Uploading files...")

            client = self.ssh.connect()
            if not client:
                _ui_log("ERROR: Could not connect to server via SSH.")
                _ui_status("SSH connection failed")
                return

            selected_branch = self.view.repo_setup_page.get_selected_branch()
            allow_upload, preflight = self._run_preflight_checks(
                client,
                subdomain,
                operation="upload",
                selected_branch=selected_branch,
            )
            self._report_preflight("upload", preflight, _ui_log)
            if not allow_upload:
                _ui_status("Upload blocked by preflight checks")
                return

            _ui_log("SSH connected successfully.")


            if not self.git_manager.is_git_repo(client, subdomain):
                _ui_log("Initializing Git repository first...")
                success, msg = self.git_manager.init_git_repo(client, subdomain, _ui_log)
                if not success:
                    _ui_log(f"Failed to init git: {msg}")
                    _ui_status("Git init failed")
                    return
                _ui_log(msg)
            else:
                _ui_log("Git repository already initialized.")


            _ui_log("\n--- SFTP Upload ---")
            _ui_log(f"Local:  {upload_folder}")
            _ui_log(f"Remote: /var/www/{subdomain}/public_html")
            _ui_status("Uploading files via SFTP...")
            success, msg = self.git_manager.upload_folder_to_server(
                client, upload_folder, subdomain, _ui_log,
                clean_first=True,
            )
            _ui_log(msg)

            if not success:
                _ui_log("SFTP upload failed!")
                _ui_status("Upload failed")
                return


            if framework and framework != "none":
                _ui_log(f"\n--- Framework Installation: {framework.upper()} ---")
                _ui_status(f"Installing {framework} dependencies...")
                if framework == "vite":
                    fw_success, fw_msg = self.git_manager.install_vite(
                        client, subdomain, _ui_log
                    )

                    if dependencies:
                        self._install_npm_dependencies(client, subdomain, dependencies, _LogAdapter())
                elif framework == "wordpress":
                    fw_success, fw_msg = self.git_manager.install_wordpress(
                        client, subdomain, _ui_log
                    )

                    if dependencies:
                        self._install_wp_dependencies(client, subdomain, dependencies, _LogAdapter())
                else:
                    fw_success, fw_msg = False, f"Unknown framework: {framework}"

                _ui_log(fw_msg)
                if not fw_success:
                    _ui_log("WARNING: Framework setup failed, continuing with commit...")
            else:

                _ui_log("\n--- Auto-Detect Dependencies ---")
                _ui_status("Checking for dependencies...")
                path = self.git_manager.get_subdomain_path(subdomain)


                check_cmd = f"test -f '{path}/package.json' && echo 'YES' || echo 'NO'"
                _, stdout, _ = client.exec_command(check_cmd)
                has_pkg = stdout.read().decode().strip() == 'YES'


                check_wp = (
                    f"test -f '{path}/wp-config.php' -o "
                    f"-f '{path}/wp-config-sample.php' && echo 'YES' || echo 'NO'"
                )
                _, stdout, _ = client.exec_command(check_wp)
                has_wp = stdout.read().decode().strip() == 'YES'

                if has_pkg:
                    _ui_log("Detected Node.js project (package.json)")
                    _ui_status("Installing npm dependencies...")
                    fw_success, fw_msg = self.git_manager.install_vite(
                        client, subdomain, _ui_log
                    )
                    _ui_log(fw_msg)
                elif has_wp:
                    _ui_log("Detected WordPress project")
                    _ui_status("Setting up WordPress...")
                    fw_success, fw_msg = self.git_manager.install_wordpress(
                        client, subdomain, _ui_log
                    )
                    _ui_log(fw_msg)
                else:
                    _ui_log("No package.json or WordPress detected — skipping dependency install.")

            _ui_log("\n--- Git Commit ---")

            _ui_log("Adding and committing all files...")
            _ui_status("Committing...")
            success, msg = self.git_manager.add_and_commit(
                client, subdomain, commit_msg, _ui_log
            )
            _ui_log(msg)

            if not success:
                _ui_log(f"Commit failed: {msg}")
                _ui_status("Commit failed")
                return


            has_remote, remote_url = self.git_manager.get_remote_info(client, subdomain)
            if has_remote:
                _ui_log("\n--- Git Push ---")
                _ui_log(f"Remote: {remote_url}")
                _ui_status("Pushing to remote...")
                github_token = self.view.repo_setup_page.get_github_token()
                success, msg = self.git_manager.push_to_remote(
                    client, subdomain, log_callback=_ui_log,
                    github_token=github_token,
                    force=True,
                )
                _ui_log(msg)
                if success:
                    _ui_status("Upload & Push complete!")
                else:
                    _ui_status("Push failed (files uploaded to server)")
            else:
                _ui_log("\nNo remote configured — files uploaded and committed locally.")
                _ui_log("Use 'Connect Remote' then 'Commit & Push' to push to GitHub.")
                _ui_status("Upload & Commit complete (no remote)")

            _ui_log(f"\n{'=' * 50}")
            self._record_app_activity(subdomain, "upload", f"Upload & Push: {upload_folder}")
            self.root.after(0, lambda sd=subdomain: self.schedule_git_status_check(sd))

        except Exception as e:
            _ui_log(f"ERROR: {str(e)}")
            _ui_log(traceback.format_exc())
            _ui_status(f"Error: {str(e)}")
        finally:
            if client:
                client.close()
