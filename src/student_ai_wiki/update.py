"""
update.py - tell the student when a newer student-ai-wiki release is on PyPI.

One request a day at most, a short timeout, silence on every failure, and the answer kept in one
small file outside the vault. Session hook mode reads that file and opens no socket, so starting
a session is never delayed by the network.

Environment:
  STUDENT_WIKI_NO_UPDATE_CHECK  any non-empty value turns the check off (README)
  STUDENT_WIKI_UPDATE_CACHE     full path to the cache file (the tests use it)
  STUDENT_WIKI_UPDATE_URL       the URL to read, a file:// URL included (the tests use it)

Every call into the outside world (the environment, the platform, the clock, the fetcher, the
cache path) is a defaulted argument, which is what makes the logic testable with no network.
"""
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from . import __version__
from .vault import write_bytes_atomic

ENV_DISABLE = "STUDENT_WIKI_NO_UPDATE_CHECK"
ENV_CACHE = "STUDENT_WIKI_UPDATE_CACHE"
ENV_URL = "STUDENT_WIKI_UPDATE_URL"
PYPI_URL = "https://pypi.org/pypi/student-ai-wiki/json"
CACHE_DIR_NAME = "student-ai-wiki"
CACHE_FILE = "update-check.json"
CACHE_SCHEMA = 1
MAX_AGE_SECONDS = 24 * 60 * 60
TIMEOUT_SECONDS = 1.5
MAX_BYTES = 1 << 21
# The version string reaches an AI tool's context through the session hook, so only plain numbers
# are accepted: a newline, an escape sequence or prose is dropped here. Numbers-only comparison
# also keeps a release candidate from reading as newer than the release it precedes.
VERSION_RE = re.compile(r"\d+(\.\d+){0,3}")

# One command is one process, so this bounds a machine with an unwritable cache to one request.
_MEMO = {}


def _environ(env):
    return os.environ if env is None else env


def disabled(env=None) -> bool:
    return bool(_environ(env).get(ENV_DISABLE))


def cache_path(env=None, platform=None) -> Path:
    """The one file this tool writes outside a vault."""
    env = _environ(env)
    override = env.get(ENV_CACHE)
    if override:
        return Path(override).expanduser()
    platform = sys.platform if platform is None else platform
    if platform == "win32":
        base = Path(env.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        # The XDG spec ignores a relative XDG_CACHE_HOME.
        xdg = env.get("XDG_CACHE_HOME") or ""
        base = Path(xdg) if os.path.isabs(xdg) else Path.home() / ".cache"
    return base / CACHE_DIR_NAME / CACHE_FILE


def read_cache(path=None):
    """The cached answer, or None when the file is missing, unreadable or of another schema."""
    path = cache_path() if path is None else Path(path)
    try:
        entry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(entry, dict) or entry.get("schema") != CACHE_SCHEMA:
        return None
    if not isinstance(entry.get("checked_at"), (int, float)) or isinstance(entry["checked_at"], bool):
        return None
    return entry


def write_cache(entry, path=None) -> bool:
    """Best effort. A machine that cannot write the cache still gets its notice."""
    path = cache_path() if path is None else Path(path)
    try:
        write_bytes_atomic(path, (json.dumps(entry, sort_keys=True) + "\n").encode("utf-8"))
    except OSError:
        return False
    return True


def fetch_latest(url=None, timeout=TIMEOUT_SECONDS, env=None):
    """The newest release on PyPI, or None. Every failure is silent, by design."""
    url = url or _environ(env).get(ENV_URL) or PYPI_URL
    request = urllib.request.Request(url, headers={
        "User-Agent": f"student-ai-wiki/{__version__}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # A file:// response carries no status.
            if getattr(response, "status", None) not in (200, None):
                return None
            payload = json.loads(response.read(MAX_BYTES).decode("utf-8", "replace"))
        latest = str(payload.get("info", {}).get("version", "")).strip()
    except Exception:
        return None
    return latest if VERSION_RE.fullmatch(latest) else None


def _numbers(value):
    text = "" if value is None else str(value).strip()
    return tuple(int(part) for part in text.split(".")) if VERSION_RE.fullmatch(text) else None


def is_newer(latest, current) -> bool:
    left, right = _numbers(latest), _numbers(current)
    if left is None or right is None:
        return False
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def _status(current, latest, source, checked_at) -> dict:
    return {"current": current, "latest": latest, "available": is_newer(latest, current),
            "source": source, "checked_at": checked_at}


def check(allow_network=True, current=None, now=None, path=None, fetch=None, env=None) -> dict:
    """The answer to "is there a newer release", from the cache or from PyPI.

    Age governs refetching alone: with allow_network False a stale entry is still served, and
    is_newer re-reads it against the installed version, so a student who upgraded stops seeing it.
    """
    current = __version__ if current is None else current
    if disabled(env):
        return _status(current, None, "disabled", None)
    now = time.time() if now is None else now
    path = cache_path(env) if path is None else Path(path)
    key = str(path)
    entry = _MEMO.get(key) or read_cache(path)
    # A timestamp from the future means a clock change, so the entry counts as stale.
    fresh = entry is not None and 0 <= now - entry["checked_at"] <= MAX_AGE_SECONDS
    if entry is not None and (fresh or not allow_network):
        _MEMO[key] = entry
        return _status(current, entry.get("latest"), "cache", entry["checked_at"])
    if not allow_network:
        return _status(current, None, "unavailable", None)
    latest = (fetch or fetch_latest)(env=env)
    entry = {"schema": CACHE_SCHEMA, "tool": "student-ai-wiki",
             "checked_at": int(now), "latest": latest}
    _MEMO[key] = entry
    # A failed request is recorded too, so an offline machine tries once a day and no more.
    write_cache(entry, path)
    return _status(current, latest, "network" if latest else "unavailable", entry["checked_at"])


def notice(status, compact=False) -> list:
    """The lines to print, or an empty list when there is nothing to say."""
    if not status or not status.get("available"):
        return []
    head = f"Update available: student-ai-wiki {status['latest']} (you have {status['current']})."
    if compact:
        return [f"{head} Run `pipx upgrade student-ai-wiki` (with uv: "
                "`uv tool upgrade student-ai-wiki`), then `student-wiki upgrade` inside the vault."]
    return [f"{head} Two steps:",
            "  1. Upgrade the tool:  pipx upgrade student-ai-wiki   (with uv: uv tool upgrade student-ai-wiki)",
            "  2. Refresh the vault: student-wiki upgrade"]
