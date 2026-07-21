from __future__ import annotations

import hashlib
from pathlib import Path

from nicegui_app.ui.i18n import MESSAGES
from nicegui_app.ui.page_catalog import PAGE_DEFINITIONS


PROJECT_ROOT = Path(__file__).resolve().parents[1]

from tests.ui_source import combined_i18n_source, combined_page_source


def test_readme_explains_safe_start_and_links_to_operator_documents() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "START_SING_YIN_ROSTER.cmd" in readme
    assert "127.0.0.1:8080" in readme
    assert "docs/OPERATOR_GUIDE.md" in readme
    assert "docs/RELEASE_HANDOVER.md" in readme
    assert "docs/DEPLOYMENT_DECISION.md" in readme
    assert "docs/WINDOWS_DEDICATED_HOST_SETUP.md" in readme
    assert "docs/WINDOWS_SSH_MAINTENANCE.md" in readme
    assert "docs/CLOUDFLARE_REMOTE_ACCESS_SETUP.md" in readme
    assert "START_PRACTICE_MODE.cmd" in readme
    assert "RESET_PRACTICE_MODE.cmd" in readme
    assert "nicegui-self-hosted" in readme
    assert "streamlit-cloud" in readme


def test_windows_ssh_maintenance_guide_preserves_private_key_and_network_boundaries() -> None:
    guide = (PROJECT_ROOT / "docs" / "WINDOWS_SSH_MAINTENANCE.md").read_text(
        encoding="utf-8"
    )
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(
        encoding="utf-8"
    )

    assert "ssh sing-yin-roster-host" in guide
    assert "verify_windows_ssh.ps1" in guide
    assert "127.0.0.1:22" in guide and "[::1]:22" in guide
    assert "密碼及互動式登入均停用" in guide
    assert "never change `ListenAddress` to `0.0.0.0`" in guide
    assert "不可把 SSH 私鑰" in guide
    assert "SingYinRosterSvc" in guide and "不能透過 SSH 登入" in guide
    assert "Cloudflare private route" in guide
    assert "docs/WINDOWS_SSH_MAINTENANCE.md" in readme_en
    assert "WINDOWS_SSH_MAINTENANCE.md" in handover
    for relative_path in (
        "docs/OPERATOR_GUIDE.md",
        "docs/QUICKSTART.md",
        "docs/RELEASE_HANDOVER.md",
        "docs/DEPLOYMENT_DECISION.md",
        "docs/ACCEPTANCE_EVIDENCE.md",
        "docs/NICEGUI_ARCHITECTURE.md",
        "Professional_Design_System.md",
        "PROJECT_STATUS.md",
        "README-EN.md",
        "LICENSE",
        "NOTICE.md",
        "CONTRIBUTING.md",
        "docs/BRANCH_STRATEGY.md",
        "docs/UPDATE_WORKFLOW.md",
        "archive/README.md",
    ):
        assert (PROJECT_ROOT / relative_path).is_file()


def test_github_handover_documents_current_runtime_and_public_archive_boundary() -> None:
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
    branch_strategy = (PROJECT_ROOT / "docs" / "BRANCH_STRATEGY.md").read_text(encoding="utf-8")
    archive = (PROJECT_ROOT / "archive" / "README.md").read_text(encoding="utf-8")
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    notice_text = (PROJECT_ROOT / "NOTICE.md").read_text(encoding="utf-8")

    assert "NiceGUI + SQLite" in readme_en
    assert "streamlit-cloud" in branch_strategy and "nicegui-self-hosted" in branch_strategy
    assert "fictional" in archive.lower() and "no roster" in archive.lower()
    assert "MIT License" in license_text
    assert "does not modify" in notice_text and "restrict the MIT License" in notice_text
    assert "I am **LI Chuangjie Jacky (李創杰)**" in notice_text
    assert "only two co-creators" in notice_text
    assert "我是 **李創杰**" in notice_text
    assert "只由我與 Codex 兩位共創者" in notice_text
    assert "李創杰與 Codex 兩位共創者" in (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")


def test_v12_guest_documents_match_the_signed_browser_bridge_and_release_truth() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
    status = (PROJECT_ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    security = (PROJECT_ROOT / "docs" / "UNIFIED_GUEST_SECURITY_MODEL.md").read_text(
        encoding="utf-8"
    )
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(
        encoding="utf-8"
    )

    for document in (readme, readme_en, status, architecture, security, handover):
        assert "sessionStorage" in document
        assert "workspace" in document

    assert "tests/test_guest_snapshot_bridge.py" in security
    assert "live-connection nonce" in readme_en
    assert "per-connection nonce" in architecture
    assert "連線 nonce" in handover
    assert "SING_YIN_UNIFIED_GUEST" in status
    assert "13／13" in status
    assert "v1.1 rollback" in readme_en
    assert "13／13" in readme
    assert "NiceGUI has no guest" not in design
    assert "NiceGUI never presents an anonymous guest role" not in design
    assert "still a v1.2 release gate" not in architecture
    assert "瀏覽器 snapshot 橋接" in security
    assert "尚未完成的瀏覽器 snapshot 橋接" not in security


def test_release_truth_docs_keep_live_rc15_separate_from_history() -> None:
    status = (PROJECT_ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    security = (PROJECT_ROOT / "docs" / "UNIFIED_GUEST_SECURITY_MODEL.md").read_text(
        encoding="utf-8"
    )
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(
        encoding="utf-8"
    )
    operator = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")

    for document in (status, architecture, security, handover):
        assert "v1.2.0-rc.15" in document
        assert "17a1cf9" in document
        assert "f8ea712c-6b64-4d32-8f62-3405bc313e24" in document

    assert "Service Weave v1.2 rc15 controlled rollout" in status
    assert "v1.2 rc15 is the current controlled Windows origin" in status
    assert "Historical Service Weave v1.2 rc11 rollout" in status
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## 程式審查、邊界與擴展預期" in readme
    assert "SING_YIN_PORT" in readme
    assert "一百倍" in readme
    assert "cancelWelcomeFade is not defined" in status
    assert "目前發布（v1.2 rc15）" in (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    assert "remains disabled by default" not in status
    assert "now run the matching rc7 release" not in status
    assert "Windows origin remains healthy／ready on rc4" not in security
    assert "This document does not claim that v1.2 is deployed" not in security

    next_steps = status.split("## Next Steps", 1)[1].split(
        "## Key Decisions and Architecture", 1
    )[0]
    assert "new immutable candidate" in next_steps
    assert "v1.2.0-rc.5" not in next_steps

    release_sequence = handover.split("### 後續受控發布次序", 1)[1].split(
        "## 正式驗收清單", 1
    )[0]
    assert "下一個獲批准的 annotated tag" in release_sequence
    assert "本次為 `v1.2.0-rc.7`" not in release_sequence
    assert "v1.1.0-rc.16" in handover

    assert "訪客體驗 / Try as guest" in operator
    assert "互動示範工作區" in operator
    assert "只有 `/view#…`" in operator


def test_operator_deployment_docs_use_live_rc15_and_candidate_bound_next_tag() -> None:
    quickstart = (PROJECT_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    windows = (PROJECT_ROOT / "docs" / "WINDOWS_DEDICATED_HOST_SETUP.md").read_text(
        encoding="utf-8"
    )
    cloudflare = (PROJECT_ROOT / "docs" / "CLOUDFLARE_REMOTE_ACCESS_SETUP.md").read_text(
        encoding="utf-8"
    )
    viewer = (PROJECT_ROOT / "docs" / "PUBLIC_ROSTER_VIEWER.md").read_text(
        encoding="utf-8"
    )
    decision = (PROJECT_ROOT / "docs" / "DEPLOYMENT_DECISION.md").read_text(
        encoding="utf-8"
    )

    for document in (quickstart, windows, cloudflare, viewer, decision):
        assert "v1.2.0-rc.15" in document
        assert "17a1cf9" in document
        assert "f8ea712c-6b64-4d32-8f62-3405bc313e24" in document

    assert "schema-compatible rc4" not in quickstart
    assert "pre-v1.2 baseline" not in quickstart
    assert "v1.2 rc5 候選狀態" not in viewer
    assert "v1.2 rc7 發布狀態" not in cloudflare
    assert "v1.1 已部署基線與 v1.2 候選" not in decision
    assert '$ReleaseRef = "<next-approved-annotated-tag>"' in windows
    assert '$ReleaseRef = "v1.1.0-rc.16"' not in windows
    assert "<next-approved-annotated-tag>" in decision


def test_author_facing_documents_use_li_chuangjie_first_person_voice() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
    operator_guide = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    music_brief = (PROJECT_ROOT / "docs" / "MUSIC_PLAYLIST_CANDIDATES.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "我是李創杰" in readme
    assert "I am LI Chuangjie Jacky" in readme_en
    assert "我把這份手冊留給下一任首席導學風紀" in operator_guide
    assert "我是李創杰" in handover and "我把這份手冊與系統一起留給下一任" in handover
    assert "這是我（李創杰）" in music_brief
    assert "Author voice and handover narrative" in design_system
    assert "`我與 Codex` / `Codex and I`" in design_system


def test_double_click_launcher_handles_existing_and_conflicting_ports() -> None:
    cmd = (PROJECT_ROOT / "START_SING_YIN_ROSTER.cmd").read_text(encoding="utf-8")
    launcher = (PROJECT_ROOT / "scripts" / "start_sing_yin_roster.ps1").read_text(encoding="utf-8")
    quickstart = (PROJECT_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")

    assert "start_sing_yin_roster.ps1" in cmd
    assert "Find-ExistingSingYinPort" in launcher
    assert "Find-FreePort" in launcher
    assert "System.Threading.Mutex" in launcher
    assert "Another launcher is starting" in launcher
    assert '$env:SING_YIN_OPEN_BROWSER = "false"' in launcher
    assert "The system is ready" in launcher
    assert "WinError 10048" in quickstart
    expected_remote_access_line = (
        "2. 在任何獲准裝置開啟唯一正式網站："
        "<https://sing-yin-roster-viewer.singyin-study-prefect.workers.dev/>。"
    )
    assert any(line == expected_remote_access_line for line in quickstart.splitlines())
    assert "本機維護" in quickstart
    assert 'applicationMode -eq $ExpectedApplicationMode' in launcher
    assert 'catch [System.Net.WebException]' in launcher
    assert '$readyResponse.StatusCode -lt 300' in launcher
    assert r'.venv\Scripts\python.exe' in launcher


def test_windows_dedicated_host_guide_is_complete_and_local_only() -> None:
    guide = (PROJECT_ROOT / "docs" / "WINDOWS_DEDICATED_HOST_SETUP.md").read_text(encoding="utf-8")

    for required_text in (
        "Windows 11",
        r"C:\SingYinRoster",
        "py install 3.12",
        "py -V:3.12 -m venv .venv",
        "SING_YIN_DEPLOYMENT_MODE=local",
        "SING_YIN_HOST=127.0.0.1",
        "Sing Yin Roster Host",
        "Invoke-RestMethod http://127.0.0.1:8080/healthz",
        "git fetch --prune --tags origin",
        "git switch --detach $ReleaseRef",
        "建立交接備份包",
    ):
        assert required_text in guide

    assert "不要自行把主機改成 `0.0.0.0`" in guide
    assert "Cloudflare 遠端存取完整設定手冊" in guide


def test_windows_and_cloudflare_automation_is_fail_closed_and_documented() -> None:
    prepare = (PROJECT_ROOT / "scripts" / "prepare_windows_host.ps1").read_text(encoding="utf-8")
    assert '--require-hashes -r (Join-Path $ProjectRoot "requirements.lock")' in prepare
    assert '--require-hashes -r (Join-Path $ProjectRoot "requirements-dev.lock")' in prepare
    task = (PROJECT_ROOT / "scripts" / "register_windows_startup_task.ps1").read_text(encoding="utf-8")
    activate = (PROJECT_ROOT / "scripts" / "activate_cloudflare_remote_access.ps1").read_text(encoding="utf-8")
    verify = (PROJECT_ROOT / "scripts" / "verify_cloudflare_access.ps1").read_text(encoding="utf-8")
    guide = (PROJECT_ROOT / "docs" / "CLOUDFLARE_REMOTE_ACCESS_SETUP.md").read_text(encoding="utf-8")

    assert "Python 3.12" in prepare and "-m venv" in prepare and "check_deployment_readiness.py" in prepare
    assert "Get-Command py.exe" in prepare and "Get-Command python.exe" in prepare
    assert "-m playwright install chromium" in prepare
    assert "New-ScheduledTaskAction" in task
    assert "Get-SingYinConfiguredEndpoint" in task
    assert "$($endpoint.Host):$($endpoint.Port)/healthz" in task
    for required_text in (
        'SING_YIN_HOST" "127.0.0.1',
        "ACCESS READY",
        "Read-Host",
        "-AsSecureString",
        "verify_cloudflare_access.ps1",
        "Stop-Service cloudflared",
        "before-remote",
    ):
        assert required_text in activate
    assert "$request.AllowAutoRedirect = $false" in verify
    assert '"https://$PublicHostname/auth/login"' in verify
    assert "cloudflareaccess\\.com" in verify
    assert "Invoke-SingYinAccessLoginPageRequest" in verify
    assert "totp-form" in verify and "verify-code" in verify
    assert "dash\\.cloudflare\\.com/oauth2|Unknown app" in verify
    common = (PROJECT_ROOT / "scripts" / "windows_host_common.ps1").read_text(encoding="utf-8")
    assert "ProgramFiles(x86)" in common
    assert "不要在家中路由器開放 3389、8080" in guide
    assert "未登入／獲准／未獲准" in guide


def test_practice_mode_is_a_complete_handover_and_architecture_contract() -> None:
    quickstart = (PROJECT_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "START_PRACTICE_MODE.cmd" in quickstart and "RESET_PRACTICE_MODE.cmd" in quickstart
    assert "data/practice/" in handover and "PRACTICE_" in handover
    assert "ApplicationModeSettings" in architecture and "verify_practice_mode.py" in architecture
    assert "Practice-mode identity" in design and "colour-only" in design


def test_project_environment_is_loaded_before_path_constants_are_resolved() -> None:
    config = (PROJECT_ROOT / "nicegui_app" / "config.py").read_text(encoding="utf-8")

    assert config.index('load_dotenv(PROJECT_ROOT / ".env")') < config.index("DEFAULT_DATABASE_PATH =")


def test_release_verification_dependencies_and_safe_orchestrator_are_shipped() -> None:
    development_requirements = (PROJECT_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    verifier = (PROJECT_ROOT / "scripts" / "verify_release_candidate.py").read_text(encoding="utf-8")

    for dependency in ("pytest", "playwright", "pypdf", "httpx2"):
        assert dependency in development_requirements
    for variable in (
        "SING_YIN_E2E_ISOLATED",
        "SING_YIN_DATABASE_PATH",
        "SING_YIN_BACKUP_DIR",
        "SING_YIN_LOG_DIR",
    ):
        assert variable in verifier
    assert "CANONICAL_DATABASE" in verifier and "CANONICAL_BACKUPS" in verifier
    assert "verify_nicegui_ui.py" in verifier
    assert "verify_runtime_performance.py" in verifier
    assert "verify_nicegui_write_pipeline.py" in verifier
    assert "verify_nicegui_partial_backup.py" in verifier
    assert "check_deployment_readiness.py" in verifier
    update_workflow = (PROJECT_ROOT / "docs" / "UPDATE_WORKFLOW.md").read_text(encoding="utf-8")
    assert "python -X utf8 scripts\\verify_update.py" in update_workflow
    assert "未能識別的新路徑或 Git base" in update_workflow


def test_acceptance_matrix_separates_machine_evidence_from_human_approval() -> None:
    matrix = (PROJECT_ROOT / "docs" / "ACCEPTANCE_EVIDENCE.md").read_text(encoding="utf-8")

    for identifier in tuple(f"H-{index:02d}" for index in range(1, 14)) + tuple(
        f"A-{index:02d}" for index in range(1, 5)
    ):
        assert identifier in matrix
    assert "正式驗收未完成" in matrix
    assert "humanAcceptanceRequired: true" in matrix
    assert "不可上載到公開服務" in matrix


def test_deployment_guide_preserves_local_first_and_access_gates() -> None:
    guide = (PROJECT_ROOT / "docs" / "DEPLOYMENT_DECISION.md").read_text(encoding="utf-8")
    assert "私有 Cloudflare Tunnel + WARP" in guide
    assert "WARP device-enrollment policy" in guide
    assert "Quick Tunnel" in guide
    assert "應用內權限" in guide
    assert "127.0.0.1:8080" in guide
    assert "主機連接器健康；待真人遠端裝置驗收" in guide
    assert "Access app destination 只可是 `/auth/login`" in guide
    assert "Guest start、status 及 logout 必須由 Worker 公開接收" in guide
    assert "沒有管理員前綴或第二網站" in guide
    assert "CLOUDFLARE_REMOTE_ACCESS_SETUP.md" in guide


def test_architecture_documents_the_isolated_full_write_pipeline() -> None:
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "verify_nicegui_write_pipeline.py" in architecture
    assert "SING_YIN_E2E_ISOLATED=1" in architecture
    assert "second isolated database" in architecture


def test_handover_documents_safe_support_log_investigation() -> None:
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    support_script = PROJECT_ROOT / "scripts" / "inspect_support_log.py"

    assert support_script.is_file()
    assert "inspect_support_log.py" in handover
    assert "X-Request-ID" in handover
    assert "SING_YIN_LOG_MAX_BYTES" in handover


def test_operator_guidance_documents_architecture_and_co_creation_boundaries() -> None:
    guide = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "平台與團隊" in guide
    assert "系統架構與可信設計" in guide
    assert "START_SING_YIN_ROSTER.cmd" in guide
    assert "sidebar-stewardship-light-v1.webp" in design_system
    assert "architecture-stewardship-dark-v1.webp" in design_system
    assert "不可放在資料表、表單、警告或 PDF" in design_system
    assert "sing-yin-crest-favicon.png" in design_system
    assert "sing-yin-crest-navigation.png" in design_system
    assert "sing-yin-crest-display-print.png" in design_system
    assert "Partial success" in design_system


def test_platform_showcase_exposes_enterprise_style_operating_model_without_fake_staff() -> None:
    pages = combined_page_source()
    messages = combined_i18n_source()
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")

    assert '@ui.page("/platform")' in pages
    assert "def _render_co_creation" in shared
    assert 'data-testid=platform-live-summary' in pages
    for test_id in ("team-operating-model", "capability-map", "solutions-portfolio", "platform-principles"):
        assert f"data-testid={test_id}" in pages
    architecture_page = pages.split('@ui.page("/system-architecture")', 1)[1]
    assert "data-testid=team-operating-model" not in architecture_page
    assert "Study Prefect Team" in messages
    assert "Service Governance Lead" in messages
    assert "Duty Coordination Lead" in messages
    assert "Room Service Steward" in messages
    assert "four capabilities" in messages
    assert "not additional departments or staff" in MESSAGES["capability_map_copy"]["en"]


def test_co_creation_profile_uses_local_identity_media_and_canonical_instagram_link() -> None:
    shared = (PROJECT_ROOT / "nicegui_app" / "ui" / "page_shared.py").read_text(encoding="utf-8")
    contact = (PROJECT_ROOT / "nicegui_app" / "contact.py").read_text(encoding="utf-8")
    avatar = PROJECT_ROOT / "nicegui_app" / "assets" / "brand" / "li-chuangjie-avatar.jpg"
    banner = PROJECT_ROOT / "nicegui_app" / "assets" / "brand" / "li-chuangjie-banner.png"

    assert avatar.is_file()
    assert banner.is_file()
    assert hashlib.sha256(avatar.read_bytes()).hexdigest() == (
        "9ab4506d8254d157579b3927acd57e343a537913528a9223113689ed4703413a"
    )
    assert hashlib.sha256(banner.read_bytes()).hexdigest() == (
        "35fa985443809865909ac0b44c5cd592dc9e4252618a6f364cb3dcd18b609e13"
    )
    assert "data-testid=co-creation-profile" in shared
    assert "/assets/brand/li-chuangjie-avatar.jpg" in shared
    assert "/assets/brand/li-chuangjie-banner.png" in shared
    assert "loading=lazy decoding=async" in shared
    assert 'INSTAGRAM_PROFILE_URL = "https://www.instagram.com/5662jacky/"' in contact
    assert "with ui.link(target=INSTAGRAM_PROFILE_URL)" in shared
    assert 'target=_blank rel="noopener noreferrer"' in shared
    assert "李創杰 · LI Chuangjie, Jacky" in MESSAGES["co_creation_creator_name"]["zh-HK"]


def test_engineering_showcase_turns_documented_quality_into_verifiable_ui_evidence() -> None:
    pages = combined_page_source()
    messages = combined_i18n_source()

    assert '@ui.page("/engineering")' in pages
    engineering_definition = next(page for page in PAGE_DEFINITIONS if page.route == "/engineering")
    assert (engineering_definition.title_key, engineering_definition.icon) == (
        "engineering",
        "build_circle",
    )
    for test_id in (
        "engineering-facts",
        "engineering-blueprint",
        "engineering-gates",
        "engineering-pillars",
        "engineering-evolution",
    ):
        assert f"data-testid={test_id}" in pages
    engineering_page = pages.split('@ui.page("/engineering")', 1)[1].split('@ui.page("/system-architecture")', 1)[0]
    assert "load_release_evidence()" in engineering_page
    assert "get_workflow()" not in engineering_page
    assert "evidence.passed_checks" in engineering_page and "evidence.total_checks" in engineering_page
    assert "engineering_fact_full_suite" in engineering_page
    assert "student" not in engineering_page.lower()
    assert "The full gate chain" in messages
    assert "engineering_gate_security" in messages
    assert "engineering_gate_runtime" in messages
    assert "engineering_gate_guest" in messages


def test_feedback_channel_is_consistent_bilingual_and_scopes_diagnostic_attachments() -> None:
    contact = (PROJECT_ROOT / "nicegui_app" / "contact.py").read_text(encoding="utf-8")
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    messages = combined_i18n_source()
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")

    assert 'FEEDBACK_EMAIL = "s10777@syss.edu.hk"' in contact
    assert 'GITHUB_REPOSITORY_URL = "https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System"' in contact
    assert 'INSTAGRAM_PROFILE_URL = "https://www.instagram.com/5662jacky/"' in contact
    assert "mailto:" in contact and "urlencode" in contact
    assert "data-testid=sidebar-feedback" in shell
    assert "data-testid=feedback-channel" in pages
    assert "feedback_channel_safe_note" in messages
    assert "github_repository_action" in messages
    assert "診斷確有需要時可附上相關資料" in messages
    assert "Attach relevant evidence when it is genuinely needed" in messages
    assert "核對收件人" in messages
    assert "limiting it to what the investigation requires" in messages
    assert "s10777@syss.edu.hk" in readme and "s10777@syss.edu.hk" in readme_en


def test_partial_backup_recovery_is_documented_for_operator_and_maintainer() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "資料已儲存，但備份未完成" in readme
    assert "不可重複" in handover
    assert "CommittedWriteBackupError" in architecture
    assert "verify_nicegui_partial_backup.py" in architecture


def test_nonblocking_prefect_and_leave_writes_are_part_of_the_handover_contract() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "進度視窗完成前不要重複點擊" in readme
    assert "停用不是刪除" in handover
    assert "pre-generation leave declaration/cancellation" in architecture
    assert "prefect creation/update/archive" in architecture
    assert "`_safe_read_action` is reserved" in architecture
    assert "historical rosters, fairness entries, and audit evidence remain" in design_system


def test_roster_preflight_and_value_snapshot_contract_is_documented() -> None:
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "週開始日期不是星期一" in handover
    assert "RosterWorkflow.validate_week_start" in architecture
    assert "snapshots every visible identifier and reason" in architecture
    assert "before the first asynchronous yield" in design_system


def test_verified_backup_empty_state_and_activation_are_handover_contracts() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "交接備份包" in readme and "保持停用" in readme
    assert "只有校驗成功並重新載入後" in handover
    assert "keeps package/restore controls disabled" in architecture
    assert "must not open a dead-end confirmation" in design_system


def test_invalid_backup_categories_are_safe_operator_and_handover_guidance() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    guide = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "安全分類及數量" in readme
    assert "不要自行改名、補寫 manifest" in guide
    assert "backup_inventory" in architecture
    assert "never renders the raw `error`" in architecture
    assert "Trust warnings aggregate and classify" in design_system


def test_backup_verification_performance_contract_keeps_live_trust_checks() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (PROJECT_ROOT / "docs" / "NICEGUI_ARCHITECTURE.md").read_text(encoding="utf-8")
    design_system = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "最多四路唯讀方式驗證" in readme
    assert "parallel but never cached" in architecture
    assert "at most four" in architecture
    assert "missing_file" in architecture
    assert "bounded read-only parallelism" in design_system


def test_readme_showcases_current_architecture_faq_and_co_creation_without_legacy_runtime() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "## 系統架構與可信設計" in readme
    assert "```mermaid" in readme
    assert "roster_policy" in readme
    assert "roster_core" in readme
    assert "roster_workflow" in readme
    assert "stateDiagram-v2" in readme
    assert "## FAQ／常見問題" in readme
    assert "## 共創結語 / Co-creation closing note" in readme
    assert "Codex 的結語" in readme
    assert "Streamlit Cloud" in readme  # historical branch label only
    assert "streamlit run" not in readme
    assert "`app.py`" not in readme
    assert "PDF 內嵌備份" not in readme


def test_pdf_font_setup_documents_the_bundled_three_weight_contract() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    host_setup = (PROJECT_ROOT / "docs" / "WINDOWS_DEDICATED_HOST_SETUP.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")

    for variable in (
        "SING_YIN_PDF_FONT_REGULAR",
        "SING_YIN_PDF_FONT_MEDIUM",
        "SING_YIN_PDF_FONT_SEMIBOLD",
    ):
        assert variable in env_example
        assert variable in handover
    assert "NotoSansHK-*.ttf" in host_setup
    assert "安裝 Noto Sans TC，或設定 `SING_YIN_PDF_FONT`" not in host_setup


def test_reference_pages_form_two_clear_reading_lanes_without_duplicate_docs_route() -> None:
    pages = combined_page_source()
    navigation = (PROJECT_ROOT / "nicegui_app" / "ui" / "reference_navigation.py").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert '@ui.page("/docs")' not in pages
    assert "render_page_toc" in navigation and "render_reference_pager" in navigation
    assert 'data-testid=guide-troubleshooting' in pages
    assert pages.count('data-testid=reference-index') == 1
    assert 'previous=("/getting-started", "getting_started")' in pages
    assert 'next_=("/handover", "handover")' in pages
    assert 'previous=("/guide", "operator_guide")' in pages
    assert 'next_=("/system-architecture", "system_architecture")' in pages
    assert 'previous=("/platform", "platform")' in pages
    assert 'next_=("/engineering", "engineering")' in pages
    reference_routes = [
        page.route
        for page in PAGE_DEFINITIONS
        if page.navigation_group == "nav_reference"
    ]
    assert reference_routes.index("/platform") < reference_routes.index(
        "/system-architecture"
    ) < reference_routes.index("/engineering")
    assert '("verified_user", "start_reference_trust_title", "start_reference_trust_body", "platform", "/platform")' in pages
    for anchor in (
        "platform-snapshot-section",
        "platform-team-section",
        "platform-capabilities-section",
        "platform-solutions-section",
        "platform-principles-section",
        "platform-resources-section",
        "handover-steps-section",
        "handover-rollover-section",
        "handover-readiness-section",
        "handover-acceptance-section",
        "start-first-steps",
        "start-reference-map",
    ):
        assert anchor in pages
    assert 'role=table aria-label="{t("guide_troubleshooting_title")}"' in pages
    assert 'id=start-first-steps aria-label="{t("start_toc_first_steps")}"' in pages
    assert 'id=handover-steps-section aria-label="{t("handover_steps_title")}"' in pages
    assert "what you see／what it means／safe next action" in design
    assert "DeepSeek API Docs" in design


def test_operator_troubleshooting_reference_is_complete_and_bilingual() -> None:
    for issue in ("vacancy", "stale", "publish", "backup", "restore", "session", "support"):
        for column in ("seen", "meaning", "next"):
            key = f"guide_issue_{issue}_{column}"
            assert key in MESSAGES
            assert MESSAGES[key]["zh-HK"].strip()
            assert MESSAGES[key]["en"].strip()


def test_uiverse_attribution_is_kept_with_the_component_governance() -> None:
    notice = (PROJECT_ROOT / "NOTICE.md").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    assert "Uiverse" in notice and "MIT License" in notice
    assert "Sing Yin tactile component grammar" in design
