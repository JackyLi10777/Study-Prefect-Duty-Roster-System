from __future__ import annotations

from pathlib import Path

from nicegui_app.ui.i18n import MESSAGES


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
    assert "docs/CLOUDFLARE_REMOTE_ACCESS_SETUP.md" in readme
    assert "START_PRACTICE_MODE.cmd" in readme
    assert "RESET_PRACTICE_MODE.cmd" in readme
    assert "nicegui-self-hosted" in readme
    assert "streamlit-cloud" in readme
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
        "git pull --ff-only origin main",
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
    assert "New-ScheduledTaskAction" in task and "127.0.0.1:8080/healthz" in task
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
    assert "MaximumRedirection 0" in verify
    assert "cloudflareaccess\\.com" in verify
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
    assert "Cloudflare Tunnel + Cloudflare Access" in guide
    assert "Quick Tunnel" in guide
    assert "應用內權限" in guide
    assert "127.0.0.1:8080" in guide
    assert "待帳戶設定及真人驗收後啟用" in guide
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
    assert "capability groups" in messages
    assert "not four additional departments or staff" in MESSAGES["capability_map_copy"]["en"]


def test_engineering_showcase_turns_documented_quality_into_verifiable_ui_evidence() -> None:
    pages = combined_page_source()
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    messages = combined_i18n_source()

    assert '@ui.page("/engineering")' in pages
    assert '("/engineering", "engineering", "precision_manufacturing")' in shell
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


def test_feedback_channel_is_consistent_bilingual_and_does_not_invite_data_attachments() -> None:
    contact = (PROJECT_ROOT / "nicegui_app" / "contact.py").read_text(encoding="utf-8")
    shell = (PROJECT_ROOT / "nicegui_app" / "ui" / "shell.py").read_text(encoding="utf-8")
    pages = combined_page_source()
    messages = combined_i18n_source()
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")

    assert 'FEEDBACK_EMAIL = "s10777@syss.edu.hk"' in contact
    assert 'GITHUB_REPOSITORY_URL = "https://github.com/JackyLi10777/Study-Prefect-Duty-Roster-System"' in contact
    assert "mailto:" in contact and "urlencode" in contact
    assert "data-testid=sidebar-feedback" in shell
    assert "data-testid=feedback-channel" in pages
    assert "feedback_channel_safe_note" in messages
    assert "github_repository_action" in messages
    assert "不要附上姓名" in messages
    assert "do not attach names" in messages
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
