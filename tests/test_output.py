"""Tests for the human-readable output of init and upgrade. Run: python3 -m unittest discover -s tests"""
import os
import stat
import unittest

from _util import VaultCase, run_cli


class OutputTest(VaultCase):
    def fake_tools(self, *names):
        """An environment whose PATH holds only the named AI tools."""
        bin_dir = self.base / "bin"
        bin_dir.mkdir(exist_ok=True)
        for name in names:
            # Windows finds a command through PATHEXT, so the fake tool needs an extension there.
            tool = bin_dir / (name + ".cmd" if os.name == "nt" else name)
            tool.write_text("#!/bin/sh\n", encoding="utf-8")
            tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
        return dict(os.environ, PATH=str(bin_dir))

    def test_init_prints_a_summary_and_a_line_to_paste(self):
        proc = run_cli("init", self.vault, env=self.fake_tools("claude", "codex"))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = proc.stdout
        self.assertFalse(out.lstrip().startswith("{"))
        self.assertIn(f"Created your vault at {self.vault}", out)
        self.assertIn("Obsidian", out)
        self.assertIn("&& claude", out)
        self.assertIn("(or: codex)", out)
        self.assertIn("ingest ~/Downloads/", out)
        self.assertLess(len(out.splitlines()), 15)

    def test_start_command_names_the_installed_tool(self):
        out = run_cli("init", self.vault, env=self.fake_tools("codex")).stdout
        self.assertIn("&& codex", out)
        self.assertNotIn("(or:", out)

    def test_init_without_an_ai_tool_says_where_to_get_one(self):
        out = run_cli("init", self.vault, env=self.fake_tools()).stdout
        self.assertIn("Neither claude nor codex is installed", out)
        self.assertIn("&& claude", out)

    def test_start_command_quotes_a_path_with_spaces(self):
        spaced = self.base / "My Vault"
        out = self.cli_json("init", spaced, "--json")
        self.assertIn("'", out["start_command"])
        self.assertIn("My Vault", out["start_command"])

    def test_dry_run_says_nothing_was_written(self):
        out = run_cli("init", self.vault, "--dry-run").stdout
        self.assertIn("Would create your vault", out)
        self.assertIn("Nothing was written", out)
        self.assertFalse(self.vault.exists())

    def test_upgrade_reports_in_plain_words(self):
        self.init()
        self.assertIn("is up to date", run_cli("upgrade", "--root", self.vault).stdout)
        (self.vault / "AGENTS.md").write_text("edited\n", encoding="utf-8")
        (self.vault / ".claude" / "commands" / "due.md").unlink()
        out = run_cli("upgrade", "--root", self.vault).stdout
        self.assertIn("1 file added", out)
        self.assertIn(".claude/commands/due.md", out)
        self.assertIn("Left alone because you edited them (1)", out)
        self.assertIn("student-wiki upgrade --force", out)
        only_conflict = run_cli("upgrade", "--root", self.vault).stdout
        self.assertIn("Checked your vault", only_conflict)


if __name__ == "__main__":
    unittest.main()
