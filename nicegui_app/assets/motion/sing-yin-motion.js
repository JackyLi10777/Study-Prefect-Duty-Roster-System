/* Sing Yin motion layer: purposeful, one-shot, reduced-motion safe, and disposable. */
(() => {
  if (window.__singYinMotionBootstrapped) return;
  window.__singYinMotionBootstrapped = true;

  const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';
  const FINE_POINTER_QUERY = '(hover: hover) and (pointer: fine)';
  const COARSE_POINTER_QUERY = '(hover: none), (pointer: coarse)';
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
  /* Pointer light for real links/actions (lift + glow) and calm ambient editorial cards (glow only). */
  const pointerSurfaceSelector = [
    '.sy-dashboard-history-item:has(.q-btn)',
    '.sy-reference-index-card:has(.q-btn)',
    '.sy-export-option:has(.q-btn)',
    '.sy-platform-resource[href]',
    '.sy-solution-card:has(.q-btn)',
    '.sy-engineering-resource-link',
    '.sy-co-creation'
  ].join(',');
  /* Non-interactive paper surfaces may receive a soft follow-light without implying clickability. */
  const ambientPointerSurfaceSelector = [
    '.sy-team-role',
    '.sy-capability-card',
    '.sy-trust-evidence-card',
    '.sy-service-stage',
    '.sy-platform-value',
    '.sy-devotional-companion',
    '.sy-platform-map-node',
    '.sy-adjustment-step',
    '.sy-acceptance-panel',
    '.sy-policy-panel',
    '.sy-surface[data-sy-ambient-light="true"]',
    '.sy-surface-subtle[data-sy-ambient-light="true"]'
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
    ...['dark_mode', 'light_mode', 'brightness_auto', 'translate', 'volume_off', 'volume_up', 'manage_accounts', 'admin_panel_settings'].map((name) => [name, 'toggle']),
    ...['menu'].map((name) => [name, 'menu']),
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
  /* A selected set of familiar controls tells a short visual story by
   * changing into a second, semantically related glyph. This is deliberately
   * more than translation: calendar -> confirmed calendar, closed book ->
   * open book, question -> illuminated idea, and grid -> rearranged grid. */
  const iconStoryGlyphs = new Map([
    ['space_dashboard', 'dashboard_customize'],
    ['dashboard', 'view_quilt'],
    ['calendar_month', 'event_available'],
    ['calendar_view_week', 'event_note'],
    ['groups', 'diversity_3'],
    ['handshake', 'sync_alt'],
    ['admin_panel_settings', 'verified_user'],
    ['settings', 'settings_suggest'],
    ['domain', 'apartment'],
    ['account_tree', 'hub'],
    ['build_circle', 'construction'],
    ['play_circle', 'rocket_launch'],
    ['help_outline', 'lightbulb'],
    ['menu_book', 'auto_stories'],
    ['edit_calendar', 'calendar_month'],
    ['edit_note', 'fact_check'],
    ['save', 'task_alt'],
    ['picture_as_pdf', 'file_download'],
    ['translate', 'language'],
    ['logout', 'exit_to_app'],
    ['headphones', 'graphic_eq'],
    ['support_agent', 'contact_support'],
    ['mail_outline', 'forward_to_inbox'],
    ['format_list_bulleted', 'checklist']
  ]);
  const persistentIconPairs = new Map([
    ['volume_off', 'volume_up'],
    ['volume_up', 'volume_off'],
    ['light_mode', 'dark_mode'],
    ['dark_mode', 'light_mode'],
    ['play_arrow', 'pause'],
    ['pause', 'play_arrow'],
    ['menu', 'close'],
    ['close', 'menu']
  ]);

  const pointerControllers = new Map();
  const tocObservers = new Map();
  const feedbackTimers = new Map();
  const iconStoryTimelines = new Map();
  const iconStoryTouchTimers = new Map();
  const iconStoryState = window.SingYinIconStoryState?.create?.() || null;
  const ACTION_MEMORY_MS = 5 * 60 * 1000;
  let intersectionObserver = null;
  let mutationObserver = null;
  let motionMedia = null;
  let interactionAbortController = null;
  let lastActionHost = null;
  let lastActionAt = 0;
  let operationFeedbackHost = null;
  let feedbackHandler = null;
  let disclosureHandler = null;
  let domReadyHandler = null;
  let disposed = false;

  const reducedMotion = () => window.matchMedia(REDUCED_QUERY).matches;
  const queryWithin = (root, selector) => {
    const matches = [];
    if (root instanceof Element && root.matches(selector)) matches.push(root);
    root.querySelectorAll?.(selector).forEach((element) => matches.push(element));
    return matches;
  };
  const setDataset = (element, key, value) => {
    if (element.dataset[key] !== value) element.dataset[key] = value;
  };
  const deleteDataset = (element, key) => {
    if (key in element.dataset) delete element.dataset[key];
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
    surface.classList.remove('sy-pointer-reactive', 'sy-pointer-ambient');
    delete surface.dataset.syPointerReady;
    delete surface.dataset.syPointerMode;
    surface.style.removeProperty('--sy-pointer-x');
    surface.style.removeProperty('--sy-pointer-y');
  };

  const enhancePointerSurface = (surface, mode = 'action') => {
    if (surface.dataset.syPointerReady === 'true' || reducedMotion()) return;
    if (mode === 'ambient' && surface.matches(pointerSurfaceSelector)) {
      /* Prefer the action treatment only when the surface is already an action card. */
      mode = 'action';
    }
    surface.dataset.syPointerReady = 'true';
    surface.dataset.syPointerMode = mode;
    surface.classList.add('sy-pointer-reactive');
    if (mode === 'ambient') surface.classList.add('sy-pointer-ambient');
    const light = document.createElement('span');
    light.className = mode === 'ambient' ? 'sy-pointer-light sy-pointer-light--ambient' : 'sy-pointer-light';
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
      const role = host.dataset.syIconMotionRole || iconMotionRoles.get(name) || 'signal';
      setDataset(icon, 'syIconMotion', role);
      setDataset(icon, 'syIconName', name);
      const category = host.dataset.syIconStoryCategory || 'preview';
      setDataset(icon, 'syIconStoryCategory', category);
      if (category === 'persistent') {
        deleteDataset(icon, 'syIconStoryFrom');
        deleteDataset(icon, 'syIconStoryTo');
        deleteDataset(icon, 'syIconStoryActive');
        iconStoryState?.setPersistent(host, name);
        return;
      }
      if (category === 'static') {
        deleteDataset(icon, 'syIconStoryFrom');
        deleteDataset(icon, 'syIconStoryTo');
        deleteDataset(icon, 'syIconStoryActive');
        iconStoryState?.clear(host);
        return;
      }
      const storyGlyph = host.dataset.syIconStoryTo || iconStoryGlyphs.get(name);
      if (storyGlyph) {
        setDataset(icon, 'syIconStoryFrom', name);
        setDataset(icon, 'syIconStoryTo', storyGlyph);
      } else {
        deleteDataset(icon, 'syIconStoryFrom');
        deleteDataset(icon, 'syIconStoryTo');
        deleteDataset(icon, 'syIconStoryActive');
      }
    });
  };
  const guardStateFor = host => iconStoryState?.setGuards(host, {
    reduced: reducedMotion(),
    disabled: host.matches('.disabled,[aria-disabled="true"]'),
    busy: host.matches('.q-btn--loading,[aria-busy="true"]')
  });
  const cancelIconTimeline = icon => {
    if (!(icon instanceof HTMLElement)) return;
    const previousTimeline = iconStoryTimelines.get(icon);
    if (previousTimeline) {
      previousTimeline.kill();
      iconStoryTimelines.delete(icon);
    }
    window.gsap?.killTweensOf(icon);
    window.gsap?.set(icon, { clearProps: 'opacity,visibility,scale,y,transform' });
  };
  const morphGlyph = (icon, next, { active = false } = {}) => {
    if (!(icon instanceof HTMLElement) || !next) return;
    cancelIconTimeline(icon);
    if (icon.textContent?.trim() === next) {
      icon.dataset.syIconName = next;
      icon.dataset.syIconStoryActive = active ? 'true' : 'false';
      return;
    }
    const host = icon.closest(interactiveIconHostSelector);
    const guards = host instanceof HTMLElement ? guardStateFor(host) : null;
    if (reducedMotion() || guards?.interactive === false || !window.gsap) {
      icon.textContent = next;
      icon.dataset.syIconName = next;
      icon.dataset.syIconStoryActive = active ? 'true' : 'false';
      return;
    }
    const timeline = window.gsap.timeline({
      defaults: { overwrite: 'auto' },
      onComplete: () => {
        if (iconStoryTimelines.get(icon) === timeline) iconStoryTimelines.delete(icon);
      }
    });
    iconStoryTimelines.set(icon, timeline);
    timeline
      .to(icon, {
        autoAlpha: 0,
        scale: 0.42,
        duration: 0.08,
        ease: 'power2.in',
        onComplete: () => {
          icon.textContent = next;
          icon.dataset.syIconName = next;
          icon.dataset.syIconStoryActive = active ? 'true' : 'false';
        }
      })
      .fromTo(
        icon,
        { autoAlpha: 0, scale: 0.58 },
        {
          autoAlpha: 1,
          scale: 1,
          duration: 0.10,
          ease: 'power3.out',
          clearProps: 'opacity,visibility,scale,y,transform'
        }
      );
  };
  const setPersistentGlyph = (target, next, { animate = true } = {}) => {
    const host = target instanceof Element
      ? (target.matches(interactiveIconHostSelector) ? target : target.closest(interactiveIconHostSelector))
      : null;
    if (!(host instanceof HTMLElement) || !next) return false;
    const icon = host.querySelector(interactiveIconSelector);
    if (!(icon instanceof HTMLElement)) return false;
    host.dataset.syIconStoryCategory = 'persistent';
    icon.dataset.syIconStoryCategory = 'persistent';
    const touchTimer = iconStoryTouchTimers.get(host);
    if (touchTimer) window.clearTimeout(touchTimer);
    iconStoryTouchTimers.delete(host);
    const state = iconStoryState?.setPersistent(host, next);
    delete icon.dataset.syIconStoryFrom;
    delete icon.dataset.syIconStoryTo;
    delete icon.dataset.syIconStoryActive;
    if (!animate || !state) {
      cancelIconTimeline(icon);
      icon.textContent = next;
      icon.dataset.syIconName = next;
    } else {
      morphGlyph(icon, next, { active: false });
    }
    return true;
  };
  const animateIconStory = (host, active, { allowCoarse = false } = {}) => {
    const icon = host.querySelector(`${interactiveIconSelector}[data-sy-icon-story-to]`);
    if (!(icon instanceof HTMLElement)) return;
    cancelIconTimeline(icon);
    const guards = guardStateFor(host);
    if (
      reducedMotion()
      || (!allowCoarse && !window.matchMedia(FINE_POINTER_QUERY).matches)
      || guards?.interactive === false
    ) {
      const original = icon.dataset.syIconStoryFrom;
      if (original) {
        icon.textContent = original;
        icon.dataset.syIconName = original;
      }
      icon.dataset.syIconStoryActive = 'false';
      return;
    }
    const next = active ? icon.dataset.syIconStoryTo : icon.dataset.syIconStoryFrom;
    if (!next) return;
    morphGlyph(icon, next, { active });
  };
  const iconStoryHost = (event) => event.target instanceof Element
    ? event.target.closest(interactiveIconHostSelector)
    : null;
  const onIconStoryEnter = (event) => {
    const host = iconStoryHost(event);
    if (!(host instanceof HTMLElement)) return;
    const related = event.relatedTarget;
    if (related instanceof Node && host.contains(related)) return;
    const input = event.type === 'pointerover' ? 'pointer' : 'focus';
    const active = iconStoryState?.transition(host, input, true);
    if (active === null || active === undefined) return;
    animateIconStory(host, active);
  };
  const onIconStoryLeave = (event) => {
    const host = iconStoryHost(event);
    if (!(host instanceof HTMLElement)) return;
    const related = event.relatedTarget;
    if (related instanceof Node && host.contains(related)) return;
    const input = event.type === 'pointerout' ? 'pointer' : 'focus';
    const active = iconStoryState?.transition(host, input, false);
    if (active === null || active === undefined) return;
    animateIconStory(host, active);
  };
  const onIconStoryPointerDown = (event) => {
    if (
      reducedMotion()
      || window.matchMedia(FINE_POINTER_QUERY).matches
      || !window.matchMedia(COARSE_POINTER_QUERY).matches
      || (event.pointerType && event.pointerType === 'mouse')
    ) return;
    const host = iconStoryHost(event);
    if (!(host instanceof HTMLElement) || !host.querySelector('[data-sy-icon-story-to]')) return;
    if (host.matches('.disabled,[aria-disabled="true"],[aria-busy="true"]')) return;
    const existing = iconStoryTouchTimers.get(host);
    if (existing) window.clearTimeout(existing);
    const icon = host.querySelector(`${interactiveIconSelector}[data-sy-icon-story-to]`);
    if (!(icon instanceof HTMLElement)) return;
    const temporaryGlyph = icon.dataset.syIconStoryTo;
    animateIconStory(host, true, { allowCoarse: true });
    const timer = window.setTimeout(() => {
      iconStoryTouchTimers.delete(host);
      if (!host.isConnected) return;
      const currentIcon = host.querySelector(interactiveIconSelector);
      if (!(currentIcon instanceof HTMLElement)) return;
      /* A real sound, theme, drawer, or disclosure state may have changed while
       * the touch story was playing. Never restore the old glyph over that new
       * state; instead, hydrate the new glyph for its next interaction. */
      if (
        currentIcon !== icon
        || currentIcon.textContent?.trim() !== temporaryGlyph
        || currentIcon.dataset.syIconStoryActive !== 'true'
      ) {
        delete currentIcon.dataset.syIconStoryActive;
        delete currentIcon.dataset.syIconStoryFrom;
        delete currentIcon.dataset.syIconStoryTo;
        hydrateIconMotion(currentIcon);
        return;
      }
      animateIconStory(host, false, { allowCoarse: true });
    }, 460);
    iconStoryTouchTimers.set(host, timer);
  };
  const hydratePointers = (root = document) => {
    queryWithin(root, pointerSurfaceSelector).forEach((surface) => enhancePointerSurface(surface, 'action'));
    queryWithin(root, ambientPointerSurfaceSelector).forEach((surface) => enhancePointerSurface(surface, 'ambient'));
  };
  const removePointersWithin = (root) => {
    if (!(root instanceof Element)) return;
    if (pointerControllers.has(root)) removePointerSurface(root);
    root.querySelectorAll?.('.sy-pointer-reactive').forEach(removePointerSurface);
  };
  const removeIconMotionWithin = root => {
    if (!(root instanceof Element)) return;
    const hosts = [];
    if (root.matches(interactiveIconHostSelector)) hosts.push(root);
    root.querySelectorAll?.(interactiveIconHostSelector).forEach(host => hosts.push(host));
    hosts.forEach(host => {
      iconStoryState?.clear(host);
      const timer = iconStoryTouchTimers.get(host);
      if (timer) window.clearTimeout(timer);
      iconStoryTouchTimers.delete(host);
      host.querySelectorAll?.(interactiveIconSelector).forEach(icon => cancelIconTimeline(icon));
    });
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

  const removeToc = (nav) => {
    tocObservers.get(nav)?.observer.disconnect();
    tocObservers.delete(nav);
    nav.querySelectorAll('[aria-current="location"]').forEach((link) => link.removeAttribute('aria-current'));
    delete nav.dataset.syTocReady;
    delete nav.dataset.syTocSignature;
  };

  const enhanceToc = (nav) => {
    const links = Array.from(nav.querySelectorAll('[data-sy-toc-target]'));
    const pairs = links
      .map((link) => [link, document.getElementById(link.dataset.syTocTarget)])
      .filter((pair) => pair[1]);
    if (!pairs.length) {
      if (tocObservers.has(nav)) removeToc(nav);
      return;
    }
    const signature = pairs.map(([link]) => link.dataset.syTocTarget).join('|');
    const targets = pairs.map(([, target]) => target);
    const existing = tocObservers.get(nav);
    const sameNodes = existing
      && existing.links.length === links.length
      && existing.targets.length === targets.length
      && existing.links.every((link, index) => link.isConnected && link === links[index])
      && existing.targets.every((target, index) => target.isConnected && target === targets[index]);
    if (
      nav.dataset.syTocReady === 'true'
      && nav.dataset.syTocSignature === signature
      && sameNodes
    ) return;
    if (existing || nav.dataset.syTocReady === 'true') removeToc(nav);
    nav.dataset.syTocReady = 'true';
    nav.dataset.syTocSignature = signature;
    links.forEach((link) => link.removeAttribute('aria-current'));
    links[0]?.setAttribute('aria-current', 'location');
    const targetToLink = new Map(pairs.map(([link, target]) => [target, link]));
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
      if (!visible.length) return;
      links.forEach((link) => link.removeAttribute('aria-current'));
      targetToLink.get(visible[0].target)?.setAttribute('aria-current', 'location');
    }, { rootMargin: '-16% 0px -68% 0px', threshold: [0, 0.12, 0.4] });
    pairs.forEach(([, target]) => observer.observe(target));
    tocObservers.set(nav, { observer, links, targets });
  };

  const hydrateToc = (root = document) => {
    queryWithin(root, '.sy-reference-toc').forEach(enhanceToc);
  };

  const removeTocWithin = (root) => {
    if (!(root instanceof Element)) return;
    if (tocObservers.has(root)) removeToc(root);
    root.querySelectorAll?.('.sy-reference-toc').forEach((nav) => {
      if (tocObservers.has(nav)) removeToc(nav);
    });
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
    Array.from(tocObservers.keys()).forEach(removeToc);
    iconStoryTimelines.forEach((timeline, icon) => {
      timeline.kill();
      window.gsap?.set(icon, { clearProps: 'opacity,visibility,scale,y,transform' });
    });
    iconStoryTimelines.clear();
    feedbackTimers.forEach((timer) => window.clearTimeout(timer));
    feedbackTimers.clear();
    iconStoryTouchTimers.forEach((timer) => window.clearTimeout(timer));
    iconStoryTouchTimers.clear();
    if (feedbackHandler) window.removeEventListener('sy:feedback', feedbackHandler);
    if (disclosureHandler) document.removeEventListener('click', disclosureHandler, true);
    if (domReadyHandler) document.removeEventListener('DOMContentLoaded', domReadyHandler);
    document.querySelectorAll('.sy-feedback-pulse').forEach((pulse) => pulse.remove());
    document.querySelectorAll('[data-sy-feedback-state]').forEach((element) => {
      delete element.dataset.syFeedbackState;
    });
    lastActionHost = null;
    operationFeedbackHost = null;
    delete document.documentElement.dataset.syMotion;
    delete window.__syIconMotion;
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
    hydrateToc();
    interactionAbortController = new AbortController();
    const interactionListenerOptions = {
      capture: true,
      signal: interactionAbortController.signal
    };
    document.addEventListener('pointerdown', rememberActionHost, interactionListenerOptions);
    document.addEventListener('pointerdown', onIconStoryPointerDown, interactionListenerOptions);
    document.addEventListener('keydown', rememberActionHost, interactionListenerOptions);
    document.addEventListener('pointerover', onIconStoryEnter, interactionListenerOptions);
    document.addEventListener('pointerout', onIconStoryLeave, interactionListenerOptions);
    document.addEventListener('focusin', onIconStoryEnter, interactionListenerOptions);
    document.addEventListener('focusout', onIconStoryLeave, interactionListenerOptions);

    motionMedia = window.gsap.matchMedia();
    motionMedia.add(
      { reduce: REDUCED_QUERY, fine: FINE_POINTER_QUERY },
      (context) => {
        const { reduce, fine } = context.conditions;
        document.documentElement.dataset.syMotion = reduce ? 'reduced' : 'ready';
        if (reduce) {
          iconStoryTouchTimers.forEach(timer => window.clearTimeout(timer));
          iconStoryTouchTimers.clear();
        }
        document.querySelectorAll(interactiveIconHostSelector).forEach(host => {
          const state = guardStateFor(host);
          const icon = host.querySelector(interactiveIconSelector);
          if (reduce && icon instanceof HTMLElement && icon.dataset.syIconStoryFrom) {
            cancelIconTimeline(icon);
            icon.textContent = icon.dataset.syIconStoryFrom;
            icon.dataset.syIconName = icon.dataset.syIconStoryFrom;
            icon.dataset.syIconStoryActive = 'false';
          }
          if (!state?.interactive) cancelIconTimeline(icon);
        });
        Array.from(pointerControllers.keys()).forEach(removePointerSurface);
        if (!reduce && fine) hydratePointers();
        return () => Array.from(pointerControllers.keys()).forEach(removePointerSurface);
      }
    );

    mutationObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.removedNodes.forEach(removePointersWithin);
        mutation.removedNodes.forEach(removeTocWithin);
        mutation.removedNodes.forEach(removeIconMotionWithin);
        if (mutation.type === 'attributes' && mutation.target instanceof Element) {
          hydrateIconMotion(mutation.target);
          const host = mutation.target.matches(interactiveIconHostSelector)
            ? mutation.target : mutation.target.closest(interactiveIconHostSelector);
          if (host instanceof HTMLElement) guardStateFor(host);
        }
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          hydrateMotion(node);
          hydrateIconMotion(node);
          hydrateToc(node);
          if (!reducedMotion() && window.matchMedia(FINE_POINTER_QUERY).matches) hydratePointers(node);
        });
      });
      /* A target section can arrive after its TOC in a streamed NiceGUI patch. */
      hydrateToc();
    });
    mutationObserver.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'aria-disabled', 'aria-busy', 'data-sy-icon-motion-role', 'data-sy-icon-story-to', 'data-sy-icon-story-category']
    });
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
    disclosureHandler = (event) => {
      const trigger = event.target instanceof Element
        ? event.target.closest('.q-expansion-item .q-item')
        : null;
      if (!trigger) return;
      const expansion = trigger.closest('.q-expansion-item');
      if (!expansion) return;
      expansion.dataset.syFeedback = 'disclosure';
      window.setTimeout(() => {
        if (!disposed) delete expansion.dataset.syFeedback;
      }, 260);
    };
    document.addEventListener('click', disclosureHandler, true);
    window.__syIconMotion = Object.freeze({
      setPersistentGlyph,
      hydrate: hydrateIconMotion,
      classify: target => {
        const host = target instanceof Element
          ? (target.matches(interactiveIconHostSelector) ? target : target.closest(interactiveIconHostSelector))
          : null;
        const icon = host?.querySelector(interactiveIconSelector);
        if (!(host instanceof HTMLElement) || !(icon instanceof HTMLElement)) return null;
        return Object.freeze({
          category: icon.dataset.syIconStoryCategory || 'preview',
          role: icon.dataset.syIconMotion || 'signal',
          source: icon.dataset.syIconName || icon.textContent?.trim() || '',
          destination: icon.dataset.syIconStoryTo || '',
        });
      },
      storySources: Object.freeze([...iconStoryGlyphs.keys()]),
      persistentPairs: Object.freeze([...persistentIconPairs.entries()])
    });
  };

  if (document.readyState === 'loading') {
    domReadyHandler = boot;
    document.addEventListener('DOMContentLoaded', domReadyHandler, { once: true });
  } else {
    boot();
  }
})();
