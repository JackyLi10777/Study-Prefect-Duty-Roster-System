"""Versioned product and institutional identity contract.

Service Weave identifies the software product.  The Sing Yin crest remains a
separate institutional mark.  This module turns the framework-neutral JSON
manifest into immutable, digest-bearing values for NiceGUI and release checks.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Mapping

from nicegui_app.config import PROJECT_ROOT


SOURCE_PATH = PROJECT_ROOT / "design_system" / "product-identity.v1.json"
_SUPPORTED_CONTRACT_VERSION = "1.0.0"
_WORKER_DIGEST = re.compile(
    r"SERVICE_WEAVE_FAVICON_SHA256\s*=\s*['\"](?P<digest>[a-f0-9]{64})['\"]"
)


class ProductIdentityContractError(ValueError):
    """Raised when the identity manifest is incomplete or unsafe."""


@dataclass(frozen=True)
class BrandAssetVariant:
    """One approved asset variant with a verified content digest."""

    key: str
    theme: str
    purpose: str
    relative_path: str
    public_url: str | None
    sha256: str

    @property
    def path(self) -> Path:
        return PROJECT_ROOT / self.relative_path


@dataclass(frozen=True)
class ProductIdentity:
    """Immutable names, marks, accessible labels, version, and asset digest."""

    product_name_zh: str
    product_name_en: str
    functional_name_zh: str
    functional_name_en: str
    product_mark_variants: tuple[BrandAssetVariant, ...]
    institutional_crest_variants: tuple[BrandAssetVariant, ...]
    accessible_names: Mapping[str, Mapping[str, str]]
    asset_version: str
    digest: str
    delivery: Mapping[str, str]

    def product_name(self, locale: str) -> str:
        return self.product_name_en if locale == "en" else self.product_name_zh

    def functional_name(self, locale: str) -> str:
        return self.functional_name_en if locale == "en" else self.functional_name_zh

    def accessible_name(self, identity: str, locale: str) -> str:
        names = self.accessible_names[identity]
        return names.get(locale, names["zh-HK"])

    def product_asset(self, key: str) -> BrandAssetVariant:
        return _variant_by_key(self.product_mark_variants, key)

    def crest_asset(self, key: str) -> BrandAssetVariant:
        return _variant_by_key(self.institutional_crest_variants, key)


def _variant_by_key(
    variants: tuple[BrandAssetVariant, ...], key: str
) -> BrandAssetVariant:
    for variant in variants:
        if variant.key == key:
            return variant
    raise KeyError(key)


def _safe_project_file(relative_path: object) -> tuple[str, Path]:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ProductIdentityContractError("Asset relativePath must be a non-empty string")
    raw_path = Path(relative_path)
    if raw_path.is_absolute():
        raise ProductIdentityContractError("Identity assets must use project-relative paths")
    resolved = (PROJECT_ROOT / raw_path).resolve()
    try:
        resolved.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ProductIdentityContractError(
            f"Identity asset escapes the project root: {relative_path}"
        ) from exc
    return raw_path.as_posix(), resolved


def _asset_variant(raw: Mapping[str, Any]) -> BrandAssetVariant:
    required = ("key", "theme", "purpose", "relativePath")
    missing = [
        name
        for name in required
        if not isinstance(raw.get(name), str) or not raw[name].strip()
    ]
    if missing:
        raise ProductIdentityContractError(
            "Identity asset is missing fields: " + ", ".join(missing)
        )
    relative_path, path = _safe_project_file(raw["relativePath"])
    if not path.is_file():
        raise ProductIdentityContractError(f"Missing identity asset: {relative_path}")
    public_url = raw.get("publicUrl")
    if public_url is not None and (
        not isinstance(public_url, str) or not public_url.startswith("/assets/")
    ):
        raise ProductIdentityContractError(
            f"Invalid public asset URL for {raw['key']}: {public_url!r}"
        )
    return BrandAssetVariant(
        key=raw["key"],
        theme=raw["theme"],
        purpose=raw["purpose"],
        relative_path=relative_path,
        public_url=public_url,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _localized(raw: object, field: str) -> Mapping[str, str]:
    if not isinstance(raw, Mapping):
        raise ProductIdentityContractError(f"{field} must be a locale mapping")
    values = {locale: raw.get(locale) for locale in ("zh-HK", "en")}
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ProductIdentityContractError(f"{field} requires zh-HK and en values")
    return MappingProxyType(values)  # type: ignore[arg-type]


def _unique_variants(
    raw_variants: object, field: str
) -> tuple[BrandAssetVariant, ...]:
    if not isinstance(raw_variants, list) or not raw_variants:
        raise ProductIdentityContractError(f"{field} must be a non-empty list")
    variants = tuple(_asset_variant(raw) for raw in raw_variants if isinstance(raw, Mapping))
    if len(variants) != len(raw_variants):
        raise ProductIdentityContractError(f"{field} contains a non-object entry")
    keys = [variant.key for variant in variants]
    paths = [variant.relative_path for variant in variants]
    if len(keys) != len(set(keys)):
        raise ProductIdentityContractError(f"{field} contains duplicate keys")
    if len(paths) != len(set(paths)):
        raise ProductIdentityContractError(f"{field} contains duplicate files")
    return variants


def _identity_digest(
    *,
    contract_version: str,
    asset_version: str,
    names: tuple[str, ...],
    variants: tuple[BrandAssetVariant, ...],
) -> str:
    payload = {
        "contractVersion": contract_version,
        "assetVersion": asset_version,
        "names": names,
        "assets": [
            {
                "key": variant.key,
                "path": variant.relative_path,
                "sha256": variant.sha256,
            }
            for variant in variants
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1)
def load_product_identity() -> ProductIdentity:
    """Load the canonical identity manifest and bind it to current asset bytes."""

    raw = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    contract_version = raw.get("contractVersion")
    if contract_version != _SUPPORTED_CONTRACT_VERSION:
        raise ProductIdentityContractError("Unsupported product-identity contract version")
    asset_version = raw.get("assetVersion")
    if not isinstance(asset_version, str) or not asset_version.strip():
        raise ProductIdentityContractError("assetVersion must be a non-empty string")

    product_name = _localized(raw.get("productName"), "productName")
    functional_name = _localized(raw.get("functionalName"), "functionalName")
    accessible_raw = raw.get("accessibleNames")
    if not isinstance(accessible_raw, Mapping):
        raise ProductIdentityContractError("accessibleNames must be an object")
    accessible_names = MappingProxyType(
        {
            identity: _localized(accessible_raw.get(identity), f"accessibleNames.{identity}")
            for identity in ("productMark", "institutionalCrest")
        }
    )
    product_variants = _unique_variants(raw.get("productMarkVariants"), "productMarkVariants")
    crest_variants = _unique_variants(
        raw.get("institutionalCrestVariants"), "institutionalCrestVariants"
    )
    delivery_raw = raw.get("delivery")
    if not isinstance(delivery_raw, Mapping) or any(
        not isinstance(value, str) or not value.strip() for value in delivery_raw.values()
    ):
        raise ProductIdentityContractError("delivery must contain non-empty string values")
    delivery = MappingProxyType(dict(delivery_raw))

    for delivery_key in (
        "faviconVariant",
        "navigationLightVariant",
        "navigationDarkVariant",
        "windowsVariant",
    ):
        _variant_by_key(product_variants, delivery[delivery_key])
    _safe_project_file(delivery["workerGeneratedModule"])

    names = (
        product_name["zh-HK"],
        product_name["en"],
        functional_name["zh-HK"],
        functional_name["en"],
        accessible_names["productMark"]["zh-HK"],
        accessible_names["productMark"]["en"],
        accessible_names["institutionalCrest"]["zh-HK"],
        accessible_names["institutionalCrest"]["en"],
    )
    all_variants = (*product_variants, *crest_variants)
    return ProductIdentity(
        product_name_zh=product_name["zh-HK"],
        product_name_en=product_name["en"],
        functional_name_zh=functional_name["zh-HK"],
        functional_name_en=functional_name["en"],
        product_mark_variants=product_variants,
        institutional_crest_variants=crest_variants,
        accessible_names=accessible_names,
        asset_version=asset_version,
        digest=_identity_digest(
            contract_version=contract_version,
            asset_version=asset_version,
            names=names,
            variants=all_variants,
        ),
        delivery=delivery,
    )


def product_identity_drift(identity: ProductIdentity | None = None) -> list[str]:
    """Return delivery drift without modifying any brand asset."""

    active = identity or load_product_identity()
    drift: list[str] = []
    worker_path = PROJECT_ROOT / active.delivery["workerGeneratedModule"]
    if not worker_path.is_file():
        return [f"missing Worker brand delivery: {worker_path.relative_to(PROJECT_ROOT)}"]
    match = _WORKER_DIGEST.search(worker_path.read_text(encoding="utf-8"))
    favicon = active.product_asset(active.delivery["faviconVariant"])
    if match is None:
        drift.append("Worker brand delivery does not expose its favicon digest")
    elif match.group("digest") != favicon.sha256:
        drift.append("Worker Service Weave favicon differs from the identity contract")
    return drift


PRODUCT_IDENTITY = load_product_identity()


__all__ = (
    "BrandAssetVariant",
    "PRODUCT_IDENTITY",
    "ProductIdentity",
    "ProductIdentityContractError",
    "SOURCE_PATH",
    "load_product_identity",
    "product_identity_drift",
)
