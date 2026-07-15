# Setup & Push Guide — ai-engineering-projects

This monorepo contains 15 AI-engineering projects. Project 1 (Support Knowledge
Copilot) is a working, tested scaffold; the rest have READMEs + a shared ROADMAP
that a scheduled agent advances one item at a time.

---

## A. Get the code onto your machine

1. Download `ai-engineering-projects.zip` (from this chat).
2. Unzip it somewhere you keep code, e.g. `~/code/` (Windows: `C:\Users\GAURAV\code\`).
3. Open a terminal **inside** the unzipped `ai-engineering-projects` folder:
   - Windows: open the folder in File Explorer → right-click → "Open in Terminal"
     (or `cd C:\Users\GAURAV\code\ai-engineering-projects`).
   - Mac/Linux: `cd ~/code/ai-engineering-projects`.

---

## B. Run Project 1 locally (optional, ~2 min — proves it works)

Requires Python 3.11+.

```bash
cd 01-support-knowledge-copilot
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q            # expect: 5 passed
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000/docs and try `POST /ask` with:
`{"question": "What does error 429 mean?"}`
You'll get an answer with citations, a confidence breakdown, and the retrieved chunks.

Return to the repo root when done: `cd ..`

---

## C. Push to GitHub (creates the repo + uploads everything)

You need the **GitHub CLI** (`gh`). Install once:
- Windows: `winget install GitHub.cli`
- Mac: `brew install gh`
- Linux: see https://github.com/cli/cli#installation

Then, from the repo root:

**Windows (PowerShell):**
```powershell
.\push_to_github.ps1
```

**Mac/Linux:**
```bash
bash push_to_github.sh
```

The script will:
1. Sign you into GitHub the first time (opens a browser — this is the auth step only you can do).
2. Initialize git and make the first commit.
3. Create a **private** repo named `ai-engineering-projects` under your account.
4. Push all files and print the repo URL.

> To make it public instead, edit the `VISIBILITY`/`$Visibility` line at the top of the script from `private` to `public` before running.

### Manual alternative (if you'd rather not use the script)
```bash
git init
git branch -M main
git add .
git commit -m "Initial commit: AI engineering monorepo"
gh repo create ai-engineering-projects --private --source=. --remote=origin --push
```

---

## D. Turn on the automated builder

Your scheduled task **alternate-day-app-builder** already targets
`https://github.com/<you>/ai-engineering-projects` and runs every other day at 10am.
For it to open PRs on its own it needs the **GitHub connector** authorized in
Claude (Settings → Connectors → GitHub). Once the repo exists and the connector
is authorized, it will:

1. Read `ROADMAP.md`, pick the first unchecked `- [ ]` item.
2. Implement that one item in the right project folder.
3. Run `ruff` + `pytest`, check the item off, and open a PR for your review.

Tip: after authorizing, click **Run now** on the task once to pre-approve its tools.

---

## What's in the box

- `README.md` — repo overview + project table
- `ROADMAP.md` — every project broken into checkbox build items (the builder's to-do list)
- `CONTRIBUTING.md` — how the automated builder works
- `01-support-knowledge-copilot/` — working FastAPI app (hybrid RAG + citations), tests, Docker, CI
- `02-...` through `15-...` — per-project READMEs (tech stack, phases, interview notes)
- `push_to_github.sh` / `push_to_github.ps1` — one-shot push scripts
