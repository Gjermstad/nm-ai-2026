# Task 1 — Tripletex AI Accounting Agent

**NM i AI 2026 · Kristiania Vikings · Kenneth Gjermstad**

---

## What this is

This is our submission for Task 1 of NM i AI 2026 — a 69-hour Norwegian AI championship held March 19–22, 2026. The task was to build an AI agent that could complete accounting tasks in the Tripletex ERP system automatically.

The competition validator would send our HTTP endpoint a random accounting task — written in any language (Norwegian, Nynorsk, English, German, French, Spanish, Portuguese) — and then check the Tripletex API to see if the agent had completed it correctly. Each task had 6–22 individual checks, and your score was the sum of your best result per task type across 30 different task types.

We finished with **35.79 points on Tripletex, rank #225 of 469 teams**. Our overall competition score was 66.1 (rank #206), carried largely by Task 2 and Task 3.

---

## How the agent works

The agent is a FastAPI application deployed on Google Cloud Run. When the validator sends a task, the agent:

1. Parses the request — extracts the task prompt and decodes any attached PDF files
2. Calls Gemini 2.5 Flash (via Vertex AI) with the task and a detailed set of instructions about the Tripletex API
3. Gemini returns a structured JSON plan — a list of Tripletex API calls to make in sequence
4. The agent executes those calls in order, resolving references between steps (e.g. "use the ID from step 2 in step 4")
5. If any calls fail with validation errors, the agent asks Gemini to fix them and tries again once
6. Returns 200 OK — the validator then inspects the Tripletex sandbox to score the result

The core insight is that the "intelligence" lives almost entirely in the prompt — the instructions we give Gemini about which endpoints exist, which fields are valid, what to search before creating, and what never to do. Better prompt = better score. The Python code is mostly plumbing.

---

## The stack

- **Language:** Python 3.11
- **Framework:** FastAPI
- **Hosting:** Google Cloud Run (europe-north1, auto-scaling, 2 GB memory, 300s timeout)
- **LLM:** Gemini 2.5 Flash via Vertex AI (service account auth — no API key needed on Cloud Run)
- **PDF parsing:** pypdf
- **Logs:** Google Cloud Logging (incredibly useful for debugging)

---

## What went well

### The architecture held up
Single-shot LLM planning with one repair pass worked surprisingly well for most tasks. Gemini would generate a 5–12 step API plan, we'd execute it, and if anything got a 422 error we'd ask Gemini to fix just that part. Simple, fast, and debuggable.

### The Gemini system prompt became our product
Early on we thought the code was the hard part. It wasn't. The code barely changed after the first few days. The real work — and the real score improvements — came from improving the instructions we gave Gemini. Adding "NEVER use dot notation in the fields parameter", "do NOT add a project field to POST /activity", "always search before creating" — each of those one-liners fixed a whole category of failures.

### Cloud Run logs were invaluable
We logged every incoming prompt and every API call with its response. This made debugging fast: grep for the task prompt, see exactly what Gemini planned, see exactly which call failed and why. Without structured logs we'd have been flying blind.

### Iteration speed
Editing the prompt in `main.py`, committing, deploying to Cloud Run, and seeing results in the competition validator took about 3 minutes end to end. That tight loop let us fix several bugs in a single session.

### The NorgesGruppen score (93.0)
Task 3 was basically carried home. That success showed that the approach of investing heavily in the right tools and iterating fast is sound — it just needed more time on Task 1.

---

## What went wrong

### The f-string crash (our worst hour)

`build_llm_prompt()` is a Python f-string — a string where `{variable}` gets replaced with the variable's value. We added documentation text that included `{voucherId}` as an example, which Python tried to evaluate as a variable. It didn't exist. This raised a `NameError` and caused HTTP 500 on every single request.

The brutal part: from the outside, everything looked fine. The endpoint returned 500, but we weren't watching for that — we were watching the competition score. It ran broken for over an hour before we found it in the logs. Every submission during that window scored 0%.

**Lesson:** When the code itself is a prompt template, you have to be obsessive about escaping. And you need alerting on 5xx errors, not just score monitoring.

### The overnight loop burned all 300 daily submissions

We set up a JavaScript loop in the browser that submitted 4 tasks every 3 minutes while we slept. It ran for 5 hours and hit the 300-per-day submission limit around 07:30 AM. When we got back in the morning with new fixes ready, there was nothing left to submit. The fixes sat untested until the competition ended.

**Lesson:** Never burn more than half your daily limit unattended. Save the rest for when you can actually watch the results and react.

### The loop didn't check response codes

The JS loop counted every `fetch()` call as a successful submission — including the ones that returned 429 (rate limit exceeded). We thought we had submitted 16 fresh ones in the morning. They were all rejected silently. We only found out by directly testing the API.

**Lesson:** Always handle non-2xx responses explicitly. Silent failures compound.

### Page navigation killed the JS loop

Every time we navigated to the competition page to check results, the page reloaded and wiped all the JavaScript state — including the loop. It died several times without us noticing. The fix would have been to check results via a `fetch()` API call from the same tab, rather than reloading.

### 6 of 30 task types never seen

With the submission limit burned overnight and no quota left in the morning, we never got scored on 6 of the 30 task types. Some of those might have been easy wins.

### Employee already exists — cascade failure

Several task types involved a named person as project manager. Gemini would try to create that employee even though they already existed in the Tripletex sandbox, get a 422 ("email already exists"), and then every downstream step — create project, create order, create invoice — would be skipped because they depended on the employee ID. A single wrong call at step 1 wiped out 8+ checks at once.

We had the fix for this pattern elsewhere in the prompt (for customers, departments, suppliers — always search first), but hadn't applied it specifically to the project manager context.

---

## How we got better

Most improvements came in a few specific moments:

**PR #15** — Stopped trying to look up VAT types via the API (`GET /vat/type` returns 404) and hardcoded the IDs instead. Turned several 0% scores into working invoices immediately.

**PR #22** — Discovered that Tripletex requires a bank account to be configured before any invoice payment can go through. Added a mandatory first step to every invoice flow: look up account 1920 and mark it as a bank account. Unlocked a whole tier of tasks.

**PR #26** — Bank return reversal was using credit notes (wrong — that cancels the invoice). Switched to the correct voucher reversal endpoint. Another category of tasks suddenly started working.

**PR #55** — The occupation code lookup was silently ignoring our filter parameter and returning all 140 codes. Gemini was picking the wrong one. Fixed by telling Gemini to fetch all codes and scan the list rather than filtering.

**PR #61** — Found and fixed the f-string crash. Score went from 0% on everything to recovering immediately.

**PR #64** — Three fixes in one: activities don't have a project field; if a supplier doesn't exist you have to create it before the invoice; account 1500 requires a customer reference in manual voucher postings. These had been causing failures across multiple task types.

Score progression: ~23 (night 1) → 28.7 (before crash fix) → **35.79 (final)**.

---

## What we'd do differently

If we were to do this again, the priority list would be:

1. **Budget submissions carefully from day one.** 300/day, spread across the competition, with manual review of results before the next batch.

2. **Set up error alerting immediately.** 5xx errors should send a notification — not something you discover by squinting at scores.

3. **Write the system prompt like it's the codebase.** Treat every instruction as a function with edge cases. Ask "what would the LLM do if the data looks slightly different?"

4. **Spend the first few hours just reading the API docs**, not submitting. The Tripletex API has a lot of quirks (silent filter ignoring, system-generated postings, dot notation restrictions) that cost us many hours to discover through trial and error.

5. **Set up a second tab for monitoring** instead of using the same tab running the JS loop.

---

## Reflections on using AI to build AI

This project was built almost entirely with AI assistance (Claude). Kenneth had been coding with AI tools for about a week at competition start. Here's what we observed from that experience:

**What worked about the collaboration:**
- Delegating clearly — "you handle the logs, I'll handle merging PRs" — kept the work moving without confusion about who was doing what
- Keeping AGENT.md and PROGRESS.md updated meant each new AI session could pick up where the last one left off without losing context
- Reviewing every PR before merging, even without fully understanding the code, caught at least one significant bug

**Where to grow:**
- Learning to read logs and diffs directly — not to write the code, but to have an opinion about whether it looks right
- Building intuition for what's reversible vs irreversible before running something unattended
- Understanding one layer below the abstraction (what is a service account, what does a container actually do) — enough to form a hypothesis when something breaks

**The broader lesson about agentic AI:**
The agent did exactly what we told it to do. When it failed, it was almost always because our instructions were ambiguous or incomplete — not because it was "wrong". The skill in building agents isn't programming in the traditional sense. It's clarity of specification: knowing precisely what you want, knowing what can go wrong, and saying both explicitly.

That's a learnable skill. And building things under pressure — like a 69-hour competition — is one of the fastest ways to develop it.

---

*Written after the competition ended. Final standing: Kristiania Vikings, 66.1 overall, #206 of 469 teams.*
