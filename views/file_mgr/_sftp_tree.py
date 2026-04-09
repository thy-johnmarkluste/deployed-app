"""
File Manager — SFTP connection, tree population, and path switching.
"""
import os
import stat
import threading
from tkinter import messagebox

from models.config import COLORS
from views.file_mgr._constants import _SKIP_DIRS, _ICON_DIR, _file_icon


class SFTPTreeMixin:
    """SFTP connection helpers and tree population logic."""

    def _connect_and_load(self):
        """Thread: open SSH/SFTP session and populate the root tree node."""
        try:
            self._client = self.ssh.connect()
            if not self._client:
                self._set_status("Connection failed", COLORS["error"], "white")
                return
            self._sftp = self._client.open_sftp()
            self._connected = True
            self._set_status("Connected", COLORS["success"], "white")
            self.win.after(0, self._populate_root)
        except Exception as exc:
            self._set_status(f"Error: {exc}", COLORS["error"], "white")

    def _set_status(self, text: str, bg=None, fg=None):
        """Thread-safe status chip update."""
        bg  = bg  or COLORS["bg_accent"]
        fg  = fg  or COLORS["text_primary"]
        self.win.after(0, lambda: self._status_lbl.configure(text=text, bg=bg, fg=fg))

    def _set_bar(self, text: str):
        """Update the bottom status bar (call from main thread)."""
        self._status_bar.configure(text=text)


    def _list_dir(self, path: str):
        """Return (dirs_sorted, files_sorted) for a remote path."""
        attrs  = self._sftp.listdir_attr(path)
        dirs   = []
        files  = []
        for a in attrs:
            name = a.filename
            if name.startswith(".") and name in _SKIP_DIRS:
                continue
            if stat.S_ISDIR(a.st_mode):

                if self._filter_pattern:
                    if self._filter_pattern in name:
                        dirs.append(name)
                else:
                    dirs.append(name)
            else:

                if self._filter_pattern:
                    if self._filter_pattern in name:
                        files.append(name)
                else:
                    files.append(name)
        dirs.sort(key=str.lower)
        files.sort(key=str.lower)
        return dirs, files

    def _populate_root(self):
        """Clear tree and populate from root_path."""
        self.tree.delete(*self.tree.get_children())
        self._set_bar(f"Loading {self.root_path} ...")

        def _worker():
            try:
                dirs, files = self._list_dir(self.root_path)
                self.win.after(0, lambda: self._insert_entries(
                    "", self.root_path, dirs, files
                ))
                self.win.after(0, lambda: self._set_bar(f"Loaded: {self.root_path}"))
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Error: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _insert_entries(self, parent_iid, parent_path, dirs, files):
        """Insert directory + file items into the tree."""
        for d in dirs:
            full = parent_path.rstrip("/") + "/" + d
            iid  = self.tree.insert(
                parent_iid, "end",
                text=f"  {_ICON_DIR}  {d}",
                values=[full, "dir"],
                open=False,
            )

            self.tree.insert(iid, "end", text="__loading__", values=["", "placeholder"])

        for f in files:
            full = parent_path.rstrip("/") + "/" + f
            icon = _file_icon(f, False)
            self.tree.insert(
                parent_iid, "end",
                text=f"  {icon}  {f}",
                values=[full, "file"],
            )

    def _on_expand(self, event):
        """Lazy-load a directory when the user expands it."""
        iid = self.tree.focus()
        values = self.tree.item(iid, "values")
        if not values or values[1] != "dir":
            return

        children = self.tree.get_children(iid)
        if len(children) == 1:
            child_vals = self.tree.item(children[0], "values")
            if child_vals and child_vals[1] == "placeholder":

                self.tree.delete(children[0])
                dir_path = values[0]
                self._set_bar(f"Loading {dir_path} ...")

                def _worker(path=dir_path, node=iid):
                    try:
                        dirs, files = self._list_dir(path)
                        self.win.after(0, lambda: self._insert_entries(node, path, dirs, files))
                        self.win.after(0, lambda: self._set_bar(f"Loaded: {path}"))
                    except Exception as exc:
                        self.win.after(0, lambda: self._set_bar(f"Error: {exc}"))

                threading.Thread(target=_worker, daemon=True).start()

    def _refresh_tree(self):
        if not self._connected:
            messagebox.showwarning("Not Connected", "SFTP session not ready.", parent=self.win)
            return
        self._populate_root()

    def _restart_apache(self):
        if not self._connected:
            messagebox.showwarning("Not Connected", "SSH session not ready.", parent=self.win)
            return
        if not messagebox.askyesno(
            "Restart Apache",
            "Restart Apache2 on the server?\n\nThis will briefly interrupt all hosted sites.",
            parent=self.win,
        ):
            return
        try:
            _, stdout, stderr = self._client.exec_command("sudo systemctl restart apache2")
            exit_code = stdout.channel.recv_exit_status()
            err = stderr.read().decode().strip()
            if exit_code == 0:
                messagebox.showinfo("Apache Restarted", "apache2 restarted successfully.", parent=self.win)
            else:
                messagebox.showerror(
                    "Restart Failed",
                    f"apache2 restart failed (exit {exit_code}):\n{err or 'No error output'}",
                    parent=self.win,
                )
        except Exception as exc:
            messagebox.showerror("Error", f"Could not restart apache2:\n{exc}", parent=self.win)

    def _on_path_choice_changed(self, event=None):
        """Handle path dropdown selection change."""
        choice = self._path_choice_var.get()
        path_info = self._path_options.get(choice, (self._subdomain_path, False))
        new_path, use_filter = path_info
        self.root_path = new_path
        self._path_var.set(new_path)


        if use_filter:
            self._filter_pattern = self.domain
        else:
            self._filter_pattern = None

        if self._connected:
            self._refresh_tree()
