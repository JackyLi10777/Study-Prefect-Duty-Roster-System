(() => {
  const create = () => {
    const states = new WeakMap();

    const assertHost = host => {
      if ((typeof host !== 'object' && typeof host !== 'function') || host === null) {
        throw new TypeError('Icon story hosts must be objects.');
      }
    };

    const stateFor = host => {
      assertHost(host);
      const state = states.get(host) || {
        pointer: false,
        focus: false,
        persistentGlyph: null,
        revision: 0,
        reduced: false,
        disabled: false,
        busy: false,
      };
      states.set(host, state);
      return state;
    };

    const previewActive = state => state.pointer || state.focus;

    const snapshot = state => Object.freeze({
      previewActive: previewActive(state),
      persistentGlyph: state.persistentGlyph,
      revision: state.revision,
      interactive: !(state.reduced || state.disabled || state.busy),
    });

    return Object.freeze({
      transition(host, input, enabled) {
        const state = stateFor(host);
        if (input !== 'pointer' && input !== 'focus') {
          throw new TypeError(`Unsupported icon story input: ${input}`);
        }

        const wasActive = previewActive(state);
        state[input] = Boolean(enabled);
        const isActive = previewActive(state);
        return wasActive === isActive ? null : isActive;
      },

      setPersistent(host, glyph) {
        const state = stateFor(host);
        const next = typeof glyph === 'string' ? glyph.trim() : '';
        if (!next || next === state.persistentGlyph) return null;
        state.persistentGlyph = next;
        state.revision += 1;
        return snapshot(state);
      },

      setGuards(host, { reduced = false, disabled = false, busy = false } = {}) {
        const state = stateFor(host);
        state.reduced = Boolean(reduced);
        state.disabled = Boolean(disabled);
        state.busy = Boolean(busy);
        if (!snapshot(state).interactive) {
          state.pointer = false;
          state.focus = false;
        }
        return snapshot(state);
      },

      current(host) {
        return snapshot(stateFor(host));
      },

      clear(host) {
        assertHost(host);
        states.delete(host);
      },
    });
  };

  globalThis.SingYinIconStoryState = Object.freeze({ create });
})();
