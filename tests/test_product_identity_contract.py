from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

from nicegui_app.config import (
    DISPLAY_PRINT_CREST_PATH,
    DISPLAY_WEB_CREST_PATH,
    FAVICON_CREST_PATH,
    NAVIGATION_CREST_PATH,
    SERVICE_WEAVE_FAVICON_PATH,
    SERVICE_WEAVE_NAVIGATION_DARK_PATH,
    SERVICE_WEAVE_NAVIGATION_LIGHT_PATH,
    SERVICE_WEAVE_WINDOWS_ICON_PATH,
)
from nicegui_app.ui.product_identity import (
    PRODUCT_IDENTITY,
    SOURCE_PATH,
    load_product_identity,
    product_identity_drift,
)


def test_product_identity_exposes_bilingual_names_and_accessible_labels() -> None:
    identity = load_product_identity()

    assert identity is PRODUCT_IDENTITY
    assert identity.product_name_zh == "服事經緯"
    assert identity.product_name_en == "Service Weave"
    assert identity.functional_name_zh == "聖言中學導學風紀值班表生成系統"
    assert identity.functional_name_en == "Sing Yin Study Prefect Duty Roster System"
    assert identity.accessible_name("productMark", "zh-HK") == "服事經緯軟件標誌"
    assert identity.accessible_name("productMark", "en") == "Service Weave software mark"
    assert identity.accessible_name("institutionalCrest", "zh-HK") == "聖言中學校徽"
    assert identity.accessible_name("institutionalCrest", "en") == "Sing Yin Secondary School crest"
    assert identity.asset_version == "v1"
    assert len(identity.digest) == 64


def test_product_identity_binds_runtime_assets_to_the_versioned_manifest() -> None:
    identity = load_product_identity()
    expected_product_paths = {
        SERVICE_WEAVE_FAVICON_PATH,
        SERVICE_WEAVE_NAVIGATION_LIGHT_PATH,
        SERVICE_WEAVE_NAVIGATION_DARK_PATH,
        SERVICE_WEAVE_WINDOWS_ICON_PATH,
    }
    actual_product_paths = {asset.path for asset in identity.product_mark_variants}
    assert expected_product_paths <= actual_product_paths

    expected_crest_paths = {
        FAVICON_CREST_PATH,
        NAVIGATION_CREST_PATH,
        DISPLAY_WEB_CREST_PATH,
        DISPLAY_PRINT_CREST_PATH,
    }
    assert {asset.path for asset in identity.institutional_crest_variants} == expected_crest_paths

    for asset in (*identity.product_mark_variants, *identity.institutional_crest_variants):
        assert asset.path.is_file()
        assert hashlib.sha256(asset.path.read_bytes()).hexdigest() == asset.sha256


def test_product_identity_contract_has_no_worker_delivery_drift() -> None:
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    assert source["contractVersion"] == "1.0.0"
    assert source["delivery"]["faviconVariant"] == "favicon"
    assert product_identity_drift() == []


def test_browser_release_verifier_uses_the_manifest_selected_product_favicon() -> None:
    verifier = (
        SOURCE_PATH.parents[1] / "scripts" / "verify_nicegui_ui.py"
    ).read_text(encoding="utf-8")

    assert "from nicegui_app.ui.product_identity import PRODUCT_IDENTITY" in verifier
    assert 'PRODUCT_IDENTITY.delivery["faviconVariant"]' in verifier
    assert "FAVICON_PRODUCT_PATH.read_bytes()" in verifier
    assert "FAVICON_CREST_PATH" not in verifier
    assert 'page.get_by_test_id("navigation-product-mark")' in verifier
    assert "NAVIGATION_PRODUCT_ASSETS.items()" in verifier
    assert 'page.locator(".sy-brand-mark")' not in verifier


def test_browser_release_verifier_bootstraps_the_project_when_run_by_path(tmp_path: Path) -> None:
    verifier_path = SOURCE_PATH.parents[1] / "scripts" / "verify_nicegui_ui.py"
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            (
                "import runpy; "
                f"runpy.run_path({str(verifier_path)!r}, run_name='verify_nicegui_ui_import_check')"
            ),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
