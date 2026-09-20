"""Shared test plumbing: run the CLI from the source tree, no install needed."""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
CLI = [sys.executable, "-m", "student_ai_wiki"]

# Child processes inherit this, including the ones that build their env from os.environ.
os.environ["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC), os.environ.get("PYTHONPATH")]))
os.environ.pop("STUDENT_WIKI_ROOT", None)

# The update check must never reach the network from a test. A test that wants it active builds
# its own env, drops this key and points STUDENT_WIKI_UPDATE_CACHE at a file it wrote itself.
os.environ["STUDENT_WIKI_NO_UPDATE_CHECK"] = "1"
os.environ.pop("STUDENT_WIKI_UPDATE_CACHE", None)
os.environ.pop("STUDENT_WIKI_UPDATE_URL", None)

# test_update.py imports the module in process; every other test goes through the CLI.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import hashlib  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import unittest  # noqa: E402


def run_cli(*args, cwd=None, env=None):
    return subprocess.run([*CLI, *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                          cwd=str(cwd) if cwd else None, env=env)


def tree_digest(root: Path) -> dict:
    """Relative path -> sha256 for every file, with symlinks recorded as such."""
    out = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            out[rel] = "link:" + os.readlink(path)
        elif path.is_file():
            out[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class VaultCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name).resolve()
        self.vault = self.base / "vault"

    def tearDown(self):
        self._tmp.cleanup()

    def cli_json(self, *args, cwd=None):
        proc = run_cli(*args, cwd=cwd)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def init(self, *extra):
        return self.cli_json("init", self.vault, "--json", *extra)

    def state(self):
        return json.loads((self.vault / ".student-wiki" / "state.json").read_text(encoding="utf-8"))

    def update_env(self, latest="99.0.0", age_seconds=0, **extra):
        """An environment whose update check is on and answered by a cache file written here.

        A cache entry inside its 24 hour window is served without a request, so a test that uses
        this stays offline while exercising the whole notice path.
        """
        path = self.base / "update-check.json"
        path.write_text(json.dumps({"schema": 1, "tool": "student-ai-wiki", "latest": latest,
                                    "checked_at": int(time.time()) - age_seconds}), encoding="utf-8")
        env = dict(os.environ, STUDENT_WIKI_UPDATE_CACHE=str(path))
        env.pop("STUDENT_WIKI_NO_UPDATE_CHECK", None)
        env.update(extra)          # an explicit key wins, so a test can put the kill switch back
        return env
