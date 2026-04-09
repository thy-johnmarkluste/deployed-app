"""
File Manager — Prettier code formatting.
"""
import os
import threading
from tkinter import messagebox

from models.config import COLORS
from views.file_mgr._constants import _PRETTIER_PARSERS


class PrettierMixin:
    """Format files using server-side Prettier via npx."""

    def _format_file(self):
        """Format the currently open file using Prettier on the server.

        Writes the current editor content to the server, runs
        ``npx prettier --write``, then reloads the formatted result.
        """
        if not self._cur_path or not self._connected:
            return

        ext = os.path.splitext(self._cur_path)[1].lower()
        parser = _PRETTIER_PARSERS.get(ext)
        if not parser:
            messagebox.showinfo(
                "Not Supported",
                f"Prettier does not support '{ext}' files.",
                parent=self.win,
            )
            return

        content = self._editor.get("1.0", "end-1c")
        self._fmt_btn.configure(state="disabled", text="Formatting...")
        self._set_bar(f"Formatting {os.path.basename(self._cur_path)} with Prettier...")

        def _worker(path=self._cur_path, data=content):
            try:

                with self._sftp.open(path, "w") as fh:
                    fh.write(data.encode("utf-8"))


                cmd = (
                    f"cd /var/www && "
                    f"npx --yes prettier --write --parser {parser} '{path}' 2>&1"
                )
                _, stdout, stderr = self._client.exec_command(cmd, timeout=30)
                out = stdout.read().decode("utf-8", errors="replace")
                err = stderr.read().decode("utf-8", errors="replace")
                exit_code = stdout.channel.recv_exit_status()

                if exit_code != 0:

                    combined = (out + "\n" + err).strip()
                    self.win.after(0, lambda msg=combined: self._on_format_error(msg))
                    return


                with self._sftp.open(path, "r") as fh:
                    formatted = fh.read().decode("utf-8", errors="replace")

                self.win.after(0, lambda c=formatted: self._on_format_done(c))

            except Exception as exc:
                self.win.after(0, lambda e=str(exc): self._on_format_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_format_done(self, formatted_content: str):
        """Callback: replace editor content with Prettier output."""
        self._editor.configure(state="normal")
        self._editor.delete("1.0", "end")
        self._editor.insert("1.0", formatted_content)
        self._editor.edit_reset()
        self._editor.edit_modified(False)
        self._dirty = False
        name = os.path.basename(self._cur_path)
        self._editor_title.configure(text=name, fg=COLORS["text_primary"])
        self._fmt_btn.configure(state="normal", text="\u2728  Format")
        self._set_bar(f"Formatted: {self._cur_path}")

    def _on_format_error(self, error_msg: str):
        """Callback: formatting failed."""
        self._fmt_btn.configure(state="normal", text="\u2728  Format")
        self._set_bar("Format failed")
        messagebox.showerror(
            "Format Error",
            f"Prettier formatting failed:\n\n{error_msg}\n\n"
            "Make sure Node.js and npx are available on the server.",
            parent=self.win,
        )

    def _context_format(self, path: str):
        """Right-click Format: open the file first if not already open, then format."""
        if self._cur_path != path:

            self._open_file(path)

            self.win.after(500, self._format_file)
        else:
            self._format_file()
