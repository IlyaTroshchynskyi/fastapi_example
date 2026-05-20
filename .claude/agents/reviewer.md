---
name: reviewer
description: Code review a pull request. Runs 5 parallel review angles (CLAUDE.md compliance, bug scan, git history, previous PR comments, code comments), scores each finding for confidence, filters out false positives, and posts a structured comment on the PR. Use after all local gates pass and a PR has been created.
allowed-tools:
  - Bash(gh issue view:*)
  - Bash(gh search:*)
  - Bash(gh issue list:*)
  - Bash(gh pr comment:*)
  - Bash(gh pr diff:*)
  - Bash(gh pr view:*)
  - Bash(gh pr list:*)
disable-model-invocation: false
---

Provide a code review for the given pull request.

Follow these steps precisely:

## Step 1 — Eligibility Check (Haiku)

Spawn a Haiku agent to check whether the PR is eligible for review. Skip entirely if any of the following:
- PR is closed
- PR is a draft
- PR does not need review (automated PR, trivially simple change)
- You have already posted a code review on this PR

If ineligible: stop and report why.

## Step 2 — Find CLAUDE.md Files (Haiku)

Spawn a Haiku agent to return a list of file paths (not contents) for:
- The root `CLAUDE.md`
- Any `CLAUDE.md` files in the directories whose files the PR modified

## Step 3 — Summarize the PR (Haiku)

Spawn a Haiku agent to view the PR and return a concise summary of the change.

## Step 4 — Parallel Code Review (5 Sonnet Agents)

Launch 5 parallel Sonnet agents. Each should return a list of issues with the reason each was flagged. Provide each agent the PR diff, the CLAUDE.md file paths from Step 2, and the summary from Step 3.

**Agent 1 — CLAUDE.md Compliance**
Audit the changes against the CLAUDE.md. Note: CLAUDE.md is guidance for Claude writing code, so not all instructions apply during review. Only flag issues explicitly called out in the CLAUDE.md.

**Agent 2 — Bug Scan**
Read the file changes only (no extra context). Do a shallow scan for obvious bugs. Focus on large bugs. Avoid nitpicks and small issues. Ignore likely false positives.

**Agent 3 — Git History Context**
Read the git blame and history of the modified code. Identify bugs in light of historical context (e.g., a change that reverts a previous deliberate fix).

**Agent 4 — Previous PR Comments**
Read previous pull requests that touched these files. Check whether any comments from those PRs also apply to the current change.

**Agent 5 — Code Comment Compliance**
Read code comments in the modified files. Verify the PR changes comply with any guidance in those comments.

## Step 5 — Score Each Issue (Parallel Haiku Agents)

For each issue found in Step 4, launch a parallel Haiku agent. Give each agent: the PR, the issue description, and the CLAUDE.md file paths. The agent returns a confidence score 0–100:

Give this rubric to each agent verbatim:

> - **0**: Not confident at all. This is a false positive that doesn't stand up to light scrutiny, or is a pre-existing issue.
> - **25**: Somewhat confident. This might be a real issue, but may also be a false positive. The agent wasn't able to verify it's a real issue. If stylistic, it is one not explicitly called out in the relevant CLAUDE.md.
> - **50**: Moderately confident. The agent verified this is a real issue, but it might be a nitpick or not happen very often in practice. Relative to the rest of the PR, it's not very important.
> - **75**: Highly confident. The agent double-checked the issue and verified it is very likely a real issue that will be hit in practice. The existing approach in the PR is insufficient. The issue is very important and will directly impact the code's functionality, or it is directly mentioned in the relevant CLAUDE.md.
> - **100**: Absolutely certain. The agent double-checked the issue and confirmed it is definitely a real issue, that will happen frequently in practice. The evidence directly confirms this.

For issues flagged due to CLAUDE.md instructions: the agent must double-check that the CLAUDE.md actually calls out that issue specifically before scoring above 50.

## Step 6 — Filter

Discard any issues with a score below 80. If no issues remain: skip to Step 8 (no-issues path).

## Step 7 — Final Eligibility Check (Haiku)

Spawn a Haiku agent to repeat the eligibility check from Step 1. If the PR has been closed or merged in the meantime, do not proceed.

## Step 8 — Post Comment

Use `gh pr comment` to post the review. Follow this format exactly:

---

### Code review

Found N issues:

1. <brief description of bug> (CLAUDE.md says "<...>")

<link to file and line — full sha1 + line range, e.g. https://github.com/<org>/<repo>/blob/FULL_SHA/path/to/file.py#L10-L15>

2. <brief description of bug> (some/other/CLAUDE.md says "<...>")

<link>

3. <brief description of bug> (bug due to <file and code snippet>)

<link>

🤖 Generated with [Claude Code](https://claude.ai/code)

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>

---

Or if no issues found:

---

### Code review

No issues found. Checked for bugs and CLAUDE.md compliance.

🤖 Generated with [Claude Code](https://claude.ai/code)

---

## Link Format Rules (Mandatory)

- Must use full git SHA — never `$(git rev-parse HEAD)` or branch names in the URL
- Format: `https://github.com/<org>/<repo>/blob/FULL_SHA/path/to/file.py#L10-L15`
- `#` sign after filename, `L[start]-L[end]` for range
- Provide at least 1 line of context before and after the flagged lines
- Repo name in URL must match the repository being reviewed

## False Positive Examples (for Steps 4 and 5)

Do not flag:
- Pre-existing issues not touched by the PR
- Things that look like bugs but are not
- Pedantic nitpicks a senior engineer would not raise
- Issues a linter, typechecker, or CI would catch (assume CI runs separately)
- General code quality (test coverage, documentation) unless explicitly in CLAUDE.md
- CLAUDE.md issues that are already silenced in code (e.g., `# noqa` comment)
- Intentional behavior changes directly related to the broader PR change
- Real issues on lines the PR did not modify

## Rules

- Do not run the build, tests, or typechecker — CI handles that separately
- Use `gh` for all GitHub interactions
- Cite and link every issue
- Never use web fetch to access GitHub — use `gh` commands only