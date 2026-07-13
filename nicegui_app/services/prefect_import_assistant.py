"""Optional DeepSeek adapter for schema-only prefect import assistance.

Only the displayed column headings and locally derived value kinds leave the
computer. Raw rows, Chinese names contained in those rows, API credentials,
and import results never enter logs or the request payload. The returned
mapping remains a suggestion that the operator must preview before the
existing workflow can write anything.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import socket
from typing import Any, Callable
from urllib import error as url_error
from urllib import request as url_request

from nicegui_app.utils.prefect_file_import import (
    TARGET_FIELDS,
    ParsedImportFile,
    profile_columns,
    validate_target_mapping,
)


DEEPSEEK_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
ALLOWED_DEEPSEEK_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})
MAX_RESPONSE_BYTES = 256 * 1024


class ImportAssistantError(RuntimeError):
    """A safe, operator-facing failure from the optional external adapter."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ImportAssistantStatus:
    enabled: bool
    configured: bool
    model: str

    @property
    def ready(self) -> bool:
        return self.enabled and self.configured and self.model in ALLOWED_DEEPSEEK_MODELS


@dataclass(frozen=True)
class MappingSuggestion:
    target_to_source: dict[str, str]
    model: str
    suggested_target_count: int


Transport = Callable[[dict[str, Any], str, float], dict[str, Any]]


def import_assistant_status() -> ImportAssistantStatus:
    model = os.getenv("SING_YIN_DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL).strip()
    enabled = os.getenv("SING_YIN_DEEPSEEK_ENABLED", "false").strip().casefold() in {"1", "true", "yes", "on"}
    configured = bool(os.getenv("SING_YIN_DEEPSEEK_API_KEY", "").strip())
    return ImportAssistantStatus(enabled=enabled, configured=configured, model=model)


def suggest_deepseek_column_mapping(
    parsed: ParsedImportFile,
    *,
    existing_mapping: dict[str, str] | None = None,
    transport: Transport | None = None,
) -> MappingSuggestion:
    status = import_assistant_status()
    if not status.enabled:
        raise ImportAssistantError("disabled", "DeepSeek column assistance is disabled in local settings.")
    if not status.configured:
        raise ImportAssistantError("missing_key", "DeepSeek column assistance has no local API key configured.")
    if status.model not in ALLOWED_DEEPSEEK_MODELS:
        raise ImportAssistantError(
            "model_unapproved",
            "The configured DeepSeek model is not approved for import assistance.",
        )
    api_key = os.getenv("SING_YIN_DEEPSEEK_API_KEY", "").strip()
    current = dict(existing_mapping or {})
    used_sources = set(current.values())
    remaining_targets = [target for target in TARGET_FIELDS if target not in current]
    columns = [
        {
            "source": profile.header,
            "valueKinds": list(profile.value_kinds),
            "nonEmptyCountBucket": _count_bucket(profile.non_empty_count),
        }
        for profile in profile_columns(parsed)
        if profile.header not in used_sources
    ]
    if not remaining_targets or not columns:
        return MappingSuggestion(current, status.model, 0)

    payload = {
        "model": status.model,
        "thinking": {"type": "disabled"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You map spreadsheet column headings to an approved Study Prefect import schema. "
                    "Return JSON only. Never infer or transform student records. Use only the exact source "
                    "headings and target codes supplied. Omit uncertain mappings."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "task": "suggest_column_mapping",
                        "allowedTargets": remaining_targets,
                        "columns": columns,
                        "responseSchema": {
                            "mapping": [{"source": "exact source heading", "target": "approved target code"}]
                        },
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
        "max_tokens": 600,
    }
    response = (transport or _post_json)(payload, api_key, 8.0)
    try:
        content = response["choices"][0]["message"]["content"]
        result = json.loads(content)
        suggestions = result["mapping"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise ImportAssistantError("invalid_response", "DeepSeek returned an invalid column-mapping response.") from error
    if not isinstance(suggestions, list):
        raise ImportAssistantError("invalid_response", "DeepSeek returned an invalid column-mapping response.")

    available_sources = {profile.header for profile in profile_columns(parsed)}
    added = 0
    for item in suggestions:
        if not isinstance(item, dict):
            raise ImportAssistantError("invalid_item", "DeepSeek returned an invalid column-mapping item.")
        source = item.get("source")
        target = item.get("target")
        if not isinstance(source, str) or source not in available_sources:
            raise ImportAssistantError(
                "source_outside_file",
                "DeepSeek referred to a column that is not in the selected file.",
            )
        if not isinstance(target, str) or target not in remaining_targets:
            raise ImportAssistantError(
                "target_outside_schema",
                "DeepSeek suggested a target outside the approved import schema.",
            )
        if source in current.values() or target in current:
            raise ImportAssistantError("duplicate_mapping", "DeepSeek suggested a duplicate column mapping.")
        current[target] = source
        added += 1

    # Full validation is intentionally deferred until all required fields are
    # present; partial suggestions remain useful for the operator's controls.
    if set(current) >= set(TARGET_FIELDS) - {"remarks"}:
        validate_target_mapping(current, parsed.headers)
    return MappingSuggestion(current, status.model, added)


def _post_json(payload: dict[str, Any], api_key: str, timeout: float) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    request = url_request.Request(
        DEEPSEEK_CHAT_COMPLETIONS_URL,
        data=encoded,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SingYinRoster/1.0",
        },
    )
    try:
        # The request target is the module-owned, literal HTTPS DeepSeek endpoint
        # above; neither workbook content nor operator input can select a URL.
        with url_request.urlopen(request, timeout=timeout) as response:  # nosec B310
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except url_error.HTTPError as error:
        if error.code == 401:
            raise ImportAssistantError("credential_rejected", "DeepSeek rejected the local API credential.") from error
        if error.code == 429:
            raise ImportAssistantError(
                "rate_limited",
                "DeepSeek is temporarily rate-limited; use manual mapping or try again later.",
            ) from error
        raise ImportAssistantError(
            "unavailable",
            "DeepSeek column assistance is temporarily unavailable.",
        ) from error
    except (url_error.URLError, TimeoutError, socket.timeout) as error:
        raise ImportAssistantError(
            "timeout",
            "DeepSeek did not respond in time; use manual mapping or try again later.",
        ) from error
    if len(body) > MAX_RESPONSE_BYTES:
        raise ImportAssistantError("response_too_large", "DeepSeek returned an unexpectedly large response.")
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImportAssistantError("unreadable_response", "DeepSeek returned an unreadable response.") from error
    if not isinstance(decoded, dict):
        raise ImportAssistantError("invalid_response", "DeepSeek returned an invalid response.")
    return decoded


def _count_bucket(count: int) -> str:
    if count == 0:
        return "NONE"
    if count <= 5:
        return "ONE_TO_FIVE"
    if count <= 50:
        return "SIX_TO_FIFTY"
    return "OVER_FIFTY"


__all__ = [
    "ALLOWED_DEEPSEEK_MODELS",
    "DEEPSEEK_CHAT_COMPLETIONS_URL",
    "DEFAULT_DEEPSEEK_MODEL",
    "ImportAssistantError",
    "ImportAssistantStatus",
    "MappingSuggestion",
    "import_assistant_status",
    "suggest_deepseek_column_mapping",
]
