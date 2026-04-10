"""
Domain Connector — Application entry point.
Initializes the Tkinter root and hands off to the MainController (MVC).
"""
import sys
import types
from pathlib import Path
import tkinter as tk


def _bootstrap_source_paths():
    """Add bundled source directories to sys.path for frozen app fallback imports."""
    base_candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base_candidates.append(Path(meipass))

    exe_dir = Path(sys.executable).resolve().parent
    base_candidates.extend([
        exe_dir,
        exe_dir / "_internal",
        exe_dir.parent / "Resources",
        exe_dir.parent.parent / "Resources",
    ])

    chosen_base = None
    for base in base_candidates:
        if not base.exists():
            continue
        for folder in ("controllers", "models", "views"):
            package_path = base / folder
            if package_path.exists() and str(base) not in sys.path:
                sys.path.insert(0, str(base))
                chosen_base = base

    if chosen_base is None:
        return

    # Pin local top-level packages to avoid collisions with third-party packages.
    for package in ("controllers", "models", "views"):
        package_path = chosen_base / package
        if not package_path.exists():
            continue
        module = types.ModuleType(package)
        module.__path__ = [str(package_path)]
        module.__package__ = package
        sys.modules[package] = module


def main():
    _bootstrap_source_paths()
    from models.logger import setup_logging
    from controllers.main_controller import MainController

    # Initialize logging when application starts
    setup_logging()
    
    root = tk.Tk()
    _app = MainController(root)  # noqa: F841  – prevent GC
    root.mainloop()


if __name__ == "__main__":
    main()
