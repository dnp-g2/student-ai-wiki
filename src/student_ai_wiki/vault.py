"""
vault.py - find the student's vault and read or write its state file.

The tool is installed once; a vault is any folder created by `student-wiki init`. Every
command resolves the vault the same way:

  1. --root DIR
  2. the STUDENT_WIKI_ROOT environment variable
  3. the nearest parent of the current directory that holds .student-wiki/state.json
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple

ENV_ROOT = "STUDENT_WIKI_ROOT"
STATE_DIR = ".student-wiki"
STATE_FILE = "state.json"
STATE_SCHEMA = 1
ROOT_HELP = f"vault root (default: {ENV_ROOT}, then the vault containing the current directory)"


def state_path(root: Path) -> Path:
    return root / STATE_DIR / STATE_FILE


def is_managed(root: Path) -> bool:
    return state_path(root).is_file()


def find_root(explicit: Optional[str] = None) -> Tuple[Optional[Path], str]:
    """Return (root, how); root is None when no vault was found."""
    if explicit:
        return Path(explicit).expanduser().resolve(), "--root"
    env = os.environ.get(ENV_ROOT)
    if env:
        return Path(env).expanduser().resolve(), ENV_ROOT
    here = Path.cwd().resolve()
    for folder in (here, *here.parents):
        if is_managed(folder):
            return folder, "state file"
    return None, "not found"


def resolve_root(explicit: Optional[str] = None) -> Path:
    root, how = find_root(explicit)
    if root is None:
        sys.exit(
            f"Error: no student wiki found from {Path.cwd()}. Run this inside your vault, pass --root DIR, "
            f"set {ENV_ROOT}, or create a vault with: student-wiki init <dir>"
        )
    if how == ENV_ROOT and not root.is_dir():
        sys.exit(f"Error: {ENV_ROOT}={root} is not a directory")
    return root


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".sw-", suffix=".tmp")
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.replace(tmp, path)


def load_state(root: Path) -> Optional[dict]:
    path = state_path(root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(root: Path, state: dict) -> None:
    text = json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    write_bytes_atomic(state_path(root), text.encode("utf-8"))
