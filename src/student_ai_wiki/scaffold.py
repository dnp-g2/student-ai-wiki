"""
scaffold.py - create a vault, keep its tool-owned files current, and check its health.

The package ships two template trees under data/:

  managed/  tool-owned. Copied into the vault by init and refreshed by upgrade: AGENTS.md,
            SCHEMA.md, the skills (to .claude/skills and .agents/skills), the slash commands
            (to .claude/commands) and the session hook inside .claude/settings.json.
  seed/     student-owned. Written once by init when missing, never touched again: wiki/,
            raw/, Home.md, .obsidian/, .gitignore.

A path component named dot_x in the template is written as .x in the vault.
.student-wiki/state.json records the tool version and the hash of every managed file, which
is how upgrade tells an untouched file from one the student edited.
"""
import hashlib
import json
import shlex
import shutil
import sys
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

from . import __version__
from .vault import STATE_DIR, STATE_SCHEMA, find_root, is_managed, load_state, save_state, write_bytes_atomic

SETTINGS_PATH = ".claude/settings.json"
SETTINGS_TEMPLATE = "dot_claude/settings.json"
# The command the current template installs, then every command a past release installed. Matching
# all of them is how upgrade rewrites an old hook in place, so a vault never ends up with two.
HOOK_MARKERS = ("start --hook", "tracker brief --hook")
HOOK_MARKER = HOOK_MARKERS[0]
SKIP_NAMES = ("__pycache__", ".DS_Store")


def fail(message: str) -> None:
    sys.exit(f"Error: {message}")


def emit(result: dict) -> None:
    print(json.dumps(result, indent=2, ensure_ascii=False))


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(data: bytes) -> str:
    # Line endings are normalized so a git autocrlf checkout does not read as a local edit.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def hook_matches(command: str) -> bool:
    return any(marker in command for marker in HOOK_MARKERS)


def version_tuple(text: str) -> tuple:
    parts = []
    for piece in str(text).split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


# ---------- templates ----------

def vault_relpath(template_relpath: str) -> str:
    parts = template_relpath.split("/")
    return "/".join("." + part[4:] if part.startswith("dot_") else part for part in parts)


def _walk(node, prefix=""):
    for child in sorted(node.iterdir(), key=lambda entry: entry.name):
        if child.name in SKIP_NAMES:
            continue
        rel = f"{prefix}{child.name}"
        if child.is_dir():
            yield from _walk(child, rel + "/")
        else:
            yield rel, child.read_bytes()


def _template(kind: str) -> dict:
    return dict(_walk(resources.files("student_ai_wiki") / "data" / kind))


def managed_targets() -> dict:
    """Vault path -> content for every tool-owned file except the merged settings."""
    targets = {}
    for rel, data in _template("managed").items():
        if rel == SETTINGS_TEMPLATE:
            continue
        if rel.startswith("skills/"):
            targets[".claude/" + rel] = data
            targets[".agents/" + rel] = data
        elif rel.startswith("commands/"):
            targets[".claude/" + rel] = data
        else:
            targets[vault_relpath(rel)] = data
    return targets


def seed_targets() -> dict:
    return {vault_relpath(rel): data for rel, data in _template("seed").items()}


def settings_template() -> dict:
    return json.loads(_template("managed")[SETTINGS_TEMPLATE].decode("utf-8"))


# ---------- settings merge ----------

def merge_settings(existing, template: dict, recorded_command=None):
    """Return (new_text, outcome). new_text is None when nothing needs writing.

    Only the tool's SessionStart hook is touched; every other key stays as the student left it.
    A hook the student edited (it differs from the command this tool last wrote) is kept.
    """
    wanted_group = template["hooks"]["SessionStart"][0]
    wanted_hook = wanted_group["hooks"][0]
    if existing is None:
        return json.dumps(template, indent=2) + "\n", "created"
    try:
        settings = json.loads(existing)
        if not isinstance(settings, dict):
            raise ValueError
    except ValueError:
        return None, "unparseable"
    before = json.dumps(settings, sort_keys=True)
    groups = settings.setdefault("hooks", {}).setdefault("SessionStart", [])
    matched = [(group, hook)
               for group in (groups if isinstance(groups, list) else [])
               if isinstance(group, dict)
               for hook in group.get("hooks", []) if isinstance(hook, dict)
               and hook_matches(str(hook.get("command", "")))]
    if matched:
        group, hook = matched[0]
        if recorded_command in (None, str(hook.get("command", ""))):
            hook["command"] = wanted_hook["command"]
            hook["timeout"] = wanted_hook["timeout"]
        # A hook of ours that a past release left behind under a second name, or a copy the
        # student pasted in, would run the same command twice per session.
        for other_group, other_hook in matched[1:]:
            if str(other_hook.get("command", "")) == wanted_hook["command"]:
                other_group["hooks"].remove(other_hook)
        groups[:] = [group for group in groups if group.get("hooks")]
    else:
        if not isinstance(groups, list):
            return None, "unparseable"
        groups.append(wanted_group)
    if json.dumps(settings, sort_keys=True) == before:
        return None, "unchanged"
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n", "updated"


# ---------- sync ----------

class Sync:
    """One init or upgrade run over a vault. With dry_run it only fills the report."""

    def __init__(self, root: Path, state, dry_run: bool, force: bool):
        self.root = root
        self.recorded = dict((state or {}).get("files", {}))
        self.dry_run = dry_run
        self.force = force
        self.stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
        self.files = {}
        self.report = {key: [] for key in (
            "created", "updated", "skipped_modified", "removed", "orphaned_modified",
            "backed_up", "seed_created", "seed_kept")}
        self.report["unchanged"] = 0
        self.settings = "unchanged"

    @property
    def backup_dir(self) -> Path:
        return self.root / STATE_DIR / "backups" / self.stamp

    def backup(self, rel: str) -> None:
        self.report["backed_up"].append(rel)
        if self.dry_run:
            return
        dest = self.backup_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(self.root / rel), str(dest))

    def write(self, rel: str, data: bytes) -> None:
        if not self.dry_run:
            write_bytes_atomic(self.root / rel, data)

    def disk_hash(self, rel: str):
        path = self.root / rel
        return content_hash(path.read_bytes()) if path.is_file() else None

    def managed(self, targets: dict) -> None:
        for rel, data in sorted(targets.items()):
            wanted = content_hash(data)
            recorded = self.recorded.get(rel, {}).get("sha256")
            on_disk = self.disk_hash(rel)
            entry = {"kind": "managed", "sha256": wanted}
            if on_disk is None:
                self.report["created"].append(rel)
                self.write(rel, data)
            elif on_disk == wanted:
                self.report["unchanged"] += 1
            elif recorded and on_disk == recorded:
                self.report["updated"].append(rel)
                self.write(rel, data)
            elif self.force:
                self.backup(rel)
                self.report["updated"].append(rel)
                self.write(rel, data)
            else:
                self.report["skipped_modified"].append(rel)
                entry = self.recorded.get(rel)
            if entry:
                self.files[rel] = entry
        for rel, old in sorted(self.recorded.items()):
            if rel in targets or old.get("kind") != "managed":
                continue
            on_disk = self.disk_hash(rel)
            if on_disk is None:
                continue
            if on_disk == old.get("sha256"):
                self.report["removed"].append(rel)
                if not self.dry_run:
                    (self.root / rel).unlink()
                    self._prune_empty((self.root / rel).parent)
            elif self.force:
                self.backup(rel)
                self.report["removed"].append(rel)
            else:
                self.report["orphaned_modified"].append(rel)
                self.files[rel] = old

    def _prune_empty(self, folder: Path) -> None:
        while folder != self.root and folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()
            folder = folder.parent

    def seeds(self, targets: dict) -> None:
        for rel, data in sorted(targets.items()):
            if (self.root / rel).exists():
                self.report["seed_kept"].append(rel)
            else:
                self.report["seed_created"].append(rel)
                self.write(rel, data)

    def merge_settings(self) -> None:
        path = self.root / SETTINGS_PATH
        existing = path.read_text(encoding="utf-8-sig") if path.is_file() else None
        recorded = self.recorded.get(SETTINGS_PATH, {}).get("hook_command")
        text, self.settings = merge_settings(existing, settings_template(), recorded)
        if text is not None:
            self.write(SETTINGS_PATH, text.encode("utf-8"))
        hook = settings_template()["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.files[SETTINGS_PATH] = {"kind": "merged", "hook_command": hook}

    def changed(self) -> bool:
        keys = ("created", "updated", "removed", "seed_created", "backed_up")
        return any(self.report[key] for key in keys) or self.settings in ("created", "updated")

    def save(self, state) -> None:
        if self.dry_run:
            return
        stamp = now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")
        state = dict(state or {})
        state.setdefault("created_by_version", __version__)
        state.setdefault("created_at", stamp)
        state.update(schema=STATE_SCHEMA, tool="student-ai-wiki", tool_version=__version__,
                     updated_at=stamp, files=self.files)
        save_state(self.root, state)

    def summary(self) -> dict:
        out = {key: value for key, value in self.report.items() if value}
        out["settings"] = self.settings
        if self.report["backed_up"]:
            out["backed_up_to"] = self.backup_dir.relative_to(self.root).as_posix()
        return out


# ---------- human-readable output ----------

# Start lines are printed in this order.
AI_TOOLS = ("codex", "claude")


def shell_path(path: Path) -> str:
    """The path as a student would type it: ~/... under the home folder, quoted when it needs it."""
    home = Path.home().resolve()
    if home in path.parents:
        rel = path.relative_to(home).as_posix()
        if shlex.quote(rel) == rel:
            return "~/" + rel
    return shlex.quote(str(path))


def start_commands(root: Path) -> list:
    """A program cannot change the directory of the shell that ran it, so init prints lines to paste:
    one per installed AI tool, or one per supported tool when none is installed yet."""
    tools = [tool for tool in AI_TOOLS if shutil.which(tool)] or AI_TOOLS
    return [f"cd {shell_path(root)} && {tool}" for tool in tools]


def count(items, noun: str) -> str:
    return f"{len(items)} {noun}{'' if len(items) == 1 else 's'}"


def bullet_list(title: str, items) -> list:
    return [title, *[f"    {item}" for item in items]] if items else []


def render_init(result: dict) -> str:
    dry = result["status"] == "proposed"
    written = result.get("created", []) + result.get("seed_created", [])
    lines = [f"{'Would create' if dry else 'Created'} your vault at {result['root']}  (student-wiki {result['version']})",
             f"  {count(written, 'file')}: the AI rules (AGENTS.md, skills, slash commands), a starter wiki/ and raw/, "
             "Home.md and the Obsidian settings"]
    kept = result.get("seed_kept", []) + result.get("skipped_modified", [])
    lines += bullet_list(f"  Already there and left as they were ({len(kept)}):", kept)
    if dry:
        return "\n".join(lines + ["", "Nothing was written. Run the same command without --dry-run to create it."])
    commands = result["start_commands"]
    lines += ["", "Next:",
              "  1. Open the folder in Obsidian (Open folder as vault), then enable the Dataview community plugin.",
              f"  2. Start your AI tool inside the vault. Paste {'this line' if len(commands) == 1 else 'one of these lines'}:",
              "", *[f"       {command}" for command in commands], ""]
    if not any(shutil.which(tool) for tool in AI_TOOLS):
        lines += ["     Neither codex nor claude is installed yet. Install one first:",
                  "       Codex CLI    https://developers.openai.com/codex/cli",
                  "       Claude Code  https://docs.anthropic.com/claude-code", ""]
    lines += ["  3. Then say:  ingest ~/Downloads/<your first lecture file>"]
    return "\n".join(lines)


def render_upgrade(result: dict) -> str:
    status = result["status"]
    versions = result["to_version"] if result["from_version"] == result["to_version"] \
        else f"{result['from_version']} -> {result['to_version']}"
    if status == "up_to_date":
        return f"Your vault at {result['root']} is up to date (student-wiki {versions})."
    dry = status == "proposed"
    changed = (any(result.get(key) for key in ("created", "updated", "removed"))
               or result.get("settings") in ("created", "updated"))
    verb = "Would upgrade" if dry else ("Upgraded" if changed else "Checked")
    lines = [f"{verb} your vault at {result['root']}  (student-wiki {versions})"]
    for key, verb in (("created", "added"), ("updated", "updated"), ("removed", "removed")):
        lines += bullet_list(f"  {count(result.get(key, []), 'file')} {verb}:", result.get(key, []))
    if result.get("settings") in ("created", "updated"):
        lines.append("  Session hook in .claude/settings.json refreshed; your other settings were kept.")
    if result.get("backed_up_to"):
        lines.append(f"  Your edited versions {'would be' if dry else 'were'} saved under {result['backed_up_to']}/")
    skipped = result.get("skipped_modified", []) + result.get("orphaned_modified", [])
    lines += bullet_list(f"  Left alone because you edited them ({len(skipped)}):", skipped)
    if skipped:
        lines.append("  To install the new versions and keep a backup of yours: student-wiki upgrade --force")
    lines.append("  Your wiki/, raw/, Home.md and .obsidian/ were not touched.")
    if dry:
        lines += ["", "Nothing was written. Run the same command without --dry-run to apply it."]
    return "\n".join(lines)


# ---------- init ----------

def cmd_init(args) -> None:
    root = Path(args.dir).expanduser().resolve()
    if root.exists() and not root.is_dir():
        fail(f"{root} is not a folder")
    if is_managed(root):
        fail(f"{root} is already a vault (written by {load_state(root).get('tool_version')}). "
             "Run: student-wiki upgrade")

    sync = Sync(root, None, dry_run=args.dry_run, force=False)
    sync.managed(managed_targets())
    sync.merge_settings()
    sync.seeds(seed_targets())
    sync.save(None)

    result = {"status": "proposed" if args.dry_run else "created", "root": str(root), "version": __version__}
    result.update(sync.summary())
    result["start_commands"] = start_commands(root)
    result["next_steps"] = [
        f"Open {root} in Obsidian (Open folder as vault) and enable the Dataview community plugin",
        "Start your AI tool inside the vault: " + "   or   ".join(result["start_commands"]),
        "Say: ingest ~/Downloads/<your first lecture file>",
    ]
    if args.json:
        emit(result)
    else:
        print(render_init(result))


# ---------- upgrade ----------

def managed_root(explicit):
    root, how = find_root(explicit)
    if root is None:
        fail("no student wiki found. Run this inside your vault, pass --root DIR, "
             "or create a vault with: student-wiki init <dir>")
    return root, how


def cmd_upgrade(args) -> None:
    root, _ = managed_root(args.root)
    state = load_state(root)
    if state is None:
        fail(f"{root} has no {STATE_DIR}/state.json, so it is not a vault. Create one with: student-wiki init <dir>")
    if state.get("schema", 1) > STATE_SCHEMA:
        fail(f"this vault uses state schema {state.get('schema')}, newer than this tool understands. "
             "Upgrade the tool: pipx upgrade student-ai-wiki")
    written_by = state.get("tool_version", "0")
    if version_tuple(written_by) > version_tuple(__version__) and not args.force:
        fail(f"this vault was written by student-wiki {written_by}, newer than the installed {__version__}. "
             "Upgrade the tool: pipx upgrade student-ai-wiki (or pass --force)")

    sync = Sync(root, state, dry_run=args.dry_run, force=args.force)
    sync.managed(managed_targets())
    sync.merge_settings()

    conflicts = sync.report["skipped_modified"] or sync.report["orphaned_modified"]
    if args.dry_run:
        status = "proposed"
    elif conflicts:
        status = "conflicts"
    elif sync.changed():
        status = "upgraded"
    else:
        status = "up_to_date"
    result = {"status": status, "root": str(root), "from_version": written_by, "to_version": __version__}
    result.update(sync.summary())
    if conflicts:
        result["hint"] = ("The files listed as modified were edited in this vault and were left alone. "
                          "student-wiki upgrade --force backs them up under .student-wiki/backups/ "
                          "and installs the new versions.")
    sync.save(state)
    if args.json:
        emit(result)
    else:
        print(render_upgrade(result))


# ---------- doctor ----------

def cmd_doctor(args) -> None:
    checks = []

    def check(name, ok, detail, problem=True):
        checks.append({"check": name, "ok": bool(ok), "detail": detail,
                       "level": "ok" if ok else ("problem" if problem else "info")})

    check("python", sys.version_info >= (3, 9), f"Python {sys.version.split()[0]} (3.9 or newer required)")
    on_path = shutil.which("student-wiki")
    check("command on PATH", on_path, on_path or
          "student-wiki is missing from PATH, so the session hook and the skills cannot call it. "
          "Run: pipx ensurepath, then open a new terminal")

    root, how = find_root(args.root)
    check("vault", root is not None and root.is_dir(),
          f"{root} (found by {how})" if root else "no vault found; create one with: student-wiki init <dir>")
    if root is not None and root.is_dir():
        state = load_state(root) if is_managed(root) else None
        if state is None:
            check("state file", False, "missing; create a vault with: student-wiki init <dir>")
        else:
            written_by = state.get("tool_version", "0")
            same = version_tuple(written_by) == version_tuple(__version__)
            check("vault version", same, f"vault {written_by}, tool {__version__}" +
                  ("" if same else "; run: student-wiki upgrade"))
            targets = managed_targets()
            missing = [rel for rel in targets if not (root / rel).is_file()]
            modified = [rel for rel, entry in state.get("files", {}).items()
                        if entry.get("kind") == "managed" and (root / rel).is_file()
                        and content_hash((root / rel).read_bytes()) != entry.get("sha256")]
            check("managed files present", not missing,
                  "all present" if not missing else "missing: " + ", ".join(missing) + "; run: student-wiki upgrade")
            check("managed files unmodified", not modified,
                  "none edited" if not modified else "edited here: " + ", ".join(modified), problem=False)
        for folder in ("wiki", "raw"):
            check(f"{folder}/ folder", (root / folder).is_dir(), "present" if (root / folder).is_dir() else "missing")

        settings = root / SETTINGS_PATH
        text = settings.read_text(encoding="utf-8-sig", errors="replace") if settings.is_file() else ""
        hooked = hook_matches(text)
        check("session hook", hooked, "present in .claude/settings.json" if hooked else
              "absent; Claude Code will skip the session briefing. Run: student-wiki upgrade", problem=False)
        if hooked and HOOK_MARKER not in text:
            check("session hook version", False,
                  "your hook still runs the older tracker brief command, so the starter steps and "
                  "update notices are missing from it. Set the command in .claude/settings.json to "
                  "student-wiki start --hook, or run: student-wiki upgrade --force", problem=False)

        plugins = root / ".obsidian" / "community-plugins.json"
        try:
            dataview = "dataview" in json.loads(plugins.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            dataview = False
        check("Dataview plugin listed", dataview, "listed" if dataview else
              "enable it in Obsidian: Settings, Community plugins, Browse, Dataview", problem=False)

        zone = None
        try:
            from .tracker import Page
            zone = Page(root / "wiki" / "tracker" / "_config.md").data.get("timezone")
        except Exception:
            pass
        if zone:
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(str(zone))
                check("timezone data", True, str(zone))
            except Exception:
                check("timezone data", False, f"cannot load {zone}; on Windows run: pip install tzdata")

    gh = shutil.which("gh")
    check("gh CLI", gh, gh or "optional; needed only for: student-wiki tracker ics --publish-gist", problem=False)

    problems = [item for item in checks if item["level"] == "problem"]
    if args.json:
        emit({"status": "problems" if problems else "healthy", "version": __version__, "checks": checks})
    else:
        print(f"student-wiki {__version__}")
        marks = {"ok": "ok  ", "info": "note", "problem": "FAIL"}
        for item in checks:
            print(f"  [{marks[item['level']]}] {item['check']}: {item['detail']}")
        print("Problems found." if problems else "Healthy.")
    sys.exit(1 if problems else 0)
