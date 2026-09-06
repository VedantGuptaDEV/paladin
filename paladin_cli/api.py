"""
api.py — HTTP client for the Paladin backend (default: http://localhost:8000)
"""

import json
import sys
from typing import Any
from urllib import request, error as urllib_error
from urllib.parse import urlencode

import config as cfg


def _base() -> str:
    return cfg.get("api_url", "http://localhost:8000")


def _timeout() -> int:
    return cfg.get("timeout", 30)


def _request(method: str, path: str, body: Any = None) -> Any:
    url = f"{_base()}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=_timeout()) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else None
    except urllib_error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code} {method} {path}: {body_text}") from e
    except urllib_error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Paladin backend at {_base()}.\n"
            f"  → Make sure the server is running (`paladin start`).\n"
            f"  → Reason: {e.reason}"
        ) from e


def get(path: str) -> Any:
    return _request("GET", path)


def post(path: str, body: Any = None) -> Any:
    return _request("POST", path, body)


def patch(path: str, body: Any = None) -> Any:
    return _request("PATCH", path, body)


def delete(path: str) -> Any:
    return _request("DELETE", path)


# ─── Sessions ──────────────────────────────────────────────────────────────────

def get_sessions() -> list:
    return get("/sessions") or []


def get_session(session_id: str) -> dict:
    return get(f"/sessions/{session_id}")


def create_session(prompt: str) -> dict:
    return post("/sessions", {"user_prompt": prompt})


def get_messages(session_id: str) -> list:
    return get(f"/sessions/{session_id}/messages") or []


def send_message(session_id: str, content: str) -> dict:
    return post(f"/sessions/{session_id}/messages", {"content": content})


def get_dashboard_stats() -> dict:
    return get("/dashboard/stats") or {}


# ─── Approvals ─────────────────────────────────────────────────────────────────

def get_approvals(status: str = None) -> list:
    path = "/approvals"
    if status:
        path += f"?status={status}"
    return get(path) or []


def submit_decision(approval_id: str, status: str, message: str = None) -> dict:
    body: dict[str, Any] = {"approval_id": approval_id, "status": status}
    if message:
        body["user_message"] = message
    return post(f"/approvals/{approval_id}/decision", body)


# ─── Activity ──────────────────────────────────────────────────────────────────

def get_activity(session_id: str = None, types: list = None) -> list:
    if session_id:
        path = f"/sessions/{session_id}/events"
        if types:
            path += f"?types={','.join(types)}"
        return get(path) or []
    return get("/activity") or []


# ─── Policies ──────────────────────────────────────────────────────────────────

def get_policies() -> list:
    return get("/policies") or []


def create_policy(payload: dict) -> dict:
    return post("/policies", payload)


def update_policy(policy_id: str, payload: dict) -> dict:
    return patch(f"/policies/{policy_id}", payload)


def test_policy(policy_id: str, sample: dict) -> dict:
    return post(f"/policies/{policy_id}/test", sample)
