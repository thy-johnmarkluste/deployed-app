"""
File Manager — file open, editor, and save operations.
"""
import os
import threading
from tkinter import messagebox

from models.config import COLORS
from views.file_mgr._constants import _BINARY_EXTS, _PRETTIER_PARSERS, TEXT_EDITABLE_THRESHOLD


class FileEditorMixin:
    """File open/read, editor modified tracking, and save-back logic."""

    def _on_double_click(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        values = self.tree.item(iid, "values")
        if not values or values[1] != "file":
            return

        if self._dirty and not messagebox.askyesno(
            "Unsaved Changes",
            f"Discard unsaved changes to\n{self._cur_path}?",
            parent=self.win,
        ):
            return
        file_path = values[0]
        self._open_file(file_path)

    def _open_file(self, path: str):
        """Load a remote file into the editor (background thread)."""
        ext = os.path.splitext(path)[1].lower()
        if ext in _BINARY_EXTS:
            messagebox.showinfo(
                "Binary File",
                f"'{os.path.basename(path)}' appears to be a binary file and\n"
                "cannot be displayed in the editor.\n\nUse Download instead.",
                parent=self.win,
            )
            self._dl_btn.configure(state="normal")
            self._cur_path = path
            return

        self._set_bar(f"Opening {path} ...")
        self._editor_title.configure(text=os.path.basename(path),
                                     fg=COLORS["text_primary"])
        self._path_var.set(path)

        def _worker():
            try:

                attr = self._sftp.stat(path)
                size = attr.st_size
                if size > TEXT_EDITABLE_THRESHOLD:
                    self.win.after(0, lambda: messagebox.showwarning(
                        "File Too Large",
                        f"The file is {size // 1024} KB — too large to edit in-browser.\n"
                        "Use Download to get a local copy.",
                        parent=self.win,
                    ))
                    self.win.after(0, lambda: self._dl_btn.configure(state="normal"))
                    self.win.after(0, lambda: (
                        setattr(self, '_cur_path', path)
                    ))
                    return

                with self._sftp.open(path, "r") as fh:
                    content = fh.read().decode("utf-8", errors="replace")

                def _load(c=content):
                    self._editor.configure(state="normal")
                    self._editor.delete("1.0", "end")
                    self._editor.insert("1.0", c)
                    self._editor.edit_reset()
                    self._editor.edit_modified(False)
                    self._dirty    = False
                    self._cur_path = path
                    self._save_btn.configure(state="normal")
                    self._dl_btn.configure(state="normal")
                    self._del_btn.configure(state="normal")

                    ext = os.path.splitext(path)[1].lower()
                    if ext in _PRETTIER_PARSERS:
                        self._fmt_btn.configure(state="normal")
                    else:
                        self._fmt_btn.configure(state="disabled")
                    self._set_bar(f"Opened: {path}  ({size:,} bytes)")

                self.win.after(0, _load)
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Error opening {path}: {exc}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_editor_modified(self, event=None):
        if self._editor.edit_modified():
            if not self._dirty:
                self._dirty = True
                title = self._editor_title.cget("text")
                if not title.startswith("*"):
                    self._editor_title.configure(text="* " + title,
                                                 fg=COLORS["warning"])
            self._editor.edit_modified(False)


    def _save_file(self):
        if not self._cur_path:
            return
        content = self._editor.get("1.0", "end-1c")
        self._save_btn.configure(state="disabled", text="Saving...")
        self._set_bar(f"Saving {self._cur_path} ...")

        def _worker(path=self._cur_path, data=content):
            try:
                with self._sftp.open(path, "w") as fh:
                    fh.write(data.encode("utf-8"))
                self.win.after(0, _done)
            except Exception as exc:
                self.win.after(0, lambda: self._set_bar(f"Save error: {exc}"))
                self.win.after(0, lambda: self._save_btn.configure(
                    state="normal", text="\U0001f4be  Save"))

        def _done():
            self._dirty = False
            name = os.path.basename(self._cur_path)
            self._editor_title.configure(text=name, fg=COLORS["text_primary"])
            self._save_btn.configure(state="normal", text="\U0001f4be  Save")
            self._set_bar(f"Saved: {self._cur_path}")

        threading.Thread(target=_worker, daemon=True).start()
