# AGENT.md — Task 1: Tripletex AI Accounting Agent
> NM i AI 2026 — Solo competitor, frontend student (Kristiania, 6th semester)
> Last updated: 2026-03-21 ~23:00 CET
> Status: PR #27 merged — employee sub-resources, tool_code ban, bank return reversal. 28/30 task types seen. Score: 23.3, rank #218.

---

## 0. PREFERENCES (READ THIS FIRST)

### Coding style
- Do not merge bash commands together if they are to different things. If you are to commit and also deploy, make it two steps with **separate code blocks**.
- Keep variable names and code readable for humans. Use full words, not abbreviations.
- Comment effectively so a human can read what is going on in the code.
- Every time you have made changes, update AGENT.md and PROGRESS.md so they don't fall behind.

### Workflow
- **Never push directly to main** (except for AGENT.md/PROGRESS.md-only commits — those can go straight to main).
- **Always create a new PR** for code changes. Give me the PR link every time — I don't want to scroll.
- **Always assume I merged your PR** before I submit new log data to you. Create a new PR each time.
- **After every PR**, give me the deploy commands (pull + deploy) and the submit URL at the bottom so I don't have to scroll up.
- **I always create the PR merge myself** — don't merge PRs programmatically.
- **At the start of every session, verify the branch/worktree is current with main.**
  Run `git log --oneline -5 main` and `git log --oneline -5 HEAD` and compare the tip commits.
  If HEAD is behind main, do NOT make changes on the stale branch — create a fresh branch from
  `origin/main` instead. Multiple sessions run in parallel and merge PRs continuously, so
  worktrees go stale fast. A stale branch = guaranteed merge conflicts on the PR.

### Answer format
- Be concise. Lead with the fix, not the reasoning.
- Give PR link + deploy commands + submit URL at the end of every response that produces a PR.

---

## 1. COMPETITION CONTEXT

- **Competition:** NM i AI 2026
- **Duration:** 69 hours (March 19 18:00 CET → March 22 15:00 CET)
- **Task weight:** 33% of total score (equal weight across 3 tasks)
- **Task type:** AI Accounting Agent — validator sends a random accounting task, agent must complete it via Tripletex API
- **Submission format:** Public HTTPS endpoint (`/solve`) on Cloud Run
- **Validator behavior:** POSTs a JSON payload to `/solve`, checks Tripletex API state after agent returns
- **Tier 3 status:** LIVE as of Saturday March 21 ~11:00 CET — hardest task types now included in validator

---

## 2. INFRASTRUCTURE

### GCP Project
- **Project ID:** `ai-nm26osl-1730`
- **Workbench VM:** `instance-20260319-140156`, zone `europe-west4-a`
- **VM SSH alias:** `gcp-nm-ai` (IP is ephemeral — check Compute Engine console if SSH times out)
- **Cloud Run region:** `europe-north1` (same region as validator = lower latency)
- **Vertex AI region:** `europe-west4`
- **Storage bucket:** `nm-ai-2026` (eu)

### Cloud Run Service
- **URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`
- **Service name:** `tripletex-agent`
- **Memory:** 2Gi
- **Timeout:** 300s (important — complex tasks need multiple LLM calls)
- **Min instances:** 1 during active competition windows (prevents cold starts)

### ⚠️ CRITICAL: Correct working directory
The Cloud Shell working directory for ALL git and deploy operations is:
```
~/nm-ai-2026-1
```
**NOT** `~/nm-ai-2026`. Using the wrong directory deploys stale code.

### Deploy Command (Cloud Shell only — two separate steps)
```bash
cd ~/nm-ai-2026-1 && git pull
```
```bash
cd ~/nm-ai-2026-1/task1-Tripletex && gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --allow-unauthenticated
```

### Log reading (Cloud Shell)
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tripletex-agent" --limit=200 --format="value(textPayload)" --freshness=10m
```

### Submission URL
```
https://tripletex-agent-997219197351.europe-north1.run.app
```

### GitHub Repo
- `https://github.com/Gjermstad/nm-ai-2026`
- Local working directory on Mac: `/Users/kenneth/git/annet/nmiai/nm-ai-2026`
- Always `git pull` in `~/nm-ai-2026-1` before deploying

---

## 3. LLM CHOICE: GEMINI 2.5 FLASH via Vertex AI (global endpoint)

### What we use
- **Model:** `gemini-2.5-flash` via Vertex AI REST API
- **Endpoint:** `https://aiplatform.googleapis.com/v1/projects/ai-nm26osl-1730/locations/global/publishers/google/models/gemini-2.5-flash:generateContent`
- **Auth:** GCP service account (metadata server) — no API key needed on Cloud Run

### Model history
| Option | Status | Reason |
|---|---|---|
| Vertex AI `gemini-2.0-flash-001` | ❌ Abandoned | Model not found in `europe-west4` — 404 on first submission |
| Vertex AI SDK | ❌ Abandoned | Deprecation warnings, model access issues |
| Google AI Studio REST API (`gemini-2.5-pro`) | ❌ Abandoned | Was used temporarily; replaced by Vertex AI global |
| Vertex AI global endpoint `gemini-2.5-flash` | ✅ **Current** | No API key, service account auth, works in Cloud Run |
| Claude API | ❌ Not used | Not available in GCP free tier setup |

---

## 4. TRIPLETEX API

### Sandbox
- **Base URL:** `https://kkpqfuj-amager.tripletex.dev/v2`
- **Sandbox token:** `eyJ0b2tlbklkIjoyMTQ3NjQ1MzAzLCJ0b2tlbiI6ImI3YzQ3Y2E0LTM0ZDgtNGYyZi1iMGU2LWZiMDc1NmJjODBhNyJ9`
- Use for local testing only. **Never hardcode this in deployed code.**

### Validator proxy
- **Base URL sent by validator:** something like `https://tx-proxy-jwanbnu3pq-lz.a.run.app/v2`
- This URL is only resolvable from within the validator's network
- The agent receives `base_url` and `session_token` in the request body and MUST use them

### Authentication
- Basic auth: username `"0"`, password = `session_token`
- `auth=("0", session_token)` in Python requests

### Endpoint status (as of PR #27)

**Verified working (seen 201/200/204 in validator logs):**
- `GET /customer`, `GET /employee`, `GET /project`, `GET /department`, `GET /activity`
- `POST /customer`, `POST /employee`, `POST /department`, `POST /project`, `POST /order`, `POST /product`
- `POST /supplier` (confirmed ✅ — 6/6 on supplier creation task)
- `POST /activity` (confirmed ✅ — PR #25)
- `POST /travelExpense`, `PUT /travelExpense/{id}`, `DELETE /travelExpense/{id}`
- `PUT /order/{id}/:invoice`, `PUT /invoice/{id}/:payment`, `PUT /invoice/{id}/:createCreditNote`
- `GET /invoice` (requires `invoiceDateFrom`/`invoiceDateTo`; NO dot notation in fields param)
- `GET /ledger/account`, `PUT /ledger/account/{id}`
- `POST /ledger/voucher` (body: `"postings"` array ONLY — no vouchers/voucherRows/voucherType/supplier/department fields)
- `GET /ledger/posting` (use parentheses for nested fields: `account(id,number,name)` NOT `account.id`)
- `GET /supplier`
- `POST /timesheet/entry` (confirmed ✅ — 6/6 on timesheet task)
- `POST /employee/employment` (added PR #27 — employee.id + startDate + isMainEmployer)
- `POST /employee/employment/details` (added PR #27 — employment.id, salary, %, job code)
- `GET /employee/employment/occupationCode` (look up job codes)
- `PUT /ledger/voucher/{id}/:reverse` (confirmed PR #26 — bank return reversal with `?date=TODAY`)

**Verified NOT working:**
- `GET /vat/type` → 404 (endpoint does not exist)
- `POST /supplier/invoice` → 405
- `POST /invoice/fromTimesheet` → 405
- `POST /invoice/payment` → 405 (use `PUT /invoice/{id}/:payment` instead)
- `POST /timesheet` (without `/entry`) → 404
- `POST /timeSheet` (capital S) → 404
- `PUT /invoice/{id}/:reversePayment` → 404

**BETA (always 403 in validator environment):**
- `PUT /project/{id}`, `DELETE /project/{id}`, `DELETE /customer/{id}`
- `PUT /order/orderline/{id}`, `DELETE /order/orderline/{id}`
- `POST /travelExpense/cost`

### vatType IDs (hardcoded — do NOT look up via API)
| Rate | vatType | Notes |
|---|---|---|
| 25% (standard) | `{"id": 3}` | Default for most services |
| 15% (food/beverages) | `{"id": 5}` | Middle rate |
| 0% (exempt) | omit vatType field entirely | Do NOT send vatType at all |

### Invalid voucher fields (cause 422 on POST /ledger/voucher)
- `"vouchers"` — use `"postings"` instead
- `"voucherRows"` — does not exist
- `"voucherType"` — does not exist
- `"supplier"` — does not exist on voucher
- `"department"` — does not exist on voucher
- `"customDimensions"`, `"dimension"` — do not exist

### Known validator environment issues (unfixable)
- **INT32_MAX overflow**: Invoice IDs > 2,147,483,647 cause 404 on `PUT /invoice/{id}/:payment`. Bug in validator proxy routing.
- **System-generated postings**: Manual journal entries to accounts like 1290, 1500, 1720, 2400, 2710, 2900, 3400, 5000, 6020 → 422 "system-generated" in validator. Affects month-end closing, supplier invoice vouchers, disagio tasks.
- **Session token expiry**: Some validator runs start with 403 on first call — expired token. Unfixable.

---

## 5. AGENT ARCHITECTURE

### Current architecture: Hybrid Repair (single-shot + one 422/409 repair pass)

```
Prompt → Gemini → full call plan → execute all → if 422/409 errors → Gemini repair → execute corrections → done
```

### Key implementation decisions
| Decision | Choice | Why |
|---|---|---|
| Repair trigger | 422 and 409 | 422 = validation error; 409 code 8000 = stale version field |
| Repair guard | >40s remaining | Avoids triggering repair when out of time |
| 403 response | Abort immediately | Invalid/expired session token |
| 429 response | Abort immediately | Rate limit — all subsequent calls would fail |
| Malformed calls | Skip with warning | Missing `method` or `endpoint` |
| Max API calls | 16 | Hard cap for efficiency (increased from 12 in PR #19) |
| Timeout budget | 255s deadline | 300s − 45s buffer |
| Gemini JSON mode | `responseMimeType: application/json` | Eliminates most parse failures |
| Temperature | 0.1 | Deterministic JSON output |
| Max output tokens | 8192 | Allows full multi-step plans |
| 204 responses | Append `{}` | DELETE and action endpoints return no body |
| List response wrap | `if isinstance(plan, list): plan = {"calls": plan}` | Gemini sometimes returns raw array |
| Unresolved placeholder | Skip call with warning | Dependency returned no results → prevents 422 "wrong type for field" |

---

## 6. CURRENT CODE STATE (post PR #27)

### What is deployed (all merged PRs up to #27)

**Placeholder resolution — three patterns supported (applied in order):**
1. `$responses.N.value.FIELD.SUBFIELD` — nested field (e.g. `voucher.id`) — added PR #26
2. `$responses.N.value.FIELD` — single-item response (POST/PUT)
3. `$responses.N.values.INDEX.FIELD` — list response (GET with count > 1)

**Unresolved placeholder detection (added PR #25):**
- Before executing a call, check if any `$responses.` string remains unresolved
- If so, skip the call with a warning — prevents "wrong type for field" 422 errors
- Applied to body, params, and endpoint combined

**Output format enforcement (added PR #27):**
- Prompt explicitly bans `tool_code`, `function_call`, `action` formats
- Gemini must only output REST API calls with `method`, `endpoint`, `body`, `params`

**Bank account setup (added PR #22):**
- For any invoice flow: GET /ledger/account (number=1920) → PUT /ledger/account with `isBankAccount: true`, `bankAccountNumber: "12345678903"` (11 digits, no dots, no spaces)

**Bank return reversal (added PR #26):**
- Correct flow: GET /invoice → GET /invoice/{id}?fields=id,voucher(id) → PUT /ledger/voucher/$responses.1.value.voucher.id/:reverse?date=TODAY
- NOT: credit note (that cancels the invoice, not restores outstanding balance)

**Employee sub-resources (added PR #27):**
- POST /employee (basic info, employeeNumber as string)
- POST /employee/employment (body: `{"employee": {"id": X}, "startDate": "YYYY-MM-DD", "isMainEmployer": true}`)
- POST /employee/employment/details (body: `{"employment": {"id": X}, "percentageOfFullTimeEquivalent": N, "annualSalary": N, "remunerationType": "MONTHLY_WAGE", "employmentType": "ORDINARY", "employmentForm": "PERMANENT", "occupationCode": {"id": Y}}`)

**Global fields= rule (added PR #24/25):**
- NEVER use dot notation in `fields` param on ANY endpoint (causes 400 "Illegal fields filter: Fields filter contains '.'")
- Use parentheses for nested fields: `fields=id,voucher(id)` or `fields=account(id,number,name)`

**Ternary expression ban:**
- Gemini must NEVER generate ternary/JS expressions in placeholder values
- Always use `$responses.N.value.id` directly — never `$responses.N.values.length > 0 ? ... : 944619`

**Crash fixes (both in place):**
- Initial plan: `if isinstance(plan, list): plan = {"calls": plan}`
- Repair plan: `if isinstance(repair_plan, list): repair_plan = {"calls": repair_plan}`

---

## 7. VALIDATOR REQUEST FORMAT

```json
{
  "prompt": "Opprett en ansatt med navn Ola Nordmann, epost ola@example.com",
  "files": null,
  "tripletex_credentials": {
    "base_url": "https://tx-proxy-jwanbnu3pq-lz.a.run.app/v2",
    "session_token": "eyJ..."
  }
}
```

- Prompts can be in **any language** (Norwegian, English, Nynorsk, Spanish, German, French, Portuguese, etc.)
- Task types: 30 total across 3 tiers; Tier 3 live since March 21 ~11:00 CET

---

## 8. SCORING CONTEXT

- **Competition ends:** Sunday March 22 15:00 CET (~16 hours remaining as of Saturday 23:00)
- **Our score:** 23.3 Task 1 points, rank #218 overall (as of ~22:00 CET)
- **Score is sum of best per task type** — each unique task type solved is a new opportunity
- **30 unique task types** total across Tier 1/2/3
- **28 task types seen** in our submissions so far (see PROGRESS.md for full table)
- **2 task types still unseen** — need more submissions to discover
- Top score ~44 points (websecured.io), T1=15.5, T2=28.4

---

## 9. FAILURE TRIAGE WORKFLOW

### Step 1 — Pull logs after a validator run
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tripletex-agent" --limit=200 --format="value(textPayload)" --freshness=10m
```

### Step 2 — Identify the task type and failing call
Look for:
```
PROMPT: <task text>
CALL N ERROR 422 | {"validationMessages": [{"field": "X", "message": "Y"}]}
```

### Step 3 — Fix the planning prompt in main.py
Edit `build_llm_prompt()` in `task1-Tripletex/main.py`

### Step 4 — Commit, push (on Mac), then deploy (in Cloud Shell)
```bash
# On Mac (commit and push — always a new branch + PR, never push to main for code changes)
cd /Users/kenneth/git/annet/nmiai/nm-ai-2026
git checkout -b fix/task1-<description>
git add task1-Tripletex/main.py task1-Tripletex/PROGRESS.md task1-Tripletex/AGENT.md
git commit -m "fix(task1): <description>"
git push -u origin fix/task1-<description>
```
```bash
# In Cloud Shell (pull and deploy — after PR is merged)
cd ~/nm-ai-2026-1 && git pull
```
```bash
cd ~/nm-ai-2026-1/task1-Tripletex && gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --allow-unauthenticated
```

---

## 10. IMPORTANT NOTES FOR AI ASSISTANT

- **Deploy directory is `~/nm-ai-2026-1`** — NOT `~/nm-ai-2026`. Using wrong directory = stale code deployed.
- **Deploy is done from Cloud Shell** (not VS Code terminal) due to IAM permissions
- **Port 8080 is taken by JupyterLab** on the Workbench VM — use 8082 for local testing
- **`lsof` is not available** on this VM — use `fuser -k PORT/tcp` to kill processes
- **Auth uses GCP service account (metadata server)** — LLM calls only work in Cloud Run, not locally
- **Only add endpoints to prompt if verified** — do NOT add speculative endpoints. Check logs or API spec first.
- **PROGRESS.md must stay updated** — add new task types as they appear in logs
- **main.py must start with `from fastapi`** — if it starts with `cat >` or `EOF`, the file is corrupted
- **git push is needed before deploy** — always push first from Mac, then pull in Cloud Shell
- **Always create a new branch + PR** for code changes — never push code directly to main
- **AGENT.md/PROGRESS.md-only changes** can go directly to main branch without a PR
- **Give PR link + deploy commands + submit URL** at the end of every response that produces a PR

---

## 11. WHAT TO DO NEXT (as of March 21 ~23:00 CET)

### Confirm pending PRs
1. **PR #26 (bank return)** — not yet confirmed in validator logs. Submit a bank return task to verify.
2. **PR #27 (employee sub-resources + tool_code ban)** — not yet confirmed. Submit an employee creation from PDF task to verify.

### Unfixable (don't waste time)
- Month-end closing (task #35x): all voucher accounts → 422 system-generated in validator. Getting 2/10 max (GET /ledger/account calls). Fundamentally broken in this env.
- Bank statement reconciliation (task #41): INT32_MAX + system-generated supplier voucher. No known fix.
- Supplier invoice via voucher (task #37): accounts 2400/2710 → system-generated.
- Ledger error correction (task #24): 403 on first call (expired token). Unfixable.

### Discover the 2 remaining task types
- Submit repeatedly until new task types appear in logs
- 28/30 seen — 2 more to discover

### Potential improvements if new tasks appear
- `POST /bank/reconciliation/match` or similar — unknown if it exists; only if bank reconciliation task is fixable
- `GET /project?name=X` for project lookup by name in timesheet flows
- Multiple employment entries if a task asks for multiple jobs on one employee
