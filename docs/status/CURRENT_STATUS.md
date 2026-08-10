<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-10**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.57` |
| Production source commit | `f83bbbb095e5fb2c029ac37add1308f33dd2eb9e` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.57-f83bbbb095e5-5c891432a1d8` |
| Source evidence | 317 files; `33e77fb6cddc791b60e2b695db417f29d508b77bba71f143186c4f5591ba916a`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `7951ca55-ffda-4f16-b570-d37486311914`; 100% traffic; health `passed`; source updated and promoted for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0014` |
| Verified backup | `20260810-111743-227200-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `d9603c329c995132d9955bcfbe74aafa46c5b5c6e0393e7f009b76bc2b746a29` |
| Previous application source | `v1.2.0-rc.56` — historical only |
| Previous Worker rollback version | `e118e783-fd89-489d-9c10-acba67056d50` |
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
