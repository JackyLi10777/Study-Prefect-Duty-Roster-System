<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-14**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.58` |
| Production source commit | `e90bb8fdb95ca874f668b5a7134853756471635f` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.58-e90bb8fdb95c-5c891432a1d8` |
| Source evidence | 319 files; `c57778ce438c1c23c824c444827db7eeb9166d20be3ba3e78f1bb1221fee5283`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `7951ca55-ffda-4f16-b570-d37486311914`; 100% traffic; health `passed`; source unchanged for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0014` |
| Verified backup | `20260813-161554-736678-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `0e0ee9cc9a592eeea66055e107c461e859f3ccec2791cb06f051e7078c3febc2` |
| Previous application source | `v1.2.0-rc.57` — historical only |
| Previous Worker rollback version | `7951ca55-ffda-4f16-b570-d37486311914` |
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
