const TRIAL_CSP = [
  "default-src 'none'",
  "script-src 'self'",
  "style-src 'self'",
  "connect-src 'none'",
  "img-src 'self' data: blob:",
  "font-src 'none'",
  "media-src 'none'",
  "worker-src 'none'",
  "child-src 'none'",
  "base-uri 'none'",
  "form-action 'none'",
  "frame-ancestors 'none'",
  "object-src 'none'",
  "manifest-src 'none'",
  'upgrade-insecure-requests',
].join('; ');

export const TRIAL_SECURITY_HEADERS = Object.freeze({
  'Cache-Control': 'no-store, max-age=0',
  'Content-Security-Policy': TRIAL_CSP,
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet',
});

const TRIAL_HEAD = String.raw`<meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/trial.css">`;

const BRAND = String.raw`<a class="brand" href="/" aria-label="返回網站入口 · Return to site entrance">
  <img src="/favicon.svg" width="42" height="42" alt="">
  <span><b>聖言中學</b><small>Study Prefect Duty Roster</small></span>
</a>`;

export const GUEST_PLATFORM_HTML = String.raw`<!doctype html>
<html lang="zh-Hant-HK" data-theme="auto" data-lang="zh">
<head>
  ${TRIAL_HEAD}
  <title>訪客體驗 · Study Prefect Duty Roster</title>
  <script src="/guest.js" defer></script>
</head>
<body class="platform-page">
  <a class="skip-link" href="#main" data-guest-i18n="skip">跳到主要內容</a>
  <header class="platform-nav">
    ${BRAND}
    <nav class="platform-controls" aria-label="訪客導覽 · Guest navigation">
      <a class="platform-section-link" href="#team" data-guest-i18n="navTeam">團隊架構</a>
      <a class="platform-section-link" href="#capabilities" data-guest-i18n="navCapabilities">平台能力</a>
      <a class="platform-section-link" href="#resources" data-guest-i18n="navResources">平台資源</a>
      <a class="platform-section-link" href="#trust" data-guest-i18n="navTrust">資料邊界</a>
      <button id="guestLanguageToggle" class="control-button" type="button" aria-label="Switch language">中文 / EN</button>
      <button id="guestThemeToggle" class="control-button" type="button" aria-label="切換外觀 · Change appearance">外觀：自動</button>
      <a class="button button--compact" href="/try"><span data-guest-i18n="navTry">開始試用</span><span aria-hidden="true">→</span></a>
    </nav>
  </header>

  <main id="main" tabindex="-1">
    <section class="platform-hero">
      <div class="hero-copy">
        <p class="kicker">PUBLIC PRODUCT TOUR · 訪客瀏覽模式</p>
        <h1><span data-guest-i18n="heroLine1">先理解平台，</span><br><span data-guest-i18n="heroLine2">再親手完成一張值班表。</span></h1>
        <p class="lead" data-guest-i18n="heroLead">以一組完全虛構的中文名單，體驗生成、核對、雙語預覽及 PDF 匯出。正式學校資料、管理員工作台與公平帳本全程保持隔離。</p>
        <div class="hero-actions">
          <a class="button" href="/try"><span data-guest-i18n="enterTry">進入互動試用</span><span aria-hidden="true">→</span></a>
          <a class="text-link" href="/" data-guest-i18n="returnEntrance">返回登入入口</a>
        </div>
        <div class="proof-line" aria-label="試用保障 · Trial safeguards">
          <span data-guest-i18n="proofFictional">虛構資料</span><span data-guest-i18n="proofDevice">裝置內運算</span><span data-guest-i18n="proofExpiry">30 分鐘後失效</span><span data-guest-i18n="proofServer">不寫入伺服器</span>
        </div>
      </div>
      <aside class="hero-system" aria-label="試用資料流 · Trial data flow">
        <p class="system-label">ISOLATED TRIAL</p>
        <div class="system-node system-node--active"><b>01</b><span><strong data-guest-i18n="flowBrowser">瀏覽器工作區</strong><small>Browser workspace</small></span></div>
        <div class="system-line" aria-hidden="true"></div>
        <div class="system-node"><b>02</b><span><strong data-guest-i18n="flowSession">分頁暫存</strong><small>Session-only state</small></span></div>
        <div class="system-line" aria-hidden="true"></div>
        <div class="system-node"><b>03</b><span><strong data-guest-i18n="flowPdf">裝置內 PDF</strong><small>On-device export</small></span></div>
        <p class="system-boundary"><span aria-hidden="true">✓</span> <span data-guest-i18n="zeroWrites">零伺服器寫入</span></p>
      </aside>
    </section>

    <section id="team" class="platform-section" aria-labelledby="team-title">
      <div class="section-heading"><p class="kicker">OPERATING MODEL</p><h2 id="team-title" data-guest-i18n="teamTitle">一個以服事為核心、責任清楚的團隊。</h2><p data-guest-i18n="teamLead">平台把每個角色的工作界線、核對責任與交接關係說清楚，讓公平不依賴某一個人的記憶。</p></div>
      <div class="operating-grid">
        <article><span class="role-mark">01</span><h3 data-guest-i18n="roleHeadTitle">首席導學風紀</h3><p data-guest-i18n="roleHeadCopy">主持每週生成、核對、發布、請假調整與交接；對操作決定負責。</p></article>
        <article><span class="role-mark">02</span><h3 data-guest-i18n="roleAssistantTitle">助理首席導學風紀</h3><p data-guest-i18n="roleAssistantCopy">在值班安排中只負責 Assist. in charge，保持角色界線清晰。</p></article>
        <article><span class="role-mark">03</span><h3 data-guest-i18n="rolePrefectTitle">導學風紀</h3><p data-guest-i18n="rolePrefectCopy">按可值班日及公平紀錄服務 302、303 與 202 室。</p></article>
        <article><span class="role-mark">04</span><h3 data-guest-i18n="roleAdvisorTitle">顧問老師</h3><p data-guest-i18n="roleAdvisorCopy">在正式驗收與需要時提供校務方向；日常操作由學生領袖負責。</p></article>
      </div>
    </section>

    <section id="capabilities" class="platform-section" aria-labelledby="capability-title">
      <div class="section-heading"><p class="kicker">CAPABILITIES</p><h2 id="capability-title" data-guest-i18n="capabilityTitle">一條完整而克制的試用路徑</h2><p data-guest-i18n="capabilityLead">與正式系統採用相同的核心概念，但所有結果只屬於這一個瀏覽器分頁。</p></div>
      <div class="capability-grid">
        <article><span class="index">01</span><h3 data-guest-i18n="cap1Title">查看虛構名單</h3><p data-guest-i18n="cap1Copy">中文姓名、職位與班別清楚標示；角色界線與正式規則一致。</p></article>
        <article><span class="index">02</span><h3 data-guest-i18n="cap2Title">登記示範請假</h3><p data-guest-i18n="cap2Copy">加入或撤回生成前請假，立即理解排班前準備的用途。</p></article>
        <article><span class="index">03</span><h3 data-guest-i18n="cap3Title">生成及核對</h3><p data-guest-i18n="cap3Copy">在裝置內建立固定、可重複、符合角色與不連續規則的示範週表。</p></article>
        <article><span class="index">04</span><h3 data-guest-i18n="cap4Title">匯出雙語 PDF</h3><p data-guest-i18n="cap4Copy">直接下載 A4 橫向 PDF；中英文標籤並列，所有姓名保持中文。</p></article>
      </div>
    </section>

    <section class="platform-section" aria-labelledby="solutions-title">
      <div class="section-heading"><p class="kicker">SERVICE SOLUTIONS</p><h2 id="solutions-title" data-guest-i18n="solutionsTitle">由每週工作到多年交接，形成一條完整服務生命線。</h2></div>
      <div class="solution-grid">
        <article><span aria-hidden="true">週</span><div><h3 data-guest-i18n="solutionWeeklyTitle">每週值班運作</h3><p data-guest-i18n="solutionWeeklyCopy">生成草稿、逐項核對、發布並匯出中英文 PDF。</p></div></article>
        <article><span aria-hidden="true">調</span><div><h3 data-guest-i18n="solutionAdjustTitle">已發布後調整</h3><p data-guest-i18n="solutionAdjustCopy">在不重排整週的前提下，安全記錄請假與替補。</p></div></article>
        <article><span aria-hidden="true">衡</span><div><h3 data-guest-i18n="solutionFairTitle">公平與可解釋性</h3><p data-guest-i18n="solutionFairCopy">以 history_weight、公平帳本與審計記錄說明每次安排。</p></div></article>
        <article><span aria-hidden="true">承</span><div><h3 data-guest-i18n="solutionHandoverTitle">延續與交接</h3><p data-guest-i18n="solutionHandoverCopy">由備份、受控還原到新學年名單，讓下一任可安全接手。</p></div></article>
      </div>
    </section>

    <section id="resources" class="platform-section" aria-labelledby="resources-title">
      <div class="section-heading"><p class="kicker">PLATFORM &amp; RESOURCES</p><h2 id="resources-title" data-guest-i18n="resourcesTitle">把操作方法、工程證據與團隊文化放在同一個可信框架。</h2><p data-guest-i18n="resourcesLead">訪客可完整了解平台如何服務、如何保護資料，以及為何能交給下一任使用；正式編輯能力仍只屬於管理員。</p></div>
      <div class="resource-grid">
        <article><span class="resource-icon" aria-hidden="true">團</span><h3 data-guest-i18n="resourceTeamTitle">平台與團隊</h3><p data-guest-i18n="resourceTeamCopy">交代 Study Prefect Operations 的角色、能力、服務方案、文化與共創責任。</p></article>
        <article><span class="resource-icon" aria-hidden="true">工</span><h3 data-guest-i18n="resourceQualityTitle">工程與品質證據</h3><p data-guest-i18n="resourceQualityCopy">展示分層架構、發布閘門、隔離測試、健康檢查、日誌及可維護性原則。</p></article>
        <article><span class="resource-icon" aria-hidden="true">構</span><h3 data-guest-i18n="resourceArchitectureTitle">系統架構與可信設計</h3><p data-guest-i18n="resourceArchitectureCopy">說明介面、政策、工作流、交易、SQLite、備份、審計及 Cloudflare 邊界。</p></article>
        <article><span class="resource-icon" aria-hidden="true">始</span><h3 data-guest-i18n="resourceStartTitle">開始使用</h3><p data-guest-i18n="resourceStartCopy">以最短路徑理解名單準備、請假、生成、核對、發布、PDF 及事後調整。</p></article>
        <article><span class="resource-icon" aria-hidden="true">冊</span><h3 data-guest-i18n="resourceGuideTitle">使用手冊</h3><p data-guest-i18n="resourceGuideCopy">繁中優先、英文完整的逐步指引，並解釋空白、錯誤、確認、復原與交接。</p></article>
        <article><span class="resource-icon" aria-hidden="true">經</span><h3 data-guest-i18n="resourceDevotionalTitle">每日經文</h3><p data-guest-i18n="resourceDevotionalCopy">以 RCUV 2010（神版）及 NKJV 配合默想、禱告與服事提醒，先安靜再開始工作。</p></article>
      </div>
      <div class="co-creation-strip"><div><p class="kicker">CO-CREATED BY STUDY PREFECT OPERATIONS</p><h3 data-guest-i18n="coCreationTitle">由李創杰與 Codex 共同建立，為下一任留下可理解、可核對、可接手的平台。</h3></div><div class="co-creation-links"><a class="text-link" href="mailto:s10777@syss.edu.hk" data-guest-i18n="feedbackLink">電郵反饋</a><a class="text-link" href="https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System" target="_blank" rel="noopener noreferrer" data-guest-i18n="githubLink">查看 GitHub</a></div></div>
    </section>

    <section id="trust" class="platform-section platform-section--trust" aria-labelledby="trust-title">
      <div class="section-heading"><p class="kicker">TRUST BOUNDARY</p><h2 id="trust-title" data-guest-i18n="trustTitle">試用與正式資料之間，有一道真正的邊界。</h2></div>
      <div class="trust-layout">
        <div class="trust-statement"><p class="trust-quote">“The guest tour contains no official roster data.”</p><p data-guest-i18n="trustCopy">不包含任何正式值班資料。試用頁只載入固定虛構名單及本機程式碼；操作後不會連接 NiceGUI、KV、SQLite、備份、日誌或公平帳本。</p></div>
        <ul class="trust-list">
          <li><strong data-guest-i18n="boundaryTabTitle">只在目前分頁</strong><span data-guest-i18n="boundaryTabCopy">使用 sessionStorage，關閉分頁即清除。</span></li>
          <li><strong data-guest-i18n="boundaryTimeTitle">有時限</strong><span data-guest-i18n="boundaryTimeCopy">建立後 30 分鐘自動失效並重置。</span></li>
          <li><strong data-guest-i18n="boundaryResetTitle">可隨時重置</strong><span data-guest-i18n="boundaryResetCopy">一個按鈕清除請假與草稿；語言及外觀設定會保留。</span></li>
          <li><strong data-guest-i18n="boundaryPublishTitle">沒有發布能力</strong><span data-guest-i18n="boundaryPublishCopy">不能建立分享連結或改動任何正式資料。</span></li>
        </ul>
      </div>
      <a class="button" href="/try"><span data-guest-i18n="trustTry">使用虛構資料開始試用</span><span aria-hidden="true">→</span></a>
    </section>
  </main>

  <footer class="platform-footer"><p><strong>Study Prefect Operations</strong><span data-guest-i18n="footerPrinciple">不是要受人的服事，乃是要服事人。</span></p><p data-guest-i18n="footerPlatform">為公平、謹慎服務而建立的本機優先值班平台。</p></footer>
</body>
</html>`;

export const GUEST_PLATFORM_JS = String.raw`(() => {
  'use strict';
  const STORAGE_KEY = 'sing-yin-guest-display-v1';
  const LANGUAGES = ['zh', 'en'];
  const THEMES = ['auto', 'light', 'dark'];
  const COPY = {
    zh: {
      skip: '跳到主要內容', navTeam: '團隊架構', navCapabilities: '平台能力', navResources: '平台資源', navTrust: '資料邊界', navTry: '開始試用', heroLine1: '先理解平台，', heroLine2: '再親手完成一張值班表。', heroLead: '以一組完全虛構的中文名單，體驗生成、核對、雙語預覽及 PDF 匯出。正式學校資料、管理員工作台與公平帳本全程保持隔離。', enterTry: '進入互動試用', returnEntrance: '返回登入入口', proofFictional: '虛構資料', proofDevice: '裝置內運算', proofExpiry: '30 分鐘後失效', proofServer: '不寫入伺服器', flowBrowser: '瀏覽器工作區', flowSession: '分頁暫存', flowPdf: '裝置內 PDF', zeroWrites: '零伺服器寫入', teamTitle: '一個以服事為核心、責任清楚的團隊。', teamLead: '平台把每個角色的工作界線、核對責任與交接關係說清楚，讓公平不依賴某一個人的記憶。', roleHeadTitle: '首席導學風紀', roleHeadCopy: '主持每週生成、核對、發布、請假調整與交接；對操作決定負責。', roleAssistantTitle: '助理首席導學風紀', roleAssistantCopy: '在值班安排中只負責 Assist. in charge，保持角色界線清晰。', rolePrefectTitle: '導學風紀', rolePrefectCopy: '按可值班日及公平紀錄服務 302、303 與 202 室。', roleAdvisorTitle: '顧問老師', roleAdvisorCopy: '在正式驗收與需要時提供校務方向；日常操作由學生領袖負責。', capabilityTitle: '一條完整而克制的試用路徑', capabilityLead: '與正式系統採用相同的核心概念，但所有結果只屬於這一個瀏覽器分頁。', cap1Title: '查看虛構名單', cap1Copy: '中文姓名、職位與班別清楚標示；角色界線與正式規則一致。', cap2Title: '登記示範請假', cap2Copy: '加入或撤回生成前請假，立即理解排班前準備的用途。', cap3Title: '生成及核對', cap3Copy: '在裝置內建立固定、可重複、符合角色與不連續規則的示範週表。', cap4Title: '匯出雙語 PDF', cap4Copy: '直接下載 A4 橫向 PDF；中英文標籤並列，所有姓名保持中文。', solutionsTitle: '由每週工作到多年交接，形成一條完整服務生命線。', solutionWeeklyTitle: '每週值班運作', solutionWeeklyCopy: '生成草稿、逐項核對、發布並匯出中英文 PDF。', solutionAdjustTitle: '已發布後調整', solutionAdjustCopy: '在不重排整週的前提下，安全記錄請假與替補。', solutionFairTitle: '公平與可解釋性', solutionFairCopy: '以 history_weight、公平帳本與審計記錄說明每次安排。', solutionHandoverTitle: '延續與交接', solutionHandoverCopy: '由備份、受控還原到新學年名單，讓下一任可安全接手。', resourcesTitle: '六個公開資源入口，完整交代平台如何工作、驗證及交接。', resourcesLead: '訪客可查看平台與團隊、工程品質、系統架構、開始使用、使用手冊及每日經文；正式編輯能力仍只屬於管理員。', resourceTeamTitle: '平台與團隊', resourceTeamCopy: '交代 Study Prefect Operations 的角色、能力、服務方案、文化與共創責任。', resourceQualityTitle: '工程與品質證據', resourceQualityCopy: '展示分層架構、發布閘門、隔離測試、健康檢查、日誌及可維護性原則。', resourceArchitectureTitle: '系統架構與可信設計', resourceArchitectureCopy: '說明介面、政策、工作流、交易、SQLite、備份、審計及 Cloudflare 邊界。', resourceStartTitle: '開始使用', resourceStartCopy: '以最短路徑理解名單準備、請假、生成、核對、發布、PDF 及事後調整。', resourceGuideTitle: '使用手冊', resourceGuideCopy: '繁中優先、英文完整的逐步指引，並解釋空白、錯誤、確認、復原與交接。', resourceDevotionalTitle: '每日經文', resourceDevotionalCopy: '以 RCUV 2010（神版）及 NKJV 配合默想、禱告與服事提醒，先安靜再開始工作。', coCreationTitle: '由李創杰與 Codex 共同建立，為下一任留下可理解、可核對、可接手的平台。', feedbackLink: '電郵反饋', githubLink: '查看 GitHub', trustTitle: '試用與正式資料之間，有一道真正的邊界。', trustCopy: '不包含任何正式值班資料。試用頁只載入固定虛構名單及本機程式碼；操作後不會連接 NiceGUI、KV、SQLite、備份、日誌或公平帳本。', boundaryTabTitle: '只在目前分頁', boundaryTabCopy: '使用 sessionStorage，關閉分頁即清除。', boundaryTimeTitle: '有時限', boundaryTimeCopy: '建立後 30 分鐘自動失效並重置。', boundaryResetTitle: '可隨時重置', boundaryResetCopy: '一個按鈕清除請假與草稿；語言及外觀設定會保留。', boundaryPublishTitle: '沒有發布能力', boundaryPublishCopy: '不能建立分享連結或改動任何正式資料。', trustTry: '使用虛構資料開始試用', footerPrinciple: '不是要受人的服事，乃是要服事人。', footerPlatform: '為公平、謹慎服務而建立的本機優先值班平台。', themeAuto: '外觀：自動', themeLight: '外觀：淺色', themeDark: '外觀：深色',
    },
    en: {
      skip: 'Skip to main content', navTeam: 'Team model', navCapabilities: 'Capabilities', navResources: 'Resources', navTrust: 'Data boundary', navTry: 'Start trial', heroLine1: 'Understand the platform.', heroLine2: 'Then build a roster yourself.', heroLead: 'Explore generation, review, bilingual preview, and PDF export with a completely fictional Chinese directory. Official school data, the administrator workbench, and the fairness ledger remain isolated.', enterTry: 'Enter interactive trial', returnEntrance: 'Return to sign-in entrance', proofFictional: 'Fictional data', proofDevice: 'On-device processing', proofExpiry: 'Expires after 30 minutes', proofServer: 'Zero server writes', flowBrowser: 'Browser workspace', flowSession: 'Tab-only state', flowPdf: 'On-device PDF', zeroWrites: 'Zero server writes', teamTitle: 'A service-centred team with explicit responsibilities.', teamLead: 'The platform makes role boundaries, review ownership, and succession relationships visible so fairness does not depend on one person’s memory.', roleHeadTitle: 'Head Study Prefect', roleHeadCopy: 'Owns weekly generation, review, publishing, absence adjustment, and handover decisions.', roleAssistantTitle: 'Assistant Head Study Prefect', roleAssistantCopy: 'Serves only Assist. in charge in the roster, preserving a clear role boundary.', rolePrefectTitle: 'Study Prefect', rolePrefectCopy: 'Serves Rooms 302, 303, and 202 according to availability and fairness history.', roleAdvisorTitle: 'Teacher Advisor', roleAdvisorCopy: 'Provides school direction at formal acceptance and when needed; student leaders own daily operation.', capabilityTitle: 'A complete, deliberately bounded trial journey', capabilityLead: 'It uses the same core concepts as the official system, but every result belongs only to this browser tab.', cap1Title: 'Review the fictional directory', cap1Copy: 'Chinese names, roles, and classes are clear, with the same role boundaries as the official rules.', cap2Title: 'Declare trial leave', cap2Copy: 'Add or remove pre-generation leave to understand the preparation step before scheduling.', cap3Title: 'Generate and review', cap3Copy: 'Build a deterministic on-device roster that respects role and no-consecutive-duty rules.', cap4Title: 'Export a bilingual PDF', cap4Copy: 'Download an A4 landscape PDF with bilingual labels while every prefect name remains Chinese.', solutionsTitle: 'A complete service lifeline from weekly work to multi-year succession.', solutionWeeklyTitle: 'Weekly roster operations', solutionWeeklyCopy: 'Generate a draft, review each item, publish, and export Chinese and English PDFs.', solutionAdjustTitle: 'Post-publication adjustment', solutionAdjustCopy: 'Record absence and substitution safely without rebuilding the entire week.', solutionFairTitle: 'Fairness and explanation', solutionFairCopy: 'Explain every assignment through history_weight, the fairness ledger, and audit records.', solutionHandoverTitle: 'Continuity and handover', solutionHandoverCopy: 'Verified backups, managed restore, and new-year directory preparation support a safe succession.', resourcesTitle: 'Six public resource entries explain how the platform works, proves quality, and supports succession.', resourcesLead: 'Visitors can explore Platform & Team, Engineering & Quality, System Architecture & Trust, Getting Started, the Operator Guide, and Daily Verse. Official editing remains administrator-only.', resourceTeamTitle: 'Platform & Team', resourceTeamCopy: 'Explains Study Prefect Operations roles, capabilities, service solutions, culture, and co-creation responsibility.', resourceQualityTitle: 'Engineering & Quality', resourceQualityCopy: 'Shows layered design, release gates, isolated tests, health checks, logs, and maintainability principles.', resourceArchitectureTitle: 'System Architecture & Trust', resourceArchitectureCopy: 'Maps the interface, policy, workflow, transactions, SQLite, backup, audit, and Cloudflare boundaries.', resourceStartTitle: 'Getting Started', resourceStartCopy: 'Follows the shortest path through directory preparation, leave, generation, review, publishing, PDF, and later adjustment.', resourceGuideTitle: 'Operator Guide', resourceGuideCopy: 'Traditional Chinese-first and complete English procedures explain empty, error, confirmation, recovery, and handover states.', resourceDevotionalTitle: 'Daily Verse', resourceDevotionalCopy: 'RCUV 2010 (Shen Edition) and NKJV readings pair reflection, prayer, and a reminder to begin service quietly.', coCreationTitle: 'Co-created by Lee Chong Kit and Codex to leave the next Head Study Prefect a platform that can be understood, verified, and safely inherited.', feedbackLink: 'Email feedback', githubLink: 'View GitHub', trustTitle: 'A real boundary separates the trial from official data.', trustCopy: 'No official roster data is included. The trial loads only a fixed fictional directory and local code; interactions never connect to NiceGUI, KV, SQLite, backups, logs, or the fairness ledger.', boundaryTabTitle: 'Current tab only', boundaryTabCopy: 'sessionStorage is cleared when the tab closes.', boundaryTimeTitle: 'Time bounded', boundaryTimeCopy: 'The session expires and resets automatically after 30 minutes.', boundaryResetTitle: 'Reset at any time', boundaryResetCopy: 'One action clears trial leave and roster; language and appearance remain.', boundaryPublishTitle: 'No publishing capability', boundaryPublishCopy: 'The trial cannot create share links or modify official data.', trustTry: 'Start with fictional data', footerPrinciple: 'Not to be served, but to serve.', footerPlatform: 'A local-first roster platform built for fair, careful service.', themeAuto: 'Theme: Auto', themeLight: 'Theme: Light', themeDark: 'Theme: Dark',
    },
  };
  let state = { language: 'zh', theme: 'auto' };
  try {
    const stored = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || 'null');
    if (stored && LANGUAGES.includes(stored.language) && THEMES.includes(stored.theme)) state = stored;
  } catch { /* Defaults remain safe. */ }
  const save = () => { try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* In-memory controls remain available. */ } };
  const render = () => {
    document.documentElement.dataset.lang = state.language;
    document.documentElement.dataset.theme = state.theme;
    document.documentElement.lang = state.language === 'zh' ? 'zh-Hant-HK' : 'en';
    document.querySelectorAll('[data-guest-i18n]').forEach(element => { element.textContent = COPY[state.language][element.dataset.guestI18n]; });
    document.getElementById('guestLanguageToggle').textContent = state.language === 'zh' ? '中文 / EN' : 'EN / 中文';
    const themeKey = state.theme === 'light' ? 'themeLight' : state.theme === 'dark' ? 'themeDark' : 'themeAuto';
    document.getElementById('guestThemeToggle').textContent = COPY[state.language][themeKey];
  };
  document.getElementById('guestLanguageToggle').addEventListener('click', () => { state.language = state.language === 'zh' ? 'en' : 'zh'; save(); render(); });
  document.getElementById('guestThemeToggle').addEventListener('click', () => { state.theme = THEMES[(THEMES.indexOf(state.theme) + 1) % THEMES.length]; save(); render(); });
  save(); render();
})();`;

export const TRIAL_HTML = String.raw`<!doctype html>
<html lang="zh-Hant-HK" data-theme="auto" data-lang="zh">
<head>
  ${TRIAL_HEAD}
  <title>互動試用 · Roster Sandbox</title>
  <script src="/trial.js" defer></script>
</head>
<body class="trial-page">
  <a class="skip-link" href="#trialMain">跳到試用工作區 · Skip to sandbox</a>
  <header class="trial-nav">
    ${BRAND}
    <div class="trial-controls" aria-label="顯示設定 · Display settings">
      <button id="languageToggle" class="control-button" type="button" aria-label="Switch language">中文 / EN</button>
      <button id="themeToggleTrial" class="control-button" type="button" aria-label="切換外觀 · Change appearance">外觀：自動</button>
      <a class="control-button" href="/guest" data-i18n="exit">離開試用</a>
    </div>
  </header>

  <main id="trialMain" class="trial-shell" tabindex="-1">
    <section class="trial-intro">
      <div><p class="kicker">INTERACTIVE SANDBOX · 互動試用</p><h1 data-i18n="title">用虛構資料，完成一週值班表。</h1><p data-i18n="intro">所有操作只留在這個分頁，30 分鐘後失效；不會接觸正式名單、伺服器資料或公平帳本。</p></div>
      <div class="privacy-seal" role="status"><span aria-hidden="true">✓</span><p><strong data-i18n="privacyTitle">裝置內試用</strong><small data-i18n="privacyDetail">零伺服器寫入 · Session only</small></p></div>
    </section>

    <nav class="step-rail" aria-label="試用步驟 · Trial steps">
      <a href="#directory"><b>01</b><span data-i18n="step1">認識名單</span></a>
      <a href="#prepare"><b>02</b><span data-i18n="step2">準備請假</span></a>
      <a href="#preview"><b>03</b><span data-i18n="step3">生成及匯出</span></a>
    </nav>

    <section id="directory" class="workspace-section" aria-labelledby="directoryTitle">
      <div class="workspace-heading"><div><p class="step-label">STEP 01</p><h2 id="directoryTitle" data-i18n="directoryTitle">虛構導學風紀名單</h2><p data-i18n="directoryHelp">先理解角色分工。以下姓名、班別及資料全部為虛構，只用作產品示範。</p></div><span id="directoryCount" class="count-badge"></span></div>
      <div id="directoryGrid" class="directory-grid"></div>
    </section>

    <section id="prepare" class="workspace-section" aria-labelledby="prepareTitle">
      <div class="workspace-heading"><div><p class="step-label">STEP 02</p><h2 id="prepareTitle" data-i18n="prepareTitle">登記生成前請假</h2><p data-i18n="prepareHelp">這一步可以略過。加入示範請假後，生成器會避開該同學當日的崗位。</p></div></div>
      <div class="absence-composer">
        <label><span data-i18n="personLabel">導學風紀</span><select id="absencePerson"></select></label>
        <label><span data-i18n="dayLabel">日期</span><select id="absenceDay"></select></label>
        <button id="addAbsence" class="button button--secondary" type="button" data-i18n="addAbsence">加入示範請假</button>
      </div>
      <div id="absenceList" class="absence-list" aria-live="polite"></div>
    </section>

    <section id="preview" class="workspace-section workspace-section--preview" aria-labelledby="previewTitle">
      <div class="workspace-heading"><div><p class="step-label">STEP 03</p><h2 id="previewTitle" data-i18n="previewTitle">生成、核對與匯出</h2><p data-i18n="previewHelp">同一組輸入會得到同一個結果；助理首席只負責 Assist. in charge，一般導學風紀只負責房間。</p></div></div>
      <div class="action-bar">
        <button id="generateRoster" class="button" type="button"><span data-i18n="generate">生成示範值班表</span><span aria-hidden="true">→</span></button>
        <button id="downloadPdf" class="button button--secondary" type="button" disabled data-i18n="download">下載雙語 PDF</button>
        <button id="resetTrial" class="text-button" type="button" data-i18n="reset">重置全部試用資料</button>
      </div>
      <div id="trialStatus" class="status-line" aria-live="polite"></div>
      <div id="rosterEmpty" class="roster-empty"><span aria-hidden="true">週</span><p><strong data-i18n="emptyTitle">值班表仍未生成</strong><small data-i18n="emptyHelp">檢查名單及請假後，按「生成示範值班表」。</small></p></div>
      <div id="rosterPreview" class="roster-preview" hidden>
        <div class="preview-heading"><div><p class="kicker">WEEKLY ROSTER PREVIEW</p><h3 data-i18n="tableTitle">本週導學風紀值班表</h3></div><p id="weekRange"></p></div>
        <div class="table-scroll"><table id="rosterTable"></table></div>
        <div id="policyChecks" class="policy-checks"></div>
      </div>
    </section>

    <aside class="trial-boundary"><span aria-hidden="true">i</span><p><strong data-i18n="boundaryTitle">這不是正式發布。</strong><span data-i18n="boundaryCopy">試用結果不能分享成正式值班表，也不會影響任何人的 history_weight、服務時數或公平工作量。</span></p></aside>
  </main>
  <footer class="platform-footer"><p><strong>Guest Trial Sandbox</strong><span data-i18n="footerCopy">關閉分頁後，試用資料即會消失。</span></p><p id="expiryText"></p></footer>
  <noscript><div class="noscript">互動試用需要啟用 JavaScript；它只會在你的裝置內執行。 · JavaScript is required and runs only on your device.</div></noscript>
</body>
</html>`;

export const TRIAL_CSS = String.raw`
:root {
  color-scheme: light dark;
  --paper: #f5f3ed;
  --surface: #fffefa;
  --surface-soft: #eeece5;
  --ink: #182321;
  --muted: #66706c;
  --line: #d8d8d0;
  --line-strong: #b9c0ba;
  --brand: #176b67;
  --brand-strong: #0d514e;
  --brand-soft: #e3f0ec;
  --button-ink: #ffffff;
  --blue: #245f8f;
  --gold: #987332;
  --danger: #9b3f35;
  --focus: #1f73b7;
  --shadow: 0 22px 70px rgba(33, 42, 38, 0.10);
  --radius: 22px;
  --font: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang HK", "Noto Sans HK", "Microsoft JhengHei", sans-serif;
}
html[data-theme="dark"] {
  --paper: #0d1417;
  --surface: #141d20;
  --surface-soft: #1a2527;
  --ink: #edf3ef;
  --muted: #aab7b1;
  --line: #2c393b;
  --line-strong: #465456;
  --brand: #7fc5bb;
  --brand-strong: #a6dbd2;
  --brand-soft: #183936;
  --button-ink: #0b2422;
  --blue: #8dbbdd;
  --gold: #d3b16a;
  --danger: #e1a098;
  --focus: #8ec8f2;
  --shadow: 0 24px 80px rgba(0, 0, 0, 0.30);
}
@media (prefers-color-scheme: dark) {
  html[data-theme="auto"] {
    --paper: #0d1417; --surface: #141d20; --surface-soft: #1a2527; --ink: #edf3ef; --muted: #aab7b1;
    --line: #2c393b; --line-strong: #465456; --brand: #7fc5bb; --brand-strong: #a6dbd2;
    --brand-soft: #183936; --button-ink: #0b2422; --blue: #8dbbdd; --gold: #d3b16a; --danger: #e1a098; --focus: #8ec8f2;
    --shadow: 0 24px 80px rgba(0, 0, 0, 0.30);
  }
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; background: var(--paper); }
body { margin: 0; color: var(--ink); background: var(--paper); font-family: var(--font); line-height: 1.55; text-rendering: optimizeLegibility; }
a { color: inherit; }
button, select { font: inherit; }
button, a { -webkit-tap-highlight-color: transparent; }
button:focus-visible, a:focus-visible, select:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }
.skip-link { position: fixed; z-index: 20; top: 8px; left: 8px; padding: 10px 14px; border-radius: 10px; color: var(--surface); background: var(--ink); transform: translateY(-150%); }
.skip-link:focus { transform: none; }
.brand { display: inline-flex; align-items: center; gap: 11px; text-decoration: none; }
.brand img { width: 42px; height: 42px; object-fit: contain; }
.brand span { display: grid; }
.brand b { font-size: .82rem; letter-spacing: .04em; }
.brand small { color: var(--muted); font-size: .66rem; }
.platform-nav, .trial-nav { position: relative; z-index: 3; display: flex; align-items: center; justify-content: space-between; width: min(1180px, calc(100% - 40px)); min-height: 78px; margin: 0 auto; }
.platform-nav nav, .trial-controls { display: flex; align-items: center; gap: 8px; }
.platform-controls { flex-wrap: wrap; justify-content: flex-end; max-width: min(100%, 720px); }
.platform-nav nav > a:not(.button) { min-height: 44px; padding: 12px; color: var(--muted); font-size: .78rem; font-weight: 650; text-decoration: none; }
.button, .control-button { display: inline-flex; min-height: 46px; align-items: center; justify-content: center; gap: 12px; border: 1px solid var(--brand-strong); border-radius: 13px; padding: 11px 17px; color: var(--button-ink); background: var(--brand-strong); font-weight: 720; text-decoration: none; cursor: pointer; box-shadow: 0 8px 20px color-mix(in srgb, var(--brand) 17%, transparent); transition: transform 140ms ease, box-shadow 180ms ease, background 180ms ease; }
.button:hover { transform: translateY(-1px); box-shadow: 0 11px 28px color-mix(in srgb, var(--brand) 22%, transparent); }
.button:active { transform: scale(.985); }
.button:disabled { cursor: not-allowed; opacity: .46; transform: none; box-shadow: none; }
.button--compact { min-height: 42px; padding: 9px 14px; font-size: .76rem; }
.button--secondary, .control-button { color: var(--ink); border-color: var(--line-strong); background: var(--surface); box-shadow: none; }
.text-link, .text-button { min-height: 44px; padding: 11px 4px; color: var(--brand-strong); border: 0; background: none; font-weight: 700; text-decoration: underline; text-underline-offset: 4px; cursor: pointer; }
.kicker, .step-label { margin: 0; color: var(--brand); font-size: .66rem; font-weight: 820; letter-spacing: .14em; }
.platform-hero { position: relative; display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(290px, .7fr); gap: clamp(38px, 7vw, 96px); width: min(1180px, calc(100% - 40px)); min-height: 680px; align-items: center; margin: 0 auto; padding: 72px 0 100px; }
.platform-hero::before { content: ""; position: absolute; z-index: -1; inset: 5% 20% 8% -12%; border-radius: 50%; background: radial-gradient(circle, color-mix(in srgb, var(--brand) 12%, transparent), transparent 68%); filter: blur(2px); }
.hero-copy h1 { max-width: 800px; margin: 18px 0 22px; font-size: clamp(3rem, 7vw, 6.7rem); letter-spacing: -.065em; line-height: .98; }
.lead { max-width: 720px; margin: 8px 0; color: var(--muted); font-size: clamp(1rem, 1.6vw, 1.17rem); line-height: 1.75; }
.lead--en { max-width: 650px; font-size: .88rem; }
.hero-actions { display: flex; align-items: center; gap: 20px; margin-top: 30px; }
.proof-line { display: flex; flex-wrap: wrap; gap: 8px 18px; margin-top: 30px; color: var(--muted); font-size: .72rem; font-weight: 650; }
.proof-line span::before { content: "✓"; margin-right: 6px; color: var(--brand); }
.hero-system { padding: 28px; border: 1px solid var(--line); border-radius: 28px; background: color-mix(in srgb, var(--surface) 92%, transparent); box-shadow: var(--shadow); }
.system-label { margin: 0 0 22px; color: var(--muted); font-size: .62rem; font-weight: 820; letter-spacing: .14em; }
.system-node { display: flex; align-items: center; gap: 14px; padding: 15px; border: 1px solid var(--line); border-radius: 15px; background: var(--surface-soft); }
.system-node--active { border-color: color-mix(in srgb, var(--brand) 45%, var(--line)); background: var(--brand-soft); }
.system-node b { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; color: var(--brand-strong); background: var(--surface); font-size: .68rem; }
.system-node span { display: grid; }
.system-node strong { font-size: .8rem; }
.system-node small { color: var(--muted); font-size: .68rem; }
.system-line { width: 1px; height: 20px; margin-left: 31px; background: var(--line-strong); }
.system-boundary { margin: 22px 0 0; color: var(--brand-strong); font-size: .75rem; font-weight: 760; }
.platform-section { width: min(1180px, calc(100% - 40px)); margin: 0 auto; padding: 100px 0; border-top: 1px solid var(--line); }
.section-heading { max-width: 760px; margin-bottom: 42px; }
.section-heading h2 { margin: 12px 0; font-size: clamp(2rem, 4vw, 4rem); letter-spacing: -.05em; line-height: 1.08; }
.section-heading > p:not(.kicker) { color: var(--muted); }
.capability-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.capability-grid article { min-height: 280px; padding: 24px; border: 1px solid var(--line); border-radius: 19px; background: var(--surface); }
.capability-grid .index { color: var(--brand); font-size: .66rem; font-weight: 820; }
.capability-grid h3 { margin: 72px 0 10px; font-size: 1.1rem; }
.capability-grid p { color: var(--muted); font-size: .78rem; }
.capability-grid small { display: block; margin-top: 18px; color: var(--muted); font-size: .67rem; }
.operating-grid, .resource-grid { display: grid; gap: 12px; }
.operating-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.resource-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.operating-grid article, .resource-grid article { min-height: 230px; padding: 24px; border: 1px solid var(--line); border-radius: 19px; background: var(--surface); }
.role-mark { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 11px; color: var(--brand-strong); background: var(--brand-soft); font-size: .66rem; font-weight: 820; }
.operating-grid h3, .resource-grid h3 { margin: 42px 0 10px; font-size: 1.05rem; }
.operating-grid p, .resource-grid p { color: var(--muted); font-size: .76rem; }
.solution-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.solution-grid article { display: grid; grid-template-columns: 54px 1fr; gap: 18px; min-height: 170px; align-items: start; padding: 26px; border: 1px solid var(--line); border-radius: 19px; background: var(--surface); }
.solution-grid article > span, .resource-icon { display: grid; width: 48px; height: 48px; place-items: center; border-radius: 14px; color: var(--brand-strong); background: var(--brand-soft); font-weight: 820; }
.solution-grid h3 { margin: 2px 0 9px; font-size: 1rem; }
.solution-grid p { margin: 0; color: var(--muted); font-size: .76rem; }
.resource-grid h3 { margin-top: 32px; }
.co-creation-strip { display: flex; align-items: flex-end; justify-content: space-between; gap: 32px; margin-top: 16px; padding: 30px; border: 1px solid color-mix(in srgb, var(--brand) 40%, var(--line)); border-radius: 19px; background: var(--brand-soft); }
.co-creation-strip h3 { max-width: 780px; margin: 10px 0 0; font-size: clamp(1.15rem, 2.5vw, 1.75rem); line-height: 1.35; }
.co-creation-links { display: flex; flex: 0 0 auto; gap: 18px; }
.platform-section--trust { padding-bottom: 130px; }
.trust-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 56px; margin-bottom: 38px; }
.trust-statement { padding: 30px; border-left: 4px solid var(--brand); background: var(--surface); }
.trust-statement p { color: var(--muted); }
.trust-quote { color: var(--ink) !important; font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: .86rem; }
.trust-list { display: grid; gap: 18px; margin: 0; padding: 0; list-style: none; }
.trust-list li { display: grid; gap: 4px; padding-bottom: 17px; border-bottom: 1px solid var(--line); }
.trust-list strong { font-size: .88rem; }
.trust-list span { color: var(--muted); font-size: .75rem; }
.platform-footer { display: flex; justify-content: space-between; gap: 30px; padding: 34px max(20px, calc((100vw - 1180px)/2)); color: var(--muted); border-top: 1px solid var(--line); background: var(--surface); font-size: .7rem; }
.platform-footer p { display: grid; margin: 0; }
.platform-footer strong { color: var(--ink); }

.trial-nav { border-bottom: 1px solid var(--line); }
.trial-controls { flex-wrap: wrap; justify-content: flex-end; }
.control-button { min-height: 40px; padding: 8px 12px; font-size: .7rem; }
.trial-shell { width: min(1120px, calc(100% - 40px)); margin: 0 auto; padding: 54px 0 90px; }
.trial-intro { display: flex; align-items: flex-start; justify-content: space-between; gap: 40px; }
.trial-intro h1 { max-width: 790px; margin: 14px 0 12px; font-size: clamp(2.3rem, 5vw, 5.1rem); letter-spacing: -.058em; line-height: 1.02; }
.trial-intro > div > p:not(.kicker) { max-width: 700px; color: var(--muted); }
.privacy-seal { display: flex; flex: 0 0 auto; align-items: center; gap: 12px; min-width: 230px; padding: 16px; border: 1px solid color-mix(in srgb, var(--brand) 38%, var(--line)); border-radius: 16px; background: var(--brand-soft); }
.privacy-seal > span { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 50%; color: var(--surface); background: var(--brand-strong); }
.privacy-seal p { display: grid; margin: 0; }
.privacy-seal strong { font-size: .78rem; }
.privacy-seal small { color: var(--muted); font-size: .65rem; }
.step-rail { position: sticky; z-index: 4; top: 10px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 1px; margin: 46px 0 20px; overflow: hidden; border: 1px solid var(--line); border-radius: 16px; background: var(--line); box-shadow: 0 10px 30px color-mix(in srgb, var(--paper) 70%, transparent); }
.step-rail a { display: flex; min-height: 56px; align-items: center; gap: 10px; padding: 12px 16px; background: var(--surface); font-size: .74rem; font-weight: 700; text-decoration: none; }
.step-rail b { color: var(--brand); font-size: .65rem; }
.workspace-section { margin-top: 18px; padding: clamp(22px, 4vw, 42px); border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface); box-shadow: 0 10px 34px color-mix(in srgb, var(--ink) 5%, transparent); }
.workspace-heading { display: flex; justify-content: space-between; gap: 30px; margin-bottom: 28px; }
.workspace-heading h2 { margin: 8px 0 6px; font-size: clamp(1.35rem, 3vw, 2.05rem); letter-spacing: -.035em; }
.workspace-heading p:not(.step-label) { max-width: 720px; margin: 0; color: var(--muted); font-size: .78rem; }
.count-badge { align-self: flex-start; padding: 7px 11px; border-radius: 999px; color: var(--brand-strong); background: var(--brand-soft); font-size: .68rem; font-weight: 740; }
.directory-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; }
.person-card { display: grid; grid-template-columns: 38px 1fr; gap: 11px; padding: 14px; border: 1px solid var(--line); border-radius: 14px; background: var(--surface-soft); }
.person-avatar { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 12px; color: var(--brand-strong); background: var(--brand-soft); font-weight: 820; }
.person-card p { display: grid; margin: 0; }
.person-card strong { font-size: .8rem; }
.person-card small { color: var(--muted); font-size: .64rem; }
.role-assistant { border-left: 3px solid var(--gold); }
.role-prefect { border-left: 3px solid var(--brand); }
.absence-composer { display: grid; grid-template-columns: 1fr 1fr auto; align-items: end; gap: 12px; }
.absence-composer label { display: grid; gap: 7px; color: var(--muted); font-size: .68rem; font-weight: 700; }
select { width: 100%; min-height: 46px; padding: 10px 12px; color: var(--ink); border: 1px solid var(--line-strong); border-radius: 12px; background: var(--surface); }
.absence-list { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }
.absence-chip { display: inline-flex; align-items: center; gap: 8px; min-height: 40px; padding: 7px 8px 7px 12px; border: 1px solid var(--line); border-radius: 999px; color: var(--ink); background: var(--surface-soft); font-size: .7rem; }
.absence-chip button { display: grid; width: 28px; height: 28px; place-items: center; border: 0; border-radius: 50%; color: var(--danger); background: var(--surface); cursor: pointer; }
.absence-empty { margin: 0; color: var(--muted); font-size: .72rem; }
.action-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.status-line { min-height: 24px; margin: 14px 0; color: var(--brand-strong); font-size: .72rem; font-weight: 690; }
.roster-empty { display: flex; min-height: 190px; align-items: center; justify-content: center; gap: 14px; border: 1px dashed var(--line-strong); border-radius: 16px; background: var(--surface-soft); }
.roster-empty[hidden], .roster-preview[hidden] { display: none !important; }
.roster-empty > span { display: grid; width: 44px; height: 44px; place-items: center; border-radius: 13px; color: var(--brand); background: var(--surface); font-weight: 800; }
.roster-empty p { display: grid; margin: 0; }
.roster-empty small { margin-top: 4px; color: var(--muted); }
.preview-heading { display: flex; justify-content: space-between; gap: 20px; align-items: end; padding: 20px 0; }
.preview-heading h3 { margin: 6px 0 0; font-size: 1.3rem; }
.preview-heading > p { color: var(--muted); font-size: .72rem; }
.table-scroll { overflow-x: auto; border: 1px solid var(--line); border-radius: 15px; }
table { width: 100%; min-width: 830px; border-collapse: collapse; background: var(--surface); }
th, td { min-width: 125px; padding: 13px 10px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); text-align: center; }
tr:last-child th, tr:last-child td { border-bottom: 0; }
th:last-child, td:last-child { border-right: 0; }
thead th { color: var(--surface); background: var(--brand-strong); font-size: .71rem; }
tbody th { min-width: 190px; color: var(--surface); background: color-mix(in srgb, var(--brand-strong) 88%, var(--ink)); text-align: left; font-size: .7rem; }
th small { display: block; margin-top: 2px; opacity: .75; font-size: .58rem; font-weight: 500; }
td { font-size: .78rem; font-weight: 680; }
td.closed { color: var(--muted); background: var(--surface-soft); font-weight: 520; }
td.vacant { color: var(--danger); }
.policy-checks { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 14px; }
.policy-check { padding: 11px 12px; border-radius: 11px; color: var(--brand-strong); background: var(--brand-soft); font-size: .66rem; font-weight: 690; }
.trial-boundary { display: flex; gap: 12px; margin-top: 18px; padding: 18px; border: 1px solid var(--line); border-radius: 15px; color: var(--muted); background: var(--surface-soft); }
.trial-boundary > span { display: grid; flex: 0 0 auto; width: 30px; height: 30px; place-items: center; border-radius: 50%; color: var(--surface); background: var(--blue); font-weight: 800; }
.trial-boundary p { display: grid; margin: 0; font-size: .72rem; }
.trial-boundary strong { color: var(--ink); }
.noscript { position: fixed; inset: auto 20px 20px; z-index: 10; padding: 14px; border-radius: 12px; color: #fff; background: #772f2b; }

@media (max-width: 900px) {
  .platform-hero { grid-template-columns: 1fr; min-height: 0; padding-top: 50px; }
  .hero-system { max-width: 520px; }
  .capability-grid { grid-template-columns: repeat(2, 1fr); }
  .operating-grid, .resource-grid { grid-template-columns: repeat(2, 1fr); }
  .trust-layout { grid-template-columns: 1fr; }
  .directory-grid { grid-template-columns: repeat(2, 1fr); }
  .trial-intro { display: grid; }
  .privacy-seal { width: 100%; }
  .absence-composer { grid-template-columns: 1fr 1fr; }
  .absence-composer .button { grid-column: 1 / -1; }
}
@media (max-width: 680px) {
  .platform-nav, .trial-nav, .platform-hero, .platform-section, .trial-shell { width: min(100% - 24px, 1180px); }
  .platform-nav { display: grid; grid-template-columns: 1fr; align-items: flex-start; gap: 12px; padding-block: 14px; }
  .platform-controls { width: 100%; max-width: none; justify-content: flex-start; }
  .platform-nav nav > a:not(.button) { display: none; }
  .hero-copy h1 { font-size: clamp(2.8rem, 15vw, 4.5rem); }
  .hero-actions { align-items: stretch; flex-direction: column; }
  .hero-actions .button { width: 100%; }
  .capability-grid { grid-template-columns: 1fr; }
  .operating-grid, .resource-grid, .solution-grid { grid-template-columns: 1fr; }
  .co-creation-strip { align-items: flex-start; flex-direction: column; }
  .co-creation-links { flex-wrap: wrap; }
  .capability-grid article { min-height: 230px; }
  .capability-grid h3 { margin-top: 45px; }
  .platform-footer { display: grid; }
  .trial-nav { align-items: flex-start; padding: 13px 0; }
  .trial-nav .brand small { display: none; }
  .trial-controls { max-width: 55%; }
  .control-button { min-height: 44px; }
  .trial-intro h1 { font-size: clamp(2.4rem, 13vw, 4rem); }
  .step-rail { position: static; }
  .step-rail a { min-width: 0; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px; }
  .step-rail span { font-size: .67rem; }
  .workspace-section { padding: 22px 16px; }
  .workspace-heading { display: grid; }
  .directory-grid, .absence-composer, .policy-checks { grid-template-columns: 1fr; }
  .absence-composer .button { grid-column: auto; }
  .action-bar { display: grid; }
  .action-bar .button, .action-bar .text-button { width: 100%; }
  .preview-heading { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; }
}
@media (forced-colors: active) {
  .button, .control-button, .workspace-section, .person-card, .hero-system { border: 1px solid CanvasText; }
}
@media print {
  .platform-nav, .trial-nav, .step-rail, .action-bar, .trial-boundary, .platform-footer { display: none !important; }
  body { background: #fff; }
  .trial-shell { width: 100%; padding: 0; }
  .workspace-section { box-shadow: none; break-inside: avoid; }
}`;

export const TRIAL_JS = String.raw`(() => {
  'use strict';

  const STORAGE_KEY = 'sing-yin-guest-trial-v1';
  const DISPLAY_STORAGE_KEY = 'sing-yin-guest-display-v1';
  const STATE_SCHEMA = 'sing-yin-guest-trial-state-v1';
  const SESSION_TTL_MS = 30 * 60 * 1000;
  const LANGUAGES = ['zh', 'en'];
  const THEMES = ['auto', 'light', 'dark'];

  const DIRECTORY = Object.freeze([
    { id: 'a01', name: '林晨恩', role: 'assistant', className: '5A' },
    { id: 'a02', name: '陳樂言', role: 'assistant', className: '5B' },
    { id: 'a03', name: '梁澄心', role: 'assistant', className: '5C' },
    { id: 'a04', name: '周善行', role: 'assistant', className: '5D' },
    { id: 'a05', name: '何思齊', role: 'assistant', className: '5A' },
    { id: 'a06', name: '馮以恩', role: 'assistant', className: '5B' },
    { id: 'p01', name: '黃知行', role: 'prefect', className: '5A' },
    { id: 'p02', name: '李卓謙', role: 'prefect', className: '5A' },
    { id: 'p03', name: '張頌晴', role: 'prefect', className: '5B' },
    { id: 'p04', name: '鄭安澄', role: 'prefect', className: '5B' },
    { id: 'p05', name: '吳朗言', role: 'prefect', className: '5C' },
    { id: 'p06', name: '杜心悅', role: 'prefect', className: '5C' },
    { id: 'p07', name: '許樂桐', role: 'prefect', className: '5D' },
    { id: 'p08', name: '郭明謙', role: 'prefect', className: '5D' },
    { id: 'p09', name: '蔡頌恩', role: 'prefect', className: '5A' },
    { id: 'p10', name: '葉思朗', role: 'prefect', className: '5B' },
    { id: 'p11', name: '羅雅言', role: 'prefect', className: '5C' },
    { id: 'p12', name: '蘇善晴', role: 'prefect', className: '5D' },
  ]);

  const DAYS = Object.freeze([
    { code: 'MONDAY', zh: '星期一', en: 'Monday' },
    { code: 'TUESDAY', zh: '星期二', en: 'Tuesday' },
    { code: 'WEDNESDAY', zh: '星期三', en: 'Wednesday' },
    { code: 'THURSDAY', zh: '星期四', en: 'Thursday' },
    { code: 'FRIDAY', zh: '星期五', en: 'Friday' },
  ]);

  const POSTS = Object.freeze([
    { code: 'ASSIST_IN_CHARGE', zh: '助理首席導學風紀當值', en: 'Assist. in charge', role: 'assistant', open: [0, 1, 2, 3, 4] },
    { code: 'ROOM_302', zh: '302 室（自修室）', en: 'Room 302 (Study Room)', role: 'prefect', open: [0, 1, 2, 3, 4] },
    { code: 'ROOM_303_1', zh: '303 室（功課完成）— 1', en: 'Room 303 (HW Completion) — 1', role: 'prefect', open: [0, 1, 2, 3, 4] },
    { code: 'ROOM_303_2', zh: '303 室（功課完成）— 2', en: 'Room 303 (HW Completion) — 2', role: 'prefect', open: [0, 1, 2, 3, 4] },
    { code: 'ROOM_202_1', zh: '202 室（中一溫習小組）— 1', en: 'Room 202 (F1 Study Group) — 1', role: 'prefect', open: [0, 2, 3] },
    { code: 'ROOM_202_2', zh: '202 室（中一溫習小組）— 2', en: 'Room 202 (F1 Study Group) — 2', role: 'prefect', open: [0, 2, 3] },
  ]);

  const COPY = Object.freeze({
    zh: {
      title: '用虛構資料，完成一週值班表。', intro: '所有操作只留在這個分頁，30 分鐘後失效；不會接觸正式名單、伺服器資料或公平帳本。',
      privacyTitle: '裝置內試用', privacyDetail: '零伺服器寫入 · Session only', step1: '認識名單', step2: '準備請假', step3: '生成及匯出',
      directoryTitle: '虛構導學風紀名單', directoryHelp: '先理解角色分工。以下姓名、班別及資料全部為虛構，只用作產品示範。',
      prepareTitle: '登記生成前請假', prepareHelp: '這一步可以略過。加入示範請假後，生成器會避開該同學當日的崗位。', personLabel: '導學風紀', dayLabel: '日期', addAbsence: '加入示範請假',
      previewTitle: '生成、核對與匯出', previewHelp: '同一組輸入會得到同一個結果；助理首席只負責 Assist. in charge，一般導學風紀只負責房間。', generate: '生成示範值班表', download: '下載雙語 PDF', reset: '重置全部試用資料',
      emptyTitle: '值班表仍未生成', emptyHelp: '檢查名單及請假後，按「生成示範值班表」。', tableTitle: '本週導學風紀值班表', boundaryTitle: '這不是正式發布。', boundaryCopy: '試用結果不能分享成正式值班表，也不會影響任何人的 history_weight、服務時數或公平工作量。', footerCopy: '關閉分頁後，試用資料即會消失。',
      assistant: '助理首席導學風紀', prefect: '導學風紀', people: '位虛構成員', noAbsence: '尚未加入示範請假。', absent: '請假', remove: '移除', generated: '示範值班表已在此裝置生成，請核對後下載 PDF。', resetDone: '試用資料已清除。', duplicateAbsence: '這項示範請假已經存在。', pdfReady: '雙語 PDF 已在此裝置建立。', expired: '上一次試用已滿 30 分鐘，系統已自動重置。', closed: '休室', vacancy: '待補', exit: '離開試用', language: '中文 / EN', themeAuto: '外觀：自動', themeLight: '外觀：淺色', themeDark: '外觀：深色',
    },
    en: {
      title: 'Build a weekly roster with fictional data.', intro: 'Everything stays in this browser tab and expires after 30 minutes. Official data, server storage, and the fairness ledger remain untouched.',
      privacyTitle: 'On-device trial', privacyDetail: 'Zero server writes · Session only', step1: 'Meet the directory', step2: 'Prepare leave', step3: 'Generate & export',
      directoryTitle: 'Fictional prefect directory', directoryHelp: 'Start with role boundaries. Every name, class, and record below is fictional and exists only for this product trial.',
      prepareTitle: 'Declare pre-generation leave', prepareHelp: 'This step is optional. The generator will avoid assigning the selected prefect on that day.', personLabel: 'Prefect', dayLabel: 'Day', addAbsence: 'Add trial leave',
      previewTitle: 'Generate, review, and export', previewHelp: 'The same inputs produce the same result. Assistant Heads only serve Assist. in charge; ordinary Study Prefects only serve rooms.', generate: 'Generate trial roster', download: 'Download bilingual PDF', reset: 'Reset all trial data',
      emptyTitle: 'No roster generated yet', emptyHelp: 'Review the directory and leave, then choose “Generate trial roster”.', tableTitle: 'Weekly Study Prefect Duty Roster', boundaryTitle: 'This is not an official publication.', boundaryCopy: 'Trial results cannot become official share links and never affect history_weight, service hours, or the fairness ledger.', footerCopy: 'Closing this tab removes the trial data.',
      assistant: 'Assistant Head Study Prefect', prefect: 'Study Prefect', people: 'fictional members', noAbsence: 'No trial leave has been added.', absent: 'Leave', remove: 'Remove', generated: 'The trial roster was generated on this device. Review it, then download the PDF.', resetDone: 'Trial data was cleared.', duplicateAbsence: 'That trial leave already exists.', pdfReady: 'The bilingual PDF was created on this device.', expired: 'The previous 30-minute trial expired and was reset.', closed: 'Closed', vacancy: 'Vacancy', exit: 'Leave trial', language: '中文 / EN', themeAuto: 'Theme: Auto', themeLight: 'Theme: Light', themeDark: 'Theme: Dark',
    },
  });

  function displayPreferences() {
    try {
      const stored = JSON.parse(sessionStorage.getItem(DISPLAY_STORAGE_KEY) || 'null');
      if (stored && LANGUAGES.includes(stored.language) && THEMES.includes(stored.theme)) return stored;
    } catch { /* Defaults remain safe. */ }
    return { language: 'zh', theme: 'auto' };
  }

  function freshState(now) {
    const display = displayPreferences();
    return { schema: STATE_SCHEMA, createdAt: now, expiresAt: now + SESSION_TTL_MS, language: display.language, theme: display.theme, absences: [], roster: null, weekStart: nextMondayIso(new Date(now)) };
  }

  function safeLoad() {
    const now = Date.now();
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return { state: freshState(now), expired: false };
      const parsed = JSON.parse(raw);
      const valid = parsed && parsed.schema === STATE_SCHEMA && Number.isFinite(parsed.createdAt) && Number.isFinite(parsed.expiresAt) && parsed.expiresAt > now && parsed.expiresAt - parsed.createdAt === SESSION_TTL_MS && LANGUAGES.includes(parsed.language) && THEMES.includes(parsed.theme) && Array.isArray(parsed.absences) && parsed.absences.every(validAbsenceShape);
      if (!valid) {
        sessionStorage.removeItem(STORAGE_KEY);
        return { state: freshState(now), expired: Boolean(parsed && parsed.expiresAt <= now) };
      }
      parsed.roster = validRosterShape(parsed.roster) ? parsed.roster : null;
      return { state: parsed, expired: false };
    } catch {
      return { state: freshState(now), expired: false };
    }
  }

  function safeSave() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      sessionStorage.setItem(DISPLAY_STORAGE_KEY, JSON.stringify({ language: state.language, theme: state.theme }));
    } catch { /* Memory state remains available. */ }
  }

  function validAbsenceShape(item) {
    return Boolean(item && typeof item === 'object' && DIRECTORY.some(person => person.id === item.personId) && Number.isInteger(item.dayIndex) && item.dayIndex >= 0 && item.dayIndex < DAYS.length);
  }

  function validRosterShape(roster) {
    if (roster === null) return true;
    if (!roster || typeof roster !== 'object' || !/^\d{4}-\d{2}-\d{2}$/.test(roster.weekStart) || !Array.isArray(roster.rows) || roster.rows.length !== POSTS.length) return false;
    return roster.rows.every((row, rowIndex) => row && row.code === POSTS[rowIndex].code && Array.isArray(row.cells) && row.cells.length === DAYS.length && row.cells.every(cell => {
      if (!cell || !['assigned', 'closed', 'vacant'].includes(cell.status)) return false;
      if (cell.status !== 'assigned') return true;
      const person = DIRECTORY.find(candidate => candidate.id === cell.personId);
      return Boolean(person && person.role === POSTS[rowIndex].role && cell.name === person.name);
    }));
  }

  function pad(value) { return String(value).padStart(2, '0'); }
  function isoDate(date) { return String(date.getFullYear()) + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()); }
  function nextMondayIso(date) {
    const copy = new Date(date.getFullYear(), date.getMonth(), date.getDate());
    const delta = (8 - copy.getDay()) % 7 || 7;
    copy.setDate(copy.getDate() + delta);
    return isoDate(copy);
  }
  function addDays(iso, days) { const parts = iso.split('-').map(Number); const date = new Date(parts[0], parts[1] - 1, parts[2]); date.setDate(date.getDate() + days); return isoDate(date); }
  function formatShort(iso) { const parts = iso.split('-'); return parts[2] + '/' + parts[1]; }
  function personById(id) { return DIRECTORY.find(person => person.id === id); }
  function text(key) { return COPY[state.language][key] || COPY.zh[key] || key; }
  function roleLabel(role) { return role === 'assistant' ? text('assistant') : text('prefect'); }
  function absenceKey(personId, dayIndex) { return personId + '|' + String(dayIndex); }

  function generateRoster() {
    const dutyCounts = Object.fromEntries(DIRECTORY.map(person => [person.id, 0]));
    const previousDay = new Set();
    const rows = POSTS.map(post => ({ code: post.code, zh: post.zh, en: post.en, cells: [] }));
    const absenceSet = new Set(state.absences.map(item => absenceKey(item.personId, item.dayIndex)));

    for (let dayIndex = 0; dayIndex < DAYS.length; dayIndex += 1) {
      const today = new Set();
      for (let rowIndex = 0; rowIndex < POSTS.length; rowIndex += 1) {
        const post = POSTS[rowIndex];
        if (!post.open.includes(dayIndex)) {
          rows[rowIndex].cells.push({ status: 'closed' });
          continue;
        }
        const pool = DIRECTORY
          .filter(person => person.role === post.role)
          .filter(person => !today.has(person.id))
          .filter(person => !previousDay.has(person.id))
          .filter(person => !absenceSet.has(absenceKey(person.id, dayIndex)))
          .sort((left, right) => dutyCounts[left.id] - dutyCounts[right.id] || left.id.localeCompare(right.id));
        const selected = pool[0];
        if (!selected) {
          rows[rowIndex].cells.push({ status: 'vacant' });
          continue;
        }
        today.add(selected.id);
        dutyCounts[selected.id] += 1;
        rows[rowIndex].cells.push({ status: 'assigned', personId: selected.id, name: selected.name });
      }
      previousDay.clear();
      today.forEach(id => previousDay.add(id));
    }
    return { weekStart: state.weekStart, rows, generatedAt: Date.now() };
  }

  function validateRoster(roster) {
    const errors = [];
    const previous = new Set();
    DAYS.forEach((day, dayIndex) => {
      const today = new Set();
      roster.rows.forEach((row, rowIndex) => {
        const cell = row.cells[dayIndex];
        if (!cell || cell.status !== 'assigned') return;
        const person = personById(cell.personId);
        if (!person || person.role !== POSTS[rowIndex].role) errors.push('role');
        if (today.has(cell.personId)) errors.push('duplicate');
        if (previous.has(cell.personId)) errors.push('consecutive');
        if (state.absences.some(item => item.personId === cell.personId && item.dayIndex === dayIndex)) errors.push('absence');
        today.add(cell.personId);
      });
      previous.clear();
      today.forEach(id => previous.add(id));
    });
    return errors;
  }

  let loaded = safeLoad();
  let state = loaded.state;
  let expiryTimeoutId = null;
  const elements = {
    directoryGrid: document.getElementById('directoryGrid'), directoryCount: document.getElementById('directoryCount'),
    person: document.getElementById('absencePerson'), day: document.getElementById('absenceDay'), absenceList: document.getElementById('absenceList'),
    status: document.getElementById('trialStatus'), empty: document.getElementById('rosterEmpty'), preview: document.getElementById('rosterPreview'),
    table: document.getElementById('rosterTable'), weekRange: document.getElementById('weekRange'), policyChecks: document.getElementById('policyChecks'),
    download: document.getElementById('downloadPdf'), expiry: document.getElementById('expiryText'),
  };

  function applyLanguage() {
    document.documentElement.dataset.lang = state.language;
    document.documentElement.lang = state.language === 'zh' ? 'zh-Hant-HK' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(element => { element.textContent = text(element.dataset.i18n); });
    document.getElementById('languageToggle').textContent = text('language');
    renderDirectory(); renderSelects(); renderAbsences(); renderRoster(); renderExpiry();
  }

  function applyTheme() {
    document.documentElement.dataset.theme = state.theme;
    const key = state.theme === 'light' ? 'themeLight' : state.theme === 'dark' ? 'themeDark' : 'themeAuto';
    document.getElementById('themeToggleTrial').textContent = text(key);
  }

  function renderDirectory() {
    elements.directoryGrid.replaceChildren();
    DIRECTORY.forEach(person => {
      const card = document.createElement('article');
      card.className = 'person-card role-' + person.role;
      const avatar = document.createElement('span'); avatar.className = 'person-avatar'; avatar.textContent = person.name.slice(-1);
      const copy = document.createElement('p');
      const name = document.createElement('strong'); name.textContent = person.name;
      const detail = document.createElement('small'); detail.textContent = roleLabel(person.role) + ' · ' + person.className;
      copy.append(name, detail); card.append(avatar, copy); elements.directoryGrid.append(card);
    });
    elements.directoryCount.textContent = String(DIRECTORY.length) + ' ' + text('people');
  }

  function renderSelects() {
    const selectedPerson = elements.person.value;
    const selectedDay = elements.day.value;
    elements.person.replaceChildren(); elements.day.replaceChildren();
    DIRECTORY.forEach(person => { const option = document.createElement('option'); option.value = person.id; option.textContent = person.name + ' · ' + roleLabel(person.role) + ' · ' + person.className; elements.person.append(option); });
    DAYS.forEach((day, index) => { const option = document.createElement('option'); option.value = String(index); option.textContent = (state.language === 'zh' ? day.zh : day.en) + ' · ' + formatShort(addDays(state.weekStart, index)); elements.day.append(option); });
    if (DIRECTORY.some(person => person.id === selectedPerson)) elements.person.value = selectedPerson;
    if (/^[0-4]$/.test(selectedDay)) elements.day.value = selectedDay;
  }

  function renderAbsences() {
    elements.absenceList.replaceChildren();
    if (!state.absences.length) { const empty = document.createElement('p'); empty.className = 'absence-empty'; empty.textContent = text('noAbsence'); elements.absenceList.append(empty); return; }
    state.absences.forEach((item, index) => {
      const person = personById(item.personId); if (!person) return;
      const chip = document.createElement('span'); chip.className = 'absence-chip';
      const label = document.createElement('span'); label.textContent = person.name + ' · ' + (state.language === 'zh' ? DAYS[item.dayIndex].zh : DAYS[item.dayIndex].en) + ' · ' + text('absent');
      const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×'; remove.setAttribute('aria-label', text('remove') + ' ' + person.name);
      remove.addEventListener('click', () => { if (!ensureUnexpired()) return; state.absences.splice(index, 1); state.roster = null; safeSave(); renderAbsences(); renderRoster(); setStatus(''); });
      chip.append(label, remove); elements.absenceList.append(chip);
    });
  }

  function renderRoster() {
    const roster = state.roster;
    elements.download.disabled = !roster;
    elements.empty.hidden = Boolean(roster); elements.preview.hidden = !roster;
    if (!roster) return;
    const thead = document.createElement('thead'); const header = document.createElement('tr');
    const duty = document.createElement('th'); duty.scope = 'col'; duty.textContent = state.language === 'zh' ? '值班位置' : 'Duty position'; header.append(duty);
    DAYS.forEach((day, index) => { const th = document.createElement('th'); th.scope = 'col'; th.textContent = state.language === 'zh' ? day.zh : day.en; const small = document.createElement('small'); small.textContent = formatShort(addDays(roster.weekStart, index)); th.append(small); header.append(th); });
    thead.append(header);
    const tbody = document.createElement('tbody');
    roster.rows.forEach((row, rowIndex) => { const tr = document.createElement('tr'); const th = document.createElement('th'); th.scope = 'row'; th.textContent = state.language === 'zh' ? row.zh : row.en; const time = document.createElement('small'); time.textContent = '15:40–17:00'; th.append(time); tr.append(th);
      row.cells.forEach(cell => { const td = document.createElement('td'); if (cell.status === 'assigned') td.textContent = cell.name; else { td.className = cell.status; td.textContent = cell.status === 'closed' ? text('closed') : text('vacancy'); } tr.append(td); }); tbody.append(tr); });
    elements.table.replaceChildren(thead, tbody);
    elements.weekRange.textContent = roster.weekStart + ' — ' + addDays(roster.weekStart, 4);
    const checks = state.language === 'zh' ? ['✓ 角色限制已核對', '✓ 同日沒有重複', '✓ 沒有連續生成當值'] : ['✓ Role boundaries checked', '✓ No same-day duplicates', '✓ No consecutive generated duties'];
    elements.policyChecks.replaceChildren(...checks.map(value => { const item = document.createElement('div'); item.className = 'policy-check'; item.textContent = value; return item; }));
  }

  function renderExpiry() {
    const minutes = Math.max(0, Math.ceil((state.expiresAt - Date.now()) / 60000));
    elements.expiry.textContent = state.language === 'zh' ? '本分頁試用剩餘約 ' + minutes + ' 分鐘' : 'About ' + minutes + ' minutes remain in this tab';
  }

  function setStatus(message) { elements.status.textContent = message; }

  function scheduleExpiry() {
    if (expiryTimeoutId !== null) clearTimeout(expiryTimeoutId);
    const delay = Math.max(0, state.expiresAt - Date.now());
    expiryTimeoutId = setTimeout(() => { expireTrialIfNeeded(); }, Math.min(delay + 25, 2_147_483_647));
  }

  function expireTrialIfNeeded() {
    if (Date.now() < state.expiresAt) { scheduleExpiry(); return false; }
    const language = state.language;
    const theme = state.theme;
    try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* In-memory expiry still succeeds. */ }
    state = freshState(Date.now());
    state.language = LANGUAGES.includes(language) ? language : 'zh';
    state.theme = THEMES.includes(theme) ? theme : 'auto';
    safeSave(); applyLanguage(); applyTheme(); setStatus(text('expired')); scheduleExpiry();
    return true;
  }

  function ensureUnexpired() { return !expireTrialIfNeeded(); }

  document.getElementById('addAbsence').addEventListener('click', () => {
    if (!ensureUnexpired()) return;
    const item = { personId: elements.person.value, dayIndex: Number(elements.day.value) };
    if (state.absences.some(existing => existing.personId === item.personId && existing.dayIndex === item.dayIndex)) { setStatus(text('duplicateAbsence')); return; }
    state.absences.push(item); state.absences.sort((a, b) => a.dayIndex - b.dayIndex || a.personId.localeCompare(b.personId)); state.roster = null; safeSave(); renderAbsences(); renderRoster(); setStatus('');
  });

  document.getElementById('generateRoster').addEventListener('click', () => {
    if (!ensureUnexpired()) return;
    state.roster = generateRoster();
    const errors = validateRoster(state.roster);
    if (errors.length) { state.roster = null; setStatus(state.language === 'zh' ? '無法建立安全的示範值班表，請重置後再試。' : 'A safe trial roster could not be built. Reset and try again.'); renderRoster(); return; }
    safeSave(); renderRoster(); setStatus(text('generated')); elements.preview.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' });
  });

  document.getElementById('languageToggle').addEventListener('click', () => { if (!ensureUnexpired()) return; state.language = state.language === 'zh' ? 'en' : 'zh'; safeSave(); applyLanguage(); applyTheme(); });
  document.getElementById('themeToggleTrial').addEventListener('click', () => { if (!ensureUnexpired()) return; state.theme = THEMES[(THEMES.indexOf(state.theme) + 1) % THEMES.length]; safeSave(); applyTheme(); });
  document.getElementById('resetTrial').addEventListener('click', () => { const language = state.language; const theme = state.theme; try { sessionStorage.removeItem(STORAGE_KEY); } catch { /* In-memory reset still succeeds. */ } state = freshState(Date.now()); state.language = language; state.theme = theme; safeSave(); applyLanguage(); applyTheme(); setStatus(text('resetDone')); scheduleExpiry(); });

  function drawText(ctx, value, x, y, options) {
    const opts = options || {}; ctx.save(); ctx.fillStyle = opts.color || '#182321'; ctx.font = (opts.weight || 500) + ' ' + (opts.size || 24) + 'px -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang HK", "Microsoft JhengHei", sans-serif'; ctx.textAlign = opts.align || 'left'; ctx.textBaseline = opts.baseline || 'alphabetic';
    const maxWidth = opts.maxWidth || 0; let textValue = String(value); if (maxWidth && ctx.measureText(textValue).width > maxWidth) { while (textValue.length > 1 && ctx.measureText(textValue + '…').width > maxWidth) textValue = textValue.slice(0, -1); textValue += '…'; }
    ctx.fillText(textValue, x, y); ctx.restore();
  }

  function rosterCanvas(roster) {
    const canvas = document.createElement('canvas'); canvas.width = 2339; canvas.height = 1654; const ctx = canvas.getContext('2d', { alpha: false });
    ctx.fillStyle = '#fffef9'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#176b67'; ctx.fillRect(0, 0, canvas.width, 20);
    drawText(ctx, 'SING YIN SECONDARY SCHOOL', 1169, 100, { size: 24, weight: 750, align: 'center', color: '#176b67' });
    drawText(ctx, '導學風紀值班表 · STUDY PREFECT DUTY ROSTER', 1169, 160, { size: 50, weight: 750, align: 'center' });
    drawText(ctx, '互動試用 · FICTIONAL DATA · ' + roster.weekStart + ' — ' + addDays(roster.weekStart, 4), 1169, 207, { size: 23, align: 'center', color: '#66706c' });
    const left = 90; const top = 290; const tableWidth = 2159; const firstCol = 520; const dayCol = (tableWidth - firstCol) / 5; const rowHeight = 164; const headerHeight = 125;
    ctx.fillStyle = '#0d514e'; ctx.fillRect(left, top, tableWidth, headerHeight);
    drawText(ctx, '值班位置 · Duty position', left + firstCol / 2, top + 68, { size: 24, weight: 700, align: 'center', color: '#ffffff' });
    DAYS.forEach((day, index) => { const x = left + firstCol + dayCol * index; drawText(ctx, day.zh + ' · ' + day.en, x + dayCol / 2, top + 49, { size: 21, weight: 700, align: 'center', color: '#ffffff', maxWidth: dayCol - 20 }); drawText(ctx, formatShort(addDays(roster.weekStart, index)), x + dayCol / 2, top + 88, { size: 18, align: 'center', color: '#dcece8' }); });
    roster.rows.forEach((row, rowIndex) => { const y = top + headerHeight + rowHeight * rowIndex; ctx.fillStyle = '#176b67'; ctx.fillRect(left, y, firstCol, rowHeight); drawText(ctx, row.zh, left + 24, y + 63, { size: 24, weight: 700, color: '#ffffff', maxWidth: firstCol - 48 }); drawText(ctx, row.en, left + 24, y + 102, { size: 18, color: '#dcece8', maxWidth: firstCol - 48 }); drawText(ctx, '15:40–17:00', left + 24, y + 134, { size: 17, color: '#dcece8' });
      row.cells.forEach((cell, dayIndex) => { const x = left + firstCol + dayCol * dayIndex; ctx.fillStyle = (rowIndex + dayIndex) % 2 ? '#f2f5ef' : '#fffef9'; if (cell.status === 'closed') ctx.fillStyle = '#e8ecea'; ctx.fillRect(x, y, dayCol, rowHeight); const label = cell.status === 'assigned' ? cell.name : cell.status === 'closed' ? '休室 · Closed' : '待補 · Vacancy'; drawText(ctx, label, x + dayCol / 2, y + rowHeight / 2 + 8, { size: cell.status === 'assigned' ? 27 : 21, weight: cell.status === 'assigned' ? 700 : 550, align: 'center', color: cell.status === 'vacant' ? '#9b3f35' : cell.status === 'closed' ? '#66706c' : '#182321', maxWidth: dayCol - 22 }); }); });
    ctx.strokeStyle = '#aeb9b3'; ctx.lineWidth = 2; ctx.strokeRect(left, top, tableWidth, headerHeight + rowHeight * roster.rows.length); for (let index = 0; index <= 5; index += 1) { const x = index === 0 ? left : left + firstCol + dayCol * (index - 1); ctx.beginPath(); ctx.moveTo(x, top); ctx.lineTo(x, top + headerHeight + rowHeight * roster.rows.length); ctx.stroke(); } for (let index = 0; index <= roster.rows.length; index += 1) { const y = top + headerHeight + rowHeight * index; ctx.beginPath(); ctx.moveTo(left, y); ctx.lineTo(left + tableWidth, y); ctx.stroke(); }
    drawText(ctx, '全部姓名及資料均為虛構 · All names and records are fictional · Browser-only trial', 1169, 1535, { size: 20, align: 'center', color: '#66706c' });
    return canvas;
  }

  function ascii(value) { return new TextEncoder().encode(value); }
  function joinBytes(parts) { const length = parts.reduce((sum, part) => sum + part.length, 0); const output = new Uint8Array(length); let offset = 0; parts.forEach(part => { output.set(part, offset); offset += part.length; }); return output; }
  function jpegPdf(jpeg, width, height) {
    const parts = []; const offsets = [0]; let position = 0; const push = bytes => { parts.push(bytes); position += bytes.length; }; const pushText = value => push(ascii(value));
    pushText('%PDF-1.4\n%\xE2\xE3\xCF\xD3\n');
    const object = (number, bodyParts) => { offsets[number] = position; pushText(String(number) + ' 0 obj\n'); bodyParts.forEach(push); pushText('\nendobj\n'); };
    object(1, [ascii('<< /Type /Catalog /Pages 2 0 R >>')]);
    object(2, [ascii('<< /Type /Pages /Kids [3 0 R] /Count 1 >>')]);
    object(3, [ascii('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 841.89 595.28] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>')]);
    object(4, [ascii('<< /Type /XObject /Subtype /Image /Width ' + width + ' /Height ' + height + ' /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ' + jpeg.length + ' >>\nstream\n'), jpeg, ascii('\nendstream')]);
    const content = ascii('q 841.89 0 0 595.28 0 0 cm /Im0 Do Q');
    object(5, [ascii('<< /Length ' + content.length + ' >>\nstream\n'), content, ascii('\nendstream')]);
    const xref = position; pushText('xref\n0 6\n0000000000 65535 f \n'); for (let index = 1; index <= 5; index += 1) pushText(String(offsets[index]).padStart(10, '0') + ' 00000 n \n'); pushText('trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n' + String(xref) + '\n%%EOF');
    return joinBytes(parts);
  }

  function canvasJpeg(canvas) { return new Promise((resolve, reject) => canvas.toBlob(blob => { if (!blob) { reject(new Error('jpeg')); return; } blob.arrayBuffer().then(buffer => resolve(new Uint8Array(buffer)), reject); }, 'image/jpeg', .95)); }

  document.getElementById('downloadPdf').addEventListener('click', async () => {
    if (!ensureUnexpired()) return;
    if (!state.roster) return;
    const button = elements.download; button.disabled = true; button.setAttribute('aria-busy', 'true');
    try { const canvas = rosterCanvas(state.roster); const jpeg = await canvasJpeg(canvas); const pdf = jpegPdf(jpeg, canvas.width, canvas.height); const url = URL.createObjectURL(new Blob([pdf], { type: 'application/pdf' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'SYSS_Guest_Trial_Roster_' + state.roster.weekStart + '_Bilingual.pdf'; document.body.append(anchor); anchor.click(); anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); setStatus(text('pdfReady')); }
    catch { setStatus(state.language === 'zh' ? 'PDF 建立失敗，請再試一次。' : 'The PDF could not be created. Please try again.'); }
    finally { button.disabled = false; button.removeAttribute('aria-busy'); }
  });

  safeSave(); applyLanguage(); applyTheme(); scheduleExpiry();
  setInterval(() => { if (ensureUnexpired()) renderExpiry(); }, 60_000);
  if (loaded.expired) setStatus(text('expired'));
})();`;
