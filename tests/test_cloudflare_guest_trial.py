from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "cloudflare" / "roster_viewer" / "worker.js"
TRIAL = ROOT / "cloudflare" / "roster_viewer" / "guest_trial.js"


def _worker_source() -> str:
    return WORKER.read_text(encoding="utf-8")


def _trial_source() -> str:
    return TRIAL.read_text(encoding="utf-8")


def test_trial_routes_are_bounded_static_assets_and_fail_closed() -> None:
    worker = _worker_source()

    assert "from './guest_trial.js'" in worker
    for path in ("/guest", "/guest.js", "/try", "/trial.css", "/trial.js"):
        assert f"path === '{path}'" in worker
    assert worker.count("trialAssetResponse('Method not allowed'") >= 6
    assert "trialAssetResponse" in worker
    assert "if (!output.headers.has(name))" in worker
    assert "if (path.startsWith('/try/'))" in worker
    assert "if (path.startsWith('/guest/'))" in worker
    assert "'isolated-client-trial'" in worker


def test_trial_content_security_policy_forbids_all_runtime_connections() -> None:
    source = _trial_source()

    for directive in (
        '"default-src \'none\'"',
        '"connect-src \'none\'"',
        '"font-src \'none\'"',
        '"worker-src \'none\'"',
        '"form-action \'none\'"',
        '"frame-ancestors \'none\'"',
    ):
        assert directive in source
    assert "TRIAL_SECURITY_HEADERS" in source
    assert "'Cache-Control': 'no-store, max-age=0'" in source


def test_trial_uses_expiring_session_storage_and_no_network_or_durable_storage() -> None:
    source = _trial_source()

    for required in (
        "const SESSION_TTL_MS = 30 * 60 * 1000",
        "sessionStorage.getItem(STORAGE_KEY)",
        "sessionStorage.setItem(STORAGE_KEY",
        "sessionStorage.removeItem(STORAGE_KEY)",
        "parsed.expiresAt > now",
        "freshState(Date.now())",
        "function ensureUnexpired()",
        "if (!ensureUnexpired()) return",
        "scheduleExpiry()",
        "setInterval(() => { if (ensureUnexpired()) renderExpiry(); }, 60_000)",
        "parsed.absences.every(validAbsenceShape)",
        "cell.name === person.name",
    ):
        assert required in source

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "localStorage",
        "indexedDB",
    ):
        assert forbidden not in source


def test_trial_directory_policy_and_bilingual_pdf_contract() -> None:
    source = _trial_source()

    assert source.count("role: 'assistant'") >= 6
    assert source.count("role: 'prefect'") >= 12
    assert "person.role === post.role" in source
    assert "!today.has(person.id)" in source
    assert "!previousDay.has(person.id)" in source
    assert "!absenceSet.has(absenceKey(person.id, dayIndex))" in source
    assert "open: [0, 2, 3]" in source
    assert "15:40–17:00" in source
    assert "助理首席導學風紀當值" in source
    assert "All names and records are fictional" in source
    assert "全部姓名及資料均為虛構" in source
    assert "cell.name" in source
    assert "canvas.width = 2339" in source
    assert "canvas.height = 1654" in source
    assert "/MediaBox [0 0 841.89 595.28]" in source
    assert "new Blob([pdf], { type: 'application/pdf' })" in source
    assert "SYSS_Guest_Trial_Roster_" in source


def test_guest_platform_separates_overview_from_focused_trial() -> None:
    source = _trial_source()

    assert "GUEST_PLATFORM_HTML" in source
    assert "GUEST_PLATFORM_JS" in source
    assert "TRIAL_HTML" in source
    assert 'href="/try"' in source
    assert "PUBLIC PRODUCT TOUR" in source
    assert "CAPABILITIES" in source
    assert "OPERATING MODEL" in source
    assert "SERVICE SOLUTIONS" in source
    assert "PLATFORM &amp; RESOURCES" in source
    assert "首席導學風紀" in source
    assert "Assistant Head Study Prefect" in source
    assert "history_weight" in source
    assert "s10777@syss.edu.hk" in source
    assert "JackyLi10777/Study-Prefect-Duty-Roster-System" in source
    assert "TRUST BOUNDARY" in source
    assert "The guest tour contains no official roster data." in source
    assert "不包含任何正式值班資料" in source
    assert "零伺服器寫入" in source
    assert "prefers-reduced-motion: reduce" in source
    assert "@media (max-width: 680px)" in source
    assert "guestLanguageToggle" in source
    assert "guestThemeToggle" in source
    assert "sing-yin-guest-display-v1" in source
    assert "--button-ink: #0b2422" in source
    assert ".platform-controls { flex-wrap: wrap" in source
    assert 'data-i18n="exit"' in source


def test_guest_platform_resource_tour_remains_read_only_and_bilingual() -> None:
    source = _trial_source()

    for key in (
        "navTeam",
        "navResources",
        "teamTitle",
        "roleHeadTitle",
        "solutionsTitle",
        "resourcesTitle",
        "resourceTeamTitle",
        "resourceQualityTitle",
        "resourceArchitectureTitle",
        "resourceStartTitle",
        "resourceGuideTitle",
        "resourceDevotionalTitle",
        "coCreationTitle",
        "feedbackLink",
        "githubLink",
    ):
        assert source.count(f"{key}:") == 2, f"{key} must have complete Chinese and English copy"
    assert 'id="team"' in source
    assert 'id="resources"' in source
    assert source.count('class="resource-icon"') == 6
    assert ".resource-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }" in source
    assert "RCUV 2010（神版）及 NKJV" in source
    assert "RCUV 2010 (Shen Edition) and NKJV" in source
    assert "fetch(" not in source
    assert "form-action 'none'" in source


def test_generated_preview_replaces_the_empty_state() -> None:
    source = _trial_source()

    assert "elements.empty.hidden = Boolean(roster)" in source
    assert "elements.preview.hidden = !roster" in source
    assert ".roster-empty[hidden], .roster-preview[hidden] { display: none !important; }" in source
