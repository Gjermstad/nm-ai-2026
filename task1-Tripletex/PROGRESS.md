# Progress Report: Tripletex AI Accounting Agent

## 1. What we have built so far

We have built a FastAPI application that acts as an AI-powered accounting agent for Tripletex. The application exposes a `/solve` endpoint that accepts a natural language prompt and then uses a Gemini large language model to convert the prompt into one or more Tripletex API calls.

The application currently supports:
*   Parsing natural language prompts into Tripletex API calls.
*   Executing multiple API calls in sequence.
*   Handling dependencies between API calls (e.g., creating a customer and then creating an invoice for that customer).
*   Authentication with the Tripletex API via a proxy.
*   Robust error handling and logging.

## 2. What still needs to be done

*   **Deploy to Cloud Run:** The application needs to be containerized and deployed to Google Cloud Run to be accessible as a public service.
*   **Test against sandbox:** The application needs to be thoroughly tested against the Tripletex sandbox environment to ensure that it is working as expected.
*   **Submit:** Once the application is deployed and tested, it can be submitted for the competition.

## 3. Key technical details

*   **Project ID:** `ai-nm26osl-1730`
*   **Region:** `europe-west4`
*   **Model name:** `gemini-2.5-pro-preview-03-25`
*   **API endpoints supported:**
    *   `POST /v2/employee`: Create employee
    *   `GET /v2/employee`: List employees
    *   `POST /v2/customer`: Create customer
    *   `POST /v2/product`: Create product
    *   `POST /v2/invoice`: Create invoice
    *   `POST /v2/invoice/{id}/:payment`: Register payment
    *   `POST /v2/travelExpense`: Create travel expense
    *   `DELETE /v2/travelExpense/{id}`: Delete travel expense
    *   `POST /v2/project`: Create project
    *   `POST /v2/department`: Create department
    *   `POST /v2/ledger/voucher`: Create voucher/accounting entry

## 4. How to run the app locally for testing

To run the application locally for testing, follow these steps:

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Run the application:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8080
    ```
3.  **Send requests to the `/solve` endpoint:**
    You can use a tool like `curl` or Postman to send POST requests to `http://localhost:8080/solve`. The request body should be a JSON object with the following structure:
    ```json
    {
      "prompt": "Create an employee named John Doe",
      "proxyUrl": "https://...",
      "sessionToken": "..."
    }
    ```
