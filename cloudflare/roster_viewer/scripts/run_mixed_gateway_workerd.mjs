/**
 * Start the real roster gateway and a loopback-only origin adapter in one
 * local workerd process. This launcher is exclusively for the isolated mixed
 * load verifier; it cannot deploy or contact a Cloudflare account.
 */

import { access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const WORKER_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const PROJECT_ROOT = path.resolve(WORKER_ROOT, '..', '..');
const WORKER_ENTRY = path.join(WORKER_ROOT, 'worker.js');
const ORIGIN_PROXY_ENTRY = path.join(
  PROJECT_ROOT,
  'scripts',
  'fixtures',
  'cloudflare_loopback_origin_proxy.js',
);
// Mirror the production Worker contract; the pinned local workerd is exercised
// by the mixed-load smoke rather than inferred from its package date.
const COMPATIBILITY_DATE = '2026-07-13';

let activeMiniflare = null;

async function disposeActiveRuntime() {
  const runtime = activeMiniflare;
  activeMiniflare = null;
  if (runtime !== null) {
    await runtime.dispose();
  }
}

const ALLOWED_ARGUMENTS = new Set([
  '--port',
  '--inspector-port',
  '--origin-port',
  '--https-cert',
  '--https-key',
  '--persist',
]);

function parseArguments(argv) {
  const values = new Map();
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index];
    const value = argv[index + 1];
    if (!ALLOWED_ARGUMENTS.has(name) || !value || values.has(name)) {
      throw new Error('Invalid or duplicate mixed-load runtime argument');
    }
    values.set(name, value);
  }
  if (values.size !== ALLOWED_ARGUMENTS.size) {
    throw new Error('A required mixed-load runtime argument is missing');
  }
  return values;
}

function exactPort(rawValue, label) {
  if (!/^\d{4,5}$/.test(rawValue)) {
    throw new Error(`${label} must be an unprivileged loopback port`);
  }
  const value = Number(rawValue);
  if (!Number.isSafeInteger(value) || value < 1024 || value > 65535) {
    throw new Error(`${label} must be an unprivileged loopback port`);
  }
  return value;
}

function exactAbsolutePath(rawValue, label) {
  if (rawValue !== rawValue.trim() || !path.isAbsolute(rawValue)) {
    throw new Error(`${label} must be an absolute path`);
  }
  return path.resolve(rawValue);
}

function requiredSecret(name) {
  const value = process.env[name];
  if (typeof value !== 'string' || value !== value.trim() || value.length < 32) {
    throw new Error(`Required test-only secret ${name} is missing or malformed`);
  }
  return value;
}

async function main() {
  const argumentsByName = parseArguments(process.argv.slice(2));
  const port = exactPort(argumentsByName.get('--port'), 'port');
  const inspectorPort = exactPort(argumentsByName.get('--inspector-port'), 'inspector port');
  const originPort = exactPort(argumentsByName.get('--origin-port'), 'origin port');
  if (new Set([port, inspectorPort, originPort]).size !== 3) {
    throw new Error('Mixed-load runtime ports must be distinct');
  }

  const certificatePath = exactAbsolutePath(argumentsByName.get('--https-cert'), 'certificate');
  const keyPath = exactAbsolutePath(argumentsByName.get('--https-key'), 'private key');
  const persistencePath = exactAbsolutePath(argumentsByName.get('--persist'), 'persistence directory');
  await Promise.all([
    access(WORKER_ENTRY),
    access(ORIGIN_PROXY_ENTRY),
    access(certificatePath),
    access(keyPath),
  ]);

  const adminBearerToken = requiredSecret('SING_YIN_LOAD_ADMIN_BEARER_TOKEN');
  const adminSessionSecret = requiredSecret('SING_YIN_LOAD_ADMIN_SESSION_SECRET');
  const guestSessionSecret = requiredSecret('SING_YIN_LOAD_GUEST_SESSION_SECRET');
  const originPrincipalSecret = requiredSecret('SING_YIN_LOAD_ORIGIN_PRINCIPAL_SECRET');
  const { Log, LogLevel, Miniflare } = await import('miniflare');

  const miniflare = new Miniflare({
    host: '127.0.0.1',
    port,
    inspectorHost: '127.0.0.1',
    inspectorPort,
    httpsCertPath: certificatePath,
    httpsKeyPath: keyPath,
    kvPersist: persistencePath,
    cachePersist: false,
    log: new Log(LogLevel.INFO, { prefix: 'mixed-load-workerd' }),
    logRequests: false,
    telemetry: { enabled: false },
    workers: [
      {
        name: 'sing-yin-mixed-load-gateway',
        scriptPath: WORKER_ENTRY,
        modules: true,
        modulesRules: [
          { type: 'ESModule', include: ['**/*.js', '**/*.mjs'] },
        ],
        compatibilityDate: COMPATIBILITY_DATE,
        bindings: {
          ACCESS_TEAM_DOMAIN: 'https://mixed-load.cloudflareaccess.com',
          ACCESS_AUD: 'mixed-load-access-audience',
          ADMIN_BEARER_TOKEN: adminBearerToken,
          ADMIN_IDENTITY_ALLOWLIST: JSON.stringify({ emails: ['mixed-load-admin@example.invalid'] }),
          ADMIN_SESSION_SECRET: adminSessionSecret,
          GUEST_SESSION_SECRET: guestSessionSecret,
          AUTH_EPOCH: 1,
          ORIGIN_PORT: originPort,
          ORIGIN_PRINCIPAL_KID: 'mixed-load-origin-v1',
          ORIGIN_PRINCIPAL_SECRET: originPrincipalSecret,
        },
        serviceBindings: {
          ROSTER_ORIGIN: 'sing-yin-mixed-load-origin-proxy',
        },
        kvNamespaces: {
          ROSTER_SHARES: 'sing-yin-mixed-load-roster-shares',
        },
        ratelimits: {
          GUEST_START_RATE_LIMITER: {
            namespace_id: '1999001',
            simple: { limit: 20, period: 60 },
          },
          PUBLIC_VIEW_RATE_LIMITER: {
            namespace_id: '1999002',
            simple: { limit: 120, period: 60 },
          },
        },
      },
      {
        name: 'sing-yin-mixed-load-origin-proxy',
        scriptPath: ORIGIN_PROXY_ENTRY,
        modules: true,
        modulesRules: [
          { type: 'ESModule', include: ['**/*.js', '**/*.mjs'] },
        ],
        compatibilityDate: COMPATIBILITY_DATE,
        bindings: {
          LOOPBACK_ORIGIN: `http://127.0.0.1:${originPort}`,
        },
      },
    ],
  });
  activeMiniflare = miniflare;

  const stop = (signal) => {
    console.log(`[mixed-load-workerd] received ${signal}; stopping`);
    void disposeActiveRuntime().finally(() => process.exit(0));
  };
  process.once('SIGINT', () => stop('SIGINT'));
  process.once('SIGTERM', () => stop('SIGTERM'));

  const ready = await miniflare.ready;
  console.log(`[mixed-load-workerd] ready at ${ready.origin}`);
  await new Promise(() => {});
}

main().catch(async (error) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[ERROR] mixed-load workerd failed: ${message}`);
  process.exitCode = 1;
  try {
    await disposeActiveRuntime();
  } catch (cleanupError) {
    const cleanupMessage = cleanupError instanceof Error ? cleanupError.message : String(cleanupError);
    console.error(`[ERROR] mixed-load workerd cleanup failed: ${cleanupMessage}`);
  }
});
