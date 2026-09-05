"""Exercise first-use mounting and the existing browser appearance runtime."""
import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from nicegui_app.access_context import AccessMode
from nicegui_app.ui import shell


class Element:
    def __init__(self):
        self.id = 42
        self.events = {}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def classes(self, *_):
        return self

    def props(self, *_):
        return self

    def on_value_change(self, callback):
        self.events["value"] = callback
        return self

    def on(self, event, callback=None, **kwargs):
        self.events[event] = kwargs.get("js_handler", callback)
        return self


@pytest.mark.parametrize("mode", [AccessMode.ADMIN, AccessMode.GUEST, AccessMode.LOCAL_MAINTENANCE])
def test_preferences_mount_only_on_first_expansion_with_current_values(monkeypatch, mode):
    expansion = Element()
    scripts, rendered = [], []
    ui = SimpleNamespace(element=lambda *_: Element(), label=lambda *_: Element(),
                         expansion=lambda *_, **__: expansion, run_javascript=scripts.append)
    monkeypatch.setattr(shell, "ui", ui)
    state = {"sound": False, "locale": "zh-HK", "theme": "light"}
    monkeypatch.setattr(shell, "t", lambda key: key)
    monkeypatch.setattr(shell, "language_switch_copy", lambda **_: ("Language", "Switch language"))
    monkeypatch.setattr(shell, "current_locale", lambda: state["locale"])
    monkeypatch.setattr(shell, "sound_feedback_enabled", lambda: state["sound"])
    monkeypatch.setattr(shell, "current_theme", lambda: state["theme"])
    monkeypatch.setattr(shell, "theme_preference", lambda: state["theme"])
    monkeypatch.setattr(shell, "current_page_context", lambda: SimpleNamespace(principal=SimpleNamespace(mode=mode)))

    def tile(**kwargs):
        rendered.append(kwargs)
        return SimpleNamespace(button=Element(), value_label=Element())

    monkeypatch.setattr(shell, "_render_mobile_setting_tile", tile)
    theme_controls, sound_controls = {"buttons": [], "busy": False}, []
    shell._render_mobile_drawer_tools(object(), theme_controls, sound_controls)
    assert rendered == [] and theme_controls["buttons"] == [] and sound_controls == []
    expansion.events["value"](SimpleNamespace(value=False))
    assert rendered == []
    state.update(sound=True, locale="en", theme="dark")
    for _ in range(20):
        expansion.events["value"](SimpleNamespace(value=True))
        expansion.events["value"](SimpleNamespace(value=False))
    expected_kinds = ["language", "sound", "theme"]
    if mode in {AccessMode.ADMIN, AccessMode.GUEST}:
        expected_kinds.append("account")
    assert [item["kind"] for item in rendered] == expected_kinds
    assert rendered[0]["value"] == "mobile_setting_value_english"
    assert rendered[1]["pressed"] is True
    assert rendered[2]["value"] == "mobile_theme_dark"
    if mode in {AccessMode.ADMIN, AccessMode.GUEST}:
        assert rendered[3]["value"] == f"mobile_setting_account_{mode.value}"
    assert len(theme_controls["buttons"]) == len(sound_controls) == 1
    assert len(scripts) == 1 and "__syThemeControls" in scripts[0]
    assert "before-hide" in expansion.events


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_late_mobile_theme_control_cannot_override_existing_header_choice(monkeypatch, theme):
    scripts = []
    monkeypatch.setattr(shell, "ui", SimpleNamespace(run_javascript=scripts.append))
    shell._install_theme_control_runtime()
    node = shutil.which("node")
    assert node, "Node is required to execute the appearance runtime contract"
    harness = r"""
const assert = require('node:assert/strict');
const input = JSON.parse(process.argv[2]);
const makeButton = preference => ({dataset: {themePreference:preference, actionLight:'Light', actionDark:'Dark',
    stateLight:'LIGHT', stateDark:'DARK'}, attrs:{}, state:{textContent:''}, icon:{textContent:''},
    setAttribute(k,v){this.attrs[k]=v;}, removeAttribute(k){delete this.attrs[k];},
    querySelector(s){return s === '.q-icon' ? this.icon : s === '[data-sy-theme-state]' ? this.state : null;}});
const header = makeButton('system');
let buttons = [header];
global.document = {body:{style:{setProperty(){}}}, documentElement:{dataset:{}},
    querySelectorAll:()=>buttons,
    querySelector:s=>s === '[data-testid="theme-control"]' ? header : null};
global.window = {Quasar:{Dark:{set(){}}}};
global.matchMedia = ()=>({matches:false,addEventListener(){}});
global.MutationObserver = class {observe(){} disconnect(){}};
global.BroadcastChannel = class {postMessage(){} addEventListener(){} close(){}};
global.requestAnimationFrame = ()=>1;
global.cancelAnimationFrame = ()=>{};
eval(input.script);
window.__syThemeControls.applyExplicit(input.theme, {animate:false});
const mobile = makeButton(input.theme === 'dark' ? 'light' : 'dark');
buttons = [mobile, header]; // Drawer precedes the already-mounted header in DOM.
window.__syThemeControls.sync({animate:false});
assert.equal(window.__syThemeControls.resolved(), input.theme);
assert.equal(mobile.dataset.themePreference, input.theme);
assert.equal(mobile.dataset.themeResolved, input.theme);
assert.equal(mobile.state.textContent, input.theme.toUpperCase());
window.__syThemeControlsCleanup();
"""
    result = subprocess.run([node, "-", json.dumps({"script": scripts[0], "theme": theme})],
                            input=harness, text=True, encoding="utf-8", capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
