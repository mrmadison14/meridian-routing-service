# Meridian Ticket Routing Service

[![tests](https://github.com/mrmadison14/meridian-routing-service/actions/workflows/test.yml/badge.svg)](https://github.com/mrmadison14/meridian-routing-service/actions/workflows/test.yml)

A helpdesk posts ticket-created events to this service. The webhook signature is verified before anything else happens, a first-match-wins rules engine picks the right chat channel (by priority, product, or subject keyword), and the decision is delivered. It replaced a no-code workflow that had grown past what no-code review and testing could support.

This is a clean-room rebuild of a production microservice I built and run, at a real volume of 120 to 250 tickets a week. The company here ("Meridian Fleet Systems") and the rules file are fictional; the architecture, the security model, and the tests are the real thing. There is an [interactive simulator](https://mrmadison14.github.io/portfolio/demo-routing-service.html) of the rules engine, and the rest of my work lives at [mrmadison14.github.io/portfolio](https://mrmadison14.github.io/portfolio/).

```
helpdesk webhook ──▶ HMAC-SHA256 check ──▶ rules engine ──▶ chat channel + assignee
                     (reject on mismatch     (first match
                      or stale timestamp)     wins, JSON config)
```

## Design notes

- **Signature first, parsing second.** The request body is not even parsed as JSON until the timestamped HMAC-SHA256 signature checks out (constant-time compare, 300-second freshness window). Unauthenticated input gets the smallest possible attack surface.
- **The rules file must end in a catch-all**, and `load_rules` refuses to start otherwise. A routing service that can fail to route is an outage you find out about from a customer.
- **A shadowed catch-all is also a startup error.** An unconditional rule placed anywhere but last would silently eat every ticket below it.
- **Everything is injected.** The app factory takes its secret, rules, notifier, and clock as arguments, so the tests drive the full HTTP path (signed request in, routed decision out) with no network and no environment.

## Run it

```
uv run pytest                  # test suite
WEBHOOK_SECRET=dev uv run uvicorn --factory meridian_routing:create_app
docker build -t meridian-routing . && docker run -e WEBHOOK_SECRET=dev -p 8000:8000 meridian-routing
```

Requires [uv](https://docs.astral.sh/uv/) for the first two.
