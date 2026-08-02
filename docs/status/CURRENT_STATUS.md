<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-02**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.49` |
| Production source commit | `21928e38a0df6fd217a8ba449eb675b94a282f01` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.49-21928e38a0df-5c891432a1d8` |
| Source evidence | 312 files; `e350497ba121e2420f00cbae3725334e8c45267e140388bbd0b5530e84135878`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `99ed9a4e-8167-44bd-b478-562ff8f4d17e`; 100% traffic; health `passed`; source updated and promoted for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0012` |
| Verified backup | `20260802-091628-350429-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `f827c8932bd78ca2b2528728e6770c539c6f2ad8adfa64a3ec85cd69485e8fd9` |
| Previous application source | `v1.2.0-rc.47` — historical only |
| Previous Worker rollback version | `a7218f51-ec6c-4002-a9be-9dfbb691136c` |
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
