"""Delivery behind a protocol.

Production posts to chat channels and assigns an agent. Tests and local runs
use MemoryNotifier, which records decisions instead of posting them.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from .models import RouteDecision, Ticket

logger = logging.getLogger(__name__)


class Notifier(Protocol):
    def post(self, ticket: Ticket, decision: RouteDecision) -> None: ...


@dataclass
class MemoryNotifier:
    posted: list[RouteDecision] = field(default_factory=list)

    def post(self, ticket: Ticket, decision: RouteDecision) -> None:
        self.posted.append(decision)
        logger.info("ticket %s -> %s (rule %s)", ticket.id, decision.channel, decision.rule_id)
