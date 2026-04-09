"""
Repository Setup Page — framework selection and dependency checkboxes.
"""
import tkinter as tk

from models.config import COLORS
from views.repo_setup._helpers import _create_label


class FrameworkDepsMixin:
    """Framework selection change handler and dependency checkbox builder."""

    def _on_framework_changed(self, event=None):
        """Rebuild the dependency checkboxes and framework panels when framework changes."""
        self._deps_skipped = False
        self._db_skipped = False
        self._db_step_done = False
        self._rebuild_dep_checkboxes()
        self._rebuild_wp_setup_panel()
        self._rebuild_vite_db_panel()
        if hasattr(self, "_refresh_setup_step_ui"):
            self._refresh_setup_step_ui()

            if hasattr(self, "_update_next_button_state"):
                self._update_next_button_state()
    def _rebuild_dep_checkboxes(self):
        """Clear and recreate dependency checkboxes for the current framework."""

        for w in self._dep_widgets:
            w.destroy()
        self._dep_widgets.clear()
        self._dep_vars.clear()

        framework = self.framework_var.get()
        deps = self._framework_deps.get(framework, [])

        if not deps:
            return

        if framework == "WordPress (CMS)" and isinstance(deps, dict):
            for section_title, section_deps in (("Themes", deps.get("themes", [])), ("Plugins", deps.get("plugins", []))):
                if not section_deps:
                    continue
                section_lbl = _create_label(self._dep_frame, section_title, 9, True)
                section_lbl.pack(anchor="w", pady=(4, 2))
                self._dep_widgets.append(section_lbl)

                section_grid = tk.Frame(self._dep_frame, bg=COLORS["bg_secondary"])
                section_grid.pack(fill="x", pady=(0, 4))
                section_grid.columnconfigure(0, weight=1)
                section_grid.columnconfigure(1, weight=1)
                self._dep_widgets.append(section_grid)

                for idx, (key, label, tooltip) in enumerate(section_deps):
                    var = tk.BooleanVar(value=False)
                    self._dep_vars[key] = var
                    cb = tk.Checkbutton(
                        section_grid, text=f"{label}  —  {tooltip}",
                        variable=var,
                        font=("Segoe UI", 9),
                        bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                        selectcolor=COLORS["bg_accent"],
                        activebackground=COLORS["bg_secondary"],
                        activeforeground=COLORS["text_primary"],
                        anchor="w",
                    )
                    cb.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=1)
                    self._dep_widgets.append(cb)
            return

        lbl = _create_label(self._dep_frame, "Select dependencies to install:", 9, True)
        lbl.pack(anchor="w", pady=(4, 2))
        self._dep_widgets.append(lbl)


        grid = tk.Frame(self._dep_frame, bg=COLORS["bg_secondary"])
        grid.pack(fill="x")
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)
        self._dep_widgets.append(grid)

        for idx, (key, label, tooltip) in enumerate(deps):
            var = tk.BooleanVar(value=False)
            self._dep_vars[key] = var
            cb = tk.Checkbutton(
                grid, text=f"{label}  \u2014  {tooltip}",
                variable=var,
                font=("Segoe UI", 9),
                bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_accent"],
                activebackground=COLORS["bg_secondary"],
                activeforeground=COLORS["text_primary"],
                anchor="w",
            )
            cb.grid(row=idx // 2, column=idx % 2, sticky="w", padx=(0, 8), pady=1)
            self._dep_widgets.append(cb)
