from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIEWER_ROOT = PROJECT_ROOT / "cloudflare" / "roster_viewer"
WORKER_SOURCE = VIEWER_ROOT / "worker.js"
def _source() -> str:
    return WORKER_SOURCE.read_text(encoding="utf-8")


def _jsonc(path: Path) -> dict[str, object]:
    source = "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("//")
    )
    return json.loads(re.sub(r"\s+//.*$", "", source, flags=re.MULTILINE))


def test_public_viewer_is_a_workers_dev_kv_adapter() -> None:
    configuration = _jsonc(VIEWER_ROOT / "wrangler.template.jsonc")

    assert configuration["workers_dev"] is True
    assert configuration["preview_urls"] is False
    assert configuration["main"] == "worker.js"
    assert configuration["assets"] == {"directory": "./public"}
    assert configuration["observability"] == {
        "enabled": True,
        "head_sampling_rate": 1,
        "logs": {
            "enabled": True,
            "head_sampling_rate": 1,
            "invocation_logs": True,
            "persist": True,
        },
    }
    assert configuration["vars"] == {
        "ACCESS_TEAM_DOMAIN": "https://REPLACE_WITH_TEAM_NAME.cloudflareaccess.com",
        "ACCESS_AUD": "REPLACE_WITH_ACCESS_APPLICATION_AUD",
        "AUTH_EPOCH": 1,
        "ORIGIN_PORT": 8080,
        "ORIGIN_PRINCIPAL_KID": "origin-v1",
    }
    assert configuration["secrets"] == {
        "required": [
            "ADMIN_BEARER_TOKEN",
            "ADMIN_IDENTITY_ALLOWLIST",
            "ADMIN_SESSION_SECRET",
            "GUEST_SESSION_SECRET",
            "ORIGIN_PRINCIPAL_SECRET",
        ]
    }
    assert configuration["ratelimits"] == [
        {
            "name": "GUEST_START_RATE_LIMITER",
            "namespace_id": "1077701",
            "simple": {"limit": 20, "period": 60},
        },
        {
            "name": "PUBLIC_VIEW_RATE_LIMITER",
            "namespace_id": "1077702",
            "simple": {"limit": 120, "period": 60},
        },
    ]
    assert configuration["kv_namespaces"] == [
        {
            "binding": "ROSTER_SHARES",
            "id": "REPLACE_WITH_CLOUDFLARE_KV_NAMESPACE_ID",
        }
    ]
    assert configuration["vpc_services"] == [
        {
            "binding": "ROSTER_ORIGIN",
            "service_id": "REPLACE_WITH_VPC_SERVICE_ID",
        }
    ]


def test_worker_deployment_toolchain_is_project_pinned() -> None:
    package = json.loads((VIEWER_ROOT / "package.json").read_text(encoding="utf-8"))
    lock = (VIEWER_ROOT / "pnpm-lock.yaml").read_text(encoding="utf-8")
    workspace = (VIEWER_ROOT / "pnpm-workspace.yaml").read_text(encoding="utf-8")

    assert package["private"] is True
    assert package["version"] == "1.2.0-rc.32"
    assert package["packageManager"] == "pnpm@11.7.0"
    assert package["engines"] == {"node": ">=22"}
    assert package["devDependencies"] == {"wrangler": "4.110.0"}
    assert package["scripts"]["deploy:dry-run"].startswith("wrangler deploy --dry-run --strict")
    assert "wrangler@4.110.0" in lock
    assert "sharp@0.35.0" in lock
    assert "sharp@0.34.5" not in lock
    assert workspace.splitlines() == [
        "allowBuilds:",
        "  esbuild: true",
        "  sharp: true",
        "  workerd: true",
        "strictDepBuilds: true",
        "overrides:",
        "  sharp: 0.35.0",
    ]
    assert _jsonc(VIEWER_ROOT / "wrangler.jsonc")["$schema"] == "./node_modules/wrangler/config-schema.json"


def test_welcome_audio_controller_has_no_removed_fade_hook() -> None:
    source = _source()

    assert "cancelWelcomeFade" not in source
    assert "function initialiseWelcomeAudio()" in source
    assert "initialiseWelcomeAudio();" in source


def test_production_gateway_keeps_the_exact_admin_allowlist_out_of_public_configuration() -> None:
    configuration = _jsonc(VIEWER_ROOT / "wrangler.jsonc")
    variables = configuration["vars"]

    assert "ADMIN_IDENTITY_ALLOWLIST" not in variables
    assert variables["ORIGIN_PORT"] == 8080
    assert "ADMIN_EMAIL" not in variables
    assert "ADMIN_EMAILS" not in variables
    assert configuration["secrets"] == {
        "required": [
            "ADMIN_BEARER_TOKEN",
            "ADMIN_IDENTITY_ALLOWLIST",
            "ADMIN_SESSION_SECRET",
            "GUEST_SESSION_SECRET",
            "ORIGIN_PRINCIPAL_SECRET",
        ]
    }
    assert configuration["ratelimits"] == _jsonc(
        VIEWER_ROOT / "wrangler.template.jsonc"
    )["ratelimits"]
    assert configuration["observability"]["logs"]["persist"] is True


def test_public_entry_rate_limits_use_privacy_safe_hashed_actor_keys() -> None:
    source = _source()

    for required in (
        "GUEST_START_RATE_LIMITER",
        "PUBLIC_VIEW_RATE_LIMITER",
        "CF-Connecting-IP",
        "crypto.subtle.sign('HMAC'",
        "rate_limited",
        "edge_protection_unavailable",
        "Retry-After",
        "no-store, max-age=0",
        "normalizeRateLimitConfiguration(env)",
        "edge-rate-limiting",
    ):
        assert required in source

    rate_limit_key = re.search(
        r"async function rateLimitActorKey\(.*?\n\}",
        source,
        flags=re.DOTALL,
    )
    assert rate_limit_key is not None
    assert "console." not in rate_limit_key.group(0)


def test_worker_origin_port_is_a_validated_configuration_contract() -> None:
    source = _source()

    assert "http://127.0.0.1:8080" not in source
    assert "function originPortFromEnvironment(env)" in source
    assert "rawPort === undefined" in source
    assert "port < 1024 || port > 65_535" in source
    assert source.count("originUrlFromEnvironment(env)") == 3


def test_admin_login_failures_use_privacy_safe_support_references() -> None:
    source = _source()

    for required in (
        "admin_login_bridge_failure",
        "X-Sing-Yin-Support-Reference",
        "assertionPresent",
        "authorizationCookiePresent",
        "jwt_missing",
    ):
        assert required in source
    logged_failure = re.search(r"function loggedAccessFailure\(.*?\n\}", source, flags=re.DOTALL)
    assert logged_failure is not None
    assert "payload.email" not in logged_failure.group(0)


def test_viewer_requires_fragment_key_and_client_side_aes_gcm() -> None:
    source = _source()

    assert "window.location.hash.slice(1)" in source
    assert "history.replaceState" in source
    assert "sessionStorage.setItem" in source
    assert "crypto.subtle.importKey" in source
    assert "crypto.subtle.decrypt" in source
    assert "name: 'AES-GCM'" in source
    assert "additionalData: encoder.encode(SHARE_AAD_PREFIX + shareId)" in source
    assert "body: JSON.stringify({ shareId })" in source
    assert "keyBytes" not in re.search(r"body: JSON\.stringify\(\{ shareId \}\)", source).group(0)


def test_kv_record_contains_no_plaintext_roster_fields_or_key() -> None:
    source = _source()
    record_body = re.search(
        r"function storedRecordFrom\(.*?\) \{\s*return \{(?P<body>.*?)\n\s*\};\s*\}",
        source,
        flags=re.DOTALL,
    )
    assert record_body is not None
    body = record_body.group("body")

    assert "ciphertext:" in body
    assert "nonce:" in body
    assert "weekStart," in body
    assert "expiresAt," in body
    for forbidden in (
        "keyBytes",
        "encryptionKey",
        "prefectName",
        "nameZh",
        "room",
        "dutyTime",
        "historyWeight",
        "fairness",
        "leaveReason",
    ):
        assert forbidden not in body
    assert "aad" not in body
    assert "payload.createdAt" not in body


def test_only_minimum_lifecycle_metadata_remains_outside_ciphertext() -> None:
    source = _source()

    assert "payload.schemaVersion !== SHARE_SCHEMA" in source
    assert "Object.keys(payload).some(key => !allowedFields.has(key))" in source
    assert "validIsoDate(payload.weekStart)" in source
    assert "createdAt: new Date(createdMillis).toISOString()" in source
    assert "contentDigest," in source
    assert "weekStart: resolved.record.weekStart" in source
    assert "payload.aad" not in source
    assert "sing-yin-roster-share-v1:" in source


def test_kv_share_storage_is_content_addressed_legacy_compatible_and_fail_closed() -> None:
    source = _source()

    for required in (
        "const CONTENT_SHARE_KEY_PREFIX = 'share:v2:'",
        "async function contentDigestFor(record)",
        "return `${contentSharePrefix(shareId)}${contentDigest}`",
        "const key = contentShareKey(validated.shareId, contentDigest)",
        "version: 2",
        "record.contentDigest !== parsedKey.contentDigest",
        "await contentDigestFor(record) !== parsedKey.contentDigest",
        "contentItems.length > 1 || (legacyRecord && contentItems.length > 0)",
        "legacyRecord.version !== 1",
        "if (resolved.kind !== 'record') return missingShare()",
        "...contentItems.map(item => env.ROSTER_SHARES.delete(item.name))",
    ):
        assert required in source

    assert "KV has no compare-and-swap" in source
    assert "share_conflict" in source


def test_viewer_uses_strict_headers_no_store_no_index_and_no_cors() -> None:
    source = _source()

    required_header_values = (
        "default-src 'none'",
        "script-src 'self'",
        "connect-src 'self'",
        "frame-ancestors 'none'",
        "Cache-Control': 'no-store, max-age=0",
        "Referrer-Policy': 'no-referrer",
        "X-Content-Type-Options': 'nosniff",
        "X-Frame-Options': 'DENY",
        "X-Robots-Tag': 'noindex, nofollow, noarchive, nosnippet",
        "Cross-Origin-Opener-Policy': 'same-origin",
        "Cross-Origin-Resource-Policy': 'same-origin",
        "Permissions-Policy': 'autoplay=(self), camera=(), microphone=(), geolocation=(), payment=(), usb=()",
    )
    for header in required_header_values:
        assert header in source

    assert "Access-Control-Allow-Origin" not in source
    assert "location.search" not in source
    assert "URLSearchParams" not in source
    assert "innerHTML" not in source
    assert "insertAdjacentHTML" not in source
    assert "document.write" not in source
    assert "eval(" not in source


def test_viewer_has_minimal_public_routes_and_bearer_admin_routes() -> None:
    source = _source()

    assert "path === '/healthz'" in source
    assert "path === '/guest'" in source
    assert "path === '/api/view'" in source
    assert "path === '/api/admin/shares'" in source
    assert "request.method === 'POST'" in source
    assert "request.method === 'GET'" in source
    assert "request.method === 'DELETE'" in source
    assert "Authorization" in source
    assert "Bearer " in source
    assert "configured.length >= 32" in source
    assert "User-agent: *\\nDisallow: /" in source


def test_viewer_is_bilingual_responsive_theme_aware_printable_and_reduced_motion_safe() -> None:
    source = _source()

    assert 'lang="zh-Hant-HK"' in source
    assert "導學風紀值班表" in source
    assert "Study Prefect Duty Roster" in source
    assert "休室 · Closed" in source
    assert "待補 · Vacancy" in source
    assert "@media (prefers-color-scheme: dark)" in source
    assert ':root[data-theme="dark"]' in source
    assert "EXPLICIT_THEME_STATES = ['system', 'light', 'dark']" in source
    assert "timeZone: 'Asia/Hong_Kong'" in source
    assert "--focus-ring:" in source
    assert "outline: 3px solid var(--focus-ring)" in source
    assert ".translation-label { color: var(--portal-story-muted); font-size: 0.72rem" in source
    assert ".theme-toggle-label { min-width: 0; }" in source
    assert ':root:not([data-theme-ready="true"]) .theme-toggle { visibility: hidden; }' in source
    assert 'id="themeToggle"' in source
    assert 'data-testid="public-theme-control"' in source
    assert '<span id="themeToggleLabel" class="theme-toggle-label">淺色 · Light</span>' in source
    assert "system: {\n    current: '自動 · Auto'" not in source
    assert "themeToggle?.addEventListener('click'" in source
    assert "resolvedTheme() === 'dark' ? 'light' : 'dark'" in source
    assert "function stageThemeHandoff()" in source
    assert "stageThemeHandoff();" in source
    assert "themeToggle.setAttribute('aria-pressed', String(isDark))" in source
    assert "window.addEventListener('storage'" in source
    assert "let runtimeThemePreference = null" in source
    assert "runtimeThemePreference = theme" in source
    assert "document.documentElement.dataset.themeReady = 'true'" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "@media (max-width: 700px)" in source
    assert "@media print" in source
    assert "@page { size: A4 landscape" in source
    assert "textContent" in source
    assert "Swipe horizontally to view every weekday" in source
    assert 'aria-describedby="rosterScrollHint"' in source
    assert ".guest-enter:focus-visible { outline: 3px solid var(--focus-ring);" in source
    assert ".guest-tour-card" not in source


def test_mobile_public_controls_keep_a_44px_touch_target() -> None:
    source = _source()

    verse_refresh = re.search(r"\.verse-refresh \{(?P<body>.*?)\n\}", source, re.DOTALL)
    compact_mobile = re.search(
        r"@media \(max-width: 390px\) \{(?P<body>.*?)\n\}",
        source,
        re.DOTALL,
    )

    assert verse_refresh is not None
    assert "min-height: 44px" in verse_refresh.group("body")
    assert "min-width: 44px" in verse_refresh.group("body")
    assert "flex: 0 0 auto" in verse_refresh.group("body")
    assert compact_mobile is not None
    assert ".verse-refresh { width: 44px; padding-inline: 0; }" in compact_mobile.group("body")


def test_mobile_entrance_exposes_admin_and_guest_actions_before_supplementary_content() -> None:
    source = _source()
    mobile_actions = source.index('class="mobile-entry-actions"')
    devotional = source.index('class="devotional-prompt"')

    assert mobile_actions < devotional
    assert 'class="workflow-cue"' not in source
    assert 'class="portal-kicker"' not in source
    assert 'id="mobileAdminLogin"' in source
    assert 'id="mobileGuestEnter"' in source
    assert len(re.findall(r'<a[^>]+data-entry-role="admin"', source)) == 2
    assert len(re.findall(r'<a[^>]+data-entry-role="guest"', source)) == 2
    assert ".mobile-entry-action" in source
    assert "min-height: 52px" in source
    assert '.access-panel > [data-entry-role="admin"]' in source
    assert '.access-panel > [data-entry-role="guest"] { display: none; }' in source


def test_public_support_keeps_core_fields_visible_and_optional_details_collapsed() -> None:
    source = _source()
    expected = source.index('id="supportExpected"')
    actual = source.index('id="supportActual"')
    steps = source.index('id="supportSteps"')
    details = source.index('class="support-details"')
    category = source.index('id="supportCategory"')
    impact = source.index('id="supportImpact"')
    submit = source.index('id="supportBuild"')

    assert expected < actual < steps < details < category < impact < submit
    assert 'id="supportResult" class="support-result" hidden' in source
    assert "fetch(" not in source[source.index("const PUBLIC_SUPPORT_JS"):source.index("const VIEWER_CSS")]
    assert "if (path === '/support')" in source
    assert "staticResponse(request, PUBLIC_SUPPORT_HTML" in source
    assert "if (path === '/support-feedback.js')" in source
    assert "--warning-line" not in source
    assert "--warning-soft" not in source
    assert "staticResponse(request, PUBLIC_SUPPORT_JS" in source
    unauthenticated = source.index("if (!principal)")
    support_route = source.index("if (path === '/support')", unauthenticated)
    public_fallback = source.index("return path.startsWith('/auth/')", support_route)
    assert unauthenticated < support_route < public_fallback
    assert source[support_route:public_fallback].count("'Cache-Control': 'no-store'") == 1


def test_guest_entrance_has_one_clear_login_devotional_and_accessibility_contract() -> None:
    source = _source()

    for required in (
        'href="#mainContent"',
        'id="adminLogin"',
        'id="guestEnter"',
        'id="mobileAdminLogin"',
        'id="mobileGuestEnter"',
        'href="/guest"',
        "進入訪客示範",
        "Try the fictional demo",
        'id="shareSite"',
        'href="/auth/login"',
        "查看已發布週表，或管理本週值班",
        "收到值班表分享連結？",
        "分享網站入口",
        "只會分享首頁，不包含任何值班表或查看密鑰",
        "登入管理值班表",
        "今日經文與靈修提醒",
        "和合本修訂版 2010（神版） · NKJV",
        "LANDING_DEVOTIONALS",
        "refreshLandingVerse?.addEventListener",
        'id="portalStoryMedia"',
        "/assets/entrance-operations-light-v1.webp",
        "/assets/entrance-operations-dark-v1.webp",
        "/assets/service-weave-mark-light-v1.png",
        "/assets/service-weave-mark-dark-v1.png",
        "Copyright © 2026 LI Chuangjie",
        "updatePortalStoryDepth",
        "prefers-reduced-motion: reduce",
        ".portal-story-media { transform: none !important; }",
        "@media (forced-colors: active)",
    ):
        assert required in source

    assert "setInterval(" not in source
    assert source.count("requestAnimationFrame(") == 1
    assert (
        "requestAnimationFrame(() => { document.documentElement.dataset.themeReady = 'true'; });"
        in source
    )
    assert "https://fonts." not in source
    assert "new URL('/', window.location.origin).toString()" in source
    assert "navigator.share" in source
    assert "navigator.clipboard?.writeText" in source
    assert "導學風紀值班表生成系統" in source
    assert "trust-strip" not in source


def test_welcome_music_attempts_every_visit_and_recovers_after_browser_block() -> None:
    source = _source()

    assert "WELCOME_ENABLED_KEY" not in source
    assert "sing-yin:welcome-audio-enabled:v1" not in source
    assert "welcomeDesiredEnabled = true" in source
    assert 'id="welcomeAudioRecovery"' in source
    assert 'id="welcomeAudioEnter"' in source
    assert 'id="welcomeAudioQuiet"' in source
    assert "classifyWelcomeAudioFailure" in source
    assert "classifyWelcomeAudioFailureState" in source
    assert "networkState: welcomeAudio?.networkState || 0" in source
    assert "welcomeAudioEnter?.addEventListener('click'" in source
    assert "welcomeEntryController?.setIntent('music');" in source
    assert "welcomeEntryController?.enter(destination, '')" in source
    assert "navigateAfterWelcomeChoice(destination = welcomePendingDestination)" in source
    assert "const destination = welcomePendingDestination;\n    pauseWelcomeAudio();\n    navigateAfterWelcomeChoice(destination);" in source
    assert "if (welcomeAudioRecovery) welcomeAudioRecovery.hidden = true;" in source
    assert "setWelcomeRecoveryVisible(false);\n    if (welcomeAudioStatus)" not in source
    assert "document.addEventListener('pointerdown'" not in source
    assert "else void playWelcomeAudio({ revealRecovery: true });" in source
    assert "data-autoplay-state=\"starting\"" in source
    assert "data-entry-intent=\"unset\"" in source
    assert "welcomeAudioPlayer?.dataset.autoplayState === 'blocked'" not in source


def test_guest_entrance_uses_a_local_paired_light_dark_editorial_asset() -> None:
    public_assets = VIEWER_ROOT / "public" / "assets"
    light = public_assets / "entrance-operations-light-v1.webp"
    dark = public_assets / "entrance-operations-dark-v1.webp"

    assert light.is_file() and 20_000 < light.stat().st_size < 500_000
    assert dark.is_file() and 20_000 < dark.stat().st_size < 500_000
    assert light.read_bytes()[:4] == b"RIFF"
    assert dark.read_bytes()[:4] == b"RIFF"
    assert "data:image" not in _source()


def test_guest_entrance_uses_paired_transparent_product_marks() -> None:
    public_assets = VIEWER_ROOT / "public" / "assets"
    for filename in (
        "service-weave-mark-light-v1.png",
        "service-weave-mark-dark-v1.png",
    ):
        asset = public_assets / filename
        assert asset.is_file()
        assert asset.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    source = _source()
    assert '.brand-mark-image--dark { opacity: 0; }' in source
    assert ':root[data-theme="dark"] .brand-mark-image--dark { opacity: 1; }' in source
    assert ':root:not([data-theme="light"]) .brand-mark-image--dark { opacity: 1; }' in source


def test_guest_entry_uses_a_signed_bounded_session_and_the_same_origin_workbench() -> None:
    source = _source()

    for required in (
        "const GUEST_SESSION_COOKIE_NAME = '__Host-SingYinGuestSession'",
        "const GUEST_SESSION_MAX_AGE_SECONDS = 30 * 60",
        "path === '/auth/guest/start'",
        "request.method !== 'POST'",
        "authenticatedProxyRequestAllowed(request)",
        "createGuestSessionToken(env, {",
        "validateGuestSessionToken(guestToken, env)",
        "return redirectResponse('/?guest=1', request.url)",
        'data-guest-bootstrap="true"',
        "fetch('/auth/guest/start'",
        "principal.mode",
        "proxyToRosterOrigin(request, env, principal)",
    ):
        assert required in source

    assert source.index("const adminToken = cookieValueFromRequest") < source.index(
        "const guestToken = cookieValueFromRequest"
    )
    assert "sessionStorage" not in re.search(
        r"async function createGuestSessionToken.*?\n\}",
        source,
        flags=re.DOTALL,
    ).group(0)


def test_viewer_rejects_oversized_or_long_lived_share_payloads() -> None:
    source = _source()

    assert "MAX_ADMIN_BODY_BYTES = 196_608" in source
    assert "MAX_VIEW_BODY_BYTES = 2_048" in source
    assert "MAX_SHARE_LIFETIME_MS = 31 * 24 * 60 * 60 * 1_000" in source
    assert "MAX_SHARE_LIFETIME_MS" in source
    assert "ciphertext.byteLength > 131_072" in source
    assert "payload.shareId" in source
    assert "Object.keys(payload).some(key => key !== 'shareId')" in source


def test_public_share_errors_keep_the_key_only_for_retryable_service_failures() -> None:
    source = _source()

    for required in (
        'id="retryShare"',
        "showShareError('incomplete')",
        "showShareError('unavailable')",
        "showShareError('service')",
        "showShareError('invalid')",
        "if (!copy.retryable) clearStoredShareToken()",
        "if (fragmentPersisted)",
        "retryShare?.addEventListener('click'",
        "暫時毋須重新索取分享連結",
        "You do not need to request a new link yet.",
    ):
        assert required in source

    service_copy = re.search(
        r"service: \{(?P<body>.*?)\n\s*\},",
        source,
        flags=re.DOTALL,
    )
    assert service_copy is not None
    assert "retryable: true" in service_copy.group("body")
    assert "sessionStorage.removeItem" not in service_copy.group("body")


def test_unified_gateway_validates_access_and_keeps_public_viewer_routes_separate() -> None:
    source = _source()

    for required in (
        "Cf-Access-Jwt-Assertion",
        "CF_Authorization",
        "RS256",
        "RSASSA-PKCS1-v1_5",
        "payload.iss !== configuration.teamDomain",
        "audiences.includes(configuration.audience)",
        "nowSeconds >= payload.exp",
        "nowSeconds < payload.nbf",
        "configuration.adminEmails.includes(payload.email.toLowerCase())",
        "/cdn-cgi/access/certs",
        "/cdn-cgi/access/logout",
        "path === '/auth/admin/start'",
        "path === '/auth/guest/start'",
        "path === '/auth/logout'",
        "path === '/auth/login'",
        "path === '/auth/status'",
        "path === '/view'",
        "path === '/api/view'",
        "path === '/api/admin/shares'",
    ):
        assert required in source

    assert "管理員登入" in source
    assert "Administrator sign in" in source
    assert "Access-Control-Allow-Origin" not in source


def test_authenticated_gateway_health_and_origin_failure_are_data_free_and_actionable() -> None:
    source = _source()

    for required in (
        "origin_unavailable",
        "X-Sing-Yin-Support-Reference",
        "Retry-After",
        "主機暫時未能連接",
        "new URL('/healthz', request.url)",
        "gateway: 'ok'",
        "access: 'ok'",
    ):
        assert required in source
    assert "Your administrator identity was verified" in source


def test_authenticated_proxy_is_same_origin_sanitized_and_websocket_transparent() -> None:
    source = _source()

    assert "const supportedMethods = ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE']" in source
    assert "const isUnsafeMethod = !['GET', 'HEAD', 'OPTIONS'].includes(method)" in source
    assert "fetchSite === 'same-origin'" in source
    assert "new URL(suppliedOrigin).origin !== expectedOrigin" in source
    assert "normalized.startsWith('cf-access-')" in source
    assert "normalized.startsWith('x-sing-yin-')" in source
    assert "normalized.startsWith('x-forwarded-')" in source
    assert "ACCESS_COOKIE_NAME.toLowerCase()" in source
    assert "name !== GUEST_SESSION_COOKIE_NAME" in source
    assert "headers.set(ORIGIN_PRINCIPAL_HEADER, originPrincipal.token)" in source
    assert "const ORIGIN_PRINCIPAL_HEADER = 'X-Sing-Yin-Origin-Principal'" in source
    assert "request_binding: await originRequestBinding(request)" in source
    assert "auth_epoch: authEpoch(env)" in source
    assert "kid: originPrincipalKid(env)" in source
    assert "const originUrl = originUrlFromEnvironment(env)" in source
    assert "env.ROSTER_ORIGIN.fetch(originRequest)" in source
    assert "if (routed && routed.originResponse) return securedWorkbench(routed.originResponse)" in source
    assert "if (originResponse?.status === 101 || originResponse?.webSocket) return originResponse" in source
    assert "const WORKBENCH_SECURITY_HEADERS = Object.freeze" in source
    assert "Content-Security-Policy" not in source.split(
        "const WORKBENCH_SECURITY_HEADERS = Object.freeze", 1
    )[1].split("});", 1)[0]
    assert "console.log" not in source
    assert "console.error" not in source


def test_gateway_sessions_fail_closed_and_keep_admin_precedence() -> None:
    source = _source()

    for required in (
        "GUEST_SESSION_SECRET",
        "ORIGIN_PRINCIPAL_SECRET",
        "guest_session_secret_configuration",
        "origin_principal_secret_configuration",
        "const GUEST_SESSION_MAX_AGE_SECONDS = 30 * 60",
        "const ADMIN_SESSION_MAX_AGE_SECONDS = 8 * 60 * 60",
        "payload.epoch !== authEpoch(env)",
        "const adminToken = cookieValueFromRequest(request, ADMIN_SESSION_COOKIE_NAME)",
        "const guestToken = cookieValueFromRequest(request, GUEST_SESSION_COOKIE_NAME)",
        "headers.append('Set-Cookie', adminSessionClearCookie())",
        "headers.append('Set-Cookie', guestSessionClearCookie())",
    ):
        assert required in source

    assert source.index(
        "const adminToken = cookieValueFromRequest(request, ADMIN_SESSION_COOKIE_NAME)"
    ) < source.index(
        "const guestToken = cookieValueFromRequest(request, GUEST_SESSION_COOKIE_NAME)"
    )


def test_public_request_and_jwks_bodies_are_streamed_with_hard_limits() -> None:
    source = _source()

    assert "async function readBoundedUtf8(input, maximumBytes)" in source
    assert "input.body.getReader()" in source
    assert "await reader.cancel()" in source
    assert "readBoundedUtf8(certificateResponse, ACCESS_JWKS_MAX_BYTES)" in source
    assert "readBoundedUtf8(request, maximumBytes)" in source


def test_gateway_cta_and_share_loading_expose_honest_accessible_states() -> None:
    source = _source()

    for required in (
        'class="admin-login-indicator"',
        'class="admin-login-spinner"',
        'class="sy-secure-pulse"',
        "const adminLoginButtons = Array.from(document.querySelectorAll('[data-entry-role=\"admin\"]'))",
        "adminLoginButtons.forEach((button)",
        "button.setAttribute('aria-busy', 'true')",
        "button.setAttribute('aria-disabled', 'true')",
        "createWelcomeEntryController({",
        "welcomeEntryController.enter(destination, button.dataset.entryRole || '')",
        "if (typeof destination !== 'string' || destination.length === 0 || busy) return false",
        "event.preventDefault()",
        "window.addEventListener('pageshow'",
        "button.removeAttribute('aria-busy')",
        "button.removeAttribute('aria-disabled')",
        "welcomeEntryController.reset()",
        "animation: spin 760ms linear infinite",
        "@media (prefers-reduced-motion: reduce)",
    ):
        assert required in source

    secure_indicator = source.split(".sy-secure-pulse", 1)[1].split(
        ".state-icon", 1
    )[0]
    assert "animation:" not in secure_indicator
    assert "@keyframes secure-pulse" not in source

    assert "touch-action: manipulation" in source
    assert ".access-panel .admin-login::before" in source


@pytest.mark.skipif(shutil.which("deno") is None, reason="Deno is unavailable for Worker runtime verification")
def test_worker_runtime_access_crypto_and_proxy_contracts() -> None:
    result = subprocess.run(
        [shutil.which("deno") or "deno", "test", "--no-check", "cloudflare/roster_viewer/worker_gateway_test.js"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
