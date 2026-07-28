from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from nicegui_app.persistence.database import migrate_database
from nicegui_app.observability import (
    LOGGER_NAME,
    configure_local_logging,
    current_request_reference,
    install_asyncio_exception_handler,
    install_request_tracing,
    new_operation_reference,
    record_operator_event,
    record_operator_failure,
    record_operator_partial_failure,
)
from scripts.inspect_support_log import support_lines


def test_local_log_is_rotating_utf8_and_contains_no_operator_payload_by_default(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "logs" / "app.log")
    sensitive_value = "測試風紀的私人請假原因"

    try:
        raise ValueError(sensitive_value)
    except ValueError as error:
        reference = record_operator_failure(error, action="test_action")

    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert log_path.is_file()
    assert reference in content
    assert "action=test_action" in content
    assert "error_type=ValueError" in content
    assert sensitive_value not in content


def test_migrations_preserve_the_application_logger(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "migration-logging" / "app.log")

    migrate_database(tmp_path / "migration-logging" / "roster.sqlite3")
    reference = new_operation_reference()
    record_operator_event(action="migration_check", outcome="completed", reference=reference)

    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert logging.getLogger(LOGGER_NAME).disabled is False
    assert f"reference={reference}" in content
    assert "action=migration_check" in content


def test_operation_reference_is_short_and_non_identifying() -> None:
    reference = new_operation_reference()
    assert reference.startswith("OP-")
    assert len(reference) == 11
    assert reference[3:].isalnum()


def test_successful_operator_event_records_only_controlled_metadata(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "success" / "app.log")
    reference = new_operation_reference()
    record_operator_event(action="generate_draft", outcome="completed", reference=reference)
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert f"reference={reference}" in content
    assert "action=generate_draft" in content
    assert "outcome=completed" in content


def test_partial_failure_log_distinguishes_committed_data_from_failed_backup(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "partial" / "app.log")
    reference = new_operation_reference()
    try:
        raise RuntimeError("sensitive filesystem detail")
    except RuntimeError as error:
        record_operator_partial_failure(error, action="publish_roster", reference=reference)
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert f"reference={reference}" in content
    assert "event=operator_action_partial" in content
    assert "durable_state=committed backup=failed" in content
    assert "sensitive filesystem detail" not in content


def test_log_directory_can_be_isolated_by_environment(monkeypatch, tmp_path) -> None:
    isolated_directory = tmp_path / "isolated-logs"
    monkeypatch.setenv("SING_YIN_LOG_DIR", str(isolated_directory))
    assert configure_local_logging() == (isolated_directory / "app.log").resolve()


def test_request_trace_header_and_log_are_payload_free(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "requests" / "app.log")
    application = FastAPI()
    install_request_tracing(application)

    @application.get("/diagnostic/{unsafe_value}")
    def diagnostic(unsafe_value: str) -> dict[str, bool]:
        return {"ok": bool(unsafe_value)}

    response = TestClient(application).get("/diagnostic/測試風紀私隱資料?reason=私人請假")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("REQ-")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cross-Origin-Opener-Policy"] == "same-origin"
    csp = response.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self' 'unsafe-inline' 'unsafe-eval'" in csp
    assert "img-src 'self' data: https://i.ytimg.com https://img.youtube.com" in csp
    assert "connect-src 'self' ws: wss:" in csp
    assert "frame-src https://www.youtube-nocookie.com" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "base-uri 'none'" in csp
    assert response.headers["Cache-Control"] == "no-store"
    assert "event=http_request method=GET target=other status=200" in content
    assert "測試風紀私隱資料" not in content
    assert "私人請假" not in content
    assert current_request_reference() == "-"


def test_fast_successful_framework_asset_and_health_requests_are_debug_only(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "request-noise" / "app.log")
    application = FastAPI()
    install_request_tracing(application)

    @application.get("/assets/example.css")
    def static_asset() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/_nicegui/runtime.js")
    def nicegui_runtime() -> dict[str, bool]:
        return {"ok": True}

    @application.get("/healthz")
    def health_check() -> dict[str, bool]:
        return {"ok": True}

    client = TestClient(application)
    responses = [
        client.get("/assets/example.css"),
        client.get("/_nicegui/runtime.js"),
        client.get("/healthz"),
    ]
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert all(response.status_code == 200 for response in responses)
    assert all(response.headers["X-Request-ID"].startswith("REQ-") for response in responses)
    assert "target=asset status=200" not in content
    assert "target=nicegui_internal status=200" not in content
    assert "target=health status=200" not in content


def test_slow_successful_asset_request_remains_visible(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SING_YIN_SLOW_REQUEST_MS", "1")
    log_path = configure_local_logging(tmp_path / "slow-asset" / "app.log")
    application = FastAPI()
    install_request_tracing(application)

    @application.get("/assets/slow.css")
    async def slow_asset() -> dict[str, bool]:
        await asyncio.sleep(0.01)
        return {"ok": True}

    response = TestClient(application).get("/assets/slow.css")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"].startswith("REQ-")
    assert "WARNING" in content
    assert "event=http_request method=GET target=asset status=200" in content
    assert "slow=true" in content


def test_failed_internal_request_is_never_hidden_as_framework_noise(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "failed-internal" / "app.log")
    application = FastAPI()
    install_request_tracing(application)

    response = TestClient(application).get("/_nicegui/missing-resource.js")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert response.status_code == 404
    assert response.headers["X-Request-ID"].startswith("REQ-")
    assert "WARNING" in content
    assert "event=http_request method=GET target=nicegui_internal status=404" in content
    assert "slow=false" in content


def test_debug_mode_can_restore_fast_asset_request_detail(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SING_YIN_LOG_LEVEL", "DEBUG")
    log_path = configure_local_logging(tmp_path / "debug-assets" / "app.log")
    application = FastAPI()
    install_request_tracing(application)

    @application.get("/assets/example.css")
    def static_asset() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(application).get("/assets/example.css")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert response.status_code == 200
    assert "DEBUG" in content
    assert "event=http_request method=GET target=asset status=200" in content
    assert "slow=false" in content


def test_request_exception_logs_type_without_the_exception_message(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "request-failure" / "app.log")
    application = FastAPI()
    install_request_tracing(application)
    sensitive_value = "不應寫入日誌的請假內容"

    @application.get("/explode")
    def explode() -> None:
        raise RuntimeError(sensitive_value)

    response = TestClient(application, raise_server_exceptions=False).get("/explode")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")

    assert response.status_code == 500
    assert "event=http_request_failed method=GET target=other error_type=RuntimeError" in content
    assert sensitive_value not in content


def test_support_log_reader_filters_by_safe_reference(tmp_path) -> None:
    log_path = tmp_path / "app.log"
    log_path.write_text(
        "first trace=REQ-11111111 event=http_request\n"
        "second reference=OP-22222222 event=operator_action\n",
        encoding="utf-8",
    )

    assert support_lines(log_path, reference="OP-22222222") == ["second reference=OP-22222222 event=operator_action"]
    assert support_lines(log_path, tail=1) == ["second reference=OP-22222222 event=operator_action"]


def test_asyncio_handler_classifies_windows_browser_disconnect_without_terminal_escalation(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "async-disconnect" / "app.log")
    event_loop = asyncio.new_event_loop()
    delegated: list[dict[str, object]] = []
    event_loop.set_exception_handler(lambda _loop, context: delegated.append(context))
    try:
        install_asyncio_exception_handler(event_loop)
        installed_handler = event_loop.get_exception_handler()
        assert installed_handler is not None
        private_message = "private browser transport details"
        error = ConnectionResetError(10054, private_message)
        error.winerror = 10054
        installed_handler(event_loop, {"message": private_message, "exception": error})
    finally:
        event_loop.close()

    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "event=client_connection_closed error_type=ConnectionResetError" in content
    assert private_message not in content
    assert delegated == []


def test_asyncio_handler_logs_and_delegates_unexpected_failures_once(tmp_path) -> None:
    log_path = configure_local_logging(tmp_path / "async-failure" / "app.log")
    event_loop = asyncio.new_event_loop()
    delegated: list[dict[str, object]] = []
    event_loop.set_exception_handler(lambda _loop, context: delegated.append(context))
    try:
        install_asyncio_exception_handler(event_loop)
        installed_handler = event_loop.get_exception_handler()
        install_asyncio_exception_handler(event_loop)
        assert event_loop.get_exception_handler() is installed_handler
        assert installed_handler is not None
        private_message = "private asynchronous payload"
        try:
            raise RuntimeError(private_message)
        except RuntimeError as error:
            context: dict[str, object] = {"message": private_message, "exception": error}
            installed_handler(event_loop, context)
    finally:
        event_loop.close()

    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    content = log_path.read_text(encoding="utf-8")
    assert "event=uncaught_async_exception error_type=RuntimeError" in content
    assert private_message not in content
    assert delegated == [context]
