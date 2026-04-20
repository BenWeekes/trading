# 05 Workflows

> Step-by-step guides for common development and runtime tasks.

## Add a new backend route

1. Add route file logic under `backend/app/routes/`.
2. Register the router in `backend/app/main.py`.
3. Add or update repository/service helpers if needed.
4. Add route tests in `backend/tests/test_routes.py` or a focused new test file.
5. Run backend tests.

## Change recommendation lifecycle behavior

1. Update `backend/app/services/state_machine.py`.
2. Update orchestration or route logic.
3. Update route/orchestrator tests.
4. Verify `approve` and `execute` gating still behave correctly.

## Change desk chat behavior

1. Update routing logic in `backend/app/roles/orchestrator.py`.
2. Update UI expectations in `frontend/src/components/roles/GroupChat.tsx`.
3. Update tests for routing or timeline semantics.

## Add or modify trader-avatar behavior

1. Update `backend/app/routes/agora.py` and/or `backend/app/services/agora_bridge.py`.
2. Update `frontend/src/components/trades/TraderAvatarPanel.tsx`.
3. Keep the backend as system of record; do not move recommendation truth into Agora.
4. If behavior changes materially, document it in the AI docs.

## Run a manual local demo

1. Start backend.
2. Start frontend.
3. Open the app — auto-scan triggers on first load, populating earnings events.
4. Select an earnings event from the Earnings tab; analysis runs in background.
5. Ask directed questions in desk chat.
6. Move rec from feedback to approval.
7. Approve and execute.

## Update docs after code changes

1. Update `README.md` if human-facing setup or workflow changed.
2. Update relevant L1 files in `docs/ai/L1/`.
3. Add or update an L2 deep dive if the change adds meaningful subsystem complexity.

## Related Deep Dives

- [api_contracts](deep_dives/api_contracts.md)
- [agora_trader_integration](deep_dives/agora_trader_integration.md)
