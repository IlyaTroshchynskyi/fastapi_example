# AI assistants and project instructions

## Where instructions live

| Tool | Location |
|------|----------|
| **Cursor (primary)** | [.cursor/rules/](.cursor/rules/) — `.mdc` rules with `alwaysApply` or `globs` |
| **GitHub Copilot** | [.github/copilot-instructions.md](.github/copilot-instructions.md) and [.github/unit.tests-instructions.md](.github/unit.tests-instructions.md) |

**Canonical source:** edit [.cursor/rules/](.cursor/rules/) first, then mirror the same bullets into the `.github` files so Copilot stays aligned. The `.github` files link to the rules for reference.

## Adding or changing instructions later

- **New coding standard or convention** (always or broad Python scope) → add or extend a rule in `.cursor/rules/` (e.g. split by topic into new `.mdc` files), then update `.github/copilot-instructions.md` if you use Copilot.
- **Test-only convention** → extend [.cursor/rules/pytest-testing.mdc](.cursor/rules/pytest-testing.mdc) or add another rule with `globs` under `tests/`, then update `.github/unit.tests-instructions.md` if needed.
- **Repeatable workflow** (checklists, multi-step procedures) → add a project skill under `.cursor/skills/<name>/SKILL.md` with a clear `description` so the agent knows when to use it.
- **User-triggered playbook** (scaffold, review template) → add a Cursor command under `.cursor/commands/` when you want a slash-invoked prompt; do not rely on commands alone for baseline standards.

## Current rules

- `python-fastapi.mdc` — Python/FastAPI/Pydantic/SQLAlchemy; `alwaysApply: true`
- `pytest-testing.mdc` — tests under `tests/**/*.py`
