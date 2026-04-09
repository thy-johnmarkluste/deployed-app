"""
Persistent activity log — one JSON file per subdomain so that
application activity entries survive application restarts.

If a JSON file already exists for a subdomain, new entries are
inserted into it instead of creating a new file.
"""
import json
import os
from datetime import datetime

from models.paths import get_activity_logs_dir


def _ensure_dir():
    """Create the data directory if it doesn't exist."""
    os.makedirs(get_activity_logs_dir(), exist_ok=True)


def _log_path(subdomain: str) -> str:
    """Return the JSON file path for a given subdomain."""
    safe_name = (
        subdomain.strip()
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    return os.path.join(get_activity_logs_dir(), f"{safe_name}.json")


def file_exists(subdomain: str) -> bool:
    """Check whether a log file already exists for this subdomain."""
    return os.path.exists(_log_path(subdomain))


def load_entries(subdomain: str) -> list:
    """Return all saved activity entries for *subdomain* (newest-first)."""
    path = _log_path(subdomain)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_entries(subdomain: str, entries: list):
    """Overwrite the log file for *subdomain* with the given entries."""
    _ensure_dir()
    path = _log_path(subdomain)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def append_entry(subdomain: str, entry: dict):
    """
    Append a single entry to the existing JSON file for *subdomain*.
    If the file already exists for this subdomain, the entry is inserted
    into that same file — no new file is created.
    If no file exists yet, one is created for the first time.
    """
    if not entry.get("date"):
        entry["date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry["subdomain"] = subdomain


    entries = load_entries(subdomain)


    entries.insert(0, entry)


    entries = entries[:200]


    save_entries(subdomain, entries)


def clear_entries(subdomain: str):
    """Wipe the persisted log for *subdomain*."""
    save_entries(subdomain, [])


def get_all_subdomains() -> list:
    """Return a list of all subdomains that have a saved log file."""
    data_dir = get_activity_logs_dir()
    if not os.path.exists(data_dir):
        return []
    return [
        f.replace(".json", "")
        for f in os.listdir(data_dir)
        if f.endswith(".json")
    ]
