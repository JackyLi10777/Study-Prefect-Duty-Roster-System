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
