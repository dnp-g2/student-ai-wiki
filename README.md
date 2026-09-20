<div align="center">

# 📚 Student AI Wiki

**Turn your course slides into a personal wiki with AI**

</div>

---

### What is this?

You tell the AI where a course file is (slides, a tutorial sheet, a past exam). It files a renamed copy under `raw/`, records where the file came from, and turns it into organized wiki notes in `wiki/`. You read the notes in [Obsidian](https://obsidian.md), and the AI quizzes you, writes practice questions, and shows you where you are weak. **You never write notes yourself.**

Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

### Requirements

| You need | Notes |
|---|---|
| **Python 3.9 or newer** | Already on macOS and most Linux systems. On Windows, install it from [python.org](https://www.python.org/downloads/) |
| **pipx** or **uv** | Installs command-line tools in their own environment: [pipx](https://pipx.pypa.io/stable/installation/) or [uv](https://docs.astral.sh/uv/getting-started/installation/) |
| **Obsidian** | Free, from [obsidian.md/download](https://obsidian.md/download). The dashboards need the **Dataview** community plugin |
| **One AI CLI** | [Claude Code CLI](https://docs.anthropic.com/claude-code) **2.1.277 or newer**, or [OpenAI Codex CLI](https://developers.openai.com/codex/cli). Only these two are supported |
| **Your course material** | PDF, Word, PowerPoint, Markdown, or plain text |

---

### Install

```bash
pipx install student-ai-wiki
```

or, with uv:

```bash
uv tool install student-ai-wiki
```

Check it:

```bash
student-wiki --version
```

If the shell cannot find `student-wiki`, run `pipx ensurepath` (or `uv tool update-shell`) and open a new terminal.

---

### Quick start

**1. Create your vault.** The vault is the folder that holds your notes and course files. Put it anywhere you like:

```bash
student-wiki init ~/StudyVault
```

**2. Open it in Obsidian.** Open folder as vault → select `~/StudyVault`. Then Settings → Community plugins → Browse → `Dataview` → Install and enable.

**3. Start your AI tool inside the vault.**

```bash
cd ~/StudyVault
claude        # or: codex
```

Claude Code asks you to trust the project the first time, because the vault has a session hook that shows your deadlines. Both CLIs read `AGENTS.md` and find the skills by themselves. Claude Code also gets slash commands such as `/ingest` and `/due`; Codex uses the plain-text requests.

**4. Ingest your first file**, as described in the next section.

Your vault is yours: the tool lives elsewhere on your machine, and the vault holds only your notes, your course files, and a copy of the AI rules. Back it up however you like, including your own private git repository.

---

### Upgrading

```bash
pipx upgrade student-ai-wiki      # or: uv tool upgrade student-ai-wiki
cd ~/StudyVault
student-wiki upgrade
```

The first command updates the tool. The second refreshes the AI rules inside your vault (`AGENTS.md`, `SCHEMA.md`, the skills, the slash commands, the session hook). It never touches `wiki/`, `raw/`, `Home.md`, `.obsidian/` or your tracker settings. If you edited one of the rule files yourself, `upgrade` leaves that file alone and tells you; `student-wiki upgrade --force` saves your version under `.student-wiki/backups/` and installs the new one. Add `--dry-run` to either command to preview it.

`student-wiki doctor` checks the install and the vault and tells you what to fix.

Release notes are in [CHANGELOG.md](CHANGELOG.md).

---

### Uninstall

```bash
pipx uninstall student-ai-wiki    # or: uv tool uninstall student-ai-wiki
```

Your vault is plain files and stays where it is.

---

### Ingest your first slide deck

1. In your AI tool, type `ingest` and the location of the file, wherever it is:
   ```
   ingest ~/Downloads/L1.pdf
   ```
2. The AI works out the course and the kind of file (it asks when unsure) and proposes where the copy goes:
   ```
   ~/Downloads/L1.pdf → raw/MATH1001/lectures/2026-03-02-lecture-limits.pdf
   ```
3. Confirm. The file is copied into `raw/`, and its original location, original name, and SHA-256 are recorded in `raw/.manifest.json`
4. The AI generates concept pages, a course overview, and a source summary
5. Switch to Obsidian and open `Home.md` to see your new notes

> The same content is never filed twice, even under a different name. Your original file stays where it was.

**How `raw/` is organized.** Every file is named `YYYY-MM-DD-{type}-{short-description}.{ext}` and sits in a folder for its kind, inside its course:

| Type | Folder | What goes there |
|---|---|---|
| `lecture` | `lectures/` | Lecture slides, lecture transcripts |
| `tutorial` | `tutorials/` | Tutorial and lab sheets, worked solutions |
| `assignment` | `assignments/` | Assignment and project specs |
| `exam` | `exams/` | Past exams, quizzes, sample papers |
| `reading` | `readings/` | Textbook chapters, papers, articles |
| `notes` | `notes/` | Your own notes |
| `admin` | `admin/` | Course outline, syllabus, rubrics |

You can name the course and type yourself: `ingest ~/Downloads/final-2024.pdf MATH1001 exam`.

---

### Commands

| Command | What it does |
|---|---|
| `ingest ~/Downloads/L1.pdf` | File a copy under `raw/` with its provenance, then turn it into notes, a course overview, and links to your other courses |
| `lint` | Check the wiki for problems: broken links, pages nothing links to, concepts you have not reviewed lately, missing overviews, missing glossary terms |
| `review XXXX` | The AI quizzes you until you can explain each concept simply |
| `exam-prep XXXX` | Get practice questions on your weak concepts |
| `diagram ConceptName` | Add a Mermaid diagram to a concept page (flowchart / architecture / sequence / etc.) |
| `add deadline XXXX assignment 2 due 12 Oct 23:59 worth 20%` | Track an assignment, quiz, exam or to-do; the date is shown back to you before anything is saved |
| `due` | Briefing: overdue items, the next 14 days, work to start now, exam readiness, grades |
| `grades XXXX` | Your standing in a course and the mark you need on the remaining work |
| `calendar` | Build the calendar file that puts reminders on your phone |

You can also use plain English: "quiz me on this course" or "import this file into the wiki".

These are prompts entered inside either CLI. Claude Code additionally supports `/ingest`, `/lint`, `/review`, `/exam-prep`, `/diagram`, `/tracker`, and `/due`. Codex uses the plain-text requests above with the same underlying skills.

---

### Deadlines, grades and calendar

The tracker keeps every assignment, quiz, exam and to-do in one place, so nothing depends on remembering which course page a date was on.

**Getting deadlines in.** Ingest a course outline, assignment spec or exam notice and the AI lists the assessments it found (date, time, weight, hurdle) for you to confirm. Dates are copied only as printed in the source, and anything unclear is marked for you to check. You can also just say it: `add deadline COMP9417 assignment 2 due 12 Oct 23:59 worth 20%`, or `add todo email the tutor about the lab swap`.

**Seeing everything.** `Home.md` shows the next 14 days, and `wiki/tracker/Dashboard.md` shows overdue items, work to start now, milestones, the whole semester by month, and marks so far. Each item is a small page in `wiki/tracker/` that you can edit in Obsidian's Properties panel.

**Knowing what to work on.** Each session opens with a short briefing. Items are ranked by weight and urgency, big assignments get a start-by date and milestones sized by their weight, and an exam coming up with weak concepts linked to it produces a dated suggestion to run `review` and `exam-prep`.

**Grades.** Tell the AI your marks as they come back (`I got 17/20 on COMP9417 quiz 1`). `grades COMP9417` shows your average, hurdle status, and the average you need on the remaining work for your target (`set my COMP9417 target to 75`). Ask "what if I get 70 on the final?" for a what-if.

**Reminders on your phone.** `calendar` writes `calendar/student-wiki.ics` with one event per deadline, plus start-by and milestone events, each with reminders scaled to the weight.

| Calendar | How to add it | Reminders |
|---|---|---|
| Apple Calendar | File → Import | Kept from the file |
| Google Calendar | Settings → Import & export | Google ignores reminders inside calendar files: set default notifications on that calendar |
| Outlook | Add calendar → Upload from file | Kept from the file |

Run `calendar` again after deadlines change and import the file again; existing events update in place. For a feed that refreshes by itself, ask the AI to publish it: the file is uploaded to a secret GitHub gist through the `gh` CLI and you subscribe to its URL once. Anyone who has that URL can read your deadlines.

Set your timezone and term dates once in `wiki/tracker/_config.md`.

Claude Code shows the briefing through a session hook in `.claude/settings.json` and asks you to trust it the first time you open the project. Codex runs the same briefing from `AGENTS.md`.

---

### Adding a new course

1. Run `ingest` on the first file of the course and give the course code (e.g. `ingest ~/Downloads/week1.pdf PHYS1001`)
2. The `raw/PHYS1001/` folders and the course overview page are created for you
3. The `Home.md` dashboard updates by itself

---

### What is in a vault

```
StudyVault/
├── raw/              ← Filed copies of your course material (append-only)
│   ├── XXXX/         ← One folder per course
│   │   └── lectures/ tutorials/ assignments/ exams/ readings/ notes/ admin/
│   └── .manifest.json    ← Provenance: original path and name, SHA-256, pages produced
├── wiki/             ← AI-generated notes (auto-maintained)
│   ├── concepts/         ← Concept pages (one per concept, with diagrams)
│   ├── courses/          ← Course overviews (auto-created on ingest)
│   ├── sources/          ← Slide summaries
│   ├── exam-prep/        ← Practice questions
│   ├── tracker/          ← One page per assignment, exam, deadline, to-do, plus the Dashboard
│   ├── connections-log.md  ← Links found between courses
│   ├── contradictions.md   ← Places where sources disagree
│   ├── glossary.md         ← English term index (auto-populated)
│   ├── overview.md         ← The big picture across courses (auto-updated)
│   ├── index.md            ← Master catalog
│   └── hot.md              ← AI context cache (read first each session)
├── calendar/         ← Generated .ics reminder feed
├── Home.md           ← Obsidian dashboard
│
│   Installed by the tool, refreshed by `student-wiki upgrade`:
├── AGENTS.md         ← Single instruction entry point for both CLIs
├── SCHEMA.md         ← Design reference
├── .claude/skills/   ← Operation rules for Claude Code (loaded on demand)
├── .claude/commands/ ← Claude slash commands
├── .claude/settings.json ← Session hook that shows your deadlines
├── .agents/skills/   ← The same operation rules for Codex
└── .student-wiki/    ← Tool version that last wrote the vault, and upgrade backups
```

The AI runs two commands for you: `student-wiki file` copies a source into `raw/` and records its provenance, and `student-wiki tracker` owns every date, priority and grade calculation. Both work from anywhere inside the vault, and you can run them yourself (`student-wiki tracker --help`).

---

### Troubleshooting

| Symptom | Fix |
|---|---|
| `student-wiki: command not found` | Run `pipx ensurepath` (or `uv tool update-shell`), then open a new terminal |
| The AI says it cannot run `student-wiki` | Same fix; then restart `claude` or `codex` from the new terminal |
| No deadline briefing when Claude Code starts | Accept the project trust prompt, then run `student-wiki doctor` inside the vault |
| Timed deadlines show in the wrong timezone on Windows | Set `timezone` in `wiki/tracker/_config.md`; `student-wiki doctor` reports whether the timezone data loads |
| `upgrade` reports `conflicts` | You edited a rule file. Keep your edit, or run `student-wiki upgrade --force` (your version is saved under `.student-wiki/backups/`) |
| The Home dashboard is empty | Enable the Dataview plugin in Obsidian |
| Publishing the calendar fails | `calendar` publishing needs the [GitHub CLI](https://cli.github.com) signed in with the `gist` scope |
| PowerShell is your Claude Code shell | The session hook is written for a POSIX shell (Git Bash, the Claude Code default on Windows). Edit the command in `.claude/settings.json` to `student-wiki tracker brief --hook`; `upgrade` keeps your other settings |

---

### Versioning

Releases follow [Semantic Versioning](https://semver.org) over the `student-wiki` command line, the vault layout, and the `.student-wiki/state.json` format. While the version is `0.x`, a minor release may change these; the [changelog](CHANGELOG.md) says so when it happens. Every vault records the tool version that last wrote it, and a vault written by a newer version refuses an older tool.

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).

---

### Credits

- [IssacW228's student-llm-wiki](https://github.com/IssacW228/student-llm-wiki) (the upstream project this fork is based on)
- [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (the original pattern)
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (hot cache, manifest dedup, splitting rules into skills)
- [Obsidian](https://obsidian.md) (where you read your notes)

### License

MIT
