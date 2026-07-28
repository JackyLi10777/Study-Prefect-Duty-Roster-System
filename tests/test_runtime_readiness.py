from nicegui_app.main import compose_readiness_payload


def test_readiness_requires_database_maintenance_and_recovery_to_be_clear() -> None:
    payload, status = compose_readiness_payload(
        {"status": "ok", "application": "sing-yin-roster"},
        {
            "workflowInitialized": True,
            "maintenance": False,
            "recoveryRequired": False,
            "guestSessions": 2,
        },
    )
    assert status == 200
    assert payload["status"] == "ready"
    assert payload["writeReady"] is True

    for runtime in (
        {"workflowInitialized": False, "maintenance": False, "recoveryRequired": False},
        {"workflowInitialized": True, "maintenance": True, "recoveryRequired": False},
        {"workflowInitialized": True, "maintenance": False, "recoveryRequired": True},
    ):
        payload, status = compose_readiness_payload(
            {"status": "ok"},
            runtime,
        )
        assert status == 503
        assert payload["status"] == "degraded"
        assert payload["writeReady"] is False
