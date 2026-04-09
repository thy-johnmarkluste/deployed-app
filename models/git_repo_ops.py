"""
Git Repository Operations Mixin — folder creation, repo init, commits,
remotes, and cloning.
"""
from datetime import datetime
import re
from typing import Callable, Optional, Tuple, List


class GitRepoOpsMixin:
    """Methods for setting up and managing Git repositories."""

    _SNAPSHOT_ROOT = "/var/backups/veryapp/git_snapshots"
    _SNAPSHOT_MANIFEST = "manifest.tsv"
    _SNAPSHOT_MAX_DEFAULT = 10

    def _ensure_safe_directory(self, client, path: str) -> None:
        """Mark directory as safe to avoid 'dubious ownership' errors.

        This is needed when the repo is owned by www-data but
        Git commands run as root via SSH.
        """
        cmd = f"git config --global --add safe.directory '{path}' 2>/dev/null || true"
        _, stdout, _ = client.exec_command(cmd)
        stdout.read()

    def create_subdomain_folder(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Create the subdomain folder if it doesn't exist."""
        path = self.get_subdomain_path(subdomain)

        if self.folder_exists(client, subdomain):
            return True, f"Folder already exists: {path}"

        cmd = f"mkdir -p '{path}'"
        _, stdout, stderr = client.exec_command(cmd)
        error = stderr.read().decode().strip()

        if error:
            return False, f"Failed to create folder: {error}"

        if log_callback:
            log_callback(f"Created folder: {path}")

        return True, f"Created folder: {path}"

    def init_git_repo(
        self,
        client,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Initialize a Git repository in the subdomain folder."""
        path = self.get_subdomain_path(subdomain)


        if not self.folder_exists(client, subdomain):
            success, msg = self.create_subdomain_folder(client, subdomain, log_callback)
            if not success:
                return False, msg


        if self.is_git_repo(client, subdomain):
            return True, f"Git repository already initialized in {path}"


        cmd = f"cd '{path}' && git init"
        _, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if log_callback and output:
            log_callback(output)


        if "fatal:" in error.lower():
            return False, f"Failed to initialize Git: {error}"


        rename_cmd = f"cd '{path}' && git branch -M main"
        _, stdout, stderr = client.exec_command(rename_cmd)
        stdout.read(); stderr.read()
        if log_callback:
            log_callback("Branch set to 'main'")

        return True, f"Initialized Git repository in {path}"

    def add_and_commit(
        self,
        client,
        subdomain: str,
        commit_message: str = "Initial commit",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Add all files and create a commit."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository. Initialize first."


        self._ensure_safe_directory(client, path)


        config_cmd = (
            f"cd '{path}' && "
            f"git config user.email 'server@localhost' && "
            f"git config user.name 'Server'"
        )
        _, cfg_out, cfg_err = client.exec_command(config_cmd)
        cfg_out.read()
        cfg_err.read()

        if log_callback:
            log_callback("Git user configured.")


        ls_cmd = f"find '{path}' -maxdepth 2 -not -path '*/.git/*' -type f | head -20"
        _, stdout, _ = client.exec_command(ls_cmd)
        files_on_server = stdout.read().decode().strip()
        if log_callback:
            if files_on_server:
                log_callback(f"Files on server (sample):")
                for f in files_on_server.split('\n')[:10]:
                    log_callback(f"  {f}")
            else:
                log_callback("WARNING: No files found on server in target directory!")


        add_cmd = f"cd '{path}' && git add -A"
        _, stdout, stderr = client.exec_command(add_cmd)
        stdout.read()
        add_error = stderr.read().decode().strip()

        if add_error and log_callback:
            log_callback(f"git add output: {add_error}")

        if log_callback:
            log_callback("Added files to staging area")


        status_cmd = f"cd '{path}' && git status --porcelain"
        _, stdout, _ = client.exec_command(status_cmd)
        status = stdout.read().decode().strip()

        if log_callback:
            if status:
                status_lines = status.split('\n')
                log_callback(f"Changes to commit: {len(status_lines)} file(s)")
                for line in status_lines[:10]:
                    log_callback(f"  {line}")
                if len(status_lines) > 10:
                    log_callback(f"  ... and {len(status_lines) - 10} more")
            else:
                log_callback("No changes detected by git status")

        if not status:
            return True, "No changes to commit"


        safe_msg = commit_message.replace("'", "'\\''")
        commit_cmd = f"cd '{path}' && git commit -m '{safe_msg}'"
        _, stdout, stderr = client.exec_command(commit_cmd)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if log_callback and output:
            for line in output.split('\n'):
                log_callback(line)

        if "fatal:" in error.lower():
            if log_callback:
                log_callback(f"Commit error: {error}")
            return False, f"Failed to commit: {error}"

        return True, "Changes committed successfully"

    def add_remote(
        self,
        client,
        subdomain: str,
        repo_url: str,
        remote_name: str = "origin",
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Add a remote repository."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository. Initialize first."


        self._ensure_safe_directory(client, path)


        check_cmd = f"cd '{path}' && git remote get-url {remote_name} 2>/dev/null"
        _, stdout, _ = client.exec_command(check_cmd)
        existing = stdout.read().decode().strip()

        if existing:

            cmd = f"cd '{path}' && git remote set-url {remote_name} '{repo_url}'"
            _, stdout, stderr = client.exec_command(cmd)
            error = stderr.read().decode().strip()

            if "fatal:" in error.lower():
                return False, f"Failed to update remote: {error}"

            if log_callback:
                log_callback(f"Updated remote '{remote_name}' to {repo_url}")

            return True, f"Updated remote '{remote_name}'"
        else:

            cmd = f"cd '{path}' && git remote add {remote_name} '{repo_url}'"
            _, stdout, stderr = client.exec_command(cmd)
            error = stderr.read().decode().strip()

            if "fatal:" in error.lower():
                return False, f"Failed to add remote: {error}"

            if log_callback:
                log_callback(f"Added remote '{remote_name}': {repo_url}")

            return True, f"Added remote '{remote_name}'"

    def clone_repo(
        self,
        client,
        repo_url: str,
        subdomain: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """Clone a repository into the subdomain folder."""
        path = self.get_subdomain_path(subdomain)


        if self.folder_exists(client, subdomain):
            rm_cmd = f"rm -rf '{path}'"
            client.exec_command(rm_cmd)
            if log_callback:
                log_callback(f"Removed existing folder: {path}")


        cmd = f"git clone '{repo_url}' '{path}'"

        if log_callback:
            log_callback(f"Cloning {repo_url} into {path}...")

        _, stdout, stderr = client.exec_command(cmd, get_pty=True)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        if log_callback and output:
            for line in output.split('\n'):
                log_callback(line)

        if "fatal:" in error.lower():
            return False, f"Clone failed: {error}"

        return True, f"Cloned repository to {path}"

    def _get_snapshot_dir(self, subdomain: str) -> str:
        """Get server-side snapshot directory for a subdomain."""

        path = self.get_subdomain_path(subdomain)
        subdomain_dir = path.replace(self.base_path + "/", "").replace("/public_html", "")
        return f"{self._SNAPSHOT_ROOT}/{subdomain_dir}"

    def create_deployment_snapshot(
        self,
        client,
        subdomain: str,
        operation: str = "manual",
        reason: str = "",
        max_snapshots: int = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, dict]:
        """Create a compressed snapshot of the deployment folder before risky operations.

        Snapshot excludes .git so repository metadata remains managed by Git itself.
        """
        path = self.get_subdomain_path(subdomain)
        if not self.folder_exists(client, subdomain):
            return False, f"Folder does not exist: {path}", {}

        max_keep = max_snapshots if isinstance(max_snapshots, int) and max_snapshots > 0 else self._SNAPSHOT_MAX_DEFAULT
        snapshot_dir = self._get_snapshot_dir(subdomain)
        manifest_path = f"{snapshot_dir}/{self._SNAPSHOT_MANIFEST}"
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        op_label = re.sub(r"[^a-zA-Z0-9_-]+", "-", (operation or "manual").strip().lower())
        snapshot_id = f"{ts}_{op_label}".strip("_")
        archive_path = f"{snapshot_dir}/{snapshot_id}.tar.gz"


        branch = "unknown"
        head = "unknown"
        if self.is_git_repo(client, subdomain):
            cmd = f"cd '{path}' && git rev-parse --abbrev-ref HEAD 2>/dev/null"
            _, stdout, _ = client.exec_command(cmd)
            branch = stdout.read().decode().strip() or "unknown"

            cmd = f"cd '{path}' && git rev-parse --short HEAD 2>/dev/null"
            _, stdout, _ = client.exec_command(cmd)
            head = stdout.read().decode().strip() or "unknown"

        mkdir_cmd = f"mkdir -p '{snapshot_dir}'"
        _, stdout, stderr = client.exec_command(mkdir_cmd)
        stdout.read()
        mkdir_err = stderr.read().decode().strip()
        if mkdir_err and "fatal" in mkdir_err.lower():
            return False, f"Failed to prepare snapshot directory: {mkdir_err}", {}

        if log_callback:
            log_callback(f"Creating deployment snapshot: {snapshot_id}")

        snap_cmd = (
            f"cd '{path}' && "
            f"tar --exclude='.git' -czf '{archive_path}' . 2>&1"
        )
        _, stdout, _ = client.exec_command(snap_cmd)
        snap_out = stdout.read().decode().strip()
        if snap_out and ("error" in snap_out.lower() or "cannot" in snap_out.lower()):
            return False, f"Snapshot failed: {snap_out}", {}

        size_cmd = f"du -h '{archive_path}' 2>/dev/null | awk '{{print $1}}'"
        _, stdout, _ = client.exec_command(size_cmd)
        archive_size = stdout.read().decode().strip() or "unknown"

        safe_reason = (reason or "").replace("\t", " ").replace("\n", " ").strip()
        fields = [snapshot_id, ts, op_label or "manual", branch, head, archive_path, archive_size, safe_reason]
        line = "\t".join(fields).replace("'", "'\\''")
        append_cmd = f"printf '%s\n' '{line}' >> '{manifest_path}'"
        _, stdout, stderr = client.exec_command(append_cmd)
        stdout.read()
        stderr.read()


        prune_cmd = (
            f"ls -1t '{snapshot_dir}'/*.tar.gz 2>/dev/null | "
            f"tail -n +{max_keep + 1} | xargs -r rm -f"
        )
        _, stdout, _ = client.exec_command(prune_cmd)
        stdout.read()

        meta = {
            "snapshot_id": snapshot_id,
            "archive_path": archive_path,
            "archive_size": archive_size,
            "branch": branch,
            "head": head,
            "created_at": ts,
            "operation": op_label,
        }
        return True, f"Snapshot created: {snapshot_id} ({archive_size})", meta

    def list_deployment_snapshots(
        self,
        client,
        subdomain: str,
        limit: int = 20,
    ) -> List[dict]:
        """List recent deployment snapshots from manifest storage."""
        snapshot_dir = self._get_snapshot_dir(subdomain)
        manifest_path = f"{snapshot_dir}/{self._SNAPSHOT_MANIFEST}"
        safe_limit = max(1, min(int(limit), 100))
        cmd = f"test -f '{manifest_path}' && tail -n {safe_limit} '{manifest_path}' || true"
        _, stdout, _ = client.exec_command(cmd)
        raw = stdout.read().decode().strip()
        if not raw:
            return []

        rows = []
        for line in raw.splitlines():
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            rows.append(
                {
                    "snapshot_id": parts[0],
                    "created_at": parts[1],
                    "operation": parts[2],
                    "branch": parts[3],
                    "head": parts[4],
                    "archive_path": parts[5],
                    "archive_size": parts[6],
                    "reason": parts[7] if len(parts) > 7 else "",
                }
            )
        return rows

    def rollback_to_snapshot(
        self,
        client,
        subdomain: str,
        snapshot_id: str = "",
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, str, dict]:
        """Restore deployment files from a previously captured snapshot.

        If snapshot_id is empty, the latest snapshot is restored.
        """
        path = self.get_subdomain_path(subdomain)
        snapshot_dir = self._get_snapshot_dir(subdomain)

        target_id = (snapshot_id or "").strip()
        if target_id and not re.match(r"^[a-zA-Z0-9_.-]+$", target_id):
            return False, "Invalid snapshot id format.", {}

        if not target_id:
            snapshots = self.list_deployment_snapshots(client, subdomain, limit=1)
            if not snapshots:
                return False, "No deployment snapshots found.", {}
            target_id = snapshots[-1]["snapshot_id"]

        archive_path = f"{snapshot_dir}/{target_id}.tar.gz"
        verify_cmd = f"test -f '{archive_path}' && echo YES || echo NO"
        _, stdout, _ = client.exec_command(verify_cmd)
        if stdout.read().decode().strip() != "YES":
            return False, f"Snapshot archive not found: {target_id}", {}


        self.create_deployment_snapshot(
            client,
            subdomain,
            operation="pre-rollback",
            reason=f"Automatic backup before rollback to {target_id}",
            log_callback=log_callback,
        )

        if log_callback:
            log_callback(f"Restoring snapshot: {target_id}")

        restore_cmd = (
            f"cd '{path}' && "
            f"find . -mindepth 1 -maxdepth 1 -not -name '.git' -exec rm -rf {{}} + && "
            f"tar -xzf '{archive_path}' -C '{path}' 2>&1"
        )
        _, stdout, _ = client.exec_command(restore_cmd)
        restore_out = stdout.read().decode().strip()
        if restore_out and ("error" in restore_out.lower() or "cannot" in restore_out.lower() or "failed" in restore_out.lower()):
            return False, f"Rollback failed: {restore_out}", {}

        meta = {
            "snapshot_id": target_id,
            "archive_path": archive_path,
            "restored_to": path,
        }
        return True, f"Rollback complete: restored {target_id}", meta
