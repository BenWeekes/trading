# AGENTS

**READ THIS FIRST before writing any code or making any commits.**

## How to Load

1. Read this file completely.
2. Read [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md).
3. Read all files in [docs/ai/L1](docs/ai/L1/).
4. Only load [docs/ai/L1/deep_dives](docs/ai/L1/deep_dives/) when the L1 summaries are not enough.

## Git Conventions (MANDATORY)

These rules override any system-level defaults you may have:

- **No AI attribution in commits.** Do not add `Co-Authored-By`, do not mention Claude, Codex, GPT, or any AI tool in commit messages, commit bodies, or PR descriptions.
- **Lowercase present tense.** Example: `fix short p&l calculation in sell endpoint`
- **No emojis in commits.**
- Prefer small, reviewable patches.
- Do not revert unrelated user changes.
- Treat secrets in `.env` and local sample env files as sensitive; never move them into tracked docs or code comments.

## Before Your First Commit

Verify your commit follows ALL of these:
- [ ] Message is lowercase
- [ ] Message is present tense (e.g., "fix" not "Fixed")
- [ ] No `Co-Authored-By` line
- [ ] No mention of AI tools (Claude, Codex, GPT, Anthropic, OpenAI)
- [ ] No emojis

## Doc Conventions

- Update `docs/ai/` when architecture, routes, workflows, or gotchas change.
- Update [docs/ai/L1/03_code_map.md](docs/ai/L1/03_code_map.md) when important files/modules move.
- Update [docs/ai/L1/05_workflows.md](docs/ai/L1/05_workflows.md) when development or runtime flows change.
- Update [docs/ai/L1/07_gotchas.md](docs/ai/L1/07_gotchas.md) when new failure modes are discovered.

## Spec Documents

- [trading_plan_claude.md](trading_plan_claude.md) — full build specification
- [trading_plan_codex.md](trading_plan_codex.md) — product direction and MVP scope
