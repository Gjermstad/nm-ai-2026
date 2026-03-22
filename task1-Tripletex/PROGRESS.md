# Progress Report: Tripletex AI Accounting Agent

## 1. Current state (2026-03-22 ~03:05 CET)

**Score: ~28.7 | Rank: ~#241 of 396 teams | All 30 task types seen**

Deployed revision: `tripletex-agent-00058-6z5`

PRs merged this session (Mar 22, ~01:00–03:05):
- **PR #53**: Added `nationalIdentityNumber` to employee fields + `workingHoursScheme` valid values (also introduced `{voucherId}` f-string bug — fixed in #61)
- **PR #55**: Fixed occupationCode: fetch all codes without filter, scan full list
- **PR #58**: Fixed deploy command: `--allow-unauthenticated` (was `--no-allow-unauthenticated`)
- **PR #61** (CRITICAL): Fixed f-string crash — `{voucherId}` → `{{voucherId}}` in build_llm_prompt; caused HTTP 500 on every request from PR #53 deploy until #61
- **PR #63**: Fixed occupationCode repair pass — repair prompt now includes full list JSON (8000 chars); use nameNO= filter when job title given; use .value (not .values) placeholder to intentionally trigger repair pass for numeric-only STYRK codes

**Known remaining issues:**
- occupationCode lookup for large lists (7116 codes, only first 1000 returned alphabetically): if target code is late alphabetically and no job title, repair pass may not find it
- Auto-submit loop runs in browser — dies if Mac sleeps (Mac must stay awake)

**Deployed URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`

Competition ends March 22 15:00 CET.

---

## 2. What is implemented

### Core architecture
- `/solve` endpoint (FastAPI) accepting prompt, files (PDF/image), and Tripletex credentials
- Single-shot planner: Gemini 2.5 Flash (Vertex AI global endpoint, `responseMimeType: application/json`) generates a full call plan in one LLM call
- Bounded repair pass: if any calls return 422 or 409, one corrective LLM call is made with full error context
- Parse failure retry: if the LLM output fails JSON parsing, one corrective prompt is sent before giving up
- File handling: base64 decode + PDF text extraction via `pypdf` (3000 char cap per file)
- Placeholder resolver: `$responses.N.value.FIELD.SUBFIELD` (nested), `$responses.N.value.FIELD`, `$responses.N.values.INDEX.FIELD`
- Unresolved placeholder detection: skip call if `$responses.` remains after resolve (prevents "wrong type for field" 422)
- Timeout budgeting: 255s deadline, checked before every LLM and API call
- Hard cap of 16 total Tripletex API calls per request
- BETA endpoint block: confirmed 403 endpoints listed so Gemini never tries them
- List response wrap: `if isinstance(plan, list): plan = {"calls": plan}` — prevents crash when Gemini returns raw array
- Output format enforcement: bans tool_code/function_call/action output from Gemini

### Bank account setup (PR #22)
- GET /ledger/account (number=1920) → PUT /ledger/account with isBankAccount=true, bankAccountNumber="12345678903" (11 digits, no dots)
- Added as mandatory first two calls whenever any invoice flow is detected
- Confirmed working: 8/8 on timesheet+project invoice task

### Bank return reversal (PR #26)
- GET /invoice → GET /invoice/{id}?fields=id,voucher(id) → PUT /ledger/voucher/$responses.1.value.voucher.id/:reverse?date=TODAY
- NOT credit note (that cancels the invoice)

### Employee sub-resources (PR #27)
- POST /employee → POST /employee/employment → POST /employee/employment/details
- employeeNumber as string field on employee

---

## 3. Task types seen in validator (28 confirmed + 2 unseen)

| # | Prompt summary (language) | Score | Tier | Root cause of failure / fix |
|---|---|---|---|---|
| 1 | Credit note for Luna SL — "Almacenamiento en la nube" 31750 NOK (Spanish) | ✅ 8/8 | 2 | — |
| 2 | Create and send invoice to Fjelltopp AS, 42600 NOK, Nettverksteneste (Nynorsk) | ❌ 0/7 | 2 | Bank account 422 on `PUT /order/:invoice` — validator env issue |
| 3 | Set fixed price 429500 NOK on project "ERP-implementering" for Elvdal AS, invoice 33% (Nynorsk) | ⚠️ 2/8 | 3 | Bank account 422 on invoice; fixed-price endpoint is BETA (403) |
| 4 | Register payment on Brattli AS invoice, 31300 NOK "Konsulenttimer" (Norwegian) | ⚠️ 2/7 | 2 | GET /invoice missing `invoiceDateFrom`/`invoiceDateTo` → 422 → unresolved placeholder → 404 payment. Fixed PR #12. |
| 5 | Reverse bank return — Lysgård AS, 15600 NOK "Konsulenttimer" → reinstate invoice (Norwegian) | ⚠️ 2/8 | 2 | Credit note was wrong approach. Fixed PR #26: GET /invoice/{id}?fields=id,voucher(id) → PUT /ledger/voucher/{voucherId}/:reverse?date=TODAY |
| 6 | Create order + invoice + payment for Waldstein GmbH, Netzwerkdienst + Beratungsstunden (German) | ⚠️ 4/8 | 2 | Invoice worked ✅; payment 404 — `paidAmount` placeholder not resolved in params. Fixed PR #12. |
| 7 | Create project "Intégration Montagne" for Montagne SARL, PM Nathan Martin (French) | ✅ 8/8 | 1 | — |
| 8 | Create order + invoice + payment for Río Verde SL, 2 products (Spanish) | ⚠️ 4/8 | 2 | Payment 404 — invoice ID 2147557274 > INT32_MAX; paidAmount hardcoded correctly. Unfixable (validator env). |
| 9 | Create customer Sonnental GmbH with address Solveien 21 Tromsø (German) | ❌ 0/8 | 1 | Wrong address fields (`visitingAddress`). Fixed PR #13: use `postalAddress`/`physicalAddress`. |
| 10 | Create invoice for Havbris AS, 3 lines: 25%/15%/0% VAT (Norwegian) | ❌ 0/8 | 2 | GET /vat/type → 404; Gemini used JSONPath filter → wrong vatType. Fixed PR #15: hardcode IDs 3/5/omit. |
| 11 | Log 34 hours for Charlotte Williams on "Analyse" in "Security Audit", invoice Windmill Ltd (English) | ❌ 0/8 | 2 | Wrong endpoint `/timesheet` (correct: `/timesheet/entry`); wrong activity lookup. Fixed PR #14. |
| 12 | Create departments "Drift", "Logistikk", "IT" (Portuguese) | ✅ 8/8 | 1 | — |
| 13 | Create and SEND invoice to Stormberg AS, 31250 NOK, Opplæring (Norwegian) | ❌ 0/8 | 2 | Bank account 422 — validator env issue |
| 14 | Invoice Sierra SL: 3 lines, 25%/15%/0% VAT (Spanish) | ❌ 0/8 | 2 | Same GET /vat/type → 404. Fixed PR #15. |
| 15 | Travel expense for Pablo Rodríguez "Conferencia Ålesund", per diems + flight + taxi (Spanish) | ⚠️ 2/8 | 2 | Header created ✓; individual costs BETA (POST /travelExpense/cost → 403). Unfixable. |
| 16 | Fixed price 324900 NOK project "Migração para nuvem", invoice 50% milestone (Portuguese) | ❌ 0/8 | 3 | Gemini returned raw JSON array → crash `AttributeError`. Fixed PR #16: wrap list in dict. |
| 17 | Invoice Bergwerk GmbH: 3 lines, 25%/15%/0% VAT (German) | ❌ 0/8 | 2 | Order ✓ (vatType fix working); invoice 422 bank account env issue. |
| 18 | Supplier invoice INV-2026-4811 from Montanha Lda 33200 NOK, account 7300 (Portuguese) | ❌ 0/8 | 2 | `POST /supplier/invoice` → 405. Accounts 2400/2710 → system-generated. Unfixable. |
| 19 | Create employee + set employment start date (Norwegian) | ❌ 0/8 | 1 | `startDate`/`employmentDate` not on Employee object → 422. Fixed PR #18. Also PR #27 adds employment sub-resources. |
| 20 | Create supplier (leverandør) (Norwegian/German) | ✅ 6/6 | 1 | POST /supplier added PR #18, confirmed ✅ |
| 21 | Create customer with organizationNumber (Norwegian) | ❌ 0/8 | 1 | Customer created (201) but `organizationNumber` missing from body. Fixed PR #18. |
| 22 | Unknown (from submit #35 — logs not captured) | ❌ | ? | — |
| 23 | Year-end closing / depreciation booking — årsoppgjør (Nynorsk) | ❌ 0/10 | 3 | `"vouchers"` field bug → all POST /ledger/voucher 422. Fixed PR #19: use `"postings"`. Also account 1209 not in validator env. |
| 24 | Ledger error correction — find and fix 4 accounting errors (Portuguese) | ❌ 0/? | 3 | 403 on first call (expired session token — validator env issue). Unfixable. |
| 25 | Travel expense with per diems + flight + taxi (German) | ⚠️ 2/8 | 2 | Same as #15: header ✅, POST /travelExpense/cost BETA → 403. Unfixable. |
| 26 | Custom accounting dimension "Region" + voucher linked to dimension (English) | ❌ 0/13 | 3 | POST /accounting/dimension → 404. Dimension fields on postings also 422. Fixed PR #21: skip dimensions, post voucher without them. |
| 27 | Timesheet 12h "Design" on "Configuration cloud" for Soleil SARL, generate project invoice (French) | ✅ 6/6 | 2 | POST /timesheet/entry ✅ confirmed. Invoice failed (bank account 422). |
| 28 | Currency exchange difference (disagio) on EUR invoice payment (Portuguese) | ⚠️ 4/8 | 3 | Bank account 422 on invoice creation. Fixed PR #22: PUT /ledger/account to set bankAccountNumber before invoice. |
| 29 | Employee onboarding from PDF offer letter (French) | ❌ 0/? | 3 | 403 on first call (expired token — validator env). PDF extraction working (607 chars). |
| 30 | Train ticket (Togbillett) expense as voucher, dept Logistikk, from PDF receipt (German) | ❌ 0/10 | 2 | "supplier"/"department" fields on voucher → 422. Fixed PR #22: only date/description/postings allowed on voucher. |
| 31 | Overdue invoice + reminder fee (purregebyr) for Spanish customer | ❌ 0/10 | 3 | GET /invoice with `customer.id` in fields → 400 "Illegal fields filter: Fields filter contains '.'". `voucherRows` on voucher → 422. Fixed PR #24. |
| 32 | Currency exchange disagio — Fjelltopp AS, 10143 EUR invoice (Nynorsk) | ⚠️ 2/10 | 3 | Bank account ✅; PUT /invoice/:payment → 404 (INT32_MAX). POST /ledger/voucher → 422 system-generated postings (accounts 1500/3400). Unfixable. |
| 33 | Purregebyr (reminder fee) — Skogheim AS (Nynorsk) | ⚠️ 2/10 | 3 | Bank account ✅; Order+Invoice created ✅; payment → 404 (INT32_MAX). POST /ledger/voucher → 422 system-generated postings. Unfixable. |
| 34 | Create product "Textbook" with product number 9036, 0% VAT (English) | ❌ 0/7 | 1 | POST /product missing `number` field → product number not set. Fixed PR #24. |
| 34b | Create product "Eau minérale" #7027, 36750 NOK, 15% VAT (French) | ✅ 6/7 | 1 | PR #24 fix confirmed working — number field included ✅ |
| 35 | Month-end closing March 2026 — periodisering, avskriving, lønnsavsetning (Nynorsk) | ⚠️ 2/10 | 3 | Account 6030 not in validator → unresolved placeholder → 422. Fixed PR #25: skip calls with unresolved placeholders. |
| 35x | Month-end closing (Norwegian/Spanish variants) | ⚠️ 2/10 | 3 | ALL voucher account postings → 422 system-generated in this validator env (1290, 1720, 5000, 2900, 6020, 6500). 2pts = GET /ledger/account calls only. Fundamentally unfixable. |
| 36 | Analyze ledger Jan vs Feb, find top 3 expense accounts, create projects + activities (Spanish) | ❌ 0/10 | 3 | GET /ledger/posting with dot notation → 400. POST /activity not in prompt. Fixed PR #25: parentheses syntax, add POST /activity. |
| 37 | Supplier invoice from PDF, Rio Azul Lda, IT-konsulenttjenester, INV-2026-6669 (Portuguese) | ⚠️ 2/10 | 2 | POST /ledger/voucher to accounts 2400/2710/6300 → 422 system-generated. Unfixable. |
| 38 | Complete project lifecycle: create project, log time x2, register supplier cost, create invoice (English) | ⚠️ 2/11 | 3 | Gemini hallucinated `tool_code` format instead of REST API calls → all skipped. Fixed PR #27: reinforce output format, ban tool_code. |
| 42 | Timesheet 11h "Design" on "Integración de plataforma" for Ana Romero / Costa Brava SL, project invoice (Spanish) | ⚠️ 4/8 | 2 | `employee` field in orderLines → 422. Repair pass added `customer` to timesheet/entry → 422. Fixed PR #34. |
| 43 | Create order + invoice + payment for Nordlys AS, Datarådgjeving + Programvarelisens (Nynorsk) | ⚠️ 4/8 | 2 | Invoice ID 2147631572 > INT32_MAX → payment 404. Unfixable. |
| 44 | Fixed price 365350 NOK on "Intégration CRM" for Colline SARL, PM Adam Thomas, 75% milestone invoice (French) | ⚠️ 2/8 | 3 | GET /customer found it but Gemini still POST /customer → duplicate. GET /employee found it but still POST /employee → 422. POST /project depends on POST /employee → cascade skip. Fixed this PR: SEARCH FIRST for customer + employee. |
| 45 | PDF receipt: book accommodation to dept "Utvikling", correct account + VAT (Nynorsk) | ❌ 0/10 | 2 | GET /dept found Utvikling but still POST /dept. Voucher created (201) but wrong account (6320 Renovasjon used for accommodation; should be ~7140 Reisekostnader). Fixed this PR: SEARCH FIRST for department. Account guidance TBD. |
| 39 | Create and send invoice to Lumière SARL, 34100 NOK, Stockage cloud (French) | ✅ 7/7 | 2 | Bank account ✅, sendToCustomer=true ✅ |
| 40 | Create employee from PDF employment contract — Maximilian Fischer, Kvalitetskontroll dept (German) | ❌ 0/22 | 3 | Gemini used ternary expression for department.id → unresolved placeholder → employee skipped. Fixed PR #27: ban ternary, add employeeNumber + employment sub-resources. |
| 41 | Bank statement reconciliation CSV — match payments to customer/supplier invoices (German) | ❌ 0/10 | 3 | Customer payment → 404 (INT32_MAX). Supplier payment voucher → 422 system-generated. Repair POST /supplierPayment → 404. Unfixable. |
| ? | Unseen #1 | — | ? | — |
| ? | Unseen #2 | — | ? | — |

**Patterns observed:**
- Credit notes on existing invoices → works ✅
- Create project + assign PM → works ✅
- Create departments → works ✅
- Create supplier → works ✅
- Log timesheet hours → works ✅
- Create/send invoice → works ✅ (when bank account is configured)
- Payment via PUT /invoice/:payment → works IF invoice ID ≤ INT32_MAX ✅
- Bank return reversal → works ✅ (PR #26 — not yet confirmed in live logs)
- Employee with sub-resources → added PR #27, not yet confirmed
- New invoice creation → intermittently fails with bank account 422 (validator env), unfixable
- Payment 404 for invoice IDs > INT32_MAX → unfixable (validator proxy overflow)
- System-generated account postings → unfixable in this validator environment

---

## 4. Endpoint verification status

### Verified working (seen 200/201/204 in validator logs)
- `GET /customer`, `GET /employee`, `GET /project`, `GET /department`, `GET /activity`
- `POST /customer`, `POST /employee`, `POST /department`, `POST /project`, `POST /order`, `POST /product`
- `POST /supplier` (confirmed ✅ — 6/6 score on supplier creation task)
- `POST /activity` (confirmed ✅ — PR #25)
- `POST /timesheet/entry` (confirmed ✅ — 6/6, 8/8 on timesheet+project invoice tasks)
- `POST /travelExpense`, `PUT /travelExpense/{id}`, `DELETE /travelExpense/{id}`
- `PUT /order/{id}/:invoice`, `PUT /invoice/{id}/:payment`, `PUT /invoice/{id}/:createCreditNote`
- `GET /invoice` (requires `invoiceDateFrom`/`invoiceDateTo`; NO dot notation in fields param)
- `GET /ledger/account`, `PUT /ledger/account/{id}`
- `GET /ledger/posting` (parentheses syntax: `account(id,number,name)`)
- `GET /supplier`
- `POST /ledger/voucher` (body uses `"postings"` array; only date/description/postings allowed)
- `PUT /ledger/voucher/{id}/:reverse` (PR #26 — bank return reversal)
- `POST /employee/employment` (PR #27 — not yet confirmed in live logs)
- `POST /employee/employment/details` (PR #27 — not yet confirmed in live logs)
- `GET /employee/employment/occupationCode` (PR #27 — not yet confirmed in live logs)

### Verified NOT working
- `GET /vat/type` → 404
- `POST /supplier/invoice` → 405
- `POST /invoice/fromTimesheet` → 405
- `POST /invoice/payment` → 405 (use `PUT /invoice/{id}/:payment` instead)
- `POST /timesheet` (no `/entry`) → 404
- `POST /timeSheet` (capital S) → 404
- `PUT /invoice/{id}/:reversePayment` → 404

### BETA (always 403 in validator)
- `PUT /project/{id}`, `DELETE /project/{id}`, `DELETE /customer/{id}`
- `PUT /order/orderline/{id}`, `DELETE /order/orderline/{id}`
- `POST /travelExpense/cost`

### Invalid voucher fields (cause 422 on POST /ledger/voucher)
- `"vouchers"` — use `"postings"` instead
- `"voucherRows"` — does not exist
- `"voucherType"` — does not exist
- `"supplier"` — does not exist on voucher
- `"department"` — does not exist on voucher
- `"customDimensions"`, `"dimension"` — do not exist

---

## 5. What to do next

### Confirm pending fixes
1. **Bank return (PR #26)** — not yet confirmed in validator logs. Submit a "bankretur"/"bank return" task.
2. **Employee sub-resources (PR #27)** — not yet confirmed. Submit an employee from PDF task.
3. **Auth errors** — two recent submits returned "The request was not authenticated" (Cloud Run rejects). Check SOLVE_API_KEY env var and Cloud Run IAM settings before next submit.

### Invalid order line fields (cause 422 "Feltet eksisterer ikke i objektet")
- `employee` — does NOT exist on orderLine. Remove entirely.
- Valid fields: `description`, `count`, `unitPriceExcludingVatCurrency`, `vatType`, `project`

### Invalid timesheet/entry fields (cause 422)
- `customer` — does NOT exist on timesheet/entry.
- Valid optional fields: `hourlyRate`, `comment`

### Unfixable (stop trying)
- Month-end closing (#35x): all accounts → system-generated. Max 2/10.
- Bank statement reconciliation (#41): INT32_MAX + system-generated. 0/10.
- Supplier invoice via voucher (#37): accounts 2400/2710 → system-generated. Max 2/10.
- Ledger error correction (#24): 403 on first call. Unfixable.

### Discover remaining 2 task types
- Submit repeatedly — 28/30 seen, 2 unknown

---

## 6. Key technical details

- **Project ID:** `ai-nm26osl-1730`
- **Cloud Run region:** `europe-north1`
- **Cloud Run service:** `tripletex-agent`
- **Working directory for deploy:** `~/nm-ai-2026-1/task1-Tripletex` (NOT `~/nm-ai-2026`)
- **Model:** `gemini-2.5-flash` via Vertex AI global endpoint (service account auth, no API key needed)
- **Gemini JSON mode:** enabled (`responseMimeType: application/json`)

---

## 9. Operational workflow (how to deploy, submit, and read logs)

### After merging a PR — deploy steps (local terminal)
Deploy can be run from the LOCAL terminal (no need for Cloud Shell):
```bash
cd /Users/kenneth/git/annet/nmiai/nm-ai-2026/task1-Tripletex
gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --allow-unauthenticated --quiet
```

Or via Cloud Shell if local gcloud is not authenticated:
Open: https://shell.cloud.google.com/?project=ai-nm26osl-1730&show=terminal
```bash
cd ~/nm-ai-2026-1 && git pull
cd ~/nm-ai-2026-1/task1-Tripletex && gcloud run deploy tripletex-agent --source . --region europe-north1 --project ai-nm26osl-1730 --allow-unauthenticated
```

⚠️ **CRITICAL: use `--allow-unauthenticated`** (NOT `--no-allow-unauthenticated`).
Using `--no-allow-unauthenticated` strips the allUsers IAM binding and all validator calls return
"The request was not authenticated" → 0% on every submission. Confirmed broken on 2026-03-22.

If you accidentally deploy with `--no-allow-unauthenticated`, fix immediately:
```bash
gcloud run services add-iam-policy-binding tripletex-agent --member=allUsers --role=roles/run.invoker --region=europe-north1 --project=ai-nm26osl-1730
```

### Submit (competition page)
URL: **https://app.ainm.no/submit/tripletex**

Competition API endpoint (for scripting):
```
POST https://api.ainm.no/tasks/cccccccc-cccc-cccc-cccc-cccccccccccc/submissions
Body: {"endpoint_url": "https://tripletex-agent-997219197351.europe-north1.run.app", "endpoint_api_key": null}
Auth: requires browser session cookie (credentials: include) — cookie is HttpOnly, not accessible via JS
```

Manual: Enter endpoint `https://tripletex-agent-997219197351.europe-north1.run.app`, click Submit 4 times, wait ~120s, read logs.

### Auto-submit loop (runs in browser console on https://app.ainm.no/submit/tripletex)
Paste this into the browser console on the competition page. **Mac must stay awake** — JS timers freeze on sleep.

```javascript
window._autoSubmitRunning = false;
clearTimeout(window._autoSubmitTimer);

const ENDPOINT = 'https://tripletex-agent-997219197351.europe-north1.run.app';
const TASK_ID = 'cccccccc-cccc-cccc-cccc-cccccccccccc';
const BATCH = 4;
const INTERVAL_MS = 3 * 60 * 1000; // 3 minutes between batches

async function submitOnce(n) {
  const res = await fetch(`https://api.ainm.no/tasks/${TASK_ID}/submissions`, {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({endpoint_url: ENDPOINT, endpoint_api_key: null})
  });
  console.log(`[autoSubmit] Submit #${n} → HTTP ${res.status}`);
  return res.status;
}

async function runBatch() {
  if (!window._autoSubmitRunning) { console.log('[autoSubmit] Stopped.'); return; }
  for (let i = 1; i <= BATCH; i++) {
    await submitOnce(window._autoSubmitCount + i);
    if (i < BATCH) await new Promise(r => setTimeout(r, 5000));
  }
  window._autoSubmitCount += BATCH;
  console.log(`[autoSubmit] Batch done (${window._autoSubmitCount} total). Next in ${INTERVAL_MS/1000}s`);
  window._autoSubmitTimer = setTimeout(runBatch, INTERVAL_MS);
}

window._autoSubmitRunning = true;
window._autoSubmitCount = 0;
console.log('[autoSubmit] Clean restart at ' + new Date().toLocaleTimeString());
runBatch();
```

Check loop status: `window._autoSubmitRunning + " | count: " + window._autoSubmitCount`
Stop loop: `window._autoSubmitRunning = false`

⚠️ If the loop stops after one batch (Mac slept), paste the full script again to restart.

### Read logs (local terminal — gcloud must be authenticated)
```bash
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="tripletex-agent"' \
  --project=ai-nm26osl-1730 --format='value(timestamp,textPayload)' --limit=300 2>&1
```
Note: if local gcloud returns nothing, use Cloud Shell instead.

### Identify failures in logs
Look for:
```
PROMPT: <task text>
CALL N ERROR 422 | {"validationMessages": ...}
CALL N: skipping — unresolved placeholder
WARNING: Could not parse repair plan
```
Fast completions (< 15s) with 0% score = 403 token expired (unfixable) or IAM auth error (fixable).

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
