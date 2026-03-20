"""Unit tests for core agent logic in main.py."""
import time
import pytest
from unittest.mock import MagicMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import resolve, extract_json, execute_calls, MAX_CALLS


# ---------------------------------------------------------------------------
# resolve()
# ---------------------------------------------------------------------------

def test_resolve_value_field():
    responses = [{"value": {"id": 42, "version": 3, "name": "Acme"}}]
    assert resolve("$responses.0.value.id", responses) == "42"
    assert resolve("$responses.0.value.version", responses) == "3"
    assert resolve("$responses.0.value.name", responses) == "Acme"


def test_resolve_values_index_field():
    responses = [
        {},
        {"values": [
            {"id": 10, "name": "first"},
            {"id": 20, "name": "second"},
            {"id": 30, "name": "third"},
        ]},
    ]
    assert resolve("$responses.1.values.2.name", responses) == "third"
    assert resolve("$responses.1.values.0.id", responses) == "10"


def test_resolve_unmatched_left_intact():
    responses = [{"value": {"id": 1}}]
    # Out-of-range step index
    result = resolve("$responses.5.value.id", responses)
    assert result == "$responses.5.value.id"
    # Missing field
    result = resolve("$responses.0.value.nonexistent", responses)
    assert result == "$responses.0.value.nonexistent"
    # Out-of-range list index
    responses2 = [{"values": [{"id": 1}]}]
    result = resolve("$responses.0.values.9.id", responses2)
    assert result == "$responses.0.values.9.id"


def test_resolve_multiple_placeholders():
    responses = [
        {"values": [{"id": 7}]},
        {"value": {"id": 99}},
    ]
    text = '{"deptId": "$responses.0.values.0.id", "empId": "$responses.1.value.id"}'
    result = resolve(text, responses)
    assert '"deptId": "7"' in result
    assert '"empId": "99"' in result


# ---------------------------------------------------------------------------
# extract_json()
# ---------------------------------------------------------------------------

def test_extract_json_clean():
    data = extract_json('{"calls": []}')
    assert data == {"calls": []}


def test_extract_json_fenced():
    text = '```json\n{"calls": [{"method": "GET"}]}\n```'
    data = extract_json(text)
    assert data["calls"][0]["method"] == "GET"


def test_extract_json_with_preamble():
    text = 'Sure, here is your plan:\n{"calls": [{"method": "POST"}]}'
    data = extract_json(text)
    assert data is not None
    assert data["calls"][0]["method"] == "POST"


def test_extract_json_invalid_returns_none():
    assert extract_json("this is not json") is None
    assert extract_json("") is None
    assert extract_json("```\nnot json\n```") is None


# ---------------------------------------------------------------------------
# execute_calls()
# ---------------------------------------------------------------------------

def _fake_response(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    r.text = str(json_body)
    return r


def test_executor_skips_malformed_call():
    """Missing 'method' key should be skipped; responses still gets a placeholder."""
    calls = [
        {"endpoint": "/employee"},          # missing method → skip
        {"method": "GET", "endpoint": "/department"},  # valid
    ]
    responses = []
    deadline = time.time() + 60

    with patch("main.requests.request", return_value=_fake_response(200, {"values": [{"id": 1}]})):
        execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert len(responses) == 2
    assert responses[0] == {"error": "malformed call"}
    assert responses[1].get("values") is not None


def test_executor_respects_call_cap():
    """Should stop after MAX_CALLS regardless of plan length."""
    calls = [{"method": "GET", "endpoint": f"/employee?page={i}"} for i in range(MAX_CALLS + 5)]
    responses = []
    deadline = time.time() + 60

    with patch("main.requests.request", return_value=_fake_response(200, {"values": []})):
        execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert len(responses) == MAX_CALLS


def test_executor_aborts_on_403():
    """403 should stop execution immediately — no further calls made."""
    calls = [
        {"method": "GET", "endpoint": "/employee"},
        {"method": "GET", "endpoint": "/customer"},  # should never run
    ]
    responses = []
    deadline = time.time() + 60

    call_count = 0
    def fake_request(**kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(403)

    with patch("main.requests.request", fake_request):
        execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert call_count == 1
    assert len(responses) == 0  # 403 breaks before append


def test_executor_aborts_on_429():
    """429 rate limit should stop execution immediately."""
    calls = [
        {"method": "GET", "endpoint": "/employee"},
        {"method": "GET", "endpoint": "/customer"},  # should never run
    ]
    responses = []
    deadline = time.time() + 60

    call_count = 0
    def fake_request(**kwargs):
        nonlocal call_count
        call_count += 1
        return _fake_response(429)

    with patch("main.requests.request", fake_request):
        execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert call_count == 1
    assert len(responses) == 0


def test_executor_collects_422_errors():
    """422 responses are returned in the errors list with status field."""
    calls = [{"method": "POST", "endpoint": "/employee", "body": {}}]
    responses = []
    deadline = time.time() + 60
    error_body = {"validationMessages": [{"field": "firstName", "message": "missing firstName"}]}

    with patch("main.requests.request", return_value=_fake_response(422, error_body)):
        errors = execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert len(errors) == 1
    assert errors[0]["call"]["endpoint"] == "/employee"
    assert errors[0]["status"] == 422


def test_executor_collects_409_errors():
    """409 revision conflicts are included in the repair list."""
    calls = [{"method": "PUT", "endpoint": "/employee/42", "body": {"version": 1}}]
    responses = []
    deadline = time.time() + 60
    error_body = {"status": 409, "code": 8000, "message": "Revision exception"}

    with patch("main.requests.request", return_value=_fake_response(409, error_body)):
        errors = execute_calls(calls, responses, "http://example.com", "tok", deadline)

    assert len(errors) == 1
    assert errors[0]["status"] == 409
