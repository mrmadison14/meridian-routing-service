"""Timestamped HMAC-SHA256 webhook signatures.

The sender signs `{timestamp}.{body}` and supplies both as headers.
Verification recomputes the signature with a constant-time compare and
rejects stale timestamps, which closes off both tampering and replay.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta

MAX_AGE = timedelta(seconds=300)


class SignatureError(Exception):
    pass


def sign(secret: bytes, timestamp: str, body: bytes) -> str:
    message = timestamp.encode() + b"." + body
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify(secret: bytes, timestamp: str, body: bytes, signature: str, *, now: datetime) -> None:
    try:
        sent_at = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise SignatureError(f"unparseable timestamp: {timestamp!r}") from exc
    age = now - sent_at
    if age > MAX_AGE or age < -MAX_AGE:
        raise SignatureError(f"timestamp outside the {MAX_AGE.seconds}s window")
    expected = sign(secret, timestamp, body)
    if not hmac.compare_digest(expected, signature):
        raise SignatureError("signature mismatch")
