"""
File Manager Dialog — composite class assembled from focused mixins.
"""
from views.file_mgr._core_ui import FileManagerCoreMixin
from views.file_mgr._sftp_tree import SFTPTreeMixin
from views.file_mgr._editor import FileEditorMixin
from views.file_mgr._download_delete import DownloadDeleteMixin
from views.file_mgr._prettier import PrettierMixin
from views.file_mgr._context_menu import ContextMenuMixin


class FileManagerDialog(
    ContextMenuMixin,
    PrettierMixin,
    DownloadDeleteMixin,
    FileEditorMixin,
    SFTPTreeMixin,
    FileManagerCoreMixin,
):
    """Modal SFTP file browser + inline editor dialog."""
    pass
