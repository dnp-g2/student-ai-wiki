"""Tests for scripts/file_source.py. Run: python3 -m unittest tests/test_file_source.py"""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "file_source.py"


class FileSourceTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name).resolve()
        self.root = base / "wiki-root"
        self.inbox = base / "Down loads"
        (self.root / "raw").mkdir(parents=True)
        self.inbox.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def source(self, name, content=b"slides"):
        path = self.inbox / name
        path.write_bytes(content)
        return path

    def run_script(self, path, *extra, course="comp6713", kind="lecture"):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path), "--course", course, "--type", kind,
             "--root", str(self.root), *extra],
            capture_output=True, text=True,
        )

    def manifest(self):
        return json.loads((self.root / "raw" / ".manifest.json").read_text())

    def test_files_with_conventional_name_and_provenance(self):
        src = self.source("L3 (Final) Attention.PDF", b"attention")
        proc = self.run_script(src, "--date", "2026-09-20")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        expected = "raw/COMP6713/lectures/2026-09-20-lecture-l3-final-attention.pdf"
        self.assertEqual(out["status"], "filed")
        self.assertEqual(out["raw_path"], expected)
        self.assertEqual((self.root / expected).read_bytes(), b"attention")

        entry = self.manifest()["sources"][expected]
        self.assertEqual(entry["sha256"], hashlib.sha256(b"attention").hexdigest())
        self.assertEqual(entry["size_bytes"], 9)
        self.assertEqual(entry["original_path"], str(src))
        self.assertEqual(entry["original_name"], "L3 (Final) Attention.PDF")
        self.assertEqual((entry["course"], entry["type"], entry["date"]),
                         ("COMP6713", "lecture", "2026-09-20"))
        self.assertIn("filed_at", entry)
        self.assertNotIn("ingested_at", entry)
        self.assertEqual(self.manifest()["version"], 2)

    def test_date_precedence(self):
        dated = self.source("2026-03-02-week3.docx", b"a")
        out = json.loads(self.run_script(dated, "--date", "2026-04-01", "--dry-run", kind="tutorial").stdout)
        self.assertEqual(out["raw_path"], "raw/COMP6713/tutorials/2026-04-01-tutorial-week3.docx")

        out = json.loads(self.run_script(dated, kind="tutorial").stdout)
        self.assertEqual(out["raw_path"], "raw/COMP6713/tutorials/2026-03-02-tutorial-week3.docx")

        undated = self.source("outline.pdf", b"b")
        out = json.loads(self.run_script(undated, kind="admin").stdout)
        self.assertEqual(out["raw_path"], f"raw/COMP6713/admin/{date.today().isoformat()}-admin-outline.pdf")

    def test_conventional_name_is_not_double_prefixed(self):
        src = self.source("2026-05-01-exam-final-2025.pdf", b"exam")
        out = json.loads(self.run_script(src, kind="exam").stdout)
        self.assertEqual(out["raw_path"], "raw/COMP6713/exams/2026-05-01-exam-final-2025.pdf")

    def test_slug_override_and_misc_course(self):
        src = self.source("scan0001.pdf", b"c")
        out = json.loads(self.run_script(src, "--slug", "Bayes Rule Cheat-Sheet", "--date", "2026-01-05",
                                         course="MISC", kind="notes").stdout)
        self.assertEqual(out["raw_path"], "raw/misc/notes/2026-01-05-notes-bayes-rule-cheat-sheet.pdf")

    def test_dry_run_writes_nothing(self):
        src = self.source("L1.pdf")
        proc = self.run_script(src, "--dry-run")
        self.assertEqual(json.loads(proc.stdout)["status"], "proposed")
        self.assertEqual(list((self.root / "raw").iterdir()), [])

    def test_duplicate_content_is_reported_not_copied(self):
        first = self.source("L1.pdf", b"same")
        filed = json.loads(self.run_script(first, "--date", "2026-02-02").stdout)
        again = self.source("L1 copy.pdf", b"same")
        out = json.loads(self.run_script(again, "--date", "2026-02-03").stdout)
        self.assertEqual(out["status"], "duplicate")
        self.assertEqual(out["raw_path"], filed["raw_path"])
        self.assertFalse(out["ingested"])
        self.assertEqual(len(self.manifest()["sources"]), 1)
        self.assertEqual(len(list((self.root / "raw" / "COMP6713" / "lectures").iterdir())), 1)

    def test_name_collision_refuses_and_leaves_existing_file(self):
        self.run_script(self.source("L1.pdf", b"one"), "--date", "2026-02-02")
        other = self.inbox / "sub"
        other.mkdir()
        clash = other / "L1.pdf"
        clash.write_bytes(b"two")
        proc = self.run_script(clash, "--date", "2026-02-02")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("immutable", proc.stderr)
        kept = self.root / "raw/COMP6713/lectures/2026-02-02-lecture-l1.pdf"
        self.assertEqual(kept.read_bytes(), b"one")
        self.assertEqual(len(self.manifest()["sources"]), 1)

    def test_file_already_in_raw_is_registered_in_place(self):
        legacy = self.root / "raw" / "COMP6713" / "L9.pdf"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b"legacy")
        out = json.loads(self.run_script(legacy).stdout)
        self.assertEqual(out["status"], "registered")
        self.assertEqual(out["raw_path"], "raw/COMP6713/L9.pdf")
        self.assertTrue(legacy.exists())
        self.assertIn("raw/COMP6713/L9.pdf", self.manifest()["sources"])

    def test_bad_inputs(self):
        self.assertNotEqual(self.run_script(self.inbox / "missing.pdf").returncode, 0)
        self.assertNotEqual(self.run_script(self.inbox).returncode, 0)
        src = self.source("L1.pdf")
        self.assertNotEqual(self.run_script(src, course="../etc").returncode, 0)
        self.assertNotEqual(self.run_script(src, "--date", "2026-13-40").returncode, 0)
        self.assertNotEqual(self.run_script(src, kind="meeting").returncode, 0)


if __name__ == "__main__":
    unittest.main()
