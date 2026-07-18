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
    '.sy-platform-operating-map',
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
  const interactiveIconSelector = [
    '.q-icon.material-icons',
    '.q-icon.material-icons-outlined',
    '.q-icon.material-symbols-outlined',
    '.q-icon.material-symbols-rounded'
  ].join(',');
  const interactiveIconHostSelector = '.q-btn,.q-tab,.q-item.q-item--clickable';
  const iconMotionRoles = new Map([
    ...['arrow_forward', 'east', 'open_in_new', 'ios_share', 'link'].map((name) => [name, 'forward']),
    ...['arrow_back'].map((name) => [name, 'back']),
    ...['refresh', 'event_repeat', 'restore', 'settings_backup_restore'].map((name) => [name, 'refresh']),
    ...['save', 'publish', 'archive', 'inventory_2', 'fact_check', 'task_alt', 'check_circle', 'verified_user', 'person_check', 'lock', 'encrypted'].map((name) => [name, 'confirm']),
    ...['download', 'download_for_offline', 'picture_as_pdf', 'data_object'].map((name) => [name, 'download']),
    ...['upload', 'upload_file', 'add_to_drive'].map((name) => [name, 'upload']),
    ...['swap_horiz', 'content_copy'].map((name) => [name, 'exchange']),
    ...['person_add', 'group_add', 'playlist_add'].map((name) => [name, 'create']),
    ...['edit', 'edit_note', 'edit_calendar', 'auto_fix_high'].map((name) => [name, 'edit']),
    ...['dark_mode', 'light_mode', 'translate', 'volume_off', 'volume_up', 'menu', 'manage_accounts', 'admin_panel_settings'].map((name) => [name, 'toggle']),
    ...['play_arrow', 'play_circle', 'smart_display'].map((name) => [name, 'play']),
    ...['search'].map((name) => [name, 'search']),
    ...['delete_outline', 'logout', 'person_off', 'link_off', 'close', 'event_busy'].map((name) => [name, 'danger']),
    ...['warning_amber', 'assignment_late', 'gpp_maybe', 'pending_actions'].map((name) => [name, 'attention']),
    ...[
      'home', 'space_dashboard', 'dashboard', 'view_quilt', 'calendar_month',
      'calendar_view_week', 'groups', 'handshake', 'database', 'settings',
      'domain', 'engineering', 'account_tree', 'menu_book', 'help_outline'
    ].map((name) => [name, 'navigation'])
  ]);

  const pointerControllers = new Map();
  const feedbackTimers = new Map();
  const ACTION_MEMORY_MS = 5 * 60 * 1000;
  let intersectionObserver = null;
  let mutationObserver = null;
  let motionMedia = null;
  let interactionAbortController = null;
  let lastActionHost = null;
  let lastActionAt = 0;
  let operationFeedbackHost = null;
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
    delete element.dataset.syMotionComplete;
    const complete = () => {
      element.dataset.syMotionComplete = 'true';
    };
    if (reducedMotion() || !window.gsap) {
      complete();
      return;
    }
    const targets = children ? Array.from(element.children).slice(0, 8) : [element];
    if (!targets.length) {
      complete();
      return;
    }
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
        clearProps: 'transform,opacity,visibility',
        onComplete: complete
      }
    );
  };

  const observe = (element, children = false) => {
    if (element.dataset.syMotionObserved === 'true') return;
    element.dataset.syMotionObserved = 'true';
    if (!intersectionObserver || reducedMotion()) {
      element.dataset.syMotionReady = 'true';
      element.dataset.syMotionComplete = 'true';
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
  const hydrateIconMotion = (root = document) => {
    queryWithin(root, interactiveIconSelector).forEach((icon) => {
      const host = icon.closest(interactiveIconHostSelector);
      const name = icon.textContent?.trim() || '';
      if (!host || !name) return;
      const role = iconMotionRoles.get(name) || 'signal';
      icon.dataset.syIconMotion = role;
      icon.dataset.syIconName = name;
    });
  };
  const hydratePointers = (root = document) => {
    queryWithin(root, pointerSurfaceSelector).forEach(enhancePointerSurface);
  };
  const removePointersWithin = (root) => {
    if (!(root instanceof Element)) return;
    if (pointerControllers.has(root)) removePointerSurface(root);
    root.querySelectorAll?.('.sy-pointer-reactive').forEach(removePointerSurface);
  };

  const rememberActionHost = (event) => {
    if (
      event.type === 'keydown'
      && !['Enter', ' '].includes(event.key)
    ) return;
    const source = event.target instanceof Element
      ? event.target.closest(interactiveIconHostSelector)
      : null;
    if (!(source instanceof HTMLElement) || !source.querySelector(interactiveIconSelector)) return;
    lastActionHost = source;
    lastActionAt = Date.now();
    operationFeedbackHost = null;
    markFeedbackTarget('navigation', source);
  };
  const resolveFeedbackTarget = (kind) => {
    const active = document.activeElement instanceof HTMLElement
      ? document.activeElement.closest(interactiveIconHostSelector)
      : null;
    if (active instanceof HTMLElement && active.isConnected && active.querySelector(interactiveIconSelector)) {
      lastActionHost = active;
      lastActionAt = Date.now();
      return active;
    }
    if (
      ['success', 'attention', 'error'].includes(kind)
      && operationFeedbackHost instanceof HTMLElement
      && operationFeedbackHost.isConnected
    ) return operationFeedbackHost;
    if (
      lastActionHost instanceof HTMLElement
      && lastActionHost.isConnected
      && Date.now() - lastActionAt <= ACTION_MEMORY_MS
    ) return lastActionHost;
    return null;
  };
  const feedbackPulse = (kind, target) => {
    if (reducedMotion() || !window.gsap) return;
    const bounds = target instanceof HTMLElement ? target.getBoundingClientRect() : null;
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
  const markFeedbackTarget = (kind, target) => {
    if (!(target instanceof HTMLElement)) return;
    const state = ['success', 'working', 'attention', 'error'].includes(kind) ? kind : 'navigation';
    if (kind === 'working') operationFeedbackHost = target;
    const existing = feedbackTimers.get(target);
    if (existing) window.clearTimeout(existing);
    target.dataset.syFeedbackState = state;
    const timer = window.setTimeout(() => {
      if (target.dataset.syFeedbackState === state) delete target.dataset.syFeedbackState;
      feedbackTimers.delete(target);
      if (
        ['success', 'attention', 'error'].includes(kind)
        && operationFeedbackHost === target
      ) operationFeedbackHost = null;
    }, 620);
    feedbackTimers.set(target, timer);
  };

  const dispose = () => {
    if (disposed) return;
    disposed = true;
    intersectionObserver?.disconnect();
    mutationObserver?.disconnect();
    motionMedia?.revert();
    interactionAbortController?.abort();
    Array.from(pointerControllers.keys()).forEach(removePointerSurface);
    feedbackTimers.forEach((timer) => window.clearTimeout(timer));
    feedbackTimers.clear();
    if (feedbackHandler) window.removeEventListener('sy:feedback', feedbackHandler);
    if (domReadyHandler) document.removeEventListener('DOMContentLoaded', domReadyHandler);
    document.querySelectorAll('.sy-feedback-pulse').forEach((pulse) => pulse.remove());
    document.querySelectorAll('[data-sy-feedback-state]').forEach((element) => {
      delete element.dataset.syFeedbackState;
    });
    lastActionHost = null;
    operationFeedbackHost = null;
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
    hydrateIconMotion();
    interactionAbortController = new AbortController();
    const interactionListenerOptions = {
      capture: true,
      signal: interactionAbortController.signal
    };
    document.addEventListener('pointerdown', rememberActionHost, interactionListenerOptions);
    document.addEventListener('keydown', rememberActionHost, interactionListenerOptions);

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
          hydrateIconMotion(node);
          if (!reducedMotion() && window.matchMedia(FINE_POINTER_QUERY).matches) hydratePointers(node);
        });
      });
    });
    mutationObserver.observe(document.body, { childList: true, subtree: true });
    document.fonts?.ready.then(() => {
      if (!disposed) hydrateMotion();
    });
    feedbackHandler = (event) => {
      const kind = event.detail?.kind || 'success';
      const target = resolveFeedbackTarget(kind);
      feedbackPulse(kind, target);
      markFeedbackTarget(kind, target);
    };
    window.addEventListener('sy:feedback', feedbackHandler);
  };

  if (document.readyState === 'loading') {
    domReadyHandler = boot;
    document.addEventListener('DOMContentLoaded', domReadyHandler, { once: true });
  } else {
    boot();
  }
})();
