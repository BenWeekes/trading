# 08 Security

> Trust boundaries, secret handling, execution safety, and auth-sensitive behavior.

## Secret handling

- Keep provider keys in local env files only.
- Never paste secrets into tracked docs.
- Rotate keys that have appeared in chat transcripts or shared logs.

## Trading safety rules

- The app is paper-first.
- `execute` must not succeed unless a recommendation is already `approved`.
- Prompt text and role outputs are advisory, not trusted facts.
- Recommendation and execution records must remain auditable.

## Avatar / Agora boundary

- Agora is not the system of record.
- Voice/avatar behavior must not bypass trading backend approval rules.
- Spoken trader turns should converge on the same recommendation state as typed turns.

## Auth expectations

- Local auth can remain simple.
- Published app should require secure login.
- Approval and execution routes should always be server-validated.

## Data handling

- Role messages, approvals, and executions are workflow records and should be retained.
- Avoid creating noisy or misleading recommendation records from speculative or contextless inputs.

## Related Deep Dives

- [role_and_state_machine](deep_dives/role_and_state_machine.md)
- [api_contracts](deep_dives/api_contracts.md)
