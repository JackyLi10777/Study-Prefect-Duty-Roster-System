const SHARE_SCHEMA = 'sing-yin-public-roster-v1';
const SHARE_KEY_PREFIX = 'share:';
const MAX_ADMIN_BODY_BYTES = 196_608;
const MAX_VIEW_BODY_BYTES = 2_048;
const MAX_SHARE_LIFETIME_MS = 31 * 24 * 60 * 60 * 1_000;
const MIN_SHARE_LIFETIME_MS = 60 * 1_000;
const MAX_ACCESS_JWT_BYTES = 32_768;
const ACCESS_JWKS_CACHE_TTL_MS = 5 * 60 * 1_000;
const ACCESS_JWKS_MIN_REFRESH_MS = 60 * 1_000;
const ACCESS_JWKS_MAX_BYTES = 65_536;
const ACCESS_COOKIE_NAME = 'CF_Authorization';
const accessJwksCache = new Map();

const SECURITY_HEADERS = Object.freeze({
  'Cache-Control': 'no-store, max-age=0',
  'Content-Security-Policy': [
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "connect-src 'self'",
    "img-src 'self' data:",
    "font-src 'none'",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "manifest-src 'none'",
    'upgrade-insecure-requests',
  ].join('; '),
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet',
});

const VIEWER_HTML = `<!doctype html>
<html lang="zh-Hant-HK">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <title>導學風紀值班表 · Study Prefect Duty Roster</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/viewer.css">
</head>
<body>
  <header class="site-header">
    <div class="brand-mark" aria-hidden="true">SY</div>
    <div>
      <p class="eyebrow">SING YIN SECONDARY SCHOOL</p>
      <p class="brand-title">導學風紀值班表</p>
      <p class="brand-subtitle" lang="en">Study Prefect Duty Roster</p>
    </div>
  </header>

  <main class="page-shell">
    <section id="guestState" class="state-card state-card--guest" hidden>
      <div class="state-icon state-icon--welcome" aria-hidden="true">閱</div>
      <p class="eyebrow">PUBLIC ROSTER VIEWER</p>
      <h1>歡迎使用導學風紀值班表</h1>
      <p>如你收到值班表分享連結，請直接開啟該連結。分享內容只供查看，不能修改學校資料。</p>
      <p class="state-english" lang="en">Open the share link issued to you to view a published roster. Public links are read-only.</p>
      <a class="admin-login" href="/auth/login">管理員登入 <span lang="en">· Admin login</span></a>
    </section>

    <section id="loadingState" class="state-card" aria-live="polite" aria-busy="true">
      <span class="state-spinner" aria-hidden="true"></span>
      <h1>正在安全開啟值班表</h1>
      <p lang="en">Opening the roster securely…</p>
    </section>

    <section id="errorState" class="state-card state-card--error" hidden role="alert">
      <div class="state-icon" aria-hidden="true">!</div>
      <h1 id="errorTitle">未能開啟這份值班表</h1>
      <p id="errorMessage">連結可能不完整、已到期或已由首席導學風紀撤銷。</p>
      <p class="state-english" lang="en">This link may be incomplete, expired, or revoked. Please ask the Head Study Prefect for a new link.</p>
    </section>

    <article id="rosterState" class="roster-card" hidden>
      <header class="roster-heading">
        <div>
          <p class="eyebrow">PUBLISHED · READ ONLY</p>
          <h1 id="rosterTitleZh">本週導學風紀值班表</h1>
          <p id="rosterTitleEn" class="roster-title-en" lang="en">Weekly Study Prefect Duty Roster</p>
        </div>
        <div class="status-chip">
          <span class="status-dot" aria-hidden="true"></span>
          <span>已發布 · Published</span>
        </div>
      </header>

      <div class="roster-meta">
        <div>
          <span class="meta-label">值班週 · Week</span>
          <strong id="weekLabel">—</strong>
        </div>
        <div>
          <span class="meta-label">連結有效期 · Link valid until</span>
          <strong id="expiryLabel">—</strong>
        </div>
      </div>

      <div class="table-scroll" tabindex="0" aria-label="值班表，可左右捲動 · Roster table, horizontally scrollable">
        <table id="rosterTable">
          <caption class="sr-only">導學風紀每週值班表 · Weekly Study Prefect Duty Roster</caption>
        </table>
      </div>

      <aside class="viewer-note">
        <p>這是唯讀版本。如有更改，請以首席導學風紀最新發布的連結為準。</p>
        <p lang="en">Read-only copy. If duties change, use the latest link issued by the Head Study Prefect.</p>
      </aside>
    </article>
  </main>

  <footer class="site-footer">
    <span>不是要受人的服事，乃是要服事人。</span>
    <span lang="en">Not to be served, but to serve.</span>
  </footer>
  <script type="module" src="/viewer.js"></script>
</body>
</html>`;

const VIEWER_CSS = `:root {
  color-scheme: light dark;
  --canvas: #f3f1ec;
  --surface: #fffefa;
  --surface-muted: #f7f5ef;
  --ink: #1f2927;
  --ink-muted: #5d6966;
  --line: #d8ddd9;
  --line-strong: #b9c4bf;
  --brand: #176d68;
  --brand-soft: #e5f0ed;
  --blue: #315f91;
  --danger: #9d3e36;
  --danger-soft: #f9ebe8;
  --shadow: 0 24px 64px rgba(31, 41, 39, 0.11);
  --radius-large: 24px;
  --radius-medium: 14px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
}

* { box-sizing: border-box; }

html { min-width: 320px; background: var(--canvas); }

body {
  min-height: 100vh;
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at 8% 4%, rgba(23, 109, 104, 0.08), transparent 28rem),
    var(--canvas);
  display: flex;
  flex-direction: column;
}

button, input, select, textarea { font: inherit; }

.site-header,
.page-shell,
.site-footer {
  width: min(1180px, calc(100% - 40px));
  margin-inline: auto;
}

.site-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-block: 28px 18px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: var(--surface);
  color: var(--brand);
  font-weight: 750;
  letter-spacing: -0.04em;
  box-shadow: 0 8px 22px rgba(31, 41, 39, 0.08);
}

.eyebrow {
  margin: 0 0 3px;
  color: var(--ink-muted);
  font-size: 0.68rem;
  font-weight: 760;
  letter-spacing: 0.13em;
}

.brand-title { margin: 0; font-size: 1rem; font-weight: 720; }
.brand-subtitle { margin: 2px 0 0; color: var(--ink-muted); font-size: 0.76rem; }

.page-shell { flex: 1; padding-block: 18px 42px; }

.state-card,
.roster-card {
  border: 1px solid var(--line);
  border-radius: var(--radius-large);
  background: color-mix(in srgb, var(--surface) 96%, transparent);
  box-shadow: var(--shadow);
}

.state-card {
  min-height: 350px;
  padding: 72px 24px;
  text-align: center;
  display: grid;
  align-content: center;
  justify-items: center;
}

.state-card[hidden],
.roster-card[hidden] { display: none; }

.state-card h1 { margin: 20px 0 7px; font-size: clamp(1.35rem, 3vw, 1.8rem); }
.state-card p { max-width: 42rem; margin: 0; color: var(--ink-muted); line-height: 1.65; }
.state-english { margin-top: 8px !important; }

.state-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--line);
  border-top-color: var(--brand);
  border-radius: 50%;
  animation: spin 900ms linear infinite;
}

.state-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: var(--danger-soft);
  color: var(--danger);
  font-size: 1.25rem;
  font-weight: 800;
}

.state-icon--welcome {
  background: var(--brand-soft);
  color: var(--brand);
}

.admin-login {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  margin-top: 28px;
  padding: 10px 18px;
  border: 1px solid color-mix(in srgb, var(--blue) 36%, var(--line));
  border-radius: 999px;
  background: var(--surface);
  color: var(--blue);
  font-size: 0.84rem;
  font-weight: 720;
  text-decoration: none;
  transition: border-color 140ms ease, background-color 140ms ease, transform 140ms ease;
}

.admin-login:hover {
  border-color: var(--blue);
  background: color-mix(in srgb, var(--blue) 8%, var(--surface));
  transform: translateY(-1px);
}

.admin-login:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--blue) 42%, transparent);
  outline-offset: 3px;
}

.guest-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.roster-card { overflow: hidden; }

.roster-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 34px 36px 28px;
  border-bottom: 1px solid var(--line);
}

.roster-heading h1 {
  margin: 3px 0 0;
  font-size: clamp(1.65rem, 4vw, 2.4rem);
  line-height: 1.18;
  letter-spacing: -0.025em;
}

.roster-title-en { margin: 7px 0 0; color: var(--ink-muted); font-size: 1rem; }

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex: none;
  min-height: 34px;
  padding: 7px 12px;
  border: 1px solid color-mix(in srgb, var(--brand) 28%, var(--line));
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 0.78rem;
  font-weight: 720;
}

.status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

.roster-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
  border-bottom: 1px solid var(--line);
}

.roster-meta > div { padding: 18px 36px; background: var(--surface-muted); }
.meta-label { display: block; margin-bottom: 5px; color: var(--ink-muted); font-size: 0.72rem; }
.roster-meta strong { font-size: 0.96rem; font-variant-numeric: tabular-nums; }

.table-scroll { overflow-x: auto; outline: none; scrollbar-color: var(--line-strong) transparent; }
.table-scroll:focus-visible { box-shadow: inset 0 0 0 3px color-mix(in srgb, var(--blue) 70%, transparent); }

table {
  width: 100%;
  min-width: 900px;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}

th, td { border-right: 1px solid var(--line); border-bottom: 1px solid var(--line); }
th:last-child, td:last-child { border-right: 0; }
tbody tr:last-child th, tbody tr:last-child td { border-bottom: 0; }

thead th {
  padding: 15px 12px;
  background: #254d4a;
  color: #fff;
  text-align: center;
  font-size: 0.78rem;
  font-weight: 720;
  line-height: 1.38;
}

thead th:first-child { width: 236px; text-align: left; padding-left: 22px; }

.day-en,
.day-date,
.duty-en,
.duty-time {
  display: block;
  margin-top: 3px;
  color: inherit;
  font-size: 0.68rem;
  font-weight: 520;
  opacity: 0.75;
}

tbody th {
  padding: 15px 18px 15px 22px;
  background: color-mix(in srgb, var(--brand-soft) 68%, var(--surface));
  text-align: left;
  font-size: 0.84rem;
  font-weight: 720;
  line-height: 1.35;
}

tbody td {
  height: 76px;
  padding: 13px 10px;
  background: var(--surface);
  text-align: center;
  vertical-align: middle;
}

.prefect-name { display: block; font-size: 1rem; font-weight: 740; letter-spacing: 0.025em; }
.cell-status { display: block; color: var(--ink-muted); font-size: 0.76rem; line-height: 1.45; }
.cell--closed { background: color-mix(in srgb, var(--surface-muted) 88%, var(--line)); }
.cell--vacant { background: color-mix(in srgb, #fff1d5 70%, var(--surface)); }
.cell--vacant .cell-status { color: #845b19; font-weight: 680; }

.viewer-note {
  margin: 0;
  padding: 20px 36px 24px;
  border-top: 1px solid var(--line);
  background: var(--surface-muted);
  color: var(--ink-muted);
  font-size: 0.77rem;
  line-height: 1.6;
}

.viewer-note p { margin: 0; }
.viewer-note p + p { margin-top: 3px; }

.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-block: 18px 30px;
  border-top: 1px solid var(--line);
  color: var(--ink-muted);
  font-size: 0.72rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-color-scheme: dark) {
  :root {
    --canvas: #0c1217;
    --surface: #121b21;
    --surface-muted: #172128;
    --ink: #edf3f0;
    --ink-muted: #a8b6b1;
    --line: #2b383d;
    --line-strong: #435258;
    --brand: #80c9c0;
    --brand-soft: #173331;
    --blue: #8db6df;
    --danger: #f0a29a;
    --danger-soft: #412421;
    --shadow: 0 28px 76px rgba(0, 0, 0, 0.36);
  }

  body {
    background:
      radial-gradient(circle at 8% 4%, rgba(128, 201, 192, 0.08), transparent 28rem),
      var(--canvas);
  }

  thead th { background: #193b3a; }
  .cell--vacant { background: color-mix(in srgb, #4a3719 62%, var(--surface)); }
  .cell--vacant .cell-status { color: #e7c27e; }
}

@media (max-width: 700px) {
  .site-header,
  .page-shell,
  .site-footer { width: min(100% - 24px, 1180px); }

  .site-header { padding-top: 18px; }
  .page-shell { padding-top: 8px; }
  .roster-heading { display: grid; padding: 26px 22px 22px; }
  .status-chip { justify-self: start; }
  .roster-meta { grid-template-columns: 1fr; }
  .roster-meta > div { padding: 15px 22px; }
  .viewer-note { padding-inline: 22px; }
  .site-footer { display: grid; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

@media print {
  :root {
    color-scheme: light;
    --canvas: #fff;
    --surface: #fff;
    --surface-muted: #f7f7f4;
    --ink: #111;
    --ink-muted: #484848;
    --line: #aeb5b1;
    --line-strong: #767f7b;
    --brand: #145e5a;
    --brand-soft: #e9f0ee;
    --shadow: none;
  }

  @page { size: A4 landscape; margin: 10mm; }
  body { min-height: auto; background: #fff; print-color-adjust: exact; -webkit-print-color-adjust: exact; }
  .site-header, .site-footer { display: none; }
  .page-shell { width: 100%; padding: 0; }
  .roster-card { border-radius: 0; box-shadow: none; }
  .roster-heading { padding: 10mm 8mm 6mm; }
  .roster-meta > div { padding: 4mm 8mm; }
  .table-scroll { overflow: visible; }
  table { min-width: 0; font-size: 9pt; }
  thead th:first-child { width: 42mm; }
  tbody td { height: 14mm; }
  .viewer-note { display: none; }
}
`;

const VIEWER_JS = `const SHARE_SCHEMA = 'sing-yin-public-roster-v1';
const SHARE_AAD_PREFIX = 'sing-yin-roster-share-v1:';
const SESSION_TOKEN_KEY = 'sing-yin-roster-viewer-token-v1';
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });

const loadingState = document.getElementById('loadingState');
const guestState = document.getElementById('guestState');
const errorState = document.getElementById('errorState');
const rosterState = document.getElementById('rosterState');
const rosterTable = document.getElementById('rosterTable');

function showOnly(element) {
  guestState.hidden = element !== guestState;
  loadingState.hidden = element !== loadingState;
  errorState.hidden = element !== errorState;
  rosterState.hidden = element !== rosterState;
  loadingState.setAttribute('aria-busy', element === loadingState ? 'true' : 'false');
}

function hasShareToken() {
  if (window.location.hash.slice(1).trim()) return true;
  try {
    return Boolean(sessionStorage.getItem(SESSION_TOKEN_KEY));
  } catch {
    return false;
  }
}

function failOpen() {
  try {
    sessionStorage.removeItem(SESSION_TOKEN_KEY);
  } catch {
    // Some privacy modes disable session storage; the viewer still fails closed.
  }
  showOnly(errorState);
}

function base64UrlBytes(value) {
  if (!/^[A-Za-z0-9_-]+$/.test(value)) throw new Error('invalid base64url');
  const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, character => character.charCodeAt(0));
}

function readToken() {
  const fragment = window.location.hash.slice(1).trim();
  if (fragment) {
    try {
      sessionStorage.setItem(SESSION_TOKEN_KEY, fragment);
    } catch {
      // The fragment remains available for this page load when storage is blocked.
    }
    try {
      history.replaceState(null, '', window.location.pathname);
    } catch {
      // Decryption still works; leaving the fragment is safer than breaking the link.
    }
  }
  let storedToken = '';
  try {
    storedToken = sessionStorage.getItem(SESSION_TOKEN_KEY) || '';
  } catch {
    // Storage is optional; the URL fragment is the authoritative first-load token.
  }
  const token = fragment || storedToken;
  const separator = token.indexOf('.');
  if (separator < 1 || token.indexOf('.', separator + 1) !== -1) throw new Error('invalid token');
  const shareId = token.slice(0, separator);
  const keyText = token.slice(separator + 1);
  if (!/^[A-Za-z0-9_-]{20,64}$/.test(shareId)) throw new Error('invalid share id');
  const keyBytes = base64UrlBytes(keyText);
  if (keyBytes.byteLength !== 32) throw new Error('invalid key');
  return { shareId, keyBytes };
}

async function decryptSnapshot(shareId, keyBytes, payload) {
  if (payload.schemaVersion !== SHARE_SCHEMA) throw new Error('unsupported schema');
  const nonce = base64UrlBytes(payload.nonce);
  const ciphertext = base64UrlBytes(payload.ciphertext);
  if (nonce.byteLength !== 12 || ciphertext.byteLength < 17) throw new Error('invalid encrypted payload');
  const key = await crypto.subtle.importKey('raw', keyBytes, { name: 'AES-GCM' }, false, ['decrypt']);
  const plaintext = await crypto.subtle.decrypt(
    {
      name: 'AES-GCM',
      iv: nonce,
      additionalData: encoder.encode(SHARE_AAD_PREFIX + shareId),
      tagLength: 128,
    },
    key,
    ciphertext,
  );
  const snapshot = JSON.parse(decoder.decode(plaintext));
  validateSnapshot(snapshot);
  return snapshot;
}

function validateSnapshot(snapshot) {
  if (!snapshot || snapshot.schemaVersion !== SHARE_SCHEMA) throw new Error('invalid snapshot');
  if (!Array.isArray(snapshot.days) || snapshot.days.length < 1 || snapshot.days.length > 7) throw new Error('invalid days');
  if (!Array.isArray(snapshot.rows) || snapshot.rows.length < 1 || snapshot.rows.length > 20) throw new Error('invalid rows');
  for (const row of snapshot.rows) {
    if (!Array.isArray(row.cells) || row.cells.length !== snapshot.days.length) throw new Error('invalid cells');
  }
}

function textElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  element.textContent = String(text ?? '');
  return element;
}

function localDate(value) {
  const match = /^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(String(value ?? ''));
  return match ? match.slice(1).join('-') : String(value ?? '');
}

function formatExpiry(value) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return '—';
  return new Intl.DateTimeFormat('zh-HK', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(date);
}

function renderRoster(snapshot, expiresAt) {
  document.getElementById('rosterTitleZh').textContent = snapshot.titleZh || '本週導學風紀值班表';
  document.getElementById('rosterTitleEn').textContent = snapshot.titleEn || 'Weekly Study Prefect Duty Roster';
  const firstDay = snapshot.days[0]?.date || snapshot.weekStart || '';
  const lastDay = snapshot.days.at(-1)?.date || firstDay;
  document.getElementById('weekLabel').textContent = firstDay === lastDay ? localDate(firstDay) : localDate(firstDay) + ' — ' + localDate(lastDay);
  document.getElementById('expiryLabel').textContent = formatExpiry(expiresAt);

  const head = document.createElement('thead');
  const headingRow = document.createElement('tr');
  const dutyHeading = textElement('th', '', '值班位置');
  dutyHeading.setAttribute('scope', 'col');
  dutyHeading.append(textElement('span', 'day-en', 'Duty position'));
  headingRow.append(dutyHeading);

  for (const day of snapshot.days) {
    const heading = textElement('th', '', day.labelZh || day.code || '');
    heading.setAttribute('scope', 'col');
    heading.append(textElement('span', 'day-en', day.labelEn || ''));
    heading.append(textElement('span', 'day-date', localDate(day.date)));
    headingRow.append(heading);
  }
  head.append(headingRow);

  const body = document.createElement('tbody');
  for (const row of snapshot.rows) {
    const tableRow = document.createElement('tr');
    const rowHeading = textElement('th', '', row.labelZh || row.postCode || '');
    rowHeading.setAttribute('scope', 'row');
    rowHeading.append(textElement('span', 'duty-en', row.labelEn || ''));
    const dutyStart = row.dutyTime?.start || '';
    const dutyEnd = row.dutyTime?.end || '';
    if (dutyStart && dutyEnd) rowHeading.append(textElement('span', 'duty-time', dutyStart + '–' + dutyEnd));
    tableRow.append(rowHeading);

    for (const cell of row.cells) {
      const tableCell = document.createElement('td');
      const status = cell?.status || 'vacant';
      if (status === 'assigned' && cell.nameZh) {
        tableCell.append(textElement('span', 'prefect-name', cell.nameZh));
      } else if (status === 'closed') {
        tableCell.className = 'cell--closed';
        tableCell.append(textElement('span', 'cell-status', '休室 · Closed'));
      } else {
        tableCell.className = 'cell--vacant';
        tableCell.append(textElement('span', 'cell-status', '待補 · Vacancy'));
      }
      tableRow.append(tableCell);
    }
    body.append(tableRow);
  }

  rosterTable.replaceChildren(head, body);
  showOnly(rosterState);
}

async function openSharedRoster() {
  if (window.location.pathname === '/' && !hasShareToken()) {
    showOnly(guestState);
    return;
  }
  try {
    const { shareId, keyBytes } = readToken();
    const response = await fetch('/api/view', {
      method: 'POST',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shareId }),
    });
    if (!response.ok) throw new Error('share unavailable');
    const payload = await response.json();
    const snapshot = await decryptSnapshot(shareId, keyBytes, payload);
    renderRoster(snapshot, payload.expiresAt);
  } catch {
    failOpen();
  }
}

openSharedRoster();
`;

const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="16" fill="#176d68"/>
<path d="M15 17c7-2 13 0 17 4v28c-4-4-10-6-17-4V17Zm34 0c-7-2-13 0-17 4v28c4-4 10-6 17-4V17Z" fill="none" stroke="#fff" stroke-width="4" stroke-linejoin="round"/>
</svg>`;

const ACCESS_FAILURE_HTML = `<!doctype html>
<html lang="zh-Hant-HK">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <title>管理員登入未完成 · Admin sign-in incomplete</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/viewer.css">
</head>
<body>
  <main class="page-shell">
    <section class="state-card state-card--error" role="alert">
      <div class="state-icon" aria-hidden="true">!</div>
      <h1>未能確認管理員身分</h1>
      <p>登入資料可能已到期或不適用於這個網站。請返回首頁後重新登入。</p>
      <p class="state-english" lang="en">Your administrator session could not be verified. Return to the home page and sign in again.</p>
      <div class="guest-actions">
        <a class="admin-login" href="/logout">清除登入狀態 <span lang="en">· Sign out</span></a>
        <a class="admin-login" href="/">返回首頁 <span lang="en">· Return home</span></a>
      </div>
    </section>
  </main>
</body>
</html>`;

class AccessValidationError extends Error {
  constructor() {
    super('access_validation_failed');
    this.name = 'AccessValidationError';
  }
}

function normalizeAccessConfiguration(env) {
  const rawTeamDomain = typeof env.ACCESS_TEAM_DOMAIN === 'string' ? env.ACCESS_TEAM_DOMAIN.trim() : '';
  const rawAudience = typeof env.ACCESS_AUD === 'string' ? env.ACCESS_AUD : '';
  const audience = rawAudience.trim();
  const adminEmail = typeof env.ADMIN_EMAIL === 'string' ? env.ADMIN_EMAIL : '';
  let teamDomain;
  try {
    const parsed = new URL(rawTeamDomain);
    if (
      parsed.protocol !== 'https:'
      || parsed.username
      || parsed.password
      || parsed.port
      || parsed.pathname !== '/'
      || parsed.search
      || parsed.hash
      || !parsed.hostname.endsWith('.cloudflareaccess.com')
      || parsed.hostname === 'cloudflareaccess.com'
    ) {
      throw new AccessValidationError();
    }
    teamDomain = parsed.origin;
  } catch {
    throw new AccessValidationError();
  }
  if (!audience || audience.length > 512 || rawAudience !== audience || /\s/.test(audience)) {
    throw new AccessValidationError();
  }
  if (
    !adminEmail
    || adminEmail !== adminEmail.trim()
    || adminEmail.length > 320
    || !/^[^@\s]+@[^@\s]+$/.test(adminEmail)
  ) {
    throw new AccessValidationError();
  }
  return { teamDomain, audience, adminEmail };
}

function accessTokenFromRequest(request) {
  const assertion = request.headers.get('Cf-Access-Jwt-Assertion');
  if (assertion && assertion.trim()) return assertion.trim();
  const cookieHeader = request.headers.get('Cookie') || '';
  for (const part of cookieHeader.split(';')) {
    const separator = part.indexOf('=');
    if (separator < 1 || part.slice(0, separator).trim().toLowerCase() !== ACCESS_COOKIE_NAME.toLowerCase()) continue;
    const rawValue = part.slice(separator + 1).trim();
    try {
      return decodeURIComponent(rawValue);
    } catch {
      return rawValue;
    }
  }
  return '';
}

function jsonObjectFromJwtSegment(segment, maximumBytes) {
  const bytes = decodeBase64Url(segment);
  if (!bytes || bytes.byteLength < 2 || bytes.byteLength > maximumBytes) throw new AccessValidationError();
  let parsed;
  try {
    parsed = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes));
  } catch {
    throw new AccessValidationError();
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new AccessValidationError();
  return parsed;
}

async function loadAccessJwks(teamDomain, fetcher, nowMillis, forceRefresh = false) {
  const cached = accessJwksCache.get(teamDomain);
  if (!forceRefresh && cached && cached.expiresAt > nowMillis) return cached.keys;
  const certificateUrl = `${teamDomain}/cdn-cgi/access/certs`;
  let certificateResponse;
  try {
    certificateResponse = await fetcher(certificateUrl, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
      redirect: 'error',
    });
  } catch {
    throw new AccessValidationError();
  }
  if (!certificateResponse || !certificateResponse.ok) throw new AccessValidationError();
  const declaredLength = Number(certificateResponse.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > ACCESS_JWKS_MAX_BYTES) throw new AccessValidationError();
  let raw;
  try {
    raw = await readBoundedUtf8(certificateResponse, ACCESS_JWKS_MAX_BYTES);
  } catch {
    throw new AccessValidationError();
  }
  let document;
  try {
    document = JSON.parse(raw);
  } catch {
    throw new AccessValidationError();
  }
  if (!document || !Array.isArray(document.keys) || document.keys.length < 1 || document.keys.length > 16) {
    throw new AccessValidationError();
  }
  const keys = document.keys.filter(key => key && typeof key === 'object' && !Array.isArray(key));
  if (keys.length !== document.keys.length) throw new AccessValidationError();
  accessJwksCache.set(teamDomain, {
    keys,
    fetchedAt: nowMillis,
    expiresAt: nowMillis + ACCESS_JWKS_CACHE_TTL_MS,
  });
  return keys;
}

async function accessJwkForKid(teamDomain, kid, fetcher, nowMillis) {
  let keys = await loadAccessJwks(teamDomain, fetcher, nowMillis);
  let matches = keys.filter(candidate => candidate.kid === kid);
  if (matches.length === 0) {
    const cached = accessJwksCache.get(teamDomain);
    if (cached && nowMillis - cached.fetchedAt < ACCESS_JWKS_MIN_REFRESH_MS) throw new AccessValidationError();
    keys = await loadAccessJwks(teamDomain, fetcher, nowMillis, true);
    matches = keys.filter(candidate => candidate.kid === kid);
  }
  const key = matches.length === 1 ? matches[0] : null;
  const modulus = key ? decodeBase64Url(key.n) : null;
  const exponent = key ? decodeBase64Url(key.e) : null;
  if (
    !key
    || key.kty !== 'RSA'
    || key.alg !== 'RS256'
    || (key.use !== undefined && key.use !== 'sig')
    || (key.key_ops !== undefined && (!Array.isArray(key.key_ops) || !key.key_ops.includes('verify')))
    || !modulus
    || modulus.byteLength < 256
    || !exponent
    || exponent.byteLength < 1
    || exponent.byteLength > 8
  ) {
    throw new AccessValidationError();
  }
  return key;
}

async function validateAccessJwt(token, env, options = {}) {
  const configuration = normalizeAccessConfiguration(env);
  if (typeof token !== 'string' || token.length < 16 || token.length > MAX_ACCESS_JWT_BYTES) {
    throw new AccessValidationError();
  }
  const parts = token.split('.');
  if (parts.length !== 3 || parts.some(part => !part)) throw new AccessValidationError();
  const [headerSegment, payloadSegment, signatureSegment] = parts;
  const header = jsonObjectFromJwtSegment(headerSegment, 4_096);
  const payload = jsonObjectFromJwtSegment(payloadSegment, 16_384);
  const signature = decodeBase64Url(signatureSegment);
  if (
    header.alg !== 'RS256'
    || typeof header.kid !== 'string'
    || header.kid.length < 1
    || header.kid.length > 256
    || header.crit !== undefined
    || (header.typ !== undefined && header.typ !== 'JWT')
    || !signature
    || signature.byteLength < 128
    || signature.byteLength > 1_024
  ) {
    throw new AccessValidationError();
  }

  const nowMillis = options.nowMillis ?? Date.now();
  const nowSeconds = Math.floor(nowMillis / 1_000);
  const audiences = typeof payload.aud === 'string' ? [payload.aud] : payload.aud;
  if (
    payload.iss !== configuration.teamDomain
    || !Array.isArray(audiences)
    || !audiences.every(item => typeof item === 'string')
    || !audiences.includes(configuration.audience)
    || typeof payload.exp !== 'number'
    || !Number.isFinite(payload.exp)
    || nowSeconds >= payload.exp
    || (payload.nbf !== undefined && (
      typeof payload.nbf !== 'number'
      || !Number.isFinite(payload.nbf)
      || nowSeconds < payload.nbf
    ))
    || payload.email !== configuration.adminEmail
  ) {
    throw new AccessValidationError();
  }
  const fetcher = options.fetcher ?? fetch;
  const jwk = await accessJwkForKid(configuration.teamDomain, header.kid, fetcher, nowMillis);
  const modulus = decodeBase64Url(jwk.n);
  if (!modulus || signature.byteLength !== modulus.byteLength) throw new AccessValidationError();
  let publicKey;
  try {
    publicKey = await crypto.subtle.importKey(
      'jwk',
      jwk,
      { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' },
      false,
      ['verify'],
    );
  } catch {
    throw new AccessValidationError();
  }
  const verified = await crypto.subtle.verify(
    { name: 'RSASSA-PKCS1-v1_5' },
    publicKey,
    signature,
    new TextEncoder().encode(`${headerSegment}.${payloadSegment}`),
  );
  if (!verified) throw new AccessValidationError();

  return { payload, configuration };
}

function stripAccessCredentials(inputHeaders) {
  const headers = new Headers(inputHeaders);
  for (const name of [...headers.keys()]) {
    if (name.toLowerCase().startsWith('cf-access-')) headers.delete(name);
  }
  headers.delete('X-Sing-Yin-Access-Email');
  const cookieHeader = headers.get('Cookie') || '';
  const retainedCookies = cookieHeader
    .split(';')
    .map(part => part.trim())
    .filter(part => {
      if (!part) return false;
      const separator = part.indexOf('=');
      const name = (separator < 0 ? part : part.slice(0, separator)).trim();
      return name.toLowerCase() !== ACCESS_COOKIE_NAME.toLowerCase();
    });
  if (retainedCookies.length) headers.set('Cookie', retainedCookies.join('; '));
  else headers.delete('Cookie');
  return headers;
}

function authenticatedProxyRequestAllowed(request) {
  const method = request.method.toUpperCase();
  const supportedMethods = ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE'];
  if (!supportedMethods.includes(method)) return false;
  const isUnsafeMethod = !['GET', 'HEAD', 'OPTIONS'].includes(method);
  const isWebSocket = (request.headers.get('Upgrade') || '').toLowerCase() === 'websocket';
  if (!isUnsafeMethod && !isWebSocket) return true;
  const suppliedOrigin = request.headers.get('Origin');
  if (!suppliedOrigin) return false;
  let expectedOrigin;
  try {
    expectedOrigin = new URL(request.url).origin;
    if (new URL(suppliedOrigin).origin !== expectedOrigin) return false;
  } catch {
    return false;
  }
  const fetchSite = (request.headers.get('Sec-Fetch-Site') || '').toLowerCase();
  return !fetchSite || fetchSite === 'same-origin';
}

async function proxyToRosterOrigin(request, env, verifiedEmail) {
  if (!env.ROSTER_ORIGIN || typeof env.ROSTER_ORIGIN.fetch !== 'function') throw new AccessValidationError();
  const publicUrl = new URL(request.url);
  const originUrl = new URL('http://127.0.0.1:8080');
  originUrl.pathname = publicUrl.pathname;
  originUrl.search = publicUrl.search;
  const headers = stripAccessCredentials(request.headers);
  headers.set('X-Forwarded-Host', publicUrl.host);
  headers.set('X-Forwarded-Proto', 'https');
  headers.set('X-Sing-Yin-Access-Email', verifiedEmail);
  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  };
  if (request.method !== 'GET' && request.method !== 'HEAD') init.body = request.body;
  const originRequest = new Request(originUrl.toString(), init);
  return await env.ROSTER_ORIGIN.fetch(originRequest);
}

function accessFailureResponse(status = 403) {
  return response(ACCESS_FAILURE_HTML, status, { 'Content-Type': 'text/html; charset=utf-8' });
}

function redirectResponse(destination, requestUrl, status = 302) {
  return response(null, status, { Location: new URL(destination, requestUrl).toString() });
}

function originProxyResult(originResponse) {
  return { originResponse };
}

function response(body, status = 200, headers = {}) {
  return new Response(body, { status, headers });
}

function jsonResponse(payload, status = 200) {
  return response(JSON.stringify(payload), status, { 'Content-Type': 'application/json; charset=utf-8' });
}

function secured(input) {
  const output = new Response(input.body, input);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) output.headers.set(name, value);
  return output;
}

function methodNotAllowed(allowed) {
  return response('Method not allowed', 405, { 'Content-Type': 'text/plain; charset=utf-8', Allow: allowed });
}

function missingShare() {
  return jsonResponse({ error: 'share_unavailable' }, 404);
}

function validShareId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{20,64}$/.test(value);
}

function validIsoDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split('-').map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}

function decodeBase64Url(value) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value)) return null;
  try {
    const padded = value.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - (value.length % 4)) % 4);
    const binary = atob(padded);
    return Uint8Array.from(binary, character => character.charCodeAt(0));
  } catch {
    return null;
  }
}

async function readBoundedUtf8(input, maximumBytes) {
  const declaredLength = Number(input.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > maximumBytes) throw new RangeError('request too large');
  if (!input.body) return '';
  const reader = input.body.getReader();
  const decoder = new TextDecoder('utf-8', { fatal: true });
  let body = '';
  let totalBytes = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > maximumBytes) {
        await reader.cancel();
        throw new RangeError('request too large');
      }
      body += decoder.decode(value, { stream: true });
    }
    body += decoder.decode();
  } finally {
    reader.releaseLock();
  }
  return body;
}

async function readJson(request, maximumBytes) {
  const body = await readBoundedUtf8(request, maximumBytes);
  return JSON.parse(body);
}

async function sha256(value) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value)));
}

async function bearerAuthorized(request, env) {
  const configured = typeof env.ADMIN_BEARER_TOKEN === 'string' ? env.ADMIN_BEARER_TOKEN : '';
  const authorization = request.headers.get('Authorization') || '';
  const supplied = authorization.startsWith('Bearer ') ? authorization.slice(7) : '';
  const [configuredHash, suppliedHash] = await Promise.all([sha256(configured), sha256(supplied)]);
  let difference = configured.length ^ supplied.length;
  for (let index = 0; index < configuredHash.length; index += 1) difference |= configuredHash[index] ^ suppliedHash[index];
  return configured.length >= 32 && difference === 0;
}

function storedRecordFrom(payload, shareId, weekStart, createdAt, expiresAt) {
  return {
    version: 1,
    schemaVersion: SHARE_SCHEMA,
    shareId,
    weekStart,
    ciphertext: payload.ciphertext,
    nonce: payload.nonce,
    createdAt,
    expiresAt,
  };
}

function validateCreatePayload(payload, now) {
  if (!payload || payload.schemaVersion !== SHARE_SCHEMA || !validShareId(payload.shareId)) return null;
  const allowedFields = new Set([
    'schemaVersion',
    'shareId',
    'weekStart',
    'createdAt',
    'expiresAt',
    'nonce',
    'ciphertext',
  ]);
  if (Object.keys(payload).some(key => !allowedFields.has(key))) return null;
  if (!validIsoDate(payload.weekStart)) return null;
  const nonce = decodeBase64Url(payload.nonce);
  const ciphertext = decodeBase64Url(payload.ciphertext);
  if (!nonce || nonce.byteLength !== 12) return null;
  if (!ciphertext || ciphertext.byteLength < 17 || ciphertext.byteLength > 131_072) return null;
  const expiryMillis = Date.parse(payload.expiresAt);
  if (!Number.isFinite(expiryMillis)) return null;
  if (expiryMillis - now < MIN_SHARE_LIFETIME_MS || expiryMillis - now > MAX_SHARE_LIFETIME_MS) return null;
  return {
    shareId: payload.shareId,
    weekStart: payload.weekStart,
    expiresAt: new Date(expiryMillis).toISOString(),
    expiryMillis,
  };
}

async function createShare(request, env) {
  let payload;
  try {
    payload = await readJson(request, MAX_ADMIN_BODY_BYTES);
  } catch (error) {
    return jsonResponse({ error: error instanceof RangeError ? 'request_too_large' : 'invalid_request' }, error instanceof RangeError ? 413 : 400);
  }
  const now = Date.now();
  const validated = validateCreatePayload(payload, now);
  if (!validated) return jsonResponse({ error: 'invalid_request' }, 400);
  const key = SHARE_KEY_PREFIX + validated.shareId;
  if (await env.ROSTER_SHARES.get(key)) return jsonResponse({ error: 'share_exists' }, 409);

  const createdAt = new Date(now).toISOString();
  const record = storedRecordFrom(
    payload,
    validated.shareId,
    validated.weekStart,
    createdAt,
    validated.expiresAt,
  );
  const metadata = {
    weekStart: validated.weekStart,
    createdAt,
    expiresAt: validated.expiresAt,
    schemaVersion: SHARE_SCHEMA,
  };
  await env.ROSTER_SHARES.put(key, JSON.stringify(record), {
    expiration: Math.floor(validated.expiryMillis / 1_000),
    metadata,
  });
  return jsonResponse({
    shareId: validated.shareId,
    weekStart: validated.weekStart,
    createdAt,
    expiresAt: validated.expiresAt,
  }, 201);
}

async function listShares(env) {
  const listing = await env.ROSTER_SHARES.list({ prefix: SHARE_KEY_PREFIX, limit: 1_000 });
  const shares = listing.keys.map(item => ({
    shareId: item.name.slice(SHARE_KEY_PREFIX.length),
    weekStart: item.metadata?.weekStart || null,
    createdAt: item.metadata?.createdAt || null,
    expiresAt: item.metadata?.expiresAt || null,
  }));
  return jsonResponse({ shares, cursor: listing.list_complete ? null : listing.cursor || null });
}

async function deleteShare(shareId, env) {
  if (!validShareId(shareId)) return jsonResponse({ error: 'invalid_request' }, 400);
  await env.ROSTER_SHARES.delete(SHARE_KEY_PREFIX + shareId);
  return new Response(null, { status: 204 });
}

async function viewShare(request, env, context) {
  let payload;
  try {
    payload = await readJson(request, MAX_VIEW_BODY_BYTES);
  } catch {
    return missingShare();
  }
  if (!payload || !validShareId(payload.shareId) || Object.keys(payload).some(key => key !== 'shareId')) return missingShare();
  const key = SHARE_KEY_PREFIX + payload.shareId;
  const record = await env.ROSTER_SHARES.get(key, { type: 'json' });
  if (!record || record.shareId !== payload.shareId || record.schemaVersion !== SHARE_SCHEMA) return missingShare();
  const expiryMillis = Date.parse(record.expiresAt);
  if (!Number.isFinite(expiryMillis) || expiryMillis <= Date.now()) {
    context.waitUntil(env.ROSTER_SHARES.delete(key));
    return missingShare();
  }
  return jsonResponse({
    schemaVersion: SHARE_SCHEMA,
    ciphertext: record.ciphertext,
    nonce: record.nonce,
    expiresAt: record.expiresAt,
  });
}

async function route(request, env, context) {
  const url = new URL(request.url);
  const path = url.pathname;

  if (path === '/view' && request.method === 'GET') {
    return response(VIEWER_HTML, 200, { 'Content-Type': 'text/html; charset=utf-8' });
  }
  if (path === '/viewer.css' && request.method === 'GET') {
    return response(VIEWER_CSS, 200, { 'Content-Type': 'text/css; charset=utf-8' });
  }
  if (path === '/viewer.js' && request.method === 'GET') {
    return response(VIEWER_JS, 200, { 'Content-Type': 'text/javascript; charset=utf-8' });
  }
  if (path === '/favicon.svg' && request.method === 'GET') {
    return response(FAVICON_SVG, 200, { 'Content-Type': 'image/svg+xml; charset=utf-8' });
  }
  if (path === '/robots.txt' && request.method === 'GET') {
    return response('User-agent: *\nDisallow: /\n', 200, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  if (path === '/healthz' && request.method === 'GET') {
    return jsonResponse({
      status: 'ok',
      application: 'sing-yin-roster-gateway',
      capabilities: ['encrypted-public-viewer', 'access-admin-gateway', 'private-origin-proxy'],
    });
  }
  if (path === '/api/view') {
    if (request.method !== 'POST') return methodNotAllowed('POST');
    return viewShare(request, env, context);
  }

  if (path === '/api/admin/shares' || path.startsWith('/api/admin/shares/')) {
    if (!(await bearerAuthorized(request, env))) return jsonResponse({ error: 'unauthorized' }, 401);
    if (path === '/api/admin/shares' && request.method === 'POST') return createShare(request, env);
    if (path === '/api/admin/shares' && request.method === 'GET') return listShares(env);
    if (request.method === 'DELETE') return deleteShare(path.slice('/api/admin/shares/'.length), env);
    return methodNotAllowed('GET, POST, DELETE');
  }

  if (path === '/logout') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    return redirectResponse('/cdn-cgi/access/logout', request.url);
  }

  const token = accessTokenFromRequest(request);
  if (!token) {
    if (path === '/' && request.method === 'GET') {
      return response(VIEWER_HTML, 200, { 'Content-Type': 'text/html; charset=utf-8' });
    }
    if (path === '/auth/login') return accessFailureResponse();
    return redirectResponse('/', request.url);
  }

  let access;
  try {
    access = await validateAccessJwt(token, env);
  } catch {
    if (path === '/' && request.method === 'GET') {
      return response(VIEWER_HTML, 200, { 'Content-Type': 'text/html; charset=utf-8' });
    }
    return accessFailureResponse();
  }
  if (path === '/auth/login') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    return redirectResponse('/', request.url);
  }
  if (!authenticatedProxyRequestAllowed(request)) return accessFailureResponse();
  return originProxyResult(await proxyToRosterOrigin(request, env, access.payload.email));
}

export default {
  async fetch(request, env, context) {
    try {
      const routed = await route(request, env, context);
      if (routed && routed.originResponse) return routed.originResponse;
      return secured(routed);
    } catch {
      return secured(jsonResponse({ error: 'service_unavailable' }, 503));
    }
  },
};

export {
  SECURITY_HEADERS,
  SHARE_SCHEMA,
  accessTokenFromRequest,
  authenticatedProxyRequestAllowed,
  normalizeAccessConfiguration,
  proxyToRosterOrigin,
  storedRecordFrom,
  stripAccessCredentials,
  validateAccessJwt,
  validateCreatePayload,
};
