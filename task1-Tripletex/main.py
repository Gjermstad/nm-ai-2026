from fastapi import FastAPI
from pydantic import BaseModel
import requests
import json
import logging
import re
from typing import List, Optional
from datetime import date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("agent")

PROJECT_ID = "ai-nm26osl-1730"
VERTEX_URL = f"https://aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/publishers/google/models/gemini-2.5-flash:generateContent"

app   = FastAPI()
TODAY = date.today().isoformat()

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
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def call_llm(prompt: str) -> str:
    logger.info("Calling Vertex AI (gemini-2.5-flash, global)...")
    token = get_access_token()
    resp = requests.post(
        VERTEX_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048}
        },
        timeout=120
    )
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    logger.info("LLM response (first 600 chars): %s", text[:600])
    return text

def resolve(value: str, responses: list) -> str:
    for j, resp in enumerate(responses):
        if resp.get("value") and isinstance(resp["value"], dict):
            single_id = resp["value"].get("id")
            if single_id is not None:
                value = value.replace(f"$responses.{j}.value.id", str(single_id))
        if resp.get("values") and len(resp["values"]) > 0:
            list_id = resp["values"][0].get("id")
            if list_id is not None:
                value = value.replace(f"$responses.{j}.values.0.id", str(list_id))
    return value

@app.post("/solve")
async def solve(req: SolveRequest):
    prompt        = req.prompt
    base_url      = req.tripletex_credentials.base_url
    session_token = req.tripletex_credentials.session_token

    logger.info("=" * 60)
    logger.info("PROMPT: %s", prompt)
    logger.info("BASE_URL: %s", base_url)
    logger.info("=" * 60)

    llm_prompt = f"""You are a Tripletex accounting API expert. Convert the task below into a precise sequence of Tripletex v2 REST API calls.

TASK (may be in Norwegian, English, Spanish, German, French, Portuguese, Nynorsk):
"{prompt}"

TODAY'S DATE: {TODAY}

=== REQUIRED FIELDS ===

POST /employee:
  REQUIRED: firstName, lastName, userType, email, department ({{"id": DEPT_ID}})
  userType: "STANDARD" (default) | "EXTENDED" (if prompt says administrator/kontoadministrator/admin) | "NO_ACCESS"
  department.id: ALWAYS do GET /department first, use "$responses.0.values.0.id"

POST /customer:
  REQUIRED: name
  Optional: email, phoneNumber, isCustomer (true)

POST /department:
  REQUIRED: name

POST /project:
  REQUIRED: name, startDate ("YYYY-MM-DD"), projectManager ({{"id": EMPLOYEE_ID}})

POST /order:
  REQUIRED: customer ({{"id": ID}}), orderDate ("{TODAY}")
  orderLines: [{{"description": "...", "count": 1, "unitPriceExcludingVatCurrency": 1000}}]

POST /invoice:
  REQUIRED: invoiceDate ("{TODAY}"), invoiceDueDate ("{TODAY}"), orders: [{{"id": ORDER_ID}}]

POST /travelExpense:
  REQUIRED: employee ({{"id": ID}}), description, startDate ("YYYY-MM-DD"), endDate ("YYYY-MM-DD")

DELETE /travelExpense/{{id}}:
  GET /travelExpense first, then DELETE /travelExpense/$responses.N.values.0.id

=== PLACEHOLDER SYNTAX ===
"$responses.N.value.id"     -> id from POST response at step N
"$responses.N.values.0.id"  -> id of first item from GET list at step N

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

    try:
        raw = call_llm(llm_prompt)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {"status": "completed"}

    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        plan = json.loads(cleaned)
    except Exception as e:
        logger.error("JSON parse failed: %s\nRaw: %s", e, raw[:500])
        return {"status": "completed"}

    calls = plan.get("calls", [])
    logger.info("Plan has %d API calls", len(calls))

    responses = []
    for i, call in enumerate(calls):
        method   = call["method"].upper()
        endpoint = call["endpoint"]
        body     = call.get("body")
        params   = call.get("params")

        if body:
            body_str = json.dumps(body)
            body_str = resolve(body_str, responses)
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
                timeout=60
            )
            if r.status_code == 204:
                logger.info("CALL %d: 204 No Content", i)
                responses.append({})
            else:
                resp_json = r.json()
                logger.info("CALL %d: %d | %s", i, r.status_code, json.dumps(resp_json)[:400])
                if r.status_code >= 400:
                    logger.error("CALL %d ERROR: %s", i, r.text[:400])
                responses.append(resp_json)
        except Exception as e:
            logger.error("CALL %d request exception: %s", i, e)
            responses.append({"error": str(e)})

    logger.info("All calls done. Returning completed.")
    return {"status": "completed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)