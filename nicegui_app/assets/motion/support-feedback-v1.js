(() => {
  'use strict';

  const install = () => {
    const root = document.querySelector('[data-testid="guest-browser-only-support"]');
    if (!(root instanceof HTMLElement)) return false;
    if (root.dataset.installed === 'true') return true;
    const form = root.querySelector('#sy-support-browser-form');
    const result = root.querySelector('#sy-support-browser-result');
    const resultActions = root.querySelector('#sy-support-browser-result-actions');
    const error = root.querySelector('#sy-support-browser-error');
    const download = root.querySelector('#sy-support-browser-download');
    const copy = root.querySelector('#sy-support-browser-copy');
    const email = root.querySelector('#sy-support-browser-email');
    if (!(form instanceof HTMLFormElement) || !(result instanceof HTMLOutputElement)) return false;
    root.dataset.installed = 'true';
    let report = null;

    const value = id => String(root.querySelector(`#sy-support-${id}`)?.value || '').trim();
    const setActions = enabled => {
      if (resultActions instanceof HTMLElement) resultActions.hidden = !enabled;
    };
    const incidentId = () => {
      const date = new Date().toISOString().slice(0, 10).replaceAll('-', '');
      const bytes = new Uint8Array(4);
      crypto.getRandomValues(bytes);
      return `GUEST-${date}-${Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
    };
    const build = () => {
      const expected = value('expected');
      const actual = value('actual');
      const steps = value('steps').split(/\r?\n/).map(item => item.trim()).filter(Boolean).slice(0, 12);
      if (!expected || !actual || !steps.length) {
        error.textContent = root.dataset.requiredMessage || 'Complete the required fields.';
        report = null;
        setActions(false);
        return false;
      }
      error.textContent = '';
      report = {
        schema_version: 1,
        temporary_reference: incidentId(),
        persistence: 'browser-only',
        created_at_utc: new Date().toISOString(),
        route_category: value('route'),
        workflow_action: value('action'),
        expected_behavior: expected,
        actual_behavior: actual,
        reproduction_steps: steps,
        impact: value('impact'),
        frequency: value('frequency'),
        last_known_good: value('last-good'),
      };
      result.textContent = report.temporary_reference;
      setActions(true);
      return true;
    };

    form.addEventListener('submit', event => {
      event.preventDefault();
      build();
    });
    form.addEventListener('reset', () => {
      report = null;
      error.textContent = '';
      result.textContent = '';
      setActions(false);
    });
    download?.addEventListener('click', () => {
      if (!report && !build()) return;
      const blob = new Blob([`${JSON.stringify(report, null, 2)}\n`], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `${report.temporary_reference}.json`;
      anchor.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
    copy?.addEventListener('click', async () => {
      if (!report && !build()) return;
      await navigator.clipboard.writeText(report.temporary_reference);
    });
    email?.addEventListener('click', () => {
      if (!report && !build()) return;
      const subject = `Temporary incident ${report.temporary_reference}`;
      const body = `${report.temporary_reference}\nBrowser-only report; attach the downloaded JSON only after reviewing it.`;
      location.href = `mailto:${encodeURIComponent(root.dataset.email || '')}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    });
    setActions(false);
    return true;
  };

  const start = () => {
    if (install()) return;
    const observer = new MutationObserver(() => {
      if (install()) observer.disconnect();
    });
    observer.observe(document.documentElement, {childList: true, subtree: true});
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
