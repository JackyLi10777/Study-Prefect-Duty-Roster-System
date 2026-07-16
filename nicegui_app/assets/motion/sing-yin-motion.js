/* Sing Yin motion layer: purposeful, one-shot, reduced-motion safe, and disposable. */
(() => {
  if (window.__singYinMotionBootstrapped) return;
  window.__singYinMotionBootstrapped = true;

  const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
  const FINE_POINTER_QUERY = '(hover: hover) and (pointer: fine)';
  const narrativeSelectors = [
    '.sy-page-context',
    '.sy-daily-start',
    '.sy-workbench',
    '.sy-dashboard-history',
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
    '.sy-devotional-reading-grid',
    '.sy-reference-index',
    '.sy-engineering-facts',
    '.sy-team-operating-model',
    '.sy-capability-map',
    '.sy-solutions-portfolio',
    '.sy-service-lifeline',
    '.sy-architecture-grid',
    '.sy-trust-evidence-grid'
  ].join(',');
  /* Pointer light is reserved for real links/actions and editorial showcase surfaces. */
  const pointerSurfaceSelector = [
    '.sy-dashboard-history-item:has(.q-btn)',
    '.sy-reference-index-card:has(.q-btn)',
    '.sy-export-option:has(.q-btn)',
    '.sy-platform-resource[href]',
    '.sy-solution-card:has(.q-btn)',
    '.sy-engineering-resource-link',
    '.sy-co-creation'
  ].join(',');

  const pointerControllers = new Map();
  let intersectionObserver = null;
  let mutationObserver = null;
  let motionMedia = null;
  let feedbackHandler = null;
  let domReadyHandler = null;
  let disposed = false;

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

  const observe = (element, children = false) => {
    if (element.dataset.syMotionObserved === 'true') return;
    element.dataset.syMotionObserved = 'true';
    if (!intersectionObserver || reducedMotion()) {
      element.dataset.syMotionReady = 'true';
      return;
    }
    element.dataset.syMotionChildren = children ? 'true' : 'false';
    intersectionObserver.observe(element);
  };

  const removePointerSurface = (surface) => {
    const controller = pointerControllers.get(surface);
    controller?.abort();
    pointerControllers.delete(surface);
    surface.querySelector(':scope > .sy-pointer-light')?.remove();
    surface.classList.remove('sy-pointer-reactive');
    delete surface.dataset.syPointerReady;
    surface.style.removeProperty('--sy-pointer-x');
    surface.style.removeProperty('--sy-pointer-y');
  };

  const enhancePointerSurface = (surface) => {
    if (surface.dataset.syPointerReady === 'true' || reducedMotion()) return;
    surface.dataset.syPointerReady = 'true';
    surface.classList.add('sy-pointer-reactive');
    const light = document.createElement('span');
    light.className = 'sy-pointer-light';
    light.setAttribute('aria-hidden', 'true');
    surface.appendChild(light);

    const controller = new AbortController();
    pointerControllers.set(surface, controller);
    const pointer = { x: surface.clientWidth / 2, y: surface.clientHeight / 2 };
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
    const options = { passive: true, signal: controller.signal };
    surface.addEventListener('pointerenter', prepareQuickSetters, options);
    surface.addEventListener('pointermove', (event) => {
      /* Read the current bounds on demand so scrolling cannot leave a stale spotlight. */
      const bounds = surface.getBoundingClientRect();
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
    }, options);
    surface.addEventListener('pointerleave', centre, options);
    centre();
  };

  const hydrateMotion = (root = document) => {
    queryWithin(root, narrativeSelectors).forEach((element) => observe(element, false));
    queryWithin(root, groupSelectors).forEach((element) => observe(element, true));
  };
  const hydratePointers = (root = document) => {
    queryWithin(root, pointerSurfaceSelector).forEach(enhancePointerSurface);
  };
  const removePointersWithin = (root) => {
    if (!(root instanceof Element)) return;
    if (pointerControllers.has(root)) removePointerSurface(root);
    root.querySelectorAll?.('.sy-pointer-reactive').forEach(removePointerSurface);
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

  const dispose = () => {
    if (disposed) return;
    disposed = true;
    intersectionObserver?.disconnect();
    mutationObserver?.disconnect();
    motionMedia?.revert();
    Array.from(pointerControllers.keys()).forEach(removePointerSurface);
    if (feedbackHandler) window.removeEventListener('sy:feedback', feedbackHandler);
    if (domReadyHandler) document.removeEventListener('DOMContentLoaded', domReadyHandler);
    document.querySelectorAll('.sy-feedback-pulse').forEach((pulse) => pulse.remove());
    delete document.documentElement.dataset.syMotion;
    window.__singYinMotionBootstrapped = false;
  };
  window.__disposeSingYinMotion = dispose;

  let bootAttempts = 0;
  const boot = () => {
    if (disposed) return;
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
    intersectionObserver = new IntersectionObserver(
      (entries) => entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        intersectionObserver?.unobserve(entry.target);
        animateOnce(entry.target, entry.target.dataset.syMotionChildren === 'true');
      }),
      { rootMargin: '0px 0px -7% 0px', threshold: 0.12 }
    );
    hydrateMotion();

    motionMedia = window.gsap.matchMedia();
    motionMedia.add(
      { reduce: REDUCED_QUERY, fine: FINE_POINTER_QUERY },
      (context) => {
        const { reduce, fine } = context.conditions;
        document.documentElement.dataset.syMotion = reduce ? 'reduced' : 'ready';
        Array.from(pointerControllers.keys()).forEach(removePointerSurface);
        if (!reduce && fine) hydratePointers();
        return () => Array.from(pointerControllers.keys()).forEach(removePointerSurface);
      }
    );

    mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.removedNodes.forEach(removePointersWithin);
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          hydrateMotion(node);
          if (!reducedMotion() && window.matchMedia(FINE_POINTER_QUERY).matches) hydratePointers(node);
        });
      });
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });
    document.fonts?.ready.then(() => {
      if (!disposed) hydrateMotion();
    });
    feedbackHandler = (event) => feedbackPulse(event.detail?.kind || 'success');
    window.addEventListener('sy:feedback', feedbackHandler);
  };

  if (document.readyState === 'loading') {
    domReadyHandler = boot;
    document.addEventListener('DOMContentLoaded', domReadyHandler, { once: true });
  } else {
    boot();
  }
})();
