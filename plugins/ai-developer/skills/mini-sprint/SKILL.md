---
name: mini-sprint
description: Identify issues for the next sprint, and plan it accordingly. Uses worktrees for isolated development and auto-merges PRs when CI passes. Use when the user wants to plan a sprint, batch issues, work on multiple issues at once, or asks about sprint planning — even if they don't say "mini-sprint" explicitly.
---

NUM_ISSUES = 3 unless $ARGUMENTS set

# Mini Sprint

Identify the next batch of issues, plan the sprint, implement each in an isolated worktree, create PRs, and auto-merge when CI passes.

## Phase 1: Issue Selection

Run the fetch script to get prioritized issues:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/mini-sprint/scripts/fetch_issues.py"
```

Select the top NUM_ISSUES issues that aren't skipped. For each, read the full issue details:

```bash
gh issue view <number>
```

Present the selection with justification. Wait for user confirmation before proceeding.

### Priority Rules

1. **Skip** — `cost-approval-needed`, `post-revenue`, `on-hold` labels
2. **P0** — `blocker`
3. **P1** — `critical` or `security`
4. **P2** — `high`
5. **P3** — Bugs over features at same priority
6. **P4** — `medium`
7. **P5** — `low`
8. **P6** — `test`/`tests`

### Additional guidance

- Stripe / billing issues take precedence over new features
- Backend changes before frontend, unless frontend dependencies are already implemented

## Phase 1.5: CI Health Check

Before starting any sprint work, verify the repo has a green CI baseline. This prevents wasted effort on PRs that can never merge.

### 1.5a. Detect CI workflows

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null
```

### 1.5b. If NO CI exists → Create baseline CI

The repo has no quality gate. Create one before proceeding so all sprint PRs are validated.

1. Auto-detect the project type:

```bash
# Check for project markers
[ -f package.json ] && echo "node"
[ -f Pipfile ] || [ -f pyproject.toml ] || [ -f requirements.txt ] && echo "python"
[ -f go.mod ] && echo "go"
[ -f Cargo.toml ] && echo "rust"
```

2. Create a `chore/add-ci` branch:

```bash
git checkout -b chore/add-ci
```

3. Generate `.github/workflows/ci.yml` with a basic lint + test job appropriate for the detected stack:
   - **Node.js:** `pnpm install && pnpm lint && pnpm test`
   - **Python:** `pipenv install --dev && pipenv run lint && pipenv run test` (or `make lint && make test` if Makefile exists)
   - **Go:** `go vet ./... && go test ./...`
   - **Rust:** `cargo clippy && cargo test`

   Use the latest stable language version. Trigger on `push` and `pull_request` to `main`/`master`.

4. Commit, push, create PR, wait for checks, merge:

```bash
git add .github/workflows/ci.yml
git commit -m "chore: add baseline CI workflow for lint and tests"
git push -u origin chore/add-ci
gh pr create --title "chore: add baseline CI workflow" --body "Adds lint + test CI so sprint PRs have a quality gate."
sleep $(( RANDOM % 91 + 30 ))
gh pr checks $(gh pr view --json number -q .number) --watch --fail-fast
gh pr merge --squash --delete-branch
git checkout main && git pull
```

5. If the CI PR itself fails (e.g., existing lint errors), treat it as Edge Case 1 below — fix the issues in the same branch before merging.

### 1.5c. If CI exists → Verify default branch is green

Check if the latest CI run on the default branch is passing:

```bash
DEFAULT_BRANCH=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name)
gh run list --branch $DEFAULT_BRANCH --limit 1 --json conclusion,status -q '.[0]'
```

**If `conclusion` is `success`:** CI is green. Proceed to Phase 2.

**If `conclusion` is `failure` (or no runs exist):** The default branch is red. Sprint PRs will inherit these failures and can't merge cleanly.

1. Identify what's failing:

```bash
RUN_ID=$(gh run list --branch $DEFAULT_BRANCH --limit 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --log-failed 2>/dev/null | tail -50
```

2. Create a fix-it branch:

```bash
git checkout -b fix/ci-baseline
```

3. Fix the failing tests/lint/build issues. Use the appropriate subagent type based on the failures (e.g., `backend-developer` for test fixes, `devops-troubleshooter` for workflow issues).

4. Commit, push, create PR, wait for green, merge:

```bash
git add -A
git commit -m "fix: resolve CI failures on default branch"
git push -u origin fix/ci-baseline
gh pr create --title "fix: resolve CI failures on default branch" --body "Fixes existing CI failures so sprint PRs start from a green baseline."
sleep $(( RANDOM % 91 + 30 ))
gh pr checks $(gh pr view --json number -q .number) --watch --fail-fast
gh pr merge --squash --delete-branch
git checkout $DEFAULT_BRANCH && git pull
```

5. If the fix-it PR also fails, report to the user with the failure details and ask how to proceed. Do NOT start the sprint on a red baseline.

### 1.5d. Confirm green baseline

After either path (creating CI or fixing failures), verify:

```bash
echo "CI baseline confirmed green. Proceeding with sprint."
```

All subsequent worktree branches will be created from this clean state.

---

## Phase 2: Planning

Switch to `/plan` mode. For each selected issue:

1. Research the codebase to understand scope and dependencies
2. Create a task list with implementation steps
3. Identify which subagent type each issue needs
4. Check for inter-issue dependencies (order matters if issue B depends on issue A)

## Phase 3: Worktree Setup (per issue)

Each issue gets its own isolated worktree. This keeps main clean and lets subagents work in parallel without conflicts.

### 3a. Determine worktree directory

```bash
# Check existing convention
ls -d .worktrees 2>/dev/null || ls -d worktrees 2>/dev/null
```

If neither exists, create `.worktrees/` and ensure it's gitignored:

```bash
git check-ignore -q .worktrees 2>/dev/null || echo '.worktrees/' >> .gitignore
```

### 3b. Create feature branch + worktree

Branch naming: `fix/issue-<N>-<slug>` for bugs, `feat/issue-<N>-<slug>` for features, `chore/issue-<N>-<slug>` for maintenance.

```bash
BRANCH="feat/issue-<N>-<short-slug>"
git worktree add .worktrees/$BRANCH -b $BRANCH
```

### 3c. Install dependencies and verify baseline

Auto-detect project type and install inside the worktree:

```bash
cd <worktree-path>

# Node.js
[ -f package.json ] && pnpm install

# Python
[ -f Pipfile ] && pipenv install --dev
[ -f requirements.txt ] && pip install -r requirements.txt

# Go / Rust
[ -f go.mod ] && go mod download
[ -f Cargo.toml ] && cargo build
```

Run the test suite to confirm a clean baseline. If tests fail, report and ask before proceeding.

## Phase 4: Implementation (parallel subagents)

Dispatch subagents to work on each issue concurrently in their respective worktrees. Each subagent gets:

- The worktree path to work in
- The issue number and details
- Instructions to implement, test, lint, and commit

Use the appropriate subagent type based on the issue domain:

- `frontend-developer` — React, UI components, styling
- `backend-developer` — APIs, services, data layer
- `cloud-architect` — Infrastructure, AWS, Terraform, DevOps
- `test-writer` — Write new or updated tests for changed code (runs on sonnet to save tokens)
- `test-runner` — Python, JS, TS, TF, or other test execution
- `code-auditor` — Post-implementation security and quality audit
- `devops-troubleshooter` — CI/CD, deployment, monitoring
- `documentation-engineer` — Docs, guides, changelogs
- `terraform-specialist` — IaC modules, state management

### Validate-then-fix loop

After each code-change agent (`frontend-developer`, `backend-developer`, `cloud-architect`) finishes:

1. Launch a `test-writer` agent to write any new or updated tests for the changed code
2. Launch a `test-runner` agent to validate all tests pass
3. Launch a `/codex:review` agent to see if we missed anything (ensure it knows the task/issue details). Requires the external `codex` plugin (`/plugin install codex@openai-codex`); if it isn't installed, skip this step and note it in the result.
4. If tests fail, launch a follow-up code agent to address the issues
5. Repeat until green

### Pre-commit audit

Before committing each issue's work:

1. Launch a `code-auditor` agent to check for security/quality issues
2. Run pre-commit hooks to ensure clean output
3. Address any findings before pushing

## Phase 5: PR Creation (per issue)

For each completed issue, push the branch and create a PR:

```bash
cd <worktree-path>
git push -u origin $BRANCH

gh pr create \
  --title "<type>(<scope>): <description> (fixes #<N>)" \
  --body "$(cat <<'EOF'
## Summary
<2-3 bullets describing the change>

Fixes #<issue-number>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

## Phase 6: Conflict Check + CI Watch + Auto-Merge

After all PRs are created, process each PR through conflict check, CI watch, and merge.

### 6a. Check for merge conflicts

GitHub needs time to compute mergeability after PR creation:

```bash
# Wait for GitHub to compute merge status
sleep $(( RANDOM % 91 + 30 ))  # 30-120s random delay

# Check mergeability
gh pr view <PR-NUMBER> --json mergeable,mergeStateStatus -q '{mergeable: .mergeable, state: .mergeStateStatus}'
```

**If `mergeable` is `CONFLICTING`:** Report the conflict, list conflicting files, ask the user. Do NOT proceed to CI watch for that PR.

**If `mergeable` is `UNKNOWN`:** Wait 30s and retry (up to 3 times).

### 6b. Detect CI

```bash
ls .github/workflows/*.yml .github/workflows/*.yaml 2>/dev/null | head -1
```

### 6c. If CI exists: Watch and auto-merge

The GitHub API is slow to register checks on new PRs. Wait before polling, otherwise `gh pr checks` returns empty and you falsely conclude there are no checks.

```bash
# GitHub needs time to pick up the PR and queue workflows
sleep $(( RANDOM % 91 + 30 ))  # 30-120s random delay

# Watch for checks to complete (blocks until done or failed)
gh pr checks <PR-NUMBER> --watch --fail-fast
```

If `gh pr checks` returns no checks after the delay, retry once more after 60s. Only after two attempts with no checks treat it as "no CI."

**If all checks pass:**

```bash
# Verify still mergeable (no new conflicts since checks started)
MERGEABLE=$(gh pr view <PR-NUMBER> --json mergeable -q '.mergeable')
if [ "$MERGEABLE" = "MERGEABLE" ]; then
  gh pr comment <PR-NUMBER> --body "All CI checks passed. Auto-merging via mini-sprint."
  gh pr merge <PR-NUMBER> --squash --delete-branch
else
  echo "Checks passed but PR has conflicts. Cannot auto-merge."
fi
```

**If any check fails:**

Do NOT auto-merge. Instead:

1. Report which check(s) failed
2. Show failure output: `gh pr checks <PR-NUMBER>`
3. Ask the user how to proceed — fix in the worktree or leave the PR open

Process multiple PRs sequentially if they have dependencies (earlier PRs may change the merge base), or in parallel if independent.

### 6d. If no CI (should not happen after Phase 1.5)

Phase 1.5 guarantees CI exists before sprint work begins. If this state is reached somehow, report it as unexpected:

```bash
echo "WARNING: No CI detected despite Phase 1.5 health check. PRs created — review and merge manually."
```

Report all PR URLs and leave worktrees intact.

## Phase 7: Cleanup + Logging

### 7a. Clean up worktrees (merged PRs only)

For each PR that was merged:

```bash
cd <original-repo-path>
git worktree remove .worktrees/$BRANCH
git worktree prune
```

Keep worktrees intact for PRs that were NOT merged (CI failed, left open).

### 7b. Documentation updates

- Update the mkdocs site in `./docs` for any code changes
- Use the `update-obsidian` skill to update project notes
- Add a brief journal entry to today's Obsidian daily note: "Working on $ProjectName issues #X, #Y, #Z"

### 7c. Sprint report

Write/update `TODO.md` with checkbox items for each issue and their status:

```markdown
## Sprint YYYY-MM-DD

- [x] #N — <title> (PR #P — merged)
- [ ] #N — <title> (PR #P — CI failed, needs attention)
- [x] #N — <title> (PR #P — merged)
```

## Decision Flowchart

```
Fetch issues → Select top NUM_ISSUES
    → CI Health Check:
        → Has CI workflows?
            NO  → Create chore/add-ci branch
                → Generate lint + test workflow for detected stack
                → PR → Watch checks → Merge
                → (If CI PR fails, fix in same branch first)
            YES → Default branch green?
                YES → Continue
                NO  → Create fix/ci-baseline branch
                    → Fix failing tests/lint/build
                    → PR → Watch checks → Merge
                    → (If fix PR fails, report to user and stop)
    → Confirm green baseline
    → /plan to research and create task list
    → For each issue:
        → Create worktree + feature branch
        → Dispatch subagent to implement
        → Validate (tests, lint, build)
        → Push + Create PR
    → For each PR:
        → Sleep 30-120s (GH API lag)
        → Mergeable?
            CONFLICTING → Report conflicts, ask user
            UNKNOWN     → Retry up to 3x
            MERGEABLE   → Continue
        → Has CI?
            YES → Sleep 30-120s (checks registration lag)
                → Watch checks (gh pr checks --watch)
                → Pass + still mergeable? → Comment + Squash merge + Cleanup
                → Fail? → Report failure, keep worktree, ask user
            NO  → Report PR URL, keep worktree
    → Update docs + journal
    → Write sprint report to TODO.md
```
