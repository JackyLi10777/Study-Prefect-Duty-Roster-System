(() => {
  'use strict';

  if (window.SingYinMusicController) return;

  const STATE_ATTRIBUTE = 'syMusicAutoplay';
  const boundAudio = new WeakSet();

  const classifyFailure = (error, audio) => {
    const name = String(error?.name || '');
    if (name === 'NotAllowedError') return 'blocked';
    if (name === 'NotSupportedError') return 'decoding';
    if (name === 'AbortError') return 'lifecycle';
    if (audio?.error?.code === 2) return 'transport';
    if (audio?.error?.code === 3 || audio?.error?.code === 4) return 'decoding';
    if (audio?.networkState === 2) return 'loading';
    if (audio?.networkState === 3) return 'decoding';
    return navigator.onLine === false ? 'transport' : 'error';
  };

  const publishState = (state, onState) => {
    document.body.dataset[STATE_ATTRIBUTE] = state;
    if (typeof onState === 'function') onState(state);
  };

  const attempt = (audio, { volume, onState } = {}) => {
    if (!(audio instanceof HTMLMediaElement)) {
      publishState('error', onState);
      return Promise.resolve({ ok: false, state: 'error' });
    }
    if (Number.isFinite(Number(volume))) {
      audio.volume = Math.max(0, Math.min(1, Number(volume)));
      audio.dataset.syBaseVolume = String(audio.volume);
    }
    publishState(audio.readyState < 3 ? 'loading' : 'starting', onState);

    let playResult;
    try {
      // Keep play() inside the caller's trusted click task when attempt() is
      // invoked by the explicit retry control. Do not insert timers or awaits.
      playResult = audio.play();
    } catch (error) {
      playResult = Promise.reject(error);
    }
    return Promise.resolve(playResult)
      .then(() => {
        publishState('playing', onState);
        return { ok: true, state: 'playing' };
      })
      .catch((error) => {
        const state = classifyFailure(error, audio);
        publishState(state, onState);
        return { ok: false, state };
      });
  };

  const pause = (audio, { onState, state = 'paused' } = {}) => {
    if (audio instanceof HTMLMediaElement) audio.pause();
    publishState(state, onState);
  };

  const pauseAll = ({ onState, state = 'paused' } = {}) => {
    document.querySelectorAll('audio.sy-page-music-audio').forEach((audio) => audio.pause());
    publishState(state, onState);
  };

  const bind = (audio, { onState } = {}) => {
    if (!(audio instanceof HTMLMediaElement) || boundAudio.has(audio)) return;
    boundAudio.add(audio);
    audio.addEventListener('playing', () => publishState('playing', onState));
    audio.addEventListener('waiting', () => publishState('loading', onState));
    audio.addEventListener('stalled', () => publishState(navigator.onLine === false ? 'transport' : 'loading', onState));
    audio.addEventListener('error', () => publishState(classifyFailure(audio.error, audio), onState));
  };

  window.SingYinMusicController = Object.freeze({
    attempt,
    bind,
    classifyFailure,
    pause,
    pauseAll,
  });
})();
