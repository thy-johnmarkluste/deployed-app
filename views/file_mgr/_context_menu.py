"""
File Manager — right-click context menu, and create file/folder dialogs.
"""
import os
import threading
import tkinter as tk
from tkinter import messagebox

from models.config import COLORS
from views.file_mgr._constants import _ICON_DIR, _PRETTIER_PARSERS, _file_icon


class ContextMenuMixin:
    """Right-click context menu and file/folder creation dialogs."""

    def _on_right_click(self, event):
        iid = self.tree.identify_row(event.y)


        if not iid:
            menu = tk.Menu(self.win, tearoff=0)
            menu.add_command(label="\U0001f4c4  New File",
                             command=lambda: self._create_new_file(self.root_path, ""))
            menu.add_command(label="\U0001f4c1  New Folder",
                             command=lambda: self._create_new_folder(self.root_path, ""))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
            return

        self.tree.selection_set(iid)
        self.tree.focus(iid)
        values = self.tree.item(iid, "values")
        if not values:
            return
        kind = values[1]

        menu = tk.Menu(self.win, tearoff=0)
        if kind == "file":
            menu.add_command(label="\U0001f4dd  Open / Edit",
                             command=lambda: self._open_file(values[0]))

            ext = os.path.splitext(values[0])[1].lower()
            if ext in _PRETTIER_PARSERS:
                menu.add_command(label="\u2728  Format with Prettier",
                                 command=lambda: self._context_format(values[0]))
            menu.add_command(label="\u2b07  Download",
                             command=lambda: (
                                 [setattr(self, "_cur_path", values[0]),
                                  self._download_file()]
                             ))
            menu.add_separator()
            menu.add_command(label="\U0001f5d1  Delete",
                             command=self._delete_selected)
        elif kind == "dir":
            menu.add_command(label="\U0001f50d  Expand",
                             command=lambda: self.tree.item(iid, open=True))
            menu.add_separator()
            menu.add_command(label="\U0001f4c4  New File",
                             command=lambda: self._create_new_file(values[0], iid))
            menu.add_command(label="\U0001f4c1  New Folder",
                             command=lambda: self._create_new_folder(values[0], iid))
            menu.add_separator()
            menu.add_command(label="\U0001f5d1  Delete Folder",
                             command=self._delete_selected)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _create_new_file(self, parent_path: str, parent_iid: str):
        """Prompt for filename and create an empty file in the selected folder."""

        dialog = tk.Toplevel(self.win)
        dialog.title("New File")
        dialog.geometry("350x120")
        dialog.configure(bg=COLORS["bg_primary"])
        dialog.transient(self.win)
        dialog.grab_set()


        dialog.update_idletasks()
        x = self.win.winfo_x() + (self.win.winfo_width() - 350) // 2
        y = self.win.winfo_y() + (self.win.winfo_height() - 120) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog, text="Enter filename:",
            font=("Segoe UI", 10),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(pady=(15, 5))

        filename_var = tk.StringVar()
        entry = tk.Entry(
            dialog, textvariable=filename_var,
            font=("Consolas", 10), width=35,
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        entry.pack(pady=5, padx=15)
        entry.focus_set()

        def _do_create():
            fname = filename_var.get().strip()
            if not fname:
                messagebox.showwarning("Invalid", "Filename cannot be empty.", parent=dialog)
                return

            if "/" in fname or "\\" in fname:
                messagebox.showwarning("Invalid", "Filename cannot contain slashes.", parent=dialog)
                return
            full_path = parent_path.rstrip("/") + "/" + fname
            dialog.destroy()
            self._do_create_file(full_path, parent_iid)

        entry.bind("<Return>", lambda e: _do_create())

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Create",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["success"], fg="white",
            cursor="hand2", command=_do_create,
        ).pack(side="left", padx=5, ipadx=12, ipady=3)

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            cursor="hand2", command=dialog.destroy,
        ).pack(side="left", padx=5, ipadx=12, ipady=3)

    def _do_create_file(self, full_path: str, parent_iid: str):
        """Actually create the file on the server."""
        self._set_bar(f"Creating {full_path} ...")

        def _worker(path=full_path, node=parent_iid):
            try:

                with self._sftp.open(path, "w") as fh:
                    fh.write(b"")
                self.win.after(0, lambda: self._after_create_file(path, node))
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Create error: {exc}"))
                self.win.after(0, lambda: messagebox.showerror(
                    "Create Failed", f"Could not create file:\n{exc}", parent=self.win))

        threading.Thread(target=_worker, daemon=True).start()

    def _after_create_file(self, path: str, parent_iid: str):
        """Callback after file created: add to tree and open in editor."""
        fname = os.path.basename(path)
        icon = _file_icon(fname, False)
        self.tree.insert(
            parent_iid if parent_iid else "", "end",
            text=f"  {icon}  {fname}",
            values=[path, "file"],
        )

        if parent_iid:
            self.tree.item(parent_iid, open=True)
        self._set_bar(f"Created: {path}")

        self._open_file(path)

    def _create_new_folder(self, parent_path: str, parent_iid: str):
        """Prompt for folder name and create it in the selected folder."""
        dialog = tk.Toplevel(self.win)
        dialog.title("New Folder")
        dialog.geometry("350x120")
        dialog.configure(bg=COLORS["bg_primary"])
        dialog.transient(self.win)
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.win.winfo_x() + (self.win.winfo_width() - 350) // 2
        y = self.win.winfo_y() + (self.win.winfo_height() - 120) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(
            dialog, text="Enter folder name:",
            font=("Segoe UI", 10),
            bg=COLORS["bg_primary"], fg=COLORS["text_primary"],
        ).pack(pady=(15, 5))

        foldername_var = tk.StringVar()
        entry = tk.Entry(
            dialog, textvariable=foldername_var,
            font=("Consolas", 10), width=35,
            bg=COLORS["bg_secondary"], fg=COLORS["text_primary"],
            insertbackground=COLORS["text_primary"],
        )
        entry.pack(pady=5, padx=15)
        entry.focus_set()

        def _do_create():
            fname = foldername_var.get().strip()
            if not fname:
                messagebox.showwarning("Invalid", "Folder name cannot be empty.", parent=dialog)
                return
            if "/" in fname or "\\" in fname:
                messagebox.showwarning("Invalid", "Folder name cannot contain slashes.", parent=dialog)
                return
            full_path = parent_path.rstrip("/") + "/" + fname
            dialog.destroy()
            self._do_create_folder(full_path, parent_iid)

        entry.bind("<Return>", lambda e: _do_create())

        btn_frame = tk.Frame(dialog, bg=COLORS["bg_primary"])
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Create",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["success"], fg="white",
            cursor="hand2", command=_do_create,
        ).pack(side="left", padx=5, ipadx=12, ipady=3)

        tk.Button(
            btn_frame, text="Cancel",
            font=("Segoe UI", 9), relief="flat",
            bg=COLORS["bg_accent"], fg=COLORS["text_primary"],
            cursor="hand2", command=dialog.destroy,
        ).pack(side="left", padx=5, ipadx=12, ipady=3)

    def _do_create_folder(self, full_path: str, parent_iid: str):
        """Actually create the folder on the server."""
        self._set_bar(f"Creating folder {full_path} ...")

        def _worker(path=full_path, node=parent_iid):
            try:
                self._sftp.mkdir(path)
                self.win.after(0, lambda: self._after_create_folder(path, node))
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Create error: {exc}"))
                self.win.after(0, lambda: messagebox.showerror(
                    "Create Failed", f"Could not create folder:\n{exc}", parent=self.win))

        threading.Thread(target=_worker, daemon=True).start()

    def _after_create_folder(self, path: str, parent_iid: str):
        """Callback after folder created: add to tree."""
        fname = os.path.basename(path)
        new_iid = self.tree.insert(
            parent_iid if parent_iid else "", 0,
            text=f"  {_ICON_DIR}  {fname}",
            values=[path, "dir"],
            open=False,
        )

        self.tree.insert(new_iid, "end", text="__loading__", values=["", "placeholder"])

        if parent_iid:
            self.tree.item(parent_iid, open=True)
        self._set_bar(f"Created folder: {path}")
