"""Composite Git mixin — combines all focused sub-mixins."""
from controllers.git_ops._validation import GitValidationMixin
from controllers.git_ops._status import GitStatusMixin
from controllers.git_ops._init_connect import GitInitConnectMixin
from controllers.git_ops._commit_push import GitCommitPushMixin
from controllers.git_ops._upload_push import GitUploadPushMixin
from controllers.git_ops._dependencies import DependencyInstallMixin
from controllers.git_ops._branch_status import BranchStatusMixin
from controllers.git_ops._wordpress_setup import WordPressSetupMixin
from controllers.git_ops._vite_setup import ViteSetupMixin


class GitMixin(
    GitValidationMixin, GitStatusMixin, GitInitConnectMixin,
    GitCommitPushMixin, GitUploadPushMixin, DependencyInstallMixin,
    BranchStatusMixin, WordPressSetupMixin, ViteSetupMixin,
):
    """Methods for Git repository management on the server."""
    pass
