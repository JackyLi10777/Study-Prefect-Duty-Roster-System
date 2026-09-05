"""Execute the real generated download JS with deterministic local browser doubles."""
import json
import shutil
import subprocess

import pytest

from nicegui_app.ui.downloads import DownloadFailureTarget, single_use_download_script


@pytest.mark.parametrize("outcome", ["http", "mime", "network", "success"])
@pytest.mark.parametrize("state", ["active", "closed", "reopened", "options_aba", "default"])
def test_download_feedback_is_scoped_to_exact_open_generation(outcome, state):
    node = shutil.which("node")
    assert node, "Node is required to execute the download browser contract"
    target = None if state == "default" else DownloadFailureTarget('status-"<fixture>', "2")
    script = single_use_download_script(
        "/api/generated-download/" + "A" * 43, "fictional.png", "Please prepare again",
        expected_media_type="image/png", failure_target=target,
    )
    harness = r"""
const assert = require('node:assert/strict');
const options = JSON.parse(process.argv[2]);
const notices = [], clicked = [];
const dialog = {open: true};
const label = {dataset: {exportGeneration: '2'}, textContent: 'new view',
    closest: () => dialog, setAttribute(name, value) { this[name] = value; },
    scrollIntoView() { this.scrolled = true; }};
global.document = {
    body: {dataset: {}, appendChild() {}}, getElementById: () => label,
    createElement: () => ({style: {}, click: () => clicked.push(true), remove() {}}),
};
global.window = {Quasar: {Notify: {create: item => notices.push(item)}},
    alert: message => notices.push(message), setTimeout: fn => fn()};
global.URL = {createObjectURL: () => 'blob:fictional', revokeObjectURL() {}};
global.fetch = async (_url, request) => {
    assert.equal(request.method, undefined); // Existing GET transport retained.
    assert.equal(request.credentials, 'same-origin');
    if (options.state === 'closed') dialog.open = false;
    if (options.state === 'reopened') { dialog.open = false; dialog.open = true; label.dataset.exportGeneration = '4'; }
    if (options.state === 'options_aba') { label.dataset.exportGeneration = '3'; label.dataset.exportGeneration = '4'; }
    if (options.outcome === 'network') throw new Error('synthetic network failure');
    return {ok: options.outcome !== 'http', status: 410,
        headers: {get: name => name === 'Content-Type' ? (options.outcome === 'mime' ? 'text/html' : 'image/png') : 'REQ-FIXTURE'},
        json: async () => ({reference: 'REQ-FIXTURE'}), blob: async () => ({size: 8})};
};
(async () => {
    await eval(options.script);
    const active = ['active', 'default'].includes(options.state);
    assert.equal(clicked.length, active && options.outcome === 'success' ? 1 : 0);
    if (!active) {
        assert.equal(label.textContent, 'new view');
        assert.deepEqual(document.body.dataset, {});
        assert.equal(notices.length, 0);
    } else if (options.outcome !== 'success' && options.state !== 'default') {
        assert.equal(label.role, 'alert');
        assert.equal(label['aria-live'], 'assertive');
        assert.equal(label['aria-busy'], 'false');
        assert.ok(label.textContent.startsWith('Please prepare again'));
        assert.ok(!label.textContent.includes('synthetic network failure'));
        assert.equal(notices.length, 0);
        assert.ok(label.scrolled);
    } else if (options.state === 'default' && options.outcome !== 'success') {
        assert.equal(notices.length, 1);
        assert.equal(label.textContent, 'new view');
    }
})().catch(error => { process.stderr.write(String(error)); process.exitCode = 1; });
"""
    completed = subprocess.run(
        [node, "-", json.dumps({"script": script, "outcome": outcome, "state": state})],
        input=harness, text=True, encoding="utf-8", capture_output=True, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
