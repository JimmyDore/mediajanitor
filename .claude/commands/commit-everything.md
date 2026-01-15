# Commit Everything

Commit all changes in the working directory. If changes span multiple unrelated topics, create separate commits for each.

## Instructions

1. Run `git status` and `git diff` to see all changes
2. Analyze the changes and group them by topic/scope:
   - Changes to the same feature = one commit
   - Unrelated changes (e.g., bug fix + new feature + docs update) = separate commits
3. For each group:
   - Stage only the files for that group: `git add <files>`
   - Commit with appropriate message following project conventions:
     - `feat(scope): description` for features
     - `fix(scope): description` for bug fixes
     - `chore(scope): description` for maintenance
     - `docs: description` for documentation
4. After all commits, run `git status` to confirm working directory is clean

## Examples of topic separation

- `prompt.md` + `afk-ralph.sh` changes about Ralph workflow = one commit
- `frontend/src/routes/+page.svelte` UI change + `backend/app/routers/auth.py` auth fix = two commits
- Multiple files for one feature (model + router + test) = one commit
