from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import logging
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

app = FastAPI()


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
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192},
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

        method   = call["method"].upper()
        endpoint = call.get("endpoint", "")
        body     = call.get("body")
        params   = call.get("params")

        if body:
            body_str = resolve(json.dumps(body), responses)
            body = json.loads(body_str)
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
            if r.status_code == 403:
                logger.error("CALL %d: 403 Forbidden — invalid/expired token, aborting", i)
                break
            if r.status_code == 204:
                logger.info("CALL %d: 204 No Content", i)
                responses.append({})
            else:
                resp_json = r.json()
                logger.info("CALL %d: %d | %s", i, r.status_code, json.dumps(resp_json)[:400])
                if r.status_code == 422:
                    logger.error("CALL %d 422: %s", i, json.dumps(resp_json)[:400])
                    errors_422.append({
                        "step": len(responses),
                        "call": call,
                        "error": resp_json,
                    })
                elif r.status_code >= 400:
                    logger.error("CALL %d ERROR %d: %s", i, r.status_code, r.text[:400])
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
  Optional: email, phoneNumber, isCustomer (true)

PUT /customer/{{id}}:
  REQUIRED: version (from GET), name
  Flow: GET /customer?name=X → PUT /customer/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"

POST /department:
  REQUIRED: name

POST /project:
  REQUIRED: name, startDate ("YYYY-MM-DD"), projectManager ({{"id": EMPLOYEE_ID}})

POST /order:
  REQUIRED: customer ({{"id": ID}}), orderDate ("{today}")
  orderLines: [{{"description": "...", "count": 1, "unitPriceExcludingVatCurrency": 1000}}]

POST /invoice:
  REQUIRED: invoiceDate, invoiceDueDate, orders: [{{"id": ORDER_ID}}]
  Use dates from the prompt; default to "{today}" if not specified.

POST /product:
  REQUIRED: name
  Optional: costExcludingVatCurrency (unit cost), priceExcludingVatCurrency (sale price)

POST /travelExpense:
  REQUIRED: employee ({{"id": ID}}), description, startDate ("YYYY-MM-DD"), endDate ("YYYY-MM-DD")

PUT /travelExpense/{{id}}:
  REQUIRED: version (from GET), employee, description, startDate, endDate
  Flow: GET /travelExpense → PUT /travelExpense/$responses.0.values.0.id
  body must include: "version": "$responses.0.values.0.version"

DELETE /travelExpense/{{id}}:
  GET /travelExpense first, then DELETE /travelExpense/$responses.N.values.0.id

=== ADVANCED PATTERNS (Tier 2/3) ===

Register invoice payment:
  GET /invoice?invoiceDateFrom=2020-01-01&invoiceDateTo=2030-12-31 → find invoice id
  POST /invoice/$responses.0.values.0.id/payment
  body: {{"paymentDate": "YYYY-MM-DD", "paidAmount": <amount>, "paymentTypeId": 1}}

Issue credit note (kreditnota):
  GET /invoice to find the invoice → POST /invoice/$responses.0.values.0.id/creditNote
  body: {{"date": "YYYY-MM-DD", "comment": "..."}}

Ledger voucher (bilag):
  POST /ledger/voucher
  body: {{"date": "YYYY-MM-DD", "description": "...", "vouchers": [{{"account": {{"id": ACCT_ID}}, "amount": 0}}]}}
  GET /ledger/account to find account IDs by number (e.g. params: {{"number": "1500"}})

=== PLACEHOLDER SYNTAX ===
"$responses.N.value.id"         -> id from POST/PUT response at step N
"$responses.N.value.version"    -> version from single-item response at step N
"$responses.N.values.0.id"      -> id of first item from GET list at step N
"$responses.N.values.0.version" -> version of first item from GET list at step N
"$responses.N.values.1.id"      -> id of second item from GET list at step N

=== OUTPUT FORMAT ===
Respond with ONLY a raw JSON object - no markdown, no code fences, no explanation.

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
    # Summarise what succeeded to give the LLM context for follow-up calls
    succeeded = []
    failed_steps = {e["step"] for e in errors_422}
    for i, resp in enumerate(responses):
        if i in failed_steps:
            continue
        v = resp.get("value")
        if isinstance(v, dict) and v.get("id"):
            succeeded.append(f"  Step {i}: id={v['id']}")

    success_section = ("\n".join(succeeded)) if succeeded else "  (none)"

    error_lines = []
    for e in errors_422:
        call = e["call"]
        error_lines.append(
            f"  Step {e['step']}: {call['method']} {call['endpoint']}\n"
            f"    body: {json.dumps(call.get('body', {}))[:300]}\n"
            f"    error: {json.dumps(e['error'])[:400]}"
        )
    error_section = "\n".join(error_lines)

    return f"""You are a Tripletex accounting API expert. Some API calls failed with 422 validation errors.
Generate ONLY the corrected replacement calls needed to fix these failures.

ORIGINAL TASK: "{original_prompt}"
TODAY: {today}

PREVIOUSLY SUCCEEDED (you can reference these via $responses.N.value.id):
{success_section}

FAILED CALLS:
{error_section}

Read the error messages carefully and generate corrected calls.
Return ONLY a raw JSON object — no markdown, no explanation:
{{"calls": [...]}}
"""


# --- Main endpoint ---

@app.post("/solve")
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

    calls = plan.get("calls", [])
    logger.info("Plan has %d API calls", len(calls))

    # --- Execute initial plan ---
    responses  = []
    errors_422 = execute_calls(calls, responses, base_url, session_token, deadline)

    # --- One repair pass for 422 validation errors ---
    if errors_422 and (deadline - time.time()) > 40:
        logger.info("Attempting repair pass for %d 422 error(s)", len(errors_422))
        repair_prompt = build_repair_prompt(prompt, today, responses, errors_422)
        try:
            raw_repair   = call_llm(repair_prompt, deadline)
            repair_plan  = extract_json(raw_repair)
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
