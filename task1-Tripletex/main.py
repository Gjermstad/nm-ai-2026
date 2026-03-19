from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import base64
import requests
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
import logging
import re
from typing import List, Optional
from datetime import date

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Vertex AI
vertexai.init(project="ai-nm26osl-1730", location="us-central1")

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


@app.post("/solve")
async def solve(solve_request: SolveRequest):
    prompt = solve_request.prompt
    base_url = solve_request.tripletex_credentials.base_url
    session_token = solve_request.tripletex_credentials.session_token
    files = solve_request.files or []

    logger.info(f"Received prompt: {prompt}")

    # 1. Parse the prompt with Gemini
    try:
        model = GenerativeModel("gemini-2.0-flash")

        content_parts = []
        for file in files:
            content_parts.append(
                Part.from_data(
                    base64.b64decode(file.content_base64),
                    mime_type=file.mime_type
                )
            )

        llm_prompt = f"""You are a Tripletex accounting API expert. Convert the task below into a precise sequence of Tripletex v2 REST API calls.

TASK (may be in any language - Norwegian, English, Spanish, German, French, Portuguese, Nynorsk):
"{prompt}"

TODAY'S DATE: {TODAY}

=== CRITICAL: REQUIRED FIELDS ===

POST /employee:
  REQUIRED: firstName, lastName, userType, email, department ({{"id": DEPT_ID}})
  userType enum: "STANDARD", "EXTENDED", "NO_ACCESS"
  If prompt says "administrator"/"kontoadministrator"/"admin" use "EXTENDED", otherwise "STANDARD"
  email: use from prompt if given, else generate as firstname.lastname@example.com (lowercase)
  department.id: ALWAYS do GET /department first to get the ID, use "$responses.0.values.0.id"

POST /customer:
  REQUIRED: name
  Optional: email, phoneNumber, isCustomer (true)

POST /department:
  REQUIRED: name

POST /project:
  REQUIRED: name, startDate ("YYYY-MM-DD"), projectManager ({{"id": EMPLOYEE_ID}})
  Optional: customer ({{"id": CUSTOMER_ID}})

POST /order:
  REQUIRED: customer ({{"id": ID}}), orderDate ("YYYY-MM-DD")
  orderLines: [{{"description": "string", "count": 1, "unitPriceExcludingVatCurrency": 1000}}]

POST /invoice:
  REQUIRED: invoiceDate ("YYYY-MM-DD"), invoiceDueDate ("YYYY-MM-DD"), orders: [{{"id": ORDER_ID}}]

POST /travelExpense:
  REQUIRED: employee ({{"id": ID}}), description, startDate ("YYYY-MM-DD"), endDate ("YYYY-MM-DD")

DELETE /travelExpense/{{id}}:
  No body. GET /travelExpense first to find the id, then DELETE /travelExpense/$responses.N.values.0.id

=== PLACEHOLDER SYNTAX ===
- "$responses.N.value.id"    -> id from POST/PUT response at index N
- "$responses.N.values.0.id" -> id of first item from GET list response at index N

=== OUTPUT FORMAT ===
Respond with ONLY a raw JSON object. No markdown, no code fences, no explanation.

Example for creating an employee:
{{
  "calls": [
    {{
      "method": "GET",
      "endpoint": "/department",
      "params": {{"fields": "id,name", "count": 1}}
    }},
    {{
      "method": "POST",
      "endpoint": "/employee",
      "body": {{
        "firstName": "Ola",
        "lastName": "Nordmann",
        "userType": "STANDARD",
        "email": "ola.nordmann@example.com",
        "department": {{"id": "$responses.0.values.0.id"}}
      }}
    }}
  ]
}}
"""

        content_parts.append(Part.from_text(llm_prompt))
        llm_response = model.generate_content(content_parts)
        raw_text = llm_response.candidates[0].content.parts[0].text
        logger.info(f"LLM raw response: {raw_text[:500]}")

        # Strip markdown fences if present
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        api_calls = json.loads(cleaned)

    except Exception as e:
        logger.error(f"LLM step failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM step failed: {e}")

    # 2. Execute Tripletex API calls in sequence
    responses = []
    for i, api_call in enumerate(api_calls["calls"]):
        method = api_call["method"].upper()
        endpoint = api_call["endpoint"]
        body = api_call.get("body")
        params = api_call.get("params")

        # Substitute placeholders in body
        if body:
            body_str = json.dumps(body)
            for j, prev_resp in enumerate(responses):
                # Single value response: $responses.j.value.id
                if prev_resp.get("value") and isinstance(prev_resp["value"], dict):
                    single_id = prev_resp["value"].get("id")
                    if single_id is not None:
                        body_str = body_str.replace(f'"$responses.{j}.value.id"', str(single_id))
                # List response: $responses.j.values.0.id
                if prev_resp.get("values") and len(prev_resp["values"]) > 0:
                    list_id = prev_resp["values"][0].get("id")
                    if list_id is not None:
                        body_str = body_str.replace(f'"$responses.{j}.values.0.id"', str(list_id))
            body = json.loads(body_str)

        # Substitute placeholders in endpoint path (for PUT/DELETE)
        for j, prev_resp in enumerate(responses):
            if prev_resp.get("value") and isinstance(prev_resp["value"], dict):
                single_id = prev_resp["value"].get("id")
                if single_id is not None:
                    endpoint = endpoint.replace(f"$responses.{j}.value.id", str(single_id))
            if prev_resp.get("values") and len(prev_resp["values"]) > 0:
                list_id = prev_resp["values"][0].get("id")
                if list_id is not None:
                    endpoint = endpoint.replace(f"$responses.{j}.values.0.id", str(list_id))

        api_url = f"{base_url}{endpoint}"
        logger.info(f"Call {i}: {method} {api_url} params={params} body={json.dumps(body)[:200] if body else None}")

        try:
            response = requests.request(
                method=method,
                url=api_url,
                auth=("0", session_token),
                json=body,
                params=params,
                timeout=60,
            )

            if response.status_code == 204:
                responses.append({})
                logger.info(f"Call {i} succeeded with 204 No Content")
            else:
                resp_json = response.json()
                logger.info(f"Call {i} response status={response.status_code}: {json.dumps(resp_json)[:300]}")
                if response.status_code >= 400:
                    logger.error(f"Tripletex error on call {i}: {response.status_code} {response.text}")
                    responses.append({"error": response.status_code, "detail": resp_json})
                else:
                    responses.append(resp_json)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed on call {i}: {e}")
            responses.append({"error": "request_failed", "detail": str(e)})

    logger.info("All calls completed — returning status completed")
    return {"status": "completed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)