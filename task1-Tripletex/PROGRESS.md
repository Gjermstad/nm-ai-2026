# Progress Report: Tripletex AI Accounting Agent

## 1. Current state

A Hybrid Repair agent is deployed to Cloud Run. It uses a single LLM call to plan all API calls upfront, executes them, and makes one corrective LLM call if any returned 422 validation errors.

**Deployed URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`

## 2. What is implemented

- `/solve` endpoint (FastAPI) accepting prompt, files, and Tripletex credentials
- Single-shot planner: Gemini 2.5 Flash (Vertex AI global endpoint) generates a full call plan
- Bounded repair pass: one corrective LLM call on 422 validation errors only
- File handling: base64 decode + PDF text extraction via `pypdf` (3000 char cap)
- Generalized placeholder resolver: `$responses.N.value.FIELD` and `$responses.N.values.INDEX.FIELD`
- Hardened JSON parsing: markdown fence stripping + `{...}` fallback + one parse-failure retry
- Timeout budgeting: 255s deadline, checked before every LLM and API call
- Hard cap of 12 total API calls for efficiency
- 403 early exit: abort on invalid/expired session token

## 3. Endpoints covered in the planning prompt

| Endpoint | Operations |
|---|---|
| `/employee` | GET, POST, PUT (with version) |
| `/customer` | GET, POST, PUT (with version) |
| `/department` | GET, POST |
| `/project` | POST |
| `/order` | POST |
| `/invoice` | POST, payment, credit note |
| `/product` | POST |
| `/travelExpense` | GET, POST, PUT (with version), DELETE |
| `/ledger/account` | GET (account lookup) |
| `/ledger/voucher` | POST |

## 4. What still needs to be done

- **Sandbox smoke test** — verify employee, invoice, travel expense flows score correctly
- **Add `--min-instances 1`** to deploy command to prevent cold starts during active judging
- **Submit and gather logs** — observe which task types are sent and which checks fail
- **Prompt tuning** — tighten field instructions based on real failure logs
- **Consider Gemini JSON mode** — `responseMimeType: "application/json"` to eliminate parse failures

## 5. Key technical details

- **Project ID:** `ai-nm26osl-1730`
- **Cloud Run region:** `europe-north1`
- **Model:** `gemini-2.5-flash` via Vertex AI global endpoint
- **Auth:** GCP service account (metadata server) — no API key needed

## 6. How to run locally

```bash
# On the Workbench VM (port 8082 — port 8080 is taken by JupyterLab)
cd ~/nm-ai-2026/task1-Tripletex && uvicorn main:app --host 0.0.0.0 --port 8082
```

Note: the metadata server is not available locally, so `get_access_token()` will fail. Use a deployed Cloud Run instance for real testing.

## 7. Sandbox test request

```bash
curl -X POST http://localhost:8082/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en ansatt med navn Ola Nordmann, epost ola@example.com",
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "eyJ0b2tlbklkIjoyMTQ3NjQ1MzAzLCJ0b2tlbiI6ImI3YzQ3Y2E0LTM0ZDgtNGYyZi1iMGU2LWZiMDc1NmJjODBhNyJ9"
    }
  }'
```
