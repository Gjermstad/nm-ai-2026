from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
import json
import logging
import os
import re
import time
import base64
import io
from typing import List, Optional
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("agent")

PROJECT_ID = "ai-nm26osl-1730"
VERTEX_URL = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/google/models/gemini-2.5-flash:generateContent"

MAX_DURATION = 255  # seconds before hard stop (300s limit - 45s buffer)
MAX_CALLS    = 12   # cap total Tripletex API calls for efficiency

# Optional inbound API key auth (set SOLVE_API_KEY env var to enable)
_API_KEY = os.getenv("SOLVE_API_KEY")
_bearer  = HTTPBearer(auto_error=False)

async def _check_auth(creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer)):
    if _API_KEY and (creds is None or creds.credentials != _API_KEY):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

app = FastAPI(dependencies=[Depends(_check_auth)])


class TripletexCredentials(BaseModel):
    base_url: str
    session_token: str


class FileInfo(BaseModel):
    filename: str
    content_base64: str
    mime_type: str


class SolveRequest(BaseModel):
    prompt: str
    files: Optional[List[FileInfo]] = None
    tripletex_credentials: TripletexCredentials


@app.get("/health")
def health():
    return {"status": "ok"}


def get_access_token() -> str:
    resp = requests.get(
        "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
        headers={"Metadata-Flavor": "Google"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def call_llm(prompt: str, deadline: float) -> str:
    remaining = deadline - time.time()
    if remaining < 30:
        raise TimeoutError(f"Insufficient time for LLM call: {remaining:.1f}s left")
    logger.info("Calling Vertex AI (gemini-2.5-flash)...")
    token = get_access_token()
    resp = requests.post(
        VERTEX_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192, "responseMimeType": "application/json"},
        },
        timeout=min(120, max(15, int(remaining) - 10)),
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    logger.info("LLM response (first 600 chars): %s", text[:600])
    return text


# --- Placeholder resolution ---
# Supports: $responses.N.value.FIELD  and  $responses.N.values.INDEX.FIELD
_VALUE_RE  = re.compile(r'\$responses\.(\d+)\.value\.(\w+)')
_VALUES_RE = re.compile(r'\$responses\.(\d+)\.values\.(\d+)\.(\w+)')


def resolve(text: str, responses: list) -> str:
    def _value_sub(m):
        idx, field = int(m.group(1)), m.group(2)
        if idx < len(responses):
            v = responses[idx].get("value")
            if isinstance(v, dict) and v.get(field) is not None:
                return str(v[field])
        return m.group(0)

    def _values_sub(m):
        idx, li, field = int(m.group(1)), int(m.group(2)), m.group(3)
        if idx < len(responses):
            vs = responses[idx].get("values", [])
            if li < len(vs) and isinstance(vs[li], dict) and vs[li].get(field) is not None:
                return str(vs[li][field])
        return m.group(0)

    text = _VALUE_RE.sub(_value_sub, text)
    text = _VALUES_RE.sub(_values_sub, text)
    return text


# --- JSON extraction ---

def extract_json(text: str) -> Optional[dict]:
    """Extract first valid JSON object from LLM output, tolerating markdown fences."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


# --- File context extraction ---

def extract_file_context(files: List[FileInfo]) -> str:
    if not files:
        return ""
    parts = []
    for f in files:
        try:
            data = base64.b64decode(f.content_base64)
        except Exception as e:
            logger.warning("Could not decode file %s: %s", f.filename, e)
            parts.append(f"[File: {f.filename} ({f.mime_type}) — decode error]")
            continue

        if f.mime_type == "application/pdf" or f.filename.lower().endswith(".pdf"):
            try:
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(data))
                text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
                text = text[:3000]  # cap to avoid token bloat
                parts.append(f"[File: {f.filename}]\n{text}")
                logger.info("Extracted %d chars from PDF %s", len(text), f.filename)
            except Exception as e:
                logger.warning("PDF extraction failed for %s: %s", f.filename, e)
                parts.append(f"[File: {f.filename} (PDF) — text extraction failed]")
        else:
            # Images and other binaries: note existence, LLM uses filename as context
            parts.append(f"[File: {f.filename} ({f.mime_type})]")

    return "\n\n".join(parts)


# --- API call executor ---

def execute_calls(calls: list, responses: list, base_url: str, session_token: str, deadline: float):
    """Execute API calls, appending to responses. Returns list of 422 error dicts."""
    errors_422 = []
    for i, call in enumerate(calls):
        if time.time() > deadline - 5:
            logger.warning("Deadline approaching, stopping at call %d", i)
            break
        if len(responses) >= MAX_CALLS:
            logger.warning("MAX_CALLS (%d) reached, stopping", MAX_CALLS)
            break

        if not isinstance(call.get("method"), str) or not isinstance(call.get("endpoint"), str):
            logger.warning("CALL %d: skipping malformed call object: %s", i, call)
            responses.append({"error": "malformed call"})
            continue

        method   = call["method"].upper()
        endpoint = call.get("endpoint", "")
        body     = call.get("body")
        params   = call.get("params")

        if body:
            body_str = resolve(json.dumps(body), responses)
            body = json.loads(body_str)
        if params:
            params_str = resolve(json.dumps(params), responses)
            params = json.loads(params_str)
        endpoint = resolve(endpoint, responses)
        url = f"{base_url}{endpoint}"

        logger.info("CALL %d: %s %s | body=%s | params=%s",
                    i, method, url,
                    json.dumps(body)[:300] if body else None, params)
        try:
            r = requests.request(
                method=method, url=url,
                auth=("0", session_token),
                json=body, params=params,
                timeout=30,
            )
            tlx_id = r.headers.get("x-tlx-request-id", "")
            if r.status_code == 403:
                logger.error("CALL %d: 403 Forbidden — invalid/expired token, aborting | tlx-id=%s", i, tlx_id)
                break
            if r.status_code == 429:
                logger.error("CALL %d: 429 Too Many Requests — rate limit hit, aborting | tlx-id=%s", i, tlx_id)
                break
            if r.status_code == 204:
                logger.info("CALL %d: 204 No Content", i)
                responses.append({})
            else:
                resp_json = r.json()
                body_rid = resp_json.get("requestId", "") if isinstance(resp_json, dict) else ""
                rid = tlx_id or body_rid
                logger.info("CALL %d: %d | %s", i, r.status_code, json.dumps(resp_json)[:400])
                if r.status_code in (409, 422):
                    logger.error("CALL %d %d | tlx-id=%s | %s", i, r.status_code, rid, json.dumps(resp_json)[:400])
                    errors_422.append({
                        "step": len(responses),
                        "status": r.status_code,
                        "call": call,
                        "error": resp_json,
                    })
                elif r.status_code >= 400:
                    logger.error("CALL %d ERROR %d | tlx-id=%s | %s", i, r.status_code, rid, r.text[:400])
                responses.append(resp_json)
        except Exception as e:
            logger.error("CALL %d exception: %s", i, e)
            responses.append({"error": str(e)})

    return errors_422


# --- Prompt builders ---

def build_llm_prompt(prompt: str, today: str, file_context: str) -> str:
    file_section = f"\n\n=== ATTACHED FILES ===\n{file_context}" if file_context else ""
    return f"""You are a Tripletex accounting API expert. Convert the task below into a precise sequence of Tripletex v2 REST API calls.

TASK (may be in Norwegian, English, Spanish, German, French, Portuguese, Nynorsk):
"{prompt}"{file_section}

TODAY'S DATE: {today}

=== REQUIRED FIELDS ===

POST /employee:
  REQUIRED: firstName, lastName, userType, email, department ({{"id": DEPT_ID}})
  userType: "STANDARD" (default) | "EXTENDED" (administrator/kontoadministrator/admin) | "NO_ACCESS"
  department.id: ALWAYS do GET /department first, use "$responses.0.values.0.id"

PUT /employee/{{id}}:
  REQUIRED: version (must come from GET response), firstName, lastName, userType, email, department
  Flow: GET /employee?firstName=X&lastName=Y → PUT /employee/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"
  endpoint example: "/employee/$responses.0.values.0.id"

POST /customer:
  REQUIRED: name
  Optional: email, phoneNumber, isCustomer (true),
            postalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}}),
            physicalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}})
  NOTE: Address fields use postalAddress/physicalAddress — NOT visitingAddress or visitingAddressLine1.
        Omit country if the address is in Norway.

PUT /customer/{{id}}:
  REQUIRED: version (from GET), name
  Flow: GET /customer?name=X → PUT /customer/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"

POST /department:
  REQUIRED: name

POST /project:
  REQUIRED: name, startDate ("YYYY-MM-DD"), projectManager ({{"id": EMPLOYEE_ID}})

POST /order:
  REQUIRED: customer ({{"id": ID}}), orderDate ("{today}"), deliveryDate ("{today}")
  deliveryDate: always include — use the same value as orderDate unless the prompt specifies otherwise.
  orderLines: [{{"description": "...", "count": 1, "unitPriceExcludingVatCurrency": 1000, "vatType": {{"id": 3}}}}]
  VAT note: by default use unitPriceExcludingVatCurrency. If isPrioritizeAmountsIncludingVat is true on the order,
  use unitPriceIncludingVatCurrency instead.
  Standard Norwegian VAT type IDs (hardcode these — do NOT try to look them up via API):
    25% (standard/high):       vatType {{"id": 3}}
    15% (food/beverage/middle): vatType {{"id": 5}}
    0%  (exempt/avgiftsfri):    omit vatType field entirely (no vatType key on the order line)
  Do NOT use GET /vat/type — that endpoint does not exist and returns 404.
  Do NOT use JSONPath filter expressions like $responses.N.values[?(@.x==y)].id — they are NOT supported.
  Optional: project ({{"id": ID}}) — link order to a project.
  Optional order line fields: employee ({{"id": ID}}), project ({{"id": ID}})

PUT /order/{{id}}/:invoice  (convert an existing order to a paid or unpaid invoice — preferred for single-order invoice):
  REQUIRED query params: invoiceDate=YYYY-MM-DD
  Optional query params: sendToCustomer=false (default — do NOT send unless prompt explicitly says to send)
  Flow: GET /order or use existing order id → PUT /order/$responses.N.value.id/:invoice?invoiceDate={today}&sendToCustomer=false
  Returns the created invoice in the response body (value.id = invoice ID, value.amountCurrency = total amount incl. VAT).
  If also registering payment in the same plan: use "$responses.N.value.amountCurrency" for paidAmount (N = index of this call).
  Example combined flow (create order, invoice it, pay it):
    call 0: GET /customer (find customer id)
    call 1: POST /order (create order, use $responses.0.values.0.id for customer.id)
    call 2: PUT /order/$responses.1.value.id/:invoice (params: invoiceDate, sendToCustomer=false)
    call 3: PUT /invoice/$responses.2.value.id/:payment (params: paymentDate, paymentTypeId=1, paidAmount="$responses.2.value.amountCurrency")

POST /invoice  (alternative — create invoice directly linking one or more orders):
  REQUIRED body fields: invoiceDate, invoiceDueDate, orders: [{{"id": ORDER_ID}}]
  REQUIRED query param: sendToCustomer=false (do NOT send unless prompt explicitly says to send)
  Use dates from the prompt; default to "{today}" if not specified.
  Example: {{"method": "POST", "endpoint": "/invoice", "params": {{"sendToCustomer": "false"}}, "body": {{...}}}}

POST /product:
  REQUIRED: name
  Optional: costExcludingVatCurrency (unit cost), priceExcludingVatCurrency (sale price)

GET /activity:
  Lists available work activities (e.g. "Analyse", "Consulting", "Support"). Use to find activity ID for timesheet entries.
  Params: name="Analyse" (search by name), fields="id,name"
  Returns values[]: [{{"id": INT, "name": "..."}}]

POST /timesheet/entry  (log worked hours — NOT /timesheet or /timeSheet):
  REQUIRED: employee ({{"id": ID}}), project ({{"id": ID}}), activity ({{"id": ID}}), date ("YYYY-MM-DD"), hours (number)
  Optional: hourlyRate (number), comment ("...")
  NOTE: The endpoint is /timesheet/entry — NOT /timesheet, NOT /timeSheet. Those return 404.
  Activity lookup: GET /activity?name=<activityName>&fields=id,name → use $responses.N.values.0.id
  DO NOT use GET /product to look up an activity — they are different things.
  DO NOT use POST /invoice/fromTimesheet — that endpoint returns 405.

Timesheet + project invoice pattern (log hours then invoice):
  1. GET /employee (by email)
  2. GET /customer (by org number)
  3. GET /project (by name + customer.id)
  4. GET /activity?name=<activityName>&fields=id,name
  5. POST /timesheet/entry (log the hours)
  6. POST /order — link to project: {{"project": {{"id": "$responses.2.values.0.id"}}}},
     orderLines: [{{"description": "<activity>", "count": <hours>, "unitPriceExcludingVatCurrency": <hourlyRate>, "vatType": {{"id": 3}}}}]
  7. PUT /order/$responses.5.value.id/:invoice (params: invoiceDate, sendToCustomer=false)

POST /travelExpense:
  REQUIRED: employee ({{"id": ID}})
  Optional: title ("short description"), date ("YYYY-MM-DD"),
            travelDetails ({{"isForeignTravel": false, "departureDate": "YYYY-MM-DD", "returnDate": "YYYY-MM-DD"}})
  NOTE: field is "title" not "description"; dates go inside travelDetails, NOT at top level.

PUT /travelExpense/{{id}}:
  REQUIRED: version (from GET), employee
  Optional: title, date, travelDetails
  Flow: GET /travelExpense → PUT /travelExpense/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"

DELETE /travelExpense/{{id}}:
  GET /travelExpense first, then DELETE /travelExpense/$responses.N.values.0.id

=== ADVANCED PATTERNS (Tier 2/3) ===

Register invoice payment (betaling på faktura):
  All parameters are QUERY PARAMS — there is no request body for this endpoint.
  Step 1: GET /invoice — REQUIRED params: invoiceDateFrom="2000-01-01", invoiceDateTo="{today}"
    Optional filter params: customer.id, amountCurrency, fields="id,invoiceNumber,amountCurrency"
    CRITICAL: invoiceDateFrom and invoiceDateTo are ALWAYS required — omitting them causes 422.
  Step 2: PUT /invoice/$responses.0.values.0.id/:payment
    REQUIRED query params: paymentDate=YYYY-MM-DD, paymentTypeId=1, paidAmount=<number>
    Use placeholder for amount: "paidAmount": "$responses.0.values.0.amountCurrency"
  Example call: {{"method": "PUT", "endpoint": "/invoice/$responses.0.values.0.id/:payment",
    "params": {{"paymentDate": "{today}", "paymentTypeId": "1", "paidAmount": "$responses.0.values.0.amountCurrency"}}}}

Issue credit note (kreditnota / kreditfaktura):
  All parameters are QUERY PARAMS — there is no request body for this endpoint.
  Step 1: GET /invoice — same as payment above (invoiceDateFrom and invoiceDateTo ALWAYS required).
  Step 2: PUT /invoice/$responses.0.values.0.id/:createCreditNote
    REQUIRED query params: date=YYYY-MM-DD
    Optional query params: comment=<text>, sendToCustomer=false, sendType=<EMAIL|EHF|...>
  Example call: {{"method": "PUT", "endpoint": "/invoice/$responses.0.values.0.id/:createCreditNote",
    "params": {{"date": "{today}", "sendToCustomer": "false"}}}}

Supplier invoice (leverandørfaktura / fatura do fornecedor):
  NOTE: The Tripletex API does NOT have a POST endpoint for creating supplier invoices.
  If a task asks to register a supplier invoice, record it as a ledger voucher instead (POST /ledger/voucher).
  Do NOT call POST /supplier/invoice (405) or POST /supplierInvoice (does not exist).
  Use GET /supplier to look up the supplier, GET /ledger/account for the account, then POST /ledger/voucher.

Ledger voucher (bilag):
  POST /ledger/voucher
  body: {{"date": "YYYY-MM-DD", "description": "...", "vouchers": [{{"account": {{"id": ACCT_ID}}, "amount": 0}}]}}
  GET /ledger/account to find account IDs by number (e.g. params: {{"number": "1500"}})
  DELETE /ledger/voucher/{{id}}: GET /ledger/voucher first → DELETE /ledger/voucher/$responses.N.values.0.id

Ledger postings (posteringer):
  GET /ledger/posting with params: {{"dateFrom": "YYYY-MM-DD", "dateTo": "YYYY-MM-DD", "fields": "id,date,description,amount,account"}}

=== BETA ENDPOINTS — NEVER USE (returns 403 Forbidden) ===
The following endpoints are tagged [BETA] in the Tripletex API and will always return 403.
Do NOT generate calls to any of these — they will always fail:
  DELETE /customer/{{id}}          → BETA, always 403. Do NOT delete customers.
  PUT /project/{{id}}              → BETA, always 403. Cannot update projects via API.
  DELETE /project/{{id}}           → BETA, always 403. Cannot delete projects via API.
  PUT /order/orderline/{{id}}      → BETA, always 403. Cannot update order lines via API.
  DELETE /order/orderline/{{id}}   → BETA, always 403. Cannot delete order lines via API.
  POST /travelExpense/cost         → BETA, always 403. Cannot add individual expense cost lines via API.
If the task asks you to do something only possible via a BETA endpoint, skip that action entirely.

=== PLACEHOLDER SYNTAX ===
"$responses.N.value.id"         -> id from POST/PUT response at step N
"$responses.N.value.version"    -> version from single-item response at step N
"$responses.N.values.0.id"      -> id of first item from GET list at step N
"$responses.N.values.0.version" -> version of first item from GET list at step N
"$responses.N.values.1.id"      -> id of second item from GET list at step N
CRITICAL: Only simple dot-path and numeric index placeholders are supported.
  DO NOT use JSONPath filter expressions like $responses.N.values[?(@.field==value)].id — NOT supported, will fail.

=== OUTPUT FORMAT ===
Respond with ONLY a raw JSON object - no markdown, no code fences, no explanation.
Each call object MUST have exactly these keys: "method", "endpoint", "body" (optional), "params" (optional).
CRITICAL: use "endpoint" not "path" or "url" for the URL path field.

{{
  "calls": [
    {{"method": "GET", "endpoint": "/department", "params": {{"fields": "id,name", "count": 1}}}},
    {{"method": "POST", "endpoint": "/employee", "body": {{
      "firstName": "Ola", "lastName": "Nordmann",
      "userType": "STANDARD", "email": "ola@example.com",
      "department": {{"id": "$responses.0.values.0.id"}}
    }}}}
  ]
}}
"""


def build_repair_prompt(original_prompt: str, today: str, responses: list, errors_422: list) -> str:
    # Summarise what succeeded — include id, version, name so repair calls can reference them
    _FIELDS = ("id", "version", "name")
    succeeded = []
    failed_steps = {e["step"] for e in errors_422}
    for i, resp in enumerate(responses):
        if i in failed_steps:
            continue
        v  = resp.get("value")
        vs = resp.get("values", [])
        if isinstance(v, dict):
            fields = {k: v[k] for k in _FIELDS if v.get(k) is not None}
            if fields:
                succeeded.append(f"  Step {i} (single): {fields}")
        elif vs:
            summary = [{k: item[k] for k in _FIELDS if item.get(k)} for item in vs[:3]]
            succeeded.append(f"  Step {i} (list, first {len(summary)}): {summary}")

    success_section = ("\n".join(succeeded)) if succeeded else "  (none)"

    error_lines = []
    for e in errors_422:
        call = e["call"]
        hint = "(version conflict — re-GET to get current version)" if e.get("status") == 409 else "(validation error — fix missing/wrong fields)"
        error_lines.append(
            f"  Step {e['step']}: {call['method']} {call['endpoint']} → HTTP {e.get('status', 422)} {hint}\n"
            f"    body: {json.dumps(call.get('body', {}))[:300]}\n"
            f"    error: {json.dumps(e['error'])[:400]}"
        )
    error_section = "\n".join(error_lines)

    return f"""You are a Tripletex accounting API expert. Some API calls failed with validation or conflict errors (422 or 409).
Generate ONLY the corrected replacement calls needed to fix these failures.

ORIGINAL TASK: "{original_prompt}"
TODAY: {today}

PREVIOUSLY SUCCEEDED (you can reference these via $responses.N.value.id):
{success_section}

FAILED CALLS:
{error_section}

Read the error messages carefully and generate corrected calls.
Each call object MUST use "endpoint" (not "path" or "url") for the URL path field.
Return ONLY a raw JSON object — no markdown, no explanation:
{{"calls": [...]}}
"""


# --- Main endpoint (also mounted at root for validators that POST to /) ---

@app.post("/solve")
@app.post("/")
async def solve(req: SolveRequest):
    deadline = time.time() + MAX_DURATION
    prompt        = req.prompt
    base_url      = req.tripletex_credentials.base_url
    session_token = req.tripletex_credentials.session_token
    today         = date.today().isoformat()

    logger.info("=" * 60)
    logger.info("PROMPT: %s", prompt)
    logger.info("BASE_URL: %s", base_url)
    logger.info("=" * 60)

    file_context = extract_file_context(req.files or [])
    llm_prompt   = build_llm_prompt(prompt, today, file_context)

    # --- Plan generation with one parse-failure retry ---
    try:
        raw = call_llm(llm_prompt, deadline)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {"status": "completed"}

    plan = extract_json(raw)
    if plan is None:
        logger.warning("JSON parse failed on first attempt, retrying with correction prompt...")
        try:
            raw2 = call_llm(
                f'Your previous response was not valid JSON. Return ONLY a raw JSON object '
                f'with a "calls" array.\n\nOriginal task:\n"{prompt}"\n\nReturn ONLY JSON, no markdown.',
                deadline,
            )
            plan = extract_json(raw2)
        except Exception as e:
            logger.error("Retry LLM call failed: %s", e)

    if plan is None:
        logger.error("Could not parse a valid plan after retry. Giving up.")
        return {"status": "completed"}

    # Gemini sometimes returns a raw array instead of {"calls": [...]}
    if isinstance(plan, list):
        plan = {"calls": plan}

    calls = plan.get("calls", [])
    logger.info("Plan has %d API calls", len(calls))

    # --- Execute initial plan ---
    responses  = []
    errors_422 = execute_calls(calls, responses, base_url, session_token, deadline)

    # --- One repair pass for 422 validation errors and 409 version conflicts ---
    if errors_422 and (deadline - time.time()) > 40:
        logger.info("Attempting repair pass for %d error(s) (422/409)", len(errors_422))
        repair_prompt = build_repair_prompt(prompt, today, responses, errors_422)
        try:
            raw_repair   = call_llm(repair_prompt, deadline)
            repair_plan  = extract_json(raw_repair)
            if isinstance(repair_plan, list):
                repair_plan = {"calls": repair_plan}
            if repair_plan:
                repair_calls = repair_plan.get("calls", [])
                logger.info("Repair plan has %d calls", len(repair_calls))
                execute_calls(repair_calls, responses, base_url, session_token, deadline)
            else:
                logger.warning("Could not parse repair plan")
        except Exception as e:
            logger.warning("Repair pass failed: %s", e)

    logger.info("All done. Total responses collected: %d", len(responses))
    return {"status": "completed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
