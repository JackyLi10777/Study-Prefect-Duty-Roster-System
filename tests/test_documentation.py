from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from nicegui_app.ui.i18n import MESSAGES
from nicegui_app.ui.page_catalog import PAGE_DEFINITIONS


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_RELEASE_STATE = json.loads(
    (PROJECT_ROOT / "docs" / "status" / "current-release.json").read_text(
        encoding="utf-8"
    )
)
CURRENT_RELEASE_TAG = CURRENT_RELEASE_STATE["release"]["tag"]
CURRENT_RELEASE_COMMIT = CURRENT_RELEASE_STATE["release"]["commit"]
CURRENT_RELEASE_FINGERPRINT = CURRENT_RELEASE_STATE["release"][
    "fingerprint_sha256"
]
CURRENT_ALEMBIC_HEAD = CURRENT_RELEASE_STATE["database"]["alembic_head"]
CURRENT_PREDECESSOR = CURRENT_RELEASE_STATE["historical_predecessor"]["release"]
CURRENT_WORKER_SOURCE_CHANGED = CURRENT_RELEASE_STATE["worker"][
    "source_changed_for_release"
]
CURRENT_STATUS_START = "<!-- SING_YIN_CURRENT_STATUS:START -->"
CURRENT_STATUS_END = "<!-- SING_YIN_CURRENT_STATUS:END -->"

from tests.ui_source import combined_i18n_source, combined_page_source


def _current_status_block(document: str) -> str:
    return document.split(CURRENT_STATUS_START, 1)[1].split(CURRENT_STATUS_END, 1)[0]


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
    assert "docs/DOCUMENTATION_INDEX.md" in readme
    assert "nicegui-self-hosted" in readme
    assert "streamlit-cloud" in readme


def test_documentation_index_routes_every_markdown_guide_and_defines_ownership() -> None:
    index = (PROJECT_ROOT / "docs" / "DOCUMENTATION_INDEX.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")

    for document in sorted((PROJECT_ROOT / "docs").glob("*.md")):
        if document.name != "DOCUMENTATION_INDEX.md":
            assert document.name in index, f"Documentation index omits {document.name}"

    for required in (
        "權威來源次序 / Source-of-truth precedence",
        "文件目錄與責任 / Catalogue and ownership",
        "使用模式、資料生命週期與成本邊界 / Mode, lifecycle, and cost boundary",
        "多用戶、可靠性與復原覆蓋 / Concurrency, reliability, and recovery coverage",
        "驗證層級 / Verification ladder",
        "已知限制與非目標 / Known limits and non-goals",
        "文件完整性維護 / Documentation maintenance checklist",
    ):
        assert required in index

    assert "docs/DOCUMENTATION_INDEX.md" in readme
    assert "docs/DOCUMENTATION_INDEX.md" in readme_en


def test_product_research_records_critical_decisions_and_four_product_zones() -> None:
    research = (PROJECT_ROOT / "docs" / "PRODUCT_RESEARCH_AND_IA_DECISIONS.md").read_text(
        encoding="utf-8"
    )
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    for zone in (
        "Public Product Entrance",
        "Unified Operations Workbench",
        "Trust & Engineering Hub",
        "Documentation and Developer Portal",
    ):
        assert zone in research
    for decision in ("**Adopt**", "**Adapt**", "**Reject"):
        assert decision in research
    for source in ("Apple Human Interface Guidelines", "Cloudflare Trust Hub", "OWASP"):
        assert source in research
    assert "2026-07-26" in research
    assert "PRODUCT_RESEARCH_AND_IA_DECISIONS.md" in design
    assert "Site-wide Neumorphism" in research
    for contract in (
        "Jobs, audiences and journeys",
        "Considered alternatives",
        "Shared component state matrix",
        "Performance and resource budgets",
        "6 MiB",
        "Admin and Guest use the same route definitions and components",
    ):
        assert contract in design


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
    assert "14／14" in status
    assert "v1.1 rollback" in readme_en
    assert "14／14" in readme
    assert "NiceGUI has no guest" not in design
    assert "NiceGUI never presents an anonymous guest role" not in design
    assert "still a v1.2 release gate" not in architecture
    assert "瀏覽器 snapshot 橋接" in security
    assert "尚未完成的瀏覽器 snapshot 橋接" not in security


def test_release_truth_docs_separate_active_drift_from_verified_history() -> None:
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
    acceptance = (PROJECT_ROOT / "docs" / "ACCEPTANCE_EVIDENCE.md").read_text(
        encoding="utf-8"
    )
    update_workflow = (PROJECT_ROOT / "docs" / "UPDATE_WORKFLOW.md").read_text(
        encoding="utf-8"
    )
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
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
    operator = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    design = (PROJECT_ROOT / "Professional_Design_System.md").read_text(encoding="utf-8")

    release_truth_documents = (status, architecture, security, handover, acceptance)
    for document in release_truth_documents:
        current_header = _current_status_block(document)
        assert CURRENT_RELEASE_TAG in current_header
        assert CURRENT_RELEASE_COMMIT in current_header
        assert CURRENT_ALEMBIC_HEAD in current_header
        assert CURRENT_PREDECESSOR in current_header
        assert "真人驗收" in current_header or "acceptance" in current_header.lower()

    active_pair_lines = tuple(
        _current_status_block(document)
        for document in (status, architecture, security, handover, acceptance)
    )
    for active_pair_line in active_pair_lines:
        assert CURRENT_RELEASE_TAG in active_pair_line
        assert CURRENT_RELEASE_COMMIT in active_pair_line
        assert CURRENT_ALEMBIC_HEAD in active_pair_line
        assert CURRENT_PREDECESSOR in active_pair_line
        assert "真人驗收" in active_pair_line or "acceptance" in active_pair_line.lower()

    stale_active_claims = (
        "only rc40 is the current deployed release",
        "the current rc39 origin",
        "current rc39 production pair",
        "currently rc39 production pair",
        "against the deployed rc35 pair",
        "目前 rc39 主機",
        "目前 rc39 origin",
        "目前正式 rc39 中",
        "current exact rc39 origin",
        "operational origin rollback now starts with exact rc39",
        "第一層 rc35 回退",
        "目前第一層受控回退是 rc35",
        "目前第一層 origin 回退是本頁頂部記錄的 rc39",
        "目前 rc43 production",
        "current rc43 production and the rc41",
        "production currently runs clean `v1.2.0-rc.43`",
        "目前正式 rc43 中",
        "the current rc43 origin",
        "current production is rc43",
    )
    for document in (
        status,
        architecture,
        security,
        handover,
        acceptance,
        quickstart,
        readme,
        readme_en,
        windows,
        cloudflare,
        viewer,
        decision,
        operator,
        update_workflow,
    ):
        normalized = document.lower()
        for stale_claim in stale_active_claims:
            assert stale_claim.lower() not in normalized

    formal_switch = decision.split("## 正式切換程序", 1)[1].split("## English", 1)[0]
    assert "本頁頂部生成狀態" in formal_switch
    assert "current rc" not in formal_switch.lower()
    assert "0012" in formal_switch
    assert "pre-0012" in formal_switch
    assert "code-only rollback" in formal_switch

    # Detailed historical rc20 provenance belongs in the status and handover
    # records; current architecture and security guides need not duplicate it.
    for document in (status, handover):
        assert "v1.2.0-rc.20" in document
        assert "e3d84858abfe23714929a87c4bcf76e55999ce7c" in document
        assert "93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a" in document

    cloudflare = (PROJECT_ROOT / "docs" / "CLOUDFLARE_REMOTE_ACCESS_SETUP.md").read_text(
        encoding="utf-8"
    )
    update_workflow = (PROJECT_ROOT / "docs" / "UPDATE_WORKFLOW.md").read_text(
        encoding="utf-8"
    )
    unified_guest = (PROJECT_ROOT / "docs" / "UNIFIED_GUEST_SECURITY_MODEL.md").read_text(
        encoding="utf-8"
    )
    assert "operational but provenance-drifted" not in cloudflare
    assert "目前 rc31 候選界線" not in update_workflow
    assert "Production currently runs clean `v1.2.0-rc.31`" not in unified_guest

    for document in (status, handover):
        assert "v1.2.0-rc.18" in document
        assert "fd504a8" in document

    # The exact rc18 rollout fingerprint belongs in historical rollback evidence.
    # The guest security model records the live pair and the exact rc20 release,
    # but intentionally does not duplicate the historical rc18 source digest.
    for document in (status, handover):
        assert "de0612fb8d9ee0530ba108efb1f658ab06e3e2212477fdb8832eb9ab3c0e1664" in document
        assert "93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a" in document

    assert "rc30 exact-source and deployment evidence" in status
    assert f"live Windows origin is clean annotated `{CURRENT_RELEASE_TAG}`" in status
    assert "R5／R6 remediation provenance" in status
    assert "v1.2 rc30 is the current controlled Windows origin" not in status
    assert "Historical Service Weave v1.2 rc18 controlled rollout" in status
    assert "Historical Service Weave v1.2 rc11 rollout" in status
    assert "rc18 host／Worker pair is now the second-level verified rollback target" in status  # noqa: RUF001
    assert "## 程式審查、邊界與擴展預期" in readme
    assert "SING_YIN_PORT" in readme
    assert "一百倍" in readme
    assert "cancelWelcomeFade is not defined" in status
    readme_header = "\n".join(readme.splitlines()[:15])
    assert "已核實線上來源" in readme_header
    assert CURRENT_ALEMBIC_HEAD in readme_header
    assert CURRENT_PREDECESSOR in readme_header
    assert "immediate known verified rollback" not in readme_header

    current_fingerprint = CURRENT_RELEASE_FINGERPRINT
    historical_rc30_fingerprint = (
        "15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc"
    )
    current_notice_zh = next(
        line for line in readme.splitlines() if line.startswith("> **已核實線上來源（")
    )
    current_notice_en = next(
        line
        for line in readme_en.splitlines()
        if line.startswith("> **Verified production truth (")
    )
    for current_notice in (current_notice_zh, current_notice_en):
        assert CURRENT_RELEASE_TAG in current_notice
        assert CURRENT_RELEASE_COMMIT in current_notice
        assert CURRENT_ALEMBIC_HEAD in current_notice
        assert CURRENT_PREDECESSOR in current_notice
        assert current_fingerprint in current_notice
        assert historical_rc30_fingerprint not in current_notice
        assert "acceptance" in current_notice.lower() or "真人驗收" in current_notice

    readme_main_row = next(
        line for line in readme.splitlines() if line.startswith("| `main` |")
    )
    assert "CURRENT_STATUS.md" in readme_main_row
    assert CURRENT_RELEASE_TAG not in readme_main_row
    assert "v1.2.0-rc.31" not in readme_main_row

    rc30_notice_zh = next(
        line for line in readme.splitlines() if line.startswith("**歷史 rc30 乾淨發布證據：**")
    )
    rc30_notice_en = next(
        line
        for line in readme_en.splitlines()
        if line.startswith("> **Historical clean-release evidence (")
    )
    for rc30_notice in (rc30_notice_zh, rc30_notice_en):
        assert "v1.2.0-rc.30" in rc30_notice
        assert historical_rc30_fingerprint in rc30_notice
        assert current_fingerprint not in rc30_notice

    current_capability_paragraph = readme_en.split(
        "<!-- CURRENT_CAPABILITY_SUMMARY:START -->", 1
    )[1].split("<!-- CURRENT_CAPABILITY_SUMMARY:END -->", 1)[0]
    assert "current system status" in current_capability_paragraph
    assert current_fingerprint not in current_capability_paragraph
    assert historical_rc30_fingerprint not in current_capability_paragraph
    assert "remains disabled by default" not in status
    assert "now run the matching rc7 release" not in status
    assert "Windows origin remains healthy／ready on rc4" not in security
    assert "This document does not claim that v1.2 is deployed" not in security

    operator_release_documents = {
        "README.md": readme,
        "README-EN.md": readme_en,
        "PROJECT_STATUS.md": status,
        "docs/ACCEPTANCE_EVIDENCE.md": acceptance,
        "docs/CLOUDFLARE_REMOTE_ACCESS_SETUP.md": cloudflare,
        "docs/DEPLOYMENT_DECISION.md": decision,
        "docs/NICEGUI_ARCHITECTURE.md": architecture,
        "docs/PUBLIC_ROSTER_VIEWER.md": viewer,
        "docs/QUICKSTART.md": quickstart,
        "docs/RELEASE_HANDOVER.md": handover,
        "docs/UNIFIED_GUEST_SECURITY_MODEL.md": security,
        "docs/UPDATE_WORKFLOW.md": update_workflow,
        "docs/WINDOWS_DEDICATED_HOST_SETUP.md": windows,
    }
    stale_release_patterns = (
        re.compile(
            r"\brc20\b.{0,240}(?:not deployed|undeployed|not-yet-deployed|"
            r"pending (?:the )?(?:host |origin )?(?:switch|switchover|cutover)|"
            r"before rc20 can replace rc18)",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"rc20.{0,240}(?:尚未(?:部署|切換)|尚待(?:執行|部署|切換)|"
            r"不代表 Windows 已切換|等待 UAC|"
            r"下一步仍是.{0,100}(?:origin switch|Windows.*切換))",
            re.DOTALL,
        ),
        re.compile(
            r"(?:\blive rc18\b|\bcurrent (?:operating )?baseline "
            r"(?:is|remains|uses) (?:v1\.2\.0-)?rc18\b|"
            r"\brunning production origin.{0,100}\brc18\b|"
            r"現行(?:正式主機|發布|基線).{0,12}rc18|"
            r"目前日常操作仍以 rc18|rc18 正式主機)",
            re.IGNORECASE | re.DOTALL,
        ),
        re.compile(
            r"(?:\blive rc(?:20|21)\b|\brunning production origin.{0,100}"
            r"\brc(?:20|21)\b|\bService Weave v1\.2 rc(?:20|21).{0,80}"
            r"\((?:live|live origin))",
            re.IGNORECASE | re.DOTALL,
        ),
    )
    for relative_path, document in operator_release_documents.items():
        for paragraph in re.split(r"\n\s*\n", document):
            for stale_pattern in stale_release_patterns:
                assert stale_pattern.search(paragraph) is None, (
                    f"{relative_path} contains stale release-state wording: "
                    f"{stale_pattern.pattern}"
                )

    next_steps = status.split("## Next Steps", 1)[1].split(
        "## Key Decisions and Architecture", 1
    )[0]
    assert "Complete supervised Head Study Prefect and teacher-advisor acceptance" in next_steps
    assert "Create a new immutable candidate only if acceptance identifies" in next_steps
    assert "v1.2.0-rc.5" not in next_steps

    release_sequence = handover.split("### rc27 已完成發布紀錄與回退次序", 1)[
        1
    ].split(
        "## 正式驗收清單", 1
    )[0]
    assert "v1.2.0-rc.20" in release_sequence
    assert "e3d84858abfe23714929a87c4bcf76e55999ce7c" in release_sequence
    assert "93c6c93866c617862c790a4ed939d9acbe789dcdfaf512c9519aff9e0b4e6d3a" in release_sequence
    assert "下一個獲批准的 annotated tag" not in release_sequence
    assert "本次為 `v1.2.0-rc.7`" not in release_sequence
    assert "v1.1.0-rc.16" in handover

    assert "訪客體驗 / Try as guest" in operator
    assert "互動示範工作區" in operator
    assert "只有 `/view#…`" in operator


def test_operator_deployment_docs_use_observed_drift_and_recovery_hierarchy() -> None:
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
        current_header = _current_status_block(document)
        assert CURRENT_RELEASE_TAG in current_header
        assert CURRENT_RELEASE_COMMIT in current_header
        assert CURRENT_ALEMBIC_HEAD in current_header
        assert CURRENT_PREDECESSOR in current_header
        assert "真人驗收" in current_header or "acceptance" in current_header.lower()
        assert "v1.2.0-rc.30" in document
        assert "74b84f43786b00feb15b51a6270ff71c9430773f" in document
        assert "11763f08-d40d-46d5-93dc-5ca2599d4154" in document

    assert "Current production identity is recorded in the document header" in decision
    assert "Historically, before the rc39 rollout" in decision
    assert "目前來源待對帳的 runtime" not in decision
    assert "現行 origin／Worker 來源待對帳" not in quickstart
    assert "受審候選的正式 tag／commit" in quickstart
    assert "現行證據以 rc30 report 為準" not in quickstart
    expected_worker_source = (
        "Worker 來源已更新"
        if CURRENT_WORKER_SOURCE_CHANGED is True
        else "Worker 來源沒有改動"
    )
    assert expected_worker_source in _current_status_block(cloudflare)
    assert "不得單側回退而形成未驗證組合" in cloudflare

    assert "保存及歸屬差異" in cloudflare
    assert "依序考慮 rc27、rc26 及 rc24" in cloudflare
    assert "restore the recorded rc17 host bundle" not in cloudflare

    assert "schema-compatible rc4" not in quickstart
    assert "pre-v1.2 baseline" not in quickstart
    assert "v1.2 rc5 候選狀態" not in viewer
    assert "v1.2 rc7 發布狀態" not in cloudflare
    assert "v1.1 已部署基線與 v1.2 候選" not in decision
    assert '$ReleaseRef = "v1.2.0-rc.20"' not in windows
    assert '$ReleaseRef = "<next-approved-annotated-tag>"' in windows
    assert '$ReleaseRef = "v1.1.0-rc.16"' not in windows
    assert "15d155d8d745b14b574b08d793150c93aa77946e7d17a63030844c44adededbc" in decision
    assert "<next-approved-annotated-tag>" not in decision


def test_docs_share_historical_rc20_device_matrix_and_current_rollback_hierarchy() -> None:
    device_viewports = ("768×1024", "820×1180", "1024×768", "1440×1024")
    device_documents = (
        "README.md",
        "README-EN.md",
        "PROJECT_STATUS.md",
        "Professional_Design_System.md",
        "docs/ACCEPTANCE_EVIDENCE.md",
        "docs/NICEGUI_ARCHITECTURE.md",
        "docs/RELEASE_HANDOVER.md",
        "docs/UPDATE_WORKFLOW.md",
        "docs/WINDOWS_DEDICATED_HOST_SETUP.md",
    )

    for relative_path in device_documents:
        document = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        for viewport in device_viewports:
            assert viewport in document, f"{relative_path} is missing {viewport}"

    acceptance = (PROJECT_ROOT / "docs" / "ACCEPTANCE_EVIDENCE.md").read_text(
        encoding="utf-8"
    )
    candidate_matrix = acceptance.split(
        "## rc20 已驗證候選裝置矩陣 / Verified candidate device matrix", 1
    )[1].split("## 使用方法", 1)[0]
    for viewport in device_viewports:
        assert viewport in candidate_matrix
    assert "scripts/verify_nicegui_mobile.py" in candidate_matrix
    assert "scripts/verify_nicegui_ui.py" in candidate_matrix
    assert "這只完成機器量測，不能代替實體裝置或部署後驗收" in acceptance
    assert "機器與線上證據不能代替真人驗收" in acceptance

    quickstart = (PROJECT_ROOT / "docs" / "QUICKSTART.md").read_text(encoding="utf-8")
    assert (
        "ACCEPTANCE_EVIDENCE.md#rc20-已驗證候選裝置矩陣--verified-candidate-device-matrix"
        in quickstart
    )

    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    readme_en = (PROJECT_ROOT / "README-EN.md").read_text(encoding="utf-8")
    status = (PROJECT_ROOT / "PROJECT_STATUS.md").read_text(encoding="utf-8")
    handover = (PROJECT_ROOT / "docs" / "RELEASE_HANDOVER.md").read_text(encoding="utf-8")
    cloudflare = (PROJECT_ROOT / "docs" / "CLOUDFLARE_REMOTE_ACCESS_SETUP.md").read_text(
        encoding="utf-8"
    )
    decision = (PROJECT_ROOT / "docs" / "DEPLOYMENT_DECISION.md").read_text(
        encoding="utf-8"
    )

    rollback_contracts = {
        "README.md": readme,
        "docs/RELEASE_HANDOVER.md": handover,
        "docs/CLOUDFLARE_REMOTE_ACCESS_SETUP.md": cloudflare,
        "docs/DEPLOYMENT_DECISION.md": decision,
    }
    for relative_path, document in rollback_contracts.items():
        current_summary = _current_status_block(document)
        assert CURRENT_RELEASE_TAG in current_summary, relative_path
        assert CURRENT_RELEASE_COMMIT in current_summary, relative_path
        assert CURRENT_ALEMBIC_HEAD in current_summary, relative_path
        assert CURRENT_PREDECESSOR in current_summary, relative_path
        assert "真人驗收" in current_summary or "acceptance" in current_summary, relative_path
    normalized_readme_en = " ".join(readme_en.split())
    assert "zero-percent version smoke" in normalized_readme_en
    assert f"live Windows origin is clean annotated `{CURRENT_RELEASE_TAG}`" in status

    assert "rc17／`99f5816` 與 Worker `c85770b2-c626-462c-bc74-5e6bd305c75b` 是即時回退組合" not in readme
    assert "is the immediate rollback pair" not in status
    assert "Service Weave rc17 is the deployed release candidate" not in decision


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
        "verify_update.py --release",
        "deploy_windows_release.ps1",
        ".sing-yin-release.json",
        "previousReleaseRef",
        "建立交接備份包",
    ):
        assert required_text in guide

    assert "不要自行把主機改成 `0.0.0.0`" in guide
    assert "Cloudflare 遠端存取完整設定手冊" in guide
    assert "git switch --detach $ReleaseRef" not in guide
    update_section = guide.split("## 12. 更新程式的完整步驟", 1)[1]
    assert (
        r"C:\SingYinRoster\.venv\Scripts\python.exe -m pip install --require-hashes "
        r"-r C:\SingYinRoster\requirements.lock"
        not in update_section
    )


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


def test_platform_showcase_exposes_real_team_responsibilities_without_invented_structure() -> None:
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
    assert "Weekly decisions, publishing, and handover" in messages
    assert "Duty coordination and Assist. in charge" in messages
    assert "Service in Rooms 302, 303, and 202" in messages
    assert "Four real work areas" in messages
    assert "not departments, offices, ranks, or additional staff" in MESSAGES["capability_map_copy"]["en"]


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


def test_environment_example_documents_operator_facing_runtime_overrides() -> None:
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    for variable in (
        "SING_YIN_APP_MODE",
        "SING_YIN_DATABASE_PATH",
        "SING_YIN_BACKUP_DIR",
        "SING_YIN_PUBLIC_URL",
        "SING_YIN_SLOW_REQUEST_MS",
        "SING_YIN_CLOUDFLARE_PRIVATE_WARP",
        "SING_YIN_CLOUDFLARE_PRIVATE_HOSTNAME",
    ):
        assert variable in env_example


def test_current_release_history_and_gate_count_are_exact() -> None:
    changelog = (PROJECT_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    operator_guide = (PROJECT_ROOT / "docs" / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")

    rc27_entry = changelog.split("## v1.2.0-rc.27 — 2026-07-27", 1)[1].split(
        "## v1.2.0-rc.26", 1
    )[0]
    for release_fact in (
        "latest earlier active roster",
        "later independent obligations",
        "explicit imports and exports",
        "same-client page-context composition atomic",
        "Deepseek R3/R4 evidence",
    ):
        assert release_fact in rc27_entry

    engineering_section = operator_guide.split("## 11. 工程與品質證據", 1)[1].split(
        "\n## ", 1
    )[0]
    assert "目前十五道發布閘門" in engineering_section
    assert "十四道閘門只屬較早版本的歷史說明" in engineering_section
    assert "八道發布閘門" not in engineering_section


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
        if page.navigation_group == "nav_trust_resources"
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
    assert 'role=table aria-label="{attr(t("guide_troubleshooting_title"))}"' in pages
    assert 'id=start-first-steps aria-label="{attr(t("start_toc_first_steps"))}"' in pages
    assert 'id=handover-steps-section aria-label="{attr(t("handover_steps_title"))}"' in pages
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
