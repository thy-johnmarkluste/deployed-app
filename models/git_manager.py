"""
Git Manager — handles Git operations for syncing subdomain folders with
remote repositories.  Executes Git commands via SSH on the remote server.

The class is composed from focused mixins to keep the codebase navigable:
  • git_repo_ops.py   — folder creation, repo init, commits, remotes, clone
  • git_sync_ops.py   — push, pull, sync, compare, activity log
  • git_deploy_ops.py — Vite/WordPress install, directory clean, SFTP upload
"""
import re
from typing import Callable, Optional, Tuple, List

from models.git_repo_ops import GitRepoOpsMixin
from models.git_sync_ops import GitSyncOpsMixin
from models.git_deploy_ops import GitDeployOpsMixin
from models.security import sanitize_path_component
from models.logger import module_logger


logger = module_logger(__name__)


class GitManager(GitRepoOpsMixin, GitSyncOpsMixin, GitDeployOpsMixin):
    """Manages Git operations for subdomain folders on the remote server."""

    def __init__(self, ssh_client_manager):
        self.ssh = ssh_client_manager
        self.base_path = "/var/www"


    def get_subdomain_path(self, subdomain: str) -> str:
        """Get the full path for a subdomain folder.
        Uses /var/www/<full-domain>/public_html as the document root.

        Note: This method does NOT validate input - it's used for internal
        data fetching operations where the subdomain comes from trusted sources
        (loaded from server/Vultr). User input should be validated separately."""

        safe_subdomain = sanitize_path_component(subdomain)
        return f"{self.base_path}/{safe_subdomain}/public_html"


    def check_git_installed(self, client) -> bool:
        """Check if Git is installed on the server."""
        cmd = "which git"
        _, stdout, _ = client.exec_command(cmd)
        return bool(stdout.read().decode().strip())

    def get_current_branch(self, client, subdomain: str) -> str:
        """Detect the current branch name (master, main, etc.).

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)
        cmd = f"cd '{path}' && git rev-parse --abbrev-ref HEAD 2>/dev/null"
        _, stdout, _ = client.exec_command(cmd)
        branch = stdout.read().decode().strip()
        return branch if branch else "main"

    def list_remote_branches(
        self,
        client,
        subdomain: str,
        github_token: str = "",
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[List[str], str]:
        """List all branches on the remote repository.

        Returns (list_of_branch_names, current_branch).
        Uses ``git ls-remote`` so it works even before the first fetch.

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return [], "main"

        has_remote, remote_url = self.get_remote_info(client, subdomain)
        if not has_remote:

            current = self.get_current_branch(client, subdomain)
            return [current], current

        clean_url = self._clean_remote_url(remote_url)
        ls_url = clean_url
        if github_token and clean_url.startswith("https://"):
            ls_url = self._build_push_url(clean_url, github_token)

        cmd = (
            f"cd '{path}' && GIT_TERMINAL_PROMPT=0 "
            f"git ls-remote --heads '{ls_url}' 2>/dev/null"
        )
        _, stdout, _ = client.exec_command(cmd)
        output = stdout.read().decode().strip()

        branches = []
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
                branch_name = parts[1].replace("refs/heads/", "")
                branches.append(branch_name)


        priority = {"main": 0, "master": 1}
        branches.sort(key=lambda b: (priority.get(b, 99), b))

        current = self.get_current_branch(client, subdomain)

        if log_callback:
            log_callback(f"Found {len(branches)} remote branch(es): {', '.join(branches)}")

        return branches, current

    def is_git_repo(self, client, subdomain: str) -> bool:
        """Check if the subdomain folder is already a Git repository.

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)
        cmd = f"[ -d '{path}/.git' ] && echo 'yes' || echo 'no'"
        _, stdout, _ = client.exec_command(cmd)
        return stdout.read().decode().strip() == 'yes'

    def folder_exists(self, client, subdomain: str) -> bool:
        """Check if the subdomain folder exists.

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)
        cmd = f"[ -d '{path}' ] && echo 'yes' || echo 'no'"
        _, stdout, _ = client.exec_command(cmd)
        return stdout.read().decode().strip() == 'yes'

    def get_git_status(
        self,
        client,
        subdomain: str
    ) -> Tuple[bool, str, List[str]]:
        """Get the current Git status of the subdomain folder.

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)

        if not self.is_git_repo(client, subdomain):
            return False, "Not a Git repository", []

        cmd = f"cd '{path}' && git status --porcelain"
        _, stdout, _ = client.exec_command(cmd)
        status = stdout.read().decode().strip()

        changes = status.split('\n') if status else []

        if not changes or changes == ['']:
            return True, "Working tree clean", []

        return True, f"{len(changes)} file(s) changed", changes

    def get_remote_info(
        self,
        client,
        subdomain: str
    ) -> Tuple[bool, str]:
        """Get the remote repository URL.

        Note: Does not validate - used for data loading from server."""
        path = self.get_subdomain_path(subdomain)
        cmd = f"cd '{path}' && git remote get-url origin 2>/dev/null"
        _, stdout, _ = client.exec_command(cmd)
        url = stdout.read().decode().strip()

        return bool(url), url

    def get_folder_structure(
        self,
        client,
        subdomain: str,
        max_depth: int = 2
    ) -> Tuple[bool, str, List[str]]:
        """Get the folder structure of the subdomain directory.

        Note: Does not validate - used for data loading from server."""

        max_depth = max(1, min(int(max_depth), 10))

        path = self.get_subdomain_path(subdomain)

        if not self.folder_exists(client, subdomain):
            return False, "Folder does not exist", []

        cmd = f"find '{path}' -maxdepth {max_depth} -type f -o -type d | head -50"
        _, stdout, _ = client.exec_command(cmd)
        output = stdout.read().decode().strip()

        files = output.split('\n') if output else []

        return True, f"Found {len(files)} items", files


    def _build_push_url(self, remote_url: str, token: str) -> str:
        """Build an authenticated push URL from a clean remote URL + token.
        Format: https://OWNER:TOKEN@github.com/OWNER/repo.git
        Uses repo owner as username, PAT as password — the format GitHub
        documents for classic Personal Access Tokens."""
        if not token or not remote_url:
            return remote_url
        if not remote_url.startswith("https://"):
            return remote_url

        clean = re.sub(r'https://[^@]+@', 'https://', remote_url)

        m = re.match(r'https://github\.com/([^/]+)/', clean)
        owner = m.group(1) if m else "git"
        return clean.replace('https://', f'https://{owner}:{token}@', 1)

    @staticmethod
    def _clean_remote_url(url: str) -> str:
        """Remove any embedded credentials from an HTTPS URL."""
        if url and url.startswith("https://") and '@' in url:
            return re.sub(r'https://[^@]+@', 'https://', url)
        return url
