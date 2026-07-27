import worker, {
  accessTokenFromRequest,
  adminSessionCookieNameForTest,
  authenticatedProxyRequestAllowed,
  createWelcomeEntryController,
  classifyWelcomeAudioFailureState,
  createAdminSessionToken,
  createGuestSessionToken,
  createOriginPrincipalToken,
  guestSessionCookieNameForTest,
  landingDevotionalsForTest,
  welcomeVolumePreferenceForTest,
  welcomeTracksForTest,
  normalizeAccessConfiguration,
  originRequestBinding,
  proxyToRosterOrigin,
  stripAccessCredentials,
  validateAdminSessionToken,
  validateGuestSessionToken,
  validateAccessJwt,
} from './worker.js';
import devotionalSeed from '../../data/devotional/daily-verses.seed.json' with { type: 'json' };

const ADMIN_SESSION_COOKIE_NAME = adminSessionCookieNameForTest();
const GUEST_SESSION_COOKIE_NAME = guestSessionCookieNameForTest();
const LANDING_DEVOTIONALS = landingDevotionalsForTest();
const WELCOME_TRACKS = welcomeTracksForTest();

function assert(condition, message = 'assertion failed') {
  if (!condition) throw new Error(message);
}

function assertEquals(actual, expected, message = 'values differ') {
  if (actual !== expected) throw new Error(`${message}: ${String(actual)} !== ${String(expected)}`);
}

async function expectRejected(factory, message = 'expected rejection') {
  let rejected = false;
  try {
    await factory();
  } catch {
    rejected = true;
  }
  assert(rejected, message);
}

function base64Url(value) {
  const bytes = typeof value === 'string' ? new TextEncoder().encode(value) : value;
  return btoa(String.fromCharCode(...bytes)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
}

const keyPairPromise = crypto.subtle.generateKey(
  {
    name: 'RSASSA-PKCS1-v1_5',
    modulusLength: 2_048,
    publicExponent: new Uint8Array([1, 0, 1]),
    hash: 'SHA-256',
  },
  true,
  ['sign', 'verify'],
);

async function signingFixture(kid = 'access-key-2026') {
  const keyPair = await keyPairPromise;
  const jwk = await crypto.subtle.exportKey('jwk', keyPair.publicKey);
  Object.assign(jwk, { alg: 'RS256', kid, use: 'sig', key_ops: ['verify'] });
  return { keyPair, jwk, kid };
}

async function signedJwt(payload, header = {}) {
  const fixture = await signingFixture(header.kid || 'access-key-2026');
  const protectedHeader = { alg: 'RS256', kid: fixture.kid, typ: 'JWT', ...header };
  const headerSegment = base64Url(JSON.stringify(protectedHeader));
  const payloadSegment = base64Url(JSON.stringify(payload));
  const signingInput = `${headerSegment}.${payloadSegment}`;
  const signature = new Uint8Array(await crypto.subtle.sign(
    { name: 'RSASSA-PKCS1-v1_5' },
    fixture.keyPair.privateKey,
    new TextEncoder().encode(signingInput),
  ));
  return `${signingInput}.${base64Url(signature)}`;
}

function rateLimitEnvironment() {
  const allowingRateLimiter = {
    async limit() {
      return { success: true };
    },
  };
  return {
    GUEST_SESSION_SECRET: 'test-only-guest-session-secret-with-more-than-32-characters', // pragma: allowlist secret -- deterministic test fixture
    GUEST_START_RATE_LIMITER: allowingRateLimiter,
    PUBLIC_VIEW_RATE_LIMITER: allowingRateLimiter,
  };
}

function accessEnvironment(teamName) {
  return {
    ...rateLimitEnvironment(),
    ACCESS_TEAM_DOMAIN: `https://${teamName}.cloudflareaccess.com`,
    ACCESS_AUD: 'expected-access-audience',
    ADMIN_IDENTITY_ALLOWLIST: JSON.stringify({
      emails: [
        'admin@syss.edu.hk',
        'operator.backup@gmail.com',
        'operator.backup@outlook.com',
      ],
    }),
    ADMIN_SESSION_SECRET: 'test-only-admin-session-secret-with-more-than-32-characters', // pragma: allowlist secret -- deterministic test fixture
    ORIGIN_PRINCIPAL_SECRET: 'test-only-origin-principal-secret-with-more-than-32-characters', // pragma: allowlist secret -- deterministic test fixture
    AUTH_EPOCH: 7,
    ORIGIN_PRINCIPAL_KID: 'test-origin-v7',
  };
}

function configuredAdminEmails(env) {
  return JSON.parse(env.ADMIN_IDENTITY_ALLOWLIST).emails;
}

async function adminSessionCookiePair(env, email, accessExpiresAt, options = {}) {
  const session = await createAdminSessionToken(email, accessExpiresAt, env, options);
  return `${ADMIN_SESSION_COOKIE_NAME}=${encodeURIComponent(session.token)}`;
}

async function guestSessionCookiePair(env, options = {}) {
  const session = await createGuestSessionToken(env, options);
  return `${GUEST_SESSION_COOKIE_NAME}=${encodeURIComponent(session.token)}`;
}

function signedPayload(token) {
  const [payloadSegment] = token.split('.');
  const padded = payloadSegment.replaceAll('-', '+').replaceAll('_', '/') + '='.repeat((4 - payloadSegment.length % 4) % 4);
  return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(padded), character => character.charCodeAt(0))));
}

function memoryKv() {
  const records = new Map();
  const metadata = new Map();
  return {
    records,
    metadata,
    async get(key, options = undefined) {
      const value = records.get(key);
      if (value === undefined) return null;
      if (options?.type === 'json') return JSON.parse(value);
      return value;
    },
    async put(key, value, options = {}) {
      records.set(key, value);
      metadata.set(key, options.metadata || null);
    },
    async delete(key) {
      records.delete(key);
      metadata.delete(key);
    },
    async list(options = {}) {
      const prefix = options.prefix || '';
      const limit = Number(options.limit || 1_000);
      const offset = Number(options.cursor || 0);
      const names = [...records.keys()].filter(name => name.startsWith(prefix)).sort();
      const selected = names.slice(offset, offset + limit);
      const nextOffset = offset + selected.length;
      const listComplete = nextOffset >= names.length;
      return {
        keys: selected.map(name => ({ name, metadata: metadata.get(name) || null })),
        list_complete: listComplete,
        cursor: listComplete ? undefined : String(nextOffset),
      };
    },
  };
}

function validClaims(env, nowSeconds, email = configuredAdminEmails(env)[0]) {
  return {
    iss: env.ACCESS_TEAM_DOMAIN,
    aud: [env.ACCESS_AUD],
    email,
    nbf: nowSeconds - 30,
    exp: nowSeconds + 300,
  };
}

function jwksFetcher(jwk, captured = {}) {
  return (url, init) => {
    captured.url = String(url);
    captured.init = init;
    return new Response(JSON.stringify({ keys: [jwk] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
}

Deno.test('landing devotionals stay exact to the canonical RCUV 2010 and NKJV seed', () => {
  const canonicalById = new Map(devotionalSeed.entries.map(entry => [entry.id, entry]));
  assertEquals(LANDING_DEVOTIONALS.length, 5);
  for (const landing of LANDING_DEVOTIONALS) {
    const canonical = canonicalById.get(landing.id);
    assert(canonical, `missing canonical devotional ${landing.id}`);
    assertEquals(canonical.source.translation.zh, 'RCUV 2010');
    assertEquals(canonical.source.translation.en, 'NKJV');
    assertEquals(canonical.translationVerification.zh.status, 'verified-exact');
    assertEquals(canonical.translationVerification.en.status, 'verified-exact');
    assertEquals(landing.referenceZh, canonical.source.reference.zh);
    assertEquals(landing.referenceEn, canonical.source.reference.en);
    assertEquals(landing.scriptureZh, canonical.scripture.zh);
    assertEquals(landing.scriptureEn, canonical.scripture.en.replace(/ \(NKJV\)$/, ''));
    assertEquals(landing.reflectionZh, canonical.reflection.zh.title);
    assertEquals(landing.reflectionEn, canonical.reflection.en.title);
    assertEquals(landing.prayerZh, canonical.reflection.zh.prayer);
    assertEquals(landing.prayerEn, canonical.reflection.en.prayer);
  }
});

Deno.test('validates every exact administrator email against the trusted team JWK', async () => {
  const env = accessEnvironment('sing-yin-runtime-valid');
  const nowSeconds = 2_000_000_000;
  const fixture = await signingFixture();
  const captured = {};

  for (const email of configuredAdminEmails(env)) {
    const token = await signedJwt(validClaims(env, nowSeconds, email));
    const result = await validateAccessJwt(token, env, {
      nowMillis: nowSeconds * 1_000,
      fetcher: jwksFetcher(fixture.jwk, captured),
    });
    assertEquals(result.payload.email, email);
  }

  assertEquals(captured.url, `${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
  assertEquals(captured.init.method, 'GET');
  assertEquals(captured.init.headers.Accept, 'application/json');
  assertEquals(captured.init.cache, undefined);
  assertEquals(captured.init.redirect, undefined);
});

Deno.test('uses Worker-compatible JWKS fetch options for the complete Access callback', async () => {
  const env = accessEnvironment('sing-yin-runtime-worker-fetch');
  const fixture = await signingFixture();
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const token = await signedJwt(validClaims(env, nowSeconds));
  const originalFetch = globalThis.fetch;
  let jwksRequests = 0;
  globalThis.fetch = (url, init = {}) => {
    if ('cache' in init || init.redirect === 'error') {
      throw new TypeError('unsupported request initializer');
    }
    jwksRequests += 1;
    assertEquals(String(url), `${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
    return new Response(JSON.stringify({ keys: [fixture.jwk] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  };
  let result;
  try {
    result = await worker.fetch(new Request('https://gateway.example/auth/login', {
      headers: {
        'Cf-Access-Jwt-Assertion': token,
        Cookie: `CF_Authorization=${token}`,
      },
    }), env, { waitUntil() {} });
  } finally {
    globalThis.fetch = originalFetch;
  }

  assertEquals(jwksRequests, 1);
  assertEquals(result.status, 302);
  assertEquals(result.headers.get('Location'), 'https://gateway.example/');
  assert((result.headers.get('Set-Cookie') || '').startsWith(`${ADMIN_SESSION_COOKIE_NAME}=`));
});

Deno.test('normalizes a bounded exact-email allowlist and rejects malformed configuration', async () => {
  const env = accessEnvironment('sing-yin-runtime-config');
  const configuration = normalizeAccessConfiguration(env);
  const configuredAllowlist = JSON.parse(env.ADMIN_IDENTITY_ALLOWLIST);
  assertEquals(configuration.adminEmails.join(','), configuredAllowlist.emails.join(','));

  for (const invalidAdminEmails of [
    [],
    ['admin@syss.edu.hk', 'admin@syss.edu.hk'],
    [' Admin@syss.edu.hk'],
    ['Admin@syss.edu.hk'],
    ['not-an-email'],
    'admin@syss.edu.hk',
  ]) {
    await expectRejected(() => Promise.resolve(normalizeAccessConfiguration({
      ...env,
      ADMIN_IDENTITY_ALLOWLIST: JSON.stringify({ emails: invalidAdminEmails }),
    })));
  }
  for (const invalidAllowlist of [
    '',
    'not-json',
    '[]',
    '{}',
    JSON.stringify({ emails: configuredAllowlist.emails, extra: true }),
  ]) {
    await expectRejected(() => Promise.resolve(normalizeAccessConfiguration({
      ...env,
      ADMIN_IDENTITY_ALLOWLIST: invalidAllowlist,
    })));
  }
});

Deno.test('fails closed for wrong algorithm, issuer, audience, time window, email, kid, or signature', async () => {
  const env = accessEnvironment('sing-yin-runtime-invalid');
  const nowSeconds = 2_000_000_000;
  const fixture = await signingFixture();
  const fetcher = jwksFetcher(fixture.jwk);
  const baseline = validClaims(env, nowSeconds);
  const invalidClaims = [
    { ...baseline, iss: 'https://other.cloudflareaccess.com' },
    { ...baseline, aud: ['wrong-audience'] },
    { ...baseline, exp: nowSeconds },
    { ...baseline, nbf: nowSeconds + 1 },
    { ...baseline, email: 'other@syss.edu.hk' },
  ];
  for (const claims of invalidClaims) {
    const token = await signedJwt(claims);
    await expectRejected(() => validateAccessJwt(token, env, { nowMillis: nowSeconds * 1_000, fetcher }));
  }

  const wrongAlgorithm = await signedJwt(baseline, { alg: 'HS256' });
  await expectRejected(() => validateAccessJwt(wrongAlgorithm, env, { nowMillis: nowSeconds * 1_000, fetcher }));

  const wrongKid = await signedJwt(baseline, { kid: 'unknown-access-key' });
  await expectRejected(() => validateAccessJwt(wrongKid, env, { nowMillis: nowSeconds * 1_000, fetcher }));

  const valid = await signedJwt(baseline);
  const tokenParts = valid.split('.');
  tokenParts[2] = `${tokenParts[2].startsWith('A') ? 'B' : 'A'}${tokenParts[2].slice(1)}`;
  const tampered = tokenParts.join('.');
  await expectRejected(() => validateAccessJwt(tampered, env, { nowMillis: nowSeconds * 1_000, fetcher }));
});

Deno.test('prefers the Access assertion header and supports the authorization cookie fallback', () => {
  const headerRequest = new Request('https://gateway.example/', {
    headers: {
      'Cf-Access-Jwt-Assertion': 'header.jwt.value',
      Cookie: 'CF_Authorization=cookie.jwt.value; session=nicegui-session',
    },
  });
  assertEquals(accessTokenFromRequest(headerRequest), 'header.jwt.value');

  const cookieRequest = new Request('https://gateway.example/', {
    headers: { Cookie: 'session=nicegui-session; CF_Authorization=cookie.jwt.value' },
  });
  assertEquals(accessTokenFromRequest(cookieRequest), 'cookie.jwt.value');
});

Deno.test('records a privacy-safe support reference when the Access callback has no token', async () => {
  const env = accessEnvironment('sing-yin-runtime-auth-diagnostic');
  let diagnostic = '';
  const originalWarn = console.warn;
  console.warn = value => { diagnostic = String(value); };
  let result;
  try {
    result = await worker.fetch(
      new Request('https://gateway.example/auth/login', {
        headers: { 'CF-Ray': '0123456789abcdef-HKG' },
      }),
      env,
      { waitUntil() {} },
    );
  } finally {
    console.warn = originalWarn;
  }

  assertEquals(result.status, 403);
  assert(/GW-[A-F0-9]{12}/.test(result.headers.get('X-Sing-Yin-Support-Reference') || ''));
  const record = JSON.parse(diagnostic);
  assertEquals(record.event, 'admin_login_bridge_failure');
  assertEquals(record.phase, 'access_token');
  assertEquals(record.reason, 'jwt_missing');
  assertEquals(record.ray, '0123456789abcdef-HKG');
  assertEquals(record.assertionPresent, false);
  assertEquals(record.authorizationCookiePresent, false);
  assert(!diagnostic.includes(env.ACCESS_AUD));
  for (const email of configuredAdminEmails(env)) assert(!diagnostic.includes(email));
});

Deno.test('separates a valid Access JWT from a missing administrator session secret', async () => {
  const env = accessEnvironment('sing-yin-runtime-session-secret-diagnostic');
  delete env.ADMIN_SESSION_SECRET;
  const fixture = await signingFixture();
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const token = await signedJwt(validClaims(env, nowSeconds));
  const originalFetch = globalThis.fetch;
  const originalWarn = console.warn;
  let diagnostic = '';
  globalThis.fetch = jwksFetcher(fixture.jwk);
  console.warn = value => { diagnostic = String(value); };
  let result;
  try {
    result = await worker.fetch(
      new Request('https://gateway.example/auth/login', {
        headers: { 'Cf-Access-Jwt-Assertion': token },
      }),
      env,
      { waitUntil() {} },
    );
  } finally {
    globalThis.fetch = originalFetch;
    console.warn = originalWarn;
  }

  assertEquals(result.status, 403);
  const record = JSON.parse(diagnostic);
  assertEquals(record.phase, 'admin_session');
  assertEquals(record.reason, 'session_secret_configuration');
  assertEquals(record.assertionPresent, true);
  assertEquals(record.authorizationCookiePresent, false);
  assert(!diagnostic.includes(token));
  for (const email of configuredAdminEmails(env)) assert(!diagnostic.includes(email));
});

Deno.test('strips Access and gateway session credentials but preserves the NiceGUI session cookie', () => {
  const sanitized = stripAccessCredentials(new Headers({
    'Cf-Access-Jwt-Assertion': 'secret-jwt',
    'Cf-Access-Authenticated-User-Email': 'spoofed-access@example.com',
    'Cf-Access-User-UUID': 'spoofed-uuid',
    'X-Sing-Yin-Access-Email': 'spoofed@example.com',
    'X-Sing-Yin-Origin-Principal': 'spoofed-principal',
    'X-Forwarded-Host': 'attacker.example',
    Cookie: `session=nicegui-session; CF_Authorization=secret-cookie; ${ADMIN_SESSION_COOKIE_NAME}=signed-session; ${GUEST_SESSION_COOKIE_NAME}=signed-guest; preference=zh-HK`,
  }));

  assertEquals(sanitized.get('Cf-Access-Jwt-Assertion'), null);
  assertEquals(sanitized.get('Cf-Access-Authenticated-User-Email'), null);
  assertEquals(sanitized.get('Cf-Access-User-UUID'), null);
  assertEquals(sanitized.get('X-Sing-Yin-Access-Email'), null);
  assertEquals(sanitized.get('X-Sing-Yin-Origin-Principal'), null);
  assertEquals(sanitized.get('X-Forwarded-Host'), null);
  assertEquals(sanitized.get('Cookie'), 'session=nicegui-session; preference=zh-HK');
});

Deno.test('landing welcome playlists use paired instrumental tracks and a 50 percent default volume', async () => {
  assertEquals(Object.keys(WELCOME_TRACKS).sort().join(','), 'bright,quiet');
  for (const profile of ['bright', 'quiet']) {
    assertEquals(WELCOME_TRACKS[profile].length, 5);
    assert(WELCOME_TRACKS[profile].every(track => track.arrangement === 'instrumental'));
    assertEquals(new Set(WELCOME_TRACKS[profile].map(track => track.id)).size, 5);
  }

  const env = accessEnvironment('sing-yin-welcome-player');
  const context = { waitUntil() {} };
  const home = await worker.fetch(new Request('https://gateway.example/'), env, context);
  const html = await home.text();
  assert(html.includes('id="welcomeAudioPlayer"'));
  assert(html.includes('id="welcomeAudioVolume" type="range" min="0" max="100" step="1" value="50"'));
  assert(html.includes('Playback is attempted at 50%; music never blocks sign-in or the guest demo.'));
  assert(html.includes('id="welcomeAudioRecovery"'));
  assert(html.includes('id="welcomeAudioEnter"'));
  assert(html.includes('id="welcomeAudioQuiet"'));
  assert(html.includes('Entry sound'));
  assert(html.includes('id="themeSelect"'));
  assert(html.includes('data-testid="public-theme-selector"'));
  assert(html.includes('<option value="system">跟隨系統 · System</option>'));
  assert(html.includes('<option value="light">淺色 · Light</option>'));
  assert(html.includes('<option value="dark">深色 · Dark</option>'));
  const stylesheet = await worker.fetch(
    new Request('https://gateway.example/viewer.css'),
    env,
    context,
  );
  assertEquals(stylesheet.status, 200);
  assert((await stylesheet.text()).includes('.theme-toggle select { min-width: 0; min-height: 44px;'));
  assert(html.includes('Copyright © 2026 LI Chuangjie'));
  assert((home.headers.get('Content-Security-Policy') || '').includes("media-src 'self'"));
  assert((home.headers.get('Permissions-Policy') || '').includes('autoplay=(self)'));

  const scriptResponse = await worker.fetch(new Request('https://gateway.example/viewer.js'), env, context);
  const script = await scriptResponse.text();
  assert(script.includes('const DEFAULT_WELCOME_VOLUME = 0.50'));
  assert(script.includes("sing-yin:welcome-audio-volume:v1"));
  assert(script.includes("sing-yin:welcome-audio-volume-default-revision:v1"));
  assert(script.includes('const WELCOME_VOLUME_DEFAULT_REVISION = 2'));
  assert(script.includes('storeWelcomeVolume(normalised)'));
  assert(script.includes('welcomeAudio.play()'));
  assert(script.includes('classifyWelcomeAudioFailure'));
  assert(script.includes('networkState: welcomeAudio?.networkState || 0'));
  assert(script.includes('classifyWelcomeAudioFailureState({'));
  assert(script.includes("welcomeAudioEnter?.addEventListener('click'"));
  assert(script.includes('createWelcomeEntryController({'));
  assert(script.includes('trustedEntryDestination'));
  assert(script.includes('welcomeEntryController.enter(destination'));
  assert(!script.includes("welcomeAudioPlayer?.dataset.autoplayState === 'blocked'"));
  assert(script.includes('if (welcomeAudioRecovery) welcomeAudioRecovery.hidden = true;'));
  assert(!script.includes("setWelcomeRecoveryVisible(false);\n    if (welcomeAudioStatus)"));
  assert(!script.includes("document.addEventListener('pointerdown'"));
  assert(script.includes("void playWelcomeAudio({ revealRecovery: true });"));
  assert(!script.includes('WELCOME_ENABLED_KEY'));
  assert(!script.includes('sing-yin:welcome-audio-enabled:v1'));
  assert(script.includes("addEventListener('ended'"));
  assert(!script.includes('cancelWelcomeFade'));
  assert(script.includes("themeSelect?.addEventListener('change'"));
  assert(script.includes("applyTheme(event.currentTarget.value, { persist: true })"));
  assert(!script.includes('THEME_STATES[(THEME_STATES.indexOf(current) + 1)'));
});

Deno.test('welcome entry attempts playback inside the activation and navigates once on success or failure', async () => {
  for (const outcome of ['success', 'rejection', 'throw']) {
    const events = [];
    const controller = createWelcomeEntryController({
      play() {
        events.push('play');
        if (outcome === 'throw') throw new Error('synchronous playback failure');
        return outcome === 'rejection'
          ? Promise.reject(new DOMException('blocked', 'NotAllowedError'))
          : Promise.resolve();
      },
      navigate(destination) { events.push(`navigate:${destination}`); },
      onPlaybackStarted() { events.push('playing'); },
      onPlaybackFailed(error) { events.push(`failed:${error.name}`); },
    });

    assertEquals(controller.getIntent(), 'unset');
    assertEquals(controller.enter('/guest', 'guest'), true);
    assertEquals(events[0], 'play');
    await Promise.resolve();
    await Promise.resolve();
    assertEquals(events.filter(event => event === 'navigate:/guest').length, 1);
    if (outcome === 'success') assert(events.includes('playing'));
    else assert(events.some(event => event.startsWith('failed:')));
  }
});

Deno.test('welcome entry falls back after bounded latency and ignores late playback settlement', async () => {
  const events = [];
  let scheduled;
  let resolvePlayback;
  const playback = new Promise(resolve => { resolvePlayback = resolve; });
  const controller = createWelcomeEntryController({
    play() { events.push('play'); return playback; },
    navigate(destination) { events.push(`navigate:${destination}`); },
    onPlaybackStarted() { events.push('playing'); },
    onPlaybackTimeout() { events.push('timeout'); },
    schedule(callback, delay) { scheduled = { callback, delay }; return 7; },
    cancel() {},
    timeoutMs: 450,
  });

  controller.enter('/auth/login', 'admin');
  assertEquals(scheduled.delay, 450);
  scheduled.callback();
  assertEquals(events.join(','), 'play,timeout,navigate:/auth/login');
  resolvePlayback();
  await Promise.resolve();
  await Promise.resolve();
  assertEquals(events.join(','), 'play,timeout,navigate:/auth/login');
});

Deno.test('welcome entry honors explicit quiet intent, current playback, duplicate suppression and pageshow reset', async () => {
  const events = [];
  const controller = createWelcomeEntryController({
    play() { events.push('play'); return Promise.resolve(); },
    navigate(destination) { events.push(`navigate:${destination}`); },
    isPlaying: () => false,
    onIntentChange(intent) { events.push(`intent:${intent}`); },
    onBusyChange(role, busy) { events.push(`busy:${role}:${busy}`); },
  });

  controller.setIntent('quiet');
  assertEquals(controller.enter('/guest', 'guest'), true);
  assertEquals(controller.enter('/guest', 'guest'), false);
  assert(!events.includes('play'));
  assertEquals(events.filter(event => event === 'navigate:/guest').length, 1);

  controller.reset();
  controller.setIntent('music');
  assertEquals(controller.enter('/auth/login', 'admin'), true);
  assertEquals(controller.enter('/auth/login', 'admin'), false);
  await Promise.resolve();
  await Promise.resolve();
  assertEquals(events.filter(event => event === 'navigate:/auth/login').length, 1);
});

Deno.test('welcome entry does not restart audio that is already playing', () => {
  let playCalls = 0;
  let navigationCalls = 0;
  const controller = createWelcomeEntryController({
    play() { playCalls += 1; return Promise.resolve(); },
    navigate() { navigationCalls += 1; },
    isPlaying: () => true,
  });
  assertEquals(controller.enter('/guest', 'guest'), true);
  assertEquals(playCalls, 0);
  assertEquals(navigationCalls, 1);
});

Deno.test('welcome audio failure classification remains explicit and deterministic', () => {
  const cases = [
    [{ errorName: 'NotAllowedError' }, 'blocked'],
    [{ errorName: 'NotSupportedError' }, 'decoding'],
    [{ errorName: 'AbortError' }, 'lifecycle'],
    [{ errorName: 'NotAllowedError', mediaErrorCode: 2 }, 'blocked'],
    [{ mediaErrorCode: 3 }, 'decoding'],
    [{ mediaErrorCode: 4 }, 'decoding'],
    [{ mediaErrorCode: 2 }, 'transport'],
    [{ networkState: 2, readyState: 1 }, 'loading'],
    [{ networkState: 2, readyState: 3 }, 'error'],
    [{ online: false }, 'transport'],
    [{}, 'error'],
  ];
  for (const [input, expected] of cases) {
    assertEquals(classifyWelcomeAudioFailureState(input), expected);
  }
});

Deno.test('welcome volume defaults only when absent and preserves explicit zero and 25 percent choices', () => {
  const createStorage = (initial = {}, { rejectWrites = false } = {}) => {
    const values = new Map(Object.entries(initial));
    return {
      getItem(key) {
        return values.has(key) ? values.get(key) : null;
      },
      setItem(key, value) {
        if (rejectWrites) throw new Error('storage is read-only');
        values.set(key, String(value));
      },
      value(key) {
        return values.get(key);
      },
    };
  };
  const volumeKey = 'sing-yin:welcome-audio-volume:v1';
  const revisionKey = 'sing-yin:welcome-audio-volume-default-revision:v1';

  const missing = createStorage();
  assertEquals(welcomeVolumePreferenceForTest(missing), 0.50);
  assertEquals(missing.value(volumeKey), '0.5');
  assertEquals(missing.value(revisionKey), '2');

  const explicit = createStorage({ [volumeKey]: '0.25' });
  assertEquals(welcomeVolumePreferenceForTest(explicit), 0.25);
  assertEquals(explicit.value(volumeKey), '0.25');
  assertEquals(explicit.value(revisionKey), '2');

  const muted = createStorage({ [volumeKey]: '0' });
  assertEquals(welcomeVolumePreferenceForTest(muted), 0);
  assertEquals(muted.value(volumeKey), '0');
  assertEquals(muted.value(revisionKey), '2');

  const readOnlyExplicit = createStorage({ [volumeKey]: '0.25' }, { rejectWrites: true });
  assertEquals(welcomeVolumePreferenceForTest(readOnlyExplicit), 0.25);
});

Deno.test('public welcome audio proxies only an exact allowlisted recording and preserves byte ranges', async () => {
  const env = accessEnvironment('sing-yin-welcome-audio-route');
  const context = { waitUntil() {} };
  let originRequest;
  env.ROSTER_ORIGIN = {
    async fetch(request) {
      originRequest = request;
      return new Response(new Uint8Array([1, 2, 3, 4]), {
        status: 206,
        headers: {
          'Content-Type': 'audio/mp4',
          'Content-Range': 'bytes 0-3/100',
          'Accept-Ranges': 'bytes',
        },
      });
    },
  };

  const allowed = await worker.fetch(new Request(
    'https://gateway.example/welcome-audio/morning-has-broken',
    { headers: { Range: 'bytes=0-3', Cookie: 'private=value' } },
  ), env, context);
  assertEquals(allowed.status, 206);
  assertEquals(allowed.headers.get('Content-Range'), 'bytes 0-3/100');
  assert(originRequest);
  assertEquals(new URL(originRequest.url).port, '8080');
  assertEquals(originRequest.headers.get('Range'), 'bytes=0-3');
  assertEquals(originRequest.headers.get('Cookie'), null);
  assert(decodeURIComponent(new URL(originRequest.url).pathname).endsWith(
    '/assets/music/Relaxing Piano - Topic - Morning ⧸ Morning Has Broken.m4a',
  ));

  originRequest = null;
  const unknown = await worker.fetch(
    new Request('https://gateway.example/welcome-audio/not-allowlisted'),
    env,
    context,
  );
  assertEquals(unknown.status, 404);
  assertEquals(originRequest, null);
});

Deno.test('enforces same-origin unsafe requests and WebSocket upgrades', () => {
  const safeGet = new Request('https://gateway.example/op');
  assert(authenticatedProxyRequestAllowed(safeGet));

  const sameOriginPost = new Request('https://gateway.example/op', {
    method: 'POST',
    headers: { Origin: 'https://gateway.example', 'Sec-Fetch-Site': 'same-origin' },
  });
  assert(authenticatedProxyRequestAllowed(sameOriginPost));

  const crossOriginPost = new Request('https://gateway.example/op', {
    method: 'POST',
    headers: { Origin: 'https://attacker.example', 'Sec-Fetch-Site': 'cross-site' },
  });
  assert(!authenticatedProxyRequestAllowed(crossOriginPost));

  const customMethod = new Request('https://gateway.example/op', {
    method: 'PROPFIND',
    headers: { Origin: 'https://gateway.example', 'Sec-Fetch-Site': 'same-origin' },
  });
  assert(!authenticatedProxyRequestAllowed(customMethod));

  const sameOriginWebSocket = new Request('https://gateway.example/_nicegui_ws', {
    headers: { Upgrade: 'websocket', Origin: 'https://gateway.example', 'Sec-Fetch-Site': 'same-origin' },
  });
  assert(authenticatedProxyRequestAllowed(sameOriginWebSocket));

  const noOriginWebSocket = new Request('https://gateway.example/_nicegui_ws', {
    headers: { Upgrade: 'websocket' },
  });
  assert(!authenticatedProxyRequestAllowed(noOriginWebSocket));
});

Deno.test('proxies the exact path, query, body, and session while injecting only verified identity', async () => {
  let capturedRequest;
  const sentinel = { status: 101, webSocket: { preserved: true } };
  const env = {
    ...accessEnvironment('sing-yin-runtime-direct-proxy'),
    ORIGIN_PORT: '9091',
    ROSTER_ORIGIN: {
      fetch(request) {
        capturedRequest = request;
        return sentinel;
      },
    },
  };
  const incoming = new Request('https://gateway.example/op/save?draft=3', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Cf-Access-Jwt-Assertion': 'secret-jwt',
      'X-Sing-Yin-Origin-Principal': 'spoofed-principal',
      Cookie: 'session=nicegui-session; CF_Authorization=secret-cookie',
    },
    body: JSON.stringify({ confirmed: true }),
  });

  const result = await proxyToRosterOrigin(incoming, env, {
    mode: 'admin',
    subject: 'admin@syss.edu.hk',
    sid: base64Url(new Uint8Array(16).fill(9)),
    exp: Math.floor(Date.now() / 1_000) + 300,
  });

  assertEquals(result, sentinel, 'origin response must be returned by identity');
  assertEquals(capturedRequest.url, 'http://127.0.0.1:9091/op/save?draft=3');
  assertEquals(capturedRequest.headers.get('Cf-Access-Jwt-Assertion'), null);
  assertEquals(capturedRequest.headers.get('Cookie'), 'session=nicegui-session');
  assertEquals(capturedRequest.headers.get('X-Sing-Yin-Access-Email'), null);
  const principal = signedPayload(capturedRequest.headers.get('X-Sing-Yin-Origin-Principal') || '');
  assertEquals(principal.mode, 'admin');
  assertEquals(principal.subject, 'admin@syss.edu.hk');
  assertEquals(principal.auth_epoch, env.AUTH_EPOCH);
  assertEquals(principal.kid, env.ORIGIN_PRINCIPAL_KID);
  assertEquals(principal.request_binding, await originRequestBinding(incoming));
  assertEquals(capturedRequest.headers.get('X-Forwarded-Host'), 'gateway.example');
  assertEquals(await capturedRequest.text(), JSON.stringify({ confirmed: true }));
});

Deno.test('rejects invalid configured origin ports before contacting the private origin', async () => {
  const invalidPorts = [null, '', '8080x', '8080.5', 1_023, 65_536, Number.NaN];
  const principal = {
    mode: 'admin',
    subject: 'admin@syss.edu.hk',
    sid: base64Url(new Uint8Array(16).fill(6)),
    exp: Math.floor(Date.now() / 1_000) + 300,
  };

  for (const invalidPort of invalidPorts) {
    let originCalls = 0;
    const env = {
      ...accessEnvironment('sing-yin-invalid-origin-port'),
      ORIGIN_PORT: invalidPort,
      ROSTER_ORIGIN: {
        fetch() {
          originCalls += 1;
          return new Response('unexpected');
        },
      },
    };
    await expectRejected(
      () => proxyToRosterOrigin(new Request('https://gateway.example/healthz'), env, principal),
      `invalid origin port must reject: ${String(invalidPort)}`,
    );
    assertEquals(originCalls, 0, `invalid origin port contacted origin: ${String(invalidPort)}`);

    const publicAudio = await worker.fetch(
      new Request('https://gateway.example/welcome-audio/morning-has-broken'),
      env,
      { waitUntil() {} },
    );
    assertEquals(publicAudio.status, 503, `invalid origin port did not fail closed: ${String(invalidPort)}`);
    assertEquals(originCalls, 0, `invalid public audio port contacted origin: ${String(invalidPort)}`);
  }
});

Deno.test('serves guest landing, redirects guest app paths, and exposes capability-only health', async () => {
  const env = accessEnvironment('sing-yin-runtime-routing');
  const context = { waitUntil() {} };

  const home = await worker.fetch(new Request('https://gateway.example/'), env, context);
  assertEquals(home.status, 200);
  assert((await home.text()).includes('管理員登入'));

  const app = await worker.fetch(new Request('https://gateway.example/op'), env, context);
  assertEquals(app.status, 302);
  assertEquals(app.headers.get('Location'), 'https://gateway.example/');

  const staleCookieHome = await worker.fetch(new Request('https://gateway.example/', {
    headers: { Cookie: 'CF_Authorization=expired.or.invalid' },
  }), env, context);
  assertEquals(staleCookieHome.status, 200);
  assert((await staleCookieHome.text()).includes('管理員登入'));

  const logout = await worker.fetch(new Request('https://gateway.example/logout'), env, context);
  assertEquals(logout.status, 302);
  assertEquals(logout.headers.get('Location'), 'https://gateway.example/cdn-cgi/access/logout');
  const clearedCookie = logout.headers.get('Set-Cookie') || '';
  assert(clearedCookie.startsWith(`${ADMIN_SESSION_COOKIE_NAME}=`));
  assert(clearedCookie.includes('Max-Age=0'));
  assert(clearedCookie.includes('Path=/'));
  assert(clearedCookie.includes('HttpOnly'));
  assert(clearedCookie.includes('Secure'));
  assert(clearedCookie.includes('SameSite=Lax'));

  const health = await worker.fetch(new Request('https://gateway.example/healthz'), env, context);
  const body = await health.text();
  assertEquals(health.status, 200);
  assert(body.includes('private-origin-proxy'));
  assert(!body.includes(env.ACCESS_TEAM_DOMAIN));
  for (const email of configuredAdminEmails(env)) assert(!body.includes(email));
  assert(!body.includes(env.ACCESS_AUD));
});

Deno.test('gateway health fails closed when the private administrator allowlist is invalid', async () => {
  const env = accessEnvironment('sing-yin-runtime-invalid-health');
  env.ADMIN_IDENTITY_ALLOWLIST = JSON.stringify({ emails: ['UPPER@example.com'] });
  const health = await worker.fetch(
    new Request('https://gateway.example/healthz'),
    env,
    { waitUntil() {} },
  );
  const body = await health.text();
  assertEquals(health.status, 503);
  assert(body.includes('configuration_error'));
  assert(!body.includes('UPPER@example.com'));
  assert(!body.includes(env.ACCESS_TEAM_DOMAIN));
});

Deno.test('gateway health fails closed when either edge rate-limit binding is missing', async () => {
  for (const bindingName of ['GUEST_START_RATE_LIMITER', 'PUBLIC_VIEW_RATE_LIMITER']) {
    const env = accessEnvironment(`sing-yin-runtime-missing-${bindingName.toLowerCase()}`);
    delete env[bindingName];
    const health = await worker.fetch(
      new Request('https://gateway.example/healthz'),
      env,
      { waitUntil() {} },
    );
    const body = await health.text();
    assertEquals(health.status, 503);
    assert(body.includes('configuration_error'));
    assert(!body.includes(bindingName));
    assertEquals(health.headers.get('Cache-Control'), 'no-store, max-age=0');
  }
});

Deno.test('admin sessions are bounded and reject tampering, expiry, and removed administrators', async () => {
  const env = accessEnvironment('sing-yin-runtime-session-validation');
  const nowMillis = Date.now();
  const nowSeconds = Math.floor(nowMillis / 1_000);
  const session = await createAdminSessionToken(
    configuredAdminEmails(env)[0],
    nowSeconds + (24 * 60 * 60),
    env,
    { nowMillis },
  );
  assertEquals(session.payload.exp - session.payload.iat, 8 * 60 * 60);
  const valid = await validateAdminSessionToken(session.token, env, { nowMillis });
  assertEquals(valid.email, configuredAdminEmails(env)[0]);

  const [payloadSegment, signatureSegment] = session.token.split('.');
  const tamperedSignature = `${signatureSegment.startsWith('A') ? 'B' : 'A'}${signatureSegment.slice(1)}`;
  const tampered = `${payloadSegment}.${tamperedSignature}`;
  await expectRejected(() => validateAdminSessionToken(tampered, env, { nowMillis }));

  let originCalls = 0;
  env.ROSTER_ORIGIN = { fetch() { originCalls += 1; return new Response('unexpected'); } };
  const rejectedRoute = await worker.fetch(new Request('https://gateway.example/rosters', {
    headers: { Cookie: `${ADMIN_SESSION_COOKIE_NAME}=${encodeURIComponent(tampered)}` },
  }), env, { waitUntil() {} });
  assertEquals(rejectedRoute.status, 403);
  assertEquals(originCalls, 0);

  const oldNowMillis = nowMillis - (9 * 60 * 60 * 1_000);
  const oldNowSeconds = Math.floor(oldNowMillis / 1_000);
  const expired = await createAdminSessionToken(
    configuredAdminEmails(env)[0],
    oldNowSeconds + 300,
    env,
    { nowMillis: oldNowMillis },
  );
  await expectRejected(() => validateAdminSessionToken(expired.token, env, { nowMillis }));

  const changedAllowlist = {
    ...env,
    ADMIN_IDENTITY_ALLOWLIST: JSON.stringify({ emails: ['replacement-admin@syss.edu.hk'] }),
  };
  await expectRejected(() => validateAdminSessionToken(session.token, changedAllowlist, { nowMillis }));
});

Deno.test('creates a bounded guest session only through a same-origin POST', async () => {
  const env = accessEnvironment('sing-yin-runtime-guest-start');
  const context = { waitUntil() {} };
  const denied = await worker.fetch(new Request('https://gateway.example/auth/guest/start', {
    method: 'POST',
    headers: { Origin: 'https://attacker.example', 'Sec-Fetch-Site': 'cross-site' },
  }), env, context);
  assertEquals(denied.status, 403);

  const started = await worker.fetch(new Request('https://gateway.example/auth/guest/start', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Origin: 'https://gateway.example',
      'Sec-Fetch-Site': 'same-origin',
    },
  }), env, context);
  assertEquals(started.status, 201);
  const body = await started.json();
  assertEquals(body.mode, 'guest');
  assertEquals(body.authenticated, true);
  assertEquals(body.redirect, '/');
  const cookie = started.headers.get('Set-Cookie') || '';
  assert(cookie.startsWith(`${GUEST_SESSION_COOKIE_NAME}=`));
  for (const attribute of ['Max-Age=', 'Path=/', 'HttpOnly', 'Secure', 'SameSite=Lax']) {
    assert(cookie.includes(attribute), `missing guest cookie attribute: ${attribute}`);
  }
  const token = decodeURIComponent(cookie.split(';', 1)[0].split('=', 2)[1]);
  const validated = await validateGuestSessionToken(token, env);
  assertEquals(validated.exp - validated.iat, 30 * 60);
  assertEquals(validated.epoch, env.AUTH_EPOCH);
});

Deno.test('rate limits public entry points with stable privacy-safe actor keys', async () => {
  const env = accessEnvironment('sing-yin-runtime-rate-limits');
  const guestKeys = [];
  env.GUEST_START_RATE_LIMITER = {
    async limit({ key }) {
      guestKeys.push(key);
      return { success: false };
    },
  };
  const guestRequest = address => new Request('https://gateway.example/auth/guest/start', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'CF-Connecting-IP': address,
      Origin: 'https://gateway.example',
      'Sec-Fetch-Site': 'same-origin',
    },
  });

  const first = await worker.fetch(guestRequest('203.0.113.42'), env, { waitUntil() {} });
  const second = await worker.fetch(guestRequest('203.0.113.42'), env, { waitUntil() {} });
  await worker.fetch(guestRequest('2001:db8::42'), env, { waitUntil() {} });
  assertEquals(first.status, 429);
  assertEquals((await first.json()).error, 'rate_limited');
  assertEquals(first.headers.get('Retry-After'), '60');
  assertEquals(first.headers.get('Cache-Control'), 'no-store, max-age=0');
  assertEquals(first.headers.get('Set-Cookie'), null);
  assertEquals(second.status, 429);
  assertEquals(guestKeys.length, 3);
  assertEquals(guestKeys[0], guestKeys[1]);
  assert(guestKeys[0] !== guestKeys[2]);
  assert(!guestKeys.join(' ').includes('203.0.113.42'));
  assert(!guestKeys.join(' ').includes('2001:db8::42'));

  let viewKey = '';
  env.PUBLIC_VIEW_RATE_LIMITER = {
    async limit({ key }) {
      viewKey = key;
      return { success: false };
    },
  };
  const view = await worker.fetch(new Request('https://gateway.example/api/view', {
    method: 'POST',
    headers: {
      'CF-Connecting-IP': '203.0.113.42',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ shareId: 'rate_limit_share_identifier_123' }),
  }), env, { waitUntil() {} });
  assertEquals(view.status, 429);
  assertEquals((await view.json()).error, 'rate_limited');
  assertEquals(view.headers.get('Retry-After'), '60');
  assertEquals(view.headers.get('Cache-Control'), 'no-store, max-age=0');
  assert(viewKey.startsWith('rl:v1:public-view:'));
  assert(!viewKey.includes('203.0.113.42'));
});

Deno.test('public entry points fail closed when edge protection is unavailable', async () => {
  const env = accessEnvironment('sing-yin-runtime-rate-limit-failure');
  env.GUEST_START_RATE_LIMITER = {
    async limit() {
      throw new Error('simulated binding failure');
    },
  };
  const unavailable = await worker.fetch(new Request('https://gateway.example/auth/guest/start', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'CF-Connecting-IP': '198.51.100.25',
      Origin: 'https://gateway.example',
      'Sec-Fetch-Site': 'same-origin',
    },
  }), env, { waitUntil() {} });
  const payload = await unavailable.json();
  assertEquals(unavailable.status, 503);
  assertEquals(payload.error, 'edge_protection_unavailable');
  assertEquals(unavailable.headers.get('Retry-After'), '15');
  assertEquals(unavailable.headers.get('Cache-Control'), 'no-store, max-age=0');
  assert(!JSON.stringify(payload).includes('198.51.100.25'));
});

Deno.test('rejects guest-session tampering expiry epoch changes and missing secrets', async () => {
  const env = accessEnvironment('sing-yin-runtime-guest-session');
  const nowMillis = 2_000_000_000_000;
  const session = await createGuestSessionToken(env, {
    nowMillis,
    sidBytes: new Uint8Array(16).fill(5),
  });
  assertEquals((await validateGuestSessionToken(session.token, env, { nowMillis })).sid, base64Url(new Uint8Array(16).fill(5)));

  const [payload, signature] = session.token.split('.');
  const tampered = `${payload}.${signature.startsWith('A') ? 'B' : 'A'}${signature.slice(1)}`;
  await expectRejected(() => validateGuestSessionToken(tampered, env, { nowMillis }));
  await expectRejected(() => validateGuestSessionToken(session.token, env, { nowMillis: nowMillis + 30 * 60 * 1_000 }));
  await expectRejected(() => validateGuestSessionToken(session.token, { ...env, AUTH_EPOCH: env.AUTH_EPOCH + 1 }, { nowMillis }));
  const noSecret = { ...env };
  delete noSecret.GUEST_SESSION_SECRET;
  await expectRejected(() => createGuestSessionToken(noSecret, { nowMillis }));
});

Deno.test('legacy guest paths redirect into the unified bootstrap and then proxy the same origin', async () => {
  const env = accessEnvironment('sing-yin-runtime-unified-guest');
  const context = { waitUntil() {} };
  let originRequest;
  env.ROSTER_ORIGIN = {
    fetch(request) {
      originRequest = request;
      return new Response('unified guest workbench', { status: 200 });
    },
  };

  for (const path of ['/guest', '/try']) {
    const legacy = await worker.fetch(new Request(`https://gateway.example${path}`), env, context);
    assertEquals(legacy.status, 302);
    assertEquals(legacy.headers.get('Location'), 'https://gateway.example/?guest=1');

    const legacyHead = await worker.fetch(new Request(`https://gateway.example${path}`, {
      method: 'HEAD',
    }), env, context);
    assertEquals(legacyHead.status, 302);
    const landingHead = await worker.fetch(new Request(legacyHead.headers.get('Location'), {
      method: 'HEAD',
    }), env, context);
    assertEquals(landingHead.status, 200);
    assertEquals((await landingHead.arrayBuffer()).byteLength, 0);
  }
  const bootstrap = await worker.fetch(new Request('https://gateway.example/?guest=1'), env, context);
  assertEquals(bootstrap.status, 200);
  const html = await bootstrap.text();
  assert(html.includes('data-guest-bootstrap="true"'));
  const viewerScript = await worker.fetch(new Request('https://gateway.example/viewer.js'), env, context);
  const script = await viewerScript.text();
  assert(script.includes("fetch('/auth/guest/start'"));
  assert(script.includes("window.location.replace('/')"));

  const guestCookie = await guestSessionCookiePair(env);
  const app = await worker.fetch(new Request('https://gateway.example/rosters', {
    headers: { Cookie: `session=nicegui-session; ${guestCookie}` },
  }), env, context);
  assertEquals(await app.text(), 'unified guest workbench');
  assertEquals(originRequest.url, 'http://127.0.0.1:8080/rosters');
  assertEquals(originRequest.headers.get('Cookie'), 'session=nicegui-session');
  const principal = signedPayload(originRequest.headers.get('X-Sing-Yin-Origin-Principal') || '');
  assertEquals(principal.mode, 'guest');
  assertEquals(principal.subject, 'guest');
  assertEquals(principal.exp - principal.iat <= 30 * 60, true);

  const status = await worker.fetch(new Request('https://gateway.example/auth/status', {
    headers: { Cookie: guestCookie },
  }), env, context);
  const statusPayload = await status.json();
  assertEquals(status.status, 200);
  assertEquals(statusPayload.authenticated, true);
  assertEquals(statusPayload.mode, 'guest');
  assertEquals(statusPayload.origin, 'ok');
});

Deno.test('proxied HTTP workbench responses gain the workbench-safe header contract', async () => {
  const env = accessEnvironment('sing-yin-runtime-workbench-headers');
  const guestCookie = await guestSessionCookiePair(env);
  env.ROSTER_ORIGIN = {
    fetch() {
      return new Response('workbench', {
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    },
  };

  const result = await worker.fetch(new Request('https://gateway.example/rosters', {
    headers: { Cookie: guestCookie },
  }), env, { waitUntil() {} });

  assertEquals(await result.text(), 'workbench');
  assertEquals(result.headers.get('Strict-Transport-Security'), 'max-age=63072000; includeSubDomains; preload');
  assertEquals(result.headers.get('Cross-Origin-Opener-Policy'), 'same-origin');
  assertEquals(result.headers.get('Cross-Origin-Resource-Policy'), 'same-origin');
  assert((result.headers.get('Permissions-Policy') || '').includes('autoplay=(self)'));
  assertEquals(result.headers.get('X-Content-Type-Options'), 'nosniff');
  assertEquals(result.headers.get('X-Frame-Options'), 'SAMEORIGIN');
  assertEquals(result.headers.get('Content-Security-Policy'), null);
});

Deno.test('generated PDF downloads preserve binary bytes and delivery headers through the gateway', async () => {
  const env = accessEnvironment('sing-yin-runtime-generated-download');
  const guestCookie = await guestSessionCookiePair(env);
  const expected = new Uint8Array([37, 80, 68, 70, 45, 49, 46, 55, 10, 37, 255, 255]);
  let originRequest;
  env.ROSTER_ORIGIN = {
    fetch(request) {
      originRequest = request;
      return new Response(expected, {
        status: 200,
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': 'attachment; filename="SYSS_Roster_DEMO_EN.pdf"',
          'Cache-Control': 'no-store',
          'X-Sing-Yin-Support-Reference': 'DL-TEST-001',
        },
      });
    },
  };

  const result = await worker.fetch(new Request(
    'https://gateway.example/api/generated-download/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
    { headers: { Cookie: guestCookie } },
  ), env, { waitUntil() {} });

  assertEquals(originRequest.url, 'http://127.0.0.1:8080/api/generated-download/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA');
  assertEquals(result.status, 200);
  assertEquals(result.headers.get('Content-Type'), 'application/pdf');
  assertEquals(result.headers.get('Content-Disposition'), 'attachment; filename="SYSS_Roster_DEMO_EN.pdf"');
  assertEquals(result.headers.get('Cache-Control'), 'no-store');
  assertEquals(result.headers.get('X-Sing-Yin-Support-Reference'), 'DL-TEST-001');
  assertEquals(
    JSON.stringify([...new Uint8Array(await result.arrayBuffer())]),
    JSON.stringify([...expected]),
  );
});

Deno.test('serves the immutable Service Weave PNG identity and redirects the old SVG path', async () => {
  const context = { waitUntil() {} };
  const favicon = await worker.fetch(
    new Request('https://gateway.example/favicon.png'),
    {},
    context,
  );
  assertEquals(favicon.status, 200);
  assertEquals(favicon.headers.get('Content-Type'), 'image/png');
  assertEquals(favicon.headers.get('Cache-Control'), 'public, max-age=31536000, immutable');
  assert((favicon.headers.get('ETag') || '').startsWith('"sha256-'));
  const bytes = new Uint8Array(await favicon.arrayBuffer());
  assertEquals(bytes.byteLength, Number(favicon.headers.get('Content-Length')));
  assertEquals(
    JSON.stringify([...bytes.slice(0, 8)]),
    JSON.stringify([137, 80, 78, 71, 13, 10, 26, 10]),
  );

  const head = await worker.fetch(
    new Request('https://gateway.example/favicon.png', { method: 'HEAD' }),
    {},
    context,
  );
  assertEquals(head.status, 200);
  assertEquals((await head.arrayBuffer()).byteLength, 0);
  assertEquals(head.headers.get('Content-Length'), favicon.headers.get('Content-Length'));

  const legacy = await worker.fetch(
    new Request('https://gateway.example/favicon.svg'),
    {},
    context,
  );
  assertEquals(legacy.status, 308);
  assertEquals(legacy.headers.get('Location'), 'https://gateway.example/favicon.png');
});

Deno.test('admin principal wins when both valid gateway cookies are present', async () => {
  const env = accessEnvironment('sing-yin-runtime-principal-precedence');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const adminCookie = await adminSessionCookiePair(env, configuredAdminEmails(env)[0], nowSeconds + 600);
  const guestCookie = await guestSessionCookiePair(env);
  let originRequest;
  env.ROSTER_ORIGIN = {
    fetch(request) {
      originRequest = request;
      return new Response('admin');
    },
  };
  const result = await worker.fetch(new Request('https://gateway.example/settings', {
    headers: { Cookie: `${adminCookie}; ${guestCookie}; session=nicegui-session` },
  }), env, { waitUntil() {} });
  assertEquals(await result.text(), 'admin');
  const principal = signedPayload(originRequest.headers.get('X-Sing-Yin-Origin-Principal') || '');
  assertEquals(principal.mode, 'admin');
  assertEquals(principal.subject, configuredAdminEmails(env)[0]);
  assertEquals(originRequest.headers.get('Cookie'), 'session=nicegui-session');
});

Deno.test('origin principal vector is deterministic request-bound epoch-aware and key-rotation-aware', async () => {
  const env = accessEnvironment('sing-yin-runtime-origin-vector');
  const nowMillis = 2_000_000_000_000;
  const request = new Request('https://gateway.example/rosters?week=2026-07-13', { method: 'GET' });
  const principal = {
    mode: 'guest',
    subject: 'guest',
    sid: base64Url(new Uint8Array(16).fill(4)),
    exp: Math.floor(nowMillis / 1_000) + 1_800,
  };
  const signed = await createOriginPrincipalToken(request, principal, env, { nowMillis });
  assertEquals(signed.payload.request_binding, await originRequestBinding(request));
  assertEquals(signed.payload.request_binding, 'IA6owyScWUXkk2hYMBvAgo2d9EdLSxS3Jwil1BFlIrQ'); // pragma: allowlist secret -- deterministic request-binding vector
  assertEquals(signed.payload.auth_epoch, env.AUTH_EPOCH);
  assertEquals(signed.payload.kid, env.ORIGIN_PRINCIPAL_KID);
  assertEquals(signed.payload.exp, principal.exp);
  assertEquals(signed.payload.iat, Math.floor(nowMillis / 1_000));
  assertEquals(
    signed.token,
    'eyJ2IjoxLCJhdWQiOiJzaW5nLXlpbi1yb3N0ZXItb3JpZ2luIiwibW9kZSI6Imd1ZXN0Iiwic3ViamVjdCI6Imd1ZXN0Iiwic2lkIjoiQkFRRUJBUUVCQVFFQkFRRUJBUUVCQSIsImlhdCI6MjAwMDAwMDAwMCwiZXhwIjoyMDAwMDAxODAwLCJhdXRoX2Vwb2NoIjo3LCJraWQiOiJ0ZXN0LW9yaWdpbi12NyIsInJlcXVlc3RfYmluZGluZyI6IklBNm93eVNjV1VYa2syaFlNQnZBZ28yZDlFZExTeFMzSndpbDFCRmxJclEifQ.2TQ5sfwCOuoBII4Ytf8FJLCuYV-8Eo7ki3-FPmJWv04',
  );

  const changedPath = new Request('https://gateway.example/settings', { method: 'GET' });
  const changed = await createOriginPrincipalToken(changedPath, principal, env, { nowMillis });
  assert(signed.token !== changed.token);
  assert(signed.payload.request_binding !== changed.payload.request_binding);
  const rotated = await createOriginPrincipalToken(request, principal, {
    ...env,
    ORIGIN_PRINCIPAL_KID: 'test-origin-v8',
    ORIGIN_PRINCIPAL_SECRET: 'rotated-test-origin-principal-secret-with-more-than-32-characters', // pragma: allowlist secret -- deterministic rotation fixture
  }, { nowMillis });
  assertEquals(rotated.payload.kid, 'test-origin-v8');
  assert(rotated.token !== signed.token);
  const noOriginSecret = { ...env };
  delete noOriginSecret.ORIGIN_PRINCIPAL_SECRET;
  await expectRejected(() => createOriginPrincipalToken(request, principal, noOriginSecret, { nowMillis }));
});

Deno.test('POST logout clears both gateway identities and public status stays data-free', async () => {
  const env = accessEnvironment('sing-yin-runtime-auth-lifecycle');
  const context = { waitUntil() {} };
  const publicStatus = await worker.fetch(new Request('https://gateway.example/auth/status'), env, context);
  assertEquals(publicStatus.status, 200);
  assertEquals((await publicStatus.json()).mode, 'public');

  const loggedOut = await worker.fetch(new Request('https://gateway.example/auth/logout', {
    method: 'POST',
    headers: { Origin: 'https://gateway.example', 'Sec-Fetch-Site': 'same-origin' },
  }), env, context);
  assertEquals(loggedOut.status, 303);
  const cookies = loggedOut.headers.get('Set-Cookie') || '';
  assert(cookies.includes(`${ADMIN_SESSION_COOKIE_NAME}=`));
  assert(cookies.includes(`${GUEST_SESSION_COOKIE_NAME}=`));
  assert(cookies.match(/Max-Age=0/g)?.length >= 2);
});

Deno.test('authenticated logout revokes admin and guest origin sessions before clearing cookies', async () => {
  const env = accessEnvironment('sing-yin-runtime-revocation-order');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const credentials = [
    {
      mode: 'admin',
      cookie: await adminSessionCookiePair(
        env,
        configuredAdminEmails(env)[0],
        nowSeconds + 600,
      ),
    },
    {
      mode: 'guest',
      cookie: await guestSessionCookiePair(env),
    },
  ];
  const observed = [];
  env.ROSTER_ORIGIN = {
    fetch(request) {
      observed.push({
        method: request.method,
        url: request.url,
        principal: signedPayload(
          request.headers.get('X-Sing-Yin-Origin-Principal') || '',
        ),
      });
      return new Response(null, { status: 204 });
    },
  };

  for (const credential of credentials) {
    const response = await worker.fetch(new Request('https://gateway.example/auth/logout', {
      method: 'POST',
      headers: {
        Cookie: credential.cookie,
        Origin: 'https://gateway.example',
        'Sec-Fetch-Site': 'same-origin',
      },
    }), env, { waitUntil() {} });
    assertEquals(response.status, 303);
    assert((response.headers.get('Set-Cookie') || '').includes('Max-Age=0'));
  }

  assertEquals(observed.length, 2);
  for (let index = 0; index < observed.length; index += 1) {
    assertEquals(observed[index].method, 'POST');
    assertEquals(observed[index].url, 'http://127.0.0.1:8080/api/auth/session/revoke');
    assertEquals(observed[index].principal.mode, credentials[index].mode);
    assertEquals(observed[index].principal.request_binding.length > 20, true);
  }
});

Deno.test('authenticated logout fails closed when origin revocation is not confirmed', async () => {
  const env = accessEnvironment('sing-yin-runtime-revocation-failure');
  const guestCookie = await guestSessionCookiePair(env);
  env.ROSTER_ORIGIN = {
    fetch() {
      return new Response('not revoked', { status: 503 });
    },
  };

  const response = await worker.fetch(new Request('https://gateway.example/auth/logout', {
    method: 'POST',
    headers: {
      Cookie: guestCookie,
      Origin: 'https://gateway.example',
      'Sec-Fetch-Site': 'same-origin',
    },
  }), env, { waitUntil() {} });

  assertEquals(response.status, 503);
  assertEquals((await response.json()).error, 'logout_temporarily_unavailable');
  assertEquals(response.headers.get('Set-Cookie'), null);
});

Deno.test('cancels an oversized chunked public viewer request before buffering the full body', async () => {
  let cancelled = false;
  let emitted = 0;
  const body = new ReadableStream({
    pull(controller) {
      emitted += 1;
      controller.enqueue(new Uint8Array(1_024));
      if (emitted >= 20) controller.close();
    },
    cancel() {
      cancelled = true;
    },
  });
  const request = new Request('https://gateway.example/api/view', { method: 'POST', body });
  const response = await worker.fetch(request, accessEnvironment('sing-yin-runtime-body-limit'), { waitUntil() {} });

  assertEquals(response.status, 404);
  assert(cancelled, 'the oversized request stream should be cancelled');
  assert(emitted < 20, 'the worker must not buffer the entire oversized request');
});

Deno.test('authenticated app routes return the VPC response directly without cloning WebSocket state', async () => {
  const env = accessEnvironment('sing-yin-runtime-proxy');
  const fixture = await signingFixture();
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const token = await signedJwt(validClaims(env, nowSeconds));
  const sentinel = { status: 101, webSocket: { preserved: true } };
  let originRequest;
  let originCalls = 0;
  env.ROSTER_ORIGIN = {
    fetch(request) {
      originCalls += 1;
      originRequest = request;
      return sentinel;
    },
  };
  const originalFetch = globalThis.fetch;
  globalThis.fetch = jwksFetcher(fixture.jwk);
  try {
    const publicViewer = await worker.fetch(new Request('https://gateway.example/view', {
      headers: { Cookie: `CF_Authorization=${token}` },
    }), env, { waitUntil() {} });
    assertEquals(publicViewer.status, 200);
    assertEquals(originCalls, 0, 'Access cookies must not divert the public viewer');

    const login = await worker.fetch(new Request('https://gateway.example/auth/login', {
      headers: { 'Cf-Access-Jwt-Assertion': token },
    }), env, { waitUntil() {} });
    assertEquals(login.status, 302);
    assertEquals(login.headers.get('Location'), 'https://gateway.example/');
    const setCookie = login.headers.get('Set-Cookie') || '';
    assert(setCookie.startsWith(`${ADMIN_SESSION_COOKIE_NAME}=`));
    assert(setCookie.includes('Path=/'));
    assert(setCookie.includes('HttpOnly'));
    assert(setCookie.includes('Secure'));
    assert(setCookie.includes('SameSite=Lax'));
    assert(!setCookie.includes(token), 'the Access JWT must never be copied into the first-party session');
    const adminCookie = setCookie.split(';', 1)[0];

    const result = await worker.fetch(new Request('https://gateway.example/op', {
      headers: {
        Cookie: `session=nicegui-session; ${adminCookie}; CF_Authorization=secret-cookie`,
      },
    }), env, { waitUntil() {} });
    assertEquals(result, sentinel, 'the 101/WebSocket carrier must not pass through secured()');
    assertEquals(originRequest.url, 'http://127.0.0.1:8080/op');
    assertEquals(originRequest.headers.get('Cookie'), 'session=nicegui-session');
    assertEquals(originRequest.headers.get('X-Sing-Yin-Access-Email'), null);
    const principal = signedPayload(originRequest.headers.get('X-Sing-Yin-Origin-Principal') || '');
    assertEquals(principal.mode, 'admin');
    assertEquals(principal.subject, configuredAdminEmails(env)[0]);
    assertEquals(principal.exp - principal.iat <= 8 * 60 * 60, true);

    const websocketResult = await worker.fetch(new Request('https://gateway.example/_nicegui_ws', {
      headers: {
        Cookie: adminCookie,
        Upgrade: 'websocket',
        Origin: 'https://gateway.example',
        'Sec-Fetch-Site': 'same-origin',
      },
    }), env, { waitUntil() {} });
    assertEquals(websocketResult, sentinel, 'authenticated WebSocket 101 must remain untouched');
    assertEquals(originRequest.url, 'http://127.0.0.1:8080/_nicegui_ws');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

Deno.test('public support stays browser-only while authenticated support reaches the workbench', async () => {
  const env = accessEnvironment('sing-yin-runtime-support-routing');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const credentials = [
    {
      mode: 'admin',
      cookie: await adminSessionCookiePair(
        env,
        configuredAdminEmails(env)[0],
        nowSeconds + 300,
      ),
    },
    {
      mode: 'guest',
      cookie: await guestSessionCookiePair(env),
    },
  ];
  const observed = [];
  env.ROSTER_ORIGIN = {
    fetch(request) {
      observed.push({
        url: request.url,
        principal: signedPayload(
          request.headers.get('X-Sing-Yin-Origin-Principal') || '',
        ),
      });
      return new Response('<main>workbench support</main>', {
        status: 200,
        headers: { 'Content-Type': 'text/html; charset=utf-8' },
      });
    },
  };

  const publicResponse = await worker.fetch(
    new Request('https://gateway.example/support'),
    env,
    { waitUntil() {} },
  );
  const publicBody = await publicResponse.text();
  assertEquals(publicResponse.status, 200);
  assert(publicBody.includes('only in your browser'));
  assertEquals(publicResponse.headers.get('Cache-Control'), 'no-store');
  assertEquals(observed.length, 0, 'public support must not reach the origin');

  for (const credential of credentials) {
    const response = await worker.fetch(new Request('https://gateway.example/support', {
      headers: { Cookie: credential.cookie },
    }), env, { waitUntil() {} });
    assertEquals(response.status, 200);
    assertEquals(await response.text(), '<main>workbench support</main>');
  }

  assertEquals(observed.length, 2);
  for (let index = 0; index < observed.length; index += 1) {
    assertEquals(observed[index].url, 'http://127.0.0.1:8080/support');
    assertEquals(observed[index].principal.mode, credentials[index].mode);
  }
});

Deno.test('authenticated status verifies the private origin without exposing identity or configuration', async () => {
  const env = accessEnvironment('sing-yin-runtime-status');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const adminCookie = await adminSessionCookiePair(
    env,
      configuredAdminEmails(env)[0],
    nowSeconds + 300,
  );
  let originRequest;
  env.ROSTER_ORIGIN = {
    fetch(request) {
      originRequest = request;
      return new Response(JSON.stringify({ status: 'ok' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    },
  };
  const result = await worker.fetch(new Request('https://gateway.example/auth/status', {
    headers: { Cookie: adminCookie },
  }), env, { waitUntil() {} });
  const body = await result.text();

  assertEquals(result.status, 200);
  assertEquals(originRequest.url, 'http://127.0.0.1:8080/healthz');
  assert(body.includes('"gateway":"ok"'));
  assert(body.includes('"access":"ok"'));
  assert(body.includes('"origin":"ok"'));
  assert(body.includes('"mode":"admin"'));
  assert(!body.includes(env.ACCESS_AUD));
    assert(!body.includes(configuredAdminEmails(env)[0]));
});

Deno.test('verified administrators receive a guided origin failure with a support reference', async () => {
  const env = accessEnvironment('sing-yin-runtime-origin-failure');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const adminCookie = await adminSessionCookiePair(
    env,
    configuredAdminEmails(env)[0],
    nowSeconds + 300,
  );
  env.ROSTER_ORIGIN = { fetch() { throw new Error('private origin unavailable'); } };
  const result = await worker.fetch(new Request('https://gateway.example/rosters', {
    headers: { Cookie: adminCookie },
  }), env, { waitUntil() {} });
  const body = await result.text();

  assertEquals(result.status, 503);
  assertEquals(result.headers.get('Retry-After'), '15');
  assert(/^GW-[A-F0-9]{12}$/.test(result.headers.get('X-Sing-Yin-Support-Reference') || ''));
  assert(body.includes('主機暫時未能連接'));
  assert(body.includes('Your administrator identity was verified'));
  assert(!body.includes(adminCookie));
  assert(!body.includes(configuredAdminEmails(env)[0]));
});

Deno.test('replays an identical share create safely but rejects a conflicting share id', async () => {
  const kv = memoryKv();
  const env = {
    ADMIN_BEARER_TOKEN: 'a'.repeat(48),
    ROSTER_SHARES: kv,
  };
  const expiresAt = new Date(Date.now() + 3_600_000).toISOString();
  const payload = {
    schemaVersion: 'sing-yin-public-roster-v1',
    shareId: 'idempotent_share_identifier_1234',
    weekStart: '2026-09-07',
    createdAt: new Date().toISOString(),
    expiresAt,
    nonce: base64Url(new Uint8Array(12).fill(7)),
    ciphertext: base64Url(new Uint8Array(32).fill(9)),
  };
  const requestFor = body => new Request('https://gateway.example/api/admin/shares', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  const created = await worker.fetch(requestFor(payload), env, { waitUntil() {} });
  const replayed = await worker.fetch(requestFor(payload), env, { waitUntil() {} });
  const conflict = await worker.fetch(requestFor({ ...payload, ciphertext: base64Url(new Uint8Array(32).fill(4)) }), env, { waitUntil() {} });
  const createdBody = await created.json();
  const replayedBody = await replayed.json();

  assertEquals(created.status, 201);
  assertEquals(replayed.status, 200);
  assertEquals(conflict.status, 409);
  assertEquals(createdBody.shareId, replayedBody.shareId);
  assertEquals(createdBody.createdAt, replayedBody.createdAt);
  assertEquals(createdBody.contentDigest, replayedBody.contentDigest);
  assertEquals(kv.records.size, 1);
  const [storedKey] = [...kv.records.keys()];
  assert(storedKey.startsWith(`share:v2:${payload.shareId}:`));
  assert(/:[a-f0-9]{64}$/.test(storedKey));
  assertEquals(createdBody.contentDigest, storedKey.slice(storedKey.lastIndexOf(':') + 1));
});

Deno.test('exact share cleanup deletes the content key without relying on KV listing visibility', async () => {
  const kv = memoryKv();
  const env = {
    ADMIN_BEARER_TOKEN: 'd'.repeat(48),
    ROSTER_SHARES: kv,
  };
  const payload = {
    schemaVersion: 'sing-yin-public-roster-v1',
    shareId: 'exact_cleanup_share_identifier_1234',
    weekStart: '2026-09-07',
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
    nonce: base64Url(new Uint8Array(12).fill(1)),
    ciphertext: base64Url(new Uint8Array(32).fill(2)),
  };
  const created = await worker.fetch(new Request('https://gateway.example/api/admin/shares', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  }), env, { waitUntil() {} });
  const receipt = await created.json();
  assertEquals(created.status, 201);
  assert(/^[a-f0-9]{64}$/.test(receipt.contentDigest));

  const originalList = kv.list;
  kv.list = async () => ({ keys: [], list_complete: true });
  const deleted = await worker.fetch(new Request(
    `https://gateway.example/api/admin/shares/${payload.shareId}?contentDigest=${receipt.contentDigest}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}` } },
  ), env, { waitUntil() {} });
  kv.list = originalList;

  assertEquals(deleted.status, 204);
  assertEquals(kv.records.size, 0);
});

Deno.test('concurrent conflicting creates remain immutable and every visible conflict fails closed', async () => {
  const kv = memoryKv();
  const originalPut = kv.put.bind(kv);
  let putCount = 0;
  let releasePuts;
  const bothPuts = new Promise(resolve => { releasePuts = resolve; });
  kv.put = async (...args) => {
    putCount += 1;
    if (putCount === 2) releasePuts();
    await bothPuts;
    await originalPut(...args);
  };
  const env = { ...rateLimitEnvironment(), ADMIN_BEARER_TOKEN: 'b'.repeat(48), ROSTER_SHARES: kv };
  const createdAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + 3_600_000).toISOString();
  const basePayload = {
    schemaVersion: 'sing-yin-public-roster-v1',
    shareId: 'concurrent_share_identifier_1234',
    weekStart: '2026-09-14',
    createdAt,
    expiresAt,
    nonce: base64Url(new Uint8Array(12).fill(3)),
  };
  const requestFor = ciphertext => new Request('https://gateway.example/api/admin/shares', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ...basePayload, ciphertext }),
  });

  const [first, second] = await Promise.all([
    worker.fetch(requestFor(base64Url(new Uint8Array(32).fill(5))), env, { waitUntil() {} }),
    worker.fetch(requestFor(base64Url(new Uint8Array(32).fill(6))), env, { waitUntil() {} }),
  ]);
  assertEquals(first.status, 409);
  assertEquals(second.status, 409);
  assertEquals(kv.records.size, 2);
  assertEquals(new Set([...kv.records.keys()]).size, 2);
  for (const key of kv.records.keys()) assert(key.startsWith(`share:v2:${basePayload.shareId}:`));

  const view = await worker.fetch(new Request('https://gateway.example/api/view', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shareId: basePayload.shareId }),
  }), env, { waitUntil() {} });
  const listing = await worker.fetch(new Request('https://gateway.example/api/admin/shares', {
    headers: { Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}` },
  }), env, { waitUntil() {} });
  assertEquals(view.status, 404);
  assertEquals(listing.status, 409);

  const deleted = await worker.fetch(new Request(
    `https://gateway.example/api/admin/shares/${basePayload.shareId}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}` } },
  ), env, { waitUntil() {} });
  assertEquals(deleted.status, 204);
  assertEquals(kv.records.size, 0);
});

Deno.test('reads lists replays and deletes legacy share records without rewriting them', async () => {
  const kv = memoryKv();
  const env = { ...rateLimitEnvironment(), ADMIN_BEARER_TOKEN: 'c'.repeat(48), ROSTER_SHARES: kv };
  const shareId = 'legacy_share_identifier_123456';
  const payload = {
    schemaVersion: 'sing-yin-public-roster-v1',
    shareId,
    weekStart: '2026-09-21',
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 3_600_000).toISOString(),
    nonce: base64Url(new Uint8Array(12).fill(8)),
    ciphertext: base64Url(new Uint8Array(32).fill(2)),
  };
  const legacyCreatedAt = new Date(Date.now() - 15_000).toISOString();
  await kv.put(`share:${shareId}`, JSON.stringify({
    version: 1,
    schemaVersion: payload.schemaVersion,
    shareId,
    weekStart: payload.weekStart,
    ciphertext: payload.ciphertext,
    nonce: payload.nonce,
    createdAt: legacyCreatedAt,
    expiresAt: payload.expiresAt,
  }));

  const view = await worker.fetch(new Request('https://gateway.example/api/view', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ shareId }),
  }), env, { waitUntil() {} });
  const listing = await worker.fetch(new Request('https://gateway.example/api/admin/shares', {
    headers: { Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}` },
  }), env, { waitUntil() {} });
  const replay = await worker.fetch(new Request('https://gateway.example/api/admin/shares', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  }), env, { waitUntil() {} });
  const listBody = await listing.json();
  const replayBody = await replay.json();
  assertEquals(view.status, 200);
  assertEquals(listing.status, 200);
  assertEquals(listBody.shares.length, 1);
  assertEquals(listBody.shares[0].shareId, shareId);
  assertEquals(replay.status, 200);
  assertEquals(replayBody.createdAt, legacyCreatedAt);
  assertEquals(kv.records.size, 1);
  assert(kv.records.has(`share:${shareId}`));

  const deleted = await worker.fetch(new Request(
    `https://gateway.example/api/admin/shares/${shareId}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${env.ADMIN_BEARER_TOKEN}` } },
  ), env, { waitUntil() {} });
  assertEquals(deleted.status, 204);
  assertEquals(kv.records.size, 0);
});
