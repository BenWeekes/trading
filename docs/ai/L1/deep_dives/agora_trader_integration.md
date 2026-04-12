# Agora Trader Integration

## When to Read This

Read this when changing the trader avatar panel, the trader voice flow, the Agora bridge, or the Agora-compatible backend endpoint.

## Purpose

Only the `trader` role is voice/avatar-first in this app. The supporting roles remain direct backend LLM calls.

## Current shape

- UI panel: [frontend/src/components/trades/TraderAvatarPanel.tsx](/Users/benwekes/work/trading/frontend/src/components/trades/TraderAvatarPanel.tsx)
- backend routes: [backend/app/routes/agora.py](/Users/benwekes/work/trading/backend/app/routes/agora.py)
- bridge logic: [backend/app/services/agora_bridge.py](/Users/benwekes/work/trading/backend/app/services/agora_bridge.py)

## Operational model

- main trading backend stays the system of record
- trader avatar start/stop/speak is proxied through backend routes
- voice turns can be resolved through `/api/agora/chat/completions`
- typed and spoken trader interaction should ultimately affect the same recommendation and timeline state

## Current compromise

The avatar panel currently embeds the configured Agora client URL in an iframe. This is acceptable for local/product iteration, but it is not the final ideal architecture.

## Ideal later direction

- native in-app Agora SDK integration in the main frontend
- shared auth/session awareness between trading app and trader voice panel
- better synchronization between live trader speaking state and desk timeline

## Key constraints

- do not route all roles through Agora
- do not let Agora own recommendation truth
- do not bypass approval/execution rules from voice paths
