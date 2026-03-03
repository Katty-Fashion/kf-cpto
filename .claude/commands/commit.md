# /commit - Session Checkpoint & Git Sync

### 1. GitOps Engineer Agent
Commit and push all changes with conventional commit format.

**IMPORTANT**: Must stage ALL files including newly created session archives:
```bash
git add -A  # Stage all changes including new files in sessions/
```
## Requirements
- No attribution messages in commits (no "Generated with...", "Co-Authored-By...", "Created by...")
- All work is company-owned
- Include session milestone in commit body
- Bump version before commit if breaking changes and updated tags

## Simple Git Flow - Keep It Simple
Use ONLY: `git add`, `git commit`, `git push` - nothing else!

### NEVER Use These Commands
- **git stash** / **git stash pop** - Pre-commit hooks can trap work in stash
- **git reset** - Can lose uncommitted work
- **git rebase** - Can complicate history and cause conflicts
- **git checkout -- <files>** - Discards uncommitted changes

### Safety Checks (Course Correction)
- Before committing, run `git stash list` to check no work is trapped in stash
- After committing, run `git stash list` again to verify no new stashes were created
- If stash is not empty, WARN the user loudly - there may be trapped work from previous failed operations

### If Something Fails
- If pre-commit hooks fail, STOP immediately and tell the user what failed
- Do NOT retry automatically - let user decide how to proceed
- Report the exact error message so user can fix the underlying issue

## Arguments
`$ARGUMENTS` - Optional flags and custom commit summary

### Supported Flags
- `--deploy` - Also deploy to production droplet after committing
- Any other text is treated as the custom commit summary

### Examples
- `/commit` - Commit only (no deploy)

**IMPORTANT**: The gitops-engineer needs the session state context from session-state-manager to create a meaningful commit message that captures the full scope of work done.
