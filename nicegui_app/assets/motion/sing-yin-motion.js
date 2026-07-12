/* Sing Yin motion layer: purposeful, one-shot, reduced-motion safe. */
(() => {
  if (window.__singYinMotionBootstrapped) return;
  window.__singYinMotionBootstrapped = true;

  const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
  const narrativeSelectors = [
    '.sy-daily-start',
    '.sy-workbench',
    '.sy-onboarding-intro',
    '.sy-guide-hero',
    '.sy-handover-hero',
    '.sy-platform-hero',
    '.sy-engineering-hero',
    '.sy-architecture-hero',
    '.sy-architecture-lifeline-visual',
    '.sy-co-creation'
  ].join(',');
  const groupSelectors = [
    '.sy-flow',
    '.sy-engineering-facts',
    '.sy-team-operating-model',
    '.sy-capability-map',
    '.sy-solutions-portfolio',
    '.sy-service-lifeline',
    '.sy-architecture-grid',
    '.sy-trust-evidence-grid'
  ].join(',');

  const reducedMotion = () => window.matchMedia(REDUCED_QUERY).matches;
  const animateOnce = (element, children = false) => {
    if (element.dataset.syMotionReady === 'true') return;
    element.dataset.syMotionReady = 'true';
    if (reducedMotion() || !window.gsap) return;
    const targets = children ? Array.from(element.children).slice(0, 8) : [element];
    if (!targets.length) return;
    window.gsap.fromTo(
      targets,
      { autoAlpha: 0.78, y: 12 },
      {
        autoAlpha: 1,
        y: 0,
        duration: children ? 0.36 : 0.44,
        stagger: children ? 0.045 : 0,
        ease: 'power2.out',
        overwrite: 'auto',
        clearProps: 'transform,opacity,visibility'
      }
    );
  };

  let observer;
  const observe = (element, children = false) => {
    if (element.dataset.syMotionObserved === 'true') return;
    element.dataset.syMotionObserved = 'true';
    if (!observer || reducedMotion()) {
      element.dataset.syMotionReady = 'true';
      return;
    }
    element.dataset.syMotionChildren = children ? 'true' : 'false';
    observer.observe(element);
  };

  const hydrate = () => {
    document.querySelectorAll(narrativeSelectors).forEach((element) => observe(element, false));
    document.querySelectorAll(groupSelectors).forEach((element) => observe(element, true));
  };

  const feedbackPulse = (kind) => {
    if (reducedMotion() || !window.gsap) return;
    const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const bounds = active && active !== document.body ? active.getBoundingClientRect() : null;
    const pulse = document.createElement('span');
    pulse.className = `sy-feedback-pulse sy-feedback-pulse--${kind}`;
    pulse.setAttribute('aria-hidden', 'true');
    pulse.style.left = `${bounds ? bounds.left + bounds.width / 2 : window.innerWidth / 2}px`;
    pulse.style.top = `${bounds ? bounds.top + bounds.height / 2 : 72}px`;
    document.body.appendChild(pulse);
    window.gsap.timeline({ onComplete: () => pulse.remove() })
      .fromTo(pulse, { autoAlpha: 0, scale: 0.68 }, { autoAlpha: 0.72, scale: 1, duration: 0.16, ease: 'power2.out' })
      .to(pulse, { autoAlpha: 0, scale: 1.52, duration: 0.34, ease: 'power1.out' });
  };

  let bootAttempts = 0;
  const boot = () => {
    if (!window.gsap) {
      bootAttempts += 1;
      if (bootAttempts < 120) {
        window.setTimeout(boot, 30);
      } else {
        document.documentElement.dataset.syMotion = 'unavailable';
      }
      return;
    }
    document.documentElement.dataset.syMotion = reducedMotion() ? 'reduced' : 'ready';
    observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        animateOnce(entry.target, entry.target.dataset.syMotionChildren === 'true');
      }),
      { rootMargin: '0px 0px -7% 0px', threshold: 0.12 }
    );
    hydrate();
    new MutationObserver(hydrate).observe(document.body, { childList: true, subtree: true });
    document.fonts?.ready.then(hydrate);
    window.addEventListener('sy:feedback', (event) => feedbackPulse(event.detail?.kind || 'success'));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
