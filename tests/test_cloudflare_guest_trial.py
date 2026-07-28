from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "roster_viewer" / "worker.js"
RETIRED_TRIAL = ROOT / "cloudflare" / "roster_viewer" / "guest_trial.js"
COMPATIBILITY_VERIFIER = ROOT / "scripts" / "verify_guest_trial.py"
PUBLIC_VIEWER_VERIFIER = ROOT / "scripts" / "verify_public_roster_viewer.py"


def _worker_source() -> str:
    return WORKER.read_text(encoding="utf-8")


def test_legacy_trial_entrypoints_redirect_into_the_unified_guest_bootstrap() -> None:
    worker = _worker_source()

    assert not RETIRED_TRIAL.exists()
    assert "from './guest_trial.js'" not in worker
    for path in ("/guest", "/try"):
        assert f"path === '{path}'" in worker
    assert "return redirectResponse('/?guest=1', request.url)" in worker
    assert 'data-guest-bootstrap="false"' in worker
    assert 'data-guest-bootstrap="true"' in worker
    assert "fetch('/auth/guest/start'" in worker
    assert "window.location.replace('/')" in worker

    for path in ("/guest.js", "/trial.css", "/trial.js"):
        assert f"path === '{path}'" not in worker
    assert "trialAssetResponse" not in worker
    assert "if (path.startsWith('/try/'))" in worker
    assert "if (path.startsWith('/guest/'))" in worker
    assert "'unified-guest-gateway'" in worker
    assert "'signed-origin-principal'" in worker


def test_worker_contains_no_second_static_guest_product() -> None:
    worker = _worker_source()

    for obsolete in (
        "guestPortalState",
        'class="guest-portal"',
        ".guest-portal",
        ".guest-mode-band",
        ".guest-tour-card",
        "PUBLIC TOUR · READ ONLY",
    ):
        assert obsolete not in worker

    assert "createGuestSessionToken(env, {" in worker
    assert "themeHandoff: themeHandoffFromRequest(request)" in worker
    assert "validateGuestSessionToken(guestToken, env)" in worker
    assert "proxyToRosterOrigin(request, env, principal)" in worker


def test_old_guest_verifier_delegates_to_the_unified_product_verifier() -> None:
    source = COMPATIBILITY_VERIFIER.read_text(encoding="utf-8")

    assert "verify_unified_guest_ui import main" in source
    for obsolete in (
        "sing-yin-guest-trial-v1",
        "#generateRoster",
        "#downloadPdf",
        "connect-src 'none'",
    ):
        assert obsolete not in source


def test_public_viewer_verifier_does_not_reintroduce_the_retired_static_tour() -> None:
    source = PUBLIC_VIEWER_VERIFIER.read_text(encoding="utf-8")

    assert "scripts/verify_unified_guest_ui.py" in source
    for obsolete in (
        "_assert_guest_tour",
        "edge-only /guest route",
        "guestThemeToggle",
        'allowed_paths = {"/guest", "/guest.js", "/trial.css"',
    ):
        assert obsolete not in source
