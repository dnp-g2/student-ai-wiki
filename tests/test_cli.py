"""Tests for the `student-wiki` dispatcher. Run: python3 -m unittest discover -s tests"""
import re
import tempfile
import unittest

from _util import REPO, run_cli


class CliTest(unittest.TestCase):
    def test_version_matches_the_package(self):
        source = (REPO / "src" / "student_ai_wiki" / "__init__.py").read_text(encoding="utf-8")
        version = re.search(r'__version__ = "([^"]+)"', source).group(1)
        proc = run_cli("--version")
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), f"student-wiki {version}")

    def test_help_lists_every_command(self):
        out = run_cli("--help").stdout
        for command in ("init", "upgrade", "doctor", "tracker", "file"):
            self.assertIn(command, out)

    def test_subcommand_help_uses_the_cli_name(self):
        self.assertIn("student-wiki tracker", run_cli("tracker", "--help").stdout)
        self.assertIn("student-wiki file", run_cli("file", "--help").stdout)

    def test_unknown_command_fails(self):
        self.assertEqual(run_cli("nonsense").returncode, 2)

    def test_hook_mode_never_fails(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertEqual(run_cli("tracker", "brief", "--hook", cwd=empty).returncode, 0)
            self.assertEqual(run_cli("tracker", "brief", "--hook", "--no-such-flag", cwd=empty).returncode, 0)
            self.assertEqual(run_cli("tracker", "brief", "--hook", "--root", "/no/such/dir").returncode, 0)


if __name__ == "__main__":
    unittest.main()
