from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .errors import SanctumFederationError
from .integrity import read_json, validate_schema


@dataclass(frozen=True)
class ContractSet:
    repository_root: Path
    inquiry_envelope: dict[str, Any]
    minister_manifest: dict[str, Any]
    ministerial_report: dict[str, Any]
    secretary_validation_record: dict[str, Any]
    dispatch_config: dict[str, Any]
    dispatch_receipt: dict[str, Any]

    @classmethod
    def load(cls, repository_root: Path) -> "ContractSet":
        root = repository_root.expanduser().resolve()
        filenames = {
            "inquiry_envelope": "inquiry-envelope.schema.json",
            "minister_manifest": "minister-manifest.schema.json",
            "ministerial_report": "ministerial-report.schema.json",
            "secretary_validation_record": (
                "secretary-validation-record.schema.json"
            ),
            "dispatch_config": "dispatch-config.schema.json",
            "dispatch_receipt": "dispatch-receipt.schema.json",
        }
        loaded: dict[str, dict[str, Any]] = {}
        for name, filename in filenames.items():
            value, _ = read_json(root / filename, f"{name} schema")
            try:
                Draft202012Validator.check_schema(value)
            except Exception as exc:
                raise SanctumFederationError(
                    f"{filename} is not a valid Draft 2020-12 schema"
                ) from exc
            loaded[name] = value
        return cls(repository_root=root, **loaded)

    def validate_envelope(self, value: dict[str, Any]) -> None:
        validate_schema(value, self.inquiry_envelope, "Inquiry Envelope")

    def validate_manifest(self, value: dict[str, Any]) -> None:
        validate_schema(value, self.minister_manifest, "Minister Manifest")

    def validate_report(self, value: dict[str, Any]) -> None:
        validate_schema(value, self.ministerial_report, "Ministerial Report")

    def validate_secretary_record(self, value: dict[str, Any]) -> None:
        validate_schema(
            value,
            self.secretary_validation_record,
            "Secretary Validation Record",
        )

    def validate_dispatch_config(self, value: dict[str, Any]) -> None:
        validate_schema(value, self.dispatch_config, "Dispatch Config")

    def validate_dispatch_receipt(self, value: dict[str, Any]) -> None:
        validate_schema(value, self.dispatch_receipt, "Dispatch Receipt")
