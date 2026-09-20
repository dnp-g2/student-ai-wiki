"""Tests for `student-wiki init`. Run: python3 -m unittest discover -s tests"""
import json
import os
import unittest

from _util import VaultCase, run_cli, tree_digest

SKILLS = ("exam-prep", "wiki-core", "wiki-diagram", "wiki-ingest", "wiki-lint", "wiki-review", "wiki-tracker")


class InitTest(VaultCase):
    def test_creates_the_whole_vault_without_symlinks(self):
        out = self.init()
        self.assertEqual(out["status"], "created")
        for rel in ("AGENTS.md", "SCHEMA.md", "Home.md", ".gitignore", ".obsidian/app.json", "wiki/hot.md",
                    "wiki/tracker/_config.md", "raw/.manifest.json", ".claude/commands/due.md"):
            self.assertTrue((self.vault / rel).is_file(), rel)
        for skill in SKILLS:
            claude = self.vault / ".claude" / "skills" / skill / "SKILL.md"
            agents = self.vault / ".agents" / "skills" / skill / "SKILL.md"
            self.assertEqual(claude.read_bytes(), agents.read_bytes())
        links = [p for p in self.vault.rglob("*") if p.is_symlink()]
        self.assertEqual(links, [])
        self.assertFalse(any(name.startswith("dot_") for _, dirs, files in os.walk(self.vault) for name in dirs + files))

    def test_state_records_managed_files_only(self):
        self.init()
        state = self.state()
        self.assertEqual(state["schema"], 1)
        self.assertEqual(state["tool_version"], state["created_by_version"])
        files = state["files"]
        self.assertEqual(files["AGENTS.md"]["kind"], "managed")
        self.assertEqual(len(files["AGENTS.md"]["sha256"]), 64)
        self.assertEqual(files[".claude/settings.json"]["kind"], "merged")
        self.assertFalse(any(rel.startswith(("wiki/", "raw/")) or rel == "Home.md" for rel in files))

    def test_session_hook_calls_the_installed_command(self):
        self.init()
        settings = json.loads((self.vault / ".claude" / "settings.json").read_text(encoding="utf-8"))
        command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertTrue(command.startswith("student-wiki tracker brief --hook"))
        self.assertTrue(command.endswith("|| true"))

    def test_dry_run_writes_nothing(self):
        out = self.init("--dry-run")
        self.assertEqual(out["status"], "proposed")
        self.assertIn("AGENTS.md", out["created"])
        self.assertFalse(self.vault.exists())

    def test_second_init_points_at_upgrade(self):
        self.init()
        proc = run_cli("init", self.vault)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("student-wiki upgrade", proc.stderr)

    def test_existing_files_are_kept(self):
        (self.vault / "wiki").mkdir(parents=True)
        (self.vault / "wiki" / "index.md").write_text("my index\n", encoding="utf-8")
        (self.vault / "AGENTS.md").write_text("my rules\n", encoding="utf-8")
        out = self.init()
        self.assertIn("wiki/index.md", out["seed_kept"])
        self.assertIn("AGENTS.md", out["skipped_modified"])
        self.assertEqual((self.vault / "wiki" / "index.md").read_text(encoding="utf-8"), "my index\n")
        self.assertEqual((self.vault / "AGENTS.md").read_text(encoding="utf-8"), "my rules\n")

    def test_commands_work_from_inside_the_new_vault(self):
        self.init()
        inside = self.vault / "wiki" / "concepts"
        add = ("tracker", "add", "--type", "assignment", "--course", "COMP1234", "--title", "A1",
               "--due", "2030-10-12", "--weight", "20")
        before = tree_digest(self.vault)
        self.assertEqual(self.cli_json(*add, "--dry-run", cwd=inside)["status"], "proposed")
        self.assertEqual(tree_digest(self.vault), before)
        self.cli_json(*add, cwd=inside)
        self.assertIn("A1", run_cli("tracker", "brief", "--days", "9999", cwd=inside).stdout)
        slides = self.base / "L1 Intro.pdf"
        slides.write_bytes(b"slides")
        filed = self.cli_json("file", slides, "--course", "comp1234", "--type", "lecture", "--dry-run", cwd=inside)
        self.assertTrue(filed["raw_path"].startswith("raw/COMP1234/lectures/"))


if __name__ == "__main__":
    unittest.main()
