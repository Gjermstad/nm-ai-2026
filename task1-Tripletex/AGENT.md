# AGENT.md — Task 1: Tripletex AI Accounting Agent
> NM i AI 2026 — Solo competitor, frontend student (Kristiania, 6th semester)
> Last updated: 2026-03-21 ~21:00 CET
> Status: PR #22 deployed (bank account fix confirmed ✅). PR #24 in progress — product number, fields dot notation, voucher invalid fields.

---

## 0. PREFERENCES
- Do not merge bash commands together if they are to different things. If you are to commit and also deploy, make it two steps with separate code boxes.
- When coding keep variable names and code readable for humans. Use rather full words than shortening them.
- Comment effectively so it is possible for a human to read what is going on in the code.
- Every time you have made changes, update AGENT.md and PROGRESS.md so they don't fall behind and get outdated.

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
cd ~/nm-ai-2026-1/task1-Tripletex && gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --no-allow-unauthenticated
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

### Endpoint status (as of PR #18)

**Verified working (seen 201/200/204 in validator logs):**
- `GET /customer`, `GET /employee`, `GET /project`, `GET /department`, `GET /activity`
- `POST /customer`, `POST /employee`, `POST /department`, `POST /project`, `POST /order`, `POST /product`
- `POST /supplier` (added PR #18; not yet confirmed in logs — endpoint verified in API spec)
- `POST /travelExpense`, `PUT /travelExpense/{id}`, `DELETE /travelExpense/{id}`
- `PUT /order/{id}/:invoice`, `PUT /invoice/{id}/:payment`, `PUT /invoice/{id}/:createCreditNote`
- `GET /invoice` (requires `invoiceDateFrom`/`invoiceDateTo`)
- `GET /ledger/account`, `POST /ledger/voucher` (body uses `"postings"` array, NOT `"vouchers"`)
- `GET /supplier`

**Verified NOT working:**
- `GET /vat/type` → 404 (endpoint does not exist)
- `POST /supplier/invoice` → 405
- `POST /invoice/fromTimesheet` → 405
- `POST /timesheet` (without `/entry`) → 404
- `POST /timeSheet` (capital S) → 404

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

### Known validator environment issues (unfixable)
- **INT32_MAX overflow**: Invoice IDs > 2,147,483,647 cause 404 on `PUT /invoice/{id}/:payment`. This is a bug in the validator proxy routing.
- **Missing bank account**: Some validator Tripletex instances don't have a bank account configured → `PUT /order/:invoice` fails with 422. Affects invoice creation tasks inconsistently.

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
| Max API calls | 12 | Hard cap for efficiency |
| Timeout budget | 255s deadline | 300s − 45s buffer |
| Gemini JSON mode | `responseMimeType: application/json` | Eliminates most parse failures |
| Temperature | 0.1 | Deterministic JSON output |
| Max output tokens | 8192 | Allows full multi-step plans |
| 204 responses | Append `{}` | DELETE and action endpoints return no body |
| List response wrap | `if isinstance(plan, list): plan = {"calls": plan}` | Gemini sometimes returns raw array |

---

## 6. CURRENT CODE STATE (post PR #18)

### What PR #18 added (merged, NOT YET DEPLOYED)
1. **POST /employee**: Added NOTE — do NOT include `startDate` or `employmentDate` in body (422); they don't exist on Employee object
2. **POST /supplier**: Added full section with required/optional fields, `isSupplier: true`
3. **POST /customer**: Added `organizationNumber` to optional fields with note to always include if provided

### Placeholder resolution
Supports only:
- `$responses.N.value.FIELD` — single-item responses (POST/PUT)
- `$responses.N.values.INDEX.FIELD` — list responses (GET with count > 1)

**NOT supported:** JSONPath filter expressions like `$responses.N.values[?(@.field==value)].id`

### Crash fixes (both in place)
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
- Task types: ~30 total across 3 tiers; Tier 3 live since March 21 ~11:00 CET

---

## 8. SCORING CONTEXT

- **Competition ends:** Sunday March 22 15:00 CET (~22 hours remaining as of Saturday 17:00)
- **Leaderboard (last known):** Top score ~44 points (websecured.io), T1=15.5, T2=28.4
- **Score is sum of best per task type** — each unique task type solved is a new opportunity
- **30 unique task types** total across Tier 1/2/3
- **21 task types seen** in our submissions so far (see PROGRESS.md)
- Tier 3 tasks now included — harder, ledger/complex workflows

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
# On Mac (commit and push)
cd /Users/kenneth/git/annet/nmiai/nm-ai-2026
git add task1-Tripletex/main.py task1-Tripletex/PROGRESS.md task1-Tripletex/AGENT.md
git commit -m "fix(task1): <description>"
git push
```
```bash
# In Cloud Shell (pull and deploy)
cd ~/nm-ai-2026-1 && git pull
```
```bash
cd ~/nm-ai-2026-1/task1-Tripletex && gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --no-allow-unauthenticated
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

---

## 11. WHAT TO DO NEXT (as of March 21 ~18:00 CET)

### Immediate
1. **Commit and push PR #19** — fixes critical `"vouchers"` → `"postings"` bug in `POST /ledger/voucher`; increases MAX_CALLS 12→16
2. **Redeploy** from `~/nm-ai-2026-1` after push
3. **Submit repeatedly** — confirm year-end depreciation task now works

### Confirmed new task types (Tier 3, seen today)
- #23: Year-end closing / depreciation booking (årsoppgjør) — multiple vouchers per asset
- #24: Ledger error correction (find + fix 4 errors) — always 403 on first call (env issue?)
- #25: Travel expense with per diems + flight + taxi — same as #15, BETA cost lines

### Known fixes pending
4. **Employee + employment sub-resource** — if "set start date" tasks come back
5. **GET /project with customer filter** — for project lookup in timesheet flows
6. **POST /timesheet/entry** — not yet confirmed in validator logs
