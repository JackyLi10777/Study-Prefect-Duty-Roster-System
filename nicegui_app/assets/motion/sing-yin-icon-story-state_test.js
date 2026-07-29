import './sing-yin-icon-story-state.js';

const assertEquals = (actual, expected, message) => {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${expected}, received ${actual}`);
  }
};

Deno.test('rapid reversal always resolves to the latest story state', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  assertEquals(machine.transition(host, 'pointer', true), true, 'pointer enter');
  assertEquals(machine.transition(host, 'pointer', false), false, 'pointer leave');
  assertEquals(machine.transition(host, 'pointer', true), true, 'second pointer enter');
});

Deno.test('pointer and keyboard focus keep one aggregate active state', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  assertEquals(machine.transition(host, 'pointer', true), true, 'pointer activates');
  assertEquals(machine.transition(host, 'focus', true), null, 'focus does not restart');
  assertEquals(machine.transition(host, 'pointer', false), null, 'focus keeps active');
  assertEquals(machine.transition(host, 'focus', false), false, 'last input restores');
});

Deno.test('focus-first overlap behaves the same as pointer-first overlap', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  assertEquals(machine.transition(host, 'focus', true), true, 'focus activates');
  assertEquals(machine.transition(host, 'pointer', true), null, 'pointer does not restart');
  assertEquals(machine.transition(host, 'focus', false), null, 'pointer keeps active');
  assertEquals(machine.transition(host, 'pointer', false), false, 'last input restores');
});

Deno.test('a persistent state change wins while a preview is active', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  machine.setPersistent(host, 'volume_off');
  assertEquals(machine.transition(host, 'pointer', true), true, 'preview starts');
  const state = machine.setPersistent(host, 'volume_up');
  assertEquals(state.persistentGlyph, 'volume_up', 'real glyph wins');
  assertEquals(state.previewActive, true, 'input state remains observable');
  assertEquals(state.revision, 2, 'persistent revision advances');
});

Deno.test('disabled busy and reduced-motion guards cancel temporary preview', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  machine.transition(host, 'focus', true);
  const guarded = machine.setGuards(host, {busy: true});
  assertEquals(guarded.interactive, false, 'busy control is not interactive');
  assertEquals(guarded.previewActive, false, 'busy control cancels preview');
  assertEquals(machine.transition(host, 'focus', false), null, 'cleanup is idempotent');
});

Deno.test('clearing a replaced host removes all prior state', () => {
  const machine = globalThis.SingYinIconStoryState.create();
  const host = {};

  machine.setPersistent(host, 'dark_mode');
  machine.transition(host, 'pointer', true);
  machine.clear(host);
  const state = machine.current(host);
  assertEquals(state.persistentGlyph, null, 'persistent glyph is cleared');
  assertEquals(state.previewActive, false, 'preview inputs are cleared');
});
