# AGENT.md — Task 1: Tripletex AI Accounting Agent

> NM i AI 2026 — Solo competitor, frontend student (Kristiania, 6th semester)
> Last updated: 2026-03-20 ~01:30 CET
> Status: Hybrid Repair agent deployed (single-shot + 422 repair pass). Vertex AI gemini-2.5-flash.

---

## 0. PREFERENCES

- Do not merge bash commands together if they are to different things. If you are to commit and also deplay, make it two steps with separate code boxes.
- When coding keep variable names and code readable for humans. Use rather full words than shortening them.
- Comment effectively so it is possible for a human to read what is going on in the code.
- Every time you have made changes, update AGENT.md and PROGRESS.md in the folder for the task so they don't fall behind and get outdated.
- **At the start of every session, verify the branch/worktree is current with main.**
  Run `git log --oneline -5 main` and `git log --oneline -5 HEAD` and compare the tip commits.
  If HEAD is behind main, do NOT make changes on the stale branch — create a fresh branch from
  `origin/main` instead. Multiple sessions run in parallel and merge PRs continuously, so
  worktrees go stale fast. A stale branch = guaranteed merge conflicts on the PR.
- During the competition we have access to a GCP account with no limit.
  - Google Cloud is an official partner of NM i AI 2026. Selected teams receive a free @gcplab.me account with a dedicated GCP project — no credit limits, no billing setup (we are one of those selected teams).
    - Cloud Run, Vertex AI, Compute Engine
    - Gemini models & AI Studio
    - Cloud Shell & VS Code IDE
    - No credit limits
  - Since we have this chance, use GCP for what it is worth, let GCP use datapower instead of local datapower, set things to work by themselves
  - Always check docs or info, if you need an API or model or anything from GCP, ask the user, don't guess
  - If you have thoughts on how to improve a part of the code, tell the user and explain reasoning, but NEVER change anything without being told.

---

## 1. COMPETITION CONTEXT

- **Competition:** NM i AI 2026
- **Duration:** 69 hours (March 19 18:00 CET → March 22 15:00 CET)
- **Task weight:** 33% of total score (equal weight across 3 tasks)
- **Task type:** AI Accounting Agent — validator sends a random accounting task, agent must complete it via Tripletex API
- **Submission format:** Public HTTPS endpoint (`/solve`) on Cloud Run
- **Validator behavior:** POSTs a JSON payload to `/solve`, checks Tripletex API state after agent returns

---

## 2. INFRASTRUCTURE

### GCP Project

- **Project ID:** `ai-nm26osl-1730`
- **Workbench VM:** `instance-20260319-140156`, zone `europe-west4-a`
- **VM SSH alias:** `gcp-nm-ai` (IP is ephemeral — check Compute Engine console if SSH times out)
- **Cloud Run region:** `europe-north1` (same region as validator = lower latency)
- **Vertex AI region:** `europe-west4`
- **Storage bucket:** `nm-ai-2026` (eu)

### GitHub Repo

- `https://github.com/Gjermstad/nm-ai-2026`
- Always `git pull` before deploying

---

## 3. ORGANIZER DOCS VIA MCP (WRITE THIS DOWN)

Use this to fetch latest competition docs and compare against local `.md` files.

### MCP server endpoint

- `https://mcp-docs.ainm.no/mcp`
- Local config file: `.mcp.json`

### Quick connectivity checks

```bash
claude mcp list
curl -sS -I https://mcp-docs.ainm.no/mcp
```

### Get available docs (through MCP tools)

```bash
claude -p "Use the nmiai MCP server. Run list_docs and print full output." --output-format text --dangerously-skip-permissions
```

### Get one specific doc resource (recommended pattern)

Use MCP `resources/read` and not only keyword search.  
If the server returns intermittent `Session not found`, retry with a fresh `initialize` per resource.

Target Astar resources:
- `challenge://astar-island/overview`
- `challenge://astar-island/mechanics`
- `challenge://astar-island/endpoint`
- `challenge://astar-island/scoring`
- `challenge://astar-island/quickstart`

### Sync policy

- Treat organizer docs as canonical.
- Keep useful local operator notes if upstream removed them.
- Remove obvious upstream artifacts/noise before saving local copies.
