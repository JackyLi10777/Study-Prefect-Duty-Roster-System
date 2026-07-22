# Repository branches / 版本分支

This repository keeps deployment generations visible instead of rewriting the
legacy Streamlit history.

| Branch | Runtime | Purpose |
|---|---|---|
| `main` | NiceGUI, SQLite, Windows/Linux self-hosted | Current maintained release and handover source |
| `nicegui-self-hosted` | Same release snapshot as `main` at publication | Platform-labelled deployment branch for a dedicated Windows PC or Linux host |
| `streamlit-cloud` | Streamlit Cloud reference implementation | Preserved legacy cloud generation, renamed from `ai` without rewriting its commit |

## Rules

- `main` is the current source of truth. It accepts changes through a pull
  request with successful `test-and-audit` and `analyze` checks; force pushes,
  deletion and unresolved conversations are blocked for administrators too.
- While the repository has one human maintainer, the pull-request rule requires
  zero approvals so the owner is not deadlocked by GitHub's self-approval rule.
  Add one required approval and CODEOWNERS review before granting a second human
  or automation account write access.
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
