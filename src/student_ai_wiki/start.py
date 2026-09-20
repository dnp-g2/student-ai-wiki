"""
start.py - what a student sees at the start of a session.

  student-wiki start [--root DIR] [--compact] [--hook] [--json]

The numbered list of things a student can say prints on the first session in a vault and then
stops, so later sessions stay as short as the deadline briefing alone. `.student-wiki/greeted`
records that it was shown. Typing `help` inside either AI tool runs this command without
--compact, which brings the list back on request.

--hook is the Claude Code SessionStart hook. It reads the cached update answer and opens no
socket, because a hook sits on the critical path of every session start.
"""
import json
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from . import __version__, update
from .scaffold import shell_path, start_commands
from .vault import STATE_DIR, find_root, is_managed, write_bytes_atomic

GREETED = "greeted"
MAX_BRIEF_ROWS = 5

# (what the student types, what it does). An entry with no gloss speaks for itself.
HELP_STEPS = (
    ("ingest ~/Downloads/L1.pdf", "file a lecture, tutorial or past exam and turn it into notes"),
    ("due", "overdue work, the next 14 days, what to start now"),
    ("add deadline COMP9417 assignment 2 due 12 Oct 23:59 worth 20%", ""),
    ("review COMP9417", "get quizzed until you can explain each concept simply"),
    ("exam-prep COMP9417", "practice questions on your weak concepts"),
    ("grades COMP9417", "your standing and the mark you need on the work that is left"),
    ("calendar", "write the reminder feed for your phone"),
    ("lint", "check the wiki for problems"),
)


# ---------- the first-run marker ----------

def greeted_path(root: Path) -> Path:
    return root / STATE_DIR / GREETED


def greeted(root) -> bool:
    return root is not None and greeted_path(root).is_file()


def mark_greeted(root) -> None:
    """Best effort: a vault that cannot be written still gets its greeting, every session."""
    if root is None:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        write_bytes_atomic(greeted_path(root), f"{stamp} student-wiki {__version__}\n".encode("utf-8"))
    except OSError:
        pass


# ---------- the pieces ----------

def help_lines() -> list:
    width = max(len(command) for command, gloss in HELP_STEPS if gloss)
    lines = ["What you can say here, as plain text:"]
    for number, (command, gloss) in enumerate(HELP_STEPS, 1):
        lines.append(f"  {number}. " + (f"{command.ljust(width)}  {gloss}" if gloss else command))
    return lines + ["", "New here? Start with line 1 on any course file you already have.",
                    "Read your notes in Obsidian: open Home.md. Say `help` to see this list again."]


def no_vault_lines() -> list:
    commands = start_commands(Path.home() / "StudyVault")
    lines = ["No vault here yet. Two steps:", "  1. student-wiki init ~/StudyVault",
             f"  2. {commands[0]}"]
    return lines + [f"     or: {command}" for command in commands[1:]]


def brief_lines(root, max_rows=MAX_BRIEF_ROWS, include_empty=True) -> list:
    """The briefing as `student-wiki tracker brief` prints it, or nothing when it cannot run.

    A corrupt tracker page, an unreadable _config.md or a missing timezone database costs the
    briefing and never the rest of the output.
    """
    try:
        from . import tracker
        item = tracker.Tracker(Namespace(root=str(root), today=None))
        data = tracker.brief_data(item, int(item.config["brief_days"]))
        if not data["total_items"] and not include_empty:
            return []
        return tracker.render_brief(item, data, max_rows).splitlines()
    except Exception:
        return []


# ---------- the command ----------

def start_data(root, how: str, compact: bool, hook: bool) -> dict:
    first_run = not greeted(root)
    data = {"status": "ok" if root is not None else "no_vault", "version": __version__,
            "root": str(root) if root is not None else None, "how": how,
            "mode": "hook" if hook else ("compact" if compact else "full"),
            "first_run": first_run, "brief": [], "help": [],
            "update": update.check(allow_network=not hook)}
    if root is None:
        data["help"] = no_vault_lines()
        return data
    data["brief"] = brief_lines(root, include_empty=not compact)
    if first_run or not compact:
        data["help"] = help_lines()
    return data


def render_start(data: dict) -> str:
    blocks = []
    if data["help"]:
        head = f"Student AI Wiki {data['version']}"
        if data["root"]:
            head += f" · vault {shell_path(Path(data['root']))}"
        blocks.append([head])
    for key in ("brief", "help"):
        if data[key]:
            blocks.append(data[key])
    blocks.append(update.notice(data["update"], compact=data["mode"] != "full"))
    return "\n\n".join("\n".join(block) for block in blocks if block)


def cmd_start(args) -> None:
    root, how = find_root(getattr(args, "root", None))
    if root is None or not root.is_dir() or not is_managed(root):
        root, how = None, how if root is None else "not a vault"
    hook = getattr(args, "hook", False)
    data = start_data(root, how, compact=getattr(args, "compact", False) or hook, hook=hook)
    if data["help"]:
        mark_greeted(root)
    if getattr(args, "json", False):
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    text = render_start(data)
    if text:
        print(text)
