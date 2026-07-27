import {
  SERVICE_WEAVE_FAVICON_BASE64,
  SERVICE_WEAVE_FAVICON_BYTE_LENGTH,
  SERVICE_WEAVE_FAVICON_SHA256,
} from './service_weave_brand.generated.js';

const SHARE_SCHEMA = 'sing-yin-public-roster-v1';
const SHARE_KEY_PREFIX = 'share:';
const CONTENT_SHARE_KEY_PREFIX = 'share:v2:';
const CONTENT_DIGEST_PATTERN = /^[a-f0-9]{64}$/;
const MAX_ADMIN_BODY_BYTES = 196_608;
const MAX_VIEW_BODY_BYTES = 2_048;
const GUEST_START_RATE_LIMIT_BINDING = 'GUEST_START_RATE_LIMITER';
const PUBLIC_VIEW_RATE_LIMIT_BINDING = 'PUBLIC_VIEW_RATE_LIMITER';
const RATE_LIMIT_RETRY_AFTER_SECONDS = 60;
const RATE_LIMIT_FAILURE_RETRY_AFTER_SECONDS = 15;
const MAX_SHARE_LIFETIME_MS = 31 * 24 * 60 * 60 * 1_000;
const MIN_SHARE_LIFETIME_MS = 60 * 1_000;
const MAX_ACCESS_JWT_BYTES = 32_768;
const ACCESS_JWKS_CACHE_TTL_MS = 5 * 60 * 1_000;
const ACCESS_JWKS_MIN_REFRESH_MS = 60 * 1_000;
const ACCESS_JWKS_MAX_BYTES = 65_536;
const ACCESS_COOKIE_NAME = 'CF_Authorization';
const ADMIN_SESSION_COOKIE_NAME = '__Host-SingYinAdminSession';
const GUEST_SESSION_COOKIE_NAME = '__Host-SingYinGuestSession';
const ADMIN_SESSION_VERSION = 2;
const GUEST_SESSION_VERSION = 1;
const ADMIN_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60;
const GUEST_SESSION_MAX_AGE_SECONDS = 30 * 60;
const ADMIN_SESSION_MAX_TOKEN_BYTES = 2_048;
const GUEST_SESSION_MAX_TOKEN_BYTES = 2_048;
const ORIGIN_PRINCIPAL_VERSION = 1;
const ORIGIN_PRINCIPAL_AUDIENCE = 'sing-yin-roster-origin';
const ORIGIN_PRINCIPAL_HEADER = 'X-Sing-Yin-Origin-Principal';
const accessJwksCache = new Map();

// Small, non-sensitive landing-page selection copied from the canonical
// devotional seed. Tests compare every field with the RCUV 2010 / NKJV source
// so the public entrance cannot silently drift from the main application.
const LANDING_DEVOTIONALS = Object.freeze([
  Object.freeze({ id: 'dv-0015', referenceZh: '哥林多前書 16:14', referenceEn: '1 Corinthians 16:14', scriptureZh: '你們所做的一切都要憑愛心而做。', scriptureEn: 'Let all that you do be done with love.', reflectionZh: '凡事憑愛心而行', reflectionEn: 'Let All Be Done in Love', prayerZh: '主啊，願愛約束我的語氣、決定和每一項服事。', prayerEn: 'Lord, let love govern my tone, decisions, and every act of service.' }),
  Object.freeze({ id: 'dv-0024', referenceZh: '哥林多前書 4:2', referenceEn: '1 Corinthians 4:2', scriptureZh: '所求於管家的，是要他忠心。', scriptureEn: 'Moreover it is required in stewards that one be found faithful.', reflectionZh: '管家所求的是忠心', reflectionEn: 'Faithful Stewards', prayerZh: '主啊，使我記得自己是管家，並在隱密處也忠心。', prayerEn: 'Lord, remind me that I am a steward, and make me faithful even in hidden work.' }),
  Object.freeze({ id: 'dv-0028', referenceZh: '阿摩司書 5:24', referenceEn: 'Amos 5:24', scriptureZh: '惟願公平如大水滾滾， 公義如江河滔滔。', scriptureEn: 'But let justice run down like water, And righteousness like a mighty stream.', reflectionZh: '公平如水滾滾', reflectionEn: 'Justice Like Waters', prayerZh: '主啊，使公平在我們團隊中成為穩定流動的常態。', prayerEn: 'Lord, make fairness a steady stream in our team, not an occasional act.' }),
  Object.freeze({ id: 'dv-0041', referenceZh: '雅各書 4:10', referenceEn: 'James 4:10', scriptureZh: '要在主面前謙卑，他就使你們高升。', scriptureEn: 'Humble yourselves in the sight of the Lord, and He will lift you up.', reflectionZh: '在主面前自卑', reflectionEn: 'Humble Before the Lord', prayerZh: '主啊，使我在祢面前自卑，讓祢塑造我的判斷和態度。', prayerEn: 'Lord, humble me before You and shape my judgment and attitude by grace.' }),
  Object.freeze({ id: 'dv-0109', referenceZh: '詩篇 31:24', referenceEn: 'Psalm 31:24', scriptureZh: '凡仰望耶和華的人， 你們都要壯膽，堅固你們的心！', scriptureEn: 'Be of good courage, And He shall strengthen your heart, All you who hope in the LORD.', reflectionZh: '仰望耶和華的人當剛強', reflectionEn: 'Take Courage as You Hope in the Lord', prayerZh: '主啊，堅固我的心，使我在等候中仍有勇氣。', prayerEn: 'Lord, strengthen my heart and give me courage as I wait for You.' }),
]);

const WELCOME_TRACKS = Object.freeze({
  bright: Object.freeze([
    Object.freeze({ id: 'morning-has-broken', title: 'Morning Has Broken', artist: 'Relaxing Piano', arrangement: 'instrumental', filename: 'Relaxing Piano - Topic - Morning ⧸ Morning Has Broken.m4a' }),
    Object.freeze({ id: 'come-fill-hearts', title: 'Come and Fill Our Hearts', artist: 'Hymns Made Fresh', arrangement: 'instrumental', filename: 'Hymns Made Fresh - Come and Fill Our Hearts - Taize PIANO Instrumental KARAOKE.m4a' }),
    Object.freeze({ id: 'in-lord-thankful', title: "In the Lord I'll Be Ever Thankful", artist: 'Emmaus Music', arrangement: 'instrumental', filename: "Emmaus Music - In The Lord I'll be Ever Thankful (Taize)  ｜  Instrumental Version.m4a" }),
    Object.freeze({ id: 'kingdom-of-god', title: 'The Kingdom of God', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - The Kingdom of God (Accompaniment).m4a' }),
    Object.freeze({ id: 'tui-amoris-ignem', title: 'Tui amoris ignem', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - Tui amoris ignem (Accompaniment).m4a' }),
  ]),
  quiet: Object.freeze([
    Object.freeze({ id: 'ubi-caritas', title: 'Ubi caritas', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - Ubi caritas (Accompaniment).m4a' }),
    Object.freeze({ id: 'nada-te-turbe', title: 'Nada te turbe', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - Nada te turbe (Accompaniment).m4a' }),
    Object.freeze({ id: 'mon-ame-se-repose', title: 'Mon âme se repose', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - Mon âme se repose (Accompaniment).m4a' }),
    Object.freeze({ id: 'dona-la-pace', title: 'Dona la pace', artist: 'Taizé', arrangement: 'instrumental', filename: 'Taizé - Topic - Dona la pace (Accompaniment).m4a' }),
    Object.freeze({ id: 'da-pacem-cordium-violin', title: 'Da pacem cordium', artist: 'Violin De Noche', arrangement: 'instrumental', filename: 'Violin De Noche - Taizé Instrumental - Da Pacem Cordium (Violin).m4a' }),
  ]),
});

const WELCOME_TRACK_BY_ID = new Map(
  Object.values(WELCOME_TRACKS).flat().map(track => [track.id, track]),
);

const WELCOME_PUBLIC_TRACKS = Object.freeze(Object.fromEntries(
  Object.entries(WELCOME_TRACKS).map(([profile, tracks]) => [
    profile,
    tracks.map(({ filename: _filename, ...track }) => track),
  ]),
));

function resolveWelcomeVolumePreference(
  storage,
  defaultVolume,
  volumeKey,
  revisionKey,
  currentRevision,
) {
  let stored;
  let storedRevision;
  try {
    stored = storage.getItem(volumeKey);
    storedRevision = Number.parseInt(storage.getItem(revisionKey) || '0', 10);
  } catch {
    return defaultVolume;
  }

  const parsed = stored === null ? defaultVolume : Number(stored);
  const value = Number.isFinite(parsed) && parsed >= 0 && parsed <= 1
    ? parsed
    : defaultVolume;

  // A saved numeric value is an operator preference, even when it happens to
  // equal an earlier default. Only a genuinely absent key receives the new
  // default; a revision marker must never rewrite an explicit 25% choice.
  if (stored === null) {
    try { storage.setItem(volumeKey, String(value)); } catch {
      // The in-memory value remains usable when private browsing blocks writes.
    }
  }
  if (!Number.isInteger(storedRevision) || storedRevision < currentRevision) {
    try { storage.setItem(revisionKey, String(currentRevision)); } catch {
      // Preference reads remain authoritative even when metadata cannot persist.
    }
  }
  return value;
}

export function createWelcomeEntryController({
  play,
  navigate,
  isPlaying = () => false,
  onIntentChange = () => {},
  onBusyChange = () => {},
  onPlaybackStarted = () => {},
  onPlaybackFailed = () => {},
  onPlaybackTimeout = () => {},
  schedule = (callback, delay) => setTimeout(callback, delay),
  cancel = timer => clearTimeout(timer),
  timeoutMs = 450,
} = {}) {
  if (typeof play !== 'function') throw new TypeError('play must be a function');
  if (typeof navigate !== 'function') throw new TypeError('navigate must be a function');

  let intent = 'unset';
  let busy = false;
  let activation = 0;
  let timer = null;

  const setIntent = (nextIntent) => {
    if (!['unset', 'music', 'quiet'].includes(nextIntent)) {
      throw new TypeError('entry intent must be unset, music, or quiet');
    }
    intent = nextIntent;
    onIntentChange(intent);
  };

  const reset = () => {
    activation += 1;
    if (timer !== null) cancel(timer);
    timer = null;
    busy = false;
    onBusyChange('', false);
  };

  const enter = (destination, role = '') => {
    if (typeof destination !== 'string' || destination.length === 0 || busy) return false;
    busy = true;
    const currentActivation = ++activation;
    onBusyChange(role, true);

    let finished = false;
    const finish = () => {
      if (finished || currentActivation !== activation) return;
      finished = true;
      if (timer !== null) cancel(timer);
      timer = null;
      navigate(destination);
    };

    if (intent === 'quiet' || isPlaying()) {
      finish();
      return true;
    }

    let playback;
    try {
      // This call intentionally remains synchronous with the trusted click.
      // Moving it behind an await or timer breaks browser user activation.
      playback = play();
    } catch (error) {
      onPlaybackFailed(error);
      finish();
      return true;
    }

    timer = schedule(() => {
      if (finished || currentActivation !== activation) return;
      onPlaybackTimeout();
      finish();
    }, timeoutMs);

    Promise.resolve(playback).then(() => {
      if (finished || currentActivation !== activation) return;
      onPlaybackStarted();
      finish();
    }, (error) => {
      if (finished || currentActivation !== activation) return;
      onPlaybackFailed(error);
      finish();
    });
    return true;
  };

  return Object.freeze({
    enter,
    reset,
    setIntent,
    getIntent: () => intent,
    isBusy: () => busy,
  });
}

export function classifyWelcomeAudioFailureState({
  errorName = '',
  mediaErrorCode = 0,
  networkState = 0,
  readyState = 0,
  online = true,
} = {}) {
  if (errorName === 'NotAllowedError') return 'blocked';
  if (errorName === 'NotSupportedError') return 'decoding';
  if (errorName === 'AbortError') return 'lifecycle';
  if (mediaErrorCode === 3 || mediaErrorCode === 4) return 'decoding';
  if (mediaErrorCode === 2) return 'transport';
  if (networkState === 2 && readyState < 3) return 'loading';
  return online === false ? 'transport' : 'error';
}

const SECURITY_HEADERS = Object.freeze({
  'Cache-Control': 'no-store, max-age=0',
  'Content-Security-Policy': [
    "default-src 'none'",
    "script-src 'self'",
    "style-src 'self'",
    "connect-src 'self'",
    "img-src 'self' data:",
    "media-src 'self'",
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
  'Permissions-Policy': 'autoplay=(self), camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet',
});

// NiceGUI needs its own scripts, WebSocket and dynamic style behavior, so the
// locked-down public-viewer CSP above must never be copied onto the workbench.
// These transport and embedding headers are safe for ordinary proxied HTTP
// responses; 101/WebSocket carriers remain byte-for-byte untouched.
const WORKBENCH_SECURITY_HEADERS = Object.freeze({
  'Cross-Origin-Opener-Policy': 'same-origin',
  'Cross-Origin-Resource-Policy': 'same-origin',
  'Permissions-Policy': 'autoplay=(self), camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'Referrer-Policy': 'no-referrer',
  'Strict-Transport-Security': 'max-age=63072000; includeSubDomains; preload',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'SAMEORIGIN',
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
  <title>導學風紀值班表生成系統 · Study Prefect Duty Roster System</title>
  <link rel="icon" href="/favicon.png" type="image/png">
  <link rel="stylesheet" href="/viewer.css">
</head>
<body data-guest-bootstrap="false">
  <a class="skip-link" href="#mainContent">跳到主要內容 · Skip to main content</a>
  <header class="site-header">
    <div class="brand-lockup">
      <span class="brand-mark" aria-hidden="true">
        <img class="brand-mark-image brand-mark-image--light" src="/assets/service-weave-mark-light-v1.png" alt="" width="1024" height="1024" decoding="async">
        <img class="brand-mark-image brand-mark-image--dark" src="/assets/service-weave-mark-dark-v1.png" alt="" width="1024" height="1024" decoding="async">
      </span>
      <div>
      <p class="eyebrow">SING YIN SECONDARY SCHOOL</p>
      <p class="brand-title">導學風紀值班表生成系統</p>
      <p class="brand-subtitle" lang="en">Study Prefect Duty Roster System</p>
      </div>
    </div>
    <label class="theme-toggle" for="themeSelect">
      <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18">
        <path d="M12 3a9 9 0 1 0 0 18V3Z"></path>
        <circle cx="12" cy="12" r="9"></circle>
      </svg>
      <span class="sr-only">外觀 · Appearance</span>
      <select id="themeSelect" aria-label="外觀：跟隨系統 · Appearance: System" data-testid="public-theme-selector">
        <option value="system">跟隨系統 · System</option>
        <option value="light">淺色 · Light</option>
        <option value="dark">深色 · Dark</option>
      </select>
    </label>
  </header>

  <main id="mainContent" class="page-shell" tabindex="-1">
    <section id="guestState" class="access-portal" aria-labelledby="guestTitle" aria-describedby="guestDescription guestDescriptionEn">
      <div class="portal-story">
        <div id="portalStoryMedia" class="portal-story-media" aria-hidden="true">
          <img class="portal-story-image portal-story-image--light" src="/assets/entrance-operations-light-v1.webp" alt="" width="1760" height="941" fetchpriority="high" decoding="async">
          <img class="portal-story-image portal-story-image--dark" src="/assets/entrance-operations-dark-v1.webp" alt="" width="1760" height="941" fetchpriority="high" decoding="async">
          <span class="portal-story-veil"></span>
        </div>
        <h1 id="guestTitle">查看已發布週表，或管理本週值班</h1>
        <p id="guestDescription" class="portal-lead">分享連結可直接查看；登入後可生成、核對、發布、匯出及處理已發布後請假。</p>
        <p id="guestDescriptionEn" class="portal-lead portal-lead--en" lang="en">Open a roster share directly, or sign in to generate, review, publish, export, and handle published-duty absences.</p>

        <nav class="mobile-entry-actions" aria-label="立即進入 · Continue to the workbench">
          <span class="mobile-entry-label">立即進入 · CONTINUE</span>
          <a id="mobileAdminLogin" class="mobile-entry-action mobile-entry-action--admin" data-entry-role="admin" href="/auth/login">
            <span><strong>管理員登入</strong><small lang="en">Administrator sign in</small></span>
            <span aria-hidden="true">→</span>
          </a>
          <a id="mobileGuestEnter" class="mobile-entry-action mobile-entry-action--guest" data-entry-role="guest" href="/guest">
            <span><strong>進入訪客示範</strong><small lang="en">Try the fictional demo</small></span>
            <span aria-hidden="true">→</span>
          </a>
        </nav>

        <section class="devotional-prompt" aria-labelledby="landingDevotionalTitle">
          <div class="devotional-prompt-heading">
            <div>
              <span class="devotional-prompt-kicker">安靜開始 · A QUIET BEGINNING</span>
              <h2 id="landingDevotionalTitle">今日經文與靈修提醒</h2>
            </div>
            <button id="refreshLandingVerse" class="verse-refresh" type="button" aria-label="換一篇經文 · Show another verse">
              <svg aria-hidden="true" viewBox="0 0 24 24" width="17" height="17"><path d="M20 11a8 8 0 1 0-2.3 5.7"></path><path d="M20 4v7h-7"></path></svg>
              <span>換一篇</span>
            </button>
          </div>
          <blockquote class="service-note" aria-live="polite">
            <p id="landingVerseZh">「你們所做的一切都要憑愛心而做。」</p>
            <p id="landingVerseEn" class="service-note-en" lang="en">“Let all that you do be done with love.”</p>
            <footer>
              <cite><span id="landingReferenceZh">哥林多前書 16:14</span> · <span id="landingReferenceEn" lang="en">1 Corinthians 16:14</span></cite>
              <span class="translation-label">和合本修訂版 2010（神版） · NKJV</span>
            </footer>
          </blockquote>
          <div class="devotional-reflection">
            <span aria-hidden="true">✦</span>
            <p><strong id="landingReflectionZh">凡事憑愛心而行</strong><span id="landingPrayerZh">主啊，願愛約束我的語氣、決定和每一項服事。</span></p>
            <p lang="en"><strong id="landingReflectionEn">Let All Be Done in Love</strong><span id="landingPrayerEn">Lord, let love govern my tone, decisions, and every act of service.</span></p>
          </div>
        </section>
      </div>

      <aside class="access-panel" aria-labelledby="adminPanelTitle">
        <div class="access-panel-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22">
            <path d="M12 3.5 19 6v5.4c0 4.2-2.5 7.7-7 9.1-4.5-1.4-7-4.9-7-9.1V6l7-2.5Z"></path>
            <path d="m9 12 2 2 4-4"></path>
          </svg>
        </div>
        <h2 id="adminPanelTitle">登入管理值班表</h2>
        <p class="access-copy">完成身份驗證後返回本網站，繼續本週工作。</p>
        <p class="access-copy access-copy--en" lang="en">After verification, return here to continue this week’s roster.</p>

        <a id="adminLogin" class="admin-login" data-entry-role="admin" href="/auth/login">
          <span class="admin-login-copy">
            <strong>管理員登入</strong>
            <span lang="en">Administrator sign in</span>
          </span>
          <span class="admin-login-indicator" aria-hidden="true">
            <span class="admin-login-arrow">→</span>
            <span class="admin-login-spinner"></span>
          </span>
        </a>
        <a id="guestEnter" class="guest-enter" data-entry-role="guest" href="/guest">
          <span class="guest-enter-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="19" height="19"><path d="M2.8 12s3.4-6 9.2-6 9.2 6 9.2 6-3.4 6-9.2 6-9.2-6-9.2-6Z"></path><circle cx="12" cy="12" r="2.6"></circle></svg>
          </span>
          <span class="guest-enter-copy"><strong>進入訪客示範</strong><span lang="en">Try the fictional demo</span></span>
          <span aria-hidden="true">→</span>
        </a>
        <p id="loginAssurance" class="login-assurance" aria-live="polite">
          <svg aria-hidden="true" viewBox="0 0 24 24" width="15" height="15"><path d="M8 11V8a4 4 0 0 1 8 0v3"></path><rect x="5" y="11" width="14" height="10" rx="2"></rect></svg>
          <span>受控身份驗證 · Verified sign-in</span>
        </p>

        <section id="welcomeAudioPlayer" class="welcome-audio-player" data-autoplay-state="starting" data-entry-intent="unset" aria-labelledby="welcomeAudioHeading">
          <audio id="welcomeAudio" preload="metadata" playsinline></audio>
          <div class="welcome-audio-main">
            <span class="welcome-audio-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="19" height="19"><path d="M9 18V5l10-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="16" cy="16" r="3"></circle></svg>
            </span>
            <div class="welcome-audio-copy">
              <span id="welcomeAudioHeading">歡迎音樂 · Welcome music</span>
              <strong id="welcomeTrackTitle">正在準備歌單…</strong>
              <small id="welcomeTrackMeta">純音樂 · Instrumental</small>
            </div>
            <div class="welcome-audio-actions">
              <button id="welcomeAudioToggle" class="welcome-audio-button" type="button" aria-label="播放歡迎音樂 · Play welcome music" aria-pressed="false">
                <svg class="welcome-audio-play" aria-hidden="true" viewBox="0 0 24 24" width="18" height="18"><path d="m8 5 11 7-11 7V5Z"></path></svg>
                <svg class="welcome-audio-pause" aria-hidden="true" viewBox="0 0 24 24" width="18" height="18"><path d="M8 5v14M16 5v14"></path></svg>
              </button>
              <button id="welcomeAudioNext" class="welcome-audio-button" type="button" aria-label="下一首歡迎音樂 · Next welcome track">
                <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18"><path d="m5 5 10 7-10 7V5ZM18 5v14"></path></svg>
              </button>
            </div>
          </div>
          <div class="welcome-audio-volume">
            <label for="welcomeAudioVolume">音量 · Volume</label>
            <input id="welcomeAudioVolume" type="range" min="0" max="100" step="1" value="50">
            <output id="welcomeAudioVolumeValue" for="welcomeAudioVolume">50%</output>
          </div>
          <p id="welcomeAudioStatus" class="welcome-audio-status" aria-live="polite">頁面會以 50% 音量嘗試播放；音樂不會阻礙登入或訪客示範。 · Playback is attempted at 50%; music never blocks sign-in or the guest demo.</p>
          <div id="welcomeAudioRecovery" class="welcome-audio-recovery" role="group" aria-labelledby="welcomeAudioRecoveryTitle" hidden>
            <strong id="welcomeAudioRecoveryTitle">進入音樂 · Entry sound</strong>
            <p>直接選擇管理員或訪客時，會預設嘗試開啟音樂；你也可安靜繼續。</p>
            <p lang="en">Choosing Administrator or Guest will try to start music by default. You can also continue quietly.</p>
            <div class="welcome-audio-recovery-actions">
              <button id="welcomeAudioEnter" class="welcome-audio-recovery-primary" type="button">預設：開啟音樂 <span lang="en">· Default: Enter with music</span></button>
              <button id="welcomeAudioQuiet" class="welcome-audio-recovery-quiet" type="button">安靜繼續 <span lang="en">· Continue quietly</span></button>
            </div>
          </div>
        </section>

        <div class="access-divider" aria-hidden="true"><span></span></div>
        <div class="guest-help">
          <div class="guest-help-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="20" height="20"><path d="M10 13a5 5 0 0 0 7.1.1l2-2a5 5 0 0 0-7.1-7.1l-1.1 1.1"></path><path d="M14 11a5 5 0 0 0-7.1-.1l-2 2A5 5 0 0 0 12 20l1.1-1.1"></path></svg>
          </div>
          <div>
            <h3>收到值班表分享連結？</h3>
            <p>直接開啟原連結，無需登入；分享內容只供查看。</p>
            <p lang="en">Open the original share link. No sign-in is required and the roster remains read-only.</p>
          </div>
        </div>

        <div class="site-share">
          <button id="shareSite" class="site-share-button" type="button">
            <svg aria-hidden="true" viewBox="0 0 24 24" width="19" height="19"><circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><path d="m8.7 10.7 6.6-4.2M8.7 13.3l6.6 4.2"></path></svg>
            <span><strong>分享網站入口</strong><small lang="en">Share this site</small></span>
          </button>
          <p id="shareSiteStatus" class="site-share-status" aria-live="polite">只會分享首頁，不包含任何值班表或查看密鑰。<span lang="en">Shares the entrance only—never a roster or viewing key.</span></p>
        </div>
        <a class="support-link" href="/support#public">報告網站問題 <span lang="en">· Report a site problem</span></a>
      </aside>

    </section>

    <noscript>
      <section class="state-card state-card--error" role="status">
        <h1>訪客入口仍可閱讀；加密值班表需要啟用 JavaScript</h1>
        <p lang="en">The guest entrance remains readable. Enable JavaScript only when opening an encrypted roster link.</p>
      </section>
    </noscript>

    <section id="loadingState" class="state-card" hidden aria-live="polite" aria-busy="true">
      <span class="sy-secure-pulse" aria-hidden="true"></span>
      <h1>正在安全開啟值班表</h1>
      <p lang="en">Opening the roster securely…</p>
    </section>

    <section id="errorState" class="state-card state-card--error" hidden role="alert">
      <div class="state-icon" aria-hidden="true">!</div>
      <h1 id="errorTitle">未能開啟這份值班表</h1>
      <p id="errorMessage">連結可能不完整、已到期或已由首席導學風紀撤銷。</p>
      <p id="errorMessageEn" class="state-english" lang="en">This link may be incomplete, expired, or revoked. Please ask the Head Study Prefect for a new link.</p>
      <div class="guest-actions">
        <button id="retryShare" class="admin-login" type="button" hidden>重新嘗試 <span lang="en">· Try again</span></button>
        <a class="admin-login" href="/">返回網站入口 <span lang="en">· Return to entrance</span></a>
      </div>
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

      <p id="rosterScrollHint" class="table-scroll-hint">
        <span aria-hidden="true">↔</span>
        左右滑動查看完整星期 <small lang="en">Swipe horizontally to view every weekday</small>
      </p>
      <div class="table-scroll" tabindex="0" aria-label="值班表，可左右捲動 · Roster table, horizontally scrollable" aria-describedby="rosterScrollHint">
        <table id="rosterTable">
          <caption class="sr-only">導學風紀每週值班表 · Weekly Study Prefect Duty Roster</caption>
        </table>
      </div>

      <aside class="viewer-note">
        <p>這是唯讀版本。如有更改，請以首席導學風紀最新發布的連結為準。</p>
        <p lang="en">Read-only copy. If duties change, use the latest link issued by the Head Study Prefect.</p>
        <a class="support-link" href="/support#viewer">報告查看問題 <span lang="en">· Report a viewing problem</span></a>
      </aside>
    </article>
  </main>

  <footer class="site-footer">
    <div class="site-footer-principle">
      <span>服務精神 · 非以役人，乃役於人</span>
      <span lang="en">Service principle · Not to be served, but to serve.</span>
    </div>
    <span class="site-footer-copyright">Copyright © 2026 LI Chuangjie</span>
  </footer>
  <script type="module" src="/viewer.js"></script>
</body>
</html>`;

const PUBLIC_SUPPORT_HTML = `<!doctype html>
<html lang="zh-Hant-HK">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <title>報告問題 · Report a problem</title>
  <link rel="icon" href="/favicon.png" type="image/png">
  <link rel="stylesheet" href="/viewer.css">
</head>
<body class="support-page">
  <main class="page-shell support-shell">
    <header class="support-heading">
      <a class="support-back" href="/">← 返回網站入口 <span lang="en">· Return to entrance</span></a>
      <h1>安全地整理問題資料</h1>
      <p>這個公開表單只會在你的瀏覽器產生一份經整理的報告，不會上傳、儲存或自動傳送任何內容。</p>
      <p lang="en">This public form creates a redacted report only in your browser. Nothing is uploaded, stored, or sent automatically.</p>
    </header>

    <form id="publicSupportForm" class="support-form" novalidate>
      <label>預期情況 · Expected behaviour
        <textarea id="supportExpected" maxlength="1200" required></textarea>
      </label>
      <label>實際情況 · Actual behaviour
        <textarea id="supportActual" maxlength="1200" required></textarea>
      </label>
      <label>最少重現步驟 · Minimal reproduction steps
        <textarea id="supportSteps" maxlength="1600" required></textarea>
      </label>
      <details class="support-details">
        <summary>加入分類、影響與安全提示 <span lang="en">· Add category, impact, and safety guidance</span></summary>
        <div class="support-details-content">
          <section class="support-safety" aria-labelledby="supportSafetyTitle">
            <h2 id="supportSafetyTitle">提交前請先移除敏感內容</h2>
            <p>不要填寫姓名、值班表內容、請假資料、密碼、登入憑證、查看密鑰、完整網址查詢字串或完整日誌。</p>
            <p lang="en">Do not include names, roster or leave content, passwords, credentials, viewing keys, URL query strings, or complete logs.</p>
          </section>
          <label>問題類別 · Category
            <select id="supportCategory" required>
              <option value="viewer">值班表查看 · Roster viewing</option>
              <option value="access">進入網站 · Site access</option>
              <option value="display">顯示或無障礙 · Display or accessibility</option>
              <option value="other">其他 · Other</option>
            </select>
          </label>
          <label>影響（選填） · Impact (optional)
            <textarea id="supportImpact" maxlength="800"></textarea>
          </label>
        </div>
      </details>
      <div class="support-actions">
        <button id="supportBuild" class="admin-login" type="submit">產生安全報告 <span lang="en">· Build safe report</span></button>
        <button id="supportReset" class="guest-enter" type="reset">清除 <span lang="en">· Clear</span></button>
      </div>
    </form>

    <section id="supportResult" class="support-result" hidden aria-live="polite">
      <h2>報告已在瀏覽器準備好</h2>
      <p>事件編號 · Incident ID: <strong id="supportIncidentId"></strong></p>
      <p>下載或複製後，由你自行選擇安全的傳送方式；系統不會自動提交。</p>
      <p lang="en">Download or copy the report, then choose an appropriate channel yourself. The system never submits it automatically.</p>
      <div class="support-actions">
        <button id="supportDownload" class="admin-login" type="button">下載 JSON <span lang="en">· Download JSON</span></button>
        <button id="supportCopy" class="guest-enter" type="button">複製摘要 <span lang="en">· Copy summary</span></button>
        <a id="supportEmail" class="guest-enter" href="mailto:s10777@syss.edu.hk">開啟電郵 <span lang="en">· Open email</span></a>
      </div>
      <p id="supportStatus" class="site-share-status" role="status"></p>
    </section>
  </main>
  <footer class="site-footer">
    <div class="site-footer-principle"><span>服務精神 · 非以役人，乃役於人</span><span lang="en">Service principle · Not to be served, but to serve.</span></div>
    <span class="site-footer-copyright">Copyright © 2026 LI Chuangjie</span>
  </footer>
  <script type="module" src="/support-feedback.js"></script>
</body>
</html>`;

const PUBLIC_SUPPORT_JS = `const form = document.getElementById('publicSupportForm');
const result = document.getElementById('supportResult');
const incidentIdNode = document.getElementById('supportIncidentId');
const statusNode = document.getElementById('supportStatus');
const downloadButton = document.getElementById('supportDownload');
const copyButton = document.getElementById('supportCopy');
const emailLink = document.getElementById('supportEmail');
let preparedReport = null;

const normalizedText = (id, maximum) => document.getElementById(id).value
  .replace(/[\\u0000-\\u0008\\u000B\\u000C\\u000E-\\u001F\\u007F]/g, ' ')
  .replace(/\\r\\n?/g, '\\n')
  .trim()
  .slice(0, maximum);

const newIncidentId = () => 'FB-' + crypto.randomUUID().replaceAll('-', '').slice(0, 16).toUpperCase();

const reportSummary = report => [
  'Incident ID: ' + report.incident_id,
  'Created (UTC): ' + report.created_at_utc,
  'Source: ' + report.source,
  'Category: ' + report.category,
  '',
  'Expected:', report.expected_behavior,
  '',
  'Actual:', report.actual_behavior,
  '',
  'Reproduction steps:', report.reproduction_steps,
  '',
  'Impact:', report.impact || '(not supplied)',
].join('\\n');

form.addEventListener('submit', event => {
  event.preventDefault();
  if (!form.reportValidity()) return;
  const source = location.hash === '#viewer' ? 'public_viewer' : 'public_entrance';
  preparedReport = Object.freeze({
    schema_version: 'sing-yin-browser-support-report-v1',
    incident_id: newIncidentId(),
    created_at_utc: new Date().toISOString(),
    source,
    actor_mode: 'public',
    category: document.getElementById('supportCategory').value,
    expected_behavior: normalizedText('supportExpected', 1200),
    actual_behavior: normalizedText('supportActual', 1200),
    reproduction_steps: normalizedText('supportSteps', 1600),
    impact: normalizedText('supportImpact', 800),
    collection: Object.freeze({ server_persistence: false, attachments: false, automatic_transmission: false }),
  });
  incidentIdNode.textContent = preparedReport.incident_id;
  emailLink.href = 'mailto:s10777@syss.edu.hk?subject=' + encodeURIComponent('Service Weave support ' + preparedReport.incident_id);
  statusNode.textContent = '';
  result.hidden = false;
  result.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' });
});

form.addEventListener('reset', () => {
  preparedReport = null;
  result.hidden = true;
  statusNode.textContent = '';
});

downloadButton.addEventListener('click', () => {
  if (!preparedReport) return;
  const blob = new Blob([JSON.stringify(preparedReport, null, 2)], { type: 'application/json' });
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = preparedReport.incident_id + '-redacted-report.json';
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
  statusNode.textContent = '已下載；請先檢查內容再傳送。 · Downloaded; review it before sending.';
});

copyButton.addEventListener('click', async () => {
  if (!preparedReport) return;
  try {
    await navigator.clipboard.writeText(reportSummary(preparedReport));
    statusNode.textContent = '已複製安全摘要。 · Safe summary copied.';
  } catch {
    statusNode.textContent = '瀏覽器未允許複製；請改用下載。 · Copy was blocked; use download instead.';
  }
});`;

const VIEWER_CSS = `:root {
  color-scheme: light dark;
  --canvas: #f3f1ec;
  --surface: #fffefa;
  --surface-muted: #f7f5ef;
  --surface-raised: #ffffff;
  --ink: #1f2927;
  --ink-muted: #5d6966;
  --line: #d8ddd9;
  --line-strong: #b9c4bf;
  --brand: #176d68;
  --brand-soft: #e5f0ed;
  --action: #244f62;
  --action-hover: #183f51;
  --action-ink: #ffffff;
  --focus-ring: #075d70;
  --gold: #a87935;
  --devotional-surface: #fff9e8;
  --devotional-control: #fffdf7;
  --devotional-ink: #6f542c;
  --devotional-muted: #7f6030;
  --portal-story: #e9efeb;
  --portal-story-ink: #172523;
  --portal-story-muted: #4c615d;
  --ambient-brand: rgba(23, 109, 104, 0.1);
  --ambient-gold: rgba(168, 121, 53, 0.08);
  --table-head: #254d4a;
  --vacant-bg: #fff1d5;
  --vacant-ink: #845b19;
  --danger: #9d3e36;
  --danger-soft: #f9ebe8;
  --shadow: 0 24px 64px rgba(31, 41, 39, 0.11);
  --shadow-raised: 0 18px 46px rgba(28, 46, 42, 0.14);
  --radius-large: 24px;
  --radius-medium: 14px;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif;
}

* { box-sizing: border-box; }

html { min-width: 320px; background: var(--canvas); }

body {
  min-height: 100vh;
  min-height: 100dvh;
  margin: 0;
  color: var(--ink);
  background:
    radial-gradient(circle at 8% 4%, var(--ambient-brand), transparent 30rem),
    radial-gradient(circle at 94% 24%, var(--ambient-gold), transparent 26rem),
    var(--canvas);
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  transition: color 220ms var(--ease-standard), background-color 220ms var(--ease-standard);
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
  justify-content: space-between;
  gap: 20px;
  padding-block: 28px 18px;
}

.brand-lockup {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.brand-mark {
  position: relative;
  flex: 0 0 auto;
  display: block;
  width: 48px;
  height: 48px;
}

.brand-mark-image {
  position: absolute;
  inset: 0;
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: opacity 180ms ease;
}

.brand-mark-image--dark { opacity: 0; }
:root[data-theme="dark"] .brand-mark-image--light { opacity: 0; }
:root[data-theme="dark"] .brand-mark-image--dark { opacity: 1; }

.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  padding: 9px 13px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: color-mix(in srgb, var(--surface) 92%, transparent);
  color: var(--ink-muted);
  font-size: 0.75rem;
  font-weight: 680;
  touch-action: manipulation;
  transition: color 140ms ease, border-color 140ms ease, background-color 180ms ease, transform 100ms ease;
}

.theme-toggle svg { fill: color-mix(in srgb, currentColor 48%, transparent); stroke: currentColor; stroke-width: 1.5; }
.theme-toggle select { min-width: 0; min-height: 24px; padding: 0 22px 0 0; border: 0; color: inherit; background: transparent; font: inherit; font-weight: inherit; cursor: pointer; }
.theme-toggle select:focus { outline: 0; }
.theme-toggle:hover { color: var(--ink); border-color: var(--line-strong); background: var(--surface); }
.theme-toggle:active { transform: scale(0.975); }
.theme-toggle:focus-within,
.skip-link:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }

.skip-link {
  position: fixed;
  z-index: 100;
  top: 10px;
  left: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--ink);
  color: var(--surface);
  font-size: 0.8rem;
  font-weight: 700;
  text-decoration: none;
  transform: translateY(-160%);
  transition: transform 140ms var(--ease-standard);
}

.skip-link:focus { transform: translateY(0); }

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

.access-portal {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.16fr) minmax(340px, 0.84fr);
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: 28px;
  background: var(--surface-raised);
  box-shadow: var(--shadow-raised);
  isolation: isolate;
}

.access-portal[hidden] { display: none; }

.portal-story {
  position: relative;
  z-index: 0;
  min-height: 580px;
  padding: 60px 54px 52px;
  overflow: hidden;
  overflow: clip;
  color: var(--portal-story-ink);
  background: var(--portal-story);
}

.portal-story > :not(.portal-story-media) { position: relative; z-index: 1; }

.portal-story-media {
  --story-shift-x: 0px;
  --story-shift-y: 0px;
  position: absolute;
  z-index: -2;
  inset: -8px;
  overflow: hidden;
  pointer-events: none;
  transform: translate3d(var(--story-shift-x), var(--story-shift-y), 0) scale(1.018);
  transition: transform 280ms var(--ease-standard);
}

.portal-story-image {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 66% center;
  transition: opacity 260ms var(--ease-standard);
}

.portal-story-image--light { opacity: 1; }
.portal-story-image--dark { opacity: 0; }

.portal-story-veil {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--portal-story) 96%, transparent) 0%, color-mix(in srgb, var(--portal-story) 88%, transparent) 52%, color-mix(in srgb, var(--portal-story) 54%, transparent) 100%),
    linear-gradient(0deg, color-mix(in srgb, var(--portal-story) 72%, transparent), transparent 46%);
}

:root[data-theme="dark"] .portal-story-image--light { opacity: 0; }
:root[data-theme="dark"] .portal-story-image--dark { opacity: 1; }

.portal-story::before,
.portal-story::after {
  content: "";
  position: absolute;
  z-index: -1;
  border: 1px solid color-mix(in srgb, var(--brand) 15%, transparent);
  border-radius: 50%;
  pointer-events: none;
}

.portal-story::before { width: 430px; height: 430px; top: -252px; right: -170px; }
.portal-story::after { width: 310px; height: 310px; top: -192px; right: -110px; }

.portal-story > h1 {
  max-width: 670px;
  margin: 25px 0 16px;
  font-size: clamp(2.15rem, 4.8vw, 4rem);
  font-weight: 760;
  letter-spacing: -0.045em;
  line-height: 1.08;
  text-wrap: balance;
}

.portal-lead {
  max-width: 610px;
  margin: 0;
  color: var(--portal-story-muted);
  font-size: 0.98rem;
  line-height: 1.72;
}

.portal-lead--en { margin-top: 5px; font-size: 0.84rem; line-height: 1.6; }

.mobile-entry-actions { display: none; }

.mobile-entry-label {
  color: var(--portal-story-muted);
  font-size: 0.62rem;
  font-weight: 800;
  letter-spacing: 0.12em;
}

.mobile-entry-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 9px 14px;
  border: 1px solid color-mix(in srgb, var(--portal-story-ink) 24%, transparent);
  border-radius: 13px;
  color: var(--portal-story-ink);
  text-decoration: none;
  touch-action: manipulation;
  transition: border-color 140ms ease, background-color 140ms ease, transform 100ms ease;
}

.mobile-entry-action > span:first-child { display: grid; gap: 1px; }
.mobile-entry-action strong { font-size: 0.8rem; }
.mobile-entry-action small { color: inherit; font-size: 0.64rem; font-weight: 560; opacity: 0.76; }
.mobile-entry-action--admin { border-color: var(--action); background: var(--action); color: var(--action-ink); }
.mobile-entry-action--guest { background: color-mix(in srgb, var(--surface) 78%, transparent); }
.mobile-entry-action:active { transform: scale(0.985); }
.mobile-entry-action:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }

.devotional-prompt {
  margin-top: 30px;
  padding: 20px 21px 19px;
  border: 1px solid color-mix(in srgb, var(--gold) 34%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--devotional-surface) 88%, transparent);
  box-shadow: 0 12px 32px color-mix(in srgb, var(--gold) 8%, transparent);
}

.devotional-prompt-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.devotional-prompt-kicker { display: block; color: var(--devotional-muted); font-size: 0.61rem; font-weight: 800; letter-spacing: 0.12em; }
.devotional-prompt h2 { margin: 4px 0 0; font-family: Georgia, "Noto Serif TC", "Songti TC", serif; font-size: 1rem; letter-spacing: 0.01em; }

.verse-refresh {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 44px;
  min-width: 44px;
  flex: 0 0 auto;
  padding: 7px 10px;
  border: 1px solid color-mix(in srgb, var(--gold) 34%, transparent);
  border-radius: 999px;
  background: color-mix(in srgb, var(--devotional-control) 86%, transparent);
  color: var(--devotional-ink);
  cursor: pointer;
  font-size: 0.7rem;
  font-weight: 720;
  touch-action: manipulation;
  transition: border-color 140ms ease, background-color 140ms ease, transform 100ms ease;
}

.verse-refresh svg { fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; transition: transform 220ms var(--ease-standard); }
.verse-refresh:hover { border-color: color-mix(in srgb, var(--gold) 62%, transparent); background: var(--devotional-control); }
.verse-refresh:hover svg { transform: rotate(24deg); }
.verse-refresh:active { transform: scale(0.97); }
.verse-refresh:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }

.service-note { margin: 15px 0 0; }
.service-note p { margin: 0; font-family: Georgia, "Noto Serif TC", "Songti TC", serif; font-size: 1rem; font-weight: 600; line-height: 1.58; }
.service-note .service-note-en { margin-top: 6px; color: color-mix(in srgb, var(--portal-story-ink) 72%, transparent); font-size: 0.78rem; font-weight: 500; }
.service-note footer { display: flex; align-items: flex-end; justify-content: space-between; gap: 8px 16px; flex-wrap: wrap; margin-top: 10px; }
.service-note cite { color: var(--devotional-ink); font-size: 0.68rem; font-style: normal; font-weight: 720; }
.translation-label { color: var(--portal-story-muted); font-size: 0.72rem; line-height: 1.4; }

.devotional-reflection {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) minmax(0, 1fr);
  align-items: start;
  gap: 8px 14px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid color-mix(in srgb, var(--gold) 24%, transparent);
  color: color-mix(in srgb, var(--portal-story-ink) 78%, transparent);
}

.devotional-reflection > span { color: var(--gold); font-size: 0.72rem; line-height: 1.55; }
.devotional-reflection p { margin: 0; font-size: 0.67rem; line-height: 1.48; }
.devotional-reflection strong,
.devotional-reflection p > span { display: block; }
.devotional-reflection strong { margin-bottom: 3px; color: var(--portal-story-ink); font-size: 0.71rem; }
.devotional-prompt.is-updating .service-note,
.devotional-prompt.is-updating .devotional-reflection { animation: verse-reveal 240ms var(--ease-standard) both; }

.access-panel {
  align-self: center;
  margin: 28px;
  padding: 39px 34px 34px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: 0 14px 36px rgba(31, 41, 39, 0.08);
}

.access-panel-icon {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  margin-bottom: 22px;
  border-radius: 15px;
  background: var(--brand-soft);
  color: var(--brand);
}

.access-panel-icon svg,
.guest-help-icon svg,
.login-assurance svg { fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.access-panel-icon svg { transition: transform 220ms var(--ease-standard); }
.access-panel h2 { margin: 11px 0 10px; font-size: clamp(1.75rem, 3vw, 2.25rem); letter-spacing: -0.035em; line-height: 1.12; }
.access-copy { margin: 0; color: var(--ink-muted); font-size: 0.87rem; line-height: 1.62; }
.access-copy--en { margin-top: 5px; font-size: 0.76rem; }

/* Directional feedback adapted from Li-Deheng's Uiverse Arrow Flow Button
   (MIT), rewritten with one bounded sheen, honest busy state and keyboard focus. */
.access-panel .admin-login {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  width: 100%;
  min-height: 58px;
  margin-top: 26px;
  padding: 11px 15px 11px 18px;
  border-color: var(--action);
  border-radius: 14px;
  background: var(--action);
  color: var(--action-ink);
  box-shadow: 0 10px 24px color-mix(in srgb, var(--action) 20%, transparent);
  touch-action: manipulation;
}

.access-panel .admin-login::before {
  position: absolute;
  z-index: 0;
  inset: 0 auto 0 -26%;
  width: 22%;
  background: linear-gradient(105deg, transparent, color-mix(in srgb, white 42%, transparent), transparent);
  content: "";
  pointer-events: none;
  transform: skewX(-17deg) translateX(-180%);
  transition: transform 460ms var(--ease-standard);
}

.access-panel .admin-login > * { position: relative; z-index: 1; }

.admin-login-copy { display: grid; gap: 1px; text-align: left; }
.admin-login-copy strong { font-size: 0.87rem; }
.admin-login-copy span { font-size: 0.66rem; font-weight: 560; opacity: 0.78; }
.admin-login-indicator { display: grid; place-items: center; width: 20px; height: 20px; margin-left: auto; }
.admin-login-arrow,
.admin-login-spinner { grid-area: 1 / 1; }
.admin-login-arrow { font-size: 1.1rem; transition: opacity 120ms ease, transform 160ms var(--ease-standard); }
.admin-login-spinner {
  width: 15px;
  height: 15px;
  border: 2px solid color-mix(in srgb, currentColor 42%, transparent);
  border-top-color: currentColor;
  border-radius: 50%;
  opacity: 0;
  transform: scale(0.78);
}
.access-panel .admin-login:hover { border-color: var(--action-hover); background: var(--action-hover); box-shadow: 0 14px 28px color-mix(in srgb, var(--action) 25%, transparent); }
.access-panel .admin-login:hover::before { transform: skewX(-17deg) translateX(690%); }
.access-panel .admin-login:hover .admin-login-arrow { transform: translateX(3px); }
.access-panel .admin-login:active { transform: translateY(0) scale(0.985); }
.access-panel .admin-login[data-connecting="true"] { pointer-events: none; opacity: 0.88; }
.access-panel .admin-login[data-connecting="true"] .admin-login-arrow { opacity: 0; transform: translateX(5px); }
.access-panel .admin-login[data-connecting="true"] .admin-login-spinner { opacity: 1; transform: scale(1); animation: spin 760ms linear infinite; }

.guest-enter {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  width: 100%;
  min-height: 54px;
  margin-top: 10px;
  padding: 10px 14px;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: var(--surface);
  color: var(--ink);
  text-decoration: none;
  touch-action: manipulation;
  transition: border-color 140ms ease, background-color 140ms ease, transform 100ms ease, box-shadow 160ms ease;
}
.guest-enter:hover { border-color: var(--brand); background: var(--surface-muted); box-shadow: 0 8px 20px color-mix(in srgb, var(--brand) 10%, transparent); }
.guest-enter:active { transform: scale(0.985); }
.guest-enter:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }
.guest-enter-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 11px; background: var(--brand-soft); color: var(--brand); }
.guest-enter-icon svg { fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; transition: transform 220ms var(--ease-standard); }
.guest-enter-copy { display: grid; gap: 1px; min-width: 0; text-align: left; }
.guest-enter-copy strong { font-size: 0.8rem; }
.guest-enter-copy span { color: var(--ink-muted); font-size: 0.65rem; font-weight: 560; }

.login-assurance { display: flex; align-items: center; justify-content: center; gap: 6px; margin: 10px 0 0; color: var(--ink-muted); font-size: 0.66rem; line-height: 1.4; }
.welcome-audio-player {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: color-mix(in srgb, var(--surface-muted) 82%, var(--surface));
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 36%, transparent);
}
.welcome-audio-main { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 11px; }
.welcome-audio-mark { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 12px; background: var(--brand-soft); color: var(--brand); }
.welcome-audio-mark svg,
.welcome-audio-button svg { fill: none; stroke: currentColor; stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.8; }
.welcome-audio-copy { display: grid; min-width: 0; gap: 1px; }
.welcome-audio-copy > span { color: var(--ink-muted); font-size: 0.61rem; font-weight: 720; letter-spacing: 0.04em; text-transform: uppercase; }
.welcome-audio-copy strong { overflow: hidden; font-size: 0.75rem; text-overflow: ellipsis; white-space: nowrap; }
.welcome-audio-copy small { overflow: hidden; color: var(--ink-muted); font-size: 0.62rem; text-overflow: ellipsis; white-space: nowrap; }
.welcome-audio-actions { display: flex; gap: 6px; }
.welcome-audio-button {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  padding: 0;
  border: 1px solid var(--line-strong);
  border-radius: 13px;
  background: var(--surface);
  color: var(--action);
  cursor: pointer;
  touch-action: manipulation;
  transition: color 140ms ease, border-color 140ms ease, background-color 140ms ease, transform 100ms ease, box-shadow 160ms ease;
}
.welcome-audio-button:hover { border-color: var(--action); background: color-mix(in srgb, var(--brand-soft) 65%, var(--surface)); box-shadow: 0 7px 16px color-mix(in srgb, var(--action) 12%, transparent); }
.welcome-audio-button:active { transform: scale(0.96); }
.welcome-audio-button:focus-visible,
.welcome-audio-volume input:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }
.welcome-audio-pause { display: none; }
.welcome-audio-player[data-playing="true"] .welcome-audio-play { display: none; }
.welcome-audio-player[data-playing="true"] .welcome-audio-pause { display: block; }
.welcome-audio-volume { display: grid; grid-template-columns: auto minmax(70px, 1fr) 34px; align-items: center; gap: 9px; margin-top: 12px; }
.welcome-audio-volume label,
.welcome-audio-volume output { color: var(--ink-muted); font-size: 0.61rem; font-weight: 650; }
.welcome-audio-volume output { text-align: right; font-variant-numeric: tabular-nums; }
.welcome-audio-volume input { width: 100%; height: 22px; margin: 0; accent-color: var(--action); cursor: pointer; }
.welcome-audio-status { margin: 7px 0 0; color: var(--ink-muted); font-size: 0.59rem; line-height: 1.45; }
.welcome-audio-recovery { margin-top: 12px; padding: 12px; border: 1px solid var(--gold); border-radius: 13px; background: var(--devotional-control); color: var(--ink); }
.welcome-audio-recovery[hidden] { display: none; }
.welcome-audio-recovery strong { display: block; font-size: 0.72rem; }
.welcome-audio-recovery p { margin: 5px 0 0; color: var(--ink-muted); font-size: 0.62rem; line-height: 1.45; }
.welcome-audio-recovery-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.welcome-audio-recovery-actions button { min-height: 44px; padding: 9px 12px; border: 1px solid var(--line-strong); border-radius: 12px; font: inherit; font-size: 0.68rem; font-weight: 720; cursor: pointer; touch-action: manipulation; }
.welcome-audio-recovery-primary { background: var(--action); color: var(--action-ink); }
.welcome-audio-recovery-quiet { background: var(--surface); color: var(--ink); }
.welcome-audio-recovery-actions button:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }
.access-divider { display: flex; align-items: center; margin: 26px 0 22px; }
.access-divider::before,
.access-divider::after { content: ""; flex: 1; height: 1px; background: var(--line); }
.access-divider span { width: 6px; height: 6px; margin-inline: 9px; border: 1px solid var(--line-strong); border-radius: 50%; }

.guest-help { display: grid; grid-template-columns: auto 1fr; gap: 12px; }
.guest-help-icon { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 12px; background: var(--surface-muted); color: var(--ink-muted); }
.guest-help h3 { margin: 0; font-size: 0.82rem; }
.guest-help p { margin: 5px 0 0; color: var(--ink-muted); font-size: 0.71rem; line-height: 1.52; }
.guest-help p[lang="en"] { margin-top: 3px; font-size: 0.66rem; }

.site-share { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--line); }
.site-share-button {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 11px;
  width: 100%;
  min-height: 48px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: 13px;
  background: var(--surface-muted);
  color: var(--ink);
  cursor: pointer;
  text-align: left;
  touch-action: manipulation;
  transition: border-color 140ms ease, background-color 140ms ease, transform 100ms ease;
}
.site-share-button:hover { border-color: var(--line-strong); background: var(--surface); }
.site-share-button:active { transform: scale(0.985); }
.site-share-button:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; }
.site-share-button:disabled { cursor: wait; opacity: 0.68; }
.site-share-button svg { flex: 0 0 auto; fill: none; stroke: var(--action); stroke-linecap: round; stroke-linejoin: round; stroke-width: 1.7; }
.site-share-button span,
.site-share-button strong,
.site-share-button small { display: block; }
.site-share-button strong { font-size: 0.75rem; }
.site-share-button small { margin-top: 2px; color: var(--ink-muted); font-size: 0.63rem; }
.site-share-status { margin: 8px 2px 0; color: var(--ink-muted); font-size: 0.62rem; line-height: 1.48; }
.site-share-status span { display: block; margin-top: 2px; }

.access-portal:not([hidden]) .portal-story { animation: portal-story-enter 380ms var(--ease-standard) both; }
.access-portal:not([hidden]) .access-panel { animation: portal-panel-enter 440ms 70ms var(--ease-standard) both; }

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

.sy-secure-pulse {
  position: relative;
  width: 42px;
  height: 42px;
  border: 1px solid color-mix(in srgb, var(--brand) 58%, var(--line));
  border-radius: 14px;
  background: var(--brand-soft);
  box-shadow: inset 0 1px 0 color-mix(in srgb, white 42%, transparent), 0 7px 18px color-mix(in srgb, var(--brand) 16%, transparent);
}
.sy-secure-pulse::before,
.sy-secure-pulse::after {
  position: absolute;
  inset: 50% auto auto 50%;
  border-radius: 50%;
  content: "";
  transform: translate(-50%, -50%);
}
.sy-secure-pulse::before { width: 10px; height: 10px; background: var(--brand); }
.sy-secure-pulse::after { width: 22px; height: 22px; border: 1px solid var(--brand); animation: secure-pulse 1.4s var(--ease-standard) infinite; }

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
  gap: 8px;
  border: 1px solid color-mix(in srgb, var(--action) 36%, var(--line));
  border-radius: 999px;
  background: var(--surface);
  color: var(--action);
  font-size: 0.84rem;
  font-weight: 720;
  text-decoration: none;
  transition: border-color 140ms ease, background-color 140ms ease, box-shadow 160ms ease, transform 120ms ease;
}

.admin-login:hover {
  border-color: var(--action);
  background: color-mix(in srgb, var(--action) 8%, var(--surface));
  transform: translateY(-1px);
}

.admin-login:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 3px;
}

.guest-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}
.guest-actions [hidden] { display: none; }

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

.table-scroll-hint { display: none; margin: 0; padding: 10px 18px; border-bottom: 1px solid var(--line); color: var(--ink-muted); background: var(--surface-muted); font-size: 0.72rem; line-height: 1.45; }
.table-scroll-hint span { margin-right: 6px; color: var(--brand); font-weight: 800; }
.table-scroll-hint small { margin-left: 4px; font-size: inherit; }
.table-scroll { overflow-x: auto; outline: none; scrollbar-color: var(--line-strong) transparent; }
.table-scroll:focus-visible { box-shadow: inset 0 0 0 3px var(--focus-ring); }

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
  background: var(--table-head);
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
.cell--vacant { background: color-mix(in srgb, var(--vacant-bg) 70%, var(--surface)); }
.cell--vacant .cell-status { color: var(--vacant-ink); font-weight: 680; }

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
.support-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-top: 12px;
  color: var(--action);
  font-size: 0.72rem;
  font-weight: 720;
  text-decoration-thickness: 1px;
  text-underline-offset: 3px;
}
.support-link:hover { color: var(--brand); }
.support-link:focus-visible,
.support-back:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 3px; border-radius: 5px; }

.support-page { align-items: stretch; }
.support-shell { width: min(100% - 32px, 860px); margin-inline: auto; padding-top: clamp(28px, 7vw, 72px); }
.support-heading { display: grid; gap: 10px; margin-bottom: 20px; }
.support-heading h1 { margin: 4px 0 0; font-size: clamp(2rem, 6vw, 3.5rem); line-height: 1.06; letter-spacing: -0.035em; }
.support-heading p { max-width: 720px; margin: 0; color: var(--ink-muted); line-height: 1.65; }
.support-back { width: fit-content; color: var(--action); font-size: 0.76rem; font-weight: 720; }
.support-safety,
.support-form,
.support-result {
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: var(--shadow);
}
.support-safety { padding: 18px 20px; border-color: color-mix(in srgb, var(--gold) 48%, var(--line)); background: color-mix(in srgb, var(--devotional-surface) 62%, var(--surface)); box-shadow: none; }
.support-safety h2,
.support-result h2 { margin: 0 0 8px; font-size: 1rem; }
.support-safety p,
.support-result p { margin: 4px 0; color: var(--ink-muted); font-size: 0.78rem; line-height: 1.58; }
.support-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; padding: clamp(20px, 4vw, 30px); }
.support-form label { display: grid; gap: 7px; color: var(--ink); font-size: 0.76rem; font-weight: 700; }
.support-form > label { grid-column: 1 / -1; }
.support-details { grid-column: 1 / -1; border-top: 1px solid var(--line); padding-top: 4px; }
.support-details summary { min-height: 44px; padding: 12px 2px; color: var(--action); font-size: 0.76rem; font-weight: 720; cursor: pointer; }
.support-details summary:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; border-radius: 6px; }
.support-details-content { display: grid; gap: 16px; padding-top: 8px; }
.support-details-content label { display: grid; gap: 7px; }
.support-form textarea,
.support-form select {
  width: 100%;
  border: 1px solid var(--line-strong);
  border-radius: 13px;
  background: var(--surface-raised);
  color: var(--ink);
  font: inherit;
  font-weight: 520;
}
.support-form select { min-height: 46px; padding: 9px 12px; }
.support-form textarea { min-height: 108px; padding: 12px; line-height: 1.55; resize: vertical; }
.support-form textarea:focus-visible,
.support-form select:focus-visible { outline: 3px solid var(--focus-ring); outline-offset: 2px; }
.support-actions { display: flex; flex-wrap: wrap; gap: 10px; grid-column: 1 / -1; }
.support-actions .admin-login,
.support-actions .guest-enter { width: auto; min-height: 46px; }
.support-result { margin-top: 16px; padding: clamp(20px, 4vw, 28px); }
.support-result .support-actions { margin-top: 16px; }

@media (max-width: 640px) {
  .support-form { grid-template-columns: 1fr; }
  .support-form label { grid-column: 1 / -1; }
  .support-actions > * { width: 100% !important; justify-content: center; }
}

.site-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding-block: 18px 30px;
  border-top: 1px solid var(--line);
  color: var(--ink-muted);
  font-size: 0.72rem;
}
.site-footer-principle { display: grid; gap: 2px; }
.site-footer-copyright { align-self: end; white-space: nowrap; font-weight: 650; }

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
@keyframes secure-pulse { 0%, 100% { opacity: .3; transform: translate(-50%, -50%) scale(.76); } 50% { opacity: .9; transform: translate(-50%, -50%) scale(1); } }
@keyframes portal-story-enter { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes portal-panel-enter { from { opacity: 0; transform: translateY(12px) scale(0.992); } to { opacity: 1; transform: translateY(0) scale(1); } }
@keyframes portal-strip-enter { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
@keyframes verse-reveal { from { opacity: 0.35; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

:root[data-theme="light"] { color-scheme: light; }

:root[data-theme="dark"] {
  color-scheme: dark;
  --canvas: #0c1217;
  --surface: #121b21;
  --surface-muted: #172128;
  --surface-raised: #10191f;
  --ink: #edf3f0;
  --ink-muted: #a8b6b1;
  --line: #2b383d;
  --line-strong: #435258;
  --brand: #80c9c0;
  --brand-soft: #173331;
  --action: #91b7c5;
  --action-hover: #a8cbd5;
  --action-ink: #08161b;
  --focus-ring: #b7e4ee;
  --gold: #d0ad68;
  --devotional-surface: #241f18;
  --devotional-control: #2b261e;
  --devotional-ink: #e5c47d;
  --devotional-muted: #c7a55f;
  --portal-story: #16221f;
  --portal-story-ink: #eef4f0;
  --portal-story-muted: #adbbb5;
  --ambient-brand: rgba(128, 201, 192, 0.075);
  --ambient-gold: rgba(208, 173, 104, 0.055);
  --table-head: #193b3a;
  --vacant-bg: #4a3719;
  --vacant-ink: #e7c27e;
  --danger: #f0a29a;
  --danger-soft: #412421;
  --shadow: 0 28px 76px rgba(0, 0, 0, 0.36);
  --shadow-raised: 0 28px 72px rgba(0, 0, 0, 0.4);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --canvas: #0c1217;
    --surface: #121b21;
    --surface-muted: #172128;
    --surface-raised: #10191f;
    --ink: #edf3f0;
    --ink-muted: #a8b6b1;
    --line: #2b383d;
    --line-strong: #435258;
    --brand: #80c9c0;
    --brand-soft: #173331;
    --action: #91b7c5;
    --action-hover: #a8cbd5;
    --action-ink: #08161b;
    --focus-ring: #b7e4ee;
    --gold: #d0ad68;
    --devotional-surface: #241f18;
    --devotional-control: #2b261e;
    --devotional-ink: #e5c47d;
    --devotional-muted: #c7a55f;
    --portal-story: #16221f;
    --portal-story-ink: #eef4f0;
    --portal-story-muted: #adbbb5;
    --ambient-brand: rgba(128, 201, 192, 0.075);
    --ambient-gold: rgba(208, 173, 104, 0.055);
    --table-head: #193b3a;
    --vacant-bg: #4a3719;
    --vacant-ink: #e7c27e;
    --danger: #f0a29a;
    --danger-soft: #412421;
    --shadow: 0 28px 76px rgba(0, 0, 0, 0.36);
    --shadow-raised: 0 28px 72px rgba(0, 0, 0, 0.4);
  }

  :root:not([data-theme="light"]) .portal-story-image--light { opacity: 0; }
  :root:not([data-theme="light"]) .portal-story-image--dark { opacity: 1; }
  :root:not([data-theme="light"]) .brand-mark-image--light { opacity: 0; }
  :root:not([data-theme="light"]) .brand-mark-image--dark { opacity: 1; }
}

@media (hover: hover) and (pointer: fine) {
  .access-panel { transition: border-color 180ms ease, box-shadow 220ms ease, transform 180ms var(--ease-standard); }
  .access-panel:hover { border-color: var(--line-strong); box-shadow: 0 18px 42px rgba(31, 41, 39, 0.12); transform: translateY(-2px); }
  .access-panel:hover .access-panel-icon svg { transform: scale(1.06) rotate(-3deg); }
  .guest-enter:hover .guest-enter-icon svg { transform: scale(1.08); }
}

@media (max-width: 940px) {
  .access-portal { grid-template-columns: 1fr; }
  .portal-story { min-height: auto; padding: 46px 42px 40px; }
  .access-panel { margin: 24px; }
}

@media (max-width: 700px) {
  .site-header,
  .page-shell,
  .site-footer { width: min(100% - 24px, 1180px); }

  .site-header { padding-top: 18px; }
  .page-shell { padding-top: 8px; }
  .portal-story { padding: 36px 24px 31px; }
  .portal-story > h1 { margin-top: 21px; font-size: clamp(2rem, 11vw, 3rem); }
  .access-panel { margin: 14px; padding: 30px 24px 27px; }
  .trust-item { padding-inline: 18px; }
  .roster-heading { display: grid; padding: 26px 22px 22px; }
  .status-chip { justify-self: start; }
  .roster-meta { grid-template-columns: 1fr; }
  .roster-meta > div { padding: 15px 22px; }
  .viewer-note { padding-inline: 22px; }
  .site-footer { display: grid; }
}

@media (max-width: 560px) {
  .site-header { align-items: flex-start; flex-wrap: wrap; gap: 12px; }
  .brand-mark { width: 44px; height: 44px; }
  .theme-toggle { margin-left: auto; padding-inline: 11px; }
  .theme-toggle select { max-width: 156px; white-space: nowrap; }
  .mobile-entry-actions {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 8px;
    margin-top: 21px;
    padding: 11px;
    border: 1px solid color-mix(in srgb, var(--portal-story-ink) 16%, transparent);
    border-radius: 17px;
    background: color-mix(in srgb, var(--portal-story) 72%, transparent);
    box-shadow: 0 12px 28px color-mix(in srgb, var(--portal-story-ink) 8%, transparent);
    backdrop-filter: blur(12px);
  }
  .access-panel > [data-entry-role="admin"],
  .access-panel > [data-entry-role="guest"] { display: none; }
  .devotional-prompt { margin-top: 24px; padding: 18px 17px 17px; }
  .devotional-reflection { grid-template-columns: auto 1fr; }
  .devotional-reflection p[lang="en"] { grid-column: 2; }
}

@media (max-width: 900px) {
  .table-scroll-hint { display: block; }
}

@media (max-width: 390px) {
  .brand-subtitle { display: none; }
  .portal-story { padding-inline: 20px; }
  .portal-story > h1 { font-size: 2rem; }
  .access-panel { padding-inline: 20px; }
  .welcome-audio-main { grid-template-columns: auto minmax(0, 1fr); }
  .welcome-audio-actions { grid-column: 2; justify-content: flex-end; }
  .welcome-audio-copy strong { white-space: normal; }
  .mobile-entry-actions { margin-top: 18px; padding: 9px; }
  .devotional-prompt-heading { align-items: center; }
  .verse-refresh span { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0, 0, 0, 0); }
  .verse-refresh { width: 44px; padding-inline: 0; }
}

@media (forced-colors: active) {
  .access-portal,
  .access-panel,
  .devotional-prompt,
  .admin-login,
  .guest-enter,
  .mobile-entry-actions,
  .mobile-entry-action,
  .theme-toggle,
  .verse-refresh,
  .site-share-button,
  .welcome-audio-button,
  .welcome-audio-player { border: 1px solid CanvasText; }
  .access-panel .admin-login { background: ButtonFace; color: ButtonText; }
  :focus-visible { outline: 3px solid Highlight !important; outline-offset: 3px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .access-panel .admin-login::before { display: none; }
  .portal-story-media { transform: none !important; }
  .brand-mark-image { transition: none !important; }
  .access-panel .admin-login[data-connecting="true"] .admin-login-spinner { animation: none; border-color: currentColor; opacity: .8; }
  .sy-secure-pulse::after { animation: none; opacity: .65; transform: translate(-50%, -50%) scale(1); }
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
const THEME_KEY = 'sing-yin-roster-viewer-theme-v1';
const THEME_STATES = ['system', 'light', 'dark'];
const LANDING_DEVOTIONALS = ${JSON.stringify(LANDING_DEVOTIONALS)};
const WELCOME_TRACKS = ${JSON.stringify(WELCOME_PUBLIC_TRACKS)};
const DEFAULT_WELCOME_VOLUME = 0.50;
const WELCOME_VOLUME_KEY = 'sing-yin:welcome-audio-volume:v1';
const WELCOME_VOLUME_DEFAULT_REVISION_KEY = 'sing-yin:welcome-audio-volume-default-revision:v1';
const WELCOME_VOLUME_DEFAULT_REVISION = 2;
const resolveWelcomeVolumePreference = ${resolveWelcomeVolumePreference.toString()};
const __name = (target) => target;
const createWelcomeEntryController = ${createWelcomeEntryController.toString()};
const classifyWelcomeAudioFailureState = ${classifyWelcomeAudioFailureState.toString()};
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', { fatal: true });

const loadingState = document.getElementById('loadingState');
const guestState = document.getElementById('guestState');
const errorState = document.getElementById('errorState');
const rosterState = document.getElementById('rosterState');
const rosterTable = document.getElementById('rosterTable');
const themeSelect = document.getElementById('themeSelect');
const entryButtons = Array.from(document.querySelectorAll('[data-entry-role]'));
const adminLoginButtons = Array.from(document.querySelectorAll('[data-entry-role="admin"]'));
const portalStory = document.querySelector('.portal-story');
const portalStoryMedia = document.getElementById('portalStoryMedia');
const devotionalPrompt = document.querySelector('.devotional-prompt');
const refreshLandingVerse = document.getElementById('refreshLandingVerse');
const welcomeAudioPlayer = document.getElementById('welcomeAudioPlayer');
const welcomeAudio = document.getElementById('welcomeAudio');
const welcomeAudioToggle = document.getElementById('welcomeAudioToggle');
const welcomeAudioNext = document.getElementById('welcomeAudioNext');
const welcomeAudioVolume = document.getElementById('welcomeAudioVolume');
const welcomeAudioVolumeValue = document.getElementById('welcomeAudioVolumeValue');
const welcomeAudioStatus = document.getElementById('welcomeAudioStatus');
const welcomeAudioRecovery = document.getElementById('welcomeAudioRecovery');
const welcomeAudioEnter = document.getElementById('welcomeAudioEnter');
const welcomeAudioQuiet = document.getElementById('welcomeAudioQuiet');
const welcomeTrackTitle = document.getElementById('welcomeTrackTitle');
const welcomeTrackMeta = document.getElementById('welcomeTrackMeta');
const shareSite = document.getElementById('shareSite');
const shareSiteStatus = document.getElementById('shareSiteStatus');
const errorTitle = document.getElementById('errorTitle');
const errorMessage = document.getElementById('errorMessage');
const errorMessageEn = document.getElementById('errorMessageEn');
const retryShare = document.getElementById('retryShare');

const shareErrorCopy = {
  incomplete: {
    title: '分享連結不完整',
    zh: '請重新開啟首席導學風紀發出的完整連結；不要只複製網址中 # 前面的部分。',
    en: 'Open the complete link issued by the Head Study Prefect. Do not copy only the part before #.',
    retryable: false,
  },
  unavailable: {
    title: '這份值班表已不能使用',
    zh: '連結可能已到期或已被撤銷。請向首席導學風紀索取最新分享連結。',
    en: 'The link may have expired or been revoked. Ask the Head Study Prefect for the latest share link.',
    retryable: false,
  },
  service: {
    title: '查看服務暫時未有回應',
    zh: '請保留此頁並稍後按「重新嘗試」；暫時毋須重新索取分享連結。',
    en: 'Keep this page open and try again shortly. You do not need to request a new link yet.',
    retryable: true,
  },
  invalid: {
    title: '未能核對這份值班表',
    zh: '連結內容可能不完整或已損壞。請重新開啟原本的完整連結；如仍失敗，請索取新連結。',
    en: 'The link content could not be verified. Reopen the original complete link, then request a new one if it still fails.',
    retryable: false,
  },
};

const themeCopy = {
  system: { aria: '外觀：跟隨系統 · Appearance: System' },
  light: { aria: '外觀：淺色 · Appearance: Light' },
  dark: { aria: '外觀：深色 · Appearance: Dark' },
};

function savedTheme() {
  try {
    const value = localStorage.getItem(THEME_KEY) || 'system';
    return THEME_STATES.includes(value) ? value : 'system';
  } catch {
    return 'system';
  }
}

function applyTheme(value, { persist = false } = {}) {
  const theme = THEME_STATES.includes(value) ? value : 'system';
  if (theme === 'system') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.dataset.theme = theme;
  if (themeSelect) {
    themeSelect.value = theme;
    themeSelect.setAttribute('aria-label', themeCopy[theme].aria);
  }
  if (persist) {
    try {
      if (theme === 'system') localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, theme);
    } catch {
      // The appearance still changes for this page when storage is unavailable.
    }
  }
}

applyTheme(savedTheme());

const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function updatePortalStoryDepth(event) {
  if (!portalStory || !portalStoryMedia || !finePointer.matches || reducedMotion.matches) return;
  const bounds = portalStory.getBoundingClientRect();
  const x = ((event.clientX - bounds.left) / bounds.width - 0.5) * 8;
  const y = ((event.clientY - bounds.top) / bounds.height - 0.5) * 6;
  portalStoryMedia.style.setProperty('--story-shift-x', x.toFixed(2) + 'px');
  portalStoryMedia.style.setProperty('--story-shift-y', y.toFixed(2) + 'px');
}

function resetPortalStoryDepth() {
  portalStoryMedia?.style.setProperty('--story-shift-x', '0px');
  portalStoryMedia?.style.setProperty('--story-shift-y', '0px');
}

portalStory?.addEventListener('pointermove', updatePortalStoryDepth, { passive: true });
portalStory?.addEventListener('pointerleave', resetPortalStoryDepth);

themeSelect?.addEventListener('change', event => {
  applyTheme(event.currentTarget.value, { persist: true });
  syncWelcomePlaylist();
});

const systemDarkScheme = window.matchMedia('(prefers-color-scheme: dark)');
let welcomeProfile = '';
let welcomeTrackIndex = 0;
let welcomeDesiredEnabled = true;
let welcomePendingDestination = '';
let welcomeEntryController = null;

function welcomeLandingActive() {
  return window.location.pathname === '/'
    && document.body?.dataset.guestBootstrap !== 'true'
    && !hasShareToken();
}

function resolvedWelcomeProfile() {
  const selected = document.documentElement.dataset.theme;
  if (selected === 'dark') return 'quiet';
  if (selected === 'light') return 'bright';
  return systemDarkScheme.matches ? 'quiet' : 'bright';
}

function storedWelcomeVolume() {
  return resolveWelcomeVolumePreference(
    localStorage,
    DEFAULT_WELCOME_VOLUME,
    WELCOME_VOLUME_KEY,
    WELCOME_VOLUME_DEFAULT_REVISION_KEY,
    WELCOME_VOLUME_DEFAULT_REVISION,
  );
}

function storeWelcomeVolume(value) {
  storeWelcomePreference(WELCOME_VOLUME_DEFAULT_REVISION_KEY, WELCOME_VOLUME_DEFAULT_REVISION);
  storeWelcomePreference(WELCOME_VOLUME_KEY, value);
}

function storeWelcomePreference(key, value) {
  try { localStorage.setItem(key, String(value)); } catch {
    // Playback remains usable for this visit when persistent storage is unavailable.
  }
}

function currentWelcomeTrack() {
  const tracks = WELCOME_TRACKS[welcomeProfile] || [];
  return tracks[welcomeTrackIndex % Math.max(1, tracks.length)] || null;
}

function renderWelcomeTrack() {
  if (!welcomeAudio) return;
  const track = currentWelcomeTrack();
  if (!track) return;
  welcomeAudio.src = '/welcome-audio/' + encodeURIComponent(track.id);
  if (welcomeTrackTitle) welcomeTrackTitle.textContent = track.title;
  if (welcomeTrackMeta) welcomeTrackMeta.textContent = track.artist + ' · 純音樂 · Instrumental';
}

function setWelcomePlayingState(playing) {
  if (welcomeAudioPlayer) welcomeAudioPlayer.dataset.playing = playing ? 'true' : 'false';
  if (welcomeAudioToggle) {
    welcomeAudioToggle.setAttribute('aria-pressed', playing ? 'true' : 'false');
    welcomeAudioToggle.setAttribute(
      'aria-label',
      playing ? '暫停歡迎音樂 · Pause welcome music' : '播放歡迎音樂 · Play welcome music',
    );
  }
}

function setWelcomeAutoplayState(state) {
  if (welcomeAudioPlayer) welcomeAudioPlayer.dataset.autoplayState = state;
}

function classifyWelcomeAudioFailure(error) {
  return classifyWelcomeAudioFailureState({
    errorName: error?.name || '',
    mediaErrorCode: welcomeAudio?.error?.code || 0,
    networkState: welcomeAudio?.networkState || 0,
    readyState: welcomeAudio?.readyState || 0,
    online: navigator.onLine,
  });
}

function setWelcomeRecoveryVisible(visible, destination = '', { focus = false } = {}) {
  welcomePendingDestination = visible ? destination : '';
  if (!welcomeAudioRecovery) return;
  welcomeAudioRecovery.hidden = !visible;
  if (visible && focus) welcomeAudioEnter?.focus({ preventScroll: true });
}

function navigateAfterWelcomeChoice(destination = welcomePendingDestination) {
  setWelcomeRecoveryVisible(false);
  if (destination) window.location.assign(destination);
}

function startWelcomeAudioPlayback() {
  if (!welcomeAudio || !welcomeLandingActive()) return Promise.resolve();
  if (!welcomeAudio.src) renderWelcomeTrack();
  const targetVolume = storedWelcomeVolume();
  welcomeAudio.volume = targetVolume;
  welcomeDesiredEnabled = true;
  setWelcomeAutoplayState('starting');
  return welcomeAudio.play();
}

function markWelcomeAudioPlaying() {
  const targetVolume = welcomeAudio?.volume ?? storedWelcomeVolume();
    setWelcomeAutoplayState('playing');
    setWelcomePlayingState(true);
    if (welcomeAudioRecovery) welcomeAudioRecovery.hidden = true;
    if (welcomeAudioStatus) welcomeAudioStatus.textContent = '正在以 ' + Math.round(targetVolume * 100) + '% 音量播放。 · Playing at ' + Math.round(targetVolume * 100) + '% volume.';
}

function markWelcomeAudioFailure(error, { revealRecovery = true } = {}) {
    setWelcomePlayingState(false);
    const failure = classifyWelcomeAudioFailure(error);
    setWelcomeAutoplayState(failure);
    if (failure === 'blocked' && revealRecovery) setWelcomeRecoveryVisible(true, welcomePendingDestination, { focus: false });
    const messages = {
      blocked: '瀏覽器需要你確認後才可播放聲音。 · Your browser needs a direct action before playing sound.',
      loading: '音樂仍在載入；請稍候再試。 · Music is still loading; try again shortly.',
      transport: '網絡中斷或音樂暫時未能傳送；請檢查連線後重試。 · The connection or audio delivery was interrupted; check the network and retry.',
      decoding: '瀏覽器未能解碼這首音樂；請選擇下一首。 · This track could not be decoded; choose the next track.',
      lifecycle: '頁面狀態已改變，播放嘗試已停止。 · Playback stopped because the page state changed.',
      error: '歡迎音樂暫時未能播放；可按播放鍵重試。 · Welcome music could not start; use play to retry.',
    };
    if (welcomeAudioStatus) welcomeAudioStatus.textContent = messages[failure] || messages.error;
}

function markWelcomeAudioTimeout() {
  setWelcomePlayingState(false);
  setWelcomeAutoplayState('loading');
  if (welcomeAudioStatus) welcomeAudioStatus.textContent = '音樂仍在載入；已繼續開啟所選入口。 · Music is still loading; the selected entry continues.';
}

function playWelcomeAudio({ revealRecovery = true } = {}) {
  let attempt;
  try {
    attempt = startWelcomeAudioPlayback();
  } catch (error) {
    markWelcomeAudioFailure(error, { revealRecovery });
    return Promise.resolve(false);
  }
  return Promise.resolve(attempt).then(() => {
    markWelcomeAudioPlaying();
    return true;
  }).catch((error) => {
    markWelcomeAudioFailure(error, { revealRecovery });
    return false;
  });
}

function pauseWelcomeAudio() {
  if (!welcomeAudio) return;
  welcomeAudio.pause();
  welcomeDesiredEnabled = false;
  welcomeEntryController?.setIntent('quiet');
  setWelcomeRecoveryVisible(false);
  setWelcomeAutoplayState('paused');
  setWelcomePlayingState(false);
  if (welcomeAudioStatus) welcomeAudioStatus.textContent = '歡迎音樂已暫停。 · Welcome music paused.';
}

function advanceWelcomeTrack({ play = false } = {}) {
  const tracks = WELCOME_TRACKS[welcomeProfile] || [];
  if (!tracks.length) return;
  welcomeTrackIndex = (welcomeTrackIndex + 1) % tracks.length;
  renderWelcomeTrack();
  if (play) void playWelcomeAudio({ revealRecovery: false });
}

function syncWelcomePlaylist() {
  if (!welcomeAudio || !welcomeLandingActive()) return;
  const nextProfile = resolvedWelcomeProfile();
  if (nextProfile === welcomeProfile) return;
  const shouldResume = !welcomeAudio.paused;
  welcomeAudio.pause();
  welcomeProfile = nextProfile;
  welcomeTrackIndex = 0;
  renderWelcomeTrack();
  if (shouldResume) void playWelcomeAudio({ revealRecovery: false });
}

function initialiseWelcomeAudio() {
  if (!welcomeAudio || !welcomeAudioPlayer || !welcomeLandingActive()) return;
  const volume = storedWelcomeVolume();
  welcomeDesiredEnabled = true;
  if (welcomeAudioVolume) welcomeAudioVolume.value = String(Math.round(volume * 100));
  if (welcomeAudioVolumeValue) welcomeAudioVolumeValue.textContent = Math.round(volume * 100) + '%';
  syncWelcomePlaylist();

  welcomeAudioToggle?.addEventListener('click', () => {
    if (welcomeAudio.paused) {
      welcomeEntryController?.setIntent('music');
      void playWelcomeAudio();
    }
    else pauseWelcomeAudio();
  });
  welcomeAudioEnter?.addEventListener('click', () => {
    const destination = welcomePendingDestination;
    welcomeEntryController?.setIntent('music');
    if (destination) welcomeEntryController?.enter(destination, '');
    else void playWelcomeAudio({ revealRecovery: true });
  });
  welcomeAudioQuiet?.addEventListener('click', () => {
    const destination = welcomePendingDestination;
    pauseWelcomeAudio();
    navigateAfterWelcomeChoice(destination);
  });
  welcomeAudioNext?.addEventListener('click', () => {
    welcomeEntryController?.setIntent('music');
    advanceWelcomeTrack({ play: welcomeDesiredEnabled || !welcomeAudio.paused });
  });
  welcomeAudioVolume?.addEventListener('input', event => {
    const volumeValue = Math.max(0, Math.min(100, Number(event.target.value) || 0));
    const normalised = volumeValue / 100;
    welcomeAudio.volume = normalised;
    storeWelcomeVolume(normalised);
    if (welcomeAudioVolumeValue) welcomeAudioVolumeValue.textContent = Math.round(volumeValue) + '%';
    if (welcomeAudioStatus && !welcomeAudio.paused) welcomeAudioStatus.textContent = '正在以 ' + Math.round(volumeValue) + '% 音量播放。 · Playing at ' + Math.round(volumeValue) + '% volume.';
  });
  welcomeAudio.addEventListener('ended', () => advanceWelcomeTrack({ play: true }));
  welcomeAudio.addEventListener('error', () => {
    const failure = classifyWelcomeAudioFailure(welcomeAudio.error);
    setWelcomeAutoplayState(failure);
    setWelcomePlayingState(false);
    if (welcomeAudioStatus) welcomeAudioStatus.textContent = failure === 'transport'
      ? '網絡中斷或音樂暫時未能傳送；請檢查連線後重試。 · The connection or audio delivery was interrupted; check the network and retry.'
      : '瀏覽器未能解碼這首音樂；請選擇下一首。 · This track could not be decoded; choose the next track.';
  });
  void playWelcomeAudio({ revealRecovery: true });
}

systemDarkScheme.addEventListener('change', () => {
  if (!document.documentElement.dataset.theme) syncWelcomePlaylist();
});

const landingVerseElements = {
  scriptureZh: document.getElementById('landingVerseZh'),
  scriptureEn: document.getElementById('landingVerseEn'),
  referenceZh: document.getElementById('landingReferenceZh'),
  referenceEn: document.getElementById('landingReferenceEn'),
  reflectionZh: document.getElementById('landingReflectionZh'),
  reflectionEn: document.getElementById('landingReflectionEn'),
  prayerZh: document.getElementById('landingPrayerZh'),
  prayerEn: document.getElementById('landingPrayerEn'),
};

function hongKongDayNumber(now = new Date()) {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone: 'Asia/Hong_Kong',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(now);
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return Math.floor(Date.UTC(Number(values.year), Number(values.month) - 1, Number(values.day)) / 86_400_000);
  } catch {
    return Math.floor(now.getTime() / 86_400_000);
  }
}

let landingVerseIndex = hongKongDayNumber() % LANDING_DEVOTIONALS.length;

function renderLandingVerse(index, { announce = false } = {}) {
  const entry = LANDING_DEVOTIONALS[index % LANDING_DEVOTIONALS.length];
  landingVerseElements.scriptureZh.textContent = '「' + entry.scriptureZh + '」';
  landingVerseElements.scriptureEn.textContent = '“' + entry.scriptureEn + '”';
  landingVerseElements.referenceZh.textContent = entry.referenceZh;
  landingVerseElements.referenceEn.textContent = entry.referenceEn;
  landingVerseElements.reflectionZh.textContent = entry.reflectionZh;
  landingVerseElements.reflectionEn.textContent = entry.reflectionEn;
  landingVerseElements.prayerZh.textContent = entry.prayerZh;
  landingVerseElements.prayerEn.textContent = entry.prayerEn;
  devotionalPrompt?.setAttribute('data-verse-id', entry.id);
  if (announce && devotionalPrompt) {
    devotionalPrompt.classList.remove('is-updating');
    void devotionalPrompt.offsetWidth;
    devotionalPrompt.classList.add('is-updating');
  }
}

renderLandingVerse(landingVerseIndex);

refreshLandingVerse?.addEventListener('click', () => {
  landingVerseIndex = (landingVerseIndex + 1) % LANDING_DEVOTIONALS.length;
  renderLandingVerse(landingVerseIndex, { announce: true });
});

async function copySiteEntrance(url) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(url);
      return;
    } catch {
      // Continue to the local fallback when clipboard permission is unavailable.
    }
  }
  const field = document.createElement('textarea');
  field.value = url;
  field.setAttribute('readonly', '');
  field.style.position = 'fixed';
  field.style.opacity = '0';
  document.body.append(field);
  field.select();
  const copied = document.execCommand('copy');
  field.remove();
  if (!copied) throw new Error('copy_failed');
}

shareSite?.addEventListener('click', async () => {
  const url = new URL('/', window.location.origin).toString();
  const initialStatus = '只會分享首頁，不包含任何值班表或查看密鑰。 Shares the entrance only—never a roster or viewing key.';
  shareSite.disabled = true;
  try {
    if (navigator.share) {
      await navigator.share({
        title: '聖言中學導學風紀值班表生成系統 · Sing Yin Study Prefect Duty Roster System',
        text: '導學風紀值班表生成系統網站入口 · Study Prefect Duty Roster System entrance',
        url,
      });
      shareSiteStatus.textContent = '網站入口已分享；不包含值班表。 · Site entrance shared; no roster was included.';
    } else {
      await copySiteEntrance(url);
      shareSiteStatus.textContent = '網站入口已複製；不包含值班表。 · Site entrance copied; no roster was included.';
    }
  } catch (error) {
    shareSiteStatus.textContent = error?.name === 'AbortError'
      ? initialStatus
      : '未能開啟分享功能，請複製瀏覽器網址。 · Sharing is unavailable; copy the browser address instead.';
  } finally {
    shareSite.disabled = false;
  }
});

const setAdminLoginState = (connecting) => {
  adminLoginButtons.forEach((button) => {
    if (!(button instanceof HTMLAnchorElement)) return;
    if (connecting) {
      button.dataset.connecting = 'true';
      button.setAttribute('aria-busy', 'true');
      button.setAttribute('aria-disabled', 'true');
    } else {
      delete button.dataset.connecting;
      button.removeAttribute('aria-busy');
      button.removeAttribute('aria-disabled');
    }
    const zh = button.querySelector('strong');
    const en = button.querySelector('[lang="en"]');
    if (zh) zh.textContent = connecting ? '正在連接安全登入…' : '管理員登入';
    if (en) en.textContent = connecting ? 'Connecting securely…' : 'Administrator sign in';
  });
};

const trustedEntryDestination = (button) => {
  if (!(button instanceof HTMLAnchorElement)) return '';
  const role = button.dataset.entryRole || '';
  const expectedPath = role === 'admin' ? '/auth/login' : role === 'guest' ? '/guest' : '';
  if (!expectedPath) return '';
  try {
    const destination = new URL(button.href, window.location.href);
    if (destination.origin !== window.location.origin) return '';
    if (destination.pathname !== expectedPath || destination.search || destination.hash) return '';
    return destination.href;
  } catch {
    return '';
  }
};

welcomeEntryController = createWelcomeEntryController({
  play: startWelcomeAudioPlayback,
  navigate: (destination) => navigateAfterWelcomeChoice(destination),
  isPlaying: () => Boolean(welcomeAudio && !welcomeAudio.paused),
  onIntentChange: (intent) => {
    if (welcomeAudioPlayer) welcomeAudioPlayer.dataset.entryIntent = intent;
  },
  onBusyChange: (role, connecting) => {
    if (role === 'admin' || !connecting) setAdminLoginState(connecting);
  },
  onPlaybackStarted: markWelcomeAudioPlaying,
  onPlaybackFailed: (error) => markWelcomeAudioFailure(error, { revealRecovery: false }),
  onPlaybackTimeout: markWelcomeAudioTimeout,
  timeoutMs: 450,
});

entryButtons.forEach((button) => button.addEventListener('click', (event) => {
  if (!(button instanceof HTMLAnchorElement)) return;
  const destination = trustedEntryDestination(button);
  if (!destination) return;
  event.preventDefault();
  welcomeEntryController.enter(destination, button.dataset.entryRole || '');
}));

window.addEventListener('pageshow', () => {
  welcomeEntryController.reset();
});

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

function clearStoredShareToken() {
  try { sessionStorage.removeItem(SESSION_TOKEN_KEY); } catch {
    // Some privacy modes disable session storage; the viewer still fails closed.
  }
}

function showShareError(kind) {
  const copy = shareErrorCopy[kind] || shareErrorCopy.invalid;
  if (!copy.retryable) clearStoredShareToken();
  errorTitle.textContent = copy.title;
  errorMessage.textContent = copy.zh;
  errorMessageEn.textContent = copy.en;
  retryShare.hidden = !copy.retryable;
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
    let fragmentPersisted = false;
    try {
      sessionStorage.setItem(SESSION_TOKEN_KEY, fragment);
      fragmentPersisted = true;
    } catch {
      // The fragment remains available for this page load when storage is blocked.
    }
    if (fragmentPersisted) {
      try {
        history.replaceState(null, '', window.location.pathname);
      } catch {
        // Decryption still works; leaving the fragment is safer than breaking the link.
      }
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

let shareOpenInFlight = false;

async function bootstrapGuestSession() {
  if (document.body?.dataset.guestBootstrap !== 'true') return false;
  showOnly(loadingState);
  try {
    const result = await fetch('/auth/guest/start', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { Accept: 'application/json' },
    });
    if (!result.ok) throw new Error('guest_bootstrap_failed');
    window.location.replace('/');
  } catch {
    showShareError('service');
  }
  return true;
}

async function openSharedRoster() {
  if (window.location.pathname === '/' && !hasShareToken()) {
    showOnly(guestState);
    return;
  }
  if (shareOpenInFlight) return;
  shareOpenInFlight = true;
  retryShare.disabled = true;
  retryShare.setAttribute('aria-busy', 'true');
  showOnly(loadingState);
  try {
    let credentials;
    try {
      credentials = readToken();
    } catch {
      showShareError('incomplete');
      return;
    }
    const { shareId, keyBytes } = credentials;
    let response;
    try {
      response = await fetch('/api/view', {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shareId }),
      });
    } catch {
      showShareError('service');
      return;
    }
    if (response.status === 404) {
      showShareError('unavailable');
      return;
    }
    if (!response.ok) {
      showShareError('service');
      return;
    }
    try {
      const payload = await response.json();
      const snapshot = await decryptSnapshot(shareId, keyBytes, payload);
      renderRoster(snapshot, payload.expiresAt);
    } catch {
      showShareError('invalid');
    }
  } finally {
    shareOpenInFlight = false;
    retryShare.disabled = false;
    retryShare.removeAttribute('aria-busy');
  }
}

retryShare?.addEventListener('click', () => { void openSharedRoster(); });
initialiseWelcomeAudio();
void bootstrapGuestSession().then(started => {
  if (!started) void openSharedRoster();
});
`;

let serviceWeaveFaviconBytesCache = null;

function serviceWeaveFaviconBytes() {
  if (serviceWeaveFaviconBytesCache !== null) return serviceWeaveFaviconBytesCache;
  const binary = atob(SERVICE_WEAVE_FAVICON_BASE64);
  const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  if (bytes.byteLength !== SERVICE_WEAVE_FAVICON_BYTE_LENGTH) {
    throw new Error('service_weave_favicon_length_mismatch');
  }
  serviceWeaveFaviconBytesCache = bytes;
  return serviceWeaveFaviconBytesCache;
}

function serviceWeaveFaviconResponse(request) {
  const bytes = serviceWeaveFaviconBytes();
  return response(request.method === 'HEAD' ? null : bytes, 200, {
    'Content-Type': 'image/png',
    'Content-Length': String(SERVICE_WEAVE_FAVICON_BYTE_LENGTH),
    'Cache-Control': 'public, max-age=31536000, immutable',
    ETag: `"sha256-${SERVICE_WEAVE_FAVICON_SHA256}"`,
  });
}

async function welcomeAudioResponse(request, env, trackId) {
  if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
  const track = WELCOME_TRACK_BY_ID.get(trackId);
  if (!track) return response('Not found', 404, { 'Content-Type': 'text/plain; charset=utf-8' });
  if (!env.ROSTER_ORIGIN || typeof env.ROSTER_ORIGIN.fetch !== 'function') {
    return response('Service unavailable', 503, { 'Content-Type': 'text/plain; charset=utf-8' });
  }

  const originUrl = originUrlFromEnvironment(env);
  originUrl.pathname = '/assets/music/' + track.filename.split('/').map(encodeURIComponent).join('/');
  const headers = new Headers();
  for (const name of ['Accept', 'Range', 'If-Range', 'If-None-Match', 'If-Modified-Since']) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  const upstream = await env.ROSTER_ORIGIN.fetch(new Request(originUrl.toString(), {
    method: request.method,
    headers,
    redirect: 'manual',
  }));
  if (![200, 206, 304, 416].includes(upstream.status)) {
    return response('Not found', upstream.status === 404 ? 404 : 503, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  const contentType = upstream.headers.get('Content-Type') || '';
  if (![304, 416].includes(upstream.status) && !/^audio\//i.test(contentType) && contentType !== 'application/octet-stream') {
    return response('Service unavailable', 503, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  const outputHeaders = new Headers(upstream.headers);
  outputHeaders.delete('Set-Cookie');
  outputHeaders.delete('Server');
  outputHeaders.set('Cache-Control', 'public, max-age=3600');
  outputHeaders.set('Content-Disposition', 'inline');
  outputHeaders.set('X-Content-Type-Options', 'nosniff');
  const body = request.method === 'HEAD' || [304, 416].includes(upstream.status) ? null : upstream.body;
  return new Response(body, { status: upstream.status, headers: outputHeaders });
}

const ACCESS_FAILURE_HTML = `<!doctype html>
<html lang="zh-Hant-HK">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <title>管理員登入未完成 · Admin sign-in incomplete</title>
  <link rel="icon" href="/favicon.png" type="image/png">
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

function gatewayReference() {
  return `GW-${crypto.randomUUID().replaceAll('-', '').slice(0, 12).toUpperCase()}`;
}

function originFailureResponse(reference) {
  const html = `<!doctype html>
<html lang="zh-Hant-HK">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">
  <meta name="referrer" content="no-referrer">
  <meta name="color-scheme" content="light dark">
  <title>工作台暫時未能連接 · Workbench temporarily unavailable</title>
  <link rel="icon" href="/favicon.png" type="image/png">
  <link rel="stylesheet" href="/viewer.css">
</head>
<body>
  <main class="page-shell">
    <section class="state-card state-card--error" role="alert">
      <div class="state-icon" aria-hidden="true">!</div>
      <h1>主機暫時未能連接</h1>
      <p>你的管理員身分已通過核對，但本機工作台暫時未有回應。請稍後重試；如問題持續，請在本機檢查網站及 Cloudflare 服務。</p>
      <p class="state-english" lang="en">Your administrator identity was verified, but the local workbench is not responding. Try again shortly, then check the local site and Cloudflare services if the issue continues.</p>
      <p class="support-reference">支援編號 · Support reference: <strong>${reference}</strong></p>
      <div class="guest-actions">
        <a class="admin-login" href="/">重新嘗試 <span lang="en">· Try again</span></a>
        <a class="admin-login" href="/logout">登出 <span lang="en">· Sign out</span></a>
      </div>
    </section>
  </main>
</body>
</html>`;
  return response(html, 503, {
    'Content-Type': 'text/html; charset=utf-8',
    'Retry-After': '15',
    'X-Sing-Yin-Support-Reference': reference,
  });
}

class AccessValidationError extends Error {
  constructor(reason = 'access_validation_failed') {
    super('access_validation_failed');
    this.name = 'AccessValidationError';
    this.reason = reason;
  }
}

function originPortFromEnvironment(env) {
  const rawPort = env?.ORIGIN_PORT;
  if (rawPort === undefined) return 8080;
  const normalizedPort = typeof rawPort === 'number' ? rawPort : String(rawPort).trim();
  if (
    normalizedPort === ''
    || (typeof normalizedPort === 'string' && !/^\d+$/.test(normalizedPort))
  ) {
    throw new AccessValidationError('origin_port_configuration');
  }
  const port = Number(normalizedPort);
  if (!Number.isSafeInteger(port) || port < 1024 || port > 65_535) {
    throw new AccessValidationError('origin_port_configuration');
  }
  return port;
}

function originUrlFromEnvironment(env) {
  return new URL(`http://127.0.0.1:${originPortFromEnvironment(env)}`);
}

function normalizeAccessConfiguration(env) {
  const rawTeamDomain = typeof env.ACCESS_TEAM_DOMAIN === 'string' ? env.ACCESS_TEAM_DOMAIN.trim() : '';
  const rawAudience = typeof env.ACCESS_AUD === 'string' ? env.ACCESS_AUD : '';
  const audience = rawAudience.trim();
  const encodedAdminConfiguration = typeof env.ADMIN_IDENTITY_ALLOWLIST === 'string'
    ? env.ADMIN_IDENTITY_ALLOWLIST.trim()
    : '';
  if (!encodedAdminConfiguration || encodedAdminConfiguration.length > 8_192) {
    throw new AccessValidationError('admin_allowlist_configuration');
  }
  let rawAdminConfiguration;
  try {
    rawAdminConfiguration = JSON.parse(encodedAdminConfiguration);
  } catch {
    throw new AccessValidationError('admin_allowlist_configuration');
  }
  const rawAdminEmails = rawAdminConfiguration?.emails;
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
    !rawAdminConfiguration
    || typeof rawAdminConfiguration !== 'object'
    || Array.isArray(rawAdminConfiguration)
    || Object.keys(rawAdminConfiguration).length !== 1
    || !Array.isArray(rawAdminEmails)
    || rawAdminEmails.length < 1
    || rawAdminEmails.length > 32
  ) {
    throw new AccessValidationError();
  }
  const adminEmails = [];
  const seenAdminEmails = new Set();
  for (const value of rawAdminEmails) {
    if (
      typeof value !== 'string'
      || value !== value.trim()
      || value !== value.toLowerCase()
      || value.length > 320
      || !/^[^@\s]+@[^@\s]+$/.test(value)
      || seenAdminEmails.has(value)
    ) {
      throw new AccessValidationError();
    }
    seenAdminEmails.add(value);
    adminEmails.push(value);
  }
  return { teamDomain, audience, adminEmails };
}

function cookieValueFromRequest(request, cookieName) {
  const cookieHeader = request.headers.get('Cookie') || '';
  for (const part of cookieHeader.split(';')) {
    const separator = part.indexOf('=');
    if (separator < 1 || part.slice(0, separator).trim() !== cookieName) continue;
    const rawValue = part.slice(separator + 1).trim();
    try {
      return decodeURIComponent(rawValue);
    } catch {
      return rawValue;
    }
  }
  return '';
}

function accessTokenFromRequest(request) {
  const assertion = request.headers.get('Cf-Access-Jwt-Assertion');
  if (assertion && assertion.trim()) return assertion.trim();
  return cookieValueFromRequest(request, ACCESS_COOKIE_NAME);
}

function adminSessionSecret(env) {
  const secret = typeof env.ADMIN_SESSION_SECRET === 'string' ? env.ADMIN_SESSION_SECRET : ''; // pragma: allowlist secret -- environment variable name only
  if (secret.length < 32 || secret.length > 512 || secret !== secret.trim()) {
    throw new AccessValidationError('session_secret_configuration');
  }
  return secret;
}

function guestSessionSecret(env) {
  const secret = typeof env.GUEST_SESSION_SECRET === 'string' ? env.GUEST_SESSION_SECRET : ''; // pragma: allowlist secret -- environment variable name only
  if (secret.length < 32 || secret.length > 512 || secret !== secret.trim()) {
    throw new AccessValidationError('guest_session_secret_configuration');
  }
  return secret;
}

function originPrincipalSecret(env) {
  const secret = typeof env.ORIGIN_PRINCIPAL_SECRET === 'string' ? env.ORIGIN_PRINCIPAL_SECRET : ''; // pragma: allowlist secret -- environment variable name only
  if (secret.length < 32 || secret.length > 512 || secret !== secret.trim()) {
    throw new AccessValidationError('origin_principal_secret_configuration');
  }
  return secret;
}

function authEpoch(env) {
  const raw = env.AUTH_EPOCH ?? 1;
  if (
    (typeof raw !== 'number' && typeof raw !== 'string')
    || (typeof raw === 'string' && !/^[1-9][0-9]{0,9}$/.test(raw))
  ) {
    throw new AccessValidationError('auth_epoch_configuration');
  }
  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value < 1 || value > 2_147_483_647) {
    throw new AccessValidationError('auth_epoch_configuration');
  }
  return value;
}

function originPrincipalKid(env) {
  const raw = env.ORIGIN_PRINCIPAL_KID ?? 'origin-v1';
  if (typeof raw !== 'string' || raw !== raw.trim() || !/^[A-Za-z0-9._-]{1,64}$/.test(raw)) {
    throw new AccessValidationError('origin_principal_kid_configuration');
  }
  return raw;
}

async function hmacKey(secret, usage) {
  return await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    usage,
  );
}

async function adminSessionHmacKey(env, usage) {
  return await hmacKey(adminSessionSecret(env), usage);
}

async function guestSessionHmacKey(env, usage) {
  return await hmacKey(guestSessionSecret(env), usage);
}

async function originPrincipalHmacKey(env, usage) {
  return await hmacKey(originPrincipalSecret(env), usage);
}

function rateLimitBinding(env, bindingName) {
  const binding = env?.[bindingName];
  if (!binding || typeof binding.limit !== 'function') {
    throw new AccessValidationError('rate_limit_configuration');
  }
  return binding;
}

function normalizeRateLimitConfiguration(env) {
  return {
    guestStart: rateLimitBinding(env, GUEST_START_RATE_LIMIT_BINDING),
    publicView: rateLimitBinding(env, PUBLIC_VIEW_RATE_LIMIT_BINDING),
  };
}

function boundedConnectingAddress(request) {
  const rawAddress = (request.headers.get('CF-Connecting-IP') || '').trim();
  if (rawAddress.length < 3 || rawAddress.length > 64 || !/^[0-9A-Fa-f:.]+$/.test(rawAddress)) {
    return 'unidentified-actor';
  }
  return rawAddress.toLowerCase();
}

async function rateLimitActorKey(request, env, scope) {
  const key = await guestSessionHmacKey(env, ['sign']);
  const input = new TextEncoder().encode(`rate-limit-v1\n${scope}\n${boundedConnectingAddress(request)}`);
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', key, input));
  return `rl:v1:${scope}:${encodeBase64Url(signature)}`;
}

function rateLimitErrorResponse(error, retryAfterSeconds, reference = gatewayReference()) {
  const headers = new Headers({
    'Cache-Control': 'no-store, max-age=0',
    'Content-Type': 'application/json; charset=utf-8',
    'Retry-After': String(retryAfterSeconds),
    'X-Sing-Yin-Support-Reference': reference,
  });
  return response(JSON.stringify({ error, reference }), error === 'rate_limited' ? 429 : 503, headers);
}

async function enforcePublicRateLimit(request, env, bindingName, scope) {
  let binding;
  let actorKey;
  try {
    binding = rateLimitBinding(env, bindingName);
    actorKey = await rateLimitActorKey(request, env, scope);
  } catch {
    return rateLimitErrorResponse('edge_protection_unavailable', RATE_LIMIT_FAILURE_RETRY_AFTER_SECONDS);
  }

  try {
    const result = await binding.limit({ key: actorKey });
    if (!result || result.success !== true) {
      return rateLimitErrorResponse('rate_limited', RATE_LIMIT_RETRY_AFTER_SECONDS);
    }
  } catch {
    return rateLimitErrorResponse('edge_protection_unavailable', RATE_LIMIT_FAILURE_RETRY_AFTER_SECONDS);
  }
  return null;
}

async function createAdminSessionToken(email, accessExpiresAt, env, options = {}) {
  const configuration = normalizeAccessConfiguration(env);
  const normalizedEmail = typeof email === 'string' ? email.toLowerCase() : '';
  if (!configuration.adminEmails.includes(normalizedEmail)) throw new AccessValidationError();
  const nowSeconds = Math.floor((options.nowMillis ?? Date.now()) / 1_000);
  const boundedAccessExpiry = Math.floor(accessExpiresAt);
  const expiresAt = Math.min(nowSeconds + ADMIN_SESSION_MAX_AGE_SECONDS, boundedAccessExpiry);
  if (!Number.isSafeInteger(nowSeconds) || !Number.isSafeInteger(expiresAt) || expiresAt <= nowSeconds) {
    throw new AccessValidationError();
  }
  const nonceBytes = new Uint8Array(16);
  crypto.getRandomValues(nonceBytes);
  const payload = {
    v: ADMIN_SESSION_VERSION,
    email: normalizedEmail,
    iat: nowSeconds,
    exp: expiresAt,
    epoch: authEpoch(env),
    nonce: encodeBase64Url(nonceBytes),
  };
  const payloadSegment = encodeBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
  const key = await adminSessionHmacKey(env, ['sign']);
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payloadSegment)));
  return { token: `${payloadSegment}.${encodeBase64Url(signature)}`, payload };
}

function adminSessionSetCookie(token, expiresAt) {
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const maxAge = Math.max(0, Math.min(ADMIN_SESSION_MAX_AGE_SECONDS, expiresAt - nowSeconds));
  return `${ADMIN_SESSION_COOKIE_NAME}=${encodeURIComponent(token)}; Max-Age=${maxAge}; Expires=${new Date(expiresAt * 1_000).toUTCString()}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

function adminSessionClearCookie() {
  return `${ADMIN_SESSION_COOKIE_NAME}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

async function createGuestSessionToken(env, options = {}) {
  const nowSeconds = Math.floor((options.nowMillis ?? Date.now()) / 1_000);
  const expiresAt = nowSeconds + GUEST_SESSION_MAX_AGE_SECONDS;
  if (!Number.isSafeInteger(nowSeconds) || !Number.isSafeInteger(expiresAt)) {
    throw new AccessValidationError();
  }
  const sidBytes = new Uint8Array(16);
  if (options.sidBytes instanceof Uint8Array && options.sidBytes.byteLength === 16) {
    sidBytes.set(options.sidBytes);
  } else {
    crypto.getRandomValues(sidBytes);
  }
  const payload = {
    v: GUEST_SESSION_VERSION,
    sid: encodeBase64Url(sidBytes),
    iat: nowSeconds,
    exp: expiresAt,
    epoch: authEpoch(env),
  };
  const payloadSegment = encodeBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
  const key = await guestSessionHmacKey(env, ['sign']);
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payloadSegment)));
  return { token: `${payloadSegment}.${encodeBase64Url(signature)}`, payload };
}

function guestSessionSetCookie(token, expiresAt) {
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const maxAge = Math.max(0, Math.min(GUEST_SESSION_MAX_AGE_SECONDS, expiresAt - nowSeconds));
  return `${GUEST_SESSION_COOKIE_NAME}=${encodeURIComponent(token)}; Max-Age=${maxAge}; Expires=${new Date(expiresAt * 1_000).toUTCString()}; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

function guestSessionClearCookie() {
  return `${GUEST_SESSION_COOKIE_NAME}=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly; Secure; SameSite=Lax`;
}

async function validateAdminSessionToken(token, env, options = {}) {
  if (typeof token !== 'string' || token.length < 32 || token.length > ADMIN_SESSION_MAX_TOKEN_BYTES) {
    throw new AccessValidationError();
  }
  const parts = token.split('.');
  if (parts.length !== 2 || parts.some(part => !part)) throw new AccessValidationError();
  const [payloadSegment, signatureSegment] = parts;
  const payloadBytes = decodeBase64Url(payloadSegment);
  const signature = decodeBase64Url(signatureSegment);
  if (!payloadBytes || payloadBytes.byteLength < 2 || payloadBytes.byteLength > 1_024 || !signature || signature.byteLength !== 32) {
    throw new AccessValidationError();
  }
  const key = await adminSessionHmacKey(env, ['verify']);
  const verified = await crypto.subtle.verify('HMAC', key, signature, new TextEncoder().encode(payloadSegment));
  if (!verified) throw new AccessValidationError();
  let payload;
  try {
    payload = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(payloadBytes));
  } catch {
    throw new AccessValidationError();
  }
  const nowSeconds = Math.floor((options.nowMillis ?? Date.now()) / 1_000);
  const configuration = normalizeAccessConfiguration(env);
  if (
    !payload
    || typeof payload !== 'object'
    || Array.isArray(payload)
    || Object.keys(payload).sort().join(',') !== 'email,epoch,exp,iat,nonce,v'
    || payload.v !== ADMIN_SESSION_VERSION
    || typeof payload.email !== 'string'
    || payload.email !== payload.email.trim()
    || payload.email !== payload.email.toLowerCase()
    || !configuration.adminEmails.includes(payload.email)
    || !Number.isSafeInteger(payload.iat)
    || !Number.isSafeInteger(payload.exp)
    || payload.iat > nowSeconds + 60
    || payload.exp <= nowSeconds
    || payload.exp <= payload.iat
    || payload.exp - payload.iat > ADMIN_SESSION_MAX_AGE_SECONDS
    || payload.epoch !== authEpoch(env)
    || typeof payload.nonce !== 'string'
    || !/^[A-Za-z0-9_-]{22}$/.test(payload.nonce)
  ) {
    throw new AccessValidationError();
  }
  return payload;
}

async function validateGuestSessionToken(token, env, options = {}) {
  if (typeof token !== 'string' || token.length < 32 || token.length > GUEST_SESSION_MAX_TOKEN_BYTES) {
    throw new AccessValidationError();
  }
  const parts = token.split('.');
  if (parts.length !== 2 || parts.some(part => !part)) throw new AccessValidationError();
  const [payloadSegment, signatureSegment] = parts;
  const payloadBytes = decodeBase64Url(payloadSegment);
  const signature = decodeBase64Url(signatureSegment);
  if (!payloadBytes || payloadBytes.byteLength < 2 || payloadBytes.byteLength > 1_024 || !signature || signature.byteLength !== 32) {
    throw new AccessValidationError();
  }
  const key = await guestSessionHmacKey(env, ['verify']);
  const verified = await crypto.subtle.verify('HMAC', key, signature, new TextEncoder().encode(payloadSegment));
  if (!verified) throw new AccessValidationError();
  let payload;
  try {
    payload = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(payloadBytes));
  } catch {
    throw new AccessValidationError();
  }
  const nowSeconds = Math.floor((options.nowMillis ?? Date.now()) / 1_000);
  if (
    !payload
    || typeof payload !== 'object'
    || Array.isArray(payload)
    || Object.keys(payload).sort().join(',') !== 'epoch,exp,iat,sid,v'
    || payload.v !== GUEST_SESSION_VERSION
    || typeof payload.sid !== 'string'
    || !/^[A-Za-z0-9_-]{22}$/.test(payload.sid)
    || !Number.isSafeInteger(payload.iat)
    || !Number.isSafeInteger(payload.exp)
    || payload.iat > nowSeconds + 60
    || payload.exp <= nowSeconds
    || payload.exp <= payload.iat
    || payload.exp - payload.iat > GUEST_SESSION_MAX_AGE_SECONDS
    || payload.epoch !== authEpoch(env)
  ) {
    throw new AccessValidationError();
  }
  return payload;
}

async function originRequestBinding(request) {
  const url = new URL(request.url);
  const material = [
    request.method.toUpperCase(),
    url.host.toLowerCase(),
    `${url.pathname}${url.search}`,
  ].join('\n');
  return encodeBase64Url(await sha256(material));
}

async function createOriginPrincipalToken(request, principal, env, options = {}) {
  const nowSeconds = Math.floor((options.nowMillis ?? Date.now()) / 1_000);
  const sessionExpiresAt = Number(principal?.exp);
  if (
    !principal
    || !['admin', 'guest'].includes(principal.mode)
    || typeof principal.subject !== 'string'
    || !principal.subject
    || principal.subject.length > 320
    || typeof principal.sid !== 'string'
    || !/^[A-Za-z0-9_-]{22}$/.test(principal.sid)
    || !Number.isSafeInteger(sessionExpiresAt)
    || !Number.isSafeInteger(nowSeconds)
    || sessionExpiresAt <= nowSeconds
  ) {
    throw new AccessValidationError();
  }
  const payload = {
    v: ORIGIN_PRINCIPAL_VERSION,
    aud: ORIGIN_PRINCIPAL_AUDIENCE,
    mode: principal.mode,
    subject: principal.subject,
    sid: principal.sid,
    iat: nowSeconds,
    exp: sessionExpiresAt,
    auth_epoch: authEpoch(env),
    kid: originPrincipalKid(env),
    request_binding: await originRequestBinding(request),
  };
  const payloadSegment = encodeBase64Url(new TextEncoder().encode(JSON.stringify(payload)));
  const key = await originPrincipalHmacKey(env, ['sign']);
  const signature = new Uint8Array(await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payloadSegment)));
  return { token: `${payloadSegment}.${encodeBase64Url(signature)}`, payload };
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
    });
  } catch {
    throw new AccessValidationError('jwks_fetch');
  }
  if (!certificateResponse || !certificateResponse.ok) throw new AccessValidationError('jwks_response');
  const declaredLength = Number(certificateResponse.headers.get('Content-Length') || '0');
  if (Number.isFinite(declaredLength) && declaredLength > ACCESS_JWKS_MAX_BYTES) throw new AccessValidationError();
  let raw;
  try {
    raw = await readBoundedUtf8(certificateResponse, ACCESS_JWKS_MAX_BYTES);
  } catch {
    throw new AccessValidationError('jwks_body');
  }
  let document;
  try {
    document = JSON.parse(raw);
  } catch {
    throw new AccessValidationError('jwks_json');
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
    throw new AccessValidationError('jwt_size');
  }
  const parts = token.split('.');
  if (parts.length !== 3 || parts.some(part => !part)) throw new AccessValidationError('jwt_structure');
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
    throw new AccessValidationError('jwt_header');
  }

  const nowMillis = options.nowMillis ?? Date.now();
  const nowSeconds = Math.floor(nowMillis / 1_000);
  const audiences = typeof payload.aud === 'string' ? [payload.aud] : payload.aud;
  if (payload.iss !== configuration.teamDomain) throw new AccessValidationError('jwt_issuer');
  if (
    !Array.isArray(audiences)
    || !audiences.every(item => typeof item === 'string')
    || !audiences.includes(configuration.audience)
  ) throw new AccessValidationError('jwt_audience');
  if (typeof payload.exp !== 'number' || !Number.isFinite(payload.exp) || nowSeconds >= payload.exp) {
    throw new AccessValidationError('jwt_expiry');
  }
  if (payload.nbf !== undefined && (
    typeof payload.nbf !== 'number'
    || !Number.isFinite(payload.nbf)
    || nowSeconds < payload.nbf
  )) throw new AccessValidationError('jwt_not_before');
  if (
    typeof payload.email !== 'string'
    || payload.email !== payload.email.trim()
    || payload.email.length > 320
    || !/^[^@\s]+@[^@\s]+$/.test(payload.email)
  ) throw new AccessValidationError('jwt_email');
  if (!configuration.adminEmails.includes(payload.email.toLowerCase())) {
    throw new AccessValidationError('jwt_email_allowlist');
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
    throw new AccessValidationError('jwk_import');
  }
  const verified = await crypto.subtle.verify(
    { name: 'RSASSA-PKCS1-v1_5' },
    publicKey,
    signature,
    new TextEncoder().encode(`${headerSegment}.${payloadSegment}`),
  );
  if (!verified) throw new AccessValidationError('jwt_signature');

  return { payload, configuration };
}

function stripAccessCredentials(inputHeaders) {
  const headers = new Headers(inputHeaders);
  for (const name of [...headers.keys()]) {
    const normalized = name.toLowerCase();
    if (
      normalized.startsWith('cf-access-')
      || normalized.startsWith('x-sing-yin-')
      || normalized.startsWith('x-forwarded-')
    ) {
      headers.delete(name);
    }
  }
  const cookieHeader = headers.get('Cookie') || '';
  const retainedCookies = cookieHeader
    .split(';')
    .map(part => part.trim())
    .filter(part => {
      if (!part) return false;
      const separator = part.indexOf('=');
      const name = (separator < 0 ? part : part.slice(0, separator)).trim();
      return name.toLowerCase() !== ACCESS_COOKIE_NAME.toLowerCase()
        && name !== ADMIN_SESSION_COOKIE_NAME
        && name !== GUEST_SESSION_COOKIE_NAME;
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

async function proxyToRosterOrigin(request, env, principal) {
  if (!env.ROSTER_ORIGIN || typeof env.ROSTER_ORIGIN.fetch !== 'function') throw new AccessValidationError();
  const publicUrl = new URL(request.url);
  const originUrl = originUrlFromEnvironment(env);
  originUrl.pathname = publicUrl.pathname;
  originUrl.search = publicUrl.search;
  const headers = stripAccessCredentials(request.headers);
  headers.set('X-Forwarded-Host', publicUrl.host);
  headers.set('X-Forwarded-Proto', 'https');
  const originPrincipal = await createOriginPrincipalToken(request, principal, env);
  headers.set(ORIGIN_PRINCIPAL_HEADER, originPrincipal.token);
  const init = {
    method: request.method,
    headers,
    redirect: 'manual',
  };
  if (request.method !== 'GET' && request.method !== 'HEAD') init.body = request.body;
  const originRequest = new Request(originUrl.toString(), init);
  return await env.ROSTER_ORIGIN.fetch(originRequest);
}

async function notifyOriginSessionRevocation(request, env, principal) {
  const revokeUrl = new URL('/api/auth/session/revoke', request.url);
  const revokeRequest = new Request(revokeUrl.toString(), {
    method: 'POST',
    headers: request.headers,
  });
  const result = await proxyToRosterOrigin(revokeRequest, env, principal);
  if (!result || result.status !== 204) throw new AccessValidationError('origin_logout_rejected');
}

function accessFailureResponse(status = 403, reference = '') {
  const headers = { 'Content-Type': 'text/html; charset=utf-8' };
  if (reference) headers['X-Sing-Yin-Support-Reference'] = reference;
  return response(ACCESS_FAILURE_HTML, status, headers);
}

function loggedAccessFailure(request, phase, error) {
  const reference = gatewayReference();
  const reason = error instanceof AccessValidationError ? error.reason : 'unexpected_error';
  console.warn(JSON.stringify({
    event: 'admin_login_bridge_failure',
    reference,
    phase,
    reason,
    ray: (request.headers.get('CF-Ray') || '').slice(0, 32),
    assertionPresent: Boolean(request.headers.get('Cf-Access-Jwt-Assertion')),
    authorizationCookiePresent: Boolean(cookieValueFromRequest(request, ACCESS_COOKIE_NAME)),
  }));
  return accessFailureResponse(403, reference);
}

function redirectResponse(destination, requestUrl, status = 302) {
  return response(null, status, { Location: new URL(destination, requestUrl).toString() });
}

function logoutResponse(requestUrl) {
  const headers = new Headers({
    Location: new URL('/cdn-cgi/access/logout', requestUrl).toString(),
  });
  headers.append('Set-Cookie', adminSessionClearCookie());
  headers.append('Set-Cookie', guestSessionClearCookie());
  return response(null, 302, headers);
}

function authLogoutResponse(requestUrl) {
  const headers = new Headers({
    Location: new URL('/', requestUrl).toString(),
  });
  headers.append('Set-Cookie', adminSessionClearCookie());
  headers.append('Set-Cookie', guestSessionClearCookie());
  return response(null, 303, headers);
}

function isConfigurationError(error) {
  return error instanceof AccessValidationError && error.reason.endsWith('_configuration');
}

async function gatewayPrincipalFromRequest(request, env) {
  const adminToken = cookieValueFromRequest(request, ADMIN_SESSION_COOKIE_NAME);
  let invalidCredential = false;
  if (adminToken) {
    try {
      const session = await validateAdminSessionToken(adminToken, env);
      return {
        mode: 'admin',
        subject: session.email,
        sid: session.nonce,
        exp: session.exp,
      };
    } catch (error) {
      if (isConfigurationError(error)) throw error;
      invalidCredential = true;
    }
  }

  const guestToken = cookieValueFromRequest(request, GUEST_SESSION_COOKIE_NAME);
  if (guestToken) {
    try {
      const session = await validateGuestSessionToken(guestToken, env);
      return {
        mode: 'guest',
        subject: 'guest',
        sid: session.sid,
        exp: session.exp,
      };
    } catch (error) {
      if (isConfigurationError(error)) throw error;
      invalidCredential = true;
    }
  }
  if (invalidCredential) throw new AccessValidationError('gateway_session_invalid');
  return null;
}

async function guestStartResponse(request, env) {
  if (!authenticatedProxyRequestAllowed(request)) return accessFailureResponse();
  const limited = await enforcePublicRateLimit(
    request,
    env,
    GUEST_START_RATE_LIMIT_BINDING,
    'guest-start',
  );
  if (limited) return limited;
  const session = await createGuestSessionToken(env);
  const acceptsJson = (request.headers.get('Accept') || '').toLowerCase().includes('application/json');
  const headers = new Headers({
    'Set-Cookie': guestSessionSetCookie(session.token, session.payload.exp),
  });
  if (acceptsJson) {
    headers.set('Content-Type', 'application/json; charset=utf-8');
    return response(JSON.stringify({
      authenticated: true,
      mode: 'guest',
      expiresAt: session.payload.exp,
      redirect: '/',
    }), 201, headers);
  }
  headers.set('Location', new URL('/', request.url).toString());
  return response(null, 303, headers);
}

function originProxyResult(originResponse) {
  return { originResponse };
}

function response(body, status = 200, headers = {}) {
  return new Response(body, { status, headers });
}

function staticResponse(request, body, status = 200, headers = {}) {
  return response(request.method === 'HEAD' ? null : body, status, headers);
}

function jsonResponse(payload, status = 200) {
  return response(JSON.stringify(payload), status, { 'Content-Type': 'application/json; charset=utf-8' });
}

function secured(input) {
  const output = new Response(input.body, input);
  for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
    if (!output.headers.has(name)) output.headers.set(name, value);
  }
  return output;
}

function securedWorkbench(originResponse) {
  if (originResponse?.status === 101 || originResponse?.webSocket) return originResponse;
  const output = new Response(originResponse.body, originResponse);
  for (const [name, value] of Object.entries(WORKBENCH_SECURITY_HEADERS)) {
    if (!output.headers.has(name)) output.headers.set(name, value);
  }
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

function encodeBase64Url(value) {
  const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
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

function storedRecordFrom(payload, shareId, weekStart, createdAt, expiresAt, contentDigest) {
  return {
    version: 2,
    schemaVersion: SHARE_SCHEMA,
    shareId,
    contentDigest,
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
  const createdMillis = Date.parse(payload.createdAt);
  const expiryMillis = Date.parse(payload.expiresAt);
  if (!Number.isFinite(createdMillis) || !Number.isFinite(expiryMillis)) return null;
  if (createdMillis > now + 5 * 60 * 1_000 || createdMillis >= expiryMillis) return null;
  if (expiryMillis - now < MIN_SHARE_LIFETIME_MS || expiryMillis - now > MAX_SHARE_LIFETIME_MS) return null;
  return {
    shareId: payload.shareId,
    weekStart: payload.weekStart,
    createdAt: new Date(createdMillis).toISOString(),
    expiresAt: new Date(expiryMillis).toISOString(),
    expiryMillis,
  };
}

function contentDigestInput(record) {
  return JSON.stringify([
    SHARE_SCHEMA,
    record.shareId,
    record.weekStart,
    record.createdAt,
    record.expiresAt,
    record.nonce,
    record.ciphertext,
  ]);
}

async function contentDigestFor(record) {
  const digest = await sha256(contentDigestInput(record));
  return [...digest].map(value => value.toString(16).padStart(2, '0')).join('');
}

function contentSharePrefix(shareId) {
  return `${CONTENT_SHARE_KEY_PREFIX}${shareId}:`;
}

function contentShareKey(shareId, contentDigest) {
  return `${contentSharePrefix(shareId)}${contentDigest}`;
}

function parseContentShareKey(key) {
  if (typeof key !== 'string' || !key.startsWith(CONTENT_SHARE_KEY_PREFIX)) return null;
  const remainder = key.slice(CONTENT_SHARE_KEY_PREFIX.length);
  const separator = remainder.lastIndexOf(':');
  if (separator <= 0) return null;
  const shareId = remainder.slice(0, separator);
  const contentDigest = remainder.slice(separator + 1);
  return validShareId(shareId) && CONTENT_DIGEST_PATTERN.test(contentDigest)
    ? { shareId, contentDigest }
    : null;
}

function parseStoredJson(raw) {
  if (raw === null || raw === undefined) return null;
  if (typeof raw === 'object') return raw;
  if (typeof raw !== 'string') return undefined;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : undefined;
  } catch {
    return undefined;
  }
}

function storedRecordHasValidContent(record, shareId) {
  if (!record || typeof record !== 'object') return false;
  if (record.schemaVersion !== SHARE_SCHEMA || record.shareId !== shareId) return false;
  if (!validIsoDate(record.weekStart)) return false;
  const nonce = decodeBase64Url(record.nonce);
  const ciphertext = decodeBase64Url(record.ciphertext);
  if (!nonce || nonce.byteLength !== 12) return false;
  if (!ciphertext || ciphertext.byteLength < 17 || ciphertext.byteLength > 131_072) return false;
  const createdMillis = Date.parse(record.createdAt);
  const expiryMillis = Date.parse(record.expiresAt);
  return Number.isFinite(createdMillis) && Number.isFinite(expiryMillis) && createdMillis < expiryMillis;
}

function sameStoredContent(left, right) {
  return left
    && right
    && left.schemaVersion === right.schemaVersion
    && left.shareId === right.shareId
    && left.weekStart === right.weekStart
    && left.createdAt === right.createdAt
    && left.expiresAt === right.expiresAt
    && left.nonce === right.nonce
    && left.ciphertext === right.ciphertext;
}

function sameLegacyPayloadContent(left, right) {
  return left
    && right
    && left.schemaVersion === right.schemaVersion
    && left.shareId === right.shareId
    && left.weekStart === right.weekStart
    && left.expiresAt === right.expiresAt
    && left.nonce === right.nonce
    && left.ciphertext === right.ciphertext;
}

async function listKvKeys(kv, prefix, limit = 1_000) {
  const keys = [];
  let cursor;
  const seenCursors = new Set();
  while (true) {
    const options = { prefix, limit };
    if (cursor) options.cursor = cursor;
    const listing = await kv.list(options);
    if (!listing || !Array.isArray(listing.keys)) throw new Error('invalid KV listing');
    keys.push(...listing.keys);
    if (listing.list_complete) return keys;
    if (!listing.cursor || seenCursors.has(listing.cursor)) throw new Error('invalid KV cursor');
    seenCursors.add(listing.cursor);
    cursor = listing.cursor;
  }
}

async function resolveStoredShare(shareId, env) {
  const legacyKey = SHARE_KEY_PREFIX + shareId;
  const [legacyRaw, contentItems] = await Promise.all([
    env.ROSTER_SHARES.get(legacyKey),
    listKvKeys(env.ROSTER_SHARES, contentSharePrefix(shareId), 2),
  ]);
  const legacyRecord = parseStoredJson(legacyRaw);
  if (legacyRecord === undefined) return { kind: 'conflict' };
  if (contentItems.length > 1 || (legacyRecord && contentItems.length > 0)) return { kind: 'conflict' };

  if (contentItems.length === 1) {
    const item = contentItems[0];
    const parsedKey = parseContentShareKey(item.name);
    if (!parsedKey || parsedKey.shareId !== shareId) return { kind: 'conflict' };
    const record = parseStoredJson(await env.ROSTER_SHARES.get(item.name));
    if (
      record === undefined
      || !record
      || record.version !== 2
      || record.contentDigest !== parsedKey.contentDigest
      || !storedRecordHasValidContent(record, shareId)
      || await contentDigestFor(record) !== parsedKey.contentDigest
    ) return { kind: 'conflict' };
    return { kind: 'record', key: item.name, record };
  }

  if (legacyRecord) {
    if (legacyRecord.version !== 1 || !storedRecordHasValidContent(legacyRecord, shareId)) {
      return { kind: 'conflict' };
    }
    return { kind: 'record', key: legacyKey, record: legacyRecord };
  }
  return { kind: 'missing' };
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
  const candidate = {
    schemaVersion: SHARE_SCHEMA,
    shareId: validated.shareId,
    weekStart: validated.weekStart,
    createdAt: validated.createdAt,
    expiresAt: validated.expiresAt,
    nonce: payload.nonce,
    ciphertext: payload.ciphertext,
  };
  const contentDigest = await contentDigestFor(candidate);
  const key = contentShareKey(validated.shareId, contentDigest);
  const record = storedRecordFrom(
    payload,
    validated.shareId,
    validated.weekStart,
    validated.createdAt,
    validated.expiresAt,
    contentDigest,
  );

  // KV has no compare-and-swap.  This preflight is only an operator-friendly
  // early conflict response; correctness comes from never sharing a mutable
  // key between different payloads and resolving every visible collision closed.
  const before = await resolveStoredShare(validated.shareId, env);
  if (before.kind === 'conflict') return jsonResponse({ error: 'share_conflict' }, 409);
  if (before.kind === 'record') {
    const exactReplay = before.record.version === 1
      ? sameLegacyPayloadContent(before.record, record)
      : sameStoredContent(before.record, record);
    if (!exactReplay) return jsonResponse({ error: 'share_exists' }, 409);
    return jsonResponse({
      shareId: before.record.shareId,
      weekStart: before.record.weekStart,
      createdAt: before.record.createdAt,
      expiresAt: before.record.expiresAt,
      ...(before.record.version === 2 ? { contentDigest: before.record.contentDigest } : {}),
    }, 200);
  }
  const metadata = {
    storageVersion: 2,
    shareId: validated.shareId,
    contentDigest,
    weekStart: validated.weekStart,
    createdAt: validated.createdAt,
    expiresAt: validated.expiresAt,
    schemaVersion: SHARE_SCHEMA,
  };
  await env.ROSTER_SHARES.put(key, JSON.stringify(record), {
    expiration: Math.floor(validated.expiryMillis / 1_000),
    metadata,
  });

  const after = await resolveStoredShare(validated.shareId, env);
  if (after.kind === 'conflict') return jsonResponse({ error: 'share_conflict' }, 409);
  if (after.kind === 'record' && !sameStoredContent(after.record, record)) {
    return jsonResponse({ error: 'share_exists' }, 409);
  }
  return jsonResponse({
    shareId: validated.shareId,
    weekStart: validated.weekStart,
    createdAt: validated.createdAt,
    expiresAt: validated.expiresAt,
    contentDigest,
  }, 201);
}

async function listShares(env) {
  const items = await listKvKeys(env.ROSTER_SHARES, SHARE_KEY_PREFIX);
  const shareIds = new Set();
  for (const item of items) {
    const contentKey = parseContentShareKey(item.name);
    if (contentKey) {
      shareIds.add(contentKey.shareId);
      continue;
    }
    const legacyShareId = typeof item.name === 'string' && item.name.startsWith(SHARE_KEY_PREFIX)
      ? item.name.slice(SHARE_KEY_PREFIX.length)
      : '';
    if (!validShareId(legacyShareId)) return jsonResponse({ error: 'share_conflict' }, 409);
    shareIds.add(legacyShareId);
  }

  const shares = [];
  for (const shareId of shareIds) {
    const resolved = await resolveStoredShare(shareId, env);
    if (resolved.kind !== 'record') return jsonResponse({ error: 'share_conflict' }, 409);
    shares.push({
      shareId,
      weekStart: resolved.record.weekStart,
      createdAt: resolved.record.createdAt,
      expiresAt: resolved.record.expiresAt,
    });
  }
  shares.sort((left, right) => String(right.createdAt).localeCompare(String(left.createdAt)));
  return jsonResponse({ shares, cursor: null });
}

async function deleteShare(request, shareId, env) {
  if (!validShareId(shareId)) return jsonResponse({ error: 'invalid_request' }, 400);
  const url = new URL(request.url);
  const parameters = [...url.searchParams.keys()];
  if (parameters.some(name => name !== 'contentDigest')) {
    return jsonResponse({ error: 'invalid_request' }, 400);
  }
  const contentDigests = url.searchParams.getAll('contentDigest');
  if (contentDigests.length > 1) return jsonResponse({ error: 'invalid_request' }, 400);
  if (contentDigests.length === 1) {
    const [contentDigest] = contentDigests;
    if (!CONTENT_DIGEST_PATTERN.test(contentDigest)) {
      return jsonResponse({ error: 'invalid_request' }, 400);
    }
    await env.ROSTER_SHARES.delete(contentShareKey(shareId, contentDigest));
    return new Response(null, { status: 204 });
  }
  const contentItems = await listKvKeys(env.ROSTER_SHARES, contentSharePrefix(shareId));
  await Promise.all([
    env.ROSTER_SHARES.delete(SHARE_KEY_PREFIX + shareId),
    ...contentItems.map(item => env.ROSTER_SHARES.delete(item.name)),
  ]);
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
  const resolved = await resolveStoredShare(payload.shareId, env);
  if (resolved.kind !== 'record') return missingShare();
  const { key, record } = resolved;
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

  if (path === '/guest') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return redirectResponse('/?guest=1', request.url);
  }
  if (path.startsWith('/guest/')) {
    return response('Not found', 404, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  if (path === '/try') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return redirectResponse('/?guest=1', request.url);
  }
  if (path.startsWith('/try/')) {
    return response('Not found', 404, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  if (path === '/support-feedback.js') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return staticResponse(request, PUBLIC_SUPPORT_JS, 200, {
      'Content-Type': 'text/javascript; charset=utf-8',
      'Cache-Control': 'no-store',
    });
  }
  if (path === '/view') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return staticResponse(request, VIEWER_HTML, 200, { 'Content-Type': 'text/html; charset=utf-8' });
  }
  if (path === '/viewer.css') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return staticResponse(request, VIEWER_CSS, 200, { 'Content-Type': 'text/css; charset=utf-8' });
  }
  if (path === '/viewer.js') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return staticResponse(request, VIEWER_JS, 200, { 'Content-Type': 'text/javascript; charset=utf-8' });
  }
  if (path.startsWith('/welcome-audio/')) {
    const trackId = path.slice('/welcome-audio/'.length);
    if (!/^[a-z0-9-]{3,64}$/.test(trackId)) {
      return response('Not found', 404, { 'Content-Type': 'text/plain; charset=utf-8' });
    }
    return await welcomeAudioResponse(request, env, trackId);
  }
  if (path === '/favicon.png' && ['GET', 'HEAD'].includes(request.method)) {
    return serviceWeaveFaviconResponse(request);
  }
  if (path === '/favicon.svg' && ['GET', 'HEAD'].includes(request.method)) {
    return redirectResponse('/favicon.png', request.url, 308);
  }
  if (path === '/robots.txt') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    return staticResponse(request, 'User-agent: *\nDisallow: /\n', 200, { 'Content-Type': 'text/plain; charset=utf-8' });
  }
  if (path === '/healthz') {
    if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
    try {
      normalizeAccessConfiguration(env);
      normalizeRateLimitConfiguration(env);
    } catch {
      return staticResponse(request, JSON.stringify({
        status: 'configuration_error',
        application: 'sing-yin-roster-gateway',
      }), 503, { 'Content-Type': 'application/json; charset=utf-8' });
    }
    const payload = {
      status: 'ok',
      application: 'sing-yin-roster-gateway',
      capabilities: ['encrypted-public-viewer', 'unified-guest-gateway', 'access-admin-gateway', 'signed-origin-principal', 'private-origin-proxy', 'edge-rate-limiting'],
    };
    return staticResponse(request, JSON.stringify(payload), 200, { 'Content-Type': 'application/json; charset=utf-8' });
  }
  if (path === '/api/view') {
    if (request.method !== 'POST') return methodNotAllowed('POST');
    const limited = await enforcePublicRateLimit(
      request,
      env,
      PUBLIC_VIEW_RATE_LIMIT_BINDING,
      'public-view',
    );
    if (limited) return limited;
    return viewShare(request, env, context);
  }

  if (path === '/api/admin/shares' || path.startsWith('/api/admin/shares/')) {
    if (!(await bearerAuthorized(request, env))) return jsonResponse({ error: 'unauthorized' }, 401);
    if (path === '/api/admin/shares' && request.method === 'POST') return createShare(request, env);
    if (path === '/api/admin/shares' && request.method === 'GET') return listShares(env);
    if (request.method === 'DELETE') {
      return deleteShare(request, path.slice('/api/admin/shares/'.length), env);
    }
    return methodNotAllowed('GET, POST, DELETE');
  }

  if (path === '/logout') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    return logoutResponse(request.url);
  }

  if (path === '/auth/admin/start') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    return redirectResponse('/auth/login', request.url);
  }

  if (path === '/auth/guest/start') {
    if (request.method !== 'POST') return methodNotAllowed('POST');
    if (url.search) return jsonResponse({ error: 'invalid_request' }, 400);
    return await guestStartResponse(request, env);
  }

  if (path === '/auth/logout') {
    if (request.method !== 'POST') return methodNotAllowed('POST');
    if (url.search || !authenticatedProxyRequestAllowed(request)) return accessFailureResponse();
    let logoutPrincipal = null;
    try {
      logoutPrincipal = await gatewayPrincipalFromRequest(request, env);
    } catch (error) {
      if (isConfigurationError(error)) return jsonResponse({ error: 'service_unavailable' }, 503);
      // An invalid or expired gateway cookie has no usable origin session.
      // Clear it locally without claiming that a valid session was revoked.
      return authLogoutResponse(request.url);
    }
    if (logoutPrincipal) {
      try {
        // Complete this notification before clearing cookies. waitUntil would
        // leave an already-open NiceGUI callback active if delivery failed.
        await notifyOriginSessionRevocation(request, env, logoutPrincipal);
      } catch {
        return jsonResponse({ error: 'logout_temporarily_unavailable' }, 503);
      }
    }
    return authLogoutResponse(request.url);
  }

  if (path === '/auth/login') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    const accessToken = accessTokenFromRequest(request);
    if (!accessToken) return loggedAccessFailure(request, 'access_token', new AccessValidationError('jwt_missing'));
    let access;
    try {
      access = await validateAccessJwt(accessToken, env);
    } catch (error) {
      return loggedAccessFailure(request, 'access_jwt', error);
    }
    let session;
    try {
      session = await createAdminSessionToken(access.payload.email, access.payload.exp, env);
    } catch (error) {
      return loggedAccessFailure(request, 'admin_session', error);
    }
    const redirect = redirectResponse('/', request.url);
    redirect.headers.append('Set-Cookie', adminSessionSetCookie(session.token, session.payload.exp));
    redirect.headers.append('Set-Cookie', guestSessionClearCookie());
    return redirect;
  }

  let principal;
  try {
    principal = await gatewayPrincipalFromRequest(request, env);
  } catch (error) {
    if (isConfigurationError(error)) return jsonResponse({ error: 'service_unavailable' }, 503);
    return accessFailureResponse();
  }
  if (!principal) {
    if (path === '/auth/status') {
      if (request.method !== 'GET') return methodNotAllowed('GET');
      return jsonResponse({
        status: 'ok',
        gateway: 'ok',
        authenticated: false,
        mode: 'public',
      });
    }
    if (path === '/' && ['GET', 'HEAD'].includes(request.method)) {
      const landingHtml = url.search === '?guest=1'
        ? VIEWER_HTML.replace('data-guest-bootstrap="false"', 'data-guest-bootstrap="true"')
        : VIEWER_HTML;
      return staticResponse(request, landingHtml, 200, { 'Content-Type': 'text/html; charset=utf-8' });
    }
    if (path === '/support') {
      if (!['GET', 'HEAD'].includes(request.method)) return methodNotAllowed('GET, HEAD');
      return staticResponse(request, PUBLIC_SUPPORT_HTML, 200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store',
      });
    }
    return path.startsWith('/auth/') ? accessFailureResponse() : redirectResponse('/', request.url);
  }
  if (path === '/auth/status') {
    if (request.method !== 'GET') return methodNotAllowed('GET');
    const reference = gatewayReference();
    try {
      const originHealthRequest = new Request(new URL('/healthz', request.url), {
        method: 'GET',
        headers: request.headers,
      });
      const originHealth = await proxyToRosterOrigin(originHealthRequest, env, principal);
      const healthy = originHealth.status === 200;
      return jsonResponse(
        {
          status: healthy ? 'ok' : 'origin_unhealthy',
          gateway: 'ok',
          access: 'ok',
          origin: healthy ? 'ok' : 'unhealthy',
          authenticated: true,
          mode: principal.mode,
          expiresAt: principal.exp,
          reference,
        },
        healthy ? 200 : 503,
      );
    } catch {
      return jsonResponse({
        status: 'origin_unavailable',
        gateway: 'ok',
        access: 'ok',
        origin: 'unavailable',
        authenticated: true,
        mode: principal.mode,
        expiresAt: principal.exp,
        reference,
      }, 503);
    }
  }
  if (!authenticatedProxyRequestAllowed(request)) return accessFailureResponse();
  try {
    return originProxyResult(await proxyToRosterOrigin(request, env, principal));
  } catch {
    return originFailureResponse(gatewayReference());
  }
}

export default {
  async fetch(request, env, context) {
    try {
      const routed = await route(request, env, context);
      if (routed && routed.originResponse) return securedWorkbench(routed.originResponse);
      return secured(routed);
    } catch {
      return secured(jsonResponse({ error: 'service_unavailable' }, 503));
    }
  },
};

// Cloudflare module workers may expose named functions for service/RPC use,
// but reject named primitive or object exports at startup.  Keep the test
// seam callable so the real workerd runtime and the Deno suite exercise the
// same entry module without exporting constants that make deployment fail.
export function landingDevotionalsForTest() {
  return LANDING_DEVOTIONALS;
}

export function welcomeTracksForTest() {
  return WELCOME_PUBLIC_TRACKS;
}

export function welcomeVolumePreferenceForTest(storage) {
  return resolveWelcomeVolumePreference(
    storage,
    0.50,
    'sing-yin:welcome-audio-volume:v1',
    'sing-yin:welcome-audio-volume-default-revision:v1',
    2,
  );
}

export function adminSessionCookieNameForTest() {
  return ADMIN_SESSION_COOKIE_NAME;
}

export function guestSessionCookieNameForTest() {
  return GUEST_SESSION_COOKIE_NAME;
}

export {
  accessTokenFromRequest,
  authenticatedProxyRequestAllowed,
  createAdminSessionToken,
  createGuestSessionToken,
  createOriginPrincipalToken,
  gatewayPrincipalFromRequest,
  normalizeAccessConfiguration,
  normalizeRateLimitConfiguration,
  originRequestBinding,
  proxyToRosterOrigin,
  storedRecordFrom,
  stripAccessCredentials,
  validateAdminSessionToken,
  validateAccessJwt,
  validateCreatePayload,
  validateGuestSessionToken,
};
