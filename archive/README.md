# Public project archive / 公開專案封存

This directory preserves non-secret artifacts requested for long-term GitHub
storage without turning live runtime paths into future commit targets.

## Contents

- `fictional-data/`: a consistent SQLite online-backup snapshot containing the
  24 fictional Chinese seed identities and no roster, leave, fairness, or
  publication records.
- `release-evidence/logs/`: privacy-safe local support and browser-verification
  evidence captured for this release.
- `release-evidence/output/`: Practice Mode browser screenshots.
- `operator-preferences/`: the current non-secret local music-library structure,
  archived away from the writable runtime path.
- `MANIFEST.json`: SHA-256 and size evidence for every archived file.

The original built-in music files remain under `music/` so a fresh clone keeps
the intended optional local listening experience. Runtime `.env`, NiceGUI
storage secrets, Tunnel/API tokens, dependency folders, caches, and temporary
performance fixtures are deliberately absent because they are machine state,
not reconstructable project content.

Legacy reference credential files are also excluded. A field-compatible,
placeholder-only `demo_code2/service_account.example.json` preserves the old
integration shape without publishing a private key.

Regenerate this archive only when the live database still passes the
fictional-fixture guard:

```powershell
python -X utf8 scripts\build_public_archive.py
```

The command refuses any database containing roster weeks, assignments, leave,
fairness-ledger, or adjustment rows.
