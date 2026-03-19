from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import base64
import requests
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
import logging
from typing import List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Vertex AI
vertexai.init(project="ai-nm26osl-1730", location="europe-west4")

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

@app.post("/solve")
async def solve(solve_request: SolveRequest):
    try:
        prompt = solve_request.prompt
        base_url = solve_request.tripletex_credentials.base_url
        session_token = solve_request.tripletex_credentials.session_token
        files = solve_request.files or []

        # 1. Parse the prompt with an LLM
        model = GenerativeModel("gemini-2.5-pro-preview-03-25")
        
        content_parts = []
        for file in files:
            content_parts.append(Part.from_data(base64.b64decode(file.content_base64), mime_type=file.mime_type))

        llm_prompt = f"""
You are an expert in the Tripletex API. Your task is to convert a natural language prompt into a sequence of Tripletex API requests.

The user wants to perform the following action: "{prompt}".

Based on this, determine the correct API endpoints, HTTP methods, and request bodies.

Your response must be a JSON object containing a list of API calls. For example:

{{
  "calls": [
    {{
      "method": "POST",
      "endpoint": "/customer",
      "body": {{
        "name": "New Customer AS"
      }}
    }},
    {{
      "method": "POST",
      "endpoint": "/invoice",
      "body": {{
        "customer": {{
          "id": "$responses.0.value.id"
        }},
        "invoiceDate": "2026-03-19",
        "dueDate": "2026-04-02",
        "orderLines": [
          {{
            "description": "Test product",
            "unitPrice": 1000
          }}
        ]
      }}
    }}
  ]
}}

Use placeholders like `$responses.0.value.id` to reference values from previous responses. The number after `responses.` is the index of the previous call.

Here are the key Tripletex API endpoints to support:

- **POST /employee**: Create employee (firstName, lastName required)
- **GET /employee**: List employees
- **POST /customer**: Create customer (name required)
- **POST /product**: Create product (name, price required)
- **POST /invoice**: Create invoice (customer.id, invoiceDate, dueDate, orderLines required)
- **POST /invoice/{{id}}/:payment**: Register payment
- **POST /travelExpense**: Create travel expense
- **DELETE /travelExpense/{{id}}**: Delete travel expense
- **POST /project**: Create project (name, customer.id required)
- **POST /department**: Create department (name required)
- **POST /ledger/voucher**: Create voucher/accounting entry

Now, generate the API request for the prompt: "{prompt}"
"""
        content_parts.append(Part.from_text(llm_prompt))
        llm_response = model.generate_content(content_parts)

        try:
            api_request_details = llm_response.candidates[0].content.parts[0].text
            api_request_details = api_request_details.strip().replace("```json", "").replace("```", "")
            api_calls = json.loads(api_request_details)
        except (ValueError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"LLM Response: {llm_response.text}")
            raise HTTPException(status_code=500, detail="Failed to parse LLM response")

        # 2. Call the Tripletex API
        responses = []
        for i, api_call in enumerate(api_calls['calls']):
            try:
                # Substitute placeholders
                body = api_call.get("body")
                if body:
                    body_str = json.dumps(body)
                    for j, prev_resp in enumerate(responses):
                        body_str = body_str.replace(f'"$responses.{j}.value.id"', str(prev_resp.get('value', {}).get('id')))
                    api_call["body"] = json.loads(body_str)

                api_url = f"{base_url}{api_call['endpoint']}"
                logger.info(f"Calling Tripletex API: {api_call['method']} {api_url}")
                response = requests.request(
                    method=api_call["method"],
                    url=api_url,
                    auth=("0", session_token),
                    json=api_call.get("body"),
                    timeout=30
                )
                response.raise_for_status()  # Raise an exception for bad status codes
                responses.append(response.json())
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to call Tripletex API: {e}")
                if e.response is not None:
                    logger.error(f"Tripletex API response: {e.response.text}")
                    raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
                raise HTTPException(status_code=500, detail="Failed to call Tripletex API")

        # 3. Return {"status": "completed"}
        logger.info("Successfully completed the request")
        return {"status": "completed"}

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
