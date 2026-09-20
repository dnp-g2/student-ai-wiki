<div align="center">

# 📚 Student LLM Wiki

**Turn your course slides into a personal wiki with AI**

</div>

---

### What is this?

You drop course PDF slides into the `raw/` folder. The AI turns them into organized wiki notes in `wiki/`. You read the notes in [Obsidian](https://obsidian.md), and the AI quizzes you, writes practice questions, and shows you where you are weak. **You never write notes yourself.**

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
| Claude Code CLI | Terminal users | [Install guide](https://docs.anthropic.com/claude-code) |
| Claude Code Web | No install needed | [claude.ai/code](https://claude.ai/code) |
| Cursor | IDE-style interface | [cursor.com](https://www.cursor.com) |
| Trae | Users in China | [trae.ai](https://www.trae.ai) |
| Cowork | Team use | See Cowork docs |
| GitHub Copilot | Existing subscribers | VS Code marketplace |

**3. Your course slides** (PDF or other text formats)

---

### Step 1: Clone the repo and open in Obsidian

```bash
git clone https://github.com/IssacW228/student-llm-wiki.git
cd student-llm-wiki
```

Open Obsidian → "Open folder as vault" → select the `student-llm-wiki` folder.

> **Install the Dataview plugin**: Obsidian Settings → Community plugins → Browse → search `Dataview` → Install and enable.

---

### Step 2: Open the project with your AI tool

<details>
<summary><strong>Claude Code CLI</strong></summary>

1. Make sure Claude Code CLI is installed and you're logged in
2. Run in the project folder:
   ```bash
   claude
   ```
3. Claude Code finds the `.claude/` config folder by itself, so there is nothing to set up
4. Type commands or plain English to get started

</details>

<details>
<summary><strong>Claude Code Web (no install needed)</strong></summary>

1. Go to [claude.ai/code](https://claude.ai/code)
2. Connect this repository to Claude Code
3. Claude Code finds the `.claude/` config by itself, so you can start typing commands right away

</details>

<details>
<summary><strong>Cursor</strong></summary>

1. Open the `student-llm-wiki` folder in Cursor
2. The rules in `.cursor/rules/wiki.mdc` are already set up and apply automatically
3. Type commands in the Cursor chat panel

</details>

<details>
<summary><strong>Trae</strong></summary>

1. Open the `student-llm-wiki` folder in Trae
2. The skills in `.trae/skills/` are already set up and Trae finds them by itself
3. Type commands in the chat panel

</details>

<details>
<summary><strong>Cowork</strong></summary>

1. Point your Cowork project at the `student-llm-wiki` folder
2. `COWORK-INSTRUCTIONS.md` loads automatically
3. Start chatting

</details>

<details>
<summary><strong>GitHub Copilot / OpenAI Codex</strong></summary>

1. Open the project in an editor with Copilot support
2. `AGENTS.md` is read automatically
3. Type commands in the chat panel

</details>

---

### Step 3: Ingest your first slide deck

1. Create a folder under `raw/` named after your course (e.g. `raw/MATH1001/`)
2. Copy your PDF into that folder
3. In your AI tool, type:
   ```
   ingest raw/MATH1001/L1.pdf
   ```
4. The AI generates concept pages, a course overview, and a source summary
5. Switch to Obsidian and open `Home.md` to see your new notes

> The same file is never ingested twice. The wiki remembers every file it has already read.

---

### Commands

| Command | What it does |
|---|---|
| `ingest raw/XXXX/L1.pdf` | Turn a slide deck into notes, a course overview, and links to your other courses |
| `lint` | Check the wiki for problems: broken links, pages nothing links to, concepts you have not reviewed lately, missing overviews, missing glossary terms |
| `review XXXX` | The AI quizzes you until you can explain each concept simply |
| `exam-prep XXXX` | Get practice questions on your weak concepts |
| `diagram ConceptName` | Add a Mermaid diagram to a concept page (flowchart / architecture / sequence / etc.) |

You can also use plain English: "quiz me on this course" or "import this file into the wiki".

---

### Adding a new course

1. Create a folder under `raw/` for the course (e.g. `raw/PHYS1001/`)
2. Put your slides in it
3. Run `ingest`. The course overview page is created for you
4. The `Home.md` dashboard updates by itself

---

### Project structure

```
student-llm-wiki/
├── raw/              ← Your slides (the AI only reads these)
│   └── XXXX/         ← One folder per course
├── wiki/             ← AI-generated notes (auto-maintained)
│   ├── concepts/         ← Concept pages (one per concept, with diagrams)
│   ├── courses/          ← Course overviews (auto-created on ingest)
│   ├── sources/          ← Slide summaries
│   ├── exam-prep/        ← Practice questions
│   ├── connections-log.md  ← Links found between courses
│   ├── contradictions.md   ← Places where sources disagree
│   ├── glossary.md         ← English term index (auto-populated)
│   ├── overview.md         ← The big picture across courses (auto-updated)
│   ├── index.md            ← Master catalog
│   └── hot.md              ← AI context cache (read first each session)
├── Home.md           ← Obsidian dashboard
│
│   AI tool config (you can leave these alone):
├── .claude/          ← Claude Code config
├── .cursor/          ← Cursor config
├── .trae/            ← Trae config
├── AGENTS.md         ← Copilot/Codex config
└── COWORK-INSTRUCTIONS.md  ← Cowork config
```

---

### Credits

- [Andrej Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (the original pattern)
- [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian) (hot cache, manifest dedup, splitting rules into skills)
- [Obsidian](https://obsidian.md) (where you read your notes)

### License

MIT
