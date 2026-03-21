# Progress Report: Tripletex AI Accounting Agent

## 1. Current state

A Hybrid Repair agent is deployed to Cloud Run. It uses a single LLM call to plan all Tripletex API calls upfront, executes them sequentially, and makes one corrective LLM call if any calls returned 422 validation errors or 409 revision conflicts. The agent has been through 8 PRs of iteration. All PRs are merged into main and deployed.

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
- BETA endpoint block: 5 confirmed 403-returning endpoints listed in prompt so Gemini never tries them

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
| `/order` | POST | Creates order with order lines; `deliveryDate` required; `isPrioritizeAmountsIncludingVat` controls VAT field |
| `/order/{id}/:invoice` | PUT (action) | Converts order to invoice; `invoiceDate` required query param; `sendToCustomer=false` default |
| `/invoice` | GET, POST | POST alternative to action endpoint; `sendToCustomer=false` query param default |
| `/invoice/{id}/:payment` | PUT (action) | Registers payment; all params are **query params** — `paymentDate`, `paymentTypeId`, `paidAmount` required |
| `/invoice/{id}/:createCreditNote` | PUT (action) | Issues credit note; all params are **query params** — `date` required, `sendToCustomer=false` default |
| `/product` | POST | `name` required; optional price fields |
| `/travelExpense` | GET, POST, PUT, DELETE | PUT requires `version` field from GET response; `title` field (not `description`); dates in `travelDetails` |
| `/ledger/account` | GET | Look up account IDs by account number |
| `/ledger/voucher` | GET, POST, DELETE | POST creates voucher with account entries |
| `/ledger/posting` | GET | Query ledger postings by date range |

**Key correctness notes confirmed from sandbox testing and OpenAPI spec:**
- `PUT /invoice/{id}/:payment` and `PUT /invoice/{id}/:createCreditNote` take **only query parameters** — no request body. Sending a JSON body does nothing.
- `PUT /order/{id}/:invoice` is the canonical way to invoice a single order. It also takes only query params.
- `sendToCustomer` defaults to sending — always explicitly pass `sendToCustomer=false` unless the prompt says to send.
- VAT: if the Order has `isPrioritizeAmountsIncludingVat=true`, use `unitPriceIncludingVatCurrency` on order lines. Otherwise use `unitPriceExcludingVatCurrency`.
- `POST /order` requires `deliveryDate` — set it equal to `orderDate` by default (confirmed via sandbox 422).
- `POST /travelExpense` uses `title` (not `description`), and dates go inside `travelDetails.departureDate`/`returnDate`, not at top level (confirmed via sandbox 422).
- `GET /order` requires `orderDateFrom` and `orderDateTo` — cannot list orders without date range.
- `GET /invoice` also requires date range params.

## 4. Smoke test results (PR #8, 2026-03-20)

Tested against deployed agent with sandbox credentials:

| Task | Result | Notes |
|---|---|---|
| Create employee (Ola Nordmann, ola@example.com) | ✅ Pass | Employee created with correct name and email |
| Delete travel expense | ✅ Pass | Agent correctly GET'd and DELETE'd the expense |
| Create order | ❌ → ✅ Fixed in PR #8 | Was failing with 422: missing `deliveryDate` |
| Create travel expense | ❌ → ✅ Fixed in PR #8 | Was failing with 422: wrong field names in prompt |
| Order → invoice | ⚠️ Untestable in sandbox | Sandbox company has no bank account configured — 422 from Tripletex. Expected to work in validator env. |
| Register payment / credit note | ⚠️ Untestable in sandbox | Depends on invoice creation — same sandbox limitation. |

## 5. Validator task types seen (live, 2026-03-21)

Note on T1/T2: the leaderboard columns T1/T2/T3 are the three competition tasks (Tripletex, NorgesGruppen, Astar Island) — not sub-tiers within Tripletex. "Tier" below refers to internal difficulty (Tier 1 = simple CRUD, Tier 2 = multi-step/action endpoints, Tier 3 = ledger/complex).

| # | Prompt (language) | Result | Points | Tier | Root cause of failure |
|---|---|---|---|---|---|
| 1 | Credit note for Luna SL — "Almacenamiento en la nube" 31750 NOK (Spanish) | ✅ 5/5 | 8/8 | 2 | — |
| 2 | Create and send invoice to Fjelltopp AS, 42600 NOK, Nettverksteneste (Nynorsk) | ❌ 0/5 | 0/7 | 2 | Bank account 422 on `PUT /order/:invoice` — validator env issue |
| 3 | Set fixed price 429500 NOK on project "ERP-implementering" for Elvdal AS, invoice 33% (Nynorsk) | ⚠️ 1/4 | 2/8 | 3 | Bank account 422 on invoice; project fixed-price = BETA (403) |
| 4 | Register payment on Brattli AS invoice, 31300 NOK "Konsulenttimer" (Norwegian) | ⚠️ 1/2 | 2/7 | 2 | GET /invoice missing `invoiceDateFrom`/`invoiceDateTo` → 422 → unresolved placeholder → 404 on payment |
| 5 | Reverse bank return — Lysgård AS, 15600 NOK "Konsulenttimer" → reinstate invoice (Norwegian) | ⚠️ 1/3 | 2/8 | 2 | Same GET /invoice date params missing; repair used `"path"` instead of `"endpoint"` |
| 6 | Create order + invoice + payment for Waldstein GmbH, Netzwerkdienst + Beratungsstunden (German) | ⚠️ 3/5 | 4/8 | 2 | Invoice creation worked ✅; payment 404 because `paidAmount` placeholder not resolved in params (bug fixed PR #12) |
| 7 | Create project "Intégration Montagne" for Montagne SARL, PM Nathan Martin (French) | ✅ 7/7 | 8/8 | 1 | — |
| 8 | Create order + invoice + payment for Río Verde SL, 2 products (Spanish) | ⚠️ 3/4 | 4/8 | 2 | Payment 404 — invoice id 2147557274 > INT32_MAX, may overflow in proxy; paidAmount was hardcoded 63000.0 (correct) |
| 9 | Create customer Sonnental GmbH with address Solveien 21 Tromsø (German) | ❌ 0/1 | 0/8 | 1 | `POST /customer` address: tried `visitingAddress` (nested) and `visitingAddressLine1` (flat), both 422. Correct field: `postalAddress` (fixed PR #13) |
| 10 | Create invoice for Havbris AS, 3 lines: 25%/15%/0% VAT (Norwegian) | ❌ 0/8 | 0/8 | 2 | Mixed VAT rates — vatType id=3 invalid for this company; Gemini guessed wrong IDs. Fix: GET /vat/type first (PR #14) |
| 11 | Log 34 hours for Charlotte Williams on "Analyse" in "Security Audit", invoice Windmill Ltd (English) | ❌ 0/8 | 0/8 | 2 | Used wrong endpoint `/timesheet` (correct: `/timesheet/entry`); used `GET /product` for activity (correct: `GET /activity`); tried `POST /invoice/fromTimesheet` (405). Fixed PR #14 |
| 12 | Create departments "Drift", "Logistikk", "IT" (Portuguese) | ✅ 7/7 | 8/8 | 1 | — |
| 13 | Create and SEND invoice to Stormberg AS, 31250 NOK, Opplæring (Norwegian) | ❌ 0/7 | 0/8 | 2 | Bank account 422 on `PUT /order/:invoice` — validator env issue |
| 14 | Invoice Sierra SL: 3 lines, 25%/15%/0% VAT (Spanish) | ❌ 0/8 | 0/8 | 2 | `GET /vat/type` → 404 (doesn't exist); Gemini used JSONPath `[?(@.percentage==25.0)]` which is unsupported → literal string → 422. Fixed PR #15: hardcode IDs 3/5/omit, block JSONPath |
| 15 | Travel expense for Pablo Rodríguez "Conferencia Ålesund", 5 days per diems + flight + taxi (Spanish) | ⚠️ 2/8 | 2/8 | 2 | Header created ✓; missed individual cost lines (flight 2750, taxi 700). Fixed PR #16: add POST /travelExpense/cost |
| 16 | Set fixed price 324900 NOK on project "Migração para nuvem", invoice 50% milestone, PM Tiago Santos (Portuguese) | ❌ 0/8 | 0/8 | 3 | Gemini returned raw JSON array `[...]` → crash `AttributeError: list has no .get`. Fixed PR #16: wrap list in dict |
| 17 | Invoice Bergwerk GmbH: 3 lines, 25%/15%/0% VAT (German) | ❌ 0/8 | 0/8 | 2 | Order created ✓ (vatType fix working); invoice 422 bank account env issue |
| 18 | Supplier invoice INV-2026-4811 from Montanha Lda 33200 NOK incl. VAT, account 7300 (Portuguese) | ❌ 0/8 | 0/8 | 2 | `POST /supplier/invoice` → 405; correct endpoint is `POST /supplierInvoice`. Fixed PR #16 |

**Patterns observed:**
- Credit notes on existing invoices → works perfectly ✅
- Create project → works perfectly ✅
- Creating new invoices → sometimes fails with bank account 422 (validator env), sometimes works (task #6, #8)
- `GET /invoice` always requires `invoiceDateFrom` + `invoiceDateTo` — Gemini keeps omitting them → fixed in PR #12
- `params` placeholders (e.g. `paidAmount: "$responses.N.value.amountCurrency"`) were never resolved → fixed in PR #12
- Repair pass using `"path"` or `"url"` instead of `"endpoint"` → fixed in PR #11
- `POST /customer` address fields: `postalAddress`/`physicalAddress` (not `visitingAddress`) → fixed in PR #13
- Order→invoice→payment: paidAmount should use `$responses.N.value.amountCurrency` placeholder → fixed in PR #13

## 6. What still needs to be done

1. **Merge PR #11 and redeploy** — fixes `"path"` vs `"endpoint"` in repair output
2. **Keep submitting** — hit as many of the 30 task types as possible; each new type is a scoring opportunity
3. **Prompt tuning from new logs** — update this table as new task types come in and fix any new failure patterns

## 6. Key technical details

- **Project ID:** `ai-nm26osl-1730`
- **Cloud Run region:** `europe-north1`
- **Cloud Run service:** `tripletex-agent`
- **Model:** `gemini-2.5-flash` via Vertex AI global endpoint (service account auth, no API key needed)
- **Gemini JSON mode:** enabled (`responseMimeType: application/json`) — constrains output to valid JSON

## 7. How to run locally

```bash
# On the Workbench VM (port 8082 — port 8080 is taken by JupyterLab)
cd ~/nm-ai-2026/task1-Tripletex && uvicorn main:app --host 0.0.0.0 --port 8082
```

Note: the GCP metadata server is not available locally, so `get_access_token()` will fail and LLM calls will not work. Use the deployed Cloud Run instance for real end-to-end testing.

## 8. How to run unit tests

```bash
cd ~/nm-ai-2026/task1-Tripletex
pip install -r requirements.txt
pytest tests/test_agent.py -v
```

## 9. Sandbox smoke test — deployed agent

```bash
# Employee create
curl -X POST https://tripletex-agent-997219197351.europe-north1.run.app/solve \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Opprett en ansatt med navn Ola Nordmann, epost ola@example.com",
    "tripletex_credentials": {
      "base_url": "https://kkpqfuj-amager.tripletex.dev/v2",
      "session_token": "eyJ0b2tlbklkIjoyMTQ3NjQ1MzAzLCJ0b2tlbiI6ImI3YzQ3Y2E0LTM0ZDgtNGYyZi1iMGU2LWZiMDc1NmJjODBhNyJ9"
    }
  }'
```
