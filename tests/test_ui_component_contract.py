from __future__ import annotations

import ast
from itertools import combinations
from pathlib import Path
import re

import tinycss2
import pytest

from nicegui_app.ui.theme_markup import STYLE_LAYERS, THEME_HEAD_HTML
from nicegui_app.ui.i18n import EN, MESSAGES, ZH_HK
from nicegui_app.ui.components import action, dialog


PROJECT_ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = PROJECT_ROOT / "nicegui_app" / "ui"
CSS_ROOT = PROJECT_ROOT / "nicegui_app" / "assets" / "css"
COMPOSITION_LAYERS = {"command-center-v2"}


def test_disabled_action_uses_nicegui_event_gating_not_only_a_visual_prop() -> None:
    button = action("Unavailable", disabled=True)
    try:
        assert button.enabled is False
        assert button._props["disable"] is True
        assert button._props["aria-disabled"] == "true"
        button.enable()
        assert button.enabled is True
        assert button._props["disable"] is False
    finally:
        button.delete()


@pytest.mark.parametrize("presentation", ["modal", "sheet", "alert", "status"])
def test_semantic_dialogs_bind_unique_accessible_names_and_descriptions(presentation):
    with dialog(title="Fictional confirmation", description="Review this fictional action",
                presentation=presentation) as first:
        with dialog(title="Second confirmation", description="Second description",
                    presentation=presentation) as second:
            try:
                assert first._props["aria-labelledby"] != second._props["aria-labelledby"]
                assert first._props["aria-describedby"] != second._props["aria-describedby"]
                assert first._props["role"] == ("alertdialog" if presentation == "alert" else "dialog")
                if presentation == "status":
                    assert first._props["persistent"] is True
            finally:
                second.delete()
                first.delete()


EXPECTED_COMPONENT_API = {
    "ActionVariant",
    "MotionPatternName",
    "StatusTone",
    "WorkflowState",
    "action",
    "code_sample",
    "dialog",
    "editorial_heading",
    "empty_state",
    "field",
    "motion_pattern",
    "native_dialog",
    "page_toc",
    "progress_state",
    "reference_pager",
    "responsive_table",
    "restricted_state",
    "status",
    "workflow_step",
}


def _selectors(path: Path) -> set[str]:
    selectors: set[str] = set()

    def split_selector_list(tokens: list[object]) -> list[str]:
        current: list[object] = []
        values: list[str] = []
        for token in tokens:
            if getattr(token, "type", "") == "literal" and getattr(token, "value", "") == ",":
                value = tinycss2.serialize(current).strip()
                if value:
                    values.append(value)
                current = []
            else:
                current.append(token)
        value = tinycss2.serialize(current).strip()
        if value:
            values.append(value)
        return values

    def walk(rules: list[object], *, inside_keyframes: bool = False) -> None:
        for rule in rules:
            if getattr(rule, "type", "") == "qualified-rule" and not inside_keyframes:
                selectors.update(split_selector_list(rule.prelude))
            elif getattr(rule, "type", "") == "at-rule" and rule.content is not None:
                keyword = str(getattr(rule, "lower_at_keyword", ""))
                walk(
                    tinycss2.parse_rule_list(rule.content, skip_whitespace=True, skip_comments=True),
                    inside_keyframes=inside_keyframes or keyword.endswith("keyframes"),
                )

    walk(
        tinycss2.parse_stylesheet(
            path.read_text(encoding="utf-8"),
            skip_whitespace=True,
            skip_comments=True,
        )
    )
    return selectors


def test_public_component_module_has_literal_stable_api() -> None:
    path = UI_ROOT / "components.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets)
    )
    assert set(ast.literal_eval(assignment.value)) == EXPECTED_COMPONENT_API


def test_stylesheets_load_in_the_declared_ownership_order() -> None:
    assert [layer for layer, _href, _media in STYLE_LAYERS] == [
        "tokens",
        "base",
        "layout",
        "compatibility-theme",
        "compatibility-material",
        "components",
        "narrative",
        "compatibility-interaction",
        "motion",
        "mobile",
        "command-center-v2",
    ]
    positions = [THEME_HEAD_HTML.index(href) for _layer, href, _media in STYLE_LAYERS]
    assert positions == sorted(positions)
    for layer, href, _media in STYLE_LAYERS:
        assert f'data-sy-style-layer="{layer}"' in THEME_HEAD_HTML
        assert (PROJECT_ROOT / "nicegui_app" / href.removeprefix("/")).is_file()
    assert 'src="/assets/runtime/music/sing-yin-music-controller.js"' in THEME_HEAD_HTML
    assert 'data-sy-runtime="music-controller"' in THEME_HEAD_HTML
    assert (
        PROJECT_ROOT
        / "nicegui_app"
        / "assets"
        / "music"
        / "sing-yin-music-controller.js"
    ).is_file()


def test_non_mobile_layers_never_reown_exact_selectors() -> None:
    layer_selectors = {
        layer: _selectors(PROJECT_ROOT / "nicegui_app" / href.removeprefix("/"))
        for layer, href, _media in STYLE_LAYERS
        if layer not in {"tokens", "mobile", *COMPOSITION_LAYERS}
    }
    for (left_name, left), (right_name, right) in combinations(layer_selectors.items(), 2):
        overlap = left & right
        assert not overlap, f"{left_name} and {right_name} both own: {sorted(overlap)}"


def test_frontend_reset_has_one_explicit_terminal_composition_layer() -> None:
    composition = [layer for layer, _href, _media in STYLE_LAYERS if layer in COMPOSITION_LAYERS]
    assert composition == ["command-center-v2"]
    assert STYLE_LAYERS[-1][0] == "command-center-v2"

    source = (CSS_ROOT / "sing-yin-command-center-v2.css").read_text(encoding="utf-8")
    assert "final composition layer" in source
    assert "deliberately does not redeclare generated design-token names" in source

    declared_properties = set(re.findall(r"(?m)^\s*(--sy-[\w-]+)\s*:", source))
    runtime_viewport_properties = {
        "--sy-visual-viewport-width",
        "--sy-visual-viewport-offset-left",
        "--sy-visual-viewport-bottom-inset",
    }
    unexpected = {
        name
        for name in declared_properties
        if not name.startswith("--sy-v2-") and name not in runtime_viewport_properties
    }
    assert not unexpected, f"terminal composition layer redeclared managed tokens: {sorted(unexpected)}"

    shell_source = (UI_ROOT / "shell.py").read_text(encoding="utf-8")
    shell_tree = ast.parse(shell_source)
    drawer_width = next(
        ast.literal_eval(node.value)
        for node in shell_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "DESKTOP_DRAWER_WIDTH_PX"
            for target in node.targets
        )
    )
    css_width = re.search(r"--sy-v2-rail-width:\s*(\d+)px", source)
    assert css_width is not None
    assert drawer_width == int(css_width.group(1)) == 264
    assert "width={DESKTOP_DRAWER_WIDTH_PX}" in shell_source
    assert "calc(var(--sy-v2-rail-width) + var(--sy-v2-content-gutter))" in source

    brand_mark = re.search(
        r"\.sy-brand-lockup \.sy-product-mark\s*\{(?P<body>.*?)\}",
        source,
        flags=re.DOTALL,
    )
    assert brand_mark is not None
    mark_width = re.search(r"width:\s*(\d+)px", brand_mark.group("body"))
    mark_height = re.search(r"height:\s*(\d+)px", brand_mark.group("body"))
    assert mark_width is not None and int(mark_width.group(1)) >= 58
    assert mark_height is not None and int(mark_height.group(1)) >= 58

    history_action = re.search(
        r"\.sy-dashboard-history-action\s*\{(?P<body>.*?)\}",
        source,
        flags=re.DOTALL,
    )
    assert history_action is not None
    assert "min-height: 44px !important" in history_action.group("body")


def test_status_badge_surface_is_owned_by_the_component_layer() -> None:
    component_source = (CSS_ROOT / "sing-yin-components-v1.css").read_text(encoding="utf-8")
    compatibility_source = (CSS_ROOT / "sing-yin-theme-v1.css").read_text(encoding="utf-8")

    assert ".sy-status-badge {" in component_source
    assert ".sy-status-badge { width:" not in compatibility_source


def test_luminous_material_roles_are_connected_to_governed_surfaces() -> None:
    theme = (CSS_ROOT / "sing-yin-theme-v1.css").read_text(encoding="utf-8")
    layout = (CSS_ROOT / "sing-yin-layout-v1.css").read_text(encoding="utf-8")
    components = (CSS_ROOT / "sing-yin-components-v1.css").read_text(encoding="utf-8")

    assert ".sy-header-tools" in theme
    assert "var(--sy-material-transient)" in theme
    assert "var(--sy-luminous-edge)" in theme
    assert ".sy-workflow-navigation" in layout
    assert "var(--sy-material-transient)" in layout
    assert "var(--sy-material-operational)" in layout
    assert "var(--sy-woven-line)" in layout
    assert ".sy-dialog" in components
    assert "var(--sy-material-transient)" in components
    assert "var(--sy-luminous-edge)" in components


def test_public_components_cover_complete_interaction_states() -> None:
    source = (UI_ROOT / "components.py").read_text(encoding="utf-8")
    for variant in ("primary", "secondary", "quiet", "attention", "danger"):
        assert f'"{variant}"' in source
    for state in ("busy", "disabled", "aria-busy=true", "aria-disabled=true", "aria-invalid=true"):
        assert state in source
    for component in (
        "def action(",
        "def field(",
        "def status(",
        "def dialog(",
        "def empty_state(",
        "def restricted_state(",
        "def progress_state(",
        "def responsive_table(",
        "def workflow_step(",
        "def editorial_heading(",
        "def page_toc(",
        "def reference_pager(",
        "def code_sample(",
    ):
        assert component in source
    assert "navigator.clipboard?.writeText" in source
    assert "window.prompt" in source
    assert "copy_failed_manual" in source


def test_progress_component_distinguishes_indeterminate_and_measured_work() -> None:
    source = (UI_ROOT / "components.py").read_text(encoding="utf-8")
    progress = source.split("def progress_state(", 1)[1].split("def responsive_table(", 1)[0]

    assert "if value is None:" in progress
    assert "indeterminate color=primary aria-label=" in progress
    assert "aria-valuenow" not in progress.split("else:", 1)[0]
    assert "bounded_value = max(0.0, min(1.0, value))" in progress
    assert "aria-valuemin=0 aria-valuemax=100" in progress


def test_shared_action_accepts_semantic_icon_metadata_without_page_timelines() -> None:
    source = (UI_ROOT / "components.py").read_text(encoding="utf-8")
    support = (UI_ROOT / "page_routes" / "support.py").read_text(encoding="utf-8")

    assert 'IconStoryCategory = Literal["preview", "persistent", "lifecycle", "role", "static"]' in source
    for argument in ("motion_role:", "icon_story_to:", "icon_story_category:"):
        assert argument in source
    for attribute in (
        "data-sy-icon-motion-role",
        "data-sy-icon-story-to",
        "data-sy-icon-story-category",
    ):
        assert attribute in source
    assert 'icon_story_to="forward_to_inbox"' in support
    assert "gsap" not in support.lower()


def test_legacy_page_helpers_delegate_to_the_public_component_contract() -> None:
    source = (UI_ROOT / "page_shared.py").read_text(encoding="utf-8")

    assert "return render_status_component(text, tone, props=props)" in source
    assert "render_responsive_table_component(" in source
    assert "render_workflow_step_component(" in source
    assert "render_empty_state_component(" in source
    assert "action_test_id=action_test_id" in source
    assert "emit_interface_feedback" in source


def test_motion_runtime_owns_toc_disclosure_and_cleanup() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(
        encoding="utf-8"
    )
    assert "tocObservers" in source
    assert "aria-current', 'location'" in source
    assert "disclosureHandler" in source
    assert "Array.from(tocObservers.keys()).forEach(removeToc)" in source
    assert "prefers-reduced-motion" in source


def test_motion_runtime_rebuilds_toc_observers_after_dom_replacement() -> None:
    source = (PROJECT_ROOT / "nicegui_app" / "assets" / "motion" / "sing-yin-motion.js").read_text(
        encoding="utf-8"
    )

    assert "if (tocObservers.has(nav)) removeToc(nav);" in source
    assert "tocObservers.get(nav)?.observer.disconnect();" in source
    assert "existing.links.every((link, index) => link.isConnected && link === links[index])" in source
    assert "existing.targets.every((target, index) => target.isConnected && target === targets[index])" in source
    assert "if (existing || nav.dataset.syTocReady === 'true') removeToc(nav);" in source
    assert "tocObservers.set(nav, { observer, links, targets });" in source


def test_showcase_exposes_filterable_evidence_and_real_developer_reference() -> None:
    source = (UI_ROOT / "page_routes" / "showcase.py").read_text(encoding="utf-8")

    assert 'data-testid=engineering-evidence-index' in source
    assert 'data-testid=engineering-evidence-results' in source
    assert 'test_id="engineering-evidence-table"' in source
    assert "for control in (type_filter, state_filter, date_filter, view_filter)" in source
    assert "empty_state(" in source
    assert "responsive_table(" in source
    assert '("architecture-developer-section", "developer_reference_title")' in source
    assert "code_sample(" in source
    assert "http://127.0.0.1:8080/healthz" in source
    assert "http://127.0.0.1:8080/readyz" in source
    assert "scripts/verify_release_candidate.py" in source

    for key in (
        "engineering_evidence_title",
        "engineering_evidence_type",
        "engineering_evidence_status",
        "engineering_evidence_date",
        "engineering_evidence_view",
        "engineering_evidence_no_results",
        "developer_reference_title",
        "developer_reference_modules_title",
        "developer_reference_context_title",
        "developer_reference_adapters_title",
        "developer_reference_identity_title",
        "developer_reference_lifecycle_title",
        "developer_reference_health_title",
        "developer_reference_recovery_title",
        "developer_reference_release_title",
        "developer_reference_health_command",
        "developer_reference_release_command",
    ):
        assert MESSAGES[key][ZH_HK].strip(), key
        assert MESSAGES[key][EN].strip(), key
