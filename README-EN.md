# Sing Yin Study Prefect Duty Roster System

> **Not to be served, but to serve. — Mark 10:45**

I am LI Chuangjie Jacky, Head Study Prefect for 2026–2027 at Sing Yin Secondary
School. I co-created this maintained, local-first roster platform with Codex so
that future Head Study Prefects can inherit a safe and understandable weekly process:

**Feedback and contact:** Questions or suggestions about the workflow, interface,
fairness explanation, or handover are welcome at
[`s10777@syss.edu.hk`](mailto:s10777@syss.edu.hk). Include an OP/REQ support
reference when one is shown, but do not attach names, leave details, rosters,
PDFs, databases, backups, screenshots, or complete logs.

**prepare → generate draft → review → publish once → export bilingual PDF →
adjust published leave → explain fairness → back up, restore, and hand over.**

The public entrance presents one prepared duty desk in paired morning-light and evening-dark versions. An unlabelled ledger, three paper workflow markers, and a restrained teal line convey record keeping, the three-step weekly sequence, and continuous service. Both original WebP assets are local to the project and contain no people, student data, writing, crest, external tracking, or third-party image request; reduced-motion mode remains a fully readable static entrance.

[Traditional Chinese README](README.md) · [Operator guide](docs/OPERATOR_GUIDE.md)
· [Architecture](docs/NICEGUI_ARCHITECTURE.md) · [Release status](PROJECT_STATUS.md)
· [Canonical-site access guide](docs/PUBLIC_ROSTER_VIEWER.md)

**Current pre-v1.2 deployment (2026-07-17):** `C:\SingYinRoster` has been
forward-recovered to the schema-compatible rc4 source at commit `30f282f`;
`/healthz` is healthy and `/readyz` is ready. NiceGUI remains loopback-only on
`127.0.0.1:8080`. The canonical Worker deliberately remains on the pre-v1.2
production baseline. The rc5 origin rollout created a fresh verified backup and
passed isolated restore, then rolled back safely because strict local readiness
treated the intentionally pending `cloudflare_access` warning as fatal before
the matching Worker stage. This remains the documented **v1.1 rollback** baseline while the rc6 correction defers only that warning to the
Worker stage; every failure and every other warning remains blocking, and live
acceptance is still mandatory. A
supervised Windows reboot, administrator login/logout, long reconnect, upload
and PDF acceptance remain outstanding; official-data cleanup remains a
separately authorized operation.

## Repository editions

| Branch | Platform | Status |
|---|---|---|
| `codex/unified-guest-redesign` | NiceGUI + SQLite, Windows self-hosted | rc7 passed all 13 formal gates; controlled origin/Worker rollout in progress |
| `main` | NiceGUI + SQLite, self-hosted | rc7 will be synchronized before the controlled switch; production remains on healthy/ready rc6 `0c36af3` |
| `nicegui-self-hosted` | Dedicated Windows or Linux host | Platform-labelled release snapshot |
| `streamlit-cloud` | Streamlit Cloud | Preserved legacy reference |

The NiceGUI edition is a substantial architectural rebuild. It does not copy
the Streamlit page handlers: policy remains in `roster_policy`, generation in
`roster_core`, and durable work in `roster_workflow`.

## Canonical daily entry and Windows maintenance start

The only URL distributed to users is
<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>.

The pre-v1.2 Worker still serves its data-free tour and browser-only fictional
trial. The v1.2 rc5 source candidate replaces those two
separate products with one NiceGUI product: a visitor selects **Guest
experience** to receive a bounded 30-minute fictional workspace, while an
approved operator selects **Admin login**, enters an exact allowlisted email
address and the one-time code sent by Cloudflare Access, and receives the
official workflow at the same routes. `/guest` and `/try` become compatibility
redirects; an explicitly issued `/view#…` link remains the separate encrypted,
read-only published-roster viewer.

The v1.2 Worker and origin authenticate both modes with server-verified,
HMAC-signed principals. On 2026-07-18 the reproducible 240-input rc7 source
passed all 13 formal release gates with fingerprint
`e06732d46588ff65e5771f32c7d40aa9cf5b19867e1f44bd9fce68f93edca5db`,
including isolated Admin/Guest browser, mobile, reduced-motion, performance,
write/PDF, backup, and recovery evidence. The matching report ran from
`2026-07-18T19:41:21.506585+08:00` to `2026-07-18T19:46:28.277693+08:00`;
machine verification is complete. Cloudflare Access is screenshot-confirmed to
protect only the exact `/auth/login` destination. The planned immutable rollout
reference is `v1.2.0-rc.7`. The running Windows origin is the healthy and ready
`v1.2.0-rc.6` release at `0c36af3`; rc7 remains pending until the controlled
host and Worker switch plus the live Admin/Guest/Viewer sequence complete. The
application has no custom password database.

The commands below prepare a host or maintenance workstation; they are not a
second normal entry point.

```powershell
python -m pip install --require-hashes -r requirements.lock
Copy-Item .env.example .env
```

During maintenance or a Cloudflare outage, double-click
`START_SING_YIN_ROSTER.cmd`. The launcher reuses an existing service, resolves
local port conflicts, waits for a real HTTP response, and opens the exact local
URL. Localhost and the enrolled private-WARP address remain recovery paths only.

For a new dedicated Windows 11 host, follow the zero-knowledge
[`WINDOWS_DEDICATED_HOST_SETUP.md`](docs/WINDOWS_DEDICATED_HOST_SETUP.md).
It includes idempotent preparation and Task Scheduler scripts. Optional remote
browser access is prepared separately by
[`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](docs/CLOUDFLARE_REMOTE_ACCESS_SETUP.md),
which keeps the origin on `127.0.0.1` and refuses activation unless an
unauthenticated request is redirected to Cloudflare Access.

Key-only host maintenance is documented separately in
[`WINDOWS_SSH_MAINTENANCE.md`](docs/WINDOWS_SSH_MAINTENANCE.md). The SSH server
binds only to loopback, disables password authentication and forwarding, and
does not create a public or LAN-facing port 22.

For a fully isolated fictional rehearsal, double-click
`START_PRACTICE_MODE.cmd`. Practice Mode has separate SQLite, backups, logs,
preferences, port range, persistent bilingual identity, and non-official PDF
marking. Close it and use `RESET_PRACTICE_MODE.cmd` for a clean rehearsal.

The Dashboard devotional direction offers **Default setting**, **Clear
guidance**, and **Quiet comfort**. The default follows the current appearance
as a recommendation only. Local page-context music makes one page-ready attempt
at a browser-local default of 24% and always exposes pause/off controls. If two
consecutive routes resolve to the same local track, the current browser session
continues its position and playing/paused state instead of restarting it; this
continuity never enters SQLite or permanent browser storage.

At the end of a school year, use **Prepare new school-year directory** from the
Handover Guide only after the final roster, published-duty adjustments, and
fairness reconciliation are complete. The workflow takes the maintenance lock,
creates verified before/after backups, archives active prefect records, and
withdraws unused pre-generation leave. It preserves old rosters, the fairness
ledger, audit history, and archived names; it is not a database wipe.

The official clean-first-use contract requires the application to start with an
empty migrated database and never auto-seed demonstration prefects. Seeing an
empty directory on first use is correct: import and review the real directory
only after rehearsal. Fictional seed data belongs to Practice Mode and the
bounded v1.2 Guest adapter, never the official database. The installed host
still requires Viewer-link revocation and the separately authorised controlled
reset before an empty official-data state may be claimed; the rc5 application
rollout does not perform that data-clearing operation.

### v1.2 rc5 candidate: one Guest and Admin product

Guest and Admin use the same NiceGUI routes, navigation, components, and weekly
sequence. A server-verified `PageContext` resolves either the official
`RosterWorkflow` and SQLite database or a bounded `GuestWorkspaceAdapter`
populated only with fixed fictional Chinese names. UI hiding is not the
security boundary: callbacks, services, downloads, exports, storage, sharing,
and integrations recheck capabilities.

Each Guest tab receives a separate process-memory workspace. The origin pushes
each meaningful revision back to that exact tab as a signed token stored only
in `sessionStorage`. A refresh can restore the latest token only after the
server verifies its session, workspace, tab, revision, application boot, and a
live-connection nonce. Duplicated tabs receive new workspaces; copied,
tampered, expired, stale, or old-boot tokens are rejected and replaced by the
safe fictional fixture. Sign-out, expiry, revocation, and cross-tab session
termination clear temporary state. Guest PDF/JSON downloads are memory-only,
one-shot, `DEMO`-marked, and `Cache-Control: no-store`.

Focused snapshot-bridge tests and the matching 13-gate rc5 report now pass, but
the report is not a claim that rc5 is already deployed. The controlled rc5 host
procedure must still create its fresh verified backup and isolated restore,
switch the origin and Worker, and complete live acceptance. Exact commands are
documented in
[`PUBLIC_ROSTER_VIEWER.md`](docs/PUBLIC_ROSTER_VIEWER.md) and
[`WINDOWS_DEDICATED_HOST_SETUP.md`](docs/WINDOWS_DEDICATED_HOST_SETUP.md). The
complete risk matrix is in [`UPDATE_WORKFLOW.md`](docs/UPDATE_WORKFLOW.md).

## Operator workflow

1. Verify Chinese names, roles, classes, and available days.
2. Record known pre-generation leave for the correct Monday-based week.
3. Generate and review the draft. Vacancies remain visible.
4. Make any manual draft change through the audited reason form.
5. Publish once. Publication—not draft generation—posts `history_weight`.
6. Download the Chinese or English landscape A4 schedule; names remain Chinese. The export dialog can hide the crest. The clean sharing version omits the internal-use line, page number, and Scripture hint by default; enable the supplementary footer only for an intentional archival copy.
7. For a late absence, use the published-duty adjustment workflow rather than
   regenerating the week.
8. Review fairness, verified backups, handover readiness, and recovery evidence.
9. When recipients need browser-direct viewing, explicitly create an expiring,
   revocable same-host `/view#…` link for the published roster. After a
   published-duty adjustment, issue a fresh link and revoke the old one.

## Policy invariants

- Assistant Head Study Prefects serve only `Assist. in charge`.
- Study Prefects serve only Rooms 302, 303, and 202.
- Room 302: one prefect, Monday–Friday.
- Room 303: two prefects, Monday–Friday.
- Room 202: two prefects, Monday, Wednesday, and Thursday only.
- No same-person duplicate duty on one day.
- Generated duties are not consecutive across days.
- Persistent `history_weight` remains the fairness anchor.

## Platform & team

The in-app **Platform & team** centre explains why the service exists before
showing how it is built. It combines an anonymous live readiness snapshot,
the official Study Prefect Team roles with explanatory responsibility titles,
four capability groups, four outcome-led solutions, operating principles, and
the co-creation note. The live strip never exposes names, classes, leave,
roster content, backup paths, or audit records.

Official roles remain Head Study Prefect, Assistant Head Study Prefect, Study
Prefect, and Teacher Advisor. Labels such as Service Governance Lead and Room
Service Steward explain accountability only; they are not database values or
replacement school titles. Weekly Operations, Fairness Assurance, Service
Experience, and Systems Continuity are capability groups, not claims of extra
staff or headcount.

## Engineering & quality evidence

The in-app engineering page turns the strongest evidence from this README,
the architecture guide, and the release report into a readable quality centre.
It presents the complete automated suite, the current report's real passed/total
gate ratio, a five-layer system blueprint, six reliability capabilities, and the
four-stage build story. The gate chain includes browser performance, bounded
memory growth, and phone-width overflow checks. These are release facts, not
usage, commercial, or vanity KPIs; source changes make previous evidence stale.

## Architecture

```mermaid
flowchart LR
    GUEST["Guest"] --> EDGE["One workers.dev site\nCloudflare Worker"]
    ADMIN["Administrator\nAccess email code"] --> EDGE
    EDGE -->|read only| VIEW["Encrypted published roster"]
    EDGE -->|signed Guest/Admin principal| VPC["Workers VPC + Tunnel"]
    VPC --> UI["NiceGUI bilingual UI"]
    UI -->|Guest adapter| GUESTMEM["Bounded process memory\nsigned sessionStorage bridge"]
    GUESTMEM --> TRIALPDF["One-shot DEMO\nPDF / JSON"]
    UI -->|Admin adapter| WF["roster_workflow transactions"]
    WF --> CORE["roster_core generation"]
    CORE --> POLICY["roster_policy rules"]
    WF --> DB["SQLite + Alembic"]
    WF --> BACKUP["Verified snapshot + manifest"]
    DB --> PDF["Chinese / English PDF\nChinese names in both"]
    WF --> ENC["Explicit minimum-data\nAES-GCM share"]
    ENC --> VIEW
```

SQLite writes use WAL, foreign keys, busy timeouts, transactions, online
snapshots, SHA-256 manifests, integrity checks, and managed restore. A
database-level publication claim prevents two browser tabs from posting the
same fairness workload twice.

The separate in-app **System architecture & trust** page stays focused on the
six-stage service lifeline, five owning layers, four verifiable trust
contracts, recovery boundaries, and operator FAQ. This separation keeps brand
context discoverable without making a daily operator scan one oversized page.

## Interface quality

- Traditional Chinese first, complete English counterpart.
- Light and dark themes with paired atmosphere artwork.
- Phone-specific roster and prefect cards rather than clipped desktop tables.
- Keyboard focus, semantic landmarks, 44px actions, reduced-motion support.
- Dignified Daily Verse reading language separate from the workbench.
- Local ambience makes one low-volume autoplay attempt after each page is ready.
  The operator can pause it or turn cross-page autoplay off at any time, and the
  control exposes playing, paused, browser-blocked, and off states. The separate
  visible YouTube player never autoplays.
- Privacy-safe `OP-...` and `REQ-...` support references.

Mature SaaS patterns are treated as hypotheses, not a visual target. The system
adopts a pattern only when it improves first-use comprehension, task completion,
recovery, mobile use, or accessibility; it deliberately omits pricing tiers,
marketing funnels, invented KPIs, and decorative density from the operator
workbench.

## Deployment

The maintained OP application remains a long-running Python service on a
dedicated Windows 11 PC, with NiceGUI bound to `127.0.0.1`. In the verified v1.2
rc5 design, the canonical `workers.dev` site is the public front door:
**Guest experience** creates a time-limited signed Guest session, while
**Admin login** invokes a path-specific Cloudflare Access policy. Both verified
modes are proxied to the same NiceGUI origin with different signed principals;
the origin resolves different adapters. After Access authentication, the
Worker independently verifies the JWT signature, audience, issuer, expiry, and
exact administrator email, then issues a short-lived signed HttpOnly
administrator session which never contains the Access JWT. Cloudflare sends
the one-time email code; no password hash is stored by NiceGUI, SQLite, KV,
backups, or Git.

The formal server-mode host receives an independent `SING_YIN_STORAGE_SECRET`
from its protected `.env`; local and practice modes may use their ignored,
managed runtime secret. The Worker requires `ADMIN_BEARER_TOKEN` and
`ADMIN_SESSION_SECRET` in Cloudflare secret storage. The Worker bearer must
match `SING_YIN_PUBLIC_ROSTER_VIEWER_ADMIN_TOKEN` in the protected origin
settings. A rotation updates both sides in one controlled maintenance window,
restarts the dedicated task, proves replacement HTTP 200 and retired HTTP 401,
and rolls both sides back if any step fails. Secret values never belong in Git,
documentation, screenshots, logs, or backups.

Same-host `/view#…` links are explicitly created, expiring and revocable. The
Windows host encrypts the minimum published-roster snapshot with AES-256-GCM;
Cloudflare KV stores ciphertext, nonce, and minimum week/creation/expiry
metadata, while the key stays in the URL fragment. Because KV is eventually
consistent, the application waits until the anonymous Viewer can read the exact
encrypted record before revealing the link or its key. If that check times out,
no key is issued and the Worker receives an exact content-key withdrawal
request. Localhost and private WARP are maintenance fallbacks, not additional
URLs to distribute. See
[`PUBLIC_ROSTER_VIEWER.md`](docs/PUBLIC_ROSTER_VIEWER.md) and
[`DEPLOYMENT_DECISION.md`](docs/DEPLOYMENT_DECISION.md) before changing the
access boundary.

## Repository archive

The repository includes source, documentation, tests, design assets, built-in
music, fictional SQLite evidence, privacy-safe logs, and browser screenshots.
Operational credentials, session secrets, dependency caches, `.next`,
`node_modules`, `__pycache__`, and temporary performance datasets are not
project source and are regenerated or supplied on the host.

`archive/MANIFEST.json` records file sizes and SHA-256 hashes. The archive
builder refuses a SQLite database that contains roster, leave, publication,
adjustment, or fairness rows.

## Verification

```powershell
python -X utf8 scripts\verify_update.py
```

This is the normal one-command entry point. Documentation, test-only, CI,
Worker, and deployable runtime changes receive different fail-closed profiles;
unknown paths are upgraded to full verification. Independent read-only checks
run concurrently. A formal runtime release still uses:

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python -X utf8 scripts\verify_release_candidate.py
```

The formal release candidate runs fail-closed checks for repository hygiene,
supply-chain security, Cloudflare Worker Deno contracts, the complete Python
suite, compilation, dependency integrity, desktop browser smoke, measured
runtime performance and memory stability, the fictional-data write/PDF and
restore pipeline, independent mobile adaptation, strict deployment readiness,
committed-without-backup recovery, and the isolated unified-Guest workflow.
The formal verifier has thirteen gates; the final matching fingerprint is
recorded only after the frozen-source rerun. Machine evidence remains separate
from the final operator/advisor acceptance checklist and from the live
host/Cloudflare switchover evidence.

## Co-creation

I am LI Chuangjie Jacky, Head Study Prefect for 2026–2027. I co-created this
system with Codex under the Study Prefect Systems & Stewardship Office identity.

**Creator profile:** 李創杰 · LI Chuangjie, Jacky · [Instagram @5662jacky](https://www.instagram.com/5662jacky/)

Codex and I are the only two co-creators of this NiceGUI rebuild and formal
release. The office name is our two-member project identity;
it does not represent additional developers, contractors, or a separate team.

I began with a practical scheduling need, but the work grew into a platform that
treats fairness, responsibility, recovery, and handover seriously. I hope future
Head Study Prefects inherit not merely a screen, but a process they can understand,
operate, explain, recover, and hand over—while making fairness visible and reducing
avoidable burden.

## License

The software is available under the [MIT License](LICENSE). The separate
[project notice](NOTICE.md) records that this formal release was completed only
by LI Chuangjie Jacky and Codex without restricting the MIT grant.
