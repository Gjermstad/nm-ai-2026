# Progress Report: Tripletex AI Accounting Agent

## 1. Current state

A Hybrid Repair agent is deployed to Cloud Run. It uses a single LLM call to plan all Tripletex API calls upfront, executes them sequentially, and makes one corrective LLM call if any calls returned 422 validation errors or 409 revision conflicts. The agent has been through five PRs of iteration and is now in a stable, competition-ready state.

**Deployed URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`

## 2. What is implemented

### Core architecture
- `/solve` endpoint (FastAPI) accepting prompt, files (PDF/image), and Tripletex credentials
- Single-shot planner: Gemini 2.5 Flash (Vertex AI global endpoint, `responseMimeType: application/json`) generates a full call plan in one LLM call
- Bounded repair pass: if any calls return 422 (validation error) or 409 (revision/version conflict), one corrective LLM call is made with full error context including field-level validation messages, HTTP status codes, and a plain-English hint per error type
- Parse failure retry: if the LLM output fails JSON parsing, one corrective prompt is sent before giving up
- File handling: base64 decode + PDF text extraction via `pypdf` (3000 char cap per file), fail-soft
- Generalized placeholder resolver: resolves `$responses.N.value.FIELD` and `$responses.N.values.INDEX.FIELD` for any field name and list index
- Timeout budgeting: 255s deadline tracked from request start, checked before every LLM call (needs 30s) and every API call (needs 5s)
- Hard cap of 12 total Tripletex API calls per request (efficiency protection)
- Optional inbound API key: `SOLVE_API_KEY` env var enables Bearer token auth on `/solve`; no-op when unset

### Error handling
- **403 Forbidden**: abort immediately — invalid/expired session token, no point continuing
- **429 Too Many Requests**: abort immediately — rate limit hit, subsequent calls would also fail
- **409 Conflict (code 8000, Revision Exception)**: collected for repair pass — stale `version` field on PUT, LLM is told to re-GET and use correct version
- **422 Unprocessable Entity**: collected for repair pass — missing or malformed fields, LLM is told to fix based on `validationMessages[].field` and `validationMessages[].message`
- **Malformed call objects**: skipped with warning if `method` or `endpoint` is missing or non-string
- **204 No Content**: treated as success (DELETE and some action endpoints return no body)

### Unit tests (14 tests, all passing)
Tests cover: placeholder resolution (all field types and edge cases), JSON extraction (clean, fenced, preamble, invalid), executor malformed call skip, call cap enforcement, 403/429 abort, 422/409 error collection.

## 3. Endpoints covered in the planning prompt

| Endpoint | Operations | Notes |
|---|---|---|
| `/employee` | GET, POST, PUT | PUT requires `version` field from GET response |
| `/customer` | GET, POST, PUT | PUT requires `version` field from GET response |
| `/department` | GET, POST | GET always done first before creating an employee |
| `/project` | POST | Requires `projectManager.id` from GET /employee |
| `/order` | POST | Creates order with order lines; `isPrioritizeAmountsIncludingVat` controls VAT field |
| `/order/{id}/:invoice` | PUT (action) | Converts order to invoice; `invoiceDate` required query param; `sendToCustomer=false` default |
| `/invoice` | GET, POST | POST alternative to action endpoint; `sendToCustomer=false` query param default |
| `/invoice/{id}/:payment` | PUT (action) | Registers payment; all params are **query params** — `paymentDate`, `paymentTypeId`, `paidAmount` required |
| `/invoice/{id}/:createCreditNote` | PUT (action) | Issues credit note; all params are **query params** — `date` required, `sendToCustomer=false` default |
| `/product` | POST | `name` required; optional price fields |
| `/travelExpense` | GET, POST, PUT, DELETE | PUT requires `version` field from GET response |
| `/ledger/account` | GET | Look up account IDs by account number |
| `/ledger/voucher` | GET, POST, DELETE | POST creates voucher with account entries |
| `/ledger/posting` | GET | Query ledger postings by date range |

**Key correctness notes confirmed from OpenAPI spec:**
- `PUT /invoice/{id}/:payment` and `PUT /invoice/{id}/:createCreditNote` take **only query parameters** — no request body. Sending a JSON body does nothing.
- `PUT /order/{id}/:invoice` is the canonical way to invoice a single order. It also takes only query params.
- `sendToCustomer` defaults to sending — always explicitly pass `sendToCustomer=false` unless the prompt says to send.
- VAT: if the Order has `isPrioritizeAmountsIncludingVat=true`, use `unitPriceIncludingVatCurrency` on order lines. Otherwise use `unitPriceExcludingVatCurrency`.

## 4. What still needs to be done

- **Sandbox smoke test** — run concrete end-to-end scenarios (employee create, order→invoice, invoice payment, credit note, travel expense delete) and record pass/fail evidence
- **Submit and gather logs** — observe which task types the validator sends and which checks fail, then tune prompt accordingly
- **Prompt tuning from validator logs** — once we have real failure data, tighten field instructions for the failing task types

## 5. Key technical details

- **Project ID:** `ai-nm26osl-1730`
- **Cloud Run region:** `europe-north1`
- **Cloud Run service:** `tripletex-agent`
- **Model:** `gemini-2.5-flash` via Vertex AI global endpoint (service account auth, no API key needed)
- **Gemini JSON mode:** enabled (`responseMimeType: application/json`) — constrains output to valid JSON

## 6. How to run locally

```bash
# On the Workbench VM (port 8082 — port 8080 is taken by JupyterLab)
cd ~/nm-ai-2026/task1-Tripletex && uvicorn main:app --host 0.0.0.0 --port 8082
```

Note: the GCP metadata server is not available locally, so `get_access_token()` will fail and LLM calls will not work. Use the deployed Cloud Run instance for real end-to-end testing.

## 7. How to run unit tests

```bash
cd ~/nm-ai-2026/task1-Tripletex
pip install -r requirements.txt
pytest tests/test_agent.py -v
```

## 8. Sandbox test request

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
