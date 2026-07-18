from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_update import (
    VerificationPlan,
    build_tasks,
    changed_paths,
    classify_paths,
    select_profile,
)


@pytest.mark.parametrize(
    ("paths", "profile", "needs_deno", "formal_release_required"),
    (
        (("README.md", "docs/RELEASE_HANDOVER.md"), "docs", False, False),
        (("tests/test_documentation.py", "PROJECT_STATUS.md"), "tests", False, False),
        (("tests/test_cloudflare_roster_viewer.py",), "tests", True, False),
        (("cloudflare/roster_viewer/worker.js", "README.md"), "worker", True, True),
        ((".github/workflows/quality.yml", "docs/BRANCH_STRATEGY.md"), "assurance", False, False),
        (("nicegui_app/ui/pages.py", "README.md"), "full", True, True),
        (("packages/roster_core/roster_core/generator.py",), "full", True, True),
        (("migrations/versions/9999_change.py",), "full", True, True),
        (("design_system/product-identity.v1.json",), "full", True, True),
        (("requirements.lock",), "full", True, True),
        (("unexpected/new-source.xyz",), "full", True, True),
    ),
)
def test_change_classifier_selects_the_highest_safe_profile(
    paths: tuple[str, ...],
    profile: str,
    needs_deno: bool,
    formal_release_required: bool,
) -> None:
    plan = classify_paths(paths)

    assert plan.profile == profile
    assert plan.needs_deno is needs_deno
    assert plan.formal_release_required is formal_release_required
    assert plan.changed_path_count == len(paths)


def test_no_change_selects_no_work() -> None:
    plan = classify_paths(())

    assert plan.profile == "none"
    assert plan.changed_path_count == 0


def test_docs_profile_runs_only_documentation_hygiene_and_secret_checks() -> None:
    plan = classify_paths(("README.md",))
    tasks = build_tasks(plan, ("README.md",), ci=False, base=None, head="HEAD", staged=False)

    assert [task.name for task in tasks] == [
        "diff_whitespace",
        "documentation_contract",
        "repository_hygiene",
        "secret_scan",
    ]
    flattened = [argument for task in tasks for command in task.commands for argument in command]
    assert "verify_release_candidate.py" not in flattened
    assert "secret_scan" in flattened


def test_local_full_profile_runs_pre_push_quality_gates_without_browser_drills() -> None:
    plan = classify_paths(("nicegui_app/main.py",))
    tasks = build_tasks(plan, ("nicegui_app/main.py",), ci=False, base=None, head="HEAD", staged=False)

    assert [task.name for task in tasks] == [
        "diff_whitespace",
        "automated_test_suite",
        "worker_contract",
        "repository_hygiene",
        "security_gates",
    ]
    flattened = [argument for task in tasks for command in task.commands for argument in command]
    assert "verify_release_candidate.py" not in flattened


def test_local_worker_profile_defers_formal_release_evidence_until_release_intent() -> None:
    plan = classify_paths(("cloudflare/roster_viewer/worker.js",))
    tasks = build_tasks(
        plan,
        ("cloudflare/roster_viewer/worker.js",),
        ci=False,
        base=None,
        head="HEAD",
        staged=False,
    )

    assert plan.formal_release_required is True
    assert [task.name for task in tasks] == [
        "diff_whitespace",
        "worker_contract",
        "repository_hygiene",
        "secret_scan",
    ]


def test_explicit_release_intent_runs_the_formal_verifier_once() -> None:
    plan = classify_paths(("nicegui_app/main.py",))
    tasks = build_tasks(
        plan,
        ("nicegui_app/main.py",),
        ci=False,
        release=True,
        base=None,
        head="HEAD",
        staged=False,
    )

    assert [task.name for task in tasks] == ["diff_whitespace", "formal_release_candidate"]
    assert sum(
        argument == "scripts/verify_release_candidate.py"
        for task in tasks
        for command in task.commands
        for argument in command
    ) == 1


def test_explicit_release_intent_can_refresh_formal_evidence_without_source_changes() -> None:
    plan = classify_paths(())
    tasks = build_tasks(
        plan,
        (),
        ci=False,
        release=True,
        base=None,
        head="HEAD",
        staged=False,
    )

    assert [task.name for task in tasks] == ["formal_release_candidate"]


def test_ci_full_profile_uses_non_browser_quality_gates() -> None:
    plan = VerificationPlan("full", "test", 1, True, True)
    tasks = build_tasks(plan, ("nicegui_app/main.py",), ci=True, base="HEAD^", head="HEAD", staged=False)

    assert [task.name for task in tasks] == [
        "diff_whitespace",
        "automated_test_suite",
        "worker_contract",
        "repository_hygiene",
        "security_gates",
    ]
    flattened = [argument for task in tasks for command in task.commands for argument in command]
    assert "verify_release_candidate.py" not in flattened
    assert flattened.count("cloudflare/roster_viewer/worker_gateway_test.js") == 1
    assert any(argument.startswith("--deselect=tests/test_cloudflare_roster_viewer.py::") for argument in flattened)


def test_shared_test_helper_escalates_to_the_complete_python_suite() -> None:
    plan = classify_paths(("tests/ui_source.py",))
    tasks = build_tasks(plan, ("tests/ui_source.py",), ci=False, base=None, head="HEAD", staged=False)
    changed_test = next(task for task in tasks if task.name == "changed_tests")

    assert changed_test.commands[0][-3:] == ("-m", "pytest", "-q")


def test_missing_git_base_fails_closed_to_full(monkeypatch, tmp_path: Path) -> None:
    class Result:
        returncode = 1
        stdout = ""

    monkeypatch.setattr("scripts.verify_update._git", lambda _arguments: Result())

    paths = changed_paths(base="missing", head="HEAD", staged=False)
    plan = classify_paths(paths)

    assert paths == ("__unresolved_git_base__",)
    assert plan.profile == "full"


def test_changed_path_discovery_includes_deleted_files(monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []

    class Result:
        returncode = 0
        stdout = "nicegui_app/removed.py\n"

    def fake_git(arguments):  # type: ignore[no-untyped-def]
        calls.append(tuple(arguments))
        return Result()

    monkeypatch.setattr("scripts.verify_update._git", fake_git)

    paths = changed_paths(base="before", head="after", staged=False)

    assert paths == ("nicegui_app/removed.py",)
    assert "--diff-filter=ACDMRTUXB" in calls[0]
    assert classify_paths(paths).profile == "full"


def test_manual_profile_may_upgrade_but_never_downgrade_automatic_risk() -> None:
    runtime = classify_paths(("nicegui_app/main.py",))
    docs = classify_paths(("README.md",))

    assert select_profile(docs, "full").profile == "full"
    assert select_profile(docs, "docs") == docs
    with pytest.raises(ValueError, match="Cannot lower automatic profile"):
        select_profile(runtime, "docs")
    with pytest.raises(ValueError, match="Cannot lower automatic profile"):
        select_profile(runtime, "none")


def test_mixed_test_and_documentation_change_runs_both_contracts() -> None:
    paths = ("tests/test_update_verification.py", "README.md")
    plan = classify_paths(paths)
    tasks = build_tasks(plan, paths, ci=False, base=None, head="HEAD", staged=False)
    changed_test = next(task for task in tasks if task.name == "changed_tests")
    command = changed_test.commands[0]

    assert "tests/test_update_verification.py" in command
    assert "tests/test_documentation.py" in command


def test_worker_ci_runs_deno_contract_once_and_keeps_mixed_docs_contract() -> None:
    paths = ("cloudflare/roster_viewer/worker.js", "README.md")
    plan = classify_paths(paths)
    tasks = build_tasks(plan, paths, ci=True, base="HEAD^", head="HEAD", staged=False)
    worker = next(task for task in tasks if task.name == "worker_contract")
    flattened = [argument for command in worker.commands for argument in command]

    assert flattened.count("cloudflare/roster_viewer/worker_gateway_test.js") == 1
    assert "tests/test_documentation.py" in flattened
