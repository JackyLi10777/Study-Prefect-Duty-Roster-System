"""Opt-in navigation for retained reading sections; no arbitrary fragment bridge."""
from collections.abc import Callable, Sequence
import json
import re

from nicegui import events, ui

from nicegui_app.ui.i18n import t
from nicegui_app.ui.lazy_sections import lazy_expansion
from nicegui_app.ui.reference_navigation import render_page_toc


# Only source-owned anchors reach Python. Unknown fragments also invalidate any
# in-flight focus request, without sending their contents to the server.
READING_RUNTIME = r"""(hostId, anchors) => {
    window.__syReadingNavigation?.abort();
    const controller = new AbortController();
    window.__syReadingNavigation = controller;
    const host = document.getElementById(hostId);
    if (!host) return;
    const allowed = new Set(anchors);
    let sequence = window.__syReadingSequence || 0;
    let frame = 0;
    const cancel = () => {
        window.__syReadingSequence = ++sequence;
        cancelAnimationFrame(frame);
    };
    controller.signal.addEventListener('abort', cancel, {once:true});
    const navigate = () => {
        cancel();
        const anchor = location.hash.slice(1);
        if (!allowed.has(anchor)) return;
        const request = sequence;
        host.dispatchEvent(new CustomEvent('reading-anchor', {detail:{anchor, sequence:request}}));
        const deadline = performance.now() + 5000;
        const focus = () => {
            if (controller.signal.aborted || sequence !== request || !host.isConnected) return;
            const target = document.getElementById(anchor);
            if (host.getAttribute('data-reading-ready') !== String(request) || !target?.getClientRects().length) {
                if (performance.now() < deadline) frame = requestAnimationFrame(focus);
                return;
            }
            const heading = target.querySelector('.q-expansion-item__container > .q-item') || target;
            if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
            heading.focus({preventScroll:true});
            target.scrollIntoView({block:'start', behavior:'instant'});
        };
        frame = requestAnimationFrame(focus);
    };
    document.addEventListener('click', event => {
        const link = event.target.closest?.('[data-sy-toc-target]');
        if (!link || !allowed.has(link.getAttribute('data-sy-toc-target')) ||
            event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        history.pushState(null, '', link.getAttribute('href'));
        navigate();
    }, {signal:controller.signal});
    window.addEventListener('hashchange', navigate, {signal:controller.signal});
    window.addEventListener('pagehide', () => controller.abort(), {signal:controller.signal});
    navigate();
}"""


class ReadingNavigation:
    """Register existing outer targets and mount them before browser focus."""

    def __init__(self) -> None:
        self._targets: dict[str, Callable[[], None]] = {}
        self._sequence = 0
        self.host = ui.element("div").props("hidden data-testid=reading-navigation")
        self.host.on("reading-anchor", self._receive, args=["detail"])

    def register(self, anchor: str, reveal: Callable[[], None]) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", anchor) or anchor in self._targets:
            raise ValueError("Invalid or duplicate reading anchor")
        self._targets[anchor] = reveal

    def _receive(self, event: events.GenericEventArguments) -> None:
        detail = event.args.get("detail") if isinstance(event.args, dict) else None
        if not isinstance(detail, dict):
            return
        anchor, sequence = detail.get("anchor"), detail.get("sequence")
        if not isinstance(anchor, str) or anchor not in self._targets:
            return
        if type(sequence) is not int or not self._sequence < sequence <= 2**53 - 1:
            return
        self._sequence = sequence
        self._targets[anchor]()
        self.host.props(f"data-reading-ready={sequence}")

    def install(self) -> None:
        ui.run_javascript(f"({READING_RUNTIME})({json.dumps('c' + str(self.host.id))}, {json.dumps(list(self._targets))})")


def reading_toc(items: Sequence[tuple[str, str]]) -> None:
    lazy_expansion(t("reading_contents"), icon="list", test_id="reading-contents",
                   render=lambda: render_page_toc(items)).classes("max-w-4xl")
