"""Tests for scripts/tracker.py. Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "tracker.py"
TODAY = "2026-09-20"

# The same item after a round trip through Obsidian's Properties UI and a Windows editor.
OBSIDIAN_PAGE = (
    "﻿---\r\n"
    "tags: [tracker, comp9417]\r\n"
    "type: assignment\r\n"
    "course: 'COMP9417'\r\n"
    "title: \"Assignment 2: Trees\"\r\n"
    "due: 2026-10-12T23:59:00\r\n"
    "weight: 20%\r\n"
    "status: doing\r\n"
    "concepts: [[[Decision-Trees]], \"[[Entropy|H]]\"]\r\n"
    "sources:\r\n"
    "- \"[[2026-09-01-admin-course-outline]]\"\r\n"
    "lecturer: Dr Example\r\n"
    "created_at: 2026-09-01\r\n"
    "---\r\n"
    "# COMP9417 · Assignment 2\r\n"
    "\r\n"
    "## Milestones\r\n"
    "- [x] Understand the spec and plan [due:: 2026-09-30]\r\n"
    "- [ ] First full draft [due:: 2026-10-07]\r\n"
    "\r\n"
    "## Notes\r\n"
    "Pair work is allowed.\r\n"
)


class TrackerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve() / "wiki-root"
        for folder in ("tracker", "concepts", "courses"):
            (self.root / "wiki" / folder).mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def run_raw(self, *args, today=TODAY, env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--root", str(self.root), "--today", today],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )

    def run_json(self, *args, **kwargs):
        proc = self.run_raw(*args, **kwargs)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def add(self, title, kind="assignment", course="COMP9417", **flags):
        args = ["add", "--type", kind, "--title", title]
        if course:
            args += ["--course", course]
        for key, value in flags.items():
            args += ["--" + key.replace("_", "-"), str(value)]
        return self.run_json(*args)

    def item_path(self, item_id):
        return self.root / "wiki" / "tracker" / f"{item_id}.md"

    def concept(self, name, confidence, last_reviewed):
        (self.root / "wiki" / "concepts" / f"{name}.md").write_text(
            f"---\ntags: [concept]\ncourses: [COMP9417]\nconfidence: {confidence}\n"
            f"last_reviewed: {last_reviewed}\n---\n# {name}\n", encoding="utf-8")


class StorageTest(TrackerCase):
    def test_add_writes_canonical_page(self):
        out = self.add("Assignment 2", due="2026-10-12", time="23:59", weight=20,
                       concepts="Gradient-Descent", source="2026-09-01-admin-course-outline")
        self.assertEqual(out["status"], "added")
        self.assertEqual(out["id"], "COMP9417-assignment-2")
        self.assertEqual(out["path"], "wiki/tracker/COMP9417-assignment-2.md")
        self.assertEqual(out["start_by"], "2026-10-02")
        text = self.item_path(out["id"]).read_text(encoding="utf-8")
        for line in ("tags:\n  - tracker\n  - comp9417\n", "type: assignment\n", "course: COMP9417\n",
                     "title: Assignment 2\n", "due: 2026-10-12\n", 'due_time: "23:59"\n', "weight: 20\n",
                     "status: todo\n", "start_by: 2026-10-02\n", "mark:\n",
                     'concepts:\n  - "[[Gradient-Descent]]"\n',
                     'sources:\n  - "[[2026-09-01-admin-course-outline]]"\n',
                     "needs_check: []\n", "created_at: 2026-09-20\n",
                     "# COMP9417 · Assignment 2\n", "## Milestones\n", "## Notes\n"):
            self.assertIn(line, text)
        self.assertNotIn("updated:", text)
        self.assertIn("concept page missing: Gradient-Descent", out["warnings"])

    def test_dry_run_writes_nothing(self):
        out = self.run_json("add", "--type", "quiz", "--course", "comp9417", "--title", "Quiz 1",
                            "--due", "2026-09-25", "--dry-run")
        self.assertEqual(out["status"], "proposed")
        self.assertEqual(list((self.root / "wiki" / "tracker").iterdir()), [])

    def test_existing_item_is_reported(self):
        self.add("Assignment 2", due="2026-10-12", weight=20)
        out = self.add("Assignment 2", due="2026-10-19")
        self.assertEqual(out["status"], "exists")
        self.assertEqual(out["item"]["due"], "2026-10-12")

    def test_todo_without_course_or_date(self):
        out = self.add("Email the tutor", kind="todo", course=None)
        self.assertEqual(out["id"], "todo-email-the-tutor")
        self.assertNotIn("start_by", out)
        listed = self.run_json("list")
        self.assertEqual([i["id"] for i in listed["items"]], ["todo-email-the-tutor"])
        out = self.add("Book a lab slot", kind="todo", course="COMP9417", due="2026-09-22")
        self.assertEqual(out["id"], "COMP9417-todo-book-a-lab-slot")

    def test_bad_inputs(self):
        for args in (["--type", "assignment", "--title", "A1"],
                     ["--type", "assignment", "--title", "A1", "--course", "../etc"],
                     ["--type", "essay", "--title", "A1", "--course", "X1"],
                     ["--type", "quiz", "--title", "Q", "--course", "X1", "--due", "2026-13-40"],
                     ["--type", "quiz", "--title", "Q", "--course", "X1", "--time", "25:00"],
                     ["--type", "quiz", "--title", "Q", "--course", "X1", "--weight", "heavy"]):
            self.assertNotEqual(self.run_raw("add", *args).returncode, 0, args)
        self.assertEqual(self.run_json("done", "COMP9417-nothing")["status"], "not_found")

    def test_start_by_follows_the_weight_band(self):
        expected = {45: "2027-02-08", 25: "2027-02-15", 15: "2027-02-19", 5: "2027-02-24", 2: "2027-02-27"}
        for weight, start in expected.items():
            out = self.add(f"Task {weight}", due="2027-03-01", weight=weight)
            self.assertEqual(out["start_by"], start, weight)
        self.assertEqual(self.add("No weight", due="2027-03-01")["start_by"], "2027-02-22")
        self.assertEqual(self.add("Soon", due="2026-09-24", weight=40)["start_by"], "2026-09-20")

    def test_milestones_are_sized_by_weight(self):
        small = self.add("Small", due="2026-10-30", weight=5)
        self.assertEqual(small["milestones"], [])
        medium = self.add("Medium", due="2026-10-30", weight=20)
        self.assertEqual(medium["start_by"], "2026-10-20")
        self.assertEqual(medium["milestones"], [
            {"text": "Understand the spec and plan", "due": "2026-10-22"},
            {"text": "First full draft", "due": "2026-10-27"},
            {"text": "Review and submit", "due": "2026-10-29"}])
        self.assertEqual(len(self.add("Large", due="2026-10-30", weight=30)["milestones"]), 5)
        exam = self.add("Final", kind="exam", due="2026-11-20", weight=50)
        self.assertEqual([m["text"] for m in exam["milestones"]][0], "Review weak concepts (run review)")
        self.assertEqual(exam["milestones"][-1]["due"], "2026-11-18")
        text = self.item_path("COMP9417-medium").read_text(encoding="utf-8")
        self.assertIn("- [ ] First full draft [due:: 2026-10-27]\n", text)
        self.assertEqual(self.add("Plain", due="2026-10-30", weight=30, plan="none")["milestones"], [])

    def test_list_filters_and_overdue_boundary(self):
        self.add("Late", due="2026-09-19", weight=5)
        self.add("Today", due="2026-09-20", weight=5)
        self.add("Far", due="2026-12-01", weight=5)
        self.add("Other course", course="COMP4337", due="2026-09-22", weight=5)
        self.run_json("done", "COMP9417-today")
        items = {i["id"]: i for i in self.run_json("list", "--all")["items"]}
        self.assertTrue(items["COMP9417-late"]["overdue"])
        self.assertFalse(items["COMP9417-today"]["overdue"])
        self.assertEqual(items["COMP9417-late"]["days_left"], -1)
        open_ids = [i["id"] for i in self.run_json("list")["items"]]
        self.assertEqual(open_ids, ["COMP9417-late", "COMP4337-other-course", "COMP9417-far"])
        soon = [i["id"] for i in self.run_json("list", "--within", "7", "--course", "comp9417")["items"]]
        self.assertEqual(soon, ["COMP9417-late"])
        done = [i["id"] for i in self.run_json("list", "--status", "done")["items"]]
        self.assertEqual(done, ["COMP9417-today"])

    def test_obsidian_rewritten_page_round_trips(self):
        path = self.item_path("COMP9417-assignment-2")
        path.write_bytes(OBSIDIAN_PAGE.encode("utf-8"))
        item = self.run_json("list")["items"][0]
        self.assertEqual((item["due"], item["due_time"], item["weight"], item["status"]),
                         ("2026-10-12", "23:59", 20, "doing"))
        self.assertEqual(item["title"], "Assignment 2: Trees")
        self.assertEqual(item["concepts"], ["Decision-Trees", "Entropy"])
        self.assertEqual(item["sources"], ["2026-09-01-admin-course-outline"])
        self.assertEqual(item["milestones"], [
            {"text": "Understand the spec and plan", "due": "2026-09-30", "done": True},
            {"text": "First full draft", "due": "2026-10-07", "done": False}])

        out = self.run_json("update", "COMP9417-assignment-2", "--status", "done")
        self.assertEqual(out["status"], "updated")
        before = OBSIDIAN_PAGE.encode("utf-8").split(b"\r\n")
        after = path.read_bytes().split(b"\r\n")
        self.assertEqual(len(before), len(after))
        changed = [(a, b) for a, b in zip(before, after) if a != b]
        self.assertEqual(changed, [(b"status: doing", b"status: done")])

    def test_update_mark_and_clear(self):
        self.add("Assignment 1", due="2026-10-12", weight=15, needs_check="due,weight")
        out = self.run_json("update", "COMP9417-assignment-1", "--due", "2026-10-19", "--add-concept", "Bias",
                            "--add-source", "spec-a1")
        self.assertEqual(out["item"]["due"], "2026-10-19")
        self.assertEqual(out["item"]["start_by"], "2026-10-09")
        self.assertEqual(out["item"]["needs_check"], ["weight"])
        self.assertEqual(out["item"]["concepts"], ["Bias"])
        self.assertTrue(any("plan" in w for w in out["warnings"]))
        out = self.run_json("update", "COMP9417-assignment-1", "--clear", "due_time", "--clear", "concepts")
        self.assertNotIn("concepts", out["item"])
        out = self.run_json("mark", "COMP9417-assignment-1", "17", "--out-of", "20")
        self.assertEqual((out["item"]["mark"], out["item"]["out_of"], out["item"]["status"]), (17, 20, "graded"))
        proposed = self.run_json("update", "COMP9417-assignment-1", "--weight", "25", "--dry-run")
        self.assertEqual(proposed["status"], "proposed")
        self.assertIn("weight: 15\n", self.item_path("COMP9417-assignment-1").read_text(encoding="utf-8"))

    def test_unsupported_frontmatter_is_reported_without_a_crash(self):
        self.item_path("COMP9417-odd").write_text(
            "---\ntype: quiz\ncourse: COMP9417\ntitle: Odd\ndue: next friday\nstatus: someday\n"
            "extra:\n  nested: map\n---\n", encoding="utf-8")
        item = self.run_json("list")["items"][0]
        self.assertNotIn("due", item)
        self.assertEqual(len(item["problems"]), 3)


if __name__ == "__main__":
    unittest.main()
