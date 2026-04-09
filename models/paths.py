"""
Centralized runtime path management for the application.

This module provides a single source of truth for all writable directories,
resolving them to the user's AppData folder on Windows to ensure:
- Packaging-safe paths (works when packaged as .exe)
- Persistence across application restarts
- Proper handling of user-specific data
"""
import os
import sys
import shutil
import subprocess
import webbrowser
from pathlib import Path


def _get_app_name() -> str:
    """Get the application name for the AppData folder."""
    # Always use 'ThyWeb' to ensure consistent config location
    # between source runs and packaged executables
    return "ThyWeb"


def get_resource_path(relative_path: str | Path) -> Path:
    """Resolve a bundled-safe resource path for source and PyInstaller runs."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = Path(__file__).resolve().parent.parent
    return base_path / Path(relative_path)


def get_app_data_dir() -> Path:
    """
    Get the main application data directory in AppData.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
    elif sys.platform == "darwin":
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path.home() / '.local' / 'share'
    
    app_name = _get_app_name()
    return base / app_name


def get_logs_dir() -> Path:
    """
    Get the logs directory.
    """
    logs_dir = get_app_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_reports_dir() -> Path:
    """
    Get the PDF reports directory.
    """
    reports_dir = get_app_data_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    legacy_dir = Path(__file__).parent.parent / "reports"
    if legacy_dir.exists() and not any(reports_dir.glob("*.pdf")):
        for item in legacy_dir.glob("*.pdf"):
            target = reports_dir / item.name
            if not target.exists():
                shutil.copy2(item, target)

    return reports_dir


def get_activity_logs_dir() -> Path:
    """
    Get the activity logs directory.
    """
    activity_dir = get_app_data_dir() / "data" / "activity_logs"
    activity_dir.mkdir(parents=True, exist_ok=True)

    legacy_dir = Path(__file__).parent.parent / "data" / "activity_logs"
    if legacy_dir.exists() and not any(activity_dir.glob("*.json")):
        for item in legacy_dir.glob("*.json"):
            target = activity_dir / item.name
            if not target.exists():
                shutil.copy2(item, target)

    return activity_dir


def get_config_path() -> Path:
    """
    Get the path to the .env configuration file.
    """
    app_config = get_app_data_dir() / ".env"
    if app_config.exists():
        return app_config

    legacy_env = Path(__file__).parent.parent / ".env"
    if legacy_env.exists():
        app_config.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_env, app_config)
        return app_config

    return app_config


def get_log_file() -> Path:
    """
    Get the main application log file path.
    """
    log_file = get_logs_dir() / "app.log"

    legacy_log = Path(__file__).parent.parent / "logs" / "app.log"
    if legacy_log.exists() and not log_file.exists():
        log_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_log, log_file)

    return log_file


# Convenience functions for backward compatibility
# These maintain the old relative path behavior while using centralized paths


def get_legacy_logs_dir() -> Path:
    """
    Get the legacy project-relative logs directory.
    """
    project_root = Path(__file__).parent.parent
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_legacy_reports_dir() -> Path:
    """
    Get the legacy project-relative reports directory.
    """
    project_root = Path(__file__).parent.parent
    reports_dir = project_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir


def get_legacy_activity_logs_dir() -> Path:
    """
    Get the legacy project-relative activity logs directory.
    """
    project_root = Path(__file__).parent.parent
    activity_dir = project_root / "data" / "activity_logs"
    activity_dir.mkdir(parents=True, exist_ok=True)
    return activity_dir


def open_path_cross_platform(path: str | Path) -> bool:
    """Open a file or folder using the platform-default application."""
    target = str(path)
    try:
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True
    except Exception:
        try:
            return webbrowser.open(target)
        except Exception:
            return False