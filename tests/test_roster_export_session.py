from nicegui_app.services.roster_export_session import ExportOptions, RosterExportSession


def test_share_lease_expires_before_start_but_not_during_an_open_os_sheet():
    from nicegui_app.services.roster_export_session import NativeShareLease

    expired = NativeShareLease(generation="4", expires_at=15)
    assert expired.expire(now=15)
    assert not expired.start(expired.token, now=15)
    assert not expired.finish(expired.token, now=15)
    active = NativeShareLease(generation="4", expires_at=15)
    assert not active.start("other-lease", now=1)
    assert active.start(active.token, now=14)
    assert not active.start(active.token, now=14)
    assert not active.expire(now=16)
    assert active.finish(active.token, now=60)
    assert not active.finish(active.token, now=60)


def test_cancelling_share_lease_rejects_any_late_os_result():
    from nicegui_app.services.roster_export_session import NativeShareLease

    lease = NativeShareLease(generation="4", expires_at=15)
    assert lease.start(lease.token, now=1)
    lease.cancel()
    assert not lease.finish(lease.token, now=2)


def test_language_aba_rejects_late_result():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.change_options(ExportOptions(language="en"))
    session.change_options(ExportOptions(language="zh"))
    assert not session.complete(request, object())
    assert session.document is None


def test_close_reopen_rejects_late_result():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.close()
    session.open()
    assert not session.complete(request, object())


def test_formats_reuse_document_until_workspace_is_reopened():
    session = RosterExportSession()
    session.open()
    document = object()
    assert session.complete(session.begin(), document)
    request = session.begin()
    assert request.document is document
    assert session.complete(request, document)
    assert session.begin().document is document
    session.close()
    session.open()
    assert session.begin().document is None


def test_stale_revision_releases_document_and_rejects_worker():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.invalidate_source()
    assert session.phase == "stale"
    assert not session.complete(request, object())
    assert session.document is None


def test_failed_audit_delivery_does_not_leave_workspace_preparing():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    assert not session.finish_direct_delivery(request, delivered=False)
    assert session.phase == "failed"
    retry = session.begin()
    assert session.finish_direct_delivery(retry, delivered=True)
    assert session.phase == "idle"


def test_late_audit_delivery_result_does_not_change_reopened_workspace():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    session.close()
    session.open()
    assert not session.finish_direct_delivery(request, delivered=True)
    assert session.phase == "idle"


def test_native_share_result_requires_current_ready_generation():
    session = RosterExportSession()
    session.open()
    request = session.begin()
    assert session.complete(request, object())
    token = str(request.generation)
    assert session.accepts_share_result(token)
    assert not session.accepts_share_result(None)
    assert not session.accepts_share_result(request.generation)
    session.change_options(ExportOptions(language="en"))
    session.change_options(ExportOptions(language="zh"))
    assert not session.accepts_share_result(token)
    request = session.begin()
    assert not session.accepts_share_result(str(request.generation))
    assert session.complete(request, object())
    assert session.accepts_share_result(str(request.generation))
    session.close()
    session.open()
    assert not session.accepts_share_result(str(request.generation))
