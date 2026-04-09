"""
File Manager — download and delete operations.
"""
import os
import threading
from tkinter import filedialog, messagebox

from models.config import COLORS


class DownloadDeleteMixin:
    """Download file to local and delete remote file/directory."""

    def _download_file(self):
        if not self._cur_path:
            return
        fname = os.path.basename(self._cur_path)
        local = filedialog.asksaveasfilename(
            parent=self.win,
            title="Save file as\u2026",
            initialfile=fname,
            defaultextension=os.path.splitext(fname)[1],
        )
        if not local:
            return
        self._set_bar(f"Downloading {self._cur_path} \u2192 {local} ...")

        def _worker(remote=self._cur_path, dest=local):
            try:
                self._sftp.get(remote, dest)
                self.win.after(0, lambda: self._set_bar(
                    f"Downloaded: {dest}"))
                self.win.after(0, lambda: messagebox.showinfo(
                    "Download Complete",
                    f"File saved to:\n{dest}",
                    parent=self.win,
                ))
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Download error: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()


    def _delete_selected(self):
        iid = self.tree.focus()
        if not iid:
            return
        values = self.tree.item(iid, "values")
        if not values:
            return
        path   = values[0]
        kind   = values[1]

        if kind == "dir":
            msg = (f"Delete directory and ALL its contents?\n\n  {path}\n\n"
                   "This cannot be undone.")
        else:
            msg = f"Delete file?\n\n  {path}\n\nThis cannot be undone."

        if not messagebox.askyesno("Confirm Delete", msg, parent=self.win):
            return

        self._set_bar(f"Deleting {path} ...")

        def _worker(p=path, k=kind, node=iid):
            try:
                if k == "dir":
                    self._client.exec_command(f"rm -rf '{p}'")
                else:
                    self._sftp.remove(p)
                self.win.after(0, lambda: self._after_delete(node, p))
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Delete error: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _after_delete(self, node_iid: str, path: str):
        self.tree.delete(node_iid)
        self._set_bar(f"Deleted: {path}")
        if self._cur_path == path:
            self._editor.configure(state="normal")
            self._editor.delete("1.0", "end")
            self._editor.configure(state="disabled")
            self._editor_title.configure(text="No file open", fg=COLORS["text_secondary"])
            self._cur_path = None
            self._dirty    = False
            self._save_btn.configure(state="disabled")
            self._dl_btn.configure(state="disabled")
            self._del_btn.configure(state="disabled")
            self._fmt_btn.configure(state="disabled")
