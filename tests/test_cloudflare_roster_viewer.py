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
EXPECTED_ADMIN_EMAILS = [
    "s10777@syss.edu.hk",
    "lichuangjie0208@gmail.com",
    "lichuangjie0208@outlook.com",
]


def _source() -> str:
    return WORKER_SOURCE.read_text(encoding="utf-8")


def _jsonc(path: Path) -> dict[str, object]:
    return json.loads(
        "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("//")
        )
    )


def test_public_viewer_is_a_workers_dev_kv_adapter() -> None:
    configuration = _jsonc(VIEWER_ROOT / "wrangler.template.jsonc")

    assert configuration["workers_dev"] is True
    assert configuration["preview_urls"] is False
    assert configuration["main"] == "worker.js"
    assert configuration["vars"] == {
        "ACCESS_TEAM_DOMAIN": "https://REPLACE_WITH_TEAM_NAME.cloudflareaccess.com",
        "ACCESS_AUD": "REPLACE_WITH_ACCESS_APPLICATION_AUD",
        "ADMIN_IDENTITY_ALLOWLIST": {"emails": ["REPLACE_WITH_EXACT_ADMIN_EMAIL"]},
    }
    assert configuration["secrets"] == {"required": ["ADMIN_BEARER_TOKEN"]}
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


def test_production_gateway_uses_a_bounded_exact_admin_email_allowlist() -> None:
    configuration = _jsonc(VIEWER_ROOT / "wrangler.jsonc")
    variables = configuration["vars"]

    assert variables["ADMIN_IDENTITY_ALLOWLIST"] == {"emails": EXPECTED_ADMIN_EMAILS}
    assert "ADMIN_EMAIL" not in variables
    assert "ADMIN_EMAILS" not in variables
    assert len(set(variables["ADMIN_IDENTITY_ALLOWLIST"]["emails"])) == len(EXPECTED_ADMIN_EMAILS)
    assert configuration["secrets"] == {"required": ["ADMIN_BEARER_TOKEN"]}


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
    assert "weekStart: item.metadata?.weekStart || null" in source
    assert "const createdAt = new Date(now).toISOString()" in source
    assert "payload.aad" not in source
    assert "sing-yin-roster-share-v1:" in source


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
    assert "THEME_STATES = ['system', 'light', 'dark']" in source
    assert "timeZone: 'Asia/Hong_Kong'" in source
    assert "--focus-ring:" in source
    assert "outline: 3px solid var(--focus-ring)" in source
    assert ".translation-label { color: var(--portal-story-muted); font-size: 0.72rem" in source
    assert ".theme-toggle span { white-space: nowrap; }" in source
    assert "@media (prefers-reduced-motion: reduce)" in source
    assert "@media (max-width: 700px)" in source
    assert "@media print" in source
    assert "@page { size: A4 landscape" in source
    assert "textContent" in source


def test_guest_entrance_has_one_clear_login_devotional_and_accessibility_contract() -> None:
    source = _source()

    for required in (
        'href="#mainContent"',
        'id="adminLogin"',
        'id="guestEnter"',
        'href="/guest"',
        'id="shareSite"',
        'href="/auth/login"',
        "一個入口，清晰完成每週值班工作",
        "收到值班表分享連結？",
        "分享網站入口",
        "只會分享首頁，不包含任何值班表或查看密鑰",
        "分享連結只供查看",
        "今日經文與靈修提醒",
        "和合本修訂版 2010（神版） · NKJV",
        "LANDING_DEVOTIONALS",
        "refreshLandingVerse?.addEventListener",
        "@media (forced-colors: active)",
    ):
        assert required in source

    assert "setInterval(" not in source
    assert "requestAnimationFrame(" not in source
    assert "https://fonts." not in source
    assert "new URL('/', window.location.origin).toString()" in source
    assert "navigator.share" in source
    assert "navigator.clipboard?.writeText" in source


def test_guest_tour_is_edge_only_read_only_and_fail_closed() -> None:
    source = _source()
    guest_section = re.search(
        r'<section id="guestPortalState".*?</section>',
        source,
        flags=re.DOTALL,
    )
    assert guest_section is not None
    guest_html = guest_section.group(0)

    for forbidden in (
        "<form",
        "<input",
        "<textarea",
        "<select",
        "contenteditable",
        "ROSTER_ORIGIN",
        "ROSTER_SHARES",
    ):
        assert forbidden not in guest_html

    assert "訪客瀏覽模式" in guest_html
    assert "目前權限：只供查看" in guest_html
    assert "The guest tour contains no roster data." in guest_html
    assert "if (!['GET', 'HEAD'].includes(request.method))" in source
    assert "window.location.pathname === '/guest'" in source

    guest_boot = re.search(
        r"if \(window\.location\.pathname === '/guest'\) \{(?P<body>.*?)\n\s*\}",
        source,
        flags=re.DOTALL,
    )
    assert guest_boot is not None
    assert "showOnly(guestPortalState)" in guest_boot.group("body")
    assert "return;" in guest_boot.group("body")
    assert "fetch(" not in guest_boot.group("body")


def test_viewer_rejects_oversized_or_long_lived_share_payloads() -> None:
    source = _source()

    assert "MAX_ADMIN_BODY_BYTES = 196_608" in source
    assert "MAX_VIEW_BODY_BYTES = 2_048" in source
    assert "MAX_SHARE_LIFETIME_MS = 31 * 24 * 60 * 60 * 1_000" in source
    assert "MAX_SHARE_LIFETIME_MS" in source
    assert "ciphertext.byteLength > 131_072" in source
    assert "payload.shareId" in source
    assert "Object.keys(payload).some(key => key !== 'shareId')" in source


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
        "path === '/auth/login'",
        "path === '/view'",
        "path === '/api/view'",
        "path === '/api/admin/shares'",
    ):
        assert required in source

    assert "管理員登入" in source
    assert "Administrator sign in" in source
    assert "Access-Control-Allow-Origin" not in source


def test_authenticated_proxy_is_same_origin_sanitized_and_websocket_transparent() -> None:
    source = _source()

    assert "const supportedMethods = ['GET', 'HEAD', 'OPTIONS', 'POST', 'PUT', 'PATCH', 'DELETE']" in source
    assert "const isUnsafeMethod = !['GET', 'HEAD', 'OPTIONS'].includes(method)" in source
    assert "fetchSite === 'same-origin'" in source
    assert "new URL(suppliedOrigin).origin !== expectedOrigin" in source
    assert "name.toLowerCase().startsWith('cf-access-')" in source
    assert "ACCESS_COOKIE_NAME.toLowerCase()" in source
    assert "headers.set('X-Sing-Yin-Access-Email', verifiedEmail)" in source
    assert "new URL('http://127.0.0.1:8080')" in source
    assert "env.ROSTER_ORIGIN.fetch(originRequest)" in source
    assert "if (routed && routed.originResponse) return routed.originResponse" in source
    assert "console.log" not in source
    assert "console.error" not in source


def test_public_request_and_jwks_bodies_are_streamed_with_hard_limits() -> None:
    source = _source()

    assert "async function readBoundedUtf8(input, maximumBytes)" in source
    assert "input.body.getReader()" in source
    assert "await reader.cancel()" in source
    assert "readBoundedUtf8(certificateResponse, ACCESS_JWKS_MAX_BYTES)" in source
    assert "readBoundedUtf8(request, maximumBytes)" in source


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
