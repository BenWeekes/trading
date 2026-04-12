# L0 Repo Card

repo_name: `trading`
repo_type: `full-stack app`
primary_languages: `Python`, `TypeScript`
frameworks: `FastAPI`, `Next.js`, `React`, `SQLite`
runtime_modes: `local dev`, `paper trading`, `demo/replay`, `optional Agora trader avatar`
system_of_record: `backend FastAPI app + SQLite/Postgres-compatible relational model`
last_reviewed: `2026-04-12`

| L1 File | Purpose |
| --- | --- |
| [01_setup](L1/01_setup.md) | Local setup, env vars, run/test commands |
| [02_architecture](L1/02_architecture.md) | System shape, data flow, main responsibilities |
| [03_code_map](L1/03_code_map.md) | Directory map and key files |
| [04_conventions](L1/04_conventions.md) | State-machine, routing, role, and implementation rules |
| [05_workflows](L1/05_workflows.md) | Common build, test, and product workflows |
| [06_interfaces](L1/06_interfaces.md) | APIs, SSE events, data objects, avatar interfaces |
| [07_gotchas](L1/07_gotchas.md) | Known traps, subtle behaviors, and local issues |
| [08_security](L1/08_security.md) | Secrets, approval safety, execution boundaries, auth notes |

| Deep Dive | Purpose |
| --- | --- |
| [role_and_state_machine](L1/deep_dives/role_and_state_machine.md) | Role system design, state machine transitions |
| [api_contracts](L1/deep_dives/api_contracts.md) | Full API surface with request/response shapes |
| [agora_trader_integration](L1/deep_dives/agora_trader_integration.md) | Avatar RTC integration details |
| [runtime_modes](L1/deep_dives/runtime_modes.md) | Live, mock, replay event modes |

| Spec Document | Purpose |
| --- | --- |
| [trading_plan_claude.md](/trading_plan_claude.md) | Full build specification — strategies, schemas, API spec, DB, costs, migration |
| [trading_plan_codex.md](/trading_plan_codex.md) | Product direction, MVP scope, UX design, build sequence |
