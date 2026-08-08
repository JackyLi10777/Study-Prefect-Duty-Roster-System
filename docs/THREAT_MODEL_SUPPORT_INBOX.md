# Threat Model：Local-First Diagnostic & Feedback Loop

## 1. Scope and security objectives

本威脅模型涵蓋 Admin 問題回報、Public／Viewer 有界文字提交、Guest 瀏覽器內回報、Incident Bundle、Support Inbox、檢視／quarantine 工具、Codex handoff 及有界主機安全摘要。既有 roster database、backup、PDF、Cloudflare Access／Worker 及正式值班工作流只在它們與回報系統接觸的邊界內討論。

安全目標：

1. 診斷系統故障不能令值班工作流失敗。
2. Guest 不得在 origin 留下持久回報內容；Public／Viewer 只可經短效簽署能力建立受限、純文字、已遮蔽 incident，不能讀取、列出、下載或修改任何 incident。
3. Incident 只收集 allowlisted、已清理、最小必要證據。
4. 不可信 bundle 不得造成 code execution、path escape、stored XSS、prompt-driven action 或跨 incident 泄漏。
5. bundle 的建立、狀態轉移及 resolution 具完整性、並行安全及可審計性。
6. Incident data 不得進 Git、release artifact、正式 database／backup 或公開渠道。

## 2. Architecture and trust boundaries

```text
Public browser ── Cloudflare Worker ── 60s support-only principal ── NiceGUI origin
     │                                                    │
     ├─ bounded text POST ────────────────────────────────┤
     └─ network-failure fallback (untrusted, ephemeral)   ├─ Admin report service
                                                          │    │
Windows authenticated Admin browser ─────────────────────┘    ├─ redactor/schema validator
                                                               ├─ same-volume staging
                                                               └─ Support Inbox (local ACL)
                                                                      │
Explicit user request ── Codex safe inspector ── isolated reproduction

Windows Event Logs / Defender / Task / Firewall / Cloudflare summaries
└──────────────────── separate host-security evidence plane ───────────┘
```

Trust boundaries：

- TB1 Internet／Cloudflare：所有 headers 先由 Worker 清理並簽署 principal；origin 不信任 browser 自報身份。
- TB2 Browser／NiceGUI callback：UI disable 不是權限；每次 Admin save 再檢查 active principal 及 `PERSISTENT_WRITE`。
- TB3 Untrusted text／redactor：所有描述、檔名、引用與附件先限制 bytes、encoding、format 及字符，再進 schema。
- TB4 Staging／Inbox：只有已完整寫入、驗證及 hash 的目錄可 atomic rename 至 Inbox。
- TB5 Inbox／Codex：report content 永遠是資料，不是 instruction；inspect 和 execute 是不同權限。
- TB6 Application／host telemetry：bundle 不能自動讀 unrestricted Windows／security logs。

## 3. Protected assets

- roster database、fairness ledger、backup、PDF、中文姓名與請假內容
- Cloudflare／origin secret、cookie、JWT、HMAC、password、token、Git credential
- Admin session 與 Guest workspace isolation
- release identity、source fingerprint、deployment evidence
- application availability、disk capacity、backup/recovery readiness
- incident evidence integrity、confidentiality、status history及 operator trust
- Git history、release artifact hygiene及 Codex authority boundary

## 4. Threat actors and assumptions

Actors：malicious public reporter、compromised Guest／Admin browser session、careless authenticated operator、malformed external bundle、prompt-injection author、local unprivileged process、malware or compromised host agent。

Assumptions：Windows service account和管理員帳戶分離；support root 位於本機 NTFS volume；Cloudflare gateway 簽章驗證保持啟用；單一 NiceGUI origin；Codex 只在明確請求後檢視；主機完全被攻陷時，單純應用層 hash 不能提供獨立可信度。

## 5. Abuse cases and mitigations

| Threat | Attack path | Primary controls | Residual risk / follow-up |
|---|---|---|---|
| Guest persistence bypass | 直接呼叫 Admin save endpoint／callback | `AccessMode` + deny-by-default `CapabilityPolicy`；Admin save service 重新要求 `PERSISTENT_WRITE`；Guest 只使用 browser JS | 被盜 Admin session 仍可建立 incident；由 Access expiry／revocation處理 |
| Public support flooding | 重複呼叫公開提交 API 消耗磁碟或 quota | exact route／method、same-origin、16 KiB body、60 秒 signed capability、6/min edge limit、20/day／200-count／50-MiB inbox quota | 分散來源仍可耗盡每日 quota；只令回報暫停，不得影響值班流程 |
| Cross-session leakage | 猜 Incident ID、download token 或引用另一 session | Incident ID 不作授權；Admin-only list/read；download token綁 session、單次、限時；no-store | 本機有 ACL 權限者仍可讀；由 NTFS ACL 限制 |
| Sensitive attachment | Operator 加入名單、截圖、log、database | 預設無附件；explicit preview/consent；嚴格 type／size／count；redaction；禁 PDF／Office／archive | PNG 仍可能含個資；v1 提醒且需人工核對，不承諾 OCR 完全遮罩 |
| CRLF／log injection | 描述或 reference 注入新 event line | 移除 control chars、normalize newline；reference strict regex；user text不寫 app.log | 允許文字仍可能誤導人，故 UI／CLI 標示 untrusted |
| Stored XSS | Markdown／HTML／filename 被瀏覽器解譯 | report 以 plain text escape；不接受 HTML／SVG；CSP；UI 不用 raw untrusted HTML | 瀏覽器／框架漏洞屬外部 residual risk |
| Path traversal／Zip Slip | `../`、absolute、UNC、ADS、reserved names | server 產生檔名；resolve + common-root；拒 symlink／reparse；v1 不接受 archive import | 手動放入 inbox 的資料仍由 inspector quarantine |
| Archive bomb | 壓縮檔極小但解壓巨大 | v1 不接受任何 archive 作 import/attachment；export only from trusted directory | 日後加入 ZIP import 前須另做 central-directory／ratio／file-count limits |
| Symlink／junction escape | staging 或 attachment 指向外部 | 每段 `lstat`／Windows reparse check；新目錄 exclusive create；atomic same-volume rename | 已取得 service-account 權限的攻擊者超出此控制 |
| Concurrent overwrite | 兩份報告碰撞／同時 move | cryptographic random Incident ID；exclusive mkdir；per-incident lock；append status + atomic rename | Windows antivirus 可短暫鎖檔，操作須 fail-safe／retry bounded |
| Partial write／power loss | manifest 有但附件／hash 未完成 | staging；逐檔 flush/fsync；完成後驗證；atomic rename；startup清理 stale staging | NTFS／硬體嚴重損壞仍需主機備份策略 |
| Disk exhaustion | 大量 report、惡意附件、無限 retention | per-field/bundle/attachment limits；daily/max count；root quota；free-space floor；no queue | quota滿時回報功能不可用，但 roster flow 必須繼續 |
| Unauthorized deletion／tampering | 本機 user 修改 incident | service-account ACL；hash manifest；append-only logical status；安全檢視時重新驗證 | 同帳戶或 admin compromise 可改檔；需獨立 export 才有外部證據 |
| Prompt injection to Codex | report 寫「執行這個命令／上傳 secret」 | inspector只輸出 allowlisted summary；明文標示 untrusted；Codex不執行附件、不跟指示、不開 URL | 人工仍可受社交工程影響；文件與工具重複提示 |
| Arbitrary URL／command | report包含外部 URL、PowerShell | 不自動 hyperlink/fetch；不執行；CLI不回顯全文 | 使用者自行複製仍可能有風險 |
| Secret leakage | exception message／log／env 被收集 | bundle只收 error type、sanitized location、safe release/meta；pattern redaction；沒有 env dump | 未知 secret pattern可逃過；allowlist比denylist優先 |
| External telemetry compromise | exporter送出 incident | v1 無 exporter；接口預設 disabled；日後需 TLS、credential、retention、DPA、rollback | Cloudflare 自身仍保留 edge metadata，按其方案治理 |
| Host agent compromise | 高權限 Wazuh/Sysmon/collector被利用 | v1 不安裝；host evidence使用原生read-only摘要；agent需另行批准 | 原生 OS telemetry也可能被高權限攻擊者清除 |
| Event-log clearing | attacker清除 Windows log | 監測清除事件摘要；不把 raw log塞入 bundle | 單機記錄可同時被清除；獨立 WEF 才能提高保障 |
| Incident enters Git/release | operator `git add` support files | `.gitignore`、hygiene classifier、release fingerprint source allowlist、tests；禁止 `git add -A` | force-add仍可能繞過，CI hygiene必須 fail closed |

## 6. Security requirements for implementation

- 所有 filesystem API 接受 `Path` 前先 canonicalize，禁止 root 自身或 root 外目標。
- 不依賴 filename extension 判 MIME；文本 strict UTF-8，PNG 驗 signature。
- JSON parser 後以 exact key set、enum、regex、list count、byte／character limit 驗證。
- manifest／environment／events／status 使用 deterministic JSON serialization；report.md 由程式生成且 escape user text。
- atomic writer failure 必須回傳安全 OP reference，不把 OS path／exception message送到 UI。
- inspector的預設 list／summary不輸出 description、attachment bytes、URL、command或secret-like內容。
- quarantine 是安全終止狀態；移動失敗時保留原檔並回報，禁止 destructive retry loop。
- 列表和 read path 只供 Admin／local maintenance；Guest 無任何對應 capability。
- security summary 不讀正式資料庫內容，不把 username、IP、path 或 command line寫入 bundle。

## 7. Validation plan

Focused tests：ID uniqueness、strict schema、redaction、CRLF、XSS、traversal、reparse／symlink、PNG／text allowlist、archive拒絕、atomic failure、permission／quota、concurrency、Guest denial、cross-session、dedupe、retention、prompt／URL／command content、Git exclusion與既有 observability regression。

E2E：Practice／isolated database觸發 synthetic failure → OP／REQ → Admin preview/save → validate/hash → safe summary → malicious bundle quarantine → Guest browser-only export → support failure不影響 roster workflow → resolution record。

## 8. Residual risks

- 單一 Windows 主機和本機 Inbox沒有獨立不可變證據；host/admin compromise可同時影響 app、incident與log。
- allowlist與pattern redaction不能保證識別所有自然語言個資；附件尤其需要人工預覽。
- Cloudflare／browser／OS產生的外部 metadata不受本功能完全控制。
- 未部署 out-of-band alerting；主機停機時只能在恢復後診斷。
- 正式 human acceptance仍需要首席導學風紀及顧問老師確認回報文案和實際交接流程。
