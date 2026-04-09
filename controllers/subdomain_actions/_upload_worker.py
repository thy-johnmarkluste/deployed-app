"""Upload worker — SFTP upload, git init / commit / push logic."""
from models.config import get_github_token as _get_saved_token


class UploadWorkerMixin:
    """Provides _do_upload_project (background thread worker)."""

    def _do_upload_project(self, domain, local_path, repo_url, github_token,
                           commit_msg, log_fn, done_fn, *,
                           clean_first=True, force_push=True,
                           framework="none", dependencies=None, branch="main"):
        """Upload files via SFTP, then init git / connect remote / commit / force-push.

        *clean_first*  – remove all non-.git files on the server before uploading
                         so stale artefacts (node_modules, dist, etc.) don't persist.
        *force_push*   – use ``git push --force`` so the upload always succeeds
                         even when the remote has diverged.
        *framework*    – optional framework to install after upload ('vite'/'wordpress').
        *dependencies* – list of dependency keys to install.
        """
        if dependencies is None:
            dependencies = []
        client = None
        try:
            log_fn(f"Connecting to {self.hostname}\u2026")
            client = self.ssh.connect()
            if not client:
                log_fn("ERROR: SSH connection failed.")
                return


            log_fn(f"Ensuring /var/www/{domain} exists\u2026")
            ok, msg = self.git_manager.create_subdomain_folder(client, domain, log_fn)
            if not ok:
                log_fn(f"ERROR: {msg}")
                return

            is_repo = self.git_manager.is_git_repo(client, domain)
            if not is_repo:
                log_fn("Initializing Git repository\u2026")
                ok, msg = self.git_manager.init_git_repo(client, domain, log_fn)
                log_fn(msg)
                if not ok:
                    return
                ok, msg = self.git_manager.add_and_commit(
                    client, domain, "Initial commit", log_fn
                )
                log_fn(msg)
            else:
                log_fn("Git repository already initialized.")


            log_fn("[Snapshot] Guard active for upload worker")
            snap_ok, snap_msg, snap_meta = self.git_manager.create_deployment_snapshot(
                client,
                domain,
                operation="upload",
                reason="Auto snapshot before upload dialog deployment",
                log_callback=log_fn,
            )
            log_fn(f"[Snapshot] {snap_msg}")
            if snap_ok and snap_meta.get("snapshot_id"):
                log_fn(f"[Snapshot] ID: {snap_meta['snapshot_id']}")
            if not snap_ok:
                log_fn("Upload blocked: failed to create deployment snapshot.")
                return


            log_fn(f"\n--- SFTP Upload ---")
            ok, msg = self.git_manager.upload_folder_to_server(
                client, local_path, domain, log_fn,
                clean_first=clean_first,
                snapshot_before_upload=False,
            )
            log_fn(msg)
            if not ok:
                log_fn("SFTP upload failed.")
                return


            if framework and framework != "none":
                log_fn(f"\n--- Framework Installation: {framework.upper()} ---")


                class _LogAdapter:
                    def log(self_inner, msg, tag="info"):
                        log_fn(msg)
                _v = _LogAdapter()

                if framework == "vite":
                    fw_ok, fw_msg = self.git_manager.install_vite(
                        client, domain, log_fn
                    )
                    if dependencies:
                        self._install_npm_dependencies(client, domain, dependencies, _v)
                elif framework == "wordpress":
                    fw_ok, fw_msg = self.git_manager.install_wordpress(
                        client, domain, log_fn
                    )
                    if dependencies:
                        self._install_wp_dependencies(client, domain, dependencies, _v)
                else:
                    fw_ok, fw_msg = False, f"Unknown framework: {framework}"
                log_fn(fw_msg)
                if not fw_ok:
                    log_fn("WARNING: Framework setup had issues, continuing with commit...")


            vhost_name = domain.replace('/', '')
            vhost_path = f"/etc/apache2/sites-available/{vhost_name}.conf"
            check_ao = (
                f"test -f '{vhost_path}' && "
                f"grep -q 'AllowOverride All' '{vhost_path}' && echo 'YES' || echo 'NO'"
            )
            _, stdout, _ = client.exec_command(check_ao)
            if stdout.read().decode().strip() != 'YES':
                log_fn("Updating vhost AllowOverride to All...")
                ao_cmd = (
                    f"sed -i 's|AllowOverride.*|AllowOverride All|g' '{vhost_path}' 2>/dev/null"
                )
                _, stdout, _ = client.exec_command(ao_cmd)
                stdout.read()


            enable_cmd = "a2enmod mime 2>/dev/null; systemctl reload apache2 2>&1"
            _, stdout, _ = client.exec_command(enable_cmd)
            stdout.read()


            has_remote = False
            if repo_url:
                log_fn(f"\nSetting remote origin to {repo_url}\u2026")
                ok, msg = self.git_manager.add_remote(
                    client, domain, repo_url, "origin", log_fn
                )
                log_fn(msg)
                has_remote = ok
            else:

                has_remote, existing_url = self.git_manager.get_remote_info(client, domain)
                if has_remote:
                    log_fn(f"\nUsing existing remote: {existing_url}")


            log_fn(f"\n--- Git Commit ---")
            ok, msg = self.git_manager.add_and_commit(
                client, domain, commit_msg, log_fn
            )
            log_fn(msg)


            if has_remote:
                log_fn(f"\n--- Git Push ---")
                ok, msg = self.git_manager.push_to_remote(
                    client, domain, log_callback=log_fn,
                    github_token=github_token,
                    force=force_push,
                    branch=branch,
                )
                log_fn(msg)
                if ok:
                    log_fn(f"\n\u2713 Upload & Push complete \u2014 files are on the server and GitHub.")
                else:
                    log_fn(f"\n\u26a0 Files uploaded to server but push to GitHub failed.")
            else:
                log_fn(f"\n\u2713 Upload complete \u2014 files are on the server (no GitHub push).")
                if not repo_url:
                    log_fn("Tip: provide a GitHub URL to also push to a repository.")


            self._git_status_cache[domain] = {
                "git": "Initialized",
                "remote": "Connected" if has_remote else "Not Connected",
            }
            self.root.after(0, self._update_tree_git_status)

            self._record_app_activity(
                domain, "upload",
                f"Uploaded project from {local_path}" + (f" and pushed to {repo_url}" if has_remote and repo_url else ""),
            )
        except Exception as exc:
            log_fn(f"\nERROR: {exc}")
        finally:
            if client:
                try:
                    client.close()
                except Exception:
                    pass
            self.root.after(0, done_fn)
