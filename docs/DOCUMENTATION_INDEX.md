# 完整文件索引 / Documentation index

本索引是整套文件的入口與覆蓋契約，不取代各專題文件。它回答四件事：不同讀者應先看哪裡、哪一份文件對某項事實有最終解釋權、甚麼改動必須同步更新哪些文件，以及目前刻意不支援甚麼。

This index is the entry point and coverage contract for the documentation set. It does not duplicate each specialist guide. It identifies the right starting point for every reader, the authoritative document for each subject, the changes that trigger documentation updates, and the boundaries the product deliberately does not cross.

## 一分鐘選路 / One-minute routing

| Reader | Immediate question | Authoritative starting point |
|---|---|---|
| 訪客／同學／師兄弟 | 如何試用？資料會否保存？ | [`PUBLIC_ROSTER_VIEWER.md`](PUBLIC_ROSTER_VIEWER.md) |
| 首席導學風紀 | 今週如何安全生成、發布、分享及處理請假？ | [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) |
| 新任首席導學風紀 | 如何先練習、再接收正式資料與交接包？ | [`QUICKSTART.md`](QUICKSTART.md) → [`RELEASE_HANDOVER.md`](RELEASE_HANDOVER.md) |
| 顧問老師 | 哪些結果是自動證據，哪些仍要真人核對？ | [`ACCEPTANCE_EVIDENCE.md`](ACCEPTANCE_EVIDENCE.md) |
| IT／主機維護者 | 如何安裝、部署、備份、復原及安全維護？ | [`WINDOWS_DEDICATED_HOST_SETUP.md`](WINDOWS_DEDICATED_HOST_SETUP.md) |
| 遠端存取維護者 | Worker、Access、VPC origin 與 Viewer 如何配合？ | [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) |
| 開發者 | 模組、交易、資料、Guest adapter 與 UI 的責任在哪裡？ | [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md) |
| 發布者／審查者 | 這次改動需要哪一級驗證及甚麼發布證據？ | [`UPDATE_WORKFLOW.md`](UPDATE_WORKFLOW.md) → [`CODE_ACCEPTANCE_REVIEW.md`](CODE_ACCEPTANCE_REVIEW.md) |
| UI／UX 維護者 | 元件、token、排版、動效與無障礙規則是甚麼？ | [`../Professional_Design_System.md`](../Professional_Design_System.md) |

## 權威來源次序 / Source-of-truth precedence

同一主題出現差異時，不以較長或較新的段落自動勝出，依下列次序核對：

1. `packages/roster_policy` 的可執行政策及 `packages/roster_core` 的生成規則。
2. `nicegui_app/services/roster_workflow.py`、交易服務、migration 與正式資料契約。
3. `nicegui_app/access_context.py`、Guest adapter、Worker 驗證與下載邊界。
4. 鎖定測試、正式 release fingerprint 及機器產生的部署／驗證報告。
5. 架構、安全、操作、交接及部署專題文件。
6. `README.md`／`README-EN.md` 的導覽與摘要。
7. 歷史分支、封存、截圖及舊版本說明。

If prose conflicts with executable policy, transactional behavior, security checks, migrations, or current release evidence, the executable and verified contract wins and the prose must be corrected. Historical branches and screenshots never define current behavior.

## 文件目錄與責任 / Catalogue and ownership

### 日常操作與交接 / Operation and handover

| Document | Owns | Update when |
|---|---|---|
| [`QUICKSTART.md`](QUICKSTART.md) | 雙擊啟動、Practice Mode、埠號衝突、最快安全入口 | launcher、port selection、practice identity 或初次啟動改變 |
| [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) | 每週端到端操作、錯誤復原、名冊、發布、PDF、Viewer、請假、公平 | 任何可見工作流程、按鈕名稱、確認語句或恢復步驟改變 |
| [`ROSTER_POLICY_MODES.md`](ROSTER_POLICY_MODES.md) | 固定星期／每週靈活 Assist. in charge 模式、固定日維護及相容資料 | mode code、預設模式、輪換、固定星期、可當值日或請假替補規則改變 |
| [`RELEASE_HANDOVER.md`](RELEASE_HANDOVER.md) | 備份、隔離還原、正式部署、回退、下一任交接 | release gate、tag、backup、restore、deployment 或 rollback 改變 |
| [`ACCEPTANCE_EVIDENCE.md`](ACCEPTANCE_EVIDENCE.md) | 自動證據與首席導學風紀／顧問老師真人責任的逐項矩陣 | gate、acceptance criterion、證據位置或人手責任改變 |
| [`PROJECT_STATUS.md`](../PROJECT_STATUS.md) | 現行版本、已完成能力、發布證據、剩餘風險 | 候選建立、部署完成、風險開關或正式狀態改變 |

### 身份、資料與遠端存取 / Identity, data, and remote access

| Document | Owns | Update when |
|---|---|---|
| [`PUBLIC_ROSTER_VIEWER.md`](PUBLIC_ROSTER_VIEWER.md) | 單一網站、Guest、Admin、登出、唯讀 `/view#…` 使用方法 | 入口文案、session、分享、Viewer 或公開 URL 改變 |
| [`UNIFIED_GUEST_SECURITY_MODEL.md`](UNIFIED_GUEST_SECURITY_MODEL.md) | Admin／Guest parity、capability、記憶體 workspace、snapshot、下載與拒絕邊界 | Guest capability、retention、capacity、snapshot 或 download 改變 |
| [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) | 公開攻擊面、資料分類、secret、完整性、GitHub 治理、事件處理及剩餘風險 | identity、public route、storage、repository permission、security gate、incident 或 recovery contract 改變 |
| [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) | Access policy、Worker、VPC Service、secret、staging、smoke、rollback | Cloudflare binding、secret class、route、deployment 或 gateway contract 改變 |
| [`DEPLOYMENT_DECISION.md`](DEPLOYMENT_DECISION.md) | 本機、單一網站、私有維護與真正雲端遷移的取捨 | hosting assumption、data residency、availability 或 operating model 改變 |
| [`WINDOWS_SSH_MAINTENANCE.md`](WINDOWS_SSH_MAINTENANCE.md) | loopback-only、key-only SSH 維護通道 | SSH binding、authentication、firewall 或 maintenance account 改變 |

### 工程、設計與發布 / Engineering, design, and release

| Document | Owns | Update when |
|---|---|---|
| [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md) | runtime、module boundary、PageContext、transactions、concurrency、readiness、backup | architectural boundary、schema、service owner 或 failure path 改變 |
| [`CODE_ACCEPTANCE_REVIEW.md`](CODE_ACCEPTANCE_REVIEW.md) | 風險導向程式審查、10×／100× 判斷、供應鏈及故障情境 | risk model、dependency、capacity assumption 或 review gate 改變 |
| [`UPDATE_WORKFLOW.md`](UPDATE_WORKFLOW.md) | working-tree／staged／release 驗證選擇與安全上傳 | verifier profile、command、staging 或 release sequence 改變 |
| [`BRANCH_STRATEGY.md`](BRANCH_STRATEGY.md) | branch、tag、platform snapshot 及歷史保留規則 | branch purpose、release line 或 archive policy 改變 |
| [`AI_AGENT_GIT_GUIDE.md`](AI_AGENT_GIT_GUIDE.md) | Codex 與輔助 Agent 的工作樹、分支、提交、審查及禁止操作 | worktree allocation、agent branch、review ownership 或 GitHub protection 改變 |
| [`../Professional_Design_System.md`](../Professional_Design_System.md) | token、component、responsive、motion、SVG／Lottie、a11y 及驗證規則 | visual token、shared component、motion 或 accessibility contract 改變 |
| [`PRODUCT_RESEARCH_AND_IA_DECISIONS.md`](PRODUCT_RESEARCH_AND_IA_DECISIONS.md) | 產品研究來源、Adopt／Adapt／Reject 取捨及四區資訊架構 | public entrance、workbench、trust hub、documentation portal 或 reference decision 改變 |
| [`MUSIC_IMPORT_DECISION.md`](MUSIC_IMPORT_DECISION.md) | 本機音訊匯入的安全及技術決策 | importer、source allowlist、metadata 或 legal/operational boundary 改變 |
| [`MUSIC_PLAYLIST_CANDIDATES.md`](MUSIC_PLAYLIST_CANDIDATES.md) | 經審核但尚未必納入的音樂候選 | playlist review 或 catalogue decision 改變 |

### 專案參與與封存 / Project participation and archive

| Document | Owns |
|---|---|
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | 開發環境、修改原則、提交及測試責任 |
| [`../CODEX_PROMPTS.md`](../CODEX_PROMPTS.md) | 項目專用提示與 agent 邊界，不是 runtime 證據 |
| [`SKILLS_OVERVIEW.md`](SKILLS_OVERVIEW.md) | Sing Yin prompt／skill 使用總覽，不替代產品文件 |
| [`../archive/README.md`](../archive/README.md) | 可公開虛構資料、空內容日誌及測試證據的封存規則 |
| [`../NOTICE.md`](../NOTICE.md) | 第三方歸屬、素材與通知 |
| [`../LICENSE`](../LICENSE) | 程式授權條款 |

## 使用模式、資料生命週期與成本邊界 / Mode, lifecycle, and cost boundary

| Surface | Identity | Data source | Retention | Allowed output | Forbidden or bounded work |
|---|---|---|---|---|---|
| Public entrance | Anonymous | Static identity and devotional seed only | No operator state | Navigation to Guest/Admin/share | No official roster query or identity elevation |
| Guest | Worker-issued Guest principal | Fixed fictional in-memory adapter | Session/tab/boot bounded | One-shot `DEMO` PDF/JSON | AI, upload, import, permanent write, backup/restore, share publication, external delivery and costly storage |
| Admin | Access-verified Admin principal | Official SQLite and verified local files | Controlled operational retention | Official PDF/JSON, backups, Viewer publication | No bypass of transaction, version, idempotency, audit, confirmation or backup obligations |
| Viewer | Possession of complete `/view#…` link | One encrypted published snapshot | Expiring/revocable KV ciphertext | Browser read-only roster | No edit, login, listing, identity upgrade or key recovery |
| Practice | Local practice identity | Separate fictional SQLite | Reset by explicit practice reset | Clearly non-official PDF/JSON | No official paths, backups, shares or identities |

## 設定分類 / Configuration classes

| Class | Examples | Storage rule | Primary reference |
|---|---|---|---|
| Public repository defaults | host mode defaults, policy version, asset versions | Version controlled and tested | `.env.example`, `nicegui_app.config` |
| Protected host configuration | official port, storage secret, data/backup/log paths | Host `.env`; never committed, copied into docs, or placed in screenshots | [`WINDOWS_DEDICATED_HOST_SETUP.md`](WINDOWS_DEDICATED_HOST_SETUP.md) |
| Cloudflare public identifiers | Worker name, Access audience identifier, KV/VPC binding identifiers | Versioned only where they are explicitly non-secret | [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) |
| Cloudflare and integration secrets | session, principal, bearer, API and private maintenance keys | Secret store or protected host only; rotate on exposure | [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) |
| Browser/session preference | language, appearance, music, sound | Admin user store or bounded Guest memory, never the roster ledger | [`UNIFIED_GUEST_SECURITY_MODEL.md`](UNIFIED_GUEST_SECURITY_MODEL.md) |
| Operator data | names, leave, rosters, fairness, PDFs, backups, logs | Controlled origin only; excluded from ordinary Git and public cloud sync | [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md) |

Never copy real secret values into this index. `.env.example` documents names and safe placeholders; the protected environment remains the only source for live values.

## 多用戶、可靠性與復原覆蓋 / Concurrency, reliability, and recovery coverage

The documentation set must continue to explain and test all of these boundaries:

- conditional publication ownership prevents two tabs from posting the same fairness effect;
- optimistic versions reject stale edits and late adjustments;
- command receipts and idempotency prevent duplicate effects after retry or reconnect;
- transaction boundaries keep roster, ledger, audit, share outbox, and backup obligations coherent;
- bounded Guest admission rejects excess new sessions without evicting active work;
- every Guest tab has isolated fictional state and cannot replay another tab/session/boot snapshot;
- maintenance fencing prevents writes during controlled backup, restore, migration, and release switching;
- `/healthz` proves liveness and database access, while `/readyz` additionally proves write readiness, recovery state, maintenance state, and backup obligations;
- a committed write followed by backup failure is reported as committed-with-obligation, never falsely rolled back or retried blindly;
- restore requires manifest, checksum, SQLite integrity, schema, fairness reconciliation, audit, and isolated restore evidence.

The detailed implementation belongs in [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md); the operator response belongs in [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) and [`RELEASE_HANDOVER.md`](RELEASE_HANDOVER.md).

## 驗證層級 / Verification ladder

| Situation | Command or evidence | Meaning |
|---|---|---|
| Before editing | `python -X utf8 scripts/verify_update.py --plan` | Determines the risk profile without claiming quality |
| Focused change | Targeted pytest/Deno/compile/browser check | Fast evidence for the touched behavior |
| Before push | `python -X utf8 scripts/verify_update.py --staged` | Verifies the exact intended staged set |
| Formal release | `python -X utf8 scripts/verify_update.py --release` | Runs the complete fingerprint-bound release gate once |
| Windows rollout | `scripts/deploy_windows_release.ps1` report, backup, isolated restore, health/readiness | Proves the protected origin moved safely or rolled back |
| Worker rollout | `scripts/deploy_cloudflare_worker.ps1` zero-traffic staging, version smoke, promotion | Proves the exact Worker version reached canonical traffic |
| Human acceptance | [`ACCEPTANCE_EVIDENCE.md`](ACCEPTANCE_EVIDENCE.md) | Confirms real identity, device, workflow, copy, PDF, and advisor expectations |

HTTP 200 alone is not UI evidence; a passing unit suite alone is not release evidence; automated gates do not replace supervised human acceptance.

## 故障定位路由 / Troubleshooting route

| Symptom | First safe check | Do not do |
|---|---|---|
| Website cannot open | Canonical URL, then Worker `/healthz`; maintainer checks origin `/healthz` and `/readyz` | Do not expose the origin or start a Quick Tunnel |
| `OP-...` appears | Record the reference and follow the recovery action; maintainer uses `inspect_support_log.py` locally | Do not upload the full log or repeat a possibly committed write |
| “資料已儲存，但備份未完成” | Reload, verify the saved result, then create a verified snapshot from Settings | Do not repeat the original command |
| Guest state disappears | Confirm the same tab/session is still active; restart the fictional exercise if expired or revoked | Do not expect permanent Guest storage |
| Viewer link fails | Check expiry/revocation and whether the complete fragment-bearing link was copied | Do not try to recover a lost fragment key from the server |
| Restore option is disabled | Create or select a snapshot that passes manifest/checksum/integrity/schema checks | Do not rename or manually place an unverified SQLite file |
| Port already in use | Use the official launcher and its discovered localhost URL | Do not kill an unknown process or hard-code a second production port |

## 已知限制與非目標 / Known limits and non-goals

- This is a single controlled origin for a school Study Prefect workflow, not a general SaaS workforce platform.
- SQLite remains appropriate for the measured operating scale; multi-origin active/active operation is not claimed.
- The system records scheduled allocation, not attendance, completed service, performance evaluation, payroll, or certification.
- Guest parity means the same product experience backed by fictional memory state; it does not grant costly or persistent capabilities.
- The optional AI mapping assistant is not required for import and never receives names, full rows, files, or final results.
- Public Viewer links are read-only bearer artifacts. They are not accounts and do not become private merely because the URL is hard to guess.
- The repository does not promise automatic cloud migration, offline-first synchronization, a mobile native app, email/SMS dispatch, or background message delivery.
- Design richness is bounded by accessibility, reduced motion, load cost, and task clarity; visual effects are not acceptance criteria by themselves.

## 文件完整性維護 / Documentation maintenance checklist

When a change is ready for review:

1. Update the authoritative specialist document first.
2. Update both `README.md` and `README-EN.md` when the entry path, public behavior, release baseline, or major capability changes.
3. Update `PROJECT_STATUS.md` for candidate/live state and residual risk.
4. Update `RELEASE_HANDOVER.md` and `ACCEPTANCE_EVIDENCE.md` for release, backup, rollback, or human checks.
5. Update `Professional_Design_System.md` for shared visual, responsive, motion, or accessibility rules.
6. Add every new `docs/*.md` file to this catalogue; the documentation test fails when a Markdown document is omitted.
7. Run link/contract tests and the risk-selected verification profile.
8. Keep historical evidence labelled historical; never silently rewrite an old release as current.

## 參考方法與批判性取捨 / Reference patterns and critical choices

The structure was informed by mature open-source documentation without copying product claims or adopting unsuitable architecture:

- [LibreBooking](https://github.com/LibreBooking/librebooking) demonstrates a navigable table of contents spanning features, deployment, developer documentation, configuration, support, contribution, and roadmap. We adopt its separation of concerns, not its PHP/MySQL deployment model.
- [ToolJet](https://github.com/ToolJet/ToolJet) separates quick start, self-hosting choices, branch model, support, and contribution. We use the reader routing pattern but keep one controlled Windows origin rather than presenting unsupported deployment providers.
- [Staffjoy Suite](https://github.com/Staffjoy/suite) documents environment variables, required services, production topology, health checks, and limitations. We adopt explicit operational dependencies and limitations, but not its legacy multi-service architecture.
- [Ed-Fi OneRoster](https://github.com/Ed-Fi-Alliance-OSS/edfi-oneroster) maps implemented coverage and links each technical concern to a focused guide. We adopt coverage ownership, not the OneRoster API or its data model.
- [ShiftWizard](https://github.com/NaphtaliO/ShiftWizard) records use cases, data flow, sequence, implementation, challenges, and future work. We retain those ideas in focused architecture/status documents instead of turning the main README into an unstructured project report.
- [Frappe](https://github.com/frappe/frappe) and [Twenty](https://github.com/twentyhq/twenty) keep product purpose, production/development entry, stack, learning, security, and contribution paths discoverable. We adopt discoverability while avoiding marketing sections unrelated to school operations.

Completeness here means every operational promise has an owner, boundary, verification path, and recovery route. It does not mean repeating the same explanation in every file.
