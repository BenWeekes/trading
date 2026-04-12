# 07 Gotchas

> Known traps, surprising behavior, and issues that will waste time if forgotten.

## SSE refresh behavior

The frontend originally refetched broad app state on every SSE event. That is too expensive when the backend emits multiple role and recommendation events quickly. Prefer debounced or targeted updates.

## Recommendation state confusion

`awaiting_user_feedback` and `awaiting_user_approval` are not the same thing. Do not collapse them accidentally.

## Trader follow-up cost

Automatically querying all three supporting roles on every trader follow-up message is too slow and expensive. Keep trader follow-up fan-out selective.

## Agora proxy behavior

Do not let helper functions silently create durable recommendation records from voice traffic unless that is an intentional product rule.

## Local npm TLS issues

Some local machines fail npm TLS verification with `UNABLE_TO_GET_ISSUER_CERT_LOCALLY`. Work around it explicitly during install rather than assuming the repo is broken.

## Avatar panel reality

The current trader avatar panel embeds the configured Agora client URL. It is integrated into the workstation visually and via backend hooks, but it is not yet a fully native in-app Agora SDK integration.

## Secret sprawl

This repo and local sample stack both use `.env` files. Be careful not to mix root trading-app config and Agora sample config mentally.

## Related Deep Dives

- [agora_trader_integration](deep_dives/agora_trader_integration.md)
