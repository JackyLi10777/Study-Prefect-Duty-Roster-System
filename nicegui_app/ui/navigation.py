"""Shared accessible navigation helpers for the NiceGUI workbench."""

from __future__ import annotations

from nicegui import ui

ROUTE_FOCUS_JAVASCRIPT = (
    "sessionStorage.setItem('sy:route-focus', 'main');"
    "window.__syRouteProgress?.start();"
)

ROUTE_PROGRESS_RUNTIME = """
(() => {
  window.__syRouteProgressCleanup?.();
  const bar = document.getElementById('sy-route-progress');
  if (!bar) return;
  let revealTimer = null;
  const controller = new AbortController();
  const hide = () => {
    if (revealTimer !== null) window.clearTimeout(revealTimer);
    revealTimer = null;
    bar.dataset.active = 'false';
    bar.setAttribute('aria-hidden', 'true');
  };
  const start = () => {
    hide();
    revealTimer = window.setTimeout(() => {
      revealTimer = null;
      bar.dataset.active = 'true';
      bar.removeAttribute('aria-hidden');
    }, 150);
  };
  window.addEventListener('pageshow', hide, {signal: controller.signal});
  window.addEventListener('pagehide', hide, {signal: controller.signal});
  window.__syRouteProgress = {start, stop: hide};
  window.__syRouteProgressCleanup = () => {
    controller.abort();
    hide();
    delete window.__syRouteProgress;
  };
  hide();
})();
"""


def mark_route_focus() -> None:
    """Ask the destination page to announce its main landmark after navigation."""

    ui.run_javascript(ROUTE_FOCUS_JAVASCRIPT)


def install_route_progress_runtime() -> None:
    """Install one delayed, self-cleaning route progress controller per page."""

    ui.run_javascript(ROUTE_PROGRESS_RUNTIME)


def navigate_to(route: str) -> None:
    """Navigate to a shared route while preserving keyboard and AT context."""

    mark_route_focus()
    ui.navigate.to(route)
