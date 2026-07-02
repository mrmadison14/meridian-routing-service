import json
from pathlib import Path

import pytest

from meridian_routing.models import Ticket
from meridian_routing.rules import Rule, RulesError, load_rules, route

RULES = [
    Rule(id="urgent", description="urgent", priority="urgent", channel="#oncall"),
    Rule(id="hardware", description="hardware", products=frozenset({"device", "harness"}), channel="#hw"),
    Rule(id="billing", description="billing", subject_pattern="billing|invoice", channel="#accounts"),
    Rule(id="catch-all", description="fallback", channel="#triage"),
]


def ticket(**overrides) -> Ticket:
    base = {"id": "ZD-1", "subject": "hello", "priority": "normal", "product": "other"}
    return Ticket(**{**base, **overrides})


def test_first_match_wins_over_later_matches():
    urgent_hardware = ticket(priority="urgent", product="device")
    assert route(urgent_hardware, RULES).channel == "#oncall"


def test_product_set_match():
    assert route(ticket(product="harness"), RULES).channel == "#hw"


def test_keyword_match_is_case_insensitive():
    assert route(ticket(subject="Question about our INVOICE"), RULES).channel == "#accounts"


def test_unmatched_falls_through_to_catch_all():
    decision = route(ticket(), RULES)
    assert decision.channel == "#triage"
    assert decision.rule_id == "catch-all"


def test_disabled_rule_is_skipped():
    rules = [
        Rule(id="urgent", description="urgent", priority="urgent", channel="#oncall", enabled=False),
        Rule(id="catch-all", description="fallback", channel="#triage"),
    ]
    assert route(ticket(priority="urgent"), rules).channel == "#triage"


def write_rules(path: Path, rules: list[dict]) -> Path:
    file = path / "rules.json"
    file.write_text(json.dumps(rules))
    return file


def test_load_rules_requires_catch_all(tmp_path):
    with pytest.raises(RulesError, match="catch-all"):
        load_rules(write_rules(tmp_path, [{"id": "a", "description": "a", "priority": "urgent", "channel": "#x"}]))


def test_load_rules_rejects_shadowing_catch_all(tmp_path):
    rules = [
        {"id": "early-catch", "description": "oops", "channel": "#x"},
        {"id": "catch-all", "description": "fallback", "channel": "#triage"},
    ]
    with pytest.raises(RulesError, match="before the end"):
        load_rules(write_rules(tmp_path, rules))


def test_load_rules_accepts_the_shipped_config():
    shipped = Path(__file__).parent.parent / "rules.json"
    rules = load_rules(shipped)
    assert rules[-1].is_catch_all()
