(() => {
  const create = () => {
    const inputs = new WeakMap();

    return Object.freeze({
      transition(host, input, enabled) {
        if ((typeof host !== 'object' && typeof host !== 'function') || host === null) {
          throw new TypeError('Icon story hosts must be objects.');
        }
        if (input !== 'pointer' && input !== 'focus') {
          throw new TypeError(`Unsupported icon story input: ${input}`);
        }

        const state = inputs.get(host) || { pointer: false, focus: false };
        const wasActive = state.pointer || state.focus;
        state[input] = Boolean(enabled);
        inputs.set(host, state);
        const isActive = state.pointer || state.focus;
        return wasActive === isActive ? null : isActive;
      },
    });
  };

  globalThis.SingYinIconStoryState = Object.freeze({ create });
})();
