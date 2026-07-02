from __future__ import annotations

from pydantic import BaseModel


class Ticket(BaseModel):
    id: str
    subject: str
    priority: str
    product: str


class RouteDecision(BaseModel):
    ticket_id: str
    channel: str
    rule_id: str
    rule_description: str
