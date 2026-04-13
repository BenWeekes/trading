# AI Agent Instructions

**Read this file completely before writing any code or making any commits.**

This repository uses progressive disclosure documentation to help AI coding
agents work efficiently. Documentation is structured in three levels under
`docs/ai/`.

## How to Load

1. Read [docs/ai/L0_repo_card.md](docs/ai/L0_repo_card.md) to identify the repo.
2. Load ALL files in `docs/ai/L1/`. They are small — load all of them upfront.
   This gives you setup, architecture, code map, conventions, workflows,
   interfaces, gotchas, and security.
3. If a task needs more detail than L1 provides, follow links to L2 deep dives
   in `docs/ai/L1/deep_dives/`. Load only the specific L2 file you need.

## Levels

- **L0 (Repo Card):** Identity and L1 index. Table of contents.
- **L1 (Summaries):** Structured summaries. Load all at session start.
- **L2 (Deep Dives):** Full specifications. Load only when L1 isn't detailed enough.

## Git Conventions

### Commit messages — conventional commits

- **Format:** `type: description` or `type(scope): description`
- **Types:** `feat:` (new feature), `fix:` (bug fix), `chore:` (maintenance), `test:` (test additions/changes), `docs:` (documentation), `refactor:` (code restructuring)
- **Scoped variant:** `feat(scope):`, `fix(scope):` — e.g. `fix(scanner): dedupe earnings rows`
- **Lowercase after prefix** — `feat: add feature`, not `feat: Add feature`
- **Present tense** — "add feature", not "added feature"

### Branch names

- **Format:** `type/short-description` — lowercase, hyphen-separated
- **Types match commit types:** `feat/`, `fix/`, `chore/`, `test/`, `docs/`
- **Examples:** `feat/avatar-rtc`, `fix/short-pnl`, `docs/update-readme`

### Rules that override your defaults

- **No AI tool names** — never mention claude, cursor, copilot, cody, aider, gemini, codex, chatgpt, gpt-3/4/5, anthropic, or openai in commit messages, commit bodies, branch names, or PR descriptions
- **No Co-Authored-By trailers** — omit all AI attribution lines
- **No --no-verify** — let git hooks run normally
- **No git config changes** — do not modify user.name or user.email
- **No emojis** in commit messages

### Before your first commit

Verify your commit follows ALL of these:
- [ ] Uses conventional commit format (`type: description`)
- [ ] Lowercase after prefix
- [ ] Present tense
- [ ] No `Co-Authored-By` line
- [ ] No mention of AI tools
- [ ] No emojis
- [ ] No `--no-verify`

## Doc Commands

| Command       | When to use                                       |
| ------------- | ------------------------------------------------- |
| generate docs | no `docs/ai/` directory exists yet                |
| update docs   | code changed since last `last_reviewed` date      |
| test docs     | verify docs give agents the right context         |

Update rules:
- Update `docs/ai/` when architecture, routes, workflows, or gotchas change.
- Update [docs/ai/L1/03_code_map.md](docs/ai/L1/03_code_map.md) when important files/modules move.
- Update [docs/ai/L1/05_workflows.md](docs/ai/L1/05_workflows.md) when development or runtime flows change.
- Update [docs/ai/L1/07_gotchas.md](docs/ai/L1/07_gotchas.md) when new failure modes are discovered.

## Working Areas

- `backend/app/roles/` — role system, orchestrator, prompts
- `backend/app/routes/` — API endpoints
- `backend/app/services/` — scanner, filters, state machine, event bus
- `backend/app/adapters/` — LLM providers, market data, broker
- `frontend/src/components/` — UI components
- `frontend/src/hooks/` — React hooks (SSE, Agora)
- `data/` — runtime data (gitignored DB, mock scenarios)

Do not modify:
- `agora-agent-samples/` — external reference repo, not our code
- `ai-devkit/` — external reference repo
- `.env` — contains secrets, never commit

## Spec Documents

- [trading_plan_claude.md](trading_plan_claude.md) — full build specification
- [trading_plan_codex.md](trading_plan_codex.md) — product direction and MVP scope
