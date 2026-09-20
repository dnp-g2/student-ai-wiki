# Contributing

## Development setup

```bash
git clone https://github.com/dnp-g2/student-ai-wiki.git
cd student-ai-wiki
uv venv && uv pip install -e .        # or: python3 -m venv .venv && .venv/bin/pip install -e .
source .venv/bin/activate
student-wiki --version
```

The package has no runtime dependencies beyond the standard library (plus `tzdata` on Windows) and supports Python 3.9 and newer. Keep it that way: avoid syntax and library features newer than 3.9. On macOS, support covers the two newest releases (currently 26 and 27); CI runs on `macos-26` and gains `macos-27` when GitHub ships that runner.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests are black-box: each one runs `python -m student_ai_wiki ...` against a temporary vault. They run from a bare checkout with no install. Every behavior change needs a test, and every command that writes must honor `--dry-run`.

The suite stays offline. `tests/_util.py` sets `STUDENT_WIKI_NO_UPDATE_CHECK=1` for every test process and every child it spawns. A test that needs the update check active calls `VaultCase.update_env()`, which writes a cache file and points `STUDENT_WIKI_UPDATE_CACHE` at it; an entry inside its 24 hour window is served without a request. `STUDENT_WIKI_UPDATE_URL` redirects the fetch, and `tests/test_update.py` uses it with a `file://` URL to exercise the one path that opens a connection.

## Layout

| Path | Contents |
|---|---|
| `src/student_ai_wiki/cli.py` | The `student-wiki` dispatcher |
| `src/student_ai_wiki/vault.py` | Vault root resolution and the state file |
| `src/student_ai_wiki/scaffold.py` | `init`, `upgrade`, `doctor` |
| `src/student_ai_wiki/start.py` | `student-wiki start`, the session opener both AI tools run |
| `src/student_ai_wiki/update.py` | The daily PyPI check and the notice it prints |
| `src/student_ai_wiki/tracker.py`, `file_source.py` | `student-wiki tracker` and `student-wiki file` |
| `src/student_ai_wiki/data/managed/` | Tool-owned vault files: `AGENTS.md`, `SCHEMA.md`, skills, slash commands, the settings hook. `upgrade` refreshes them |
| `src/student_ai_wiki/data/seed/` | Student-owned starter files: `wiki/`, `raw/`, `Home.md`, `.obsidian/`, `.gitignore`. `init` writes them once |

Skills live only in `src/student_ai_wiki/data/managed/skills/`. A path component named `dot_x` in `data/` is written as `.x` in the vault.

To try your changes the way a student would, create a throwaway vault (the `sandbox/` folder is gitignored):

```bash
student-wiki init ./sandbox
cd sandbox && claude                  # or: codex
student-wiki upgrade                  # after editing a skill, pushes it into the sandbox
```

## Commits and branches

Commits follow [Conventional Commits](https://www.conventionalcommits.org), because the changelog and the version number are generated from them:

| Prefix | Effect on the next release |
|---|---|
| `fix:` | patch |
| `feat:` | minor |
| `feat!:` or a `BREAKING CHANGE:` footer | major (minor while the version is `0.x`) |
| `docs:`, `test:`, `ci:`, `chore:`, `refactor:` | none |

Name branches `feat/...`, `fix/...`, `docs/...` or `chore/...`.

## Writing style

Generated content, skills and docs are English only. Use plain statements and commas, colons or parentheses for asides. Describe what a thing does and stop there.

## Releases

Maintainers: see [docs/releasing.md](docs/releasing.md).
