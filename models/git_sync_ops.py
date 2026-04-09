"""
Git Sync Operations Mixin — push, pull, sync, compare, and activity log.
"""
import re
from typing import Callable, Optional, Tuple, List


class GitSyncOpsMixin:
    """Methods for syncing Git repositories with remote origins."""

    def push_to_remote(
        self,
        client,
        subdomain: str,
        remote_name: str = "origin",
        branch: str = None,
        force: bool = False,
        github_token: str = "",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Push commits to remote repository."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository. Initialize first."


        self._ensure_safe_directory(client, path)


        check_url_cmd = f"cd '{path}' && git remote get-url {remote_name} 2>/dev/null"
        _, stdout, _ = client.exec_command(check_url_cmd)
        current_url = stdout.read().decode().strip()


        clean_url = self._clean_remote_url(current_url)
        if clean_url != current_url:
            fix_cmd = f"cd '{path}' && git remote set-url {remote_name} '{clean_url}'"
            _, stdout, stderr = client.exec_command(fix_cmd)
            stdout.read(); stderr.read()
            if log_callback:
                log_callback("Cleaned stored remote URL.")


        if branch is None:
            branch = self.get_current_branch(client, subdomain)


        if branch == "master":
            rename_cmd = f"cd '{path}' && git branch -M main"
            _, stdout, stderr = client.exec_command(rename_cmd)
            stdout.read(); stderr.read()
            branch = "main"
            if log_callback:
                log_callback("Renamed branch master → main")

        if log_callback:
            log_callback(f"Branch: {branch}")


        log_cmd = f"cd '{path}' && git log --oneline -1 2>&1"
        _, stdout, _ = client.exec_command(log_cmd)
        log_out = stdout.read().decode().strip()
        if log_callback:
            log_callback(f"Last commit: {log_out}")
        if not log_out or 'fatal' in log_out.lower():
            return False, "No commits to push. Commit first."


        force_flag = "-f" if force else ""

        if github_token and clean_url and clean_url.startswith("https://"):

            push_url = self._build_push_url(clean_url, github_token)
            if log_callback:
                log_callback("Using token authentication...")
            cmd = (
                f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
                f"git push {force_flag} '{push_url}' HEAD:{branch} 2>&1"
            )
        else:

            cmd = (
                f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
                f"git push {force_flag} -u {remote_name} {branch} 2>&1"
            )

        if log_callback:
            log_callback(f"Pushing to {remote_name}/{branch}...")

        _, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()


        combined = f"{output}\n{error}".strip()

        if log_callback and combined:
            for line in combined.split('\n'):
                if line.strip():
                    log_callback(line)

        if "fatal:" in combined.lower() or "error:" in combined.lower():
            if "authentication" in combined.lower() or "could not read" in combined.lower() or "invalid username" in combined.lower():
                if log_callback:
                    log_callback("")
                    log_callback("HINT: Push authentication failed. Please check:")
                    log_callback("  1. Is your Personal Access Token valid / not expired?")
                    log_callback("  2. Does it have the 'repo' scope enabled?")
                    log_callback("  3. Generate a new token at: github.com/settings/tokens")
                return False, "Push failed: GitHub token invalid or expired. Generate a new one."
            return False, f"Push failed: {combined}"


        if github_token and clean_url and clean_url.startswith("https://"):
            track_cmd = (
                f"cd '{path}' && git fetch {remote_name} 2>/dev/null; "
                f"git branch --set-upstream-to={remote_name}/{branch} {branch} 2>/dev/null"
            )
            _, stdout, stderr = client.exec_command(track_cmd)
            stdout.read(); stderr.read()

        return True, f"Pushed to {remote_name}/{branch} successfully"

    def pull_from_remote(
        self,
        client,
        subdomain: str,
        remote_name: str = "origin",
        branch: str = None,
        force_remote: bool = True,
        auto_snapshot: bool = True,
        github_token: str = "",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Pull changes from remote repository.

        When *force_remote* is True (default) the remote version (GitHub)
        is treated as the **source of truth** — the server folder is
        always hard-reset to match ``origin/<branch>`` so that merged
        changes are deployed correctly regardless of local server commits.

        A *github_token* can be supplied so that ``git fetch`` works on
        private repositories (the token is used once and never stored).
        """
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository. Initialize first."


        self._ensure_safe_directory(client, path)


        if branch is None:
            branch = self.get_current_branch(client, subdomain)

        if log_callback:
            log_callback(f"Pulling from {remote_name}/{branch}...")

        if force_remote and auto_snapshot:
            snap_ok, snap_msg, snap_meta = self.create_deployment_snapshot(
                client,
                subdomain,
                operation="pull",
                reason=f"Auto snapshot before force pull from {remote_name}/{branch}",
                log_callback=log_callback,
            )
            if log_callback:
                log_callback(snap_msg)
            if not snap_ok:
                return False, "Pull blocked: unable to create safety snapshot before reset."
            if log_callback and snap_meta.get("snapshot_id"):
                log_callback(f"Snapshot ID: {snap_meta['snapshot_id']}")


        url_cmd = f"cd '{path}' && git remote get-url {remote_name} 2>/dev/null"
        _, stdout, _ = client.exec_command(url_cmd)
        original_url = stdout.read().decode().strip()
        clean_url = self._clean_remote_url(original_url)

        if github_token:
            auth_url = self._build_push_url(clean_url, github_token)


            set_cmd = f"cd '{path}' && git remote set-url {remote_name} '{auth_url}' 2>&1"
            _, stdout, _ = client.exec_command(set_cmd)
            stdout.read()

            if log_callback:
                log_callback("Using token authentication for fetch...")
        else:
            if log_callback:
                log_callback("No GitHub token provided — fetching without auth.")


        if log_callback:
            if github_token:
                ls_url = self._build_push_url(clean_url, github_token)
            else:
                ls_url = clean_url
            ls_cmd = (
                f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
                f"git ls-remote '{ls_url}' refs/heads/{branch} 2>&1"
            )
            _, stdout, _ = client.exec_command(ls_cmd)
            ls_out = stdout.read().decode().strip()
            if ls_out and 'fatal' not in ls_out.lower():
                remote_sha = ls_out.split()[0][:10] if ls_out.split() else "?"
                log_callback(f"GitHub latest on {branch}: {remote_sha}")
            else:
                log_callback(f"Could not query GitHub: {ls_out}")


        if log_callback:
            head_cmd = f"cd '{path}' && git rev-parse --short HEAD 2>/dev/null"
            _, stdout, _ = client.exec_command(head_cmd)
            local_sha = stdout.read().decode().strip()
            log_callback(f"Server HEAD before pull: {local_sha}")


        fetch_cmd = (
            f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
            f"git fetch {remote_name} {branch} 2>&1"
        )
        _, stdout, _ = client.exec_command(fetch_cmd)
        fetch_out = stdout.read().decode().strip()


        if github_token:
            restore_cmd = f"cd '{path}' && git remote set-url {remote_name} '{clean_url}' 2>&1"
            _, stdout_r, _ = client.exec_command(restore_cmd)
            stdout_r.read()

        if log_callback and fetch_out:
            for line in fetch_out.split('\n'):
                if line.strip():
                    log_callback(line)


        cleanup_cmd = (
            f"cd '{path}' && git branch -D '{remote_name}/{branch}' 2>/dev/null"
        )
        _, stdout, _ = client.exec_command(cleanup_cmd)
        stdout.read()


        current = self.get_current_branch(client, subdomain)
        if current != branch:
            if log_callback:
                log_callback(f"Switching from '{current}' to '{branch}'...")

            checkout_cmd = (
                f"cd '{path}' && "
                f"git checkout {branch} 2>/dev/null || "
                f"git checkout -b {branch} {remote_name}/{branch} 2>&1"
            )
            _, stdout, _ = client.exec_command(checkout_cmd)
            co_out = stdout.read().decode().strip()
            if log_callback and co_out:
                for line in co_out.split('\n'):
                    if line.strip():
                        log_callback(line)
            if "error:" in co_out.lower() or "fatal:" in co_out.lower():
                return False, f"Failed to switch to branch '{branch}': {co_out}"


        diverge_cmd = (
            f"cd '{path}' && git rev-list --left-right --count "
            f"{remote_name}/{branch}...HEAD 2>/dev/null"
        )
        _, stdout, _ = client.exec_command(diverge_cmd)
        counts = stdout.read().decode().strip().split()
        behind = int(counts[0]) if len(counts) >= 1 else 0
        ahead  = int(counts[1]) if len(counts) >= 2 else 0

        if log_callback:
            log_callback(
                f"Status: {behind} commit(s) behind, {ahead} commit(s) ahead "
                f"of {remote_name}/{branch}."
            )


        if force_remote:
            if log_callback:
                log_callback(
                    "Resetting server to match remote (GitHub is source of truth)..."
                )

            reset_cmd = (
                f"cd '{path}' && "
                f"git reset --hard {remote_name}/{branch} 2>&1"
            )
            _, stdout, _ = client.exec_command(reset_cmd)
            reset_out = stdout.read().decode().strip()
            if log_callback and reset_out:
                for line in reset_out.split('\n'):
                    if line.strip():
                        log_callback(line)

            if "fatal:" in reset_out.lower():
                return False, f"Reset failed: {reset_out}"


            clean_cmd = f"cd '{path}' && git clean -fd -e .htaccess 2>&1"
            _, stdout, _ = client.exec_command(clean_cmd)
            clean_out = stdout.read().decode().strip()
            if log_callback and clean_out:
                log_callback(f"Cleaned untracked files: {clean_out}")

            if log_callback:
                log_callback(
                    f"Server folder now matches {remote_name}/{branch}."
                )
            return True, "Server reset to match remote (pull complete)"


        pull_cmd = (
            f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
            f"git -c pull.rebase=false pull {remote_name} {branch} 2>&1"
        )
        _, stdout, _ = client.exec_command(pull_cmd)
        pull_out = stdout.read().decode().strip()
        if log_callback and pull_out:
            for line in pull_out.split('\n'):
                if line.strip():
                    log_callback(line)

        if "fatal:" in pull_out.lower():
            return False, f"Pull failed: {pull_out}"

        return True, "Pulled from remote successfully"

    def sync_repo(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None,
        github_token: str = ""
    ) -> Tuple[bool, str]:
        """
        Sync the server folder with the remote repository (GitHub).
        GitHub is treated as the source of truth:
          1. Fetch + pull (reset if diverged)
          2. Re-commit any local-only files that still exist
          3. Push back to remote
        """
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository. Initialize first."


        has_remote, remote_url = self.get_remote_info(client, subdomain)
        if not has_remote:
            return False, "No remote repository configured"

        if log_callback:
            log_callback(f"Syncing with {remote_url}...")


        success, msg = self.pull_from_remote(
            client, subdomain, log_callback=log_callback,
            force_remote=True, github_token=github_token
        )

        if not success:
            return False, msg

        if log_callback:
            log_callback(msg)


        status_cmd = f"cd '{path}' && git status --porcelain"
        _, stdout, _ = client.exec_command(status_cmd)
        status = stdout.read().decode().strip()

        if status:
            if log_callback:
                log_callback("Local changes detected after pull — committing...")
            success, msg = self.add_and_commit(
                client, subdomain, "Sync: commit local changes after pull",
                log_callback
            )


            if success:
                success, msg = self.push_to_remote(
                    client, subdomain, log_callback=log_callback,
                    github_token=github_token
                )
        else:
            if log_callback:
                log_callback("Server is now in sync with remote — no local changes to push.")

        return True, "Sync complete"

    def compare_with_remote(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str, dict]:
        """Compare local folder with remote repository."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository", {}


        fetch_cmd = f"cd '{path}' && git fetch origin 2>/dev/null"
        client.exec_command(fetch_cmd)


        branch = self.get_current_branch(client, subdomain)
        status_cmd = f"cd '{path}' && git rev-list --left-right --count origin/{branch}...HEAD 2>/dev/null"
        _, stdout, _ = client.exec_command(status_cmd)
        counts = stdout.read().decode().strip().split()

        result = {
            "behind": int(counts[0]) if len(counts) >= 1 else 0,
            "ahead": int(counts[1]) if len(counts) >= 2 else 0,
            "synced": False
        }

        result["synced"] = result["behind"] == 0 and result["ahead"] == 0

        if result["synced"]:
            return True, "Repository is in sync", result

        msg = []
        if result["behind"] > 0:
            msg.append(f"{result['behind']} commit(s) behind")
        if result["ahead"] > 0:
            msg.append(f"{result['ahead']} commit(s) ahead")

        return True, ", ".join(msg), result

    def get_git_activity_log(
        self,
        client,
        subdomain: str,
        limit: int = 50,
    ) -> List[dict]:
        """Fetch recent git activity (commits, merges, pushes) for a subdomain.
        Returns a list of dicts with keys: hash, date, author, action, message."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return []


        fmt = "%h|||%ai|||%an|||%s|||%D|||%P"
        cmd = (
            f"cd '{path}' && git log --all --oneline -n {limit} "
            f"--pretty=format:'{fmt}' 2>/dev/null"
        )
        _, stdout, _ = client.exec_command(cmd)
        raw = stdout.read().decode().strip()

        if not raw:
            return []

        entries = []
        for line in raw.split("\n"):
            line = line.strip().strip("'")
            if not line:
                continue
            parts = line.split("|||")
            if len(parts) < 6:
                continue

            short_hash, date_str, author, subject, refs, parents = parts


            parent_list = parents.strip().split()
            if len(parent_list) > 1:
                action = "merge"
            elif "origin/" in refs or "push" in subject.lower():
                action = "push"
            elif subject.lower().startswith("pull") or "pull" in refs.lower():
                action = "pull"
            else:
                action = "commit"


            date_display = date_str[:16] if len(date_str) >= 16 else date_str

            entries.append({
                "hash": short_hash.strip(),
                "date": date_display.strip(),
                "author": author.strip(),
                "action": action,
                "message": subject.strip(),
            })

        return entries
