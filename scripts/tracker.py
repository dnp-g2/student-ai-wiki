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
  python3 scripts/tracker.py plan ID [--steps "Outline;Build;Submit"] [--start-by DATE]
  python3 scripts/tracker.py focus COURSE
  python3 scripts/tracker.py brief [--days 14] [--max 5] [--course C] [--json] [--hook]
  python3 scripts/tracker.py hot
  python3 scripts/tracker.py grades [--course C] [--target 75] [--what-if ID=85]
  python3 scripts/tracker.py target COURSE 75

Every command takes --root DIR (default: the repository containing this script) and
--today YYYY-MM-DD. Each prints one JSON object with a status key; brief prints text unless
--json is given. Settings come from the frontmatter of wiki/tracker/_config.md.
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

WEAK_CONFIDENCE = ("low", "medium")
STALE_AFTER_DAYS = 20
EXAM_WINDOW_DAYS = 21
MILESTONE_WINDOW_DAYS = 7
HOT_MAX_LINES = 5
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
DEFAULTS = {"timezone": None, "default_target": None, "term_start": None, "term_end": None,
            "alarms": True, "brief_days": 14}

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
        self.bom = text.startswith("\ufeff")
        text = text.lstrip("\ufeff")
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
        return ("\ufeff" if self.bom else "") + self.nl.join(head + self.body)

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


def view(item: dict, tracker) -> dict:
    """The item as reported: derived fields added, empty fields dropped."""
    shown = dict(item)
    if item["due"]:
        shown["days_left"] = (item["due"] - tracker.today).days
        shown["overdue"] = is_overdue(item, tracker.today)
    if item["status"] in OPEN:
        shown["score"] = score(item, tracker)
    return {k: v for k, v in shown.items() if v is not None and v != []}


def is_overdue(item: dict, today: date) -> bool:
    return item["status"] in OPEN and item["due"] is not None and item["due"] < today


def score(item: dict, tracker) -> int:
    """Weight x urgency x progress x exam readiness; higher means work on it sooner."""
    weight = item["weight"]
    size = max(weight, 3) if weight is not None else 5 if item["type"] == "todo" else 10
    if item["due"] is None:
        urgency = 0.5
    elif item["due"] < tracker.today:
        urgency = 4
    else:
        days_left = (item["due"] - tracker.today).days
        urgency = min(max(lead_days(weight) / max(days_left, 0.5), 0.2), 4)
    progress = 0.7 if item["status"] == "doing" else 1.0
    readiness = 1.0
    if item["type"] in EXAM_LIKE:
        weak = sum(1 for name in item["concepts"] if tracker.concept(name)["flagged"])
        readiness = min(1 + 0.1 * weak, 1.5)
    return round(size * urgency * progress * readiness)


class Tracker:
    def __init__(self, args):
        self.root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
        self.folder = self.root / "wiki" / "tracker"
        self.config = dict(DEFAULTS)
        config_path = self.folder / "_config.md"
        if config_path.exists():
            try:
                self.config.update({k: v for k, v in Page(config_path).data.items() if k in DEFAULTS and v is not None})
            except (OSError, UnicodeDecodeError):
                pass
        self.today = self._local_today()
        self._concepts = {}
        if args.today:
            try:
                self.today = date.fromisoformat(args.today)
            except ValueError:
                fail(f"--today '{args.today}' is not a valid YYYY-MM-DD date")

    def _local_today(self) -> date:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(str(self.config["timezone"]))).date()
        except Exception:  # no timezone configured, or no zone database on this machine
            return date.today()

    def setting_date(self, key: str):
        try:
            return read_date(self.config[key])[0]
        except ValueError:
            return None

    def concept(self, name: str) -> dict:
        """Confidence and review age of a concept page, read from its frontmatter only."""
        if name not in self._concepts:
            state = {"name": name, "exists": False, "flagged": False, "label": "missing page"}
            path = self.root / "wiki" / "concepts" / f"{name}.md"
            try:
                data = Page(path).data if path.exists() else None
            except (OSError, UnicodeDecodeError):
                data = None
            if data is not None:
                confidence = str(data.get("confidence") or "").lower()
                try:
                    age = (self.today - read_date(data.get("last_reviewed"))[0]).days
                except ValueError:
                    age = None
                weak, stale = confidence in WEAK_CONFIDENCE, age is not None and age > STALE_AFTER_DAYS
                state.update(exists=True, confidence=confidence or None, days_since_review=age,
                             flagged=weak or stale,
                             label=confidence if weak else f"stale {age}d" if stale else confidence or "unrated")
            self._concepts[name] = state
        return self._concepts[name]

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
        emit({"status": "exists", "id": item_id, "item": view(build_item(Page(path), tracker.root), tracker)})
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
              "item": view(build_item(page, tracker.root), tracker), "milestones": steps, "warnings": warnings}
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
          "item": view(build_item(page, tracker.root), tracker), "warnings": warnings or []})


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
        chosen.append(view(item, tracker))
    emit({"status": "ok", "today": tracker.today, "count": len(chosen), "items": chosen})


def cmd_plan(tracker: Tracker, args) -> None:
    page = tracker.open_page(args.id)
    if page is None or "type" not in page.data:
        emit({"status": "not_found", "id": args.id})
        return
    item = build_item(page, tracker.root)
    if item["due"] is None:
        fail(f"{args.id} has no due date; set one with `update {args.id} --due YYYY-MM-DD` first")
    try:
        start = read_date(args.start_by)[0] if args.start_by else None
    except ValueError:
        fail(f"--start-by '{args.start_by}' is not a valid YYYY-MM-DD date")
    if start:
        page.patch({"start_by": start})
    start = start or item["start_by"] or start_by_for(item["due"], item["weight"], item["created_at"] or tracker.today)
    if args.steps:
        names = [name.strip() for name in args.steps.split(";") if name.strip()]
        steps = [(name, (index + 1) / len(names)) for index, name in enumerate(names[:-1])] + [(names[-1], -1)]
    else:
        steps = auto_steps(item["type"], item["weight"])
    page.replace_open_milestones(place_steps(steps, start, item["due"]))
    if not args.dry_run:
        page.save()
    emit({"status": "proposed" if args.dry_run else "planned", "id": args.id, "start_by": start,
          "milestones": page.milestones()})


def cmd_focus(tracker: Tracker, args) -> None:
    course = normalise_course(args.course)
    items, _ = tracker.load()
    upcoming = [i for i in items if i["course"] == course and i["type"] in EXAM_LIKE
                and i["status"] in OPEN and i["due"] and i["due"] >= tracker.today]
    if not upcoming:
        emit({"status": "none", "course": course})
        return
    concepts = [tracker.concept(name) for name in upcoming[0]["concepts"]]
    concepts.sort(key=lambda c: not c["flagged"])
    emit({"status": "ok", "course": course, "item": view(upcoming[0], tracker), "concepts": concepts})


def overview_path(tracker: Tracker, course: str) -> Path:
    return tracker.root / "wiki" / "courses" / f"{course}-overview.md"


def target_for(tracker: Tracker, course: str, override=None):
    """Target grade: the flag, else the course overview, else default_target in _config.md."""
    candidates = [override]
    path = overview_path(tracker, course)
    try:
        candidates.append(Page(path).data.get("target_grade") if path.exists() else None)
    except (OSError, UnicodeDecodeError):
        pass
    candidates.append(tracker.config["default_target"])
    for value in candidates:
        try:
            if value is not None:
                return read_number(value)
        except ValueError:
            continue
    return None


def course_grades(tracker: Tracker, course: str, items: list, target, what_if: dict) -> dict:
    counted = [i for i in items if i["course"] == course and i["type"] != "todo" and i["status"] != "dropped"]
    for item in counted:
        if item["id"] in what_if:
            item.update(mark=what_if[item["id"]], out_of=100)
    weighted = [i for i in counted if i["weight"] is not None]
    graded = [i for i in weighted if i["mark"] is not None and i["out_of"]]
    graded_weight = sum(i["weight"] for i in graded)
    earned = sum(i["weight"] * i["mark"] / i["out_of"] for i in graded)
    tracked = sum(i["weight"] for i in weighted)
    remaining = 100 - graded_weight

    hurdles = []
    for item in counted:
        if item["hurdle"] is not None:
            has_mark = item["mark"] is not None and item["out_of"]
            state = "pending" if not has_mark else "met" if item["mark"] / item["out_of"] * 100 >= item["hurdle"] else "failed"
            hurdles.append({"id": item["id"], "hurdle": item["hurdle"], "state": state})

    result = {"course": course, "target": target, "graded_weight": graded_weight, "earned": earned,
              "average": earned / graded_weight * 100 if graded_weight else None,
              "tracked_weight": tracked, "untracked_weight": max(0, 100 - tracked), "remaining_weight": remaining,
              "remaining_items": [{"id": i["id"], "weight": i["weight"], "due": i["due"]}
                                  for i in weighted if i not in graded],
              "unweighted": [i["id"] for i in counted if i["weight"] is None],
              "hurdles": hurdles, "at_risk": any(h["state"] == "failed" for h in hurdles)}
    if tracked > 100:
        result["outcome"] = "weights_over_100"
    elif target is None:
        result["outcome"] = "no_target"
    elif remaining <= 0:
        result["outcome"] = "secured" if earned >= target else "missed"
    else:
        required = (target - earned) / remaining * 100
        result["outcome"] = "secured" if required <= 0 else "unreachable" if required > 100 else "on_track"
        if result["outcome"] == "on_track":
            result["required_average"] = required
        if result["outcome"] == "unreachable":
            result["max_possible"] = earned + remaining
    return {k: tidy(round(v, 1)) if isinstance(v, float) else v for k, v in result.items() if v is not None}


def all_grades(tracker: Tracker, items: list, only=None, target=None, what_if=None) -> list:
    courses = sorted({i["course"] for i in items if i["course"] and i["type"] != "todo"})
    return [course_grades(tracker, c, items, target_for(tracker, c, target), what_if or {})
            for c in courses if only in (None, c)]


def cmd_grades(tracker: Tracker, args) -> None:
    items, _ = tracker.load()
    what_if = {}
    for pair in args.what_if or []:
        item_id, _, value = pair.partition("=")
        if item_id not in {i["id"] for i in items}:
            fail(f"--what-if names an unknown item: {item_id}")
        try:
            what_if[item_id] = read_number(value)
        except ValueError:
            fail(f"--what-if takes ID=PERCENT, got '{pair}'")
    try:
        target = read_number(args.target) if args.target is not None else None
    except ValueError:
        fail(f"--target '{args.target}' is not a number")
    only = normalise_course(args.course) if args.course else None
    emit({"status": "ok", "courses": all_grades(tracker, items, only, target, what_if)})


def cmd_target(tracker: Tracker, args) -> None:
    course = normalise_course(args.course)
    try:
        target = read_number(args.grade)
    except ValueError:
        fail(f"'{args.grade}' is not a number")
    path = overview_path(tracker, course)
    if not path.exists():
        emit({"status": "no_overview", "course": course, "path": path.relative_to(tracker.root).as_posix()})
        return
    page = Page(path)
    page.patch({"target_grade": target})
    if not args.dry_run:
        page.save()
    emit({"status": "proposed" if args.dry_run else "updated", "course": course, "target_grade": target,
          "path": path.relative_to(tracker.root).as_posix()})


def grade_line(grade: dict) -> str:
    line = f"{grade['course']} {grade['average']:.1f}% on {grade['graded_weight']}% graded"
    target = grade.get("target")
    if grade["outcome"] == "on_track":
        line += f" · need {grade['required_average']:.1f}% on the rest for {target}"
    elif grade["outcome"] == "secured":
        line += f" · target {target} secured"
    elif grade["outcome"] in ("unreachable", "missed"):
        line += f" · target {target} is out of reach" + (f", best case {grade['max_possible']}%" if "max_possible" in grade else "")
    elif grade["outcome"] == "weights_over_100":
        line += " · weights add up to more than 100, fix them first"
    failed = [h["id"] for h in grade["hurdles"] if h["state"] == "failed"]
    return line + (f" · hurdle failed: {', '.join(failed)}" if failed else "")


def label(item: dict) -> str:
    return " ".join(filter(None, [item["course"], item["title"]]))


def stamp(item: dict) -> str:
    return " ".join(filter(None, [item["due"].isoformat(), item["due_time"]]))


def percent(item: dict) -> str:
    return f" · {item['weight']}%" if item["weight"] is not None else ""


def brief_data(tracker: Tracker, days: int, course=None) -> dict:
    items, _ = tracker.load()
    if course:
        items = [i for i in items if i["course"] == course]
    today, horizon = tracker.today, tracker.today + timedelta(days=days)
    active = [i for i in items if i["status"] in OPEN]
    overdue = [i for i in active if is_overdue(i, today)]
    due_soon = [i for i in active if i["due"] and today <= i["due"] <= horizon]
    start_now = [i for i in active if i["status"] == "todo" and i["start_by"] and i["start_by"] <= today
                 and i["due"] and i["due"] > horizon]
    milestones = sorted(
        ({"id": i["id"], "label": label(i), "text": m["text"], "due": m["due"]}
         for i in active for m in i["milestones"]
         if not m["done"] and m["due"] and m["due"] <= (today + timedelta(days=MILESTONE_WINDOW_DAYS)).isoformat()),
        key=lambda m: (m["due"], m["id"]))
    readiness = []
    for item in due_soon + [i for i in active if i["due"] and horizon < i["due"]]:
        days_left = (item["due"] - today).days
        if item["type"] not in EXAM_LIKE or days_left > EXAM_WINDOW_DAYS:
            continue
        weak = [tracker.concept(name) for name in item["concepts"] if tracker.concept(name)["flagged"]]
        if weak or not item["concepts"]:
            readiness.append({"id": item["id"], "label": label(item), "course": item["course"],
                              "days_left": days_left, "weak": weak, "linked": len(item["concepts"]),
                              "review_by": max(today, item["due"] - timedelta(days=7)),
                              "exam_prep_by": max(today, item["due"] - timedelta(days=3))})
    ranked = sorted(active, key=lambda i: (-score(i, tracker), i["id"]))
    week = None
    term_start, term_end = tracker.setting_date("term_start"), tracker.setting_date("term_end")
    if term_start and term_end and term_start <= today <= term_end:
        week = {"number": (today - term_start).days // 7 + 1, "of": (term_end - term_start).days // 7 + 1}
    return {"status": "ok", "today": today, "days": days, "week": week, "total_items": len(items),
            "overdue": [view(i, tracker) for i in overdue], "due_soon": [view(i, tracker) for i in due_soon],
            "start_now": [view(i, tracker) for i in start_now], "milestones": milestones,
            "exam_readiness": readiness, "next": view(ranked[0], tracker) if ranked else None,
            "grades": [g for g in all_grades(tracker, items, course) if g["graded_weight"]],
            "needs_check": [{"id": i["id"], "label": label(i), "fields": i["needs_check"]}
                            for i in active if i["needs_check"]]}


def render_brief(tracker: Tracker, data: dict, cap: int) -> str:
    if not data["total_items"]:
        return '📅 Tracker: no items yet. Say "add deadline ..." or ingest a course outline.'
    today = data["today"]
    head = f"📅 Tracker brief · {WEEKDAYS[today.weekday()]} {today.isoformat()}"
    if data["week"]:
        head += f" · Week {data['week']['number']} of {data['week']['of']}"
    lines = [head]

    def section(title: str, rows: list) -> None:
        if rows:
            lines.append(f"{title} ({len(rows)}):")
            lines.extend(f"- {row}" for row in rows[:cap])
            if len(rows) > cap:
                lines.append(f"- +{len(rows) - cap} more")

    def raw(item_view: dict) -> dict:
        return {**dict.fromkeys(("course", "due_time", "weight")), **item_view}

    def when(item: dict) -> str:
        due = date.fromisoformat(str(item["due"]))
        return " ".join(filter(None, [WEEKDAYS[due.weekday()], due.isoformat(), item["due_time"]]))

    section("🔥 Overdue", [f"{label(i)} · due {when(i)}{percent(i)}" for i in map(raw, data["overdue"])])
    section(f"⏰ Due in {data['days']} days",
            [f"{when(i)} · {str(i['days_left']) + 'd' if i['days_left'] else 'today'} · {label(i)}{percent(i)} · {i['status']}"
             for i in map(raw, data["due_soon"])])
    section("🚀 Start now", [f"{label(i)} · start-by {i['start_by']} · due {i['due']}{percent(i)}"
                            for i in map(raw, data["start_now"])])
    section("🪜 Milestones", [f"{m['due']} · {m['label']} · {m['text']}" + (" · late" if m["due"] < today.isoformat() else "")
                             for m in data["milestones"]])
    rows = []
    for exam in data["exam_readiness"]:
        if exam["weak"]:
            weak = ", ".join(f"{c['name']} ({c['label']})" for c in exam["weak"])
            rows.append(f"{exam['label']} in {exam['days_left']}d · weak: {weak} · run `review {exam['course']}` by "
                        f"{exam['review_by']} and `exam-prep {exam['course']}` by {exam['exam_prep_by']}")
        else:
            rows.append(f"{exam['label']} in {exam['days_left']}d · no concepts linked yet")
    section("🧠 Exam readiness", rows)
    if len(lines) == 1:
        lines.append(f"✅ Nothing due in the next {data['days']} days.")
    if data["next"]:
        lines.append(f"🎯 Next: {label(raw(data['next']))} (score {data['next']['score']})")
    section("📊 Grades", [grade_line(g) for g in data["grades"]])
    section("⚠️ Needs checking", [f"{n['label']} · {', '.join(n['fields'])}" for n in data["needs_check"]])
    return "\n".join(lines)


def cmd_brief(tracker: Tracker, args) -> None:
    days = args.days if args.days is not None else int(tracker.config["brief_days"])
    data = brief_data(tracker, days, normalise_course(args.course) if args.course else None)
    if args.json:
        emit(data)
    elif data["total_items"] or not args.hook:
        print(render_brief(tracker, data, args.max))


def cmd_hot(tracker: Tracker, args) -> None:
    path = tracker.root / "wiki" / "hot.md"
    if not path.exists():
        emit({"status": "no_hot", "path": "wiki/hot.md"})
        return
    data = brief_data(tracker, int(tracker.config["brief_days"]))
    rows = [f"- {stamp_view(i)} · {label_view(i)} · overdue" for i in data["overdue"]]
    rows += [f"- {stamp_view(i)} · {label_view(i)} · {i['status']}" for i in data["due_soon"]]
    if len(rows) > HOT_MAX_LINES:
        rows = rows[:HOT_MAX_LINES - 1] + [f"- +{len(rows) - HOT_MAX_LINES + 1} more: run `python3 scripts/tracker.py brief`"]
    section = ["## Upcoming", *(rows or ["(None)"]), ""]

    page = Page(path)
    before = page.text()
    start = next((i for i, line in enumerate(page.body) if re.match(r"^##\s+Upcoming\s*$", line)), None)
    if start is None:
        start = next((i for i, line in enumerate(page.body) if re.match(r"^##\s+Recent\s*$", line)), len(page.body))
        page.body[start:start] = section
    else:
        end = next((i for i in range(start + 1, len(page.body)) if re.match(r"^#{1,2}\s", page.body[i])), len(page.body))
        page.body[start:end] = section
    changed = page.text() != before
    if changed and not args.dry_run:
        page.save()
    emit({"status": "updated" if changed else "unchanged", "path": "wiki/hot.md", "lines": rows})


def label_view(item_view: dict) -> str:
    text = " ".join(filter(None, [item_view.get("course"), item_view["title"]]))
    return text + (f" · {item_view['weight']}%" if "weight" in item_view else "")


def stamp_view(item_view: dict) -> str:
    return " ".join(filter(None, [str(item_view["due"]), item_view.get("due_time")]))


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

    plan = commands.add_parser("plan", parents=[common, writes], help="regenerate the unticked milestones")
    plan.add_argument("id")
    plan.add_argument("--steps", help='step names separated by ";" (default: sized by type and weight)')
    plan.add_argument("--start-by", help="override the start-by date")
    plan.set_defaults(run=cmd_plan)

    focus = commands.add_parser("focus", parents=[common], help="next exam or quiz of a course and its concepts")
    focus.add_argument("course")
    focus.set_defaults(run=cmd_focus)

    brief = commands.add_parser("brief", parents=[common], help="session briefing")
    brief.add_argument("--days", type=int, help="look-ahead window (default: brief_days in _config.md, else 14)")
    brief.add_argument("--max", type=int, default=5, help="rows per section (default: 5)")
    brief.add_argument("--course")
    brief.add_argument("--json", action="store_true")
    brief.add_argument("--hook", action="store_true", help="session hook mode: silent when empty, always exits 0")
    brief.set_defaults(run=cmd_brief)

    grades = commands.add_parser("grades", parents=[common], help="standing per course and what is needed")
    grades.add_argument("--course")
    grades.add_argument("--target", help="target grade for this run (default: course overview, then _config.md)")
    grades.add_argument("--what-if", action="append", metavar="ID=PERCENT", help="pretend a mark; repeatable")
    grades.set_defaults(run=cmd_grades)

    target = commands.add_parser("target", parents=[common, writes], help="store a course's target grade")
    target.add_argument("course")
    target.add_argument("grade")
    target.set_defaults(run=cmd_target)

    hot = commands.add_parser("hot", parents=[common, writes], help="rewrite the Upcoming section of wiki/hot.md")
    hot.set_defaults(run=cmd_hot)
    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args()
    if getattr(args, "hook", False):
        # A session hook must never block the session, whatever state the tracker is in.
        try:
            args.run(Tracker(args), args)
        except BaseException:
            pass
        sys.exit(0)
    args.run(Tracker(args), args)


if __name__ == "__main__":
    main()
