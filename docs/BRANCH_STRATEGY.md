# Repository branches / 版本分支

## Current workflow

`main` is the sole active integration and release line. Start each task from
the latest `origin/main`, use an isolated worktree and a `codex/<task>` branch,
and submit its pull request directly to `main`. One writable worktree has one
owner. Preserve existing uncommitted work; do not reuse a dirty checkout.

| Branch | Role |
|---|---|
| `main` | Protected integration line; no direct or force pushes |
| `codex/<task>` | Isolated implementation or review; PR to `main` |
| `codex/mainline` | Historical integration line; not a new base or PR target |
| `collab/agent-workspace`, `collab/*` | Historical collaboration references; preserve existing work |
| `nicegui-self-hosted` | Matching platform release snapshot |
| `streamlit-cloud` | Read-only historical Streamlit reference |

Full task rules are in [AI Agent Git Guide](AI_AGENT_GIT_GUIDE.md).
These documentation changes do not change remote protection rules.

## Source and integration rules

- Fetch before creating a task branch; record its base SHA.
- Review explicit paths and commit by concern. Never stage an unreviewed
  `git add -A` or `git add .`.
- Integrate completed peer work from an immutable SHA and a reviewed functional
  difference. Do not cherry-pick stale giant patches or overwrite whole modules
  to resolve competing implementations.
- Shared changes with the same Git tree are one source, not two independent
  implementations. Preserve the accepted behavior tests from both sources.
- If main advances, synchronize by a normal reviewed merge and revalidate.
  Never rebase or amend already shared history.
- Keep credentials, runtime databases, logs and unapproved data out of commits.
- Preserve immutable release tags and historical evidence; never force-push,
  delete remote branches, or move a release tag as a cleanup shortcut.
- `nicegui-self-hosted` is not a second implementation line. Update it only
  when it represents the matching verified platform release.

## Verification and release sequence

1. Review and stage intended changes. Run
   `python -X utf8 scripts/verify_update.py --staged`.
   This is pre-push verification, not a release drill.
2. Push the task branch and open a PR directly to `main`. Require
   `test-and-audit`, `analyze` and every applicable required check; resolve
   review conversations before merge. Do not use an administrator bypass.
3. After merge, create a clean release checkout at that exact protected-main
   commit and run `python -X utf8 scripts/verify_update.py --release`.
   Bind all evidence to that source; a branch report cannot certify the merge.
4. Reconcile host, database, verified backup and Worker state before deployment.
   Use the immutable bundle and controlled recovery workflow, never a code-only
   rollback across incompatible schemas.
5. Update the generated current-release state only after observed deployment.
   CI, a merge, HTTP 200 and a running host do not prove formal school adoption.

The school has not formally adopted the system. The approved
[prelaunch plan](plans/20260905-system-integration.md) uses a new formal database
and separate fictional test data; historical host release records remain
evidence of their observed technical deployment only.

The [security and privacy contract](SECURITY_AND_PRIVACY.md), immutable Actions
references, protected main and verified recovery obligations remain in force.
