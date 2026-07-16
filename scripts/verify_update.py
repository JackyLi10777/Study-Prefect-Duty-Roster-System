"""Select and run the smallest safe verification profile for a source update.

The formal release-candidate verifier remains the authority for deployable
runtime changes. This command prevents documentation, test-only, Worker-only,
and release-tooling changes from paying that full cost unnecessarily. Normal
use verifies a branch before commit or push; ``--release`` explicitly runs the
formal browser, write, backup, and recovery evidence gate. Unknown paths fail
closed to the highest pre-push profile.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import time
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.check_repository_hygiene import is_release_source


REPORT_PATH = PROJECT_ROOT / "logs" / "change-verification-report.json"
PROFILES = ("none", "docs", "tests", "worker", "assurance", "full")

_DOCUMENTATION_ROOT_FILES = {
    "code_of_conduct.md",
    "codex_prompts.md",
    "contributing.md",
    "license",
    "notice.md",
    "professional_design_system.md",
    "project_status.md",
    "readme-en.md",
    "readme.md",
    "security.md",
}
_ASSURANCE_FILES = {
    ".github/dependabot.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/quality.yml",
    "scripts/verify_update.py",
}
_FULL_ROOT_FILES = {
    ".env.example",
    ".gitattributes",
    ".gitignore",
    "alembic.ini",
    "daily_verses.py",
    "pyproject.toml",
    "requirements-dev.lock",
    "requirements-dev.txt",
    "requirements.lock",
    "requirements.txt",
    "reset_practice_mode.cmd",
    "start_practice_mode.cmd",
    "start_sing_yin_roster.cmd",
}
_FULL_ROOT_PREFIXES = (
    "data/devotional/",
    "data/demo/",
    "migrations/",
    "music/",
    "nicegui_app/",
    "packages/",
    "scripts/",
)
_SHARED_TEST_FILES = {
    "tests/__init__.py",
    "tests/conftest.py",
    "tests/ui_source.py",
}
_ASSURANCE_TESTS = (
    "tests/test_documentation.py",
    "tests/test_release_evidence.py",
    "tests/test_release_verifier.py",
    "tests/test_repository_hygiene.py",
    "tests/test_supply_chain.py",
)
_WORKER_TESTS = (
    "tests/test_access_control_ui.py",
    "tests/test_cloudflare_guest_trial.py",
    "tests/test_cloudflare_roster_viewer.py",
    "tests/test_public_roster_share.py",
    "tests/test_supply_chain.py",
)
_WORKER_RUNTIME_TEST = (
    "tests/test_cloudflare_roster_viewer.py::"
    "test_worker_runtime_access_crypto_and_proxy_contracts"
)


@dataclass(frozen=True)
class VerificationPlan:
    profile: str
    reason: str
    changed_path_count: int
    needs_deno: bool
    formal_release_required: bool


@dataclass(frozen=True)
class Task:
    name: str
    commands: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class TaskResult:
    name: str
    status: str
    duration_ms: int
    return_code: int
    output: str = ""


def normalize_path(raw_path: str) -> str:
    """Return a stable repository-relative path without trusting shell syntax."""
    normalized = raw_path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _is_documentation(path: str) -> bool:
    lower = path.lower()
    return (
        lower.startswith("docs/")
        or (lower.startswith("archive/") and PurePosixPath(lower).name == "readme.md")
        or lower in _DOCUMENTATION_ROOT_FILES
    )


def _is_test(path: str) -> bool:
    return path.lower().startswith("tests/")


def _is_worker(path: str) -> bool:
    return path.lower().startswith("cloudflare/")


def _is_assurance(path: str) -> bool:
    lower = path.lower()
    return lower in _ASSURANCE_FILES or lower.startswith(".github/")


def _is_full(path: str) -> bool:
    lower = path.lower()
    return lower in _FULL_ROOT_FILES or any(lower.startswith(prefix) for prefix in _FULL_ROOT_PREFIXES)


def classify_paths(paths: Iterable[str]) -> VerificationPlan:
    """Classify by the highest-risk changed path; unknown paths fail closed."""
    normalized = tuple(sorted({normalize_path(path) for path in paths if normalize_path(path)}))
    if not normalized:
        return VerificationPlan("none", "No release-relevant source changes were detected.", 0, False, False)

    categories: set[str] = set()
    unknown: list[str] = []
    for path in normalized:
        if _is_documentation(path):
            categories.add("docs")
        elif _is_test(path):
            categories.add("tests")
        elif _is_worker(path):
            categories.add("worker")
        elif _is_assurance(path):
            categories.add("assurance")
        elif _is_full(path):
            categories.add("full")
        else:
            unknown.append(path)

    count = len(normalized)
    if unknown:
        return VerificationPlan(
            "full",
            "An unclassified source path was detected; verification was upgraded fail-closed.",
            count,
            True,
            True,
        )
    if "full" in categories:
        return VerificationPlan(
            "full",
            "Deployable runtime, policy, persistence, dependency, asset, or host source changed.",
            count,
            True,
            True,
        )
    if "worker" in categories:
        return VerificationPlan(
            "worker",
            "The Cloudflare gateway changed; CI can focus on its boundary, but deployment still requires formal evidence.",
            count,
            True,
            True,
        )
    if "assurance" in categories:
        return VerificationPlan(
            "assurance",
            "Verification, repository, security, or CI machinery changed.",
            count,
            False,
            False,
        )
    if "tests" in categories:
        needs_deno = any(
            path.lower() == "tests/test_cloudflare_roster_viewer.py"
            for path in normalized
        )
        return VerificationPlan(
            "tests",
            "Only tests plus documentation changed; deployed runtime is unchanged.",
            count,
            needs_deno,
            False,
        )
    return VerificationPlan(
        "docs",
        "Only documentation or maintained status text changed; deployed runtime is unchanged.",
        count,
        False,
        False,
    )


def _git(arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def changed_paths(*, base: str | None, head: str, staged: bool) -> tuple[str, ...]:
    """Read changed paths from Git while retaining untracked release sources locally."""
    if base:
        result = _git(("diff", "--name-only", "--diff-filter=ACDMRTUXB", f"{base}...{head}"))
    elif staged:
        result = _git(("diff", "--cached", "--name-only", "--diff-filter=ACDMRTUXB"))
    else:
        result = _git(("diff", "--name-only", "--diff-filter=ACDMRTUXB", "HEAD"))
    if result.returncode != 0:
        # A missing CI base must never silently downgrade verification.
        return ("__unresolved_git_base__",)
    paths = {normalize_path(path) for path in result.stdout.splitlines() if normalize_path(path)}
    if not base and not staged:
        untracked = _git(("ls-files", "--others", "--exclude-standard"))
        if untracked.returncode != 0:
            return ("__unresolved_git_state__",)
        paths.update(
            normalized
            for path in untracked.stdout.splitlines()
            if (normalized := normalize_path(path)) and is_release_source(normalized)
        )
    return tuple(sorted(paths))


def _python(*arguments: str) -> tuple[str, ...]:
    return (sys.executable, "-X", "utf8", *arguments)


def _diff_check_command(base: str | None, head: str, staged: bool) -> tuple[str, ...]:
    if base:
        return ("git", "diff", "--check", f"{base}...{head}")
    if staged:
        return ("git", "diff", "--cached", "--check")
    return ("git", "diff", "--check", "HEAD")


def _focused_test_paths(paths: Iterable[str]) -> tuple[str, ...]:
    normalized = tuple(normalize_path(path) for path in paths)
    if any(path.lower() in _SHARED_TEST_FILES for path in normalized):
        return ()
    return tuple(
        sorted(
            {
                path
                for path in normalized
                if path.lower().startswith("tests/test_") and path.lower().endswith(".py")
            }
        )
    )


def _contains_documentation(paths: Iterable[str]) -> bool:
    return any(_is_documentation(normalize_path(path)) for path in paths)


def _profile_test_arguments(
    paths: Iterable[str],
    *,
    required_tests: Iterable[str] = (),
    deselect_worker_runtime: bool = False,
) -> tuple[str, ...]:
    normalized = tuple(normalize_path(path) for path in paths)
    focused = _focused_test_paths(normalized)
    has_test_change = any(_is_test(path) for path in normalized)
    if has_test_change and not focused:
        selected: tuple[str, ...] = ()
    else:
        tests = set(required_tests)
        tests.update(focused)
        if _contains_documentation(normalized):
            tests.add("tests/test_documentation.py")
        selected = tuple(sorted(tests))
    arguments = ["-m", "pytest", "-q"]
    if deselect_worker_runtime:
        arguments.append(f"--deselect={_WORKER_RUNTIME_TEST}")
    arguments.extend(selected)
    return tuple(arguments)


def select_profile(auto_plan: VerificationPlan, requested: str) -> VerificationPlan:
    """Allow an explicit profile only when it cannot reduce automatic safety."""
    if requested in {"auto", auto_plan.profile}:
        return auto_plan
    if requested != "full":
        raise ValueError(
            f"Cannot lower automatic profile {auto_plan.profile!r} to {requested!r}; "
            "only an upgrade to 'full' is allowed."
        )
    return VerificationPlan(
        "full",
        "The automatically selected profile was explicitly upgraded to full.",
        auto_plan.changed_path_count,
        True,
        True,
    )


def build_tasks(
    plan: VerificationPlan,
    paths: Iterable[str],
    *,
    ci: bool,
    release: bool = False,
    base: str | None,
    head: str,
    staged: bool,
) -> tuple[Task, ...]:
    """Build independent read-only tasks for the selected profile."""
    if release:
        tasks: list[Task] = []
        if plan.profile != "none":
            tasks.append(Task("diff_whitespace", (_diff_check_command(base, head, staged),)))
        tasks.append(
            Task("formal_release_candidate", (_python("scripts/verify_release_candidate.py"),))
        )
        return tuple(tasks)
    if plan.profile == "none":
        return ()
    diff_task = Task("diff_whitespace", (_diff_check_command(base, head, staged),))
    hygiene = Task(
        "repository_hygiene",
        (_python("scripts/check_repository_hygiene.py"),),
    )
    secret_scan = Task(
        "secret_scan",
        (_python("scripts/run_security_checks.py", "--only", "secret_scan"),),
    )
    if plan.profile == "docs":
        return (
            diff_task,
            Task("documentation_contract", (_python("-m", "pytest", "-q", "tests/test_documentation.py"),)),
            hygiene,
            secret_scan,
        )
    if plan.profile == "tests":
        test_arguments = _profile_test_arguments(paths)
        return (
            diff_task,
            Task("changed_tests", (_python(*test_arguments),)),
            hygiene,
            secret_scan,
        )
    if plan.profile == "worker":
        deno = shutil.which("deno") or "deno"
        return (
            diff_task,
            Task(
                "worker_contract",
                (
                    (deno, "check", "cloudflare/roster_viewer/worker.js"),
                    (deno, "test", "--no-check", "cloudflare/roster_viewer/worker_gateway_test.js"),
                    (_python(*_profile_test_arguments(
                        paths,
                        required_tests=_WORKER_TESTS,
                        deselect_worker_runtime=True,
                    ))),
                ),
            ),
            hygiene,
            secret_scan,
        )
    if plan.profile == "assurance":
        assurance_arguments = _profile_test_arguments(paths, required_tests=_ASSURANCE_TESTS)
        return (
            diff_task,
            Task("assurance_contract", (_python(*assurance_arguments),)),
            hygiene,
            Task("security_gates", (_python("scripts/run_security_checks.py"),)),
        )
    deno = shutil.which("deno") or "deno"
    return (
        diff_task,
        Task(
            "automated_test_suite",
            (_python(
                "-m",
                "pytest",
                "-q",
                f"--deselect={_WORKER_RUNTIME_TEST}",
            ),),
        ),
        Task(
            "worker_contract",
            (
                (deno, "check", "cloudflare/roster_viewer/worker.js"),
                (deno, "test", "--no-check", "cloudflare/roster_viewer/worker_gateway_test.js"),
            ),
        ),
        hygiene,
        Task("security_gates", (_python("scripts/run_security_checks.py"),)),
    )


def _run_task(task: Task) -> TaskResult:
    started = time.monotonic()
    combined_output: list[str] = []
    return_code = 0
    for command in task.commands:
        common_arguments = {
            "cwd": PROJECT_ROOT,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "env": {**os.environ, "PYTHONUTF8": "1"},
            "check": False,
        }
        if task.name == "formal_release_candidate":
            # The long formal verifier owns its safe console output. Stream it
            # so an operator never waits several minutes behind a blank screen.
            result = subprocess.run(list(command), **common_arguments)
        else:
            result = subprocess.run(list(command), capture_output=True, **common_arguments)
            if result.stdout:
                combined_output.append(result.stdout.rstrip())
            if result.stderr:
                combined_output.append(result.stderr.rstrip())
        if result.returncode != 0:
            return_code = result.returncode
            break
    duration_ms = round((time.monotonic() - started) * 1000)
    return TaskResult(
        task.name,
        "pass" if return_code == 0 else "fail",
        duration_ms,
        return_code,
        "\n".join(part for part in combined_output if part),
    )


def execute_tasks(tasks: Sequence[Task], *, max_workers: int) -> tuple[TaskResult, ...]:
    """Run independent checks concurrently; the formal verifier stays serialized."""
    if not tasks:
        return ()
    if any(task.name == "formal_release_candidate" for task in tasks):
        results: list[TaskResult] = []
        for task in tasks:
            result = _run_task(task)
            results.append(result)
            if result.status == "fail":
                break
        return tuple(results)

    results_by_name: dict[str, TaskResult] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as executor:
        futures = {executor.submit(_run_task, task): task.name for task in tasks}
        for future in as_completed(futures):
            result = future.result()
            results_by_name[result.name] = result
    return tuple(results_by_name[task.name] for task in tasks)


def _write_report(
    plan: VerificationPlan,
    results: Sequence[TaskResult],
    *,
    ci: bool,
    release: bool,
    staged: bool,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    mode = (
        "release"
        if release
        else ("ci" if ci else ("pre-push" if staged else "working-tree"))
    )
    payload = {
        "schemaVersion": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "profile": plan.profile,
        "reason": plan.reason,
        "changedPathCount": plan.changed_path_count,
        "formalReleaseRequired": plan.formal_release_required,
        "formalReleaseExecuted": release,
        "status": "pass" if all(result.status == "pass" for result in results) else "fail",
        "checks": [
            {
                "name": result.name,
                "status": result.status,
                "durationMs": result.duration_ms,
                "returnCode": result.return_code,
            }
            for result in results
        ],
    }
    temporary = REPORT_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(REPORT_PATH)


def _write_github_output(path: Path, plan: VerificationPlan) -> None:
    with path.open("a", encoding="utf-8") as output:
        output.write(f"profile={plan.profile}\n")
        output.write(f"needs_deno={'true' if plan.needs_deno else 'false'}\n")
        output.write(f"formal_release_required={'true' if plan.formal_release_required else 'false'}\n")


def _print_plan(
    plan: VerificationPlan,
    tasks: Sequence[Task],
    *,
    ci: bool,
    release: bool,
    staged: bool,
) -> None:
    intent = (
        "release"
        if release
        else ("ci" if ci else ("pre-push" if staged else "working-tree"))
    )
    print(f"Verification intent: {intent}", flush=True)
    print(f"Verification profile: {plan.profile}", flush=True)
    print(f"Reason: {plan.reason}", flush=True)
    print(f"Changed paths: {plan.changed_path_count}", flush=True)
    if intent == "working-tree":
        print(
            "Commit scope: diagnostic only; review and stage intended files, then rerun with --staged.",
            flush=True,
        )
    if plan.formal_release_required and not release:
        print(
            "Formal release evidence: required before deployment; deferred for this pre-push run.",
            flush=True,
        )
    if tasks:
        print("Checks: " + ", ".join(task.name for task in tasks), flush=True)
    else:
        print("Checks: none", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git base revision; omit for the local working tree.")
    parser.add_argument("--head", default="HEAD", help="Git head revision (default: HEAD).")
    parser.add_argument("--staged", action="store_true", help="Inspect only staged changes.")
    parser.add_argument(
        "--profile",
        choices=("auto", *PROFILES),
        default="auto",
        help="Override automatic classification.",
    )
    parser.add_argument("--plan", action="store_true", help="Print the selected plan without executing it.")
    parser.add_argument("--ci", action="store_true", help="Use CI checks without browser release drills.")
    parser.add_argument(
        "--release",
        action="store_true",
        help="Run the formal browser, write, backup, and recovery release-candidate verifier.",
    )
    parser.add_argument("--github-output", type=Path, help="Append profile outputs for GitHub Actions.")
    parser.add_argument("--max-workers", type=int, default=4, help="Maximum parallel read-only checks.")
    parser.add_argument("--path", action="append", dest="paths", help="Classify an explicit path (repeatable).")
    args = parser.parse_args()
    if args.ci and args.release:
        parser.error("--ci and --release cannot be used together")

    paths = tuple(args.paths) if args.paths else changed_paths(base=args.base, head=args.head, staged=args.staged)
    auto_plan = classify_paths(paths)
    try:
        plan = select_profile(auto_plan, args.profile)
    except ValueError as error:
        parser.error(str(error))
    tasks = build_tasks(
        plan,
        paths,
        ci=args.ci,
        release=args.release,
        base=args.base,
        head=args.head,
        staged=args.staged,
    )
    _print_plan(
        plan,
        tasks,
        ci=args.ci,
        release=args.release,
        staged=args.staged,
    )
    if args.github_output:
        _write_github_output(args.github_output, plan)
    if args.plan:
        return 0
    if args.max_workers < 1:
        parser.error("--max-workers must be at least 1")

    results = execute_tasks(tasks, max_workers=args.max_workers)
    for result in results:
        print(f"[{result.status.upper()}] {result.name} ({result.duration_ms} ms)")
        if result.status == "fail" and result.output:
            print(result.output)
    _write_report(
        plan,
        results,
        ci=args.ci,
        release=args.release,
        staged=args.staged,
    )
    if all(result.status == "pass" for result in results):
        print(f"Verification passed. Report: {REPORT_PATH}")
        return 0
    print(f"Verification failed. Report: {REPORT_PATH}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
