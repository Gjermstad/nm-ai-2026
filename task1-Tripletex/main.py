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
MAX_CALLS    = 16   # cap total Tripletex API calls (Tier 3 tasks need up to 14+)

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
# Supports:
#   $responses.N.value.FIELD           — single-item response (POST/PUT/GET single)
#   $responses.N.value.FIELD.SUBFIELD  — nested object, e.g. value.voucher.id
#   $responses.N.values.INDEX.FIELD    — list response (GET list)
#   $responses.N.values.INDEX.FIELD.SUBFIELD — nested field within a list item, e.g. values.0.account.name
_VALUE_NESTED_RE  = re.compile(r'\$responses\.(\d+)\.value\.(\w+)\.(\w+)')
_VALUE_RE         = re.compile(r'\$responses\.(\d+)\.value\.(\w+)')
_VALUES_NESTED_RE = re.compile(r'\$responses\.(\d+)\.values\.(\d+)\.(\w+)\.(\w+)')
_VALUES_RE        = re.compile(r'\$responses\.(\d+)\.values\.(\d+)\.(\w+)')


def resolve(text: str, responses: list) -> str:
    def _value_nested_sub(m):
        idx, field, subfield = int(m.group(1)), m.group(2), m.group(3)
        if idx < len(responses):
            v = responses[idx].get("value")
            if isinstance(v, dict):
                nested = v.get(field)
                if isinstance(nested, dict) and nested.get(subfield) is not None:
                    return str(nested[subfield])
        return m.group(0)

    def _value_sub(m):
        idx, field = int(m.group(1)), m.group(2)
        if idx < len(responses):
            v = responses[idx].get("value")
            if isinstance(v, dict) and v.get(field) is not None:
                return str(v[field])
        return m.group(0)

    def _values_nested_sub(m):
        # Resolves $responses.N.values.INDEX.FIELD.SUBFIELD — e.g. values.0.account.name
        idx, li, field, subfield = int(m.group(1)), int(m.group(2)), m.group(3), m.group(4)
        if idx < len(responses):
            vs = responses[idx].get("values", [])
            if li < len(vs) and isinstance(vs[li], dict):
                nested = vs[li].get(field)
                if isinstance(nested, dict) and nested.get(subfield) is not None:
                    return str(nested[subfield])
        return m.group(0)

    def _values_sub(m):
        idx, li, field = int(m.group(1)), int(m.group(2)), m.group(3)
        if idx < len(responses):
            vs = responses[idx].get("values", [])
            if li < len(vs) and isinstance(vs[li], dict) and vs[li].get(field) is not None:
                return str(vs[li][field])
        return m.group(0)

    # Apply most specific patterns first to avoid partial matches
    text = _VALUE_NESTED_RE.sub(_value_nested_sub, text)
    text = _VALUE_RE.sub(_value_sub, text)
    text = _VALUES_NESTED_RE.sub(_values_nested_sub, text)  # must run before _VALUES_RE
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
    """Execute API calls, appending to responses. Returns (errors_422, skipped_calls)."""
    errors_422 = []
    skipped_calls = []
    for i, call in enumerate(calls):
        if time.time() > deadline - 5:
            logger.warning("Deadline approaching, stopping at call %d", i)
            break
        if len(responses) >= MAX_CALLS:
            logger.warning("MAX_CALLS (%d) reached, stopping", MAX_CALLS)
            break

        # Normalize httpMethod → method (repair LLM sometimes uses httpMethod)
        if "httpMethod" in call and "method" not in call:
            call = dict(call)
            call["method"] = call.pop("httpMethod")

        # Extract method from endpoint if repair LLM embeds it there (e.g. "POST /endpoint" → method="POST", endpoint="/endpoint")
        if isinstance(call.get("endpoint"), str) and " " in call["endpoint"] and not isinstance(call.get("method"), str):
            first_token, rest = call["endpoint"].split(" ", 1)
            if first_token.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                call = dict(call)
                call["method"] = first_token.upper()
                call["endpoint"] = rest

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

        # Skip calls that still contain unresolved placeholders — a dependency returned no results.
        # Sending a literal "$responses.N.values.0.id" string causes 422 "wrong type for field".
        combined_str = json.dumps({"body": body, "params": params, "endpoint": endpoint})
        if "$responses." in combined_str:
            logger.warning("CALL %d: skipping — unresolved placeholder in call (dependency returned no results): %s",
                           i, combined_str[:300])
            skipped_calls.append(call)
            responses.append({"error": "unresolved placeholder — dependency call returned no results"})
            continue

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

    return errors_422, skipped_calls


# --- Prompt builders ---

def build_llm_prompt(prompt: str, today: str, file_context: str) -> str:
    file_section = f"\n\n=== ATTACHED FILES ===\n{file_context}" if file_context else ""
    return f"""You are a Tripletex accounting API expert. Convert the task below into a precise sequence of Tripletex v2 REST API calls.

TASK (may be in Norwegian, English, Spanish, German, French, Portuguese, Nynorsk):
"{prompt}"{file_section}

TODAY'S DATE: {today}

=== REQUIRED FIELDS ===

POST /employee:
  REQUIRED: firstName, lastName, userType, department ({{"id": DEPT_ID}})
  department is ALWAYS required — omitting it causes 422 "department.id: Feltet må fylles ut".
  email: REQUIRED when userType is "STANDARD" (Tripletex-user requires email — causes 422 "email: Må angis for Tripletex-brukere" if omitted).
         Include email if provided in the task; if not provided, omit userType or set userType to "NO_ACCESS".
  Optional: employeeNumber ("string" — internal staff number, e.g. "EMP-001" or "12345"; include if task provides it),
            dateOfBirth ("YYYY-MM-DD" — birth date if provided in task or PDF),
            nationalIdentityNumber ("11-digit string" — Norwegian national identity number (personnummer / fødselsnummer / Sozialversicherungsnummer / personnummer); ALWAYS include if provided in task or PDF)
  userType: "STANDARD" (default, requires email) | "EXTENDED" (administrator/kontoadministrator/admin) | "NO_ACCESS"
  department.id: ALWAYS do GET /department first (filter by name if a department is named in the task).
    CRITICAL: If GET /department returns count: 0 (department not found), you MUST create it first:
      POST /department body: {{"name": "<department name from task>"}}
      Then use "$responses.N.value.id" (from POST result, NOT .values.0.id) for department.id in POST /employee.
    CRITICAL: NEVER use ternary expressions, JavaScript, or conditional logic in placeholder values.
      BAD:  "id": "{{$responses.0.values.length > 0 ? $responses.0.values.0.id : 944619}}"  ← FORBIDDEN
      GOOD: "id": "$responses.1.value.id"  ← use the POST /department response index
    If you are unsure whether the department exists, always plan: GET /department → POST /department → use $responses.1.value.id
  NOTE: Do NOT include startDate, employmentDate, or any employment fields in the employee body — they do NOT exist on Employee and cause 422.
        startDate belongs ONLY on POST /employee/employment (a separate call AFTER the employee is created).
        NEVER add startDate to POST /employee regardless of what the task says.
  SEARCH FIRST — CRITICAL: If the task references an existing employee (e.g. by email or name), do GET /employee?email=X&fields=id,firstName,lastName,email first.
    If found (count > 0): use "$responses.N.values.0.id" for all downstream references to this employee's ID.
    Do NOT include a POST /employee call for the same person anywhere in your plan — omit it entirely.
    The GET call IS the only call. Downstream project/order/timesheet calls must reference "$responses.N.values.0.id" from the GET, not a POST result.

POST /employee/employment  (set start date and employment type after creating employee):
  REQUIRED: employee ({{"id": EMPLOYEE_ID}}), startDate ("YYYY-MM-DD")
  Optional: isMainEmployer (true/false), endDate ("YYYY-MM-DD")
  Flow: POST /employee → POST /employee/employment with employee.id from previous response
  Example: {{"employee": {{"id": "$responses.N.value.id"}}, "startDate": "2024-01-01", "isMainEmployer": true}}
  Returns: value.id = employmentId (needed for POST /employee/employment/details)

POST /employee/employment/details  (set salary, employment percentage, job code):
  REQUIRED: employment ({{"id": EMPLOYMENT_ID}}), date ("YYYY-MM-DD" — effective date of this detail record)
  Optional: percentageOfFullTimeEquivalent (number, e.g. 100.0 for full-time, 50.0 for half-time),
            annualSalary (number — annual salary in NOK),
            hourlyWage (number — hourly wage in NOK),
            remunerationType ("MONTHLY_WAGE" | "HOURLY_WAGE" | "FEE" | "PIECEWORK_WAGE"),
            employmentType ("ORDINARY" | "MARITIME" | "FREELANCE"),
            employmentForm ("PERMANENT" | "TEMPORARY"),
            workingHoursScheme (valid values: "NOT_SHIFT" standard daytime office work, "ROUND_THE_CLOCK", "SHIFT_365", "OFFSHORE_336", "CONTINUOUS", "OTHER_SHIFT", "NOT_CHOSEN" if unspecified; use "NOT_SHIFT" for normal office/desk work),
            occupationCode ({{"id": OCCUPATION_CODE_ID}}) — job code (Berufsschlüssel/yrkeskode)
  Flow: POST /employee/employment → POST /employee/employment/details with employmentId
  Example: {{"employment": {{"id": "$responses.N.value.id"}}, "date": "2024-01-01",
    "percentageOfFullTimeEquivalent": 100.0, "annualSalary": 600000, "remunerationType": "MONTHLY_WAGE",
    "employmentType": "ORDINARY", "employmentForm": "PERMANENT", "workingHoursScheme": "NOT_SHIFT"}}

GET /employee/employment/occupationCode  (look up job code / stillingskode / Berufsschlüssel):
  CRITICAL: Do NOT use any filter params — neither code= nor nameNO= reliably filters.
  ALWAYS fetch ALL codes without any filter:
    params: {{"fields": "id,nameNO,code"}}  ← no code=, no nameNO=, nothing else
  This returns all ~140 codes. Scan the full list to find the correct entry:
    - If the task/PDF provides a numeric STYRK/ISCO code (e.g. "4110"):
        Look for the entry whose code field starts with that number (e.g. "4110101" starts with "4110").
        Do NOT pass code="4110" as a param — it is IGNORED and returns all 140 results.
    - If the task/PDF provides a job title (e.g. "Regnskapsfører", "Kontorfullmektig"):
        Look for the entry whose nameNO most closely matches that title.
  Use the id from the matching entry as occupationCode.id in POST /employee/employment/details.
  Only call this if the task explicitly provides a job/occupation code or job title requiring a code.

PUT /employee/{{id}}:
  REQUIRED: version (must come from GET response), firstName, lastName, userType, email, department
  Flow: GET /employee?firstName=X&lastName=Y → PUT /employee/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"
  endpoint example: "/employee/$responses.0.values.0.id"

POST /customer:
  REQUIRED: name
  Optional: email, phoneNumber, isCustomer (true), organizationNumber ("9-digit string"),
            postalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}}),
            physicalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}})
  NOTE: Address fields use postalAddress/physicalAddress — NOT visitingAddress or visitingAddressLine1.
        Omit country if the address is in Norway.
        Include organizationNumber if provided in the task.
  SEARCH FIRST — CRITICAL: If the task references an existing customer (by org number or name), do GET /customer?organizationNumber=X&fields=id,name,organizationNumber first.
    If found (count > 0): use "$responses.N.values.0.id" for all downstream references to this customer's ID.
    Do NOT include a POST /customer call for the same customer anywhere in your plan — omit it entirely.

PUT /customer/{{id}}:
  REQUIRED: version (from GET), name
  Flow: GET /customer?name=X → PUT /customer/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"

POST /supplier  (create a new supplier / leverandør):
  REQUIRED: name
  Optional: email, phoneNumber, organizationNumber ("9-digit string"),
            postalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}}),
            physicalAddress ({{"addressLine1": "...", "postalCode": "...", "city": "..."}})
  NOTE: Use isSupplier: true (not isCustomer) when creating a supplier.
        Address fields: postalAddress/physicalAddress — NOT visitingAddress.
  SEARCH FIRST — CRITICAL: If the task references an existing supplier (by org number or name), do GET /supplier?organizationNumber=X&fields=id,name,organizationNumber first (or GET /supplier?name=X&fields=id,name if no org number).
    If found (count > 0): use "$responses.N.values.0.id" for all downstream references — do NOT also POST /supplier for the same supplier — omit it entirely.

POST /department:
  REQUIRED: name
  SEARCH FIRST — CRITICAL: If the task references an existing department (by name), do GET /department?name=X&fields=id,name first.
    If found (count > 0): use "$responses.N.values.0.id" for all downstream references to this department's ID.
    Do NOT include a POST /department call for the same department anywhere in your plan — omit it entirely.
    The GET call IS the only call. All downstream voucher/project/order calls must reference "$responses.N.values.0.id" from the GET, not a POST result.

POST /project:
  REQUIRED: name, startDate ("YYYY-MM-DD"), projectManager ({{"id": EMPLOYEE_ID}})
  If no project manager is named in the task: do GET /employee?fields=id,firstName,lastName&count=1 first,
  then use "$responses.N.values.0.id" as projectManager.id. Do NOT hardcode id=1 — that is "Historisk ansatt" and causes 422.
  Optional: customer ({{"id": CUSTOMER_ID}}) — ALWAYS include when the task says the project is "for" or "linked to" a customer.
    To get the customer ID: GET /customer?organizationNumber=X or GET /customer?name=X first, then reference "$responses.N.values.0.id".
  NOTE: Do NOT include fixedPrice, contractSum, billingPlan, price, or any billing/pricing fields in POST /project — they do NOT exist on the project creation endpoint and cause 422.
    A fixed price cannot be set via the API (the endpoint to do so is BETA/403). Create the project normally, then proceed with order/invoice for partial credit.

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
  Optional order line fields: project ({{"id": ID}})
  NOTE: Do NOT include employee in orderLines — that field does not exist on orderLine and causes 422 "Feltet eksisterer ikke i objektet".

⚠️ BANK ACCOUNT SETUP — required before any invoice creation:
  A fresh Tripletex account has no bank account number registered, which causes 422
  "Faktura kan ikke opprettes før selskapet har registrert et bankkontonummer."
  Whenever the task involves creating an invoice (PUT /order/:invoice or POST /invoice),
  ALWAYS add these two calls at the very beginning of your plan (before any other calls):
    call 0: GET /ledger/account | params: {{"number": "1920", "fields": "id,version,number,name"}}
    call 1: PUT /ledger/account/$responses.0.values.0.id
      body: {{
        "version": "$responses.0.values.0.version",
        "number": 1920,
        "name": "$responses.0.values.0.name",
        "isBankAccount": true,
        "bankAccountNumber": "12345678903"
      }}
  Only after these two calls, proceed with GET /customer, POST /order, etc.
  Do NOT skip this step for any invoice flow — it is always required on a fresh account.

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
  Optional: number ("string" — the product number/SKU, e.g. "9036"; always include if the task specifies a product number),
            costExcludingVatCurrency (unit cost), priceExcludingVatCurrency (sale price),
            vatType ({{"id": 3}} for 25%, {{"id": 5}} for 15%, omit for 0%)
  Example: {{"name": "Textbook", "number": "9036", "priceExcludingVatCurrency": 450}}

GET /activity:
  Lists available work activities (e.g. "Analyse", "Consulting", "Support"). Use to find activity ID for timesheet entries.
  Params: name="Analyse" (search by name), fields="id,name"
  Returns values[]: [{{"id": INT, "name": "..."}}]
  FALLBACK: If count: 0 (activity not found by name), do GET /activity?fields=id,name (no name filter) to list ALL
  available activities, then pick the most relevant one. Do NOT skip the timesheet step.

POST /activity  (create a new work activity — use when task asks to create an activity):
  REQUIRED: name, activityType
  activityType MUST be one of these exact string values (NOT an object/id — plain string only):
    "GENERAL_ACTIVITY"          — a general activity not tied to a specific project
    "PROJECT_GENERAL_ACTIVITY"  — a general activity within a project context (use this when creating activities for a project)
    "PROJECT_SPECIFIC_ACTIVITY" — an activity specific to one project
    "TASK"                      — a task-type activity
  Use "PROJECT_GENERAL_ACTIVITY" when creating an activity linked to a project.
  Use "GENERAL_ACTIVITY" for standalone general activities.
  Optional: description
  Example: {{"name": "Design", "description": "Design work", "activityType": "PROJECT_GENERAL_ACTIVITY"}}

POST /timesheet/entry  (log worked hours — NOT /timesheet or /timeSheet):
  REQUIRED: employee ({{"id": ID}}), project ({{"id": ID}}), activity ({{"id": ID}}), date ("YYYY-MM-DD"), hours (number)
  Optional: hourlyRate (number), comment ("...")
  NOTE: The endpoint is /timesheet/entry — NOT /timesheet, NOT /timeSheet. Those return 404.
  NOTE: Do NOT include customer, order, or invoice fields — those fields do not exist on timesheet/entry and cause 422.
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
    Optional filter params: fields="id,invoiceNumber,amountCurrency,amountExcludingVatCurrency"
    CRITICAL: invoiceDateFrom and invoiceDateTo are ALWAYS required — omitting them causes 422.
    CRITICAL: Do NOT use dot notation in the fields param (e.g. "customer.id" will cause 400 "Illegal fields filter: Fields filter contains '.'").
      Use only simple field names: "id,invoiceNumber,amountCurrency,amountExcludingVatCurrency,invoiceDate"
    INVALID FIELDS (cause 400): "paidAmountCurrency", "dueDate" — do NOT use these.
      Valid fields: id, invoiceNumber, amountCurrency, amountExcludingVatCurrency, invoiceDate, invoiceDueDate, customer(id,name), voucher(id)
    NOTE: The server does NOT filter by amountCurrency or amountExcludingVatCurrency — it may return ALL invoices.
    If multiple invoices are returned, select the correct index by matching the amount in the task:
      values.0 = lowest invoiceNumber (oldest), values.1 = second oldest, etc.
      If the task specifies an excl. VAT amount, check values[N].amountExcludingVatCurrency to pick the right index.
      Use "$responses.N.values.1.id" for the second invoice, "$responses.N.values.0.id" for the first.
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

Reverse a bank return (bankretur — undo a registered payment so the invoice is outstanding again):
  This is NOT the same as a credit note. A credit note cancels the invoice. A bank return reversal
  undoes the payment registration and restores the invoice to outstanding/unpaid status.
  Flow:
    Step 1: GET /invoice — params: invoiceDateFrom="2000-01-01", invoiceDateTo="{today}",
            fields="id,invoiceNumber,amountCurrency,amountExcludingVatCurrency,voucher(id)"
            Match the invoice by amount from the task.
    Step 2: GET /invoice/$responses.0.values.0.id — params: fields="id,voucher(id)"
            This gets the invoice with its payment voucher.
    Step 3: PUT /ledger/voucher/$responses.1.value.voucher.id/:reverse
            REQUIRED query param: date=YYYY-MM-DD (use today or the bank return date)
            No request body. This creates a counter-entry that reverses the payment voucher.
            After this, the invoice shows as outstanding again.
  IMPORTANT: Do NOT use PUT /invoice/:createCreditNote for bank return tasks — that cancels the invoice,
             it does not restore the outstanding balance. Only use :reverse on the payment voucher.
  NOTE: The placeholder for the voucher id from a single GET /invoice/{id} response is:
        $responses.1.value.voucher.id  (where 1 = the step index of the GET /invoice/{id} call)

Supplier invoice (leverandørfaktura / fatura do fornecedor / Lieferantenrechnung):
  Use POST /supplierInvoice (camelCase, no slash — NOT /supplier/invoice which gives 405).
  REQUIRED body fields: invoiceDate ("YYYY-MM-DD"), invoiceDueDate ("YYYY-MM-DD")
  Optional but important: supplier ({{"id": SUPPLIER_ID}}), invoiceNumber ("string"),
    amountExcludingVatCurrency (number — amount excl. VAT in the invoice currency)
  Flow:
    1. GET /supplier?organizationNumber=X or GET /supplier?name=X to look up supplier (SEARCH FIRST)
    2. POST /supplierInvoice: {{"invoiceDate": "YYYY-MM-DD", "invoiceDueDate": "YYYY-MM-DD",
         "supplier": {{"id": "$responses.0.values.0.id"}},
         "invoiceNumber": "INV-2026-XXXX",
         "amountExcludingVatCurrency": AMOUNT}}
  The system automatically generates ledger postings (accounts 2400, 2710 etc).
  Do NOT also post a /ledger/voucher for the same supplier invoice — it causes duplicate bookings.

Ledger voucher (bilag):
  POST /ledger/voucher
  body: {{"date": "YYYY-MM-DD", "description": "...", "postings": [{{"account": {{"id": ACCT_ID}}, "amount": NUMBER}}]}}
  CRITICAL: The line-items array field is "postings" — NOT "vouchers". Using "vouchers" causes 422.
  CRITICAL: Each posting MUST include "row" starting from 1 — row 0 is system-reserved and causes 422:
    {{"row": 1, "account": {{"id": INT}}, "amount": NUMBER}}
    {{"row": 2, "account": {{"id": INT}}, "amount": NUMBER}}
  Positive = debit, negative = credit. Every voucher must balance (sum of all amounts = 0).
  Example depreciation entry:
    {{"row": 1, "account": {{"id": EXPENSE_ACCOUNT_ID}}, "amount": 91175}},   <- debit expense account
    {{"row": 2, "account": {{"id": ASSET_ACCOUNT_ID}},   "amount": -91175}}   <- credit asset
  DO NOT add "department", "customDimensions", "dimension", "vouchers", "voucherRows", "voucherType" fields to the voucher body — these cause 422.
  Do NOT add "supplier" at the VOUCHER level — invalid there.
  The only valid top-level fields on POST /ledger/voucher are: date, description, postings.
  The only valid fields per posting are: row (required, starts at 1), account (with id), amount, and optionally vatType, description, or supplier.
  SUPPLIER INVOICE VOUCHER: When posting to account 2400 (Leverandørgjeld), Tripletex REQUIRES supplier on that posting:
    {{"row": N, "account": {{"id": ACCOUNT_2400_ID}}, "amount": -TOTAL, "supplier": {{"id": SUPPLIER_ID}}}}
    Include supplier ONLY on the 2400 posting — not on expense or VAT postings.
  SYSTEM-GENERATED POSTINGS ERROR: If you get 422 "Posteringene er systemgenererte og kan ikke opprettes eller endres på utsiden av Tripletex",
    it means Tripletex automatically generates those postings (e.g. accounts 1500 Kundefordringer, 2740, 3400 in invoice/reminder contexts).
    In that case: skip the voucher entirely — do NOT attempt to post to those accounts manually.
  GET /ledger/account to find account IDs by number (e.g. params: {{"number": "1500", "fields": "id,number,name"}})
  If GET /ledger/account returns count: 0 for an account, skip the voucher that depends on it.
  DELETE /ledger/voucher/{{id}}: GET /ledger/voucher first → DELETE /ledger/voucher/$responses.N.values.0.id
  PUT /ledger/voucher/{{id}}/:reverse  — reverses a voucher by creating a counter-entry (used for bank return):
    REQUIRED query param: date=YYYY-MM-DD. No request body.
    Returns 200 with the new reversed voucher. The original invoice will show as outstanding again.

Ledger postings (posteringer):
  GET /ledger/posting with params: {{"dateFrom": "YYYY-MM-DD", "dateTo": "YYYY-MM-DD", "fields": "id,date,description,amount,account(id,number,name)"}}
  NOTE: To get nested account fields use parentheses syntax: account(id,number,name) — NOT dot notation (account.id causes 400).
  When analyzing postings to compare two periods, make two GET /ledger/posting calls (one per period).

=== ENDPOINTS THAT DO NOT EXIST — NEVER USE ===
The following endpoints return 404 or 405 and must never be called:
  POST /accounting/dimension              → 404. Does NOT exist.
  POST /accounting/dimension/{{id}}/value → 404. Does NOT exist.
  Do NOT add "dimension", "customDimensions", or any dimension-related fields to ledger posting objects.
  If a task asks to create a custom accounting dimension or link a voucher to a dimension:
    - Skip the dimension creation entirely
    - Post the voucher on the correct account without any dimension reference
  GET /vat/type                          → 404. Use hardcoded vatType IDs instead.
  POST /supplier/invoice                 → 405. Use POST /supplierInvoice (camelCase) instead.
  POST /invoice/fromTimesheet            → 405.
  POST /timesheet (without /entry)       → 404. Use POST /timesheet/entry.
  PUT /invoice/{{id}}/:reversePayment    → 404. Does NOT exist.
  POST /invoice/payment                  → 405. Does NOT exist. Use PUT /invoice/{{id}}/:payment instead.
  If a task asks to reverse a bank return (bankretur) so the invoice shows as outstanding again:
    Use PUT /ledger/voucher/{{voucherId}}/:reverse?date=TODAY (see bank return reversal pattern above).
    Do NOT use :reversePayment. Do NOT use :createCreditNote (that cancels the invoice, not restores it).

=== BETA ENDPOINTS — NEVER USE (returns 403 Forbidden) ===
The following endpoints are tagged [BETA] in the Tripletex API and will always return 403.
Do NOT generate calls to any of these — they will always fail:
  DELETE /customer/{{id}}          → BETA, always 403. Do NOT delete customers.
  PUT /project/{{id}}              → BETA, always 403. Cannot update projects via API.
  DELETE /project/{{id}}           → BETA, always 403. Cannot delete projects via API.
  PUT /order/orderline/{{id}}      → BETA, always 403. Cannot update order lines via API.
  DELETE /order/orderline/{{id}}   → BETA, always 403. Cannot delete order lines via API.
  POST /travelExpense/cost         → BETA, always 403 in validator. Cannot add individual expense cost lines via API.
    If you need to add costs: use POST /travelExpense (header only). Do NOT try to add individual cost lines.
If the task asks you to do something only possible via a BETA endpoint, skip that action entirely.

=== FIELDS PARAM RULES ===
CRITICAL: The "fields" query param value NEVER uses dot notation. Dot notation (e.g. "account.id") causes 400 "Illegal fields filter: Fields filter contains '.'".
  - For nested objects use parentheses: account(id,number,name) — NOT account.id, account.number
  - For flat fields just list them: "id,name,amount"
  - This rule applies to ALL endpoints: GET /ledger/posting, GET /invoice, GET /customer, etc.
  - Note: "customer.id" as a QUERY FILTER PARAM KEY (not in the fields= value) is fine for filtering.

=== PLACEHOLDER SYNTAX ===
"$responses.N.value.id"              -> id from POST/PUT/single-GET response at step N
"$responses.N.value.version"         -> version from single-item response at step N
"$responses.N.value.voucher.id"      -> nested field — e.g. voucher id from GET /invoice/{id}?fields=id,voucher(id)
"$responses.N.values.0.id"           -> id of first item from GET list at step N
"$responses.N.values.0.version"      -> version of first item from GET list at step N
"$responses.N.values.1.id"           -> id of second item from GET list at step N
"$responses.N.values.0.account.name" -> nested sub-field within list item (e.g. account name from ledger posting)
CRITICAL: Only simple dot-path and numeric index placeholders are supported.
  DO NOT use JSONPath filter expressions like $responses.N.values[?(@.field==value)].id — NOT supported, will fail.
  DO NOT use ternary expressions like ($responses.0.count > 0 ? $responses.0.values.0.id : 123) — NOT supported, will fail.
  DO NOT use JavaScript or any conditional logic — only static values and $responses.N.* placeholders.

=== OUTPUT FORMAT ===
Respond with ONLY a raw JSON object - no markdown, no code fences, no explanation.
Each call object MUST have EXACTLY these keys: "method" (HTTP verb), "endpoint" (URL path), "body" (optional JSON object), "params" (optional query params object).
CRITICAL: use "endpoint" not "path" or "url" for the URL path field.
CRITICAL: NEVER use "tool_code", "function_call", "tool_name", "action", or any other format. Only REST API calls.
CRITICAL: NEVER use JavaScript, ternary expressions, or conditional logic anywhere in the JSON. Only static values and $responses.N.* placeholders.

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


def build_repair_prompt(original_prompt: str, today: str, responses: list, errors_422: list, skipped_calls: list = None) -> str:
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

    skipped_section = ""
    if skipped_calls:
        skipped_lines = [
            f"  {c.get('method','?')} {c.get('endpoint','?')}: body={json.dumps(c.get('body') or {})[:200]}"
            for c in skipped_calls
        ]
        skipped_section = f"""
SKIPPED CALLS (were skipped because a dependency failed — must also be included in your repair):
These calls could not run because a prior call failed. Now that you are fixing that failure,
you MUST include corrected versions of ALL skipped calls too, referencing the new IDs you create:
{chr(10).join(skipped_lines)}
"""

    return f"""You are a Tripletex accounting API expert. Some API calls failed with validation or conflict errors (422 or 409).
Generate corrected replacement calls needed to fix these failures — AND include any skipped downstream calls.

ORIGINAL TASK: "{original_prompt}"
TODAY: {today}

PREVIOUSLY SUCCEEDED (you can reference these via $responses.N.value.id):
{success_section}

FAILED CALLS:
{error_section}
{skipped_section}
Read the error messages carefully and generate corrected calls.
Each call object MUST use "endpoint" (not "path" or "url") for the URL path field.
REMINDER for POST /ledger/voucher: only valid fields are date, description, postings.
  Each posting only has: account ({{id}}), amount, optionally description.
  DO NOT use voucherRows, voucherType, supplier, department, customDimensions, vouchers — these cause 422.
REMINDER for fields param on ANY endpoint: NEVER use dot notation (e.g. "account.id", "customer.id") — causes 400.
  Use parentheses for nested fields: account(id,number,name). For flat fields: "id,name,amount".
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
    errors_422, skipped_calls = execute_calls(calls, responses, base_url, session_token, deadline)

    # --- One repair pass for 422 validation errors and 409 version conflicts ---
    if (errors_422 or skipped_calls) and (deadline - time.time()) > 40:
        if errors_422:
            logger.info("Attempting repair pass for %d error(s) (422/409), %d skipped call(s)", len(errors_422), len(skipped_calls))
        else:
            logger.info("Attempting repair pass for %d skipped call(s) (no 422 errors)", len(skipped_calls))
        repair_prompt = build_repair_prompt(prompt, today, responses, errors_422, skipped_calls)
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
