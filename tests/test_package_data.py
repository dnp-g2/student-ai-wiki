"""Guards on the shipped templates and docs. Run: python3 -m unittest discover -s tests"""
import unittest

from _util import REPO, SRC

DATA = SRC / "student_ai_wiki" / "data"
DOCS = [REPO / name for name in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md")] + [REPO / "docs" / "releasing.md"]
STALE = ("scripts/tracker.py", "scripts/file_source.py", "python3 scripts/")


class PackageDataTest(unittest.TestCase):
    def test_template_counts(self):
        self.assertEqual(len(list((DATA / "managed" / "skills").glob("*/SKILL.md"))), 7)
        self.assertEqual(len(list((DATA / "managed" / "commands").glob("*.md"))), 7)
        for rel in ("managed/AGENTS.md", "managed/SCHEMA.md", "managed/dot_claude/settings.json", "seed/Home.md",
                    "seed/dot_gitignore", "seed/dot_obsidian/app.json", "seed/raw/dot_manifest.json",
                    "seed/wiki/hot.md", "seed/wiki/tracker/_config.md"):
            self.assertTrue((DATA / rel).is_file(), rel)

    def test_no_live_dotfiles_or_symlinks_in_the_template(self):
        for path in DATA.rglob("*"):
            self.assertFalse(path.is_symlink(), path)
            self.assertFalse(path.name.startswith(".") and path.name != ".DS_Store", path)

    def test_no_stale_script_paths(self):
        for path in [*DATA.rglob("*.md"), *DATA.rglob("*.json"), *[doc for doc in DOCS if doc.exists()]]:
            text = path.read_text(encoding="utf-8")
            for stale in STALE:
                if path.name == "CHANGELOG.md":
                    continue
                self.assertNotIn(stale, text, f"{path} still mentions {stale}")

    def test_seed_wiki_carries_no_tool_release_notes(self):
        self.assertNotIn("## 20", (DATA / "seed" / "wiki" / "log.md").read_text(encoding="utf-8"))
        self.assertIn("## Recent\n(None)", (DATA / "seed" / "wiki" / "hot.md").read_text(encoding="utf-8"))

    def test_authored_text_has_no_em_dash(self):
        for path in [*DATA.rglob("*.md"), *[doc for doc in DOCS if doc.exists()]]:
            self.assertNotIn("—", path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
