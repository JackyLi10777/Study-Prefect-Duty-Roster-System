<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-01**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.45` |
| Production source commit | `90777345ea9ed5652c73873edb3c8c846a9ceac5` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.45-90777345ea9e-5c891432a1d8` |
| Source evidence | 308 files; `032bf3d5d41a74e6ad50090ab7ffb13af6e5cca43a23c24adb3f8506d6d29a83`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `394e2205-ae8f-4eef-a13a-e701931e6f0d`; 100% traffic; health `passed`; source unchanged for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0012` |
| Verified backup | `20260801-064628-279309-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `bdf8366aa7b2d3b91d6754dc58d9ec0b6725bf29f7fe3e7d5bf3592b223f69e8` |
| Previous application source | `v1.2.0-rc.43` — historical only |
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
