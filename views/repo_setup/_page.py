"""
Repository Setup Page — composite view assembled from focused mixins.
"""
from views.repo_setup._core import RepoSetupPageViewBase
from views.repo_setup._token_settings import TokenSettingsMixin
from views.repo_setup._framework_deps import FrameworkDepsMixin
from views.repo_setup._wp_panel import WordPressPanelMixin
from views.repo_setup._vite_panel import VitePanelMixin


class RepoSetupPageView(
    TokenSettingsMixin,
    FrameworkDepsMixin,
    WordPressPanelMixin,
    VitePanelMixin,
    RepoSetupPageViewBase,
):
    """Complete Repository Setup page with token settings,
    framework dependency selection, WordPress and Vite panels."""
    pass
