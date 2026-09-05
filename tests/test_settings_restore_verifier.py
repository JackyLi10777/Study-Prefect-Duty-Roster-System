import pytest

from scripts.verify_settings_restore import _server_diagnostics


def test_only_the_deliberate_staged_checksum_failure_is_accepted():
    expected = ("WARNING event=operator_action_failed reference=OP-FICTIONAL "
                "action=progress_restore_working error_type=WorkflowError location=_stage_restore_source")
    assert _server_diagnostics(expected, mode="local_maintenance")["expectedChecksumFailureCount"] == 1
    assert _server_diagnostics("INFO clean shutdown", mode="guest")["serverErrorCount"] == 0


@pytest.mark.parametrize("log,mode", [
    ('ERROR [nicegui] Method "focus" not found.', "guest"),
    ("Traceback (most recent call last):", "guest"),
    ("INFO no checksum failure observed", "local_maintenance"),
    ("WARNING event=operator_action_failed action=wrong error_type=WorkflowError", "local_maintenance"),
    ("WARNING event=operator_action_failed action=progress_restore_working error_type=WorkflowError location=_stage_restore_source", "guest"),
])
def test_unexpected_or_missing_server_failure_is_not_silently_ignored(log, mode):
    with pytest.raises(AssertionError):
        _server_diagnostics(log, mode=mode)
