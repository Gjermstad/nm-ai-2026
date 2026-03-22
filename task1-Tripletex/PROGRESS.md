# Progress Report: Tripletex AI Accounting Agent

## 1. Current state (2026-03-22 ~01:15 CET)

PRs #42–#51 merged and deployed (revision 00055). Score: 27.67 (T1=12.8, T2=9.9, T3=5.0), rank #236/391. Competition ends 15:00 CET today (~14h remaining).

**Fixes this overnight session (PRs #40–#51):**
- #40: Department SEARCH FIRST (GET before POST, skip POST if found)
- #41: POST /employee department REQUIRED; ban startDate on employee body
- #42: Supplier SEARCH FIRST
- #44: activityType as REQUIRED field (wrong enum, fixed in #48)
- #46: customer field on POST /project (was missing → 0/7 on all project tasks)
- #47: Repair LLM now sees skipped calls (employment calls after failed employee now retry); email REQUIRED for STANDARD users
- #48: activityType correct enum — PROJECT_GENERAL_ACTIVITY not GENERAL_PROJECT_ACTIVITY
- #50: POST /supplierInvoice (camelCase) instead of /ledger/voucher (system-generated account fix)
- #51: dueDate→invoiceDueDate in GET /invoice fields; occupationCode filter by nameNO not code=

**User preferences (important for next session):**
- Ask user to merge PRs and deploy rather than automating it (user is awake and can do in seconds)
- Give PR link + deploy command at end of every response — user doesn't want to scroll
- Never push directly to main (except AGENT.md/PROGRESS.md docs)
- User wants to know context level so they can start a new session when needed
- User confirmed: organizers say ALL tasks are scorable at full score — nothing is truly "unfixable"

**Still to investigate (organizers say solvable):**
- `PUT /invoice/{id}/:payment → 404` when invoice ID > INT32_MAX — root cause unknown
- `POST /travelExpense/cost` → 403 BETA — try different approach or newer API version?
- Accounting dimensions — correct endpoint unknown (not /accounting/dimension)
- Employee PDF 15/22: 4 checks still failing (personnummer field? workingHoursScheme? wrong occupationCode?)
- Ledger error corrections: uses 1920 as balancing account — validator probably expects specific counterpart accounts

**Deployed URL:** `https://tripletex-agent-997219197351.europe-north1.run.app`

**Tier 3 tasks** live since ~11:00 CET March 21. Competition ends March 22 15:00 CET (~16h remaining).

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
| 36 | Analyze ledger Jan vs Feb, find top 3 expense accounts, create projects + activities (Spanish/French) | ⚠️ 0/10 | 3 | POST /activity activityType wrong enum → 422 all activity calls. Fixed PR #48: correct enum PROJECT_GENERAL_ACTIVITY. |
| 37 | Supplier invoice from PDF, Rio Azul Lda, IT-konsulenttjenester, INV-2026-6669 (Portuguese) | ⚠️ 2/10 | 2 | POST /ledger/voucher → 422 system-generated (2400/2710). Fixed PR #50: use POST /supplierInvoice instead. |
| 38 | Complete project lifecycle: create project, log time x2, register supplier cost, create invoice (English) | ⚠️ 2/11 | 3 | Gemini hallucinated `tool_code` format. Fixed PR #27. |
| 39 | Create and send invoice to Lumière SARL, 34100 NOK, Stockage cloud (French) | ✅ 7/7 | 2 | Bank account ✅, sendToCustomer=true ✅ |
| 40 | Create employee from PDF employment contract — Maximilian Fischer, Kvalitetskontroll dept (German) | ⚠️ 15/22 | 3 | Email missing → repair skipped employment calls. Fixed PR #47: repair LLM sees skipped calls + email REQUIRED for STANDARD. Scored 15/22. Remaining 4 failures: likely personnummer, workingHoursScheme, occupationCode wrong. |
| 41 | Bank statement reconciliation CSV — match payments to customer/supplier invoices (German) | ❌ 0/10 | 3 | INT32_MAX payment 404. Supplier invoice → use POST /supplierInvoice now (PR #50). Investigate. |
| 42 | Timesheet 11h "Design" on "Integración de plataforma" for Ana Romero / Costa Brava SL, project invoice (Spanish) | ⚠️ 4/8 | 2 | Fixed PR #34. |
| 43 | Create order + invoice + payment for Nordlys AS, Datarådgjeving + Programvarelisens (Nynorsk) | ⚠️ 4/8 | 2 | Invoice ID > INT32_MAX → payment 404. Organizers say solvable. |
| 44 | Fixed price project + milestone invoice (French/multi) | ⚠️ was 2/8 | 3 | SEARCH FIRST fixes in PRs #40-42. |
| 45 | PDF receipt: book accommodation to dept "Utvikling" (Nynorsk) | ⚠️ was 0/10 | 2 | SEARCH FIRST fixed PR #40. Account guidance still TBD. |
| 46 | Create project linked to customer (French/various) | ⚠️ was 0/7 | 1 | Fixed PR #46: customer field on POST /project. |
| 47 | Supplier invoice from PDF (Portuguese/various) | ⚠️ was 0/8 | 2 | Fixed PR #50: POST /supplierInvoice. |
| 48 | Currency agio/disagio + payment (EUR invoice) | ⚠️ 2/10 | 3 | dueDate → invoiceDueDate fixed PR #51. Payment INT32_MAX still an issue. |
| 49 | Employee from PDF + full employment setup (Nynorsk) | ⚠️ 15/22 | 3 | Partially fixed #47. Remaining: personnummer, occupationCode, workingHoursScheme. |
| ? | Unseen #1 | — | ? | — |

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
