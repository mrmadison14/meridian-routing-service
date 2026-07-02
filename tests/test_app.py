import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from meridian_routing.app import create_app
from meridian_routing.notifier import MemoryNotifier
from meridian_routing.rules import Rule
from meridian_routing.security import sign

SECRET = b"test-secret"
NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)
RULES = [
    Rule(id="urgent", description="urgent", priority="urgent", channel="#oncall"),
    Rule(id="catch-all", description="fallback", channel="#triage"),
]


def make_client() -> tuple[TestClient, MemoryNotifier]:
    notifier = MemoryNotifier()
    app = create_app(secret=SECRET, rules=RULES, notifier=notifier, clock=lambda: NOW)
    return TestClient(app), notifier


def signed_headers(body: bytes) -> dict[str, str]:
    ts = NOW.isoformat()
    return {"X-Timestamp": ts, "X-Signature": sign(SECRET, ts, body)}


def ticket_body(**overrides) -> bytes:
    base = {"id": "ZD-1", "subject": "device offline", "priority": "urgent", "product": "device"}
    return json.dumps({**base, **overrides}).encode()


def test_signed_ticket_is_routed_and_delivered():
    client, notifier = make_client()
    body = ticket_body()
    response = client.post("/webhook/ticket", content=body, headers=signed_headers(body))
    assert response.status_code == 200
    assert response.json()["channel"] == "#oncall"
    assert [decision.ticket_id for decision in notifier.posted] == ["ZD-1"]


def test_bad_signature_is_rejected_before_parsing():
    client, notifier = make_client()
    body = ticket_body()
    headers = signed_headers(ticket_body(priority="normal"))
    response = client.post("/webhook/ticket", content=body, headers=headers)
    assert response.status_code == 401
    assert notifier.posted == []


def test_missing_headers_rejected():
    client, _ = make_client()
    response = client.post("/webhook/ticket", content=ticket_body())
    assert response.status_code == 422


def test_healthz():
    client, _ = make_client()
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
