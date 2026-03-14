---
name: pr-manager
description: Automates creating PRs, monitoring for reviews (refreshing every 15s, 20min timeout), running codebase validation (lint/check/tidy), implementing feedback (High/Medium criticality only), committing and pushing fixes, replying to comments, and waiting for ALL reviewers to finish before exiting.
---

# PR Manager

This skill manages the lifecycle of a Pull Request, from creation through feedback implementation to merge readiness. It ensures all reviewers have completed their reviews before proceeding.

## When to Use This Skill

Use this skill when:
- Creating a PR and actively waiting for code reviews (e.g., from Gemini, Copilot, or human reviewers).
- Automating the feedback loop: implementing changes based on reviews, validating, committing, pushing, and replying to comments.
- Filtering feedback based on criticality (High/Medium vs. Low/Nitpick).

## Workflow

### 1. Create Pull Request

Ensure you are on the correct feature branch. Check if a PR already exists for this branch. If not, create one.

**Target branch rules (Tendor monorepo):**
- Feature branches (`feat/`, `fix/`, `chore/`, `refactor/`, `docs/`) → target **`main`**
- Release/hotfix branches (`release/*`, `hotfix/*`) → target **`main`**

```bash
# Check if PR exists
gh pr list --head "$(git branch --show-current)" --json url,number

# If no PR exists, create one targeting main (for feature work)
gh pr create --title "feat: <title>" --base main --body "Automated PR created by Agent"

# For release/hotfix branches, target main with the correct title format
gh pr create --title "🚀 release: <date>" --base main --body "..."
```

### 2. Wait for CI to Pass

After creating the PR, CI checks run automatically. Wait for them before requesting reviews.

```bash
# Watch CI status — polls until all checks pass or any fails
gh pr checks "$(gh pr view --json number -q .number)" --watch

# Or check current status
gh pr checks "$(gh pr view --json number -q .number)"
```

If any check fails, fix the issue locally, commit, and push. CI will re-run automatically. Do not proceed to review monitoring until all CI checks are green.

### 3. Monitor for Reviews

Use the `scripts/monitor_pr.py` script to wait for new review activity. The script polls the PR every 15 seconds with a **20-minute timeout** and **waits for ALL requested reviewers to finish** before returning.

```bash
PR_URL=$(gh pr view --json url -q .url)

# Run the monitor — exits only when all reviewers have submitted
python3 skills/pr-manager/scripts/monitor_pr.py "$PR_URL" --interval 15 --timeout 1200
```

**Exit codes:**
- `0` — All reviewers completed, new activity detected.
- `1` — Failed to fetch PR data.
- `2` — Timeout reached. Check JSON output for `all_reviewers_done` and `pending_reviewer`.

**Important:** If the script detects new activity but a reviewer is still pending, it continues waiting. It only exits successfully when every requested reviewer has submitted their review. If timeout is reached with a pending reviewer, re-run the monitor to keep waiting.

### 4. Analyze Feedback

When all reviewers have finished and new activity is detected:
1. Parse the JSON output from `monitor_pr.py`.
2. **Thoroughly read and understand** each comment/review suggestion. Do not skim.
3. **Verify against the codebase:** 
    - Open the relevant files using `read_file` or `grep` to see the actual code context.
    - Do not rely solely on the diff in the comment; check the surrounding code.
    - Verify if the suggestion is technically sound and compatible with the rest of the project.
4. **Critically evaluate the suggestion:**
    - **Is the reviewer correct?** Use your judgment. Reviewers (especially AI ones) can be wrong.
    - **Is the suggestion necessary?** Does it improve the code or just change the style?
    - **Classify the feedback:**
        - **High:** Security, Bugs, Major Logic Flaws.
        - **Medium:** Performance, Best Practices, Maintainability.
        - **Low/Nitpick:** Formatting (if linter exists), subjective style preferences.

### 5. Implement Changes

**Implement feedback selectively based on your critical evaluation.**

- **Adopt** the suggestion ONLY if:
    - You have verified it is correct and improves the code.
    - It is High or Medium criticality.
    - It does not introduce new bugs or regressions.
- **Reject** the suggestion if:
    - It is technically incorrect or breaks existing functionality.
    - It contradicts project patterns or conventions.
    - It is a Low/Nitpick that conflicts with the linter/formatter.
- **For Low/Nitpick feedback:** Do not implement unless it's trivial, automated, and uncontroversial.

**Crucial:** You are the owner of this PR. Do not blindly accept changes. If a reviewer is wrong, you must explain why in your reply instead of breaking the code.

### 6. Validate the Codebase

**Before committing any changes, run the appropriate validation commands for the codebase.**

**Tendor monorepo (Bun + Biome):**

```bash
bun run lint          # Biome lint — whole repo
bun run check         # TypeScript typecheck — whole repo (or per-app below)
bun run --cwd apps/web check    # web only
bun run --cwd apps/api check    # api only
bun run test:web      # web unit tests
bun run test:api      # api unit tests
```

> Always use `bun run`, never `npm run` or `pnpm`.

**Other project types:**

| Indicator | Commands to Run |
|-----------|----------------|
| `package.json` with `lint` | `npm run lint` / `pnpm lint` / `yarn lint` |
| `package.json` with `check` | `npm run check` / `pnpm check` |
| `tsconfig.json` (no check script) | `npx tsc --noEmit` |
| `go.mod` | `go mod tidy && go vet ./... && go build ./...` |
| `Cargo.toml` | `cargo check && cargo clippy` |
| `pyproject.toml` / `setup.py` | `ruff check .` or `flake8` / `pylint` |
| `Makefile` with `lint` | `make lint` |

If any validation fails, fix the issues before proceeding.

### 7. Commit and Push

After implementing changes and passing validation:

```bash
# Stage changed files (be specific, avoid staging unrelated files)
git add <changed-files>

# Commit with a descriptive message
git commit -m "fix: address code review feedback"

# Push to the branch
git push
```

### 8. Reply to Comments

Reply to **every single comment individually** — one reply per review comment. **NEVER batch multiple responses into a single summary comment** (e.g., `gh pr comment` with a combined body). Each reviewer comment must get its own threaded reply so the conversation stays inline with the code.

- **If implemented:** "Fixed: [Brief explanation of what was changed and why]"
- **If NOT implemented:** "Skipped: [Reasoning why it was not implemented, e.g., 'This is a nitpick handled by formatter' or 'This suggestion would break X']"

#### How to Reply

**Step 1: Get all review comments and their IDs**

```bash
# Fetch all review comments on the PR (these are inline code comments)
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments --paginate --jq '.[] | {id, path, body}'
```

**Step 2: Reply to EACH comment individually using the replies endpoint**

```bash
# Reply to a specific comment — use the comment's numeric ID
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body="Fixed: updated logic per review feedback."
```

**CRITICAL RULES:**
- **ONE reply per comment.** Do NOT combine responses.
- **Use the `/replies` endpoint** (NOT `gh pr comment` which posts a top-level comment).
- **Use the comment ID** from the review comments API, not the review ID.
- If a reply fails, retry that specific comment — do NOT fall back to a single summary comment.
- Reply to comments **sequentially** (one at a time) to avoid rate limiting or sibling call errors.

### 9. Loop or Finalize

After pushing fixes and replying to all comments:

1. **Re-run the monitor** from Step 2 to check if any reviewer re-requests changes or new reviews come in.
2. If the review state is `CHANGES_REQUESTED`, repeat from Step 2.
3. **Do not exit while any reviewer is still actively reviewing.** The monitor script enforces this — if a requested reviewer hasn't submitted their review, it keeps waiting.
4. If all reviews are `APPROVED` or all comments are addressed with no pending reviewers:
    - Output the PR URL.
    - Ask the user for final confirmation to merge.
    - If confirmed: `gh pr merge "$PR_URL" --merge --delete-branch`.
