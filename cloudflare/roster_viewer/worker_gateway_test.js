import worker, {
  accessTokenFromRequest,
  authenticatedProxyRequestAllowed,
  proxyToRosterOrigin,
  stripAccessCredentials,
  validateAccessJwt,
} from './worker.js';

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
    ADMIN_EMAIL: 'admin@syss.edu.hk',
  };
}

function validClaims(env, nowSeconds) {
  return {
    iss: env.ACCESS_TEAM_DOMAIN,
    aud: [env.ACCESS_AUD],
    email: env.ADMIN_EMAIL,
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

Deno.test('validates a Cloudflare Access RS256 JWT against the trusted team JWK', async () => {
  const env = accessEnvironment('sing-yin-runtime-valid');
  const nowSeconds = 2_000_000_000;
  const fixture = await signingFixture();
  const token = await signedJwt(validClaims(env, nowSeconds));
  const captured = {};

  const result = await validateAccessJwt(token, env, {
    nowMillis: nowSeconds * 1_000,
    fetcher: jwksFetcher(fixture.jwk, captured),
  });

  assertEquals(result.payload.email, env.ADMIN_EMAIL);
  assertEquals(captured.url, `${env.ACCESS_TEAM_DOMAIN}/cdn-cgi/access/certs`);
  assertEquals(captured.init.cache, 'no-store');
  assertEquals(captured.init.redirect, 'error');
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

Deno.test('strips Access credentials but preserves the NiceGUI session cookie', () => {
  const sanitized = stripAccessCredentials(new Headers({
    'Cf-Access-Jwt-Assertion': 'secret-jwt',
    'Cf-Access-Authenticated-User-Email': 'spoofed-access@example.com',
    'Cf-Access-User-UUID': 'spoofed-uuid',
    'X-Sing-Yin-Access-Email': 'spoofed@example.com',
    Cookie: 'session=nicegui-session; CF_Authorization=secret-cookie; preference=zh-HK',
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

  const loginWithoutAccess = await worker.fetch(new Request('https://gateway.example/auth/login'), env, context);
  assertEquals(loginWithoutAccess.status, 403);

  const staleCookieHome = await worker.fetch(new Request('https://gateway.example/', {
    headers: { Cookie: 'CF_Authorization=expired.or.invalid' },
  }), env, context);
  assertEquals(staleCookieHome.status, 200);
  assert((await staleCookieHome.text()).includes('管理員登入'));

  const logout = await worker.fetch(new Request('https://gateway.example/logout'), env, context);
  assertEquals(logout.status, 302);
  assertEquals(logout.headers.get('Location'), 'https://gateway.example/cdn-cgi/access/logout');

  const health = await worker.fetch(new Request('https://gateway.example/healthz'), env, context);
  const body = await health.text();
  assertEquals(health.status, 200);
  assert(body.includes('private-origin-proxy'));
  assert(!body.includes(env.ACCESS_TEAM_DOMAIN));
  assert(!body.includes(env.ADMIN_EMAIL));
  assert(!body.includes(env.ACCESS_AUD));
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

    const result = await worker.fetch(new Request('https://gateway.example/op', {
      headers: {
        'Cf-Access-Jwt-Assertion': token,
        Cookie: 'session=nicegui-session; CF_Authorization=secret-cookie',
      },
    }), env, { waitUntil() {} });
    assertEquals(result, sentinel, 'the 101/WebSocket carrier must not pass through secured()');
    assertEquals(originRequest.url, 'http://127.0.0.1:8080/op');
    assertEquals(originRequest.headers.get('Cookie'), 'session=nicegui-session');
    assertEquals(originRequest.headers.get('X-Sing-Yin-Access-Email'), env.ADMIN_EMAIL);

    const websocketResult = await worker.fetch(new Request('https://gateway.example/_nicegui_ws', {
      headers: {
        'Cf-Access-Jwt-Assertion': token,
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
