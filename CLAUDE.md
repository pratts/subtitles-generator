# subtitles-generator

Subtitles for any video, in any language. The CLI (`subtitle`) is built from the first half of
[video-translator](https://github.com/pratts/video-translator): read it, never change it.
See ROADMAP.md for the phases and deferred features.

## Principles
- Build the simplest version; add a feature only when real output shows a need.
- Match the existing code style; keep comments short and useful.

## Secrets
- Never print `.env` values (`OPENAI_API_KEY`, `GOOGLE_APPLICATION_CREDENTIALS`, `HF_TOKEN`) or credential files.
  Show variable names only, e.g. `grep -o "^[A-Z_]*=" .env`.

## Repository rules
main is protected by the "Main branch protection" ruleset
([repo-baseline](https://github.com/pratts/repo-baseline)):
- No direct pushes or force pushes to main: every change, docs included, goes through an issue, a branch and a PR.
- Every commit must be signed.
- The user merges their own PRs (bypass for PRs only). Use a merge commit, not squash or rebase: those create new
  commits on main and leave the git notes on commits that are no longer on main.
- A PR's branch is deleted on GitHub automatically when it merges.
- No status checks are required yet. When CI is added, re-run
  `scripts/apply-baseline.sh pratts/subtitles-generator "<check name>"` in repo-baseline, after the check has run once.

## Workflow for each piece of work
1. Create a GitHub issue if there isn't one, assigned to whoever creates it (`--assignee @me`) and in its phase's
   milestone (`Phase 1: CLI`, `Phase 2: PyPI package`, `Phase 3: Web app`; see ROADMAP.md). Work between phases
   goes into the next open phase. An existing issue without them gets them.
2. Create a branch: `feat/issue-N-short-name`, `fix/issue-N-short-name` or `docs/issue-N-short-name`.
3. Implement.
4. Run the tests (`venv/bin/pytest -q`). Each new test must fail without the change it covers.
5. Test on a real video (the user gives the path).
6. Report and wait.

## "Commit and open the PR"
Only when the user says so:
- Make a GPG-signed commit (`git commit -S`).
- For a non-trivial commit, add a git note (`git notes add`) explaining why it is built this way, not what changed.
- Push the branch and `refs/notes/commits`.
- Open the PR, assigned to whoever opens it and in the issue's milestone
  (`gh pr create --assignee @me --milestone "<milestone>"`).

## "Merged. Sync…"
1. Check that the PR really is merged (`gh pr view N --json state,mergedAt`).
2. Check out main and pull with `git pull --prune` (GitHub has already deleted the remote branch).
3. Delete the local branch (`git branch -d`).
4. Push notes if needed (`git push origin refs/notes/commits`).
5. Give the updated task list.

## Setup
```bash
python3.12 -m venv venv
venv/bin/pip install -e ".[dev]" -c constraints.txt
```
