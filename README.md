# NM i AI 2026 — Kenneth Gjermstad / Kristiania Vikings

**NM i AI** (Norwegian AI Championship) is one of Norway's largest AI competitions — a 69-hour sprint where teams build working AI systems from scratch. The 2026 edition ran from March 19–22 with a **1,000,000 NOK prize pool** and **476 competing teams**.

This repository documents my solo entry: all code, experiments, submissions, and lessons learned across three independent tasks.

---

## Results

| Task | Description | Score | Rank |
|------|-------------|-------|------|
| Task 1 — Tripletex | AI accounting agent | 34.3 (normalized) / 35.79 raw | #233 / 398 |
| Task 2 — Astar Island | Norse world terrain prediction | 69.4 (normalized) / 185.1 raw | #242 / 395 |
| Task 3 — NorgesGruppen | Grocery shelf object detection | 95.2 (normalized) / 0.8818 mAP | #204 / 347 |
| **Overall** | Average across all three tasks | **66.3** | **#214 / 476** |

_Since it was possible to get points in just one task, the leaderboard for a single task is not as long as the full leaderboard where 476 teams in total got points in at least one task._

---

## The Competition

Three independent AI challenges, each worth 33% of your total score.

| Task | Partner | Type | Submission format |
|------|---------|------|-------------------|
| Tripletex | [Tripletex](https://tripletex.no) | AI accounting agent | Live HTTPS endpoint |
| Astar Island | — | Probabilistic terrain prediction | REST API predictions |
| NorgesGruppen Data | [NorgesGruppen](https://norgesgruppen.no) | Grocery shelf object detection | Code upload (ZIP) |

The competition kicked off at 18:00 on Thursday and ended at 15:00 on Sunday — 69 hours to go from nothing to a working, deployed system.

---

## Score Progression (69 hours)

| Time | Rank | Total | Detection | Tripletex | Astar | What happened |
|------|------|-------|-----------|-----------|-------|---------------|
| Sat Mar 21, ~02:39 | #318 | 12.9 | 19.3 | 19.5 | — | Early Saturday morning |
| Sat Mar 21, morning | #274 | 32.5 | 19.3 | 27.6 | 50.6 | First Astar round result in |
| Sat Mar 21, midday | #273 | 35.2 | 19.3 | 31.8 | 54.5 | Tripletex improving |
| Sat Mar 21, ~21:42 | #233 | — | — | 26.8 | — | Overnight bot loop starts |
| Sun Mar 22, early | #230 | 56.3 | 82.4 | 32.3 | 54.1 | NorgesGruppen: fixed pipeline, 0.1786 → 0.7626, then 0.7780 |
| Sun Mar 22 | #230 | 56.8 | 84.0 | 32.3 | 54.1 | Tripletex f-string crash fixed |
| Sun Mar 22, morning | #220 | 63.1 | 84.0 | 34.3 | 70.9 | Overnight retrain lands + final NorgesGruppen submissions: 0.8818 |
| Sun Mar 22, ~12:xx | #206 | 66.1 | 93.0 | 34.3 | 70.9 | Astar rounds completing |
| Sun Mar 22, ~13:xx | **#202** | **66.8** | **95.2** | **34.3** | **70.9** | **Peak rank during competition** |
| **Sun Mar 22, 15:00** | **#214** | **66.3** | **95.2** | **34.3** | **69.4** | **Competition closed** |

The score went from **12.9 → 66.3** and rank from **#318 → #214** over the course of the weekend. Peak rank was **#202** just before the final Astar round adjusted the score slightly downward at close.

---

## Task 1 — Tripletex AI Accounting Agent

**Score: 35.79 raw / 34.3 normalized — Rank #233 of 476 — 30/30 task types**

The validator sent a random accounting task — in any of seven languages (Norwegian, Nynorsk, English, German, French, Spanish, Portuguese) — to our HTTP endpoint, then inspected the Tripletex ERP sandbox to see if the agent had completed it correctly. Each of the 30 task types tested a different accounting workflow.

### How it works

A FastAPI application deployed on **Google Cloud Run**:

1. Receives the task prompt + any attached PDFs
2. Calls **Gemini 2.5 Flash** (via Vertex AI) with detailed Tripletex API instructions
3. Gemini returns a structured JSON plan — a sequence of API calls
4. The agent executes those calls, resolving references between steps (e.g. "use the ID from step 2 in step 4")
5. If calls fail with validation errors, Gemini is asked to repair and retry once

**The core insight:** the "intelligence" lives almost entirely in the prompt. Better instructions = better score. The Python code is mostly plumbing. Every PR that improved the score was a prompt change, not a code change.

### Stack

- Python 3.11 + FastAPI
- Google Cloud Run (europe-north1, 2 GB memory, 300s timeout)
- Gemini 2.5 Flash via Vertex AI (service account auth — no API key needed on Cloud Run)
- PDF parsing: `pypdf`
- Logging: Google Cloud Logging

### Score progression

~23 (night 1) → 28.7 → **35.79 (final)**. Key improvements:

- Hardcoded VAT IDs instead of fetching them (the endpoint returns 404)
- Added mandatory bank account setup before any invoice payment flow
- Fixed bank return reversal — credit notes cancel invoices, voucher reversal was the correct endpoint
- Fixed f-string crash (see below)

### What we learned the hard way

**The f-string crash** — the system prompt lives inside a Python f-string, so every `{word}` in documentation examples gets evaluated as a variable. One unescaped `{voucherId}` caused a `NameError` → HTTP 500 on every single request, for over an hour, without any alert. Score during that window: 0%.

**The overnight loop** — we set up an auto-submit loop in the browser to run while we slept. It ran for 5 hours and burned all 300 of our daily submissions by 07:30 AM. When we woke up with new fixes ready, there was nothing left to submit. 6 of 30 task types were never scored.

**Lesson:** Silent failures compound. Design systems to fail loudly.

📁 Full write-up: [`task1-Tripletex/README.md`](task1-Tripletex/README.md)

---

## Task 2 — Astar Island Operator

**Score: 185.1 raw / 69.4 normalized — Rank #242 of 476 — 7 rounds played**

Astar Island is a Norse-themed simulation: a 40×40 tile map where each cell can evolve over time into one of six terrain classes (Empty, Settlement, Port, Ruin, Forest, Mountain). The task was to query a viewport-based simulator, observe partial information about the map, and submit a calibrated probability distribution for every cell.

Scores compound across rounds — later rounds have higher weight multipliers, so performance consistency matters more than any single result.

### How it works

We built a full **operator service** with:
- Direct REST API integration against the Astar Island competition API
- A **web dashboard** (Dashboard, Explorer, Submit, Logs tabs) for real-time monitoring
- Background query runner with automatic draft generation
- Manual submit controls by default, with a **T-20 minute deadline guard** as safety fallback
- A lightweight **history-aware linear model** trained on 17 rounds of ground-truth data to calibrate class predictions

The service ran on **Google Cloud Run** and persisted state across restarts so we could manage live rounds without laptop dependency. We never missed a round.

### What we learned

- Round-to-round variance is real: scores ranged from 25 to 52 across rounds as map dynamics shifted
- Overpredicting rare dynamic classes (Port, Ruin) hurt consistently — the global average for Port across all rounds was only ~0.8% of cells
- "Early baseline submit + deadline guard" = you never miss a round, no matter what
- Keeping `OBSERVED / INFERRED / DECISION` evidence tags in documentation made debugging under pressure much cleaner

📁 Full write-up: [`task2-Astar/README.md`](task2-Astar/README.md)

---

## Task 3 — NorgesGruppen Grocery Object Detection

**Score: 0.8818 mAP / 95.2 normalized — Rank #204 of 476 — from 0.1786 to 0.8818 in one night**

The task was to detect grocery products on store shelf images. Submit a ZIP file containing `run.py` + a model (`best.onnx`). The organizer runs it on 248 images and scores the result using mAP (mean Average Precision).

### Score progression

| Submission | Score | What changed |
|------------|-------|--------------|
| Baseline | 0.1786 | Original ONNX pipeline |
| After inference fixes | 0.7626 | Letterbox-aware scaling, correct ONNX decode, class-aware NMS |
| After conf threshold tuning | 0.7780 | CONF_THRESHOLD 0.25 → 0.20 |
| After overnight retraining | 0.8621 | YOLOv8 fine-tuned on GCP GPU (NVIDIA L4) |
| After CONF sweep | 0.8798 | CONF_THRESHOLD → 0.06 |
| After IoU sweep | 0.8808 | IOU_THRESHOLD 0.70 → 0.60 |
| **Final** | **0.8818** | CONF_THRESHOLD → 0.04 |

### What we did

1. **Fixed inference reliability first** — the original pipeline had subtle errors in ONNX output decoding, coordinate rescaling, and NMS. Fixing those alone moved us from 0.1786 to 0.7626.
2. **Switched to bounded one-variable experiments** — changing one parameter per submission made outcomes easy to attribute and rollbacks trivial.
3. **Ran a high-upside overnight retraining job on GCP** — a YOLOv8 fine-tune on a dedicated GPU VM (g2-standard-4, NVIDIA L4) ran while we slept and produced the biggest single jump (+0.084).
4. **Swept thresholds systematically** — each submission tested a specific hypothesis with a clear rollback plan.

### What we learned

- **Reliability before optimization** — we spent hours chasing tuning before the pipeline was even correct. Fix the fundamentals first.
- **Offline proxy metrics don't always transfer** — one change that looked better in local evaluation scored lower on the leaderboard.
- **High-upside compute at the right time** — running a model retrain is only worth it once you have a stable, correct baseline.

📁 Full write-up: [`task3-Norgesgruppen/README.md`](task3-Norgesgruppen/README.md)

---

## Infrastructure

All three tasks ran on a **Google Cloud Platform** project provided as part of the NM i AI 2026 GCP sponsorship:

- **Cloud Run** — for Task 1 (agent endpoint) and Task 2 (operator service)
- **Vertex AI / Gemini 2.5 Flash** — LLM inference for Task 1
- **Compute Engine** — GPU VM (NVIDIA L4) for Task 3 model training
- **Cloud Logging** — structured log aggregation for debugging under pressure

---

## Working with AI to Build AI

This entire project was built almost entirely with AI coding assistance (Claude), by someone who had been coding with AI tools for about a week at competition start.

A few things that worked well about this workflow:
- **Keeping AGENT.md and PROGRESS.md updated** meant each new AI session could pick up context without losing state — essentially a persistent memory layer across sessions
- **Don't write prompts yourself** — ask the AI how a prompt should be written based on what you need, then use what it produces. Every time we did this instead of editing manually, the prompt got better
- **Claude Code can actually use a browser** — at one point it started clicking around websites looking for documentation, taking screenshots, analyzing them to figure out where to click next. Things it couldn't read from source code, it found visually. That was genuinely surprising to watch
- **Delegating clearly** — "you handle the logs, I'll handle merging PRs" — kept the work moving without confusion
- **Reviewing every PR before merging**, even without fully understanding the code, caught at least one significant bug

And a few things to grow into:
- Learning to read diffs and logs directly — not to write the code, but to have an opinion about whether it looks right
- Building intuition for what's reversible vs irreversible before running something unattended
- Understanding one layer below the abstraction — enough to form a hypothesis when something breaks

**The broader lesson about agentic AI:**
The agent did exactly what we told it to do. When it failed, it was almost always because our instructions were ambiguous or incomplete. The skill in building agents isn't traditional programming — it's clarity of specification: knowing precisely what you want, knowing what can go wrong, and stating both explicitly. That's a learnable skill, and 69 hours of pressure is one of the fastest ways to develop it.

---

## Repository Structure

```
nm-ai-2026/
├── task1-Tripletex/        # AI accounting agent (FastAPI + Gemini + Cloud Run)
│   ├── main.py             # Agent logic + Gemini prompt
│   ├── tests/              # 14 unit tests
│   ├── README.md           # Full retrospective
│   └── PROGRESS.md         # Competition diary — all 30 task types covered
│
├── task2-Astar/            # Terrain prediction operator service
│   ├── core.py             # Prediction + probability math
│   ├── backend.py          # Orchestration + API client
│   ├── main.py             # FastAPI app + endpoints
│   ├── static/             # Web dashboard (HTML/JS/CSS)
│   ├── history/            # Training data + linear model
│   ├── tests/              # 16 unit tests
│   ├── README.md           # Full retrospective
│   └── SPEC.md             # Architecture decisions
│
└── task3-Norgesgruppen/    # Grocery shelf object detection
    ├── run.py              # ONNX inference pipeline (final submission)
    ├── README.md           # Full retrospective
    └── PastSubmissions.md  # Full submission log with hypotheses and outcomes
```

---

## About

I'm a frontend and mobile development student in my 6th semester at Kristiania University College in Bergen, currently writing my bachelor's thesis. At home I have a wife and a nine-month-old, so free time is limited. I managed roughly 25 hours of actual competition time across the 69 hours.

I signed up about a week before the competition started, having downloaded Claude Code eight days prior. My classmates had full teams. I competed solo.

In those 25 hours I deployed three independent AI systems from scratch on Google Cloud: a live accounting agent, a terrain prediction service with a real-time web dashboard, and a computer vision pipeline for grocery shelf detection. Finished **214th out of 476 teams**.

Before the IT studies, I spent nine years in sales and customer service at Elkjøp, including a stint as team lead, and I have a vocational background as a graphic designer. I'm currently looking for my first developer job in Bergen. Frontend, fullstack, mobile, or anything IT-related works. I learn best somewhere I can be around colleagues, ask questions, and grow on the job.

---

*MIT License*
