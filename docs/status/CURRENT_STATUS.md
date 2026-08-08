<!-- Generated from current-release.json by scripts/project_governance.py. Do not edit by hand. -->
# 目前系統狀態 / Current system status

> 最後核實 / Last verified: **2026-08-09**. This page records observed release truth; a newer repository commit does not imply a newer production deployment.

## 正式運行 / Live production

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| 狀態 / State | `live` |
| Release | `v1.2.0-rc.52` |
| Production source commit | `72621076f74caf9568fda1576d62311e0a26043c` |
| Immutable bundle | `C:\SingYinRoster\releases\v1.2.0-rc.52-72621076f74c-5c891432a1d8` |
| Source evidence | 314 files; `c4f224140c3b2bb935f4d367bf0fccf55800fd28a6a697e66bd261b70e097b6f`; 15/15 gates passed |
| Windows service | `SingYinRosterSvc`; health `passed`; readiness `passed`; `writeReady=true`; `maintenance=false`; `recoveryRequired=false`; `pendingBackups=0` |
| Canonical Worker | `3bac2eee-246f-4524-9725-4249770017b0`; 100% traffic; health `passed`; source updated and promoted for this release |

## 資料與復原 / Data and recovery

| 項目 / Item | 已核實值 / Verified value |
|---|---|
| Alembic head | `0013` |
| Verified backup | `20260808-164321-281874-manual_verified_backup.sqlite3` |
| Backup SHA-256 | `1d542f5aac6b25eff4abf5f79cddd295ebc04a6ef797a7ac8b8f88f22d13928a` |
| Previous application source | `v1.2.0-rc.51` — historical only |
| Previous Worker rollback version | `480e1d1a-c711-4608-aa66-c261d443928a` |
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
