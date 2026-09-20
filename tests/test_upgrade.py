"""Tests for `student-wiki upgrade`. Run: python3 -m unittest discover -s tests"""
import hashlib
import json
import unittest

from _util import VaultCase, run_cli, tree_digest

SKILL = ".claude/skills/wiki-core/SKILL.md"


class UpgradeTest(VaultCase):
    def setUp(self):
        super().setUp()
        self.init()
        self.shipped = (self.vault / SKILL).read_bytes()

    def upgrade(self, *extra):
        return self.cli_json("upgrade", "--root", self.vault, *extra)

    def rewrite_state(self, change):
        path = self.vault / ".student-wiki" / "state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        change(state)
        path.write_text(json.dumps(state), encoding="utf-8")

    def simulate_older_release(self, rel, content=b"rules from an older release\n"):
        (self.vault / rel).write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        self.rewrite_state(lambda state: state["files"][rel].update(sha256=digest))

    def test_fresh_vault_is_up_to_date(self):
        out = self.upgrade()
        self.assertEqual(out["status"], "up_to_date")
        self.assertEqual(out["unchanged"], len([f for f in self.state()["files"].values() if f["kind"] == "managed"]))

    def test_untouched_file_from_an_older_release_is_updated(self):
        self.simulate_older_release(SKILL)
        out = self.upgrade()
        self.assertEqual(out["status"], "upgraded")
        self.assertEqual(out["updated"], [SKILL])
        self.assertEqual((self.vault / SKILL).read_bytes(), self.shipped)

    def test_locally_modified_file_is_left_alone(self):
        (self.vault / SKILL).write_text("my own rules\n", encoding="utf-8")
        out = self.upgrade()
        self.assertEqual(out["status"], "conflicts")
        self.assertEqual(out["skipped_modified"], [SKILL])
        self.assertIn("--force", out["hint"])
        self.assertEqual((self.vault / SKILL).read_text(encoding="utf-8"), "my own rules\n")
        self.assertEqual(self.upgrade()["skipped_modified"], [SKILL])

    def test_force_backs_up_then_overwrites(self):
        (self.vault / SKILL).write_text("my own rules\n", encoding="utf-8")
        out = self.upgrade("--force")
        self.assertEqual(out["status"], "upgraded")
        backup = self.vault / out["backed_up_to"] / SKILL
        self.assertEqual(backup.read_text(encoding="utf-8"), "my own rules\n")
        self.assertEqual((self.vault / SKILL).read_bytes(), self.shipped)

    def test_deleted_file_is_restored(self):
        (self.vault / SKILL).unlink()
        self.assertEqual(self.upgrade()["created"], [SKILL])
        self.assertEqual((self.vault / SKILL).read_bytes(), self.shipped)

    def test_dry_run_changes_nothing(self):
        self.simulate_older_release(SKILL)
        (self.vault / "AGENTS.md").write_text("edited\n", encoding="utf-8")
        before = tree_digest(self.vault)
        out = self.upgrade("--dry-run", "--force")
        self.assertEqual(out["status"], "proposed")
        self.assertIn(SKILL, out["updated"])
        self.assertIn("AGENTS.md", out["backed_up"])
        self.assertEqual(tree_digest(self.vault), before)

    def test_file_dropped_from_the_tool_is_removed_when_untouched(self):
        for name, content in (("old-a", b"retired\n"), ("old-b", b"retired but edited\n")):
            rel = f".claude/skills/{name}/SKILL.md"
            (self.vault / rel).parent.mkdir(parents=True)
            (self.vault / rel).write_bytes(content)
            digest = hashlib.sha256(b"retired\n").hexdigest()
            self.rewrite_state(lambda state, rel=rel: state["files"].update({rel: {"kind": "managed", "sha256": digest}}))
        out = self.upgrade()
        self.assertEqual(out["removed"], [".claude/skills/old-a/SKILL.md"])
        self.assertEqual(out["orphaned_modified"], [".claude/skills/old-b/SKILL.md"])
        self.assertFalse((self.vault / ".claude/skills/old-a").exists())
        self.assertTrue((self.vault / ".claude/skills/old-b/SKILL.md").exists())

    def test_settings_merge_keeps_student_keys_and_restores_the_hook(self):
        path = self.vault / ".claude" / "settings.json"
        settings = json.loads(path.read_text(encoding="utf-8"))
        wanted = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        settings["permissions"] = {"allow": ["Bash(ls:*)"]}
        settings["hooks"]["SessionStart"] = []
        path.write_text(json.dumps(settings), encoding="utf-8")
        self.assertEqual(self.upgrade()["settings"], "updated")
        merged = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(merged["permissions"], {"allow": ["Bash(ls:*)"]})
        self.assertEqual(len(merged["hooks"]["SessionStart"]), 1)
        self.assertEqual(merged["hooks"]["SessionStart"][0]["hooks"][0]["command"], wanted)

    def test_hook_edited_by_the_student_is_kept(self):
        path = self.vault / ".claude" / "settings.json"
        settings = json.loads(path.read_text(encoding="utf-8"))
        settings["hooks"]["SessionStart"][0]["hooks"][0]["command"] = "student-wiki tracker brief --hook"
        path.write_text(json.dumps(settings), encoding="utf-8")
        self.assertEqual(self.upgrade()["settings"], "unchanged")
        kept = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(kept["hooks"]["SessionStart"][0]["hooks"][0]["command"], "student-wiki tracker brief --hook")

    def test_student_content_survives(self):
        note = self.vault / "wiki" / "concepts" / "Entropy.md"
        note.write_text("my note\n", encoding="utf-8")
        own_skill = self.vault / ".claude" / "skills" / "my-skill" / "SKILL.md"
        own_skill.parent.mkdir()
        own_skill.write_text("mine\n", encoding="utf-8")
        (self.vault / "Home.md").write_text("my home\n", encoding="utf-8")
        self.simulate_older_release(SKILL)
        self.upgrade("--force")
        self.assertEqual(note.read_text(encoding="utf-8"), "my note\n")
        self.assertEqual(own_skill.read_text(encoding="utf-8"), "mine\n")
        self.assertEqual((self.vault / "Home.md").read_text(encoding="utf-8"), "my home\n")

    def test_vault_from_a_newer_tool_is_refused(self):
        self.rewrite_state(lambda state: state.update(tool_version="999.0.0"))
        proc = run_cli("upgrade", "--root", self.vault)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("pipx upgrade student-ai-wiki", proc.stderr)

    def test_crlf_checkout_counts_as_unmodified(self):
        (self.vault / SKILL).write_bytes(self.shipped.replace(b"\n", b"\r\n"))
        self.assertEqual(self.upgrade()["status"], "up_to_date")

    def test_unmanaged_folder_points_at_init(self):
        bare = self.base / "bare"
        bare.mkdir()
        proc = run_cli("upgrade", "--root", bare)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("student-wiki init", proc.stderr)

    def test_doctor_reports_a_missing_managed_file(self):
        checks = {c["check"]: c for c in json.loads(run_cli("doctor", "--json", "--root", self.vault).stdout)["checks"]}
        self.assertTrue(checks["managed files present"]["ok"])
        self.assertTrue(checks["session hook"]["ok"])
        (self.vault / "AGENTS.md").unlink()
        proc = run_cli("doctor", "--json", "--root", self.vault)
        self.assertEqual(proc.returncode, 1)
        checks = {c["check"]: c for c in json.loads(proc.stdout)["checks"]}
        self.assertIn("AGENTS.md", checks["managed files present"]["detail"])


if __name__ == "__main__":
    unittest.main()
