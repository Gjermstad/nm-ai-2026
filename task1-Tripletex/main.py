from fastapi import FastAPI, Request, HTTPException
import base64
import requests
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize Vertex AI
vertexai.init(project="ai-nm26osl-1730", location="europe-west4")

@app.post("/solve")
async def solve(request: Request):
    try:
        body = await request.json()
        prompt = body.get("prompt")
        proxy_url = body.get("proxyUrl")
        session_token = body.get("sessionToken")

        if not all([prompt, proxy_url, session_token]):
            logger.error("Missing required fields")
            raise HTTPException(status_code=400, detail="Missing required fields")

        # 1. Parse the prompt with an LLM
        model = GenerativeModel("gemini-2.5-pro-preview-03-25")
        llm_prompt = f"""
You are an expert in the Tripletex API. Your task is to convert a natural language prompt into a sequence of Tripletex API requests.

The user wants to perform the following action: "{prompt}".

Based on this, determine the correct API endpoints, HTTP methods, and request bodies.

Your response must be a JSON object containing a list of API calls. For example:

{{
  "calls": [
    {{
      "method": "POST",
      "endpoint": "/v2/customer",
      "body": {{
        "name": "New Customer AS"
      }}
    }},
    {{
      "method": "POST",
      "endpoint": "/v2/invoice",
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

- **POST /v2/employee**: Create employee (firstName, lastName required)
- **GET /v2/employee**: List employees
- **POST /v2/customer**: Create customer (name required)
- **POST /v2/product**: Create product (name, price required)
- **POST /v2/invoice**: Create invoice (customer.id, invoiceDate, dueDate, orderLines required)
- **POST /v2/invoice/{{id}}/:payment**: Register payment
- **POST /v2/travelExpense**: Create travel expense
- **DELETE /v2/travelExpense/{{id}}**: Delete travel expense
- **POST /v2/project**: Create project (name, customer.id required)
- **POST /v2/department**: Create department (name required)
- **POST /v2/ledger/voucher**: Create voucher/accounting entry

Now, generate the API request for the prompt: "{prompt}"
"""
        llm_response = model.generate_content([Part.from_text(llm_prompt)])

        try:
            api_request_details = llm_response.candidates[0].content.parts[0].text
            api_request_details = api_request_details.strip().replace("```json", "").replace("```", "")
            api_calls = json.loads(api_request_details)
        except (ValueError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"LLM Response: {llm_response.text}")
            raise HTTPException(status_code=500, detail="Failed to parse LLM response")

        # 2. Call the Tripletex API via the proxy URL
        auth_header = base64.b64encode(f"0:{session_token}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json",
        }

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

                api_url = f"{proxy_url}{api_call['endpoint']}"
                logger.info(f"Calling Tripletex API: {api_call['method']} {api_url}")
                response = requests.request(
                    method=api_call["method"],
                    url=api_url,
                    headers=headers,
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
