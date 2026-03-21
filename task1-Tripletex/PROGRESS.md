# Progress Report: Tripletex AI Accounting Agent

## 1. Current state (2026-03-21 ~18:00 CET)

A Hybrid Repair agent is deployed to Cloud Run. PR #18 deployed and confirmed working (task #21 ✅ 8/8). PR #19 in progress — fixes critical `"vouchers"` → `"postings"` bug in `POST /ledger/voucher`, increases MAX_CALLS to 16.

**Deployed URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`

**Tier 3 tasks** are live since ~11:00 CET March 21. These include harder accounting tasks (ledger, complex multi-step).

---

## 2. What is implemented

### Core architecture
- `/solve` endpoint (FastAPI) accepting prompt, files (PDF/image), and Tripletex credentials
- Single-shot planner: Gemini 2.5 Flash (Vertex AI global endpoint, `responseMimeType: application/json`) generates a full call plan in one LLM call
- Bounded repair pass: if any calls return 422 or 409, one corrective LLM call is made with full error context
- Parse failure retry: if the LLM output fails JSON parsing, one corrective prompt is sent before giving up
- File handling: base64 decode + PDF text extraction via `pypdf` (3000 char cap per file)
- Placeholder resolver: `$responses.N.value.FIELD` and `$responses.N.values.INDEX.FIELD`
- Timeout budgeting: 255s deadline, checked before every LLM and API call
- Hard cap of 12 total Tripletex API calls per request
- BETA endpoint block: confirmed 403 endpoints listed so Gemini never tries them
- List response wrap: `if isinstance(plan, list): plan = {"calls": plan}` — prevents crash when Gemini returns raw array

### What PR #18 fixed (merged, needs deploy)
1. **POST /employee**: Added explicit NOTE — do NOT include `startDate` or `employmentDate` (these don't exist on Employee object, cause 422)
2. **POST /supplier**: Added full endpoint section with required/optional fields and `isSupplier: true`
3. **POST /customer**: Added `organizationNumber` to optional fields with note to always include it if provided

---

## 3. Task types seen in validator (21 confirmed)

| # | Prompt summary (language) | Score | Tier | Root cause of failure / fix |
|---|---|---|---|---|
| 1 | Credit note for Luna SL — "Almacenamiento en la nube" 31750 NOK (Spanish) | ✅ 8/8 | 2 | — |
| 2 | Create and send invoice to Fjelltopp AS, 42600 NOK, Nettverksteneste (Nynorsk) | ❌ 0/7 | 2 | Bank account 422 on `PUT /order/:invoice` — validator env issue |
| 3 | Set fixed price 429500 NOK on project "ERP-implementering" for Elvdal AS, invoice 33% (Nynorsk) | ⚠️ 2/8 | 3 | Bank account 422 on invoice; fixed-price endpoint is BETA (403) |
| 4 | Register payment on Brattli AS invoice, 31300 NOK "Konsulenttimer" (Norwegian) | ⚠️ 2/7 | 2 | GET /invoice missing `invoiceDateFrom`/`invoiceDateTo` → 422 → unresolved placeholder → 404 payment. Fixed PR #12. |
| 5 | Reverse bank return — Lysgård AS, 15600 NOK "Konsulenttimer" → reinstate invoice (Norwegian) | ⚠️ 2/8 | 2 | Same GET /invoice date params; repair used `"path"` instead of `"endpoint"`. Fixed PR #11/#12. |
| 6 | Create order + invoice + payment for Waldstein GmbH, Netzwerkdienst + Beratungsstunden (German) | ⚠️ 4/8 | 2 | Invoice worked ✅; payment 404 — `paidAmount` placeholder not resolved in params. Fixed PR #12. |
| 7 | Create project "Intégration Montagne" for Montagne SARL, PM Nathan Martin (French) | ✅ 8/8 | 1 | — |
| 8 | Create order + invoice + payment for Río Verde SL, 2 products (Spanish) | ⚠️ 4/8 | 2 | Payment 404 — invoice ID 2147557274 > INT32_MAX; paidAmount hardcoded correctly. Unfixable (validator env). |
| 9 | Create customer Sonnental GmbH with address Solveien 21 Tromsø (German) | ❌ 0/8 | 1 | Wrong address fields (`visitingAddress`). Fixed PR #13: use `postalAddress`/`physicalAddress`. |
| 10 | Create invoice for Havbris AS, 3 lines: 25%/15%/0% VAT (Norwegian) | ❌ 0/8 | 2 | GET /vat/type → 404; Gemini used JSONPath filter → wrong vatType. Fixed PR #15: hardcode IDs 3/5/omit. |
| 11 | Log 34 hours for Charlotte Williams on "Analyse" in "Security Audit", invoice Windmill Ltd (English) | ❌ 0/8 | 2 | Wrong endpoint `/timesheet` (correct: `/timesheet/entry`); wrong activity lookup. Fixed PR #14. |
| 12 | Create departments "Drift", "Logistikk", "IT" (Portuguese) | ✅ 8/8 | 1 | — |
| 13 | Create and SEND invoice to Stormberg AS, 31250 NOK, Opplæring (Norwegian) | ❌ 0/8 | 2 | Bank account 422 — validator env issue |
| 14 | Invoice Sierra SL: 3 lines, 25%/15%/0% VAT (Spanish) | ❌ 0/8 | 2 | Same GET /vat/type → 404. Fixed PR #15. |
| 15 | Travel expense for Pablo Rodríguez "Conferencia Ålesund", per diems + flight + taxi (Spanish) | ⚠️ 2/8 | 2 | Header created ✓; individual costs BETA (POST /travelExpense/cost → 403). Fixed PR #17: note in prompt. |
| 16 | Fixed price 324900 NOK project "Migração para nuvem", invoice 50% milestone (Portuguese) | ❌ 0/8 | 3 | Gemini returned raw JSON array → crash `AttributeError`. Fixed PR #16: wrap list in dict. |
| 17 | Invoice Bergwerk GmbH: 3 lines, 25%/15%/0% VAT (German) | ❌ 0/8 | 2 | Order ✓ (vatType fix working); invoice 422 bank account env issue. |
| 18 | Supplier invoice INV-2026-4811 from Montanha Lda 33200 NOK, account 7300 (Portuguese) | ❌ 0/8 | 2 | `POST /supplier/invoice` → 405. Fixed PR #17: use POST /ledger/voucher for supplier invoices. |
| 19 | Create employee + set employment start date (Norwegian) | ❌ 0/8 | 1 | `startDate`/`employmentDate` not on Employee object → 422. Fixed PR #18: NOTE in prompt. |
| 20 | Create supplier (leverandør) (Norwegian/German) | ❌ 0/8 | 1 | Gemini returned `{"calls": []}` — POST /supplier not in prompt. Fixed PR #18: added endpoint. |
| 21 | Create customer with organizationNumber (Norwegian) | ❌ 0/8 | 1 | Customer created (201) but `organizationNumber` missing from body. Fixed PR #18: added to optional fields. |
| 22 | Unknown (from submit #35 — logs not captured) | ❌ | ? | — |
| 23 | Year-end closing / depreciation booking — årsoppgjør (Nynorsk) | ❌ 0/10 | 3 | `"vouchers"` field bug → all POST /ledger/voucher 422. Fixed PR #19: use `"postings"`. Also account 1209 not in validator env. |
| 24 | Ledger error correction — find and fix 4 accounting errors (Portuguese) | ❌ 0/? | 3 | 403 on first call (expired session token — validator env issue). Unfixable. |
| 25 | Travel expense with per diems + flight + taxi (German) | ⚠️ 2/8 | 2 | Same as #15: header ✅, POST /travelExpense/cost BETA → 403. Unfixable. |

**Patterns observed:**
- Credit notes on existing invoices → works ✅
- Create project + assign PM → works ✅
- Create departments → works ✅
- New invoice creation → intermittently fails with bank account 422 (validator env), unfixable
- Payment 404 for invoice IDs > INT32_MAX → unfixable (validator proxy overflow)
- `GET /invoice` always requires `invoiceDateFrom` + `invoiceDateTo` — enforced in prompt (PR #12)
- `POST /customer` address: must use `postalAddress`/`physicalAddress` (fixed PR #13)
- Mixed VAT rates: hardcode IDs 3/5/omit — do NOT call GET /vat/type (fixed PR #15)
- `POST /travelExpense/cost` is BETA (fixed PR #17)

---

## 4. Endpoint verification status

### Verified working (seen 200/201/204 in validator logs)
- `GET /customer`, `GET /employee`, `GET /project`, `GET /department`, `GET /activity`
- `POST /customer`, `POST /employee`, `POST /department`, `POST /project`, `POST /order`, `POST /product`
- `POST /travelExpense`, `PUT /travelExpense/{id}`, `DELETE /travelExpense/{id}`
- `PUT /order/{id}/:invoice`, `PUT /invoice/{id}/:payment`, `PUT /invoice/{id}/:createCreditNote`
- `GET /invoice` (requires `invoiceDateFrom`/`invoiceDateTo`), `GET /ledger/account`, `GET /supplier`
- `POST /ledger/voucher`

### Verified NOT working
- `GET /vat/type` → 404
- `POST /supplier/invoice` → 405
- `POST /invoice/fromTimesheet` → 405
- `POST /timesheet` (no `/entry`) → 404
- `POST /timeSheet` (capital S) → 404

### BETA (always 403 in validator)
- `PUT /project/{id}`, `DELETE /project/{id}`, `DELETE /customer/{id}`
- `PUT /order/orderline/{id}`, `DELETE /order/orderline/{id}`
- `POST /travelExpense/cost`

### Unverified (added to prompt but not yet confirmed in validator logs)
- `POST /supplier` — added PR #18; correct per API spec; not yet seen in live logs
- `POST /timesheet/entry` — correct per API spec; not yet seen in live logs

---

## 5. What to do next

### Immediate (top priority)
1. **Redeploy** — PR #18 merged but not deployed. Run `git pull` then `gcloud run deploy` from `~/nm-ai-2026-1`
2. **Submit repeatedly** — gather logs for new Tier 3 task types, and confirm PR #18 fixes for types #19/20/21

### Known fixes pending (once confirmed by logs)
3. **Ledger/voucher details** — if Tier 3 tasks include complex ledger entries, improve the POST /ledger/voucher guidance
4. **Employment sub-resource** — if "set employee start date" returns: POST /employee/employment with `{employeeId, startDate}` but this is unverified; confirm from spec first
5. **GET /project with customer filter** — for project lookup: `GET /project?name=X&customer.id=Y`
6. **POST /timesheet/entry** — confirm in validator logs; if it fails check exact field names

### Strategy for remaining ~22 hours
- Keep submitting to discover new task types (30 total, 21 seen so far)
- Each successful new task type = points scored even if the validator submits it only once
- Tier 3 tasks are now in the pool — focus on understanding what they ask and fixing failures fast

---

## 6. Key technical details

- **Project ID:** `ai-nm26osl-1730`
- **Cloud Run region:** `europe-north1`
- **Cloud Run service:** `tripletex-agent`
- **Working directory for deploy:** `~/nm-ai-2026-1/task1-Tripletex` (NOT `~/nm-ai-2026`)
- **Model:** `gemini-2.5-flash` via Vertex AI global endpoint (service account auth, no API key needed)
- **Gemini JSON mode:** enabled (`responseMimeType: application/json`)

---

## 7. How to run locally (for reference)

```bash
# On the Workbench VM (port 8082 — port 8080 is taken by JupyterLab)
cd ~/nm-ai-2026-1/task1-Tripletex && uvicorn main:app --host 0.0.0.0 --port 8082
```

Note: GCP metadata server not available locally, so LLM calls fail. Use deployed Cloud Run for real testing.

---

## 8. Unit tests

```bash
cd ~/nm-ai-2026-1/task1-Tripletex
pip install -r requirements.txt
pytest tests/test_agent.py -v
```

14 tests, all passing (as of PR #12).
