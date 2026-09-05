// Execute the actual injected browser script with a deterministic clock.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const {script, scenario, mode} = JSON.parse(fs.readFileSync(0, 'utf8'));
const epoch = 1800000000000;
const expiry = epoch / 1000 + 3600;
const settle = () => new Promise(resolve => setImmediate(resolve));

function harness(visible = true) {
  let now = epoch;
  let nextTimer = 0;
  const timers = new Map();
  const calls = [];
  const channels = [];
  const redirects = [];
  const pending = [];
  const storage = new Map([['fictional-draft', 'unsaved']]);
  const elements = new Map();
  const eventSource = () => {
    const listeners = new Map();
    return {
      addEventListener(type, listener, options = {}) {
        if (!listeners.has(type)) listeners.set(type, new Map());
        listeners.get(type).set(listener, options);
      },
      removeEventListener(type, listener) { listeners.get(type)?.delete(listener); },
      emit(type, event = {}) {
        for (const [listener, options] of [...(listeners.get(type) || [])]) {
          if (options.once) listeners.get(type).delete(listener);
          listener(event);
        }
      },
      listenerCount() {
        return [...listeners.values()].reduce((sum, values) => sum + values.size, 0);
      },
    };
  };
  const element = () => ({
    ...eventSource(), dataset: {}, attributes: new Map(),
    setAttribute(name, value) { this.attributes.set(name, value); },
    removeAttribute(name) { this.attributes.delete(name); },
    hasAttribute(name) { return this.attributes.has(name); },
    focus() {},
    set innerHTML(value) {
      if (value.includes('sy-auth-exit-retry')) elements.set('sy-auth-exit-retry', element());
    },
    remove() {
      elements.delete(this.id);
      if (this.id === 'sy-auth-exit-state') elements.delete('sy-auth-exit-retry');
    },
  });
  elements.set('main-content', element());
  elements.set('sy-auth-exit-retry', element());
  const document = {
    ...eventSource(), visibilityState: visible ? 'visible' : 'hidden',
    body: {...element(), appendChild(value) { elements.set(value.id, value); }},
    getElementById(id) { return elements.get(id); },
    createElement() { return element(); },
    querySelectorAll() { return []; },
  };
  const setTimer = (callback, delay, repeat = 0) => {
    const id = ++nextTimer;
    timers.set(id, {callback, at: now + delay, repeat});
    return id;
  };
  const window = {
    ...eventSource(),
    setTimeout: (callback, delay) => setTimer(callback, delay),
    setInterval: (callback, delay) => setTimer(callback, delay, delay),
    location: {replace: value => redirects.push(value)},
    BroadcastChannel: function() {
      const channel = {...eventSource(), closed: false, postMessage() {}, close() { this.closed = true; }};
      channels.push(channel);
      return channel;
    },
  };
  const controls = {status: 200, authenticated: true, hold: false, holdJson: false, reject: false, logoutStatus: 200};
  const fetch = async (url, options) => {
    calls.push({url, options});
    if (url === '/auth/status') {
      if (controls.reject) throw new TypeError('fictional network unavailable');
      if (controls.hold) await new Promise(resolve => pending.push(resolve));
      return {
        status: controls.status, ok: controls.status === 200,
        json: async () => {
          if (controls.holdJson) await new Promise(resolve => pending.push(resolve));
          return {authenticated: controls.authenticated, mode, expiresAt: expiry};
        },
      };
    }
    return {ok: url !== '/auth/logout' || controls.logoutStatus === 200};
  };
  const context = vm.createContext({
    window, document, fetch, AbortController,
    Date: {now: () => now},
    Math, Number, JSON,
    sessionStorage: {clear: () => storage.clear()},
    BroadcastChannel: window.BroadcastChannel,
    setTimeout: window.setTimeout, setInterval: window.setInterval,
    clearTimeout: id => timers.delete(id), clearInterval: id => timers.delete(id),
  });
  return {
    window, document, timers, calls, channels, redirects, pending, storage, controls,
    install() { vm.runInContext(script, context, {timeout: 1000}); },
    statusCalls() { return calls.filter(call => call.url === '/auth/status').length; },
    async visibility(value) {
      document.visibilityState = value ? 'visible' : 'hidden';
      document.emit('visibilitychange');
      await settle();
    },
    async tick(milliseconds) {
      const end = now + milliseconds;
      let iterations = 0;
      while (true) {
        const next = [...timers].filter(([, timer]) => timer.at <= end)
          .sort((a, b) => a[1].at - b[1].at)[0];
        if (!next) break;
        assert(++iterations < 10000, 'timer loop failed to settle');
        const [id, timer] = next;
        now = timer.at;
        if (timer.repeat) timer.at += timer.repeat;
        else timers.delete(id);
        timer.callback();
        await settle();
      }
      now = end;
      await settle();
    },
  };
}

async function run() {
  const h = harness(scenario !== 'hidden' && scenario !== 'expiry');
  h.install();
  if (scenario === 'hidden') {
    await h.tick(180000);
    assert.equal(h.statusCalls(), 0, 'hidden tabs must not poll');
    assert.equal(h.timers.size, 1, 'only expiry remains scheduled');
    await h.visibility(true);
    assert.equal(h.statusCalls(), 1, 'returning to the page revalidates immediately');
    await h.tick(45000);
    assert.equal(h.statusCalls(), 2);
  } else if (scenario === 'visibility') {
    await h.tick(1200);
    assert.equal(h.statusCalls(), 1);
    for (let i = 0; i < 20; i++) {
      await h.visibility(false);
      const before = h.statusCalls();
      await h.tick(90000);
      assert.equal(h.statusCalls(), before);
      // Simultaneous focus and visibility events share the in-flight check.
      const resumed = h.visibility(true);
      h.window.emit('focus');
      await resumed;
      assert.equal(h.statusCalls(), before + 1);
      assert.equal(h.timers.size, 2, 'one poll timer plus expiry');
    }
    const before = h.statusCalls();
    h.window.emit('pageshow', {persisted: true});
    await settle();
    assert.equal(h.statusCalls(), before + 1);
    assert.equal(h.document.listenerCount(), 1);
    assert.equal(h.window.listenerCount(), 2);
  } else if (scenario === 'expiry') {
    await h.tick(3600000);
    assert.equal(h.statusCalls(), 0);
    assert.equal(h.storage.size, 0);
    assert.deepEqual(h.redirects, ['/']);
    assert.equal(h.calls.filter(call => call.url === '/auth/logout').length, 1);
    assert.equal(h.calls.filter(call => call.url === '/api/guest/downloads/cleanup').length, mode === 'guest' ? 1 : 0);
    assert.equal(h.timers.size, 0);
  } else if (scenario === 'revoked') {
    await h.visibility(false);
    h.controls.status = 403;
    await h.visibility(true);
    assert.deepEqual(h.redirects, ['/']);
    assert.equal(h.storage.size, 0);
    assert.equal(h.timers.size, 0);
  } else if (scenario === 'broadcast') {
    await h.visibility(false);
    h.channels[0].emit('message', {data: {type: 'session-ended', source: 'another-tab'}});
    await settle();
    assert.deepEqual(h.redirects, ['/']);
    assert.equal(h.storage.size, 0);
  } else if (scenario === 'failure') {
    h.controls.status = 503;
    await h.tick(1200);
    assert.equal(h.statusCalls(), 1);
    assert.equal(h.storage.size, 1, 'network failure does not discard unsaved state');
    await h.visibility(false);
    await h.tick(90000);
    assert.equal(h.statusCalls(), 1);
    h.controls.status = 200;
    await h.visibility(true);
    assert.equal(h.document.body.dataset.syAuthStatus, 'verified');
    assert.equal(h.statusCalls(), 2);
  } else if (scenario === 'late-response' || scenario === 'late-json') {
    h.controls[scenario === 'late-response' ? 'hold' : 'holdJson'] = true;
    await h.tick(1200);
    assert.equal(h.pending.length, 1);
    h.window.__syAuthStatusCleanup();
    h.pending[0]();
    await settle();
    assert.equal(h.timers.size, 0, 'disposed monitor cannot be resurrected by late response');
    assert.equal(h.document.body.dataset.syAuthStatus, undefined);
    assert.equal(h.document.listenerCount() + h.window.listenerCount(), 0);
  } else if (scenario === 'hidden-response') {
    h.controls.hold = true;
    await h.tick(1200);
    await h.visibility(false);
    h.pending[0]();
    await settle();
    assert.equal(h.timers.size, 1);
    await h.tick(90000);
    assert.equal(h.statusCalls(), 1);
  } else if (scenario === 'expiry-pending') {
    h.controls.hold = true;
    await h.tick(1200);
    await h.tick(3600000);
    assert.deepEqual(h.redirects, ['/']);
    h.pending[0]();
    await settle();
    assert.equal(h.timers.size, 0);
    assert.equal(h.document.body.dataset.syAuthStatus, undefined);
  } else if (scenario === 'logout-retry') {
    h.controls.status = 403;
    h.controls.logoutStatus = 503;
    await h.tick(1200);
    assert.equal(h.document.body.dataset.syLogout, 'retry-required');
    const main = h.document.getElementById('main-content');
    assert(main.hasAttribute('inert'));
    assert.deepEqual(h.redirects, []);
    h.controls.logoutStatus = 200;
    const retry = h.document.getElementById('sy-auth-exit-retry');
    retry.emit('click');
    retry.emit('click');
    await settle();
    assert.deepEqual(h.redirects, ['/']);
    assert(!main.hasAttribute('inert'));
    assert.equal(h.timers.size, 0);
    assert.equal(h.calls.filter(call => call.url === '/auth/logout').length, 2);
  } else if (scenario === 'network-error') {
    h.controls.reject = true;
    await h.tick(1200);
    assert.equal(h.document.body.dataset.syAuthStatus, 'temporarily-unavailable');
    assert.equal(h.storage.size, 1);
    h.controls.reject = false;
    await h.tick(45000);
    assert.equal(h.document.body.dataset.syAuthStatus, 'verified');
    assert.equal(h.statusCalls(), 2);
  } else if (scenario === 'reinstall') {
    for (let i = 0; i < 20; i++) h.install();
    await h.tick(1200);
    assert.equal(h.statusCalls(), 1);
    assert.equal(h.channels.filter(channel => !channel.closed).length, 1);
    assert.equal(h.document.listenerCount() + h.window.listenerCount(), 3);
    assert.equal(h.timers.size, 2);
  } else {
    assert.fail(`unknown scenario ${scenario}`);
  }
  assert(h.calls.every(call => call.options.cache === 'no-store'));
  process.stdout.write(JSON.stringify({scenario, mode, status: 'pass'}));
}

run().catch(error => { console.error(error); process.exitCode = 1; });
