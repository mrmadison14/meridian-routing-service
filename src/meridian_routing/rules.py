"""First-match-wins rules engine.

Rules live in a JSON file and are evaluated top to bottom; the first enabled
rule whose every condition matches decides the channel. The file must end in
an unconditional catch-all, and loading fails loudly if it doesn't, because a
routing service with an unroutable ticket is a paging incident waiting to
happen.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel

from .models import RouteDecision, Ticket


class RulesError(Exception):
    pass


class Rule(BaseModel):
    id: str
    description: str
    channel: str
    enabled: bool = True
    priority: str | None = None
    products: frozenset[str] | None = None
    subject_pattern: str | None = None

    def matches(self, ticket: Ticket) -> bool:
        if self.priority is not None and ticket.priority != self.priority:
            return False
        if self.products is not None and ticket.product not in self.products:
            return False
        if self.subject_pattern is not None and not re.search(
            self.subject_pattern, ticket.subject, re.IGNORECASE
        ):
            return False
        return True

    def is_catch_all(self) -> bool:
        return self.priority is None and self.products is None and self.subject_pattern is None


def load_rules(path: Path) -> list[Rule]:
    rules = [Rule.model_validate(raw) for raw in json.loads(path.read_text())]
    if not rules:
        raise RulesError(f"{path} contains no rules")
    last = rules[-1]
    if not (last.enabled and last.is_catch_all()):
        raise RulesError(f"{path} must end in an enabled unconditional catch-all rule")
    for rule in rules[:-1]:
        if rule.is_catch_all() and rule.enabled:
            raise RulesError(f"rule {rule.id!r} is an unconditional match placed before the end")
    return rules


def route(ticket: Ticket, rules: list[Rule]) -> RouteDecision:
    for rule in rules:
        if rule.enabled and rule.matches(ticket):
            return RouteDecision(
                ticket_id=ticket.id,
                channel=rule.channel,
                rule_id=rule.id,
                rule_description=rule.description,
            )
    raise RulesError("no rule matched; load_rules should have rejected this rule set")
