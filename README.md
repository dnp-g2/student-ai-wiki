<div align="center">

# 📚 Student AI Wiki

**Turn your course slides into a personal wiki with AI**

</div>

---

### What is this?

You tell the AI where a course file is (slides, a tutorial sheet, a past exam). It files a renamed copy under `raw/`, records where the file came from, and turns it into organized wiki notes in `wiki/`. You read the notes in [Obsidian](https://obsidian.md), and the AI quizzes you, writes practice questions, and shows you where you are weak. **You never write notes yourself.**

Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).

---

### Prerequisites

**1. Obsidian (for browsing your notes)**
- Download: [https://obsidian.md/download](https://obsidian.md/download)
- Free. Available on Windows / macOS / Linux / iOS / Android
- Once it is installed, add the **Dataview** community plugin (the Home dashboard needs it)

**2. An AI tool (pick just one)**

| Tool | Best for | Get it |
|---|---|---|
| Claude Code CLI **≥2.1.277** | Claude in your terminal | [Install guide](https://docs.anthropic.com/claude-code) |
| OpenAI Codex CLI | Codex in your terminal | [Install guide](https://developers.openai.com/codex/cli) |

**The minimum supported Claude Code CLI version is 2.1.277.** Older versions are not supported. Use a current OpenAI Codex CLI release.

Both CLIs use the root [`AGENTS.md`](AGENTS.md) as their shared project instructions and load operational rules from [`skills/`](skills/) on demand. Only these two CLIs are supported.

**3. Python 3** (already on macOS and most Linux systems; the filing and tracker scripts use the standard library only). On Windows, make sure the `python3` command works, and run `pip install tzdata` so timed deadlines convert to your timezone.

**4. Your course material** (PDF, Word, PowerPoint, Markdown, or plain text)

---

### Step 1: Clone the repo and open in Obsidian

```bash
git clone https://github.com/dnp-g2/student-ai-wiki.git
cd student-ai-wiki
```

Open Obsidian → "Open folder as vault" → select the `student-ai-wiki` folder.

> **Install the Dataview plugin**: Obsidian Settings → Community plugins → Browse → search `Dataview` → Install and enable.

---

### Step 2: Open the project with your AI tool

<details>
<summary><strong>Claude Code CLI</strong></summary>

1. Install Claude Code CLI using the [official guide](https://docs.anthropic.com/claude-code).
2. Check `claude --version`. This project requires **2.1.277 or newer**; upgrade before continuing if yours is older.
3. Run in the repository root:
   ```bash
   claude
   ```
4. Follow the sign-in prompts on first launch.
5. Project instructions come from `AGENTS.md`. `.claude/skills/` and `.claude/commands/` expose the shared skills and Claude slash commands.
6. Type a plain-text request such as `lint`, or use a Claude slash command such as `/lint`.

</details>

<details>
<summary><strong>OpenAI Codex CLI</strong></summary>

1. Install Codex CLI using the [official guide](https://developers.openai.com/codex/cli), for example with npm:
   ```bash
   npm install -g @openai/codex
   ```
2. Check the installation with `codex --version`.
3. Run in the repository root:
   ```bash
   codex
   ```
4. Follow the sign-in prompts on first launch, or run `codex login` beforehand.
5. Codex reads `AGENTS.md` automatically and discovers the shared skills through `.agents/skills/`.
6. Enter plain-text requests such as `ingest ~/Downloads/L1.pdf`, `lint`, or `review MATH1001`. The Claude slash commands are not Codex commands.

</details>

The skill and command discovery directories (`.claude/skills`, `.claude/commands`, `.agents/skills`) are relative symlinks to the canonical `skills/` and `commands/` directories. Preserve symlinks when cloning or copying the repository (Windows Git may require Developer Mode and symlink support). If native skill discovery is unavailable, explicitly ask the CLI to read `AGENTS.md` and follow its operation-rule paths; all canonical rules remain in `skills/`.

---

### Step 3: Ingest your first slide deck

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

### Project structure

```
student-ai-wiki/
├── raw/              ← Filed copies of your course material (append-only)
│   ├── XXXX/         ← One folder per course
│   │   └── lectures/ tutorials/ assignments/ exams/ readings/ notes/ admin/
│   └── .manifest.json    ← Provenance: original path and name, SHA-256, pages produced
├── scripts/
│   ├── file_source.py    ← Copies a file into raw/, renames it, records provenance
│   └── tracker.py        ← Deadlines, priorities, grades, calendar feed
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
├── calendar/         ← Generated .ics reminder feed (not committed)
├── Home.md           ← Obsidian dashboard
│
│   Shared instructions and CLI discovery:
├── AGENTS.md         ← Single instruction entry point for both CLIs
├── skills/           ← Canonical operation rules (loaded on demand)
├── commands/         ← Canonical Claude slash-command definitions
├── .agents/skills    ← Symlink to skills/ (Codex discovery)
├── .claude/skills    ← Symlink to skills/ (Claude discovery)
├── .claude/commands  ← Symlink to commands/ (Claude slash commands)
└── .claude-plugin/   ← Optional Claude plugin packaging
```

---

### Credits

- [IssacW228's student-llm-wiki](https://github.com/IssacW228/student-llm-wiki) (the upstream project this fork is based on)
- [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (the original pattern)
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (hot cache, manifest dedup, splitting rules into skills)
- [Obsidian](https://obsidian.md) (where you read your notes)

### License

MIT
