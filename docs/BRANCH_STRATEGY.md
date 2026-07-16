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

1. Run `python -X utf8 scripts/verify_update.py`. It classifies the committed
   change and runs the smallest safe profile; unknown paths fail closed.
2. If the plan reports a formal runtime release, confirm
   `logs/release-candidate-report.json` reports all gates passed for the current
   runtime fingerprint. Do not rerun hygiene or security separately because
   the formal verifier already owns those gates.
3. Build the public fictional-data/evidence archive with
   `python -X utf8 scripts/build_public_archive.py`.
4. Review staged paths; never use an unreviewed `git add -A`.
5. Commit on `main`, update `nicegui-self-hosted` only for a matching platform
   release, and push without force.
