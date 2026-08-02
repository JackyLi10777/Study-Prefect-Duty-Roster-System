<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-02**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.47` |
| Production source commit | `15f53f97eda81b3f4b1518a44567e18171891711` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.47-15f53f97eda8-5c891432a1d8` |
| Source evidence | 310 files; `3472686105c5a7356da526995438aaef025c52b8c252dc17c21e3de01e27e679`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `a7218f51-ec6c-4002-a9be-9dfbb691136c`; 100% traffic; health `passed`; source updated and promoted for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0012` |
| Verified backup | `20260801-232211-102949-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `13ca64426a59fcaae098548830de79c3da896a483b2aa8680a0f84488323c432` |
| Previous application source | `v1.2.0-rc.45` — historical only |
| Rollback contract | Migration-aware controlled restore; never switch old code alone |

## 驗收 / Acceptance

- Automated and release evidence: **passed**.
- Supervised Head Study Prefect and teacher-advisor acceptance: **尚待完成 / Pending**.
- HTTP 200, health, or CI alone never substitutes for rendered workflow and human acceptance evidence.

## 更新契約 / Update contract

1. Update `current-release.json` only from observed deployment, recovery, and acceptance evidence.
2. Run `python -X utf8 scripts/project_governance.py --write` to regenerate this page and every status notice.
3. Run `python -X utf8 scripts/project_governance.py --check` and the staged verifier before push.
4. Keep historical releases in `CHANGELOG.md` and evidence records; do not copy mutable current identifiers into ordinary guides.
