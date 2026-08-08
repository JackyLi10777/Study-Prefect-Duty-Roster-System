"""Bounded public support submissions stored outside roster transactions."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os
from typing import Any, AsyncIterable, Mapping

from nicegui_app.application_mode import current_application_mode
from nicegui_app.config import POLICY_VERSION
from nicegui_app.release_evidence import release_source_fingerprint
from nicegui_app.services.support_incidents import (
    IncidentReportInput,
    IncidentValidationError,
    REQ_REFERENCE_PATTERN,
    SupportInbox,
)


PUBLIC_SUPPORT_MAX_BODY_BYTES = 16_384
_ALLOWED_FIELDS = frozenset(
    {
        "source",
        "category",
        "expected_behavior",
        "actual_behavior",
        "reproduction_steps",
        "impact",
    }
)
_SOURCE_ROUTES = {"public_entrance": "getting_started", "public_viewer": "viewer"}
_CATEGORY_ROUTES = {
    "viewer": "viewer",
    "access": "access_control",
    "display": "other",
    "other": "other",
}


class PublicSupportRequestTooLarge(ValueError):
    """Raised before a public support request can exceed its memory budget."""


async def read_bounded_public_support_body(
    chunks: AsyncIterable[bytes],
    *,
    maximum_bytes: int = PUBLIC_SUPPORT_MAX_BODY_BYTES,
) -> bytes:
    """Read a streamed request without ever accepting more than ``maximum_bytes``."""

    if maximum_bytes < 1:
        raise ValueError("maximum_bytes must be positive")
    body = bytearray()
    async for chunk in chunks:
        if len(body) + len(chunk) > maximum_bytes:
            raise PublicSupportRequestTooLarge("public support request is too large")
        body.extend(chunk)
    return bytes(body)


@dataclass(frozen=True)
class PublicSupportSubmission:
    incident_id: str


def _bounded_text(value: object, *, maximum: int, required: bool = False) -> str:
    if not isinstance(value, str):
        raise IncidentValidationError("public support text fields must be strings")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if required and not normalized:
        raise IncidentValidationError("required public support field is empty")
    if len(normalized) > maximum:
        raise IncidentValidationError("public support field exceeds its limit")
    return normalized


def report_from_public_payload(payload: object) -> IncidentReportInput:
    """Validate an exact, text-only public payload before storage sanitization."""

    if not isinstance(payload, Mapping) or set(payload) != _ALLOWED_FIELDS:
        raise IncidentValidationError("public support payload shape is invalid")
    source = payload.get("source")
    category = payload.get("category")
    if source not in _SOURCE_ROUTES or category not in _CATEGORY_ROUTES:
        raise IncidentValidationError("public support source or category is invalid")
    steps_text = _bounded_text(payload.get("reproduction_steps"), maximum=1_600, required=True)
    steps = tuple(line.strip() for line in steps_text.split("\n") if line.strip())
    if not steps:
        raise IncidentValidationError("reproduction steps are required")
    route_category = _CATEGORY_ROUTES[str(category)]
    if source == "public_viewer" and category == "other":
        route_category = _SOURCE_ROUTES[str(source)]
    return IncidentReportInput(
        source="public_ui",
        actor_mode="public",
        route_category=route_category,
        workflow_action="page_view",
        expected_behavior=_bounded_text(payload.get("expected_behavior"), maximum=1_200, required=True),
        actual_behavior=_bounded_text(payload.get("actual_behavior"), maximum=1_200, required=True),
        reproduction_steps=steps,
        impact=_bounded_text(payload.get("impact"), maximum=800),
    )


def create_public_support_incident(
    payload: object,
    *,
    request_reference: str = "",
    inbox: SupportInbox | None = None,
) -> PublicSupportSubmission:
    """Create a redacted local incident and return only its non-secret reference."""

    report = report_from_public_payload(payload)
    fingerprint, _ = release_source_fingerprint()
    references = (
        (request_reference,)
        if isinstance(request_reference, str) and REQ_REFERENCE_PATTERN.fullmatch(request_reference)
        else ()
    )
    report = replace(report, request_references=references)
    summary = (inbox or SupportInbox()).create_incident(
        report,
        application_version=os.getenv("SING_YIN_RELEASE_VERSION", POLICY_VERSION),
        source_fingerprint=fingerprint,
        application_mode=current_application_mode().mode,
        environment={"submission_channel": "public_gateway"},
        health_summary={"capture": "ok"},
        attachments=(),
    )
    return PublicSupportSubmission(incident_id=summary.incident_id)


__all__ = [
    "PUBLIC_SUPPORT_MAX_BODY_BYTES",
    "PublicSupportSubmission",
    "create_public_support_incident",
    "report_from_public_payload",
]
