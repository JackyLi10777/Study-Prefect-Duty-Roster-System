from __future__ import annotations

from dataclasses import dataclass

from scripts.verify_public_entry_music import _observe_entry_route


@dataclass(frozen=True)
class _Request:
    url: str


class _Route:
    def __init__(self, url: str) -> None:
        self.request = _Request(url=url)
        self.fulfillment: dict[str, object] | None = None

    def fulfill(self, **kwargs: object) -> None:
        self.fulfillment = kwargs


def test_entry_observer_preserves_the_entrance_document_with_no_content() -> None:
    route = _Route("https://example.test/auth/login")
    requests: list[str] = []

    _observe_entry_route(route, requests)  # type: ignore[arg-type]

    assert requests == ["https://example.test/auth/login"]
    assert route.fulfillment == {
        "status": 204,
        "headers": {"Cache-Control": "no-store"},
        "body": b"",
    }
