# Repository branches / 版本分支

This repository keeps deployment generations visible instead of rewriting the
legacy Streamlit history.

| Branch | Runtime | Purpose |
|---|---|---|
| `main` | NiceGUI, SQLite, Windows/Linux self-hosted | Current maintained release and handover source |
| `nicegui-self-hosted` | Same release snapshot as `main` at publication | Platform-labelled deployment branch for a dedicated Windows PC or Linux host |
| `streamlit-cloud` | Streamlit Cloud reference implementation | Preserved legacy cloud generation, renamed from `ai` without rewriting its commit |

## Rules

- `main` is the current source of truth and must pass the release-candidate verifier.
- `nicegui-self-hosted` records the matching platform edition. Future
  deployment-only changes may be developed there and merged back to `main`.
- `streamlit-cloud` is retained for historical comparison and recovery. Do not
  copy its UI-owned policy logic into the NiceGUI runtime.
- Never force-push a published branch. Preserve old commits through normal
  descendants, tags, or an explicitly named archival branch.
- Runtime credentials, Cloudflare tokens, session secrets, dependency caches,
  and temporary build directories are not repository artifacts.

## Release sequence

1. Run `python -X utf8 scripts/verify_release_candidate.py`.
2. Confirm `logs/release-candidate-report.json` reports all gates passed.
3. Build the public fictional-data/evidence archive with
   `python -X utf8 scripts/build_public_archive.py`.
4. Review staged paths and run `python -X utf8 scripts/check_repository_hygiene.py`.
5. Commit on `main`, update `nicegui-self-hosted`, and push both without force.
