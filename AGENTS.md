# AGENTS

## How to Load

1. Read [docs/ai/L0_repo_card.md](/Users/benwekes/work/trading/docs/ai/L0_repo_card.md).
2. Read all files in [docs/ai/L1](/Users/benwekes/work/trading/docs/ai/L1/).
3. Only load [docs/ai/L1/deep_dives](/Users/benwekes/work/trading/docs/ai/L1/deep_dives/) when the L1 summaries are not enough.

## Git Conventions

- Do not revert unrelated user changes.
- Prefer small, reviewable patches.
- Keep commit messages lowercase and present tense if commits are later requested.
- Do not mention AI tools in commit messages.
- Treat secrets in `.env` and local sample env files as sensitive; never move them into tracked docs or code comments.

## Doc Commands

- Update `docs/ai/` when architecture, routes, workflows, or gotchas change.
- Update [docs/ai/L1/03_code_map.md](/Users/benwekes/work/trading/docs/ai/L1/03_code_map.md) when important files/modules move.
- Update [docs/ai/L1/05_workflows.md](/Users/benwekes/work/trading/docs/ai/L1/05_workflows.md) when development or runtime flows change.
- Update [docs/ai/L1/07_gotchas.md](/Users/benwekes/work/trading/docs/ai/L1/07_gotchas.md) when new failure modes are discovered.
