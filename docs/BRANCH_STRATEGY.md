# Repository branches / 版本分支

This repository keeps deployment generations visible instead of rewriting the
legacy Streamlit history.

## Active branches

| Branch | Role | Operator |
|---|---|---|
| `main` | Protected release line | **Codex only** (via PR merge) |
| `codex/mainline` | Protected Codex integration line (tracks `main`) | Codex merges reviewed PRs |
| `collab/agent-workspace` | Clean synchronization baseline only | Codex maintains; agents do not develop here |
| `collab/<agent>/<task>` | One isolated auxiliary-agent task | One agent → PR to `codex/mainline` |
| `nicegui-self-hosted` | Platform snapshot at release | Codex |
| `streamlit-cloud` | Historical Streamlit reference | Read-only |

## Worktree layout

| Local path | Branch |
|---|---|
| `D:\code_v3` | one task-scoped `codex/<task>` based on `codex/mainline` |
| `D:\code_v3-agent` | one assigned `collab/<agent>/<task>` at a time |

AI agents must follow [`docs/AI_AGENT_GIT_GUIDE.md`](AI_AGENT_GIT_GUIDE.md) for
commit conventions, branch rules, and the PR workflow.

## Rules

- `main` is the current source of truth. It accepts changes through a pull
  request with successful `test-and-audit` and `analyze` checks; force pushes,
  deletion and unresolved conversations are blocked for administrators too.
- While the repository has one human maintainer, the pull-request rule requires
  zero approvals so the owner is not deadlocked by GitHub's self-approval rule.
  Add one required approval and CODEOWNERS review before granting a second human
  or automation account write access.
- `codex/mainline` is the protected integration queue. Auxiliary agents start
  from it, submit task-scoped `collab/<agent>/<task>` pull requests, and never
  share one writable branch or worktree. The baseline
  `collab/agent-workspace` is protected too and is not an integration
  destination.
- `nicegui-self-hosted` records the matching platform edition. Future
  deployment-only changes may be developed there and merged back to `main`.
- `streamlit-cloud` is retained for historical comparison and recovery. Do not
  copy its UI-owned policy logic into the NiceGUI runtime.
- Never force-push a published branch; GitHub protection enforces this on
  `main`. Preserve old commits through normal
  descendants, tags, or an explicitly named archival branch.
- GitHub Actions requires immutable full-SHA action references. The active
  `Protect immutable release tags` repository ruleset allows a new `v*` tag to
  be created after the release gates pass, then blocks updating or deleting
  that tag. Changing this rule is a security-sensitive repository operation.
- Runtime credentials, Cloudflare tokens, session secrets, dependency caches,
  and temporary build directories are not repository artifacts.

## Release sequence

1. Run `python -X utf8 scripts/verify_update.py`. It classifies the committed
   change and runs the smallest safe profile; unknown paths fail closed.
2. If the plan reports a formal runtime release, confirm
   `logs/release-candidate-report.json` reports all gates passed for the current
   runtime fingerprint. Do not rerun hygiene or security separately because
   the formal verifier already owns those gates.
3. Build the public fictional-data/evidence archive with
   `python -X utf8 scripts/build_public_archive.py`.
4. Review staged paths; never use an unreviewed `git add -A`.
5. Push a topic branch, open a pull request, and wait for `test-and-audit` plus
   `analyze`. `analyze` covers both the Python application and the Worker
   JavaScript／TypeScript boundary. Resolve every review conversation before
   merge.
6. Merge without force. Update `nicegui-self-hosted` only for a matching
   platform release after the protected `main` commit and immutable tag agree.

The live permission contract and incident recovery path are owned by
[`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md). `CODEOWNERS` routes review;
it does not replace status checks, protected branches, least-privilege tokens,
verified backups, or immutable release evidence.
