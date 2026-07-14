import worker, {
  ADMIN_SESSION_COOKIE_NAME,
  LANDING_DEVOTIONALS,
  accessTokenFromRequest,
  authenticatedProxyRequestAllowed,
  createAdminSessionToken,
  normalizeAccessConfiguration,
  proxyToRosterOrigin,
  stripAccessCredentials,
  validateAdminSessionToken,
  validateAccessJwt,
} from './worker.js';
import devotionalSeed from '../../data/devotional/daily-verses.seed.json' with { type: 'json' };

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

function accessEnvironment(teamName) {
  return {
    ACCESS_TEAM_DOMAIN: `https://${teamName}.cloudflareaccess.com`,
    ACCESS_AUD: 'expected-access-audience',
    ADMIN_IDENTITY_ALLOWLIST: {
      emails: [
        'admin@syss.edu.hk',
        'operator.backup@gmail.com',
        'operator.backup@outlook.com',
      ],
    },
    ADMIN_SESSION_SECRET: 'test-only-admin-session-secret-with-more-than-32-characters', // pragma: allowlist secret -- deterministic test fixture
  };
}

async function adminSessionCookiePair(env, email, accessExpiresAt, options = {}) {
  const session = await createAdminSessionToken(email, accessExpiresAt, env, options);
  return `${ADMIN_SESSION_COOKIE_NAME}=${encodeURIComponent(session.token)}`;
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

function validClaims(env, nowSeconds, email = env.ADMIN_IDENTITY_ALLOWLIST.emails[0]) {
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

  for (const email of env.ADMIN_IDENTITY_ALLOWLIST.emails) {
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
  assertEquals(configuration.adminEmails.join(','), env.ADMIN_IDENTITY_ALLOWLIST.emails.join(','));

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
      ADMIN_IDENTITY_ALLOWLIST: { emails: invalidAdminEmails },
    })));
  }
  for (const invalidAllowlist of [
    null,
    [],
    {},
    { emails: env.ADMIN_IDENTITY_ALLOWLIST.emails, extra: true },
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
  for (const email of env.ADMIN_IDENTITY_ALLOWLIST.emails) assert(!diagnostic.includes(email));
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
  for (const email of env.ADMIN_IDENTITY_ALLOWLIST.emails) assert(!diagnostic.includes(email));
});

Deno.test('strips Access and gateway session credentials but preserves the NiceGUI session cookie', () => {
  const sanitized = stripAccessCredentials(new Headers({
    'Cf-Access-Jwt-Assertion': 'secret-jwt',
    'Cf-Access-Authenticated-User-Email': 'spoofed-access@example.com',
    'Cf-Access-User-UUID': 'spoofed-uuid',
    'X-Sing-Yin-Access-Email': 'spoofed@example.com',
    Cookie: `session=nicegui-session; CF_Authorization=secret-cookie; ${ADMIN_SESSION_COOKIE_NAME}=signed-session; preference=zh-HK`,
  }));

  assertEquals(sanitized.get('Cf-Access-Jwt-Assertion'), null);
  assertEquals(sanitized.get('Cf-Access-Authenticated-User-Email'), null);
  assertEquals(sanitized.get('Cf-Access-User-UUID'), null);
  assertEquals(sanitized.get('X-Sing-Yin-Access-Email'), null);
  assertEquals(sanitized.get('Cookie'), 'session=nicegui-session; preference=zh-HK');
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
      Cookie: 'session=nicegui-session; CF_Authorization=secret-cookie',
    },
    body: JSON.stringify({ confirmed: true }),
  });

  const result = await proxyToRosterOrigin(incoming, env, 'admin@syss.edu.hk');

  assertEquals(result, sentinel, 'origin response must be returned by identity');
  assertEquals(capturedRequest.url, 'http://127.0.0.1:8080/op/save?draft=3');
  assertEquals(capturedRequest.headers.get('Cf-Access-Jwt-Assertion'), null);
  assertEquals(capturedRequest.headers.get('Cookie'), 'session=nicegui-session');
  assertEquals(capturedRequest.headers.get('X-Sing-Yin-Access-Email'), 'admin@syss.edu.hk');
  assertEquals(capturedRequest.headers.get('X-Forwarded-Host'), 'gateway.example');
  assertEquals(await capturedRequest.text(), JSON.stringify({ confirmed: true }));
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
  for (const email of env.ADMIN_IDENTITY_ALLOWLIST.emails) assert(!body.includes(email));
  assert(!body.includes(env.ACCESS_AUD));
});

Deno.test('admin sessions are bounded and reject tampering, expiry, and removed administrators', async () => {
  const env = accessEnvironment('sing-yin-runtime-session-validation');
  const nowMillis = Date.now();
  const nowSeconds = Math.floor(nowMillis / 1_000);
  const session = await createAdminSessionToken(
    env.ADMIN_IDENTITY_ALLOWLIST.emails[0],
    nowSeconds + (24 * 60 * 60),
    env,
    { nowMillis },
  );
  assertEquals(session.payload.exp - session.payload.iat, 8 * 60 * 60);
  const valid = await validateAdminSessionToken(session.token, env, { nowMillis });
  assertEquals(valid.email, env.ADMIN_IDENTITY_ALLOWLIST.emails[0]);

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
    env.ADMIN_IDENTITY_ALLOWLIST.emails[0],
    oldNowSeconds + 300,
    env,
    { nowMillis: oldNowMillis },
  );
  await expectRejected(() => validateAdminSessionToken(expired.token, env, { nowMillis }));

  const changedAllowlist = {
    ...env,
    ADMIN_IDENTITY_ALLOWLIST: { emails: ['replacement-admin@syss.edu.hk'] },
  };
  await expectRejected(() => validateAdminSessionToken(session.token, changedAllowlist, { nowMillis }));
});

Deno.test('serves the guest tour at the edge without Access, KV, VPC, or write methods', async () => {
  const env = accessEnvironment('sing-yin-runtime-guest-tour');
  const context = { waitUntil() { throw new Error('guest tour must not schedule storage work'); } };
  let originCalls = 0;
  let certificateCalls = 0;
  env.ROSTER_ORIGIN = {
    fetch() {
      originCalls += 1;
      throw new Error('guest tour reached the private origin');
    },
  };
  env.ROSTER_SHARES = {
    get() { throw new Error('guest tour read KV'); },
    put() { throw new Error('guest tour wrote KV'); },
    delete() { throw new Error('guest tour deleted KV'); },
    list() { throw new Error('guest tour listed KV'); },
  };

  const fixture = await signingFixture();
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const token = await signedJwt(validClaims(env, nowSeconds));
  const originalFetch = globalThis.fetch;
  globalThis.fetch = () => {
    certificateCalls += 1;
    return new Response(JSON.stringify({ keys: [fixture.jwk] }), {
      headers: { 'Content-Type': 'application/json' },
    });
  };
  try {
    for (const headers of [
      {},
      { 'X-Sing-Yin-Access-Email': 'spoofed@syss.edu.hk', 'X-Sing-Yin-Access-Role': 'admin' },
      { 'Cf-Access-Jwt-Assertion': token, Cookie: `CF_Authorization=${token}` },
    ]) {
      const guest = await worker.fetch(new Request('https://gateway.example/guest', { headers }), env, context);
      assertEquals(guest.status, 200);
      const html = await guest.text();
      assert(html.includes('訪客瀏覽模式'));
      assert(html.includes('The guest tour contains no roster data.'));
      for (const forbidden of ['<form', '<input', '<textarea', '<select', 'contenteditable']) {
        assert(!html.toLowerCase().includes(forbidden));
      }
    }

    const head = await worker.fetch(new Request('https://gateway.example/guest', { method: 'HEAD' }), env, context);
    assertEquals(head.status, 200);
    assertEquals(await head.text(), '');

    for (const method of ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']) {
      const denied = await worker.fetch(new Request('https://gateway.example/guest', { method }), env, context);
      assertEquals(denied.status, 405, `${method} must be rejected at the public boundary`);
      assertEquals(denied.headers.get('Allow'), 'GET, HEAD');
    }

    for (const path of ['/_nicegui_ws', '/rosters', '/adjustments', '/settings', '/access-control']) {
      const denied = await worker.fetch(new Request(`https://gateway.example${path}`), env, context);
      assertEquals(denied.status, 302, `${path} must not reach the private origin without Access`);
      assertEquals(denied.headers.get('Location'), 'https://gateway.example/');
    }
  } finally {
    globalThis.fetch = originalFetch;
  }

  assertEquals(originCalls, 0, 'guest requests must never reach the private NiceGUI origin');
  assertEquals(certificateCalls, 0, 'guest requests must not invoke Access validation or external fetch');
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
    assertEquals(originRequest.headers.get('X-Sing-Yin-Access-Email'), env.ADMIN_IDENTITY_ALLOWLIST.emails[0]);

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

Deno.test('authenticated status verifies the private origin without exposing identity or configuration', async () => {
  const env = accessEnvironment('sing-yin-runtime-status');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const adminCookie = await adminSessionCookiePair(
    env,
    env.ADMIN_IDENTITY_ALLOWLIST.emails[0],
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
  assert(!body.includes(env.ACCESS_AUD));
  assert(!body.includes(env.ADMIN_IDENTITY_ALLOWLIST.emails[0]));
});

Deno.test('verified administrators receive a guided origin failure with a support reference', async () => {
  const env = accessEnvironment('sing-yin-runtime-origin-failure');
  const nowSeconds = Math.floor(Date.now() / 1_000);
  const adminCookie = await adminSessionCookiePair(
    env,
    env.ADMIN_IDENTITY_ALLOWLIST.emails[0],
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
  assert(!body.includes(env.ADMIN_IDENTITY_ALLOWLIST.emails[0]));
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
  assertEquals(kv.records.size, 1);
  const [storedKey] = [...kv.records.keys()];
  assert(storedKey.startsWith(`share:v2:${payload.shareId}:`));
  assert(/:[a-f0-9]{64}$/.test(storedKey));
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
  const env = { ADMIN_BEARER_TOKEN: 'b'.repeat(48), ROSTER_SHARES: kv };
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
  const env = { ADMIN_BEARER_TOKEN: 'c'.repeat(48), ROSTER_SHARES: kv };
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
