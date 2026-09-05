import pytest

from scripts.verify_settings_restore import _server_diagnostics
from scripts.verify_release_candidate import ReleaseVerificationError


def test_only_the_deliberate_staged_checksum_failure_is_accepted(tmp_path):
    expected = ("WARNING event=operator_action_failed reference=OP-FICTIONAL "
                "action=progress_restore_working error_type=WorkflowError location=_stage_restore_source")
    log_path = tmp_path / "server.log"
    log_path.write_text(expected, encoding="utf-8")
    assert _server_diagnostics(log_path, mode="local_maintenance")["expectedChecksumFailureCount"] == 1
    log_path.write_text("INFO clean shutdown", encoding="utf-8")
    assert _server_diagnostics(log_path, mode="guest")["serverErrorCount"] == 0


@pytest.mark.parametrize("log,mode", [
    ('ERROR [nicegui] Method "focus" not found.', "guest"),
    ("CRITICAL unexpected server failure", "guest"),
    ("Task exception was never retrieved", "guest"),
    ("Traceback (most recent call last):", "guest"),
    ("INFO no checksum failure observed", "local_maintenance"),
    ("WARNING event=operator_action_failed action=wrong error_type=WorkflowError", "local_maintenance"),
    ("WARNING event=operator_action_failed action=progress_restore_working error_type=WorkflowError location=_stage_restore_source", "guest"),
])
def test_unexpected_or_missing_server_failure_is_not_silently_ignored(log, mode, tmp_path):
    log_path = tmp_path / "server.log"
    log_path.write_text(log, encoding="utf-8")
    with pytest.raises((AssertionError, ReleaseVerificationError)):
        _server_diagnostics(log_path, mode=mode)
