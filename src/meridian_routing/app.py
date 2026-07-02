"""FastAPI application.

One meaningful endpoint: the helpdesk posts ticket-created events here, the
signature is verified before anything is parsed, the rules engine decides a
channel, and the notifier delivers. The app is built by a factory so tests
can inject their own secret, rules, notifier, and clock.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, Header, HTTPException, Request

from .models import RouteDecision, Ticket
from .notifier import MemoryNotifier, Notifier
from .rules import Rule, load_rules, route
from .security import SignatureError, verify

DEFAULT_RULES = Path(__file__).parent.parent.parent / "rules.json"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_app(
    *,
    secret: bytes | None = None,
    rules: list[Rule] | None = None,
    notifier: Notifier | None = None,
    clock: Callable[[], datetime] = _utc_now,
) -> FastAPI:
    secret = secret if secret is not None else os.environ["WEBHOOK_SECRET"].encode()
    rules = rules if rules is not None else load_rules(Path(os.environ.get("RULES_PATH", DEFAULT_RULES)))
    notifier = notifier if notifier is not None else MemoryNotifier()

    app = FastAPI(title="Meridian Ticket Routing", version="1.0.0")
    app.state.notifier = notifier

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "rules": str(len(rules))}

    @app.post("/webhook/ticket", response_model=RouteDecision)
    async def receive_ticket(
        request: Request,
        x_timestamp: str = Header(),
        x_signature: str = Header(),
    ) -> RouteDecision:
        body = await request.body()
        try:
            verify(secret, x_timestamp, body, x_signature, now=clock())
        except SignatureError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        ticket = Ticket.model_validate_json(body)
        decision = route(ticket, rules)
        notifier.post(ticket, decision)
        return decision

    return app
