from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace

import pytest

from nicegui_app.access_context import AccessMode
from nicegui_app.services import guest_downloads as downloads


class FakeTimer:
    def __init__(
        self,
        scheduler: FakeScheduler,
        interval: float,
        callback: Callable[..., None],
        args: tuple[object, ...],
    ) -> None:
        self.scheduler = scheduler
        self.deadline = scheduler.monotonic + interval
        self.callback = callback
        self.args = args
        self.daemon = False
        self.started = False
        self.cancelled = False
        self.fired = False

    def start(self) -> None:
        self.started = True
        assert self.daemon, "Download cleanup must not keep the process alive."
        assert len(self.scheduler.pending) == 1, "Only one cleanup timer may be pending."

    def cancel(self) -> None:
        self.cancelled = True

    def fire(self, *, even_if_cancelled: bool = False) -> None:
        assert even_if_cancelled or not self.cancelled
        self.fired = True
        self.callback(*self.args)


class FakeScheduler:
    def __init__(self) -> None:
        self.wall = 10_000.0
        self.monotonic = 0.0
        self.timers: list[FakeTimer] = []

    @property
    def pending(self) -> list[FakeTimer]:
        return [
            timer
            for timer in self.timers
            if timer.started and not timer.cancelled and not timer.fired
        ]

    def timer(
        self,
        interval: float,
        callback: Callable[..., None],
        args: tuple[object, ...] = (),
    ) -> FakeTimer:
        timer = FakeTimer(self, interval, callback, args)
        self.timers.append(timer)
        return timer

    def advance(self, seconds: float, *, run_callbacks: bool = True) -> None:
        self.wall += seconds
        self.monotonic += seconds
        if run_callbacks:
            while due := [timer for timer in self.pending if timer.deadline <= self.monotonic]:
                min(due, key=lambda timer: timer.deadline).fire()


@pytest.fixture
def scheduler(monkeypatch: pytest.MonkeyPatch) -> FakeScheduler:
    scheduler = FakeScheduler()
    monkeypatch.setattr(downloads, "Timer", scheduler.timer, raising=False)
    monkeypatch.setattr(
        downloads,
        "time",
        SimpleNamespace(time=lambda: scheduler.wall, monotonic=lambda: scheduler.monotonic),
    )
    return scheduler


def issue(
    registry: downloads.GuestDownloadRegistry,
    *,
    session_id: str = "guest-a",
    access_mode: AccessMode = AccessMode.GUEST,
    now: int | None = None,
) -> downloads.GuestDownloadTicket:
    return registry.issue(
        access_mode=access_mode,
        session_id=session_id,
        filename="fictional.pdf",
        content=b"%PDF-fictional-only",
        media_type="application/pdf",
        now=now,
    )


def retained_bytes(registry: downloads.GuestDownloadRegistry) -> int:
    return sum(len(record.content) for record in registry._records.values())


def test_idle_expiry_releases_payloads_without_requests_and_stops(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    assert scheduler.pending == []
    ticket = issue(registry)
    assert ticket.expires_at == 10_090
    assert retained_bytes(registry) > 0
    assert len(scheduler.pending) == 1
    scheduler.advance(89)
    assert retained_bytes(registry) > 0
    scheduler.advance(1)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
    timer_count = len(scheduler.timers)
    scheduler.advance(3_600)
    assert len(scheduler.timers) == timer_count
    assert scheduler.pending == []


def test_many_tickets_share_one_wakeup_then_only_the_next_deadline_runs(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    for _ in range(6):
        issue(registry)
    assert len(scheduler.timers) == 1
    scheduler.advance(10)
    later = issue(registry, session_id="guest-b")
    assert len(scheduler.timers) == 1
    scheduler.advance(80)
    assert list(registry._records) == [later.token]
    assert len(scheduler.pending) == 1
    assert scheduler.pending[0].deadline == 100
    scheduler.advance(10)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


@pytest.mark.parametrize("remove_first", ["consume", "cleanup"])
def test_removing_earliest_ticket_reschedules_and_ignores_cancelled_callback(
    scheduler: FakeScheduler, remove_first: str,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    first = issue(registry)
    old_timer = scheduler.pending[0]
    scheduler.advance(10)
    later = issue(registry, session_id="guest-b")
    if remove_first == "consume":
        registry.consume(token=first.token, access_mode=AccessMode.GUEST, session_id="guest-a")
    else:
        assert registry.cleanup_session("guest-a") == 1
    assert old_timer.cancelled
    next_timer = scheduler.pending[0]
    assert next_timer.deadline == 100
    scheduler.advance(80)
    old_timer.fire(even_if_cancelled=True)
    assert scheduler.pending == [next_timer]
    assert list(registry._records) == [later.token]
    scheduler.advance(10)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_cleanup_stops_timer_and_late_callback_cannot_touch_a_new_batch(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    issue(registry)
    old_timer = scheduler.pending[0]
    assert registry.cleanup_session("guest-a") == 1
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
    scheduler.advance(100)
    fresh = issue(registry)
    new_timer = scheduler.pending[0]
    old_timer.fire(even_if_cancelled=True)
    assert scheduler.pending == [new_timer]
    assert registry.consume(
        token=fresh.token, access_mode=AccessMode.GUEST, session_id="guest-a",
    ).content == b"%PDF-fictional-only"
    assert scheduler.pending == []
    assert retained_bytes(registry) == 0


def test_synthetic_now_keeps_ticket_contract_without_using_real_epoch_for_cleanup(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    ticket = issue(registry, now=100)
    assert ticket.expires_at == 190
    scheduler.advance(89)
    assert registry.consume(
        token=ticket.token, access_mode=AccessMode.GUEST, session_id="guest-a", now=189,
    ).content == b"%PDF-fictional-only"
    assert scheduler.pending == []
    expired = issue(registry, now=200)
    with pytest.raises(downloads.GuestDownloadError, match="expired"):
        registry.consume(
            token=expired.token, access_mode=AccessMode.GUEST, session_id="guest-a", now=290,
        )
    assert scheduler.pending == []


@pytest.mark.parametrize("run_callbacks", [True, False])
def test_wall_clock_rollback_never_extends_retention_or_ticket_validity(
    scheduler: FakeScheduler, run_callbacks: bool,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    ticket = issue(registry)
    scheduler.wall -= 3_600
    scheduler.advance(90, run_callbacks=run_callbacks)
    with pytest.raises(downloads.GuestDownloadError):
        registry.consume(
            token=ticket.token, access_mode=AccessMode.GUEST, session_id="guest-a",
        )
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_failed_issue_after_wall_expiry_preserves_remaining_cleanup(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry(max_downloads_per_session=1)
    issue(registry)
    old_timer = scheduler.pending[0]
    scheduler.advance(10)
    later = issue(registry, session_id="guest-b")
    with pytest.raises(downloads.GuestDownloadCapacityError, match="capacity is full"):
        issue(registry, session_id="guest-b", now=10_090)
    assert list(registry._records) == [later.token]
    assert old_timer.cancelled
    assert len(scheduler.pending) == 1
    assert scheduler.pending[0].deadline == 100
    scheduler.advance(90)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_wrong_session_and_mode_leave_ticket_live_until_one_valid_consume(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    ticket = issue(registry)
    timer = scheduler.pending[0]
    for mode, session in [(AccessMode.ADMIN, "guest-a"), (AccessMode.GUEST, "guest-b")]:
        with pytest.raises(downloads.GuestDownloadError):
            registry.consume(token=ticket.token, access_mode=mode, session_id=session)
        assert scheduler.pending == [timer]
    assert registry.consume(
        token=ticket.token, access_mode=AccessMode.GUEST, session_id="guest-a",
    ).content == b"%PDF-fictional-only"
    with pytest.raises(downloads.GuestDownloadError):
        registry.consume(token=ticket.token, access_mode=AccessMode.GUEST, session_id="guest-a")
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_concurrent_consumers_still_deliver_only_once(scheduler: FakeScheduler) -> None:
    registry = downloads.GuestDownloadRegistry()
    ticket = issue(registry)
    barrier = Barrier(2)

    def consume() -> bytes | None:
        barrier.wait(timeout=5)
        try:
            return registry.consume(
                token=ticket.token, access_mode=AccessMode.GUEST, session_id="guest-a",
            ).content
        except downloads.GuestDownloadError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(consume) for _ in range(2)]
        results = [future.result(timeout=5) for future in futures]
    assert results.count(b"%PDF-fictional-only") == 1
    assert results.count(None) == 1
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_expiry_consume_and_new_issue_race_leaves_only_new_ticket(
    scheduler: FakeScheduler,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    expired = issue(registry)
    expired_timer = scheduler.pending[0]
    scheduler.advance(90, run_callbacks=False)
    barrier = Barrier(3)

    def fire_old_callback() -> None:
        barrier.wait(timeout=5)
        expired_timer.fire(even_if_cancelled=True)

    def consume_expired() -> None:
        barrier.wait(timeout=5)
        with pytest.raises(downloads.GuestDownloadError):
            registry.consume(
                token=expired.token, access_mode=AccessMode.GUEST, session_id="guest-a",
            )

    def issue_fresh() -> downloads.GuestDownloadTicket:
        barrier.wait(timeout=5)
        return issue(registry, session_id="guest-b")

    with ThreadPoolExecutor(max_workers=3) as executor:
        callbacks = [executor.submit(fire_old_callback), executor.submit(consume_expired)]
        fresh = executor.submit(issue_fresh).result(timeout=5)
        for callback in callbacks:
            callback.result(timeout=5)
    assert list(registry._records) == [fresh.token]
    assert len(scheduler.pending) == 1
    assert scheduler.pending[0].deadline == 180
    scheduler.advance(90)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_scheduler_failure_releases_bytes_and_allows_later_retry(
    scheduler: FakeScheduler, monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = downloads.GuestDownloadRegistry()

    def fail_start(_timer: FakeTimer) -> None:
        raise RuntimeError("test scheduler unavailable")

    with monkeypatch.context() as patch:
        patch.setattr(FakeTimer, "start", fail_start)
        with pytest.raises(downloads.GuestDownloadCapacityError, match="cleanup is unavailable"):
            issue(registry)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
    issue(registry)
    assert len(scheduler.pending) == 1
    scheduler.advance(90)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


def test_timer_constructor_failure_releases_payload_without_logging_error_details(
    scheduler: FakeScheduler, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture,
) -> None:
    registry = downloads.GuestDownloadRegistry()

    def fail_constructor(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("fictional-private-marker")

    with monkeypatch.context() as patch:
        patch.setattr(downloads, "Timer", fail_constructor)
        with pytest.raises(downloads.GuestDownloadCapacityError, match="cleanup is unavailable"):
            issue(registry)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
    assert [record.message for record in caplog.records] == [
        "event=generated_download_cleanup_failed",
    ]
    assert "fictional-private-marker" not in caplog.text
    issue(registry)
    scheduler.advance(90)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []


@pytest.mark.parametrize("trigger", ["consume", "background"])
def test_rescheduling_failure_releases_survivors_and_reports_without_thread_error(
    scheduler: FakeScheduler,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    trigger: str,
) -> None:
    registry = downloads.GuestDownloadRegistry()
    first = issue(registry)
    scheduler.advance(10)
    survivor = issue(registry, session_id="guest-b")

    def fail_start(_timer: FakeTimer) -> None:
        raise RuntimeError("fictional-private-marker")

    with monkeypatch.context() as patch:
        patch.setattr(FakeTimer, "start", fail_start)
        if trigger == "consume":
            with pytest.raises(downloads.GuestDownloadCapacityError, match="cleanup is unavailable"):
                registry.consume(
                    token=first.token, access_mode=AccessMode.GUEST, session_id="guest-a",
                )
        else:
            # Fake callbacks run synchronously; an unhandled thread exception
            # would propagate here and fail the test instead of being hidden.
            scheduler.advance(80)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
    assert [record.message for record in caplog.records] == [
        "event=generated_download_cleanup_failed",
    ]
    assert "fictional-private-marker" not in caplog.text
    with pytest.raises(downloads.GuestDownloadError):
        registry.consume(
            token=survivor.token, access_mode=AccessMode.GUEST, session_id="guest-b",
        )
    issue(registry)
    scheduler.advance(90)
    assert retained_bytes(registry) == 0
    assert scheduler.pending == []
