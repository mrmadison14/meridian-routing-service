from datetime import datetime, timedelta, timezone

import pytest

from meridian_routing.security import SignatureError, sign, verify

SECRET = b"test-secret"
NOW = datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc)


def test_roundtrip():
    ts = NOW.isoformat()
    body = b'{"id": "ZD-1"}'
    verify(SECRET, ts, body, sign(SECRET, ts, body), now=NOW)


def test_tampered_body_rejected():
    ts = NOW.isoformat()
    signature = sign(SECRET, ts, b'{"priority": "normal"}')
    with pytest.raises(SignatureError, match="mismatch"):
        verify(SECRET, ts, b'{"priority": "urgent"}', signature, now=NOW)


def test_replayed_old_request_rejected():
    ts = (NOW - timedelta(minutes=10)).isoformat()
    body = b"{}"
    with pytest.raises(SignatureError, match="window"):
        verify(SECRET, ts, body, sign(SECRET, ts, body), now=NOW)


def test_wrong_secret_rejected():
    ts = NOW.isoformat()
    body = b"{}"
    with pytest.raises(SignatureError, match="mismatch"):
        verify(SECRET, ts, body, sign(b"other-secret", ts, body), now=NOW)
