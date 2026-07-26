# Security policy / 安全政策

Please report suspected vulnerabilities through GitHub **Private vulnerability
reporting** on this repository's Security tab. Do not include student names,
rosters, leave records, database files, backups, access tokens, cookies, private
keys, or complete logs in a public issue.

如懷疑存在漏洞，請使用本倉庫 Security 分頁的 GitHub **Private
vulnerability reporting** 私密通報。不要在公開 Issue 附上學生姓名、值班表、
請假紀錄、資料庫、備份、存取權杖、Cookie、私鑰或完整日誌。

## Supported release / 支援版本

Only the release identified as the current live baseline in `README.md` and
`PROJECT_STATUS.md` receives security fixes. Older tags and archival branches
are recovery or historical evidence, not independently supported deployments.

只有 `README.md` 與 `PROJECT_STATUS.md` 標示為現行正式基線的版本會接收安全
修正。舊 tag 及封存分支只供回復或歷史證據，不是獨立受支援部署。

## What to report / 適合通報的問題

- authentication or authorization bypass;
- Guest access to AI, import, upload, persistent writes, official data, or
  privileged exports;
- forged or replayed gateway principals, sessions, or public shares;
- exposure of plaintext roster data, secrets, backups, or private logs;
- cross-site request, script injection, unsafe proxying, or origin bypass;
- data corruption, lost updates, unaudited deletion, or a broken restore path;
- workflow, dependency, release, or branch-protection bypasses.

請通報身份／權限繞過、Guest 越權、session 或分享偽造／重播、明文資料或 secret
外洩、跨站／注入／origin 繞過、資料損壞或無法復原，以及 CI、供應鏈、發布或
分支保護繞過。

## Safe report contents / 安全通報內容

Include the affected version, route or component, impact, minimal reproduction,
and a redacted support reference if available. Use fictional data. Stop testing
if it could affect availability, another person's session, Cloudflare resources,
or the production database.

For ordinary bugs and UX problems, create the report through the application's
`/support` page first. A public GitHub issue should contain only the resulting
reference, a redacted technical summary, and fictional reproduction data. Keep
attachments and host-local incident bundles out of Issues and pull requests.

請提供受影響版本、路由／元件、影響、最小重現步驟及經遮蔽的支援編號；只用
虛構資料。如測試可能影響服務可用性、他人 session、Cloudflare 資源或正式
資料庫，請立即停止。

## Response and disclosure / 回應與披露

The maintainer will acknowledge a usable report as soon as practical, validate
impact, prepare a fix and recovery plan, and coordinate disclosure after a safe
release. No fixed bounty or response-time guarantee is offered.

維護者會在實際可行情況下確認有效通報、驗證影響、準備修正及回復方案，並在
安全版本發布後協調披露。本專案不承諾獎金或固定回應時限。

The full threat model, privacy boundary, repository governance, incident steps,
and residual risks are documented in
[`docs/SECURITY_AND_PRIVACY.md`](docs/SECURITY_AND_PRIVACY.md). The ordinary
support procedure and local inbox threat model are documented in
[`docs/SUPPORT_AND_INCIDENT_WORKFLOW.md`](docs/SUPPORT_AND_INCIDENT_WORKFLOW.md)
and [`docs/THREAT_MODEL_SUPPORT_INBOX.md`](docs/THREAT_MODEL_SUPPORT_INBOX.md).
