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
| 任何讀者 | 現在正式運行甚麼版本、資料庫及 Worker？ | [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) |
| IT／主機維護者 | 如何安裝、部署及安全維護正式主機？ | [`WINDOWS_DEDICATED_HOST_SETUP.md`](WINDOWS_DEDICATED_HOST_SETUP.md) |
| 災難復原保管人 | 整部主機損毀後，如何由加密離機副本復原？ | [`OFFSITE_DISASTER_RECOVERY.md`](OFFSITE_DISASTER_RECOVERY.md) |
| 遠端存取維護者 | Worker、Access、VPC origin 與 Viewer 如何配合？ | [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) |
| 開發者 | 一項改動應放在哪個模組，依賴方向是甚麼？ | [`ARCHITECTURE_OVERVIEW.md`](ARCHITECTURE_OVERVIEW.md) → [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md) |
| 發布者／審查者 | 這次改動需要哪一級驗證及甚麼發布證據？ | [`UPDATE_WORKFLOW.md`](UPDATE_WORKFLOW.md) → [`CODE_ACCEPTANCE_REVIEW.md`](CODE_ACCEPTANCE_REVIEW.md) |
| 文件維護者 | 文件如何分類、同步、迭代及淘汰？ | [`DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md) |
| UI／UX 維護者 | 元件、token、排版、動效與無障礙規則是甚麼？ | [`../Professional_Design_System.md`](../Professional_Design_System.md) → [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md) |

## 權威來源次序 / Source-of-truth precedence

同一主題出現差異時，不以較長或較新的段落自動勝出，依下列次序核對：

1. `packages/roster_policy` 的可執行政策及 `packages/roster_core` 的生成規則。
2. `nicegui_app/services/roster_workflow.py`、交易服務、migration 與正式資料契約。
3. `nicegui_app/access_context.py`、Guest adapter、Worker 驗證與下載邊界。
4. 鎖定測試、正式 release fingerprint 及機器產生的部署／驗證報告。
5. 由上述證據更新的 [`status/current-release.json`](status/current-release.json) 與生成的 [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md)。
6. 架構、安全、操作、交接及部署專題文件。
7. `README.md`／`README-EN.md` 的導覽與摘要。
8. 歷史分支、封存、截圖及舊版本說明。

If prose conflicts with executable policy, transactional behavior, security checks, migrations, or current release evidence, the executable and verified contract wins and the prose must be corrected. Historical branches and screenshots never define current behavior.

## 文件目錄與責任 / Catalogue and ownership

### 日常操作與交接 / Operation and handover

| Document | Owns | Update when |
|---|---|---|
| [`QUICKSTART.md`](QUICKSTART.md) | 雙擊啟動、Practice Mode、埠號衝突、最快安全入口 | launcher、port selection、practice identity 或初次啟動改變 |
| [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md) | 每週端到端操作、錯誤復原、名冊、發布、PDF、Viewer、請假、公平 | 任何可見工作流程、按鈕名稱、確認語句或恢復步驟改變 |
| [`ROSTER_POLICY_MODES.md`](ROSTER_POLICY_MODES.md) | 固定星期／每週靈活 Assist. in charge 模式、固定日維護及相容資料 | mode code、預設模式、輪換、固定星期、可當值日或請假替補規則改變 |
| [`ROSTER_DRAFT_EDITING.md`](ROSTER_DRAFT_EDITING.md) | 試算表式草稿編輯、四種格子狀態、每週全天停開、整批保存及衝突復原 | 草稿矩陣、格子狀態、停開覆蓋、批次 patch、PDF／公開呈現或衝突流程改變 |
| [`MOBILE_OPERATIONS_ACCEPTANCE.md`](MOBILE_OPERATIONS_ACCEPTANCE.md) | 手機快速設定、生成、單日草稿、鍵盤／safe-area及實體 Android 驗收 | 手機 drawer、bottom navigation、草稿 bottom sheet、裝置矩陣或手機真人流程改變 |
| [`RELEASE_HANDOVER.md`](RELEASE_HANDOVER.md) | 本機已驗證快照、受控還原、正式部署、相容回退及下一任交接 | release gate、tag、managed restore、deployment 或 rollback 改變 |
| [`OFFSITE_DISASTER_RECOVERY.md`](OFFSITE_DISASTER_RECOVERY.md) | 外置 BitLocker 目標、RPO／RTO、離機保留、密鑰責任、host-loss 及 replacement-location drill | off-site target、export receipt、retention、custody、disaster restore 或 drill contract 改變 |
| [`ACCEPTANCE_EVIDENCE.md`](ACCEPTANCE_EVIDENCE.md) | 自動證據與首席導學風紀／顧問老師真人責任的逐項矩陣 | gate、acceptance criterion、證據位置或人手責任改變 |
| [`status/CURRENT_STATUS.md`](status/CURRENT_STATUS.md) | 由單一 JSON 生成的精確 live／migration／Worker／rollback／acceptance 狀態 | 觀察到部署、復原或真人驗收狀態改變；先更新 JSON，再執行 `project_governance.py --write` |
| [`PROJECT_STATUS.md`](../PROJECT_STATUS.md) | 已完成能力、交付歷史、長期風險與里程碑 | 能力完成、風險開關或歷史交付記錄改變；不得手動複製目前 release identifiers |

### 身份、資料與遠端存取 / Identity, data, and remote access

| Document | Owns | Update when |
|---|---|---|
| [`PUBLIC_ROSTER_VIEWER.md`](PUBLIC_ROSTER_VIEWER.md) | 單一網站、Guest、Admin、登出、唯讀 `/view#…` 使用方法 | 入口文案、session、分享、Viewer 或公開 URL 改變 |
| [`UNIFIED_GUEST_SECURITY_MODEL.md`](UNIFIED_GUEST_SECURITY_MODEL.md) | Admin／Guest parity、capability、記憶體 workspace、snapshot、下載與拒絕邊界 | Guest capability、retention、capacity、snapshot 或 download 改變 |
| [`SECURITY_AND_PRIVACY.md`](SECURITY_AND_PRIVACY.md) | 公開攻擊面、資料分類、secret、完整性、GitHub 治理、事件處理及剩餘風險 | identity、public route、storage、repository permission、security gate、incident 或 recovery contract 改變 |
| [`SUPPORT_AND_INCIDENT_WORKFLOW.md`](SUPPORT_AND_INCIDENT_WORKFLOW.md) | Admin／Guest／Public／Viewer 問題報告、事件包、清理、檢視與安全傳送程序 | support route、incident schema、attachment、retention、inspection 或 escalation 改變 |
| [`THREAT_MODEL_SUPPORT_INBOX.md`](THREAT_MODEL_SUPPORT_INBOX.md) | 本機支援收件匣的威脅、拒絕邊界、配額、redaction、完整性與隔離假設 | support storage、input validation、quota、redaction 或 trust boundary 改變 |
| [`CLOUDFLARE_REMOTE_ACCESS_SETUP.md`](CLOUDFLARE_REMOTE_ACCESS_SETUP.md) | Access policy、Worker、VPC Service、secret、staging、smoke、rollback | Cloudflare binding、secret class、route、deployment 或 gateway contract 改變 |
| [`DEPLOYMENT_DECISION.md`](DEPLOYMENT_DECISION.md) | 本機、單一網站、私有維護與真正雲端遷移的取捨 | hosting assumption、data residency、availability 或 operating model 改變 |
| [`WINDOWS_SSH_MAINTENANCE.md`](WINDOWS_SSH_MAINTENANCE.md) | loopback-only、key-only SSH 維護通道 | SSH binding、authentication、firewall 或 maintenance account 改變 |

### 工程、設計與發布 / Engineering, design, and release

| Document | Owns | Update when |
|---|---|---|
| [`ARCHITECTURE_OVERVIEW.md`](ARCHITECTURE_OVERVIEW.md) | 十分鐘模組地圖、主要 seam、依賴方向及改動放置規則 | module owner、interface、dependency direction 或 composition 改變 |
| [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md) | runtime、PageContext、transactions、concurrency、readiness、backup 的完整細節 | schema、service implementation 或 failure path 改變 |
| [`CODE_ACCEPTANCE_REVIEW.md`](CODE_ACCEPTANCE_REVIEW.md) | 風險導向程式審查、10×／100× 判斷、供應鏈及故障情境 | risk model、dependency、capacity assumption 或 review gate 改變 |
| [`UPDATE_WORKFLOW.md`](UPDATE_WORKFLOW.md) | working-tree／staged／release 驗證選擇與安全上傳 | verifier profile、command、staging 或 release sequence 改變 |
| [`BRANCH_STRATEGY.md`](BRANCH_STRATEGY.md) | branch、tag、platform snapshot 及歷史保留規則 | branch purpose、release line 或 archive policy 改變 |
| [`AI_AGENT_GIT_GUIDE.md`](AI_AGENT_GIT_GUIDE.md) | Codex 與輔助 Agent 的工作樹、分支、提交、審查及禁止操作 | worktree allocation、agent branch、review ownership 或 GitHub protection 改變 |
| [`DOCUMENTATION_SYSTEM.md`](DOCUMENTATION_SYSTEM.md) | 文件生命週期、單一狀態來源、topic owner、ADR 及驗證規則 | 文件分類、status generator、owner 或治理流程改變 |
| [`ITERATION_REGISTER.md`](ITERATION_REGISTER.md) | 以 L1／L2／L3 排序、連接活躍風險、owner 及關閉證據的改善佇列 | 項目進入、優先級／狀態改變、風險連結改變或完成後移出 |
| [`../Professional_Design_System.md`](../Professional_Design_System.md) | token、component、responsive、motion、SVG／Lottie、a11y 及驗證規則 | visual token、shared component、motion 或 accessibility contract 改變 |
| [`FRONTEND_ARCHITECTURE.md`](FRONTEND_ARCHITECTURE.md) | 前端 composition、CSS layer、route family、responsive runtime、依賴及遷移責任 | shell／layer ownership、composition order、route hierarchy、viewport runtime 或 frontend dependency 改變 |
| [`design/ATMOSPHERE_ASSET_MANIFEST.md`](design/ATMOSPHERE_ASSET_MANIFEST.md) | AI 氣氛資產提示詞、用途、尺寸、大小、SHA-256、裁切、遮罩、人工檢視及禁用位置 | atmosphere slot、圖片、生成工具、theme pair、hash 或 placement boundary 改變 |
| [`CONTENT_DESIGN_AUDIT.md`](CONTENT_DESIGN_AUDIT.md) | 可見文案的用途分類、保留／蒸餾決定、頁面主行動與後果說明 | page hierarchy、visible copy、progressive disclosure、support copy 或 content ownership 改變 |
| [`PRODUCT_RESEARCH_AND_IA_DECISIONS.md`](PRODUCT_RESEARCH_AND_IA_DECISIONS.md) | 產品研究來源、Adopt／Adapt／Reject 取捨及四區資訊架構 | public entrance、workbench、trust hub、documentation portal 或 reference decision 改變 |
| [`VISUAL_INTERACTION_AUDIT_RC31.md`](VISUAL_INTERACTION_AUDIT_RC31.md) | rc31 外觀控制缺陷、保留邊界、驗收矩陣及反例 | rc31 theme control scope、interaction contract 或 acceptance matrix 改變 |
| [`audits/SEMANTIC_ICON_ACTION_MOTION_2026-07-30.md`](audits/SEMANTIC_ICON_ACTION_MOTION_2026-07-30.md) | 語意圖標來源分母、21 個必需控制、五項旋轉白名單、提示音預設及渲染驗證 | icon role／category／motion mode、lifecycle feedback、rotation allowlist、sound default 或 motion verifier 改變 |
| [`audits/ATMOSPHERE_MOTION_ACCEPTANCE_2026-07-31.md`](audits/ATMOSPHERE_MOTION_ACCEPTANCE_2026-07-31.md) | 全路由氣氛、每日聖言、語意旋轉、觸覺開關、裝置矩陣及部署前後證據 | 本輪資產、視覺、互動、browser gate、release 或 production evidence 改變 |
| [`audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md`](audits/MIXED_GATEWAY_LOAD_ACCEPTANCE_2026-08-01.md) | 實際 Worker source 在 local workerd 下的 Guest／Admin／WebSocket／下載／備份／outbox／Viewer 混合負載、停止條件及證據限制 | Admin read／write、Guest isolation／capacity、Gateway WebSocket、download registry、backup／outbox concurrency、Viewer publish／decrypt 或本機負載基線改變 |
| [`audits/PRODUCT_MATURITY_RADAR_2026-08-02_PHASE_5.md`](audits/PRODUCT_MATURITY_RADAR_2026-08-02_PHASE_5.md) | rc46 候選的發布完整性、驗證前後 source binding、正式 gate 及仍未部署的邊界 | release report schema、browser evidence destination、source fingerprint／clean-tree contract、ITR-002 狀態或正式發布真相改變 |
| [`audits/RC54_INTEGRATED_REVIEW_AND_RELEASE_LEDGER_2026-08-09.md`](audits/RC54_INTEGRATED_REVIEW_AND_RELEASE_LEDGER_2026-08-09.md) | rc54 平行工作整合、R1–R7 現況裁決、typed edit sessions、原子名單批次及發布完成條件 | 本候選 source boundary、整合提交、審計裁決、核心交易、驗證結果或部署證據改變 |
| [`plans/WHOLE_SITE_WAITING_EXPERIENCE_PLAN.md`](plans/WHOLE_SITE_WAITING_EXPERIENCE_PLAN.md) | Admin／Guest 入口、誠實進度、slow-state、按鈕圖標分母及全站等待狀態所有權 | entry lifecycle、progress mode、loading token、button inventory 或 waiting-state gate 改變 |
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
- host-loss recovery requires a separately stored BitLocker external copy, path-free receipt, immutable release identity, and a drill that reads only that copied bundle.
- mixed gateway capacity uses the actual Worker source under local workerd, browser WebSockets and disposable fictional SQLite; the dated report must state session count, latency context, isolation, fairness, backup／outbox result, memory stop condition and the fact that it is not Cloudflare-edge evidence.

The detailed implementation belongs in [`NICEGUI_ARCHITECTURE.md`](NICEGUI_ARCHITECTURE.md); ordinary operator response belongs in [`OPERATOR_GUIDE.md`](OPERATOR_GUIDE.md), release and compatible rollback in [`RELEASE_HANDOVER.md`](RELEASE_HANDOVER.md), and complete host-loss recovery in [`OFFSITE_DISASTER_RECOVERY.md`](OFFSITE_DISASTER_RECOVERY.md).

## 驗證層級 / Verification ladder

| Situation | Command or evidence | Meaning |
|---|---|---|
| Before editing | `python -X utf8 scripts/verify_update.py --plan` | Determines the risk profile without claiming quality |
| Focused change | Targeted pytest/Deno/compile/browser check | Fast evidence for the touched behavior |
| Mixed gateway capacity | `python -X utf8 scripts\verify_mixed_gateway_load.py` when Guest admission, Worker service binding／WebSocket, download, backup or outbox concurrency changes | Proves a bounded local real-Worker path with fictional data; does not replace edge smoke, formal release or human acceptance |
| Before push | `python -X utf8 scripts/verify_update.py --staged` | Verifies the exact intended staged set |
| Formal release | `python -X utf8 scripts/verify_update.py --release` | Runs the complete fingerprint-bound release gate once |
| Windows rollout | `scripts/deploy_windows_release.ps1` report, backup, isolated restore, health/readiness | Proves the protected origin moved safely or rolled back |
| Off-site recovery | `scripts/export_offsite_recovery.ps1` plus a replacement-location `drill` report | Proves a real encrypted external copy can restore without the original host; source-only tests do not satisfy this row |
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
2. Use [`documentation-manifest.json`](documentation-manifest.json) to confirm lifecycle class, topic owner and update triggers.
3. For observed live／migration／Worker／rollback／acceptance changes, update `status/current-release.json` and run `python -X utf8 scripts/project_governance.py --write`; never hand-copy mutable identifiers.
4. Update both `README.md` and `README-EN.md` only when reader routing, public behavior or a major capability changes.
5. Update `PROJECT_STATUS.md` for capability/history and residual risk; update `RELEASE_HANDOVER.md`／`ACCEPTANCE_EVIDENCE.md` for procedures and evidence.
6. Update `Professional_Design_System.md` for shared visual, responsive, motion or accessibility rules; update `FRONTEND_ARCHITECTURE.md` for composition, layer ownership, route-family or frontend-dependency changes.
7. Classify every new Markdown file or collection and add its authoritative route here when it is a first-class guide.
8. Run `python -X utf8 scripts/project_governance.py --check` and the risk-selected verification profile.
9. Keep historical evidence labelled historical; never silently rewrite an old release as current.

## 參考方法與批判性取捨 / Reference patterns and critical choices

The structure was informed by mature open-source documentation without copying product claims or adopting unsuitable architecture:

- [LibreBooking](https://github.com/LibreBooking/librebooking) demonstrates a navigable table of contents spanning features, deployment, developer documentation, configuration, support, contribution, and roadmap. We adopt its separation of concerns, not its PHP/MySQL deployment model.
- [ToolJet](https://github.com/ToolJet/ToolJet) separates quick start, self-hosting choices, branch model, support, and contribution. We use the reader routing pattern but keep one controlled Windows origin rather than presenting unsupported deployment providers.
- [Staffjoy Suite](https://github.com/Staffjoy/suite) documents environment variables, required services, production topology, health checks, and limitations. We adopt explicit operational dependencies and limitations, but not its legacy multi-service architecture.
- [Ed-Fi OneRoster](https://github.com/Ed-Fi-Alliance-OSS/edfi-oneroster) maps implemented coverage and links each technical concern to a focused guide. We adopt coverage ownership, not the OneRoster API or its data model.
- [ShiftWizard](https://github.com/NaphtaliO/ShiftWizard) records use cases, data flow, sequence, implementation, challenges, and future work. We retain those ideas in focused architecture/status documents instead of turning the main README into an unstructured project report.
- [Frappe](https://github.com/frappe/frappe) and [Twenty](https://github.com/twentyhq/twenty) keep product purpose, production/development entry, stack, learning, security, and contribution paths discoverable. We adopt discoverability while avoiding marketing sections unrelated to school operations.

Completeness here means every operational promise has an owner, boundary, verification path, and recovery route. It does not mean repeating the same explanation in every file.
