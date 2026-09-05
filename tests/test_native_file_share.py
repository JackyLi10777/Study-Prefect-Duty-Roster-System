from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from nicegui_app.ui.native_file_share import (
    MAX_NATIVE_SHARE_BYTES,
    build_native_file_share_from_data_url_js,
    build_native_file_share_js,
    can_offer_native_file_share,
)


@pytest.mark.parametrize("media_type", ["application/pdf", "image/png"])
def test_native_file_share_accepts_only_bounded_roster_exports(media_type: str) -> None:
    signature = b"%PDF-" if media_type == "application/pdf" else b"\x89PNG\r\n\x1a\n"
    content = signature + b"generated"
    assert can_offer_native_file_share(content, media_type=media_type)
    assert not can_offer_native_file_share(b"", media_type=media_type)
    assert not can_offer_native_file_share(
        signature + b"x" * MAX_NATIVE_SHARE_BYTES,
        media_type=media_type,
    )
    assert not can_offer_native_file_share(b"wrong signature", media_type=media_type)


@pytest.mark.parametrize(
    "media_type",
    ["image/jpeg", "image/svg+xml", "text/html", "application/octet-stream", "image/png; charset=utf-8"],
)
def test_native_file_share_rejects_media_types_outside_exact_allowlist(media_type: str) -> None:
    assert not can_offer_native_file_share(b"generated", media_type=media_type)
    with pytest.raises(ValueError):
        build_native_file_share_js(
            content=b"generated",
            filename="unsafe.file",
            media_type=media_type,
            title="Title",
            text="Text",
        )


def test_native_png_share_bridge_is_direct_click_json_safe_and_base64_safe() -> None:
    script = build_native_file_share_js(
        content=b"\x89PNG\r\n\x1a\n\x00\xff",
        filename='SYSS_Roster_20260907_v2_Avatar_"ZH".png',
        media_type="image/png",
        title="聖言中學導學風紀值班表 </script>",
        text="請查看最新版本。\n第二行",
    )

    assert "navigator.canShare({files: [file]})" in script
    assert "await navigator.share({files: [file]" in script
    assert "new File([bytes], metadata.filename, {type: metadata.mediaType})" in script
    assert '"mediaType":"image/png"' in script
    assert "AbortError" in script
    assert "report('unsupported')" in script
    assert "wa.me" not in script
    assert '\\"ZH\\"' in script
    assert "\x00" not in script
    assert "</script>" not in script
    assert "\\u003c/script\\u003e" in script


def test_preview_backed_native_share_keeps_file_bytes_out_of_compiled_handler() -> None:
    script = build_native_file_share_from_data_url_js(
        preview_selector='[data-testid="roster-whatsapp-preview"]',
        filename='SYSS_Roster_20260907_v2_WhatsApp_"ZH".png',
        media_type="image/png",
        title="聖言中學導學風紀值班表 </script>",
        text="請查看最新版本。",
    )

    assert "document.querySelector(metadata.previewSelector)" in script
    assert "image?.getAttribute('src')" in script
    assert "const binary = atob(source.slice(prefix.length))" in script
    assert "new File([bytes], resolvedFilename, {type: metadata.mediaType})" in script
    assert "await navigator.share({files: [file]" in script
    assert str(MAX_NATIVE_SHARE_BYTES) in script
    assert "137,80,78,71,13,10,26,10" in script
    assert "iVBOR" not in script
    assert "</script>" not in script
    assert "\\u003c/script\\u003e" in script

    dynamic_filename_script = build_native_file_share_from_data_url_js(
        preview_selector="#preview",
        filename_selector="#filename",
        media_type="image/png",
        title="Title",
        text="Text",
    )
    assert "document.querySelector(metadata.filenameSelector)" in dynamic_filename_script
    assert '"filenameSelector":"#filename"' in dynamic_filename_script


def test_preview_backed_native_share_rejects_an_unsafe_contract() -> None:
    with pytest.raises(ValueError, match="unsupported media type"):
        build_native_file_share_from_data_url_js(
            preview_selector="#preview",
            filename="unsafe.svg",
            media_type="image/svg+xml",
            title="Title",
            text="Text",
        )
    with pytest.raises(ValueError, match="selector"):
        build_native_file_share_from_data_url_js(
            preview_selector="  ",
            filename="roster.png",
            media_type="image/png",
            title="Title",
            text="Text",
        )


@pytest.mark.parametrize("media_type", ["application/pdf", "image/png"])
@pytest.mark.parametrize("result", ["shared", "cancelled", "failed"])
def test_native_share_promise_reports_its_start_token_when_results_arrive_backwards(media_type, result):
    deno = shutil.which("deno")
    if deno is None:
        pytest.skip("Deno is required to execute the browser share bridge")
    if media_type == "application/pdf":
        scripts = [build_native_file_share_js(
            content=b"%PDF-fixture", filename="fixture.pdf", media_type=media_type,
            title="Fixture", text="Fixture", result_token=token,
        ) for token in ["old", "new"]]
    else:
        script = build_native_file_share_from_data_url_js(
            preview_selector="#preview", filename="fixture.png", media_type=media_type,
            title="Fixture", text="Fixture", result_token_selector="#preview",
        )
        scripts = [script, script]
    scenario = f"""
      const scripts = {json.dumps(scripts)};
      const result = {json.dumps(result)};
      const pending = [];
      const events = [];
      let token = 'old';
      const navigator = {{canShare: () => true, share: () => new Promise((resolve, reject) => pending.push({{resolve, reject}}))}};
      const image = {{matches: () => true, getAttribute: name => name === 'data-share-token' ? token : 'data:image/png;base64,iVBORw0KGgpmaXh0dXJl'}};
      const document = {{querySelector: () => image}};
      const handler = source => new Function('navigator', 'document', 'emit', 'return (' + source + ')')(navigator, document, event => events.push(event));
      const oldRequest = handler(scripts[0])();
      token = 'new';
      const newRequest = handler(scripts[1])();
      if (pending.length !== 2) throw new Error('share must start synchronously in each click');
      const finish = request => result === 'shared' ? request.resolve() : request.reject(Object.assign(new Error('fixture'), {{name: result === 'cancelled' ? 'AbortError' : 'Error'}}));
      finish(pending[1]);
      await newRequest;
      finish(pending[0]);
      await oldRequest;
      if (JSON.stringify(events) !== JSON.stringify([{{status: result, token: 'new'}}, {{status: result, token: 'old'}}])) throw new Error(JSON.stringify(events));
    """
    completed = subprocess.run([deno, "eval", scenario], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stdout + completed.stderr


@pytest.mark.parametrize("media_type", ["application/pdf", "image/png"])
@pytest.mark.parametrize("expired", [False, True])
def test_confirm_gesture_checks_browser_lease_synchronously_and_is_single_use(media_type, expired):
    deno = shutil.which("deno")
    if deno is None:
        pytest.skip("Deno is required to execute the browser share bridge")
    common = dict(media_type=media_type, title="Fixture", text="Fixture", lease_token="lease-fixture", lease_expires_at=15000)
    script = (build_native_file_share_js(content=b"%PDF-fixture", filename="fixture.pdf", result_token="2", **common)
              if media_type == "application/pdf" else build_native_file_share_from_data_url_js(
                  preview_selector="#preview", filename="fixture.png", result_token_selector="#preview", **common))
    scenario = f"""
      const source = {json.dumps(script)};
      const expired = {json.dumps(expired)};
      const events = [];
      let calls = 0;
      let reject;
      const navigator = {{canShare: () => true, share: () => {{calls += 1; return new Promise((resolve, fail) => reject = fail);}}}};
      const image = {{matches: () => true, getAttribute: name => name === 'data-share-token' ? '2' : 'data:image/png;base64,iVBORw0KGgpmaXh0dXJl'}};
      const document = {{querySelector: () => image}};
      const performance = {{now: () => expired ? 15000 : 14000}};
      const handler = new Function('navigator', 'document', 'performance', 'emit', 'return (' + source + ')')(navigator, document, performance, event => events.push(event));
      const button = {{disabled:false}};
      const pending = handler({{currentTarget:button}});
      if (calls !== (expired ? 0 : 1)) throw new Error('native sharing must start in the second gesture only and before awaiting');
      if (!expired) {{
        if (!button.disabled) throw new Error('confirmation must become single use');
        reject(Object.assign(new Error('fixture'), {{name:'AbortError'}}));
      }}
      await pending;
      await handler({{currentTarget:button}});
      if (calls !== (expired ? 0 : 1)) throw new Error('a lease may not be replayed');
      const expected = expired ? ['expired','expired'] : ['started','cancelled','expired'];
      if (JSON.stringify(events.map(event=>event.status)) !== JSON.stringify(expected)) throw new Error(JSON.stringify(events));
      if (!events.every(event=>event.token==='2' && event.lease==='lease-fixture')) throw new Error('uncorrelated lease result');
    """
    completed = subprocess.run([deno, "eval", scenario], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stdout + completed.stderr
