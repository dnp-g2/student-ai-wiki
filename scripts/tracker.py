#!/usr/bin/env python3
"""
tracker.py - track assessments, deadlines, exams and to-dos for the wiki.

Every item is one page, wiki/tracker/<ID>.md, with flat frontmatter that Dataview can query
and a student can edit in Obsidian. Milestones are checkboxes under "## Milestones" in the
page body. This script owns every date calculation, sort order and score, so an agent
passes values in and reports what comes back.

Usage:
  python3 scripts/tracker.py add --type assignment --course COMP9417 --title "Assignment 2"
        --due 2026-10-12 --time 23:59 --weight 20 [--concepts A,B] [--source PAGE] [--dry-run]
  python3 scripts/tracker.py update ID [--due ...] [--status doing] [--clear FIELD]
  python3 scripts/tracker.py done ID
  python3 scripts/tracker.py mark ID 17 --out-of 20
  python3 scripts/tracker.py list [--course C] [--within DAYS] [--status S] [--type T] [--all]

Every command takes --root DIR (default: the repository containing this script) and
--today YYYY-MM-DD. Each prints one JSON object with a status key.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from file_source import slugify  # noqa: E402

TYPES = ("assignment", "quiz", "lab", "exam", "presentation", "other", "todo")
STATUSES = ("todo", "doing", "done", "graded", "dropped")
OPEN = ("todo", "doing")
EXAM_LIKE = ("exam", "quiz")
LIST_FIELDS = ("tags", "concepts", "sources", "needs_check")
FIELD_ORDER = ("tags", "type", "course", "title", "due", "due_time", "weight", "status", "start_by",
               "mark", "out_of", "hurdle", "duration_min", "concepts", "sources", "needs_check",
               "created_at")
CLEARABLE = tuple(f for f in FIELD_ORDER if f not in ("tags", "type", "title", "status", "created_at"))

# Lead time in days before the due date, by weight (percent of the course grade).
LEAD_BANDS = ((40, 21), (25, 14), (15, 10), (5, 5))
LEAD_SMALL, LEAD_UNKNOWN = 2, 7
# A float places a step at that fraction of the start-by to due window; an int is days from due.
STEPS_SMALL = (("Understand the spec and plan", 0.2), ("First full draft", 0.7), ("Review and submit", -1))
STEPS_LARGE = (("Understand the spec and plan", 0.15), ("Core work halfway", 0.4), ("Full draft", 0.7),
               ("Test and polish", 0.9), ("Submit with buffer", -1))
STEPS_EXAM = (("Review weak concepts (run review)", 0.0), ("Practice set (run exam-prep)", 0.5),
              ("Timed practice and recap", -2))

KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):(?:[ \t]+(.*))?$")
LIST_ITEM_RE = re.compile(r"^\s*-(?:\s+(.*))?$")
BARE_RE = re.compile(r"[^\W\d_][\w ./()+&-]*")
RESERVED = ("null", "true", "false", "yes", "no", "on", "off")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[T ](\d{1,2}:\d{2}))?")
TIME_RE = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)(?::\d{2})?")
MILESTONE_HEADING_RE = re.compile(r"^##\s+Milestones\s*$")
MILESTONE_RE = re.compile(r"^\s*[-*] \[([ xX])\]\s+(.*?)(?:\s*\[due::\s*(\d{4}-\d{2}-\d{2})\s*\])?\s*$")


def fail(message: str) -> None:
    sys.exit(f"Error: {message}")


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))


# --- restricted YAML -------------------------------------------------------------------------

def parse_scalar(text: str):
    text = text.strip()
    if text[:1] == '"':
        match = re.match(r'"((?:[^"\\]|\\.)*)"', text)
        if match:
            return re.sub(r"\\(.)", lambda m: {"n": "\n", "t": "\t"}.get(m.group(1), m.group(1)), match.group(1))
    if text[:1] == "'":
        match = re.match(r"'((?:[^']|'')*)'", text)
        if match:
            return match.group(1).replace("''", "'")
    text = re.sub(r"(^|\s+)#.*$", "", text)
    if text.lower() in ("", "null", "~"):
        return None
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    for convert in (int, float):
        try:
            return convert(text)
        except ValueError:
            pass
    return text


def parse_flow_list(text: str) -> list:
    inner = text[1:text.rfind("]")] if "]" in text else text[1:]
    parts, current, depth, quote = [], "", 0, None
    for char in inner:
        if quote:
            quote = None if char == quote else quote
        elif char in "\"'":
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(current)
            current = ""
            continue
        current += char
    parts.append(current)
    # A bare [[Link]] is a nested list to YAML; here it stays the link text it was meant to be.
    return [p.strip() if p.strip().startswith("[") else parse_scalar(p) for p in parts if p.strip()]


def format_scalar(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(tidy(value))
    text = value.isoformat() if isinstance(value, date) else str(value)
    if isinstance(value, date) or (BARE_RE.fullmatch(text) and text == text.strip() and text.lower() not in RESERVED):
        return text
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def format_entry(key: str, value) -> list:
    if isinstance(value, list):
        return [f"{key}:"] + [f"  - {format_scalar(v)}" for v in value] if value else [f"{key}: []"]
    text = format_scalar(value)
    return [f"{key}: {text}" if text else f"{key}:"]


def tidy(number):
    return int(number) if isinstance(number, float) and number.is_integer() else number


class Page:
    """A markdown page whose frontmatter is patched key by key; everything else stays as found."""

    def __init__(self, path: Path, text: str = None):
        self.path = path
        if text is None:
            text = path.read_bytes().decode("utf-8")
        self.bom = text.startswith("﻿")
        text = text.lstrip("﻿")
        self.nl = "\r\n" if "\r\n" in text else "\n"
        lines = text.split(self.nl)
        self.fences, self.fm, self.body = None, [], lines
        if lines and lines[0].strip() == "---":
            for index in range(1, len(lines)):
                if lines[index].strip() == "---":
                    self.fences = (lines[0], lines[index])
                    self.fm, self.body = lines[1:index], lines[index + 1:]
                    break
        self._parse()

    def _parse(self) -> None:
        self.spans, self.data, self.problems = {}, {}, []
        index = 0
        while index < len(self.fm):
            match = KEY_RE.match(self.fm[index])
            if not match:
                stray = self.fm[index].strip()
                if stray and not stray.startswith("#"):
                    self.problems.append(f"unreadable frontmatter line: {stray}")
                index += 1
                continue
            nxt = index + 1
            while nxt < len(self.fm) and not KEY_RE.match(self.fm[nxt]):
                nxt += 1
            end = nxt
            while end > index + 1 and not self.fm[end - 1].strip():
                end -= 1
            key = match.group(1)
            self.spans[key] = (index, end)
            self.data[key] = self._value(key, (match.group(2) or "").strip(), self.fm[index + 1:end])
            index = nxt

    def _value(self, key: str, inline: str, rest: list):
        rest = [line for line in rest if line.strip() and not line.lstrip().startswith("#")]
        if inline.startswith("#"):
            inline = ""
        if inline[:1] in ("|", ">", "{") or (inline and rest):
            self.problems.append(f"{key}: multi-line and nested values are not supported")
            return None
        if inline.startswith("["):
            return parse_flow_list(inline)
        if inline:
            return parse_scalar(inline)
        items = []
        for line in rest:
            match = LIST_ITEM_RE.match(line)
            if not match:
                self.problems.append(f"{key}: multi-line and nested values are not supported")
                return None
            items.append(parse_scalar(match.group(1) or ""))
        return items if rest else None

    def patch(self, changes: dict) -> None:
        present = sorted((k for k in changes if k in self.spans), key=lambda k: self.spans[k][0], reverse=True)
        for key in present:
            start, end = self.spans[key]
            lines = format_entry(key, changes[key])
            if self.fm[start:end] != lines:
                self.fm[start:end] = lines
        for key in changes:
            if key not in self.spans:
                self.fm.extend(format_entry(key, changes[key]))
        if self.fences is None:
            self.fences = ("---", "---")
        self._parse()

    def text(self) -> str:
        head = [self.fences[0], *self.fm, self.fences[1]] if self.fences else []
        return ("﻿" if self.bom else "") + self.nl.join(head + self.body)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".tracker-", suffix=".tmp")
        with os.fdopen(fd, "wb") as handle:
            handle.write(self.text().encode("utf-8"))
        os.replace(tmp, self.path)

    # Milestones live in the body so a student can tick them in Obsidian.
    def _milestone_lines(self):
        start = next((i for i, line in enumerate(self.body) if MILESTONE_HEADING_RE.match(line)), None)
        if start is None:
            return None, []
        found = []
        for index in range(start + 1, len(self.body)):
            if re.match(r"^#{1,2}\s", self.body[index]):
                break
            if MILESTONE_RE.match(self.body[index]):
                found.append(index)
        return start, found

    def milestones(self) -> list:
        result = []
        for index in self._milestone_lines()[1]:
            ticked, text, due = MILESTONE_RE.match(self.body[index]).groups()
            result.append({"text": text, "due": due, "done": ticked != " "})
        return result

    def replace_open_milestones(self, steps: list) -> None:
        heading, found = self._milestone_lines()
        lines = [f"- [ ] {s['text']} [due:: {s['due']}]" for s in steps]
        if heading is None:
            notes = next((i for i, line in enumerate(self.body) if re.match(r"^##\s+Notes\s*$", line)), len(self.body))
            self.body[notes:notes] = ["## Milestones", *lines, ""]
            return
        kept = [i for i in found if MILESTONE_RE.match(self.body[i]).group(1) != " "]
        for index in reversed([i for i in found if i not in kept]):
            del self.body[index]
        at = heading + 1 + len(kept) if kept else heading + 1
        self.body[at:at] = lines


# --- items -----------------------------------------------------------------------------------

def link_name(value) -> str:
    match = re.search(r"\[\[([^\]|#]+)", str(value))
    return (match.group(1) if match else str(value)).strip()


def read_date(value):
    match = DATE_RE.match(str(value).strip())
    if not match:
        raise ValueError(value)
    return date.fromisoformat(match.group(1)), match.group(2)


def read_time(value) -> str:
    match = TIME_RE.fullmatch(str(value).strip())
    if not match:
        raise ValueError(value)
    return f"{int(match.group(1)):02d}:{match.group(2)}"


def read_number(value):
    if isinstance(value, bool):
        raise ValueError(value)
    number = float(str(value).strip().rstrip("%").strip())
    if number < 0:
        raise ValueError(value)
    return tidy(number)


def build_item(page: Page, root: Path) -> dict:
    data, problems = page.data, list(page.problems)

    def grab(key, convert):
        value = data.get(key)
        if value is None or value == "" or value == []:
            return None
        try:
            return convert(value)
        except (ValueError, TypeError):
            problems.append(f"{key}: cannot read '{value}'")
            return None

    due, due_clock = grab("due", read_date) or (None, None)
    item = {
        "id": page.path.stem,
        "path": page.path.relative_to(root).as_posix(),
        "type": str(data.get("type")),
        "course": str(data["course"]) if data.get("course") is not None else None,
        "title": str(data["title"]) if data.get("title") is not None else page.path.stem,
        "due": due,
        "due_time": grab("due_time", read_time) or (read_time(due_clock) if due_clock else None),
        "weight": grab("weight", read_number),
        "status": str(data.get("status") or "todo"),
        "start_by": (grab("start_by", read_date) or (None,))[0],
        "mark": grab("mark", read_number),
        "out_of": grab("out_of", read_number),
        "hurdle": grab("hurdle", read_number),
        "duration_min": grab("duration_min", read_number),
        "created_at": (grab("created_at", read_date) or (None,))[0],
    }
    for key in ("concepts", "sources", "needs_check"):
        value = data.get(key)
        values = value if isinstance(value, list) else [] if value is None else [value]
        item[key] = [link_name(v) for v in values if v is not None]
    if item["type"] not in TYPES:
        problems.append(f"type: '{item['type']}' is not one of {', '.join(TYPES)}")
    if item["status"] not in STATUSES:
        problems.append(f"status: '{item['status']}' is not one of {', '.join(STATUSES)}")
        item["status"] = "todo"
    item["milestones"] = page.milestones()
    item["problems"] = problems
    return item


def view(item: dict, today: date) -> dict:
    """The item as reported: derived fields added, empty fields dropped."""
    shown = dict(item)
    if item["due"]:
        shown["days_left"] = (item["due"] - today).days
        shown["overdue"] = item["status"] in OPEN and item["due"] < today
    return {k: v for k, v in shown.items() if v is not None and v != []}


class Tracker:
    def __init__(self, args):
        self.root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
        self.folder = self.root / "wiki" / "tracker"
        self.today = date.today()
        if args.today:
            try:
                self.today = date.fromisoformat(args.today)
            except ValueError:
                fail(f"--today '{args.today}' is not a valid YYYY-MM-DD date")

    def path_for(self, item_id: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", item_id):
            fail(f"'{item_id}' is not a tracker item id")
        return self.folder / f"{item_id}.md"

    def load(self):
        """Every readable item, plus (path, reason) for pages that cannot be read at all."""
        items, unreadable = [], []
        for path in sorted(self.folder.glob("*.md")) if self.folder.is_dir() else []:
            if path.name.startswith("_"):
                continue
            try:
                page = Page(path)
            except (OSError, UnicodeDecodeError) as error:
                unreadable.append((path.relative_to(self.root).as_posix(), str(error)))
                continue
            if "type" in page.data:
                items.append(build_item(page, self.root))
        items.sort(key=lambda i: (i["due"] is None, i["due"] or date.max, i["id"]))
        return items, unreadable

    def open_page(self, item_id: str):
        path = self.path_for(item_id)
        return Page(path) if path.exists() else None


def normalise_course(text: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", text.strip()):
        fail(f"course '{text}' must be a course code such as COMP9417")
    return text.strip().upper()


def lead_days(weight) -> int:
    if weight is None:
        return LEAD_UNKNOWN
    return next((days for floor, days in LEAD_BANDS if weight >= floor), LEAD_SMALL)


def start_by_for(due: date, weight, created: date) -> date:
    return min(due, max(due - timedelta(days=lead_days(weight)), created))


def auto_steps(kind: str, weight) -> tuple:
    heavy = weight or 0
    if kind == "exam" or (kind == "quiz" and heavy >= 10):
        return STEPS_EXAM
    if kind in ("todo", "quiz"):
        return ()
    return STEPS_LARGE if heavy >= 25 else STEPS_SMALL if heavy >= 10 else ()


def place_steps(steps, start: date, due: date) -> list:
    window = (due - start).days
    placed = []
    for text, position in steps:
        when = due + timedelta(days=position) if isinstance(position, int) else start + timedelta(days=round(window * position))
        placed.append({"text": text, "due": min(max(when, start), due).isoformat()})
    return placed


def field_changes(args) -> dict:
    """Field flags shared by add and update, validated and converted."""
    changes = {}
    try:
        if args.due:
            changes["due"], clock = read_date(args.due)
            if clock:
                changes["due_time"] = read_time(clock)
        if args.start_by:
            changes["start_by"] = read_date(args.start_by)[0]
    except ValueError as error:
        fail(f"'{error}' is not a valid YYYY-MM-DD date")
    if args.time:
        try:
            changes["due_time"] = read_time(args.time)
        except ValueError:
            fail(f"--time '{args.time}' is not a valid HH:MM time")
    for flag in ("weight", "hurdle", "out_of", "duration_min"):
        if getattr(args, flag) is not None:
            try:
                changes[flag] = read_number(getattr(args, flag))
            except ValueError:
                fail(f"--{flag.replace('_', '-')} '{getattr(args, flag)}' is not a number")
    if args.needs_check is not None:
        changes["needs_check"] = split_names(args.needs_check)
        unknown = [n for n in changes["needs_check"] if n not in FIELD_ORDER]
        if unknown:
            fail(f"--needs-check takes field names; unknown: {', '.join(unknown)}")
    if args.title:
        changes["title"] = args.title.strip()
    return changes


def split_names(text: str) -> list:
    return [name.strip() for name in text.split(",") if name.strip()]


def as_links(names) -> list:
    return [f"[[{name}]]" for name in names]


def missing_concepts(tracker: Tracker, names) -> list:
    return [f"concept page missing: {n}" for n in names
            if not (tracker.root / "wiki" / "concepts" / f"{n}.md").exists()]


# --- commands --------------------------------------------------------------------------------

def cmd_add(tracker: Tracker, args) -> None:
    course = normalise_course(args.course) if args.course else None
    if args.type != "todo" and not course:
        fail("--course is required for every type except todo")
    slug = slugify(args.title)
    item_id = "-".join(filter(None, [course, "todo" if args.type == "todo" else None, slug]))
    path = tracker.path_for(item_id)
    if path.exists():
        emit({"status": "exists", "id": item_id, "item": view(build_item(Page(path), tracker.root), tracker.today)})
        return

    fields = dict.fromkeys(FIELD_ORDER)
    fields.update(tags=["tracker"] + ([course.lower()] if course else []), type=args.type, course=course,
                  status="todo", concepts=[], sources=[], needs_check=[], created_at=tracker.today)
    fields.update(field_changes(args))
    concepts = split_names(args.concepts or "")
    fields["concepts"] = as_links(concepts)
    fields["sources"] = as_links(split_names(args.source or ""))

    warnings = missing_concepts(tracker, concepts)
    steps = []
    if args.type != "todo":
        warnings += [f"{name} missing" for name in ("due", "weight") if fields[name] is None]
        if fields["due"]:
            fields["start_by"] = fields["start_by"] or start_by_for(fields["due"], fields["weight"], tracker.today)
            if args.plan == "auto":
                steps = place_steps(auto_steps(args.type, fields["weight"]), fields["start_by"], fields["due"])

    heading = f"# {course} · {fields['title']}" if course else f"# {fields['title']}"
    frontmatter = [line for key in FIELD_ORDER for line in format_entry(key, fields[key])]
    body = [heading, "", "## Milestones", *[f"- [ ] {s['text']} [due:: {s['due']}]" for s in steps], "", "## Notes", ""]
    page = Page(path, "\n".join(["---", *frontmatter, "---", *body]))
    if not args.dry_run:
        page.save()
    result = {"status": "proposed" if args.dry_run else "added", "id": item_id,
              "path": path.relative_to(tracker.root).as_posix(),
              "item": view(build_item(page, tracker.root), tracker.today), "milestones": steps, "warnings": warnings}
    if fields["start_by"]:
        result["start_by"] = fields["start_by"]
    emit(result)


def apply_changes(tracker: Tracker, args, item_id: str, changes: dict, warnings=None) -> None:
    page = tracker.open_page(item_id)
    if page is None or "type" not in page.data:
        emit({"status": "not_found", "id": item_id})
        return
    current = build_item(page, tracker.root)
    remaining = [n for n in current["needs_check"] if n not in changes]
    if remaining != current["needs_check"] and "needs_check" not in changes:
        changes["needs_check"] = remaining
    page.patch(changes)
    if not args.dry_run:
        page.save()
    emit({"status": "proposed" if args.dry_run else "updated", "id": item_id,
          "item": view(build_item(page, tracker.root), tracker.today), "warnings": warnings or []})


def cmd_update(tracker: Tracker, args) -> None:
    page = tracker.open_page(args.id)
    if page is None or "type" not in page.data:
        emit({"status": "not_found", "id": args.id})
        return
    current = build_item(page, tracker.root)
    changes, warnings = field_changes(args), []
    if args.status:
        changes["status"] = args.status
    if args.type:
        changes["type"] = args.type
    for name in args.clear or []:
        if name not in CLEARABLE:
            fail(f"--clear takes one of: {', '.join(CLEARABLE)}")
        changes[name] = [] if name in LIST_FIELDS else None
    if args.add_concept:
        added = [n for n in split_names(",".join(args.add_concept)) if n not in current["concepts"]]
        changes["concepts"] = as_links(current["concepts"] + added)
        warnings += missing_concepts(tracker, added)
    if args.add_source:
        added = [n for n in split_names(",".join(args.add_source)) if n not in current["sources"]]
        changes["sources"] = as_links(current["sources"] + added)

    kind = changes.get("type", current["type"])
    if ("due" in changes or "weight" in changes) and "start_by" not in changes and kind != "todo":
        due, weight = changes.get("due", current["due"]), changes.get("weight", current["weight"])
        changes["start_by"] = start_by_for(due, weight, current["created_at"] or tracker.today) if due else None
        if any(not m["done"] for m in current["milestones"]):
            warnings.append(f"milestone dates are unchanged; run `plan {args.id}` to respace them")
    apply_changes(tracker, args, args.id, changes, warnings)


def cmd_done(tracker: Tracker, args) -> None:
    apply_changes(tracker, args, args.id, {"status": "done"})


def cmd_mark(tracker: Tracker, args) -> None:
    page = tracker.open_page(args.id)
    try:
        mark = read_number(args.mark)
        stored = build_item(page, tracker.root)["out_of"] if page and "type" in page.data else None
        out_of = read_number(args.out_of) if args.out_of is not None else stored or 100
    except ValueError as error:
        fail(f"'{error}' is not a number")
    warnings = [f"mark {mark} is above out_of {out_of}"] if mark > out_of else []
    apply_changes(tracker, args, args.id, {"mark": mark, "out_of": out_of, "status": "graded"}, warnings)


def cmd_list(tracker: Tracker, args) -> None:
    items, _ = tracker.load()
    course = normalise_course(args.course) if args.course else None
    chosen = []
    for item in items:
        if course and item["course"] != course:
            continue
        if args.type and item["type"] != args.type:
            continue
        if args.status and item["status"] != args.status:
            continue
        if not args.status and not args.all and item["status"] not in OPEN:
            continue
        if args.within is not None and (item["due"] is None or (item["due"] - tracker.today).days > args.within):
            continue
        chosen.append(view(item, tracker.today))
    emit({"status": "ok", "today": tracker.today, "count": len(chosen), "items": chosen})


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", help="wiki root (default: the repository containing this script)")
    common.add_argument("--today", help="treat this YYYY-MM-DD date as today")
    writes = argparse.ArgumentParser(add_help=False)
    writes.add_argument("--dry-run", action="store_true", help="print the proposal and write nothing")
    fields = argparse.ArgumentParser(add_help=False)
    fields.add_argument("--due", help="due date YYYY-MM-DD; for an exam, the day it is sat")
    fields.add_argument("--time", help="due time HH:MM (leave out for an all-day item)")
    fields.add_argument("--weight", help="percent of the course grade")
    fields.add_argument("--hurdle", help="minimum percent required on this item")
    fields.add_argument("--out-of", help="maximum mark")
    fields.add_argument("--duration-min", help="exam length in minutes")
    fields.add_argument("--start-by", help="override the computed start-by date")
    fields.add_argument("--needs-check", help="comma-separated fields the source left uncertain")

    parser = argparse.ArgumentParser(description="Track assessments, deadlines, exams and to-dos.")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", parents=[common, writes, fields], help="create an item")
    add.add_argument("--type", required=True, choices=TYPES)
    add.add_argument("--title", required=True)
    add.add_argument("--course", help="course code; optional for a todo")
    add.add_argument("--concepts", help="comma-separated concept page names")
    add.add_argument("--source", help="comma-separated source page names")
    add.add_argument("--plan", choices=("auto", "none"), default="auto", help="generate milestones (default: auto)")
    add.set_defaults(run=cmd_add)

    update = commands.add_parser("update", parents=[common, writes, fields], help="change fields of an item")
    update.add_argument("id")
    update.add_argument("--title")
    update.add_argument("--type", choices=TYPES)
    update.add_argument("--status", choices=STATUSES)
    update.add_argument("--clear", action="append", metavar="FIELD", help="empty a field; repeatable")
    update.add_argument("--add-concept", action="append", metavar="NAME")
    update.add_argument("--add-source", action="append", metavar="PAGE")
    update.set_defaults(run=cmd_update)

    done = commands.add_parser("done", parents=[common, writes], help="mark an item submitted or sat")
    done.add_argument("id")
    done.set_defaults(run=cmd_done)

    mark = commands.add_parser("mark", parents=[common, writes], help="record a mark; sets status graded")
    mark.add_argument("id")
    mark.add_argument("mark")
    mark.add_argument("--out-of")
    mark.set_defaults(run=cmd_mark)

    listing = commands.add_parser("list", parents=[common], help="list items, soonest first")
    listing.add_argument("--course")
    listing.add_argument("--within", type=int, metavar="DAYS", help="due within this many days, overdue included")
    listing.add_argument("--status", choices=STATUSES)
    listing.add_argument("--type", choices=TYPES)
    listing.add_argument("--all", action="store_true", help="include done, graded and dropped items")
    listing.set_defaults(run=cmd_list)
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    args.run(Tracker(args), args)


if __name__ == "__main__":
    main()
