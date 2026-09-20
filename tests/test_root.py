"""Tests for vault root resolution. Run: python3 -m unittest discover -s tests"""
import json
import os
import unittest

from _util import VaultCase, run_cli


class RootTest(VaultCase):
    def listing(self, *args, cwd=None, env=None):
        proc = run_cli("tracker", "list", *args, cwd=cwd, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def add(self, root, title):
        proc = run_cli("tracker", "add", "--type", "todo", "--title", title, "--due", "2030-01-01", "--root", root)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def titles(self, listing):
        return [item["title"] for item in listing["items"]]

    def test_walks_up_to_the_state_file(self):
        self.init()
        self.add(self.vault, "In the vault")
        out = self.listing(cwd=self.vault / "wiki" / "concepts")
        self.assertEqual(self.titles(out), ["In the vault"])

    def test_env_beats_walk_up_and_flag_beats_env(self):
        self.init()
        other = self.base / "other"
        self.cli_json("init", other)
        self.add(self.vault, "First")
        self.add(other, "Second")
        env = dict(os.environ, STUDENT_WIKI_ROOT=str(other))
        self.assertEqual(self.titles(self.listing(cwd=self.vault, env=env)), ["Second"])
        self.assertEqual(self.titles(self.listing("--root", self.vault, cwd=self.vault, env=env)), ["First"])

    def test_no_vault_gives_a_clear_error(self):
        self.base.joinpath("empty").mkdir()
        proc = run_cli("tracker", "list", cwd=self.base / "empty")
        self.assertNotEqual(proc.returncode, 0)
        for hint in ("no student wiki found", "--root", "STUDENT_WIKI_ROOT", "student-wiki init"):
            self.assertIn(hint, proc.stderr)


if __name__ == "__main__":
    unittest.main()
