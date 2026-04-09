"""Composite mixin — assembles all subdomain-action sub-mixins."""
from controllers.subdomain_actions._tree_handlers import TreeHandlersMixin
from controllers.subdomain_actions._delete import DeleteSubdomainMixin
from controllers.subdomain_actions._action_menu import ActionMenuMixin
from controllers.subdomain_actions._upload_dialog import UploadDialogMixin
from controllers.subdomain_actions._upload_worker import UploadWorkerMixin
from controllers.subdomain_actions._connect_dialog import ConnectDialogMixin


class SubdomainActionsMixin(
    TreeHandlersMixin, DeleteSubdomainMixin, ActionMenuMixin,
    UploadDialogMixin, UploadWorkerMixin, ConnectDialogMixin,
):
    """Methods for subdomain tree click handling, delete, action popup,
    and the upload-project dialog."""
    pass
