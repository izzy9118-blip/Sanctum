from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import SanctumFederationError


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise SanctumFederationError(f"JSON object repeats key: {key}")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise SanctumFederationError(f"JSON contains non-finite number: {value}")


def parse_json_bytes(raw: bytes, label: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SanctumFederationError(f"{label} is not UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except json.JSONDecodeError as exc:
        raise SanctumFederationError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SanctumFederationError(f"{label} must be a JSON object")
    return value


def read_json(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise SanctumFederationError(f"{label} does not exist: {resolved}")
    raw = resolved.read_bytes()
    return parse_json_bytes(raw, label), raw


def canonical_json_bytes(value: Any) -> bytes:
    """Return the RFC 8785 bytes used by the v1 federation value domain.

    Federation records currently permit strings, integers, booleans, null,
    arrays, and string-keyed objects. Floats are rejected so Python and the
    released Custos adapter cannot disagree about numeric serialization.
    """

    def assert_supported(item: Any) -> None:
        if isinstance(item, float):
            raise SanctumFederationError(
                "Federation integrity values must not contain floating-point numbers"
            )
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise SanctumFederationError(
                        "Federation integrity object keys must be strings"
                    )
                assert_supported(nested)
        elif isinstance(item, list):
            for nested in item:
                assert_supported(nested)
        elif item is not None and not isinstance(item, (str, int, bool)):
            raise SanctumFederationError(
                f"Unsupported federation integrity value: {type(item).__name__}"
            )

    assert_supported(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def object_sha256_without_integrity(value: dict[str, Any]) -> str:
    subject = dict(value)
    subject.pop("integrity", None)
    return hashlib.sha256(canonical_json_bytes(subject)).hexdigest()


def raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_object_integrity(
    value: dict[str, Any],
    digest_field: str,
    label: str,
) -> None:
    integrity = value.get("integrity")
    if not isinstance(integrity, dict):
        raise SanctumFederationError(f"{label} has no integrity object")
    supplied = integrity.get(digest_field)
    if not isinstance(supplied, str):
        raise SanctumFederationError(
            f"{label} has no declared {digest_field}"
        )
    computed = object_sha256_without_integrity(value)
    if supplied != computed:
        raise SanctumFederationError(
            f"{label} integrity mismatch: {supplied} != {computed}"
        )


def schema_errors(value: Any, schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(
        validator.iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    messages: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        messages.append(f"{location}: {error.message}")
    return messages


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    label: str,
) -> None:
    errors = schema_errors(value, schema)
    if errors:
        raise SanctumFederationError(
            f"{label} failed schema validation: {errors[0]}"
        )


def parse_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise SanctumFederationError(f"{label} must be an ISO 8601 string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise SanctumFederationError(
            f"{label} is not a valid ISO 8601 date-time"
        ) from exc
    if parsed.tzinfo is None:
        raise SanctumFederationError(f"{label} must include a timezone")
    return parsed


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso8601(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def write_json_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
