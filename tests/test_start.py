"""Tests for `student-wiki start`. Run: python3 -m unittest discover -s tests"""
import json
import tempfile
import unittest

from _util import VaultCase, run_cli

MARKER = ".student-wiki/greeted"


class StartTest(VaultCase):
    def start(self, *extra, **kwargs):
        proc = run_cli("start", "--root", self.vault, *extra, **kwargs)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def marker(self):
        return self.vault / ".student-wiki" / "greeted"

    def test_the_starter_list_shows_once_and_then_stops(self):
        self.init()
        first = self.start("--compact")
        self.assertIn("What you can say here", first)
        self.assertIn("ingest ~/Downloads/", first)
        self.assertTrue(self.marker().is_file())
        self.assertNotIn("What you can say here", self.start("--compact"))

    def test_the_student_can_ask_for_the_list_again(self):
        self.init()
        self.start("--compact")
        again = self.start()
        self.assertIn("What you can say here", again)
        for request in ("ingest ~/Downloads/", "due", "review", "exam-prep", "grades", "calendar", "lint"):
            self.assertIn(request, again)
        self.assertIn("Say `help` to see this list again.", again)

    def test_a_later_session_is_the_briefing_alone(self):
        self.init()
        self.start("--compact")
        run_cli("tracker", "add", "--root", self.vault, "--type", "assignment", "--course", "COMP9417",
                "--title", "Assignment 2", "--due", "2099-01-01", "--weight", "20")
        later = self.start("--compact")
        self.assertIn("Assignment 2", later)
        self.assertNotIn("What you can say here", later)
        self.assertNotIn("Student AI Wiki", later)

    def test_hook_mode_stays_quiet_once_the_vault_is_greeted(self):
        self.init()
        self.start("--hook")
        self.assertEqual(self.start("--hook").strip(), "")

    def test_hook_mode_never_fails(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run_cli("start", "--hook", cwd=empty).returncode, 0)
            self.assertEqual(run_cli("start", "--hook", "--no-such-flag", cwd=empty).returncode, 0)
            self.assertEqual(run_cli("start", "--hook", "--root", "/no/such/dir").returncode, 0)

    def test_outside_a_vault_it_explains_init(self):
        with tempfile.TemporaryDirectory() as empty:
            proc = run_cli("start", cwd=empty)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("student-wiki init", proc.stdout)
        self.assertIn("No vault here yet", proc.stdout)

    def test_a_folder_that_is_not_a_vault_is_not_treated_as_one(self):
        self.assertIn("No vault here yet", run_cli("start", "--root", self.base).stdout)

    def test_json_carries_the_same_data_as_the_text(self):
        self.init()
        data = json.loads(self.start("--json"))
        self.assertEqual((data["status"], data["mode"], data["first_run"]), ("ok", "full", True))
        self.assertEqual(str(self.vault), data["root"])
        self.assertTrue(data["help"])
        self.assertEqual(data["update"]["source"], "disabled")
        self.assertTrue(self.marker().is_file())
        self.assertFalse(json.loads(self.start("--json", "--compact"))["first_run"])


if __name__ == "__main__":
    unittest.main()
