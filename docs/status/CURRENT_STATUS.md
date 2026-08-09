<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-09**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.54` |
| Production source commit | `f027628c5a0045d8a946be9a3453e041d03367d1` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.54-f027628c5a00-5c891432a1d8` |
| Source evidence | 316 files; `738c45917fdcbeeb84a523a1f1cc3179adee693b07e156bdb74fa6f8748b3ef8`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `053b8f6e-c5ed-4259-ac34-aaefa4dfb23d`; 100% traffic; health `passed`; source updated and promoted for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0014` |
| Verified backup | `20260809-093349-010387-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `65e2d9c086b0aa4e9495f17d55ad2d62ea238c049d046debba7b124205166a29` |
| Previous application source | `v1.2.0-rc.52` — historical only |
| Previous Worker rollback version | `3bac2eee-246f-4524-9725-4249770017b0` |
| Rollback contract | Migration-aware controlled restore; never switch old code alone |

## 驗收 / Acceptance

- Automated and release evidence: **passed**.
- Supervised Head Study Prefect and teacher-advisor acceptance: **尚待完成 / Pending**.
- Physical off-site BitLocker recovery drill: **待實體媒體演練 / Pending physical-media drill**.
- HTTP 200, health, or CI alone never substitutes for rendered workflow and human acceptance evidence.

## 更新契約 / Update contract

1. Update `current-release.json` only from observed deployment, recovery, and acceptance evidence.
2. Run `python -X utf8 scripts/project_governance.py --write` to regenerate this page and every status notice.
3. Run `python -X utf8 scripts/project_governance.py --check` and the staged verifier before push.
4. Keep historical releases in `CHANGELOG.md` and evidence records; do not copy mutable current identifiers into ordinary guides.
