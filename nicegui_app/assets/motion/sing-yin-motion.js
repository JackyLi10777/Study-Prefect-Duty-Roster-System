/* Sing Yin motion layer: purposeful, one-shot, reduced-motion safe. */
(() => {
  if (window.__singYinMotionBootstrapped) return;
  window.__singYinMotionBootstrapped = true;

  const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
  const FINE_POINTER_QUERY = '(hover: hover) and (pointer: fine)';
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
  const pointerSurfaceSelector = [
    '.sy-flow-step:not(.sy-flow-step--pending)',
    '.sy-architecture-layer',
    '.sy-export-option',
    '.sy-onboarding-intro',
    '.sy-guide-hero',
    '.sy-handover-hero',
    '.sy-engineering-hero',
    '.sy-co-creation',
    '.sy-trust-evidence-card',
    '.sy-platform-value',
    '.sy-platform-resource',
    '.sy-engineering-fact',
    '.sy-engineering-blueprint-layer',
    '.sy-engineering-pillar',
    '.sy-team-role',
    '.sy-capability-card',
    '.sy-solution-card',
    '.sy-storage-lifecycle'
  ].join(',');

  const reducedMotion = () => window.matchMedia(REDUCED_QUERY).matches;
  const queryWithin = (root, selector) => {
    const matches = [];
    if (root instanceof Element && root.matches(selector)) matches.push(root);
    root.querySelectorAll?.(selector).forEach((element) => matches.push(element));
    return matches;
  };
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

  const enhancePointerSurface = (surface) => {
    if (surface.dataset.syPointerReady === 'true') return;
    surface.dataset.syPointerReady = 'true';
    if (reducedMotion() || !window.matchMedia(FINE_POINTER_QUERY).matches) return;
    surface.classList.add('sy-pointer-reactive');
    const light = document.createElement('span');
    light.className = 'sy-pointer-light';
    light.setAttribute('aria-hidden', 'true');
    surface.appendChild(light);

    const pointer = { x: surface.clientWidth / 2, y: surface.clientHeight / 2 };
    let bounds = null;
    let xTo = null;
    let yTo = null;
    const renderPointer = () => {
      surface.style.setProperty('--sy-pointer-x', `${pointer.x}px`);
      surface.style.setProperty('--sy-pointer-y', `${pointer.y}px`);
    };
    const prepareQuickSetters = () => {
      if (xTo || !window.gsap) return;
      xTo = window.gsap.quickTo(pointer, 'x', { duration: 0.22, ease: 'power2.out', onUpdate: renderPointer });
      yTo = window.gsap.quickTo(pointer, 'y', { duration: 0.22, ease: 'power2.out', onUpdate: renderPointer });
    };
    const centre = () => {
      const x = surface.clientWidth / 2;
      const y = surface.clientHeight / 2;
      if (xTo && yTo) {
        xTo(x);
        yTo(y);
      } else {
        pointer.x = x;
        pointer.y = y;
        renderPointer();
      }
    };
    surface.addEventListener('pointerenter', () => {
      bounds = surface.getBoundingClientRect();
      prepareQuickSetters();
    }, { passive: true });
    surface.addEventListener('pointermove', (event) => {
      if (!bounds) bounds = surface.getBoundingClientRect();
      const x = event.clientX - bounds.left;
      const y = event.clientY - bounds.top;
      if (xTo && yTo) {
        xTo(x);
        yTo(y);
      } else {
        pointer.x = x;
        pointer.y = y;
        renderPointer();
      }
    }, { passive: true });
    surface.addEventListener('pointerleave', () => {
      bounds = null;
      centre();
    }, { passive: true });
  };

  const hydrate = (root = document) => {
    queryWithin(root, narrativeSelectors).forEach((element) => observe(element, false));
    queryWithin(root, groupSelectors).forEach((element) => observe(element, true));
    queryWithin(root, pointerSurfaceSelector).forEach(enhancePointerSurface);
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
    new MutationObserver((mutations) => {
      mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => {
        if (node instanceof Element) hydrate(node);
      }));
    }).observe(document.body, { childList: true, subtree: true });
    document.fonts?.ready.then(() => hydrate());
    window.addEventListener('sy:feedback', (event) => feedbackPulse(event.detail?.kind || 'success'));
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
  } else {
    boot();
  }
})();
