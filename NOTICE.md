# Project notice / 專案聲明

I am **LI Chuangjie Jacky (李創杰)**, Head Study Prefect for 2026–2027. I
completed the current NiceGUI rebuild and formal release with Codex. Codex and
I are the only two co-creators. The work is presented under **Study Prefect
Team · Service Weave co-creation**; this is a project credit, not a separate
office, department, rank, or contractor team.

我是 **李創杰**，2026–2027 年度首席導學風紀。本次 NiceGUI 重構及正式發布版本，
**只由我與 Codex 兩位共創者共同完成**。作品以 **Study Prefect Team／導學風紀組 ·
Service Weave 系統共創** 呈現；這是項目署名，不是另一個辦公室、部門、職級或外判團隊。

This notice records project authorship and context. It does not modify or
restrict the MIT License in `LICENSE`. Third-party music, fonts, school identity
materials, and other externally originating media retain their own applicable
terms and are not relicensed by the project’s MIT License.

此聲明只記錄專案的共創來源與脈絡，不會修改或限制 `LICENSE` 內的 MIT License。第三方
音樂、字體、學校識別素材及其他外來媒體仍適用其各自條款，不會因本專案採用 MIT License
而被重新授權。

The local interaction layer includes GSAP 3.13.0 under its published Standard
“no charge” license. The versioned distribution file and npm package metadata
are retained in `nicegui_app/assets/vendor/`; the application loads that file
from its own localhost origin and does not depend on a runtime CDN request.

本機互動層使用 GSAP 3.13.0，並依其公布的 Standard “no charge” license
使用。版本化程式及 npm 套件資料保存在 `nicegui_app/assets/vendor/`；網站只從
本機 localhost 載入，不會在運行時依賴 CDN。

The shared control family and public gateway include substantially rewritten
interaction patterns adapted from Uiverse.io under the MIT License. References
include adamgiebl's “massive-insect-65” button, andrew-demchenk0's
“afraid-squid-51” button, Jay-9527's “weak-dingo-78” switch, Gautammsharma's
“massive-rabbit-40” checkbox, Lanicet's “fluffy-otter-43” progress track,
Li-Deheng's “shy-moth-10” Arrow Flow Button, and JkHuger's “little-falcon-22”
loader. Production versions use local semantic tokens, scoped Quasar／gateway
selectors, keyboard and touch states, real busy／disabled／progress semantics,
and reduced-motion fallbacks. No Uiverse runtime dependency or remote asset is
loaded.

共用控制元件及公開入口採用若干經大幅重寫的 Uiverse.io 互動概念，並依 MIT
License 使用。參考來源包括 adamgiebl 的「massive-insect-65」按鈕、
andrew-demchenk0 的「afraid-squid-51」按鈕、Jay-9527 的
「weak-dingo-78」切換器、Gautammsharma 的「massive-rabbit-40」勾選框、
Lanicet 的「fluffy-otter-43」進度軌道、Li-Deheng 的「shy-moth-10」Arrow
Flow Button，以及 JkHuger 的「little-falcon-22」載入元件。正式版本改用本專案
語意色彩變數、限定 Quasar／入口類別、鍵盤／觸控狀態、真實 busy／disabled／
progress 語意及 reduced-motion 後備；運行時不會載入 Uiverse 依賴或遠端素材。

The optional local YouTube audio-import adapter uses the hash-locked `yt-dlp`
2026.7.4 Python wheel distributed under the Unlicense and the hash-locked Deno
2.9.2 runtime under the MIT License. Its operation remains separate from roster
data and does not relicense downloaded media.

選用的 YouTube 本機音訊匯入適配層使用已鎖定雜湊的 `yt-dlp` 2026.7.4
Python wheel（Unlicense）及 Deno 2.9.2 runtime（MIT License）。它與排班資料
完全分開，也不會改變下載媒體本身的授權。
