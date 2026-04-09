"""
Repository Setup Page — token settings dialog.
"""
import tkinter as tk

from models.config import (
    COLORS,
    get_github_token,
    save_github_token,
    clear_github_token,
)


class TokenSettingsMixin:
    """GitHub token settings dialog and status indicator."""

    def _refresh_token_status(self):
        """Update the token status indicator label."""
        token = get_github_token()
        if token:
            masked = token[:4] + "\u2022" * 8 + token[-4:] if len(token) > 8 else "\u2022" * len(token)
            self._token_status_label.config(
                text=f"\u2705  Set ({masked})",
                fg=COLORS["success"],
            )
        else:
            self._token_status_label.config(
                text="\u26a0  Not set \u2014 click \u2699 to configure",
                fg=COLORS["warning"],
            )

    def _open_token_settings(self):
        """Open a dialog to set, edit, or delete the GitHub token."""
        dlg = tk.Toplevel(self.frame.winfo_toplevel())
        dlg.title("GitHub Token Settings")
        dlg.geometry("460x300")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg=COLORS["bg_primary"])
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() - 460) // 2
        y = (dlg.winfo_screenheight() - 300) // 2
        dlg.geometry(f"460x300+{x}+{y}")


        tk.Label(
            dlg, text="\u2699  GitHub Token Settings",
            font=("Segoe UI", 13, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(pady=(16, 4))
        tk.Label(
            dlg,
            text="Personal Access Token for HTTPS push (requires 'repo' scope)",
            font=("Segoe UI", 9),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(pady=(0, 12))


        fields = tk.Frame(dlg, bg=COLORS["bg_primary"])
        fields.pack(fill="x", padx=24)

        tk.Label(
            fields, text="Token", anchor="w",
            font=("Segoe UI", 9, "bold"),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(0, 2))

        token_row = tk.Frame(fields, bg=COLORS["bg_primary"])
        token_row.pack(fill="x")

        token_var = tk.StringVar(value=get_github_token())
        token_entry = tk.Entry(
            token_row, textvariable=token_var, show="\u2022",
            font=("Segoe UI", 11), relief="flat",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        token_entry.pack(side="left", fill="x", expand=True, ipady=6)

        def _toggle():
            if token_entry.cget("show") == "\u2022":
                token_entry.configure(show="")
                toggle_btn.configure(text="Hide")
            else:
                token_entry.configure(show="\u2022")
                toggle_btn.configure(text="Show")

        toggle_btn = tk.Button(
            token_row, text="Show",
            font=("Segoe UI", 8), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_secondary"],
            command=_toggle,
        )
        toggle_btn.pack(side="right", padx=(6, 0), ipady=4, ipadx=6)

        tk.Label(
            fields,
            text="Saved in .env \u2014 never committed to version control",
            anchor="w", font=("Segoe UI", 8),
            bg=COLORS["bg_primary"], fg=COLORS["text_secondary"],
        ).pack(fill="x", pady=(4, 0))


        btn_frame = tk.Frame(dlg, bg=COLORS["bg_primary"])
        btn_frame.pack(fill="x", padx=24, pady=(20, 12))

        def _save():
            val = token_var.get().strip()
            if not val:
                from tkinter import messagebox
                messagebox.showwarning("Empty Token", "Please enter a token or use Delete to remove it.", parent=dlg)
                return
            save_github_token(val)
            self._refresh_token_status()
            dlg.destroy()

        def _delete():
            from tkinter import messagebox
            if messagebox.askyesno("Delete Token", "Remove the saved GitHub token?", parent=dlg):
                clear_github_token()
                self._refresh_token_status()
                dlg.destroy()

        tk.Button(
            btn_frame, text="\U0001f4be  Save Token",
            font=("Segoe UI", 10, "bold"), relief="flat", cursor="hand2",
            bg=COLORS["success"], fg="white",
            activebackground=COLORS["success"],
            command=_save,
        ).pack(side="left", ipadx=12, ipady=6)

        tk.Button(
            btn_frame, text="\U0001f5d1  Delete Token",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["error"], fg="white",
            activebackground=COLORS["error"],
            command=_delete,
        ).pack(side="left", padx=(10, 0), ipadx=12, ipady=6)

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 10), relief="flat", cursor="hand2",
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            command=dlg.destroy,
        ).pack(side="right", ipadx=12, ipady=6)
