# AGENT.md — Task 1: Tripletex AI Accounting Agent
> NM i AI 2026 — Solo competitor, frontend student (Kristiania, 6th semester)
> Last updated: 2026-03-20 ~01:30 CET
> Status: Hybrid Repair agent deployed (single-shot + 422 repair pass). Vertex AI gemini-2.5-flash.

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

### Cloud Run Service
- **URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`
- **Service name:** `tripletex-agent`
- **Memory:** 2Gi
- **Timeout:** 300s (important — complex tasks need multiple LLM calls)
- **Min instances:** 1 during active competition windows (prevents cold starts)

### Deploy Command
```bash
cd ~/nm-ai-2026/task1-Tripletex && gcloud run deploy tripletex-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --min-instances 1
```

### GitHub Repo
- `https://github.com/Gjermstad/nm-ai-2026`
- Working directory: `~/nm-ai-2026/task1-Tripletex/`
- Always `git pull` before deploying

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

### Local testing note
On the Workbench VM, the metadata server is not available. To test locally you must either:
- Use a service account key and `GOOGLE_APPLICATION_CREDENTIALS`, or
- Test via a deployed Cloud Run instance

---

## 4. TRIPLETEX API

### Sandbox
- **Base URL:** `https://kkpqfuj-amager.tripletex.dev/v2`
- **Sandbox token:** `eyJ0b2tlbklkIjoyMTQ3NjQ1MzAzLCJ0b2tlbiI6ImI3YzQ3Y2E0LTM0ZDgtNGYyZi1iMGU2LWZiMDc1NmJjODBhNyJ9`
- Use for local testing only. **Never hardcode this in deployed code.**

### Validator proxy
- **Base URL sent by validator:** something like `https://tx-proxy.ainm.no/v2`
- This URL is only resolvable from within the validator's network
- The agent receives `base_url` and `session_token` in the request body and MUST use them
- Testing with `tx-proxy.ainm.no` locally will always fail with DNS error — this is expected

### Authentication
- Basic auth: username `"0"`, password = `session_token`
- `auth=("0", session_token)` in Python requests

### Key endpoints discovered
```
GET  /department          → Always needed first for employee creation (get dept id)
GET  /employee            → List employees (for project manager, travel expense)
GET  /customer            → Search customers
GET  /travelExpense       → List travel expenses
POST /employee            → Create employee
POST /customer            → Create customer
POST /product             → Create product
POST /order               → Create order (prerequisite for invoice)
POST /invoice             → Create invoice
POST /department          → Create department
POST /project             → Create project
POST /travelExpense       → Create travel expense
DELETE /travelExpense/{id}→ Delete travel expense
PUT  /customer/{id}       → Update customer
PUT  /employee/{id}       → Update employee (requires version field from GET)
```

### Critical field requirements (learned from failures)
```
POST /employee REQUIRED: firstName, lastName, userType, email, department.id
  - userType enum: "STANDARD" | "EXTENDED" | "NO_ACCESS"
  - "EXTENDED" = administrator/admin/kontoadministrator
  - email: use from prompt, or generate as firstname.lastname@example.com
  - department.id: ALWAYS get from GET /department first

POST /customer REQUIRED: name

POST /order REQUIRED: customer.id, orderDate ("YYYY-MM-DD")

POST /invoice REQUIRED: invoiceDate, invoiceDueDate, orders: [{id: ORDER_ID}]

POST /project REQUIRED: name, startDate, projectManager.id

PUT /employee: must include version field from GET response
```

---

## 5. AGENT ARCHITECTURE

### Current architecture: Hybrid Repair (single-shot + one 422 repair pass)

```
Prompt → Gemini → full call plan → execute all → if 422 errors → Gemini repair → execute corrections → done
```

**Why Hybrid Repair instead of full ReAct:**
- Full ReAct: one LLM call per API call — high latency, risks hitting 300s timeout on complex tasks
- Single-shot only: no recovery from validation errors
- Hybrid Repair: one planning call + one optional correction call; handles the most common failure mode (422 missing/wrong fields) without multiple round-trips

**Parse failure retry:** If the LLM output is not valid JSON, one corrective prompt is sent before giving up.

### Key implementation decisions
| Decision | Choice | Why |
|---|---|---|
| Repair trigger | 422 only | 404/401/400 are not fixable by re-prompting; only 422 validation errors are |
| Repair guard | >40s remaining | Avoids triggering repair when there's no time left |
| Max API calls | 12 | Hard cap for efficiency bonus; complex tasks need ~5–8 calls |
| Timeout budget | 255s deadline | 300s limit − 45s buffer; checked before every LLM and API call |
| Temperature | 0.1 | Low temperature = more consistent JSON output |
| Max output tokens | 8192 | Allows full multi-step plans in one response |
| JSON parsing | regex + json.loads + DOTALL fallback | Gemini sometimes wraps output in markdown fences |
| 204 responses | Append `{}` | DELETE and some PUTs return no body |
| 403 response | Abort immediately | Invalid/expired token — no point continuing |

---

## 6. FAILURES AND LESSONS LEARNED

### Failure 1: Vertex AI model not found (first submission)
- **Error:** `404 Publisher Model gemini-2.0-flash-001 was not found`
- **Cause:** Model not available in `europe-west4` project
- **Fix:** Switched to Google AI Studio REST API with API key

### Failure 2: SyntaxError in deployed container (`cat > ... << 'EOF'`)
- **Error:** `SyntaxError: invalid syntax` at line 1 of `main.py`
- **Cause:** Someone (Claude/Gemini) generated a shell command and it was accidentally written into `main.py` instead of being run as a shell command
- **Fix:** Rewrote `main.py` properly and committed to git
- **Lesson:** Always verify `cat main.py | head -5` before deploying. The file must start with `from fastapi import...`

### Failure 3: EOF artifact in main.py
- **Error:** `NameError: name 'EOF' is not defined` at line 215
- **Cause:** The heredoc `EOF` marker ended up inside the Python file
- **Fix:** Cleaned up with `str_replace`
- **Lesson:** Use VS Code editor to write files, not shell heredocs

### Failure 4: Port 8080 conflicts during local testing
- **Cause:** JupyterLab runs on port 8080 on the Workbench VM
- **Fix:** Use port 8082 for local testing (`uvicorn main:app --port 8082`)
- **Kill command:** `fuser -k 8080/tcp` (lsof not available on this VM)

### Failure 5: 0 score despite agent running correctly
- **Cause:** The 00:02 AM run that succeeded was a manual test using sandbox credentials. The validator's submission at 01:05 AM hit the first broken version of the app.
- **Lesson:** After any code fix, always redeploy before submitting

### Failure 6: Validator logs invisible
- **Cause:** Cloud Run scales to multiple instances; validator may hit a different instance than what `gcloud run services logs read` shows
- **Fix:** Use `gcloud logging read` with resource filter for full log aggregation
- **Better fix:** Add `--min-instances 1` to keep one warm instance and consolidate logs

---

## 7. VALIDATOR REQUEST FORMAT

The validator POSTs to `/solve` with this structure:
```json
{
  "prompt": "Opprett en ansatt med navn Ola Nordmann, epost ola@example.com",
  "files": null,
  "tripletex_credentials": {
    "base_url": "https://tx-proxy.ainm.no/v2",
    "session_token": "eyJ..."
  }
}
```

- Prompts can be in **any language** (Norwegian, English, Nynorsk, Spanish, etc.)
- Tasks seen so far: create employee (3 checks), complex task (7 checks)
- Scoring: each check = one verification of Tripletex state after agent returns
- **Checks failed = 0 score**, need ALL checks to pass for full points

---

## 8. SCORING CONTEXT

- Top score on leaderboard: 13.44
- Our best score: 0 (all submissions failed due to bugs)
- 2/30 unique task types encountered
- 30 unique task types exist total
- Score is sum of best per task type — so each unique task type is a new opportunity

---

## 9. CURRENT main.py OVERVIEW

The current agent (`main.py`) does:
1. Receives `/solve` POST request; sets a 255s deadline
2. Decodes any attached files (PDFs extracted via `pypdf`, others noted by name)
3. Builds a single planning prompt with task, date, file context, and full API reference
4. Calls Gemini once → parses full call plan (with one parse-failure retry)
5. Executes all API calls sequentially via `execute_calls()`; stops on 403 or deadline/call-cap
6. If any calls returned 422, calls Gemini once more with error context → executes corrected calls
7. Returns `{"status": "completed"}`

### What the planning prompt tells Gemini
- All endpoint signatures with required fields (POST + PUT for employee, customer, travelExpense; product, project, order, invoice, department)
- Advanced patterns: invoice payment, credit note, ledger voucher
- Placeholder syntax for chaining responses (`$responses.N.value.FIELD`, `$responses.N.values.INDEX.FIELD`)
- Rules (always GET /department first for employees, always include version for PUT, etc.)
- Output format (single JSON object with `calls` array)

---

## 10. WHAT TO IMPROVE NEXT

### High priority
1. **Sandbox smoke test** — test employee create, invoice, travel expense delete against sandbox to confirm scores
2. **Add `--min-instances 1`** — prevents cold starts during active judging windows (add to deploy command)
3. **Submit and observe** — gather logs from real validator runs to see which task types are being sent and which checks fail

### Medium priority
4. **Parallel submissions** — submit multiple times to hit more unique task types and build score across all 30
5. **Prompt tuning from failures** — read validator logs, identify which fields are wrong, tighten prompt for those task types
6. **Gemini JSON mode** — use `responseMimeType: "application/json"` in generationConfig to guarantee valid JSON output and eliminate parse failures

### Low priority (nice to have)
7. **Tool calling** — use Gemini's native function calling instead of parsing JSON from text
8. **Structured output schema** — pass a JSON schema to Gemini to constrain the calls array format

---

## 11. QUICK REFERENCE COMMANDS

```bash
# SSH to VM
ssh gcp-nm-ai

# Pull latest code
cd ~/nm-ai-2026 && git pull

# Test locally (metadata server unavailable — LLM calls will fail; use for non-LLM testing only)
cd ~/nm-ai-2026/task1-Tripletex && uvicorn main:app --host 0.0.0.0 --port 8082

# Test curl (sandbox)
curl -X POST http://localhost:8082/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en ansatt med navn Ola Nordmann, epost ola@example.com",
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "eyJ0b2tlbklkIjoyMTQ3NjQ1MzAzLCJ0b2tlbiI6ImI3YzQ3Y2E0LTM0ZDgtNGYyZi1iMGU2LWZiMDc1NmJjODBhNyJ9"
    }
  }'

# Deploy to Cloud Run (from Cloud Shell, not VS Code terminal)
cd ~/nm-ai-2026/task1-Tripletex && gcloud run deploy tripletex-agent \
  --source . \
  --region europe-north1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --timeout 300 \
  --min-instances 1

# Check logs
gcloud run services logs read tripletex-agent --region europe-north1 --limit 100 --format="text"

# Full log aggregation (all instances)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=tripletex-agent" \
  --limit=100 --format="value(textPayload)" --freshness=30m

# Commit and push
cd ~/nm-ai-2026 && git add -A && git commit -m "your message" && git push
```

---

## 12. IMPORTANT NOTES FOR NEW AI ASSISTANT

- **Deploy is done from Cloud Shell** (not VS Code terminal) due to IAM permissions
- **Port 8080 is taken by JupyterLab** on the Workbench VM — use 8082 for local testing
- **`lsof` is not available** on this VM — use `fuser -k PORT/tcp` to kill processes
- **`pkill -f uvicorn` kills itself** when run as a background job — start uvicorn in foreground in one terminal, test in another
- **Auth uses GCP service account (metadata server)** — LLM calls only work in Cloud Run, not locally on the VM
- **Validator proxy URL is not resolvable from our Cloud Run** — DNS errors on `tx-proxy.ainm.no` from our side are expected during local testing; the validator's network can resolve it
- **git push is needed before deploy** — `gcloud run deploy --source .` builds from local files, but always push first to keep repo in sync
- **main.py must start with `from fastapi`** — if it starts with `cat >` or ends with `EOF`, the file is corrupted and needs to be rewritten
