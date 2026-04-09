"""
File Manager — constants, extension sets, and file-icon helper.
"""
import os

from models.config import COLORS


_ICON_DIR    = "\U0001f4c1"
_ICON_FILE   = "\U0001f4c4"
_ICON_CODE   = "\U0001f4dd"
_ICON_ENV    = "\u2699\ufe0f"
_ICON_IMAGE  = "\U0001f5bc\ufe0f"
_ICON_LOCK   = "\U0001f512"

_CODE_EXTS   = {".php", ".js", ".ts", ".py", ".rb", ".go", ".html", ".htm",
                ".css", ".scss", ".json", ".xml", ".yaml", ".yml", ".sh",
                ".md", ".txt", ".sql", ".vue", ".jsx", ".tsx"}
_IMAGE_EXTS  = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".bmp"}
_LOCK_EXTS   = {".pem", ".key", ".cert", ".crt"}
_ENV_NAMES   = {".env", ".htaccess", "wp-config.php", ".gitignore"}
_BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp",
                ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".woff",
                ".woff2", ".ttf", ".eot", ".otf", ".pem", ".key",

                ".frm", ".ibd", ".myd", ".myi", ".mdb", ".ibdata"}

_SKIP_DIRS   = {".git"}

TEXT_EDITABLE_THRESHOLD = 1 * 1024 * 1024


_PRETTIER_PARSERS = {
    ".js": "babel", ".jsx": "babel", ".mjs": "babel",
    ".ts": "typescript", ".tsx": "typescript",
    ".json": "json", ".json5": "json5",
    ".css": "css", ".scss": "scss", ".less": "less",
    ".html": "html", ".htm": "html",
    ".vue": "vue",
    ".md": "markdown", ".mdx": "mdx",
    ".yaml": "yaml", ".yml": "yaml",
    ".xml": "xml", ".svg": "xml",
    ".graphql": "graphql", ".gql": "graphql",
    ".php": "php",
}


def _file_icon(name: str, is_dir: bool) -> str:
    if is_dir:
        return _ICON_DIR
    base = os.path.basename(name).lower()
    ext  = os.path.splitext(base)[1]
    if base in _ENV_NAMES:
        return _ICON_ENV
    if ext in _LOCK_EXTS:
        return _ICON_LOCK
    if ext in _IMAGE_EXTS:
        return _ICON_IMAGE
    if ext in _CODE_EXTS:
        return _ICON_CODE
    return _ICON_FILE
