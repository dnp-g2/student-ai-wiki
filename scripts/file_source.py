#!/usr/bin/env python3
"""
file_source.py - file a course source into raw/ and record its provenance.

The source is copied to raw/<COURSE>/<type-folder>/YYYY-MM-DD-<type>-<slug>.<ext> and is
never modified afterwards. The original path, original filename, SHA-256 and size go into
raw/.manifest.json, keyed by the raw path. The wiki-ingest skill merges the wiki half of
the entry (ingested_at, pages_created, ...) once the pages are written.

Usage:
  python3 scripts/file_source.py <file> --course COMP6713 --type lecture
        [--date 2026-09-20] [--slug attention] [--dry-run] [--root DIR]

Types: lecture, tutorial, assignment, exam, reading, notes, admin.

Prints one JSON object. status is one of:
  proposed    dry run, nothing written
  filed       copied into raw/ and recorded
  registered  the file already lived in raw/; recorded in place
  duplicate   the same content is already in the manifest; raw_path is the existing copy
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

TYPE_FOLDERS = {
    "lecture": "lectures",
    "tutorial": "tutorials",
    "assignment": "assignments",
    "exam": "exams",
    "reading": "readings",
    "notes": "notes",
    "admin": "admin",
}
SLUG_MAX = 80


def slugify(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return slug[:SLUG_MAX].strip("-") or "source"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_manifest(path: Path) -> dict:
    if not path.exists():
        return {"version": 2, "sources": {}}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest.setdefault("sources", {})
    manifest["version"] = 2
    return manifest


def save_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".manifest-", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def fail(message: str) -> None:
    sys.exit(f"Error: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="File a course source into raw/ with provenance.")
    parser.add_argument("file", help="path to the source, anywhere on disk")
    parser.add_argument("--course", required=True, help="course code, e.g. COMP6713, or misc")
    parser.add_argument("--type", required=True, choices=sorted(TYPE_FOLDERS))
    parser.add_argument("--date", help="content date YYYY-MM-DD (default: date in the filename, else today)")
    parser.add_argument("--slug", help="short description for the filename (default: from the original name)")
    parser.add_argument("--dry-run", action="store_true", help="print the proposal and write nothing")
    parser.add_argument("--root", help="wiki root (default: the repository containing this script)")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    raw_dir = root / "raw"
    manifest_path = raw_dir / ".manifest.json"

    src = Path(args.file).expanduser().resolve()
    if not src.exists():
        fail(f"{src} does not exist")
    if not src.is_file():
        fail(f"{src} is not a file")

    course = args.course.strip()
    if course.lower() == "misc":
        course = "misc"
    elif re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", course):
        course = course.upper()
    else:
        fail(f"course '{args.course}' must be a course code such as COMP6713, or misc")

    if args.date:
        try:
            date.fromisoformat(args.date)
        except ValueError:
            fail(f"--date '{args.date}' is not a valid YYYY-MM-DD date")

    digest = sha256_of(src)
    manifest = load_manifest(manifest_path)
    sources = manifest["sources"]

    result = {
        "sha256": digest,
        "size_bytes": src.stat().st_size,
        "original_path": str(src),
        "original_name": src.name,
    }

    for raw_path, entry in sources.items():
        if entry.get("sha256") == digest:
            result.update(
                status="duplicate",
                raw_path=raw_path,
                original_path=entry.get("original_path", raw_path),
                original_name=entry.get("original_name", Path(raw_path).name),
                ingested=bool(entry.get("ingested_at")),
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

    inside_raw = raw_dir in src.parents
    if inside_raw:
        dest = src
        status = "registered"
        named = re.match(r"(\d{4}-\d{2}-\d{2})-", src.name)
        content_date = args.date or (named.group(1) if named else date.today().isoformat())
    else:
        named = re.fullmatch(r"(\d{4}-\d{2}-\d{2})-(.+)", src.stem)
        content_date = args.date or (named.group(1) if named else date.today().isoformat())
        if args.slug:
            slug = slugify(args.slug)
        else:
            rest = named.group(2) if named else src.stem
            # A name that already follows the convention keeps its slug without a doubled type token.
            rest = re.sub(rf"^{args.type}-", "", rest)
            slug = slugify(rest)
        name = f"{content_date}-{args.type}-{slug}{src.suffix.lower()}"
        dest = raw_dir / course / TYPE_FOLDERS[args.type] / name
        status = "filed"
        if dest.exists() and sha256_of(dest) != digest:
            fail(f"{dest.relative_to(root)} already exists with different content; "
                 "raw/ is immutable. Pass --slug to choose another name.")

    raw_path = dest.relative_to(root).as_posix()
    result.update(status="proposed" if args.dry_run else status, raw_path=raw_path)

    if not args.dry_run:
        if not inside_raw and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            if sha256_of(dest) != digest:
                dest.unlink()
                fail(f"copy verification failed for {raw_path}; nothing was recorded")
        sources[raw_path] = {
            "sha256": digest,
            "size_bytes": result["size_bytes"],
            "course": course,
            "type": args.type,
            "date": content_date,
            "original_path": result["original_path"],
            "original_name": result["original_name"],
            "filed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        save_manifest(manifest_path, manifest)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
