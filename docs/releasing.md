# Releasing

Releases are automated by [release-please](https://github.com/googleapis/release-please). You merge pull requests with Conventional Commit titles; the rest follows.

## The routine

1. Merge work into `main`. `.github/workflows/release-please.yml` runs and opens (or updates) a pull request titled `chore(main): release X.Y.Z`. That PR bumps `__version__` in `src/student_ai_wiki/__init__.py` and writes the new `CHANGELOG.md` section.
2. When you want to ship, review and merge the release PR.
3. The same workflow then tags `vX.Y.Z`, creates the GitHub release, builds the wheel and sdist, publishes them to PyPI through trusted publishing, and attaches them to the GitHub release.
4. Check: `pipx install student-ai-wiki==X.Y.Z` in a clean environment, then `student-wiki --version`.

`__version__` is the single source of truth. Hatchling reads it at build time; `student-wiki --version` and the vault state file read it at run time. Never edit it by hand.

To force a specific version, add a footer to any commit on `main`: `Release-As: 1.0.0`.

## One-time setup

1. **PyPI pending publisher.** Sign in to PyPI as the project owner → Your account → Publishing → Add a pending publisher: project `student-ai-wiki`, owner `dnp-g2`, repository `student-ai-wiki`, workflow `release-please.yml`, environment `pypi`. The workflow filename must match exactly.
2. **GitHub environment.** Repository Settings → Environments → New environment `pypi`. Adding yourself as a required reviewer gives a manual gate before each upload.
3. **Actions permission.** Settings → Actions → General → enable "Allow GitHub Actions to create and approve pull requests".
4. **Token for release PRs.** A pull request opened with the default `GITHUB_TOKEN` does not trigger CI. Create a fine-grained personal access token limited to this repository with read and write access to Contents, Pull requests and Workflows, and save it as the repository secret `RELEASE_PLEASE_TOKEN`. Without the secret the workflow falls back to `GITHUB_TOKEN`; close and reopen the release PR to run CI on it.
