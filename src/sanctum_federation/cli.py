from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contracts import ContractSet
from .dispatcher import AssemblyDispatcher
from .errors import SanctumFederationError
from .integrity import read_json, verify_object_integrity, write_json_exclusive
from .registry import RegistrySnapshot
from .secretary import SecretaryValidator


def dispatch_command(args: argparse.Namespace) -> int:
    result = AssemblyDispatcher(
        sanctum_root=Path(args.sanctum_root),
        secretary_actor_id=args.secretary_actor_id,
        max_workers=args.max_workers,
    ).dispatch(
        envelope_path=Path(args.envelope),
        adapter_config_path=Path(args.adapter_config),
        output_dir=Path(args.output),
    )
    print(result)
    return 0


def validate_report_command(args: argparse.Namespace) -> int:
    sanctum_root = Path(args.sanctum_root).expanduser().resolve()
    contracts = ContractSet.load(sanctum_root)
    envelope, _ = read_json(Path(args.envelope), "Inquiry Envelope")
    contracts.validate_envelope(envelope)
    verify_object_integrity(
        envelope,
        "envelope_sha256",
        "Inquiry Envelope",
    )
    registry = RegistrySnapshot.load(sanctum_root, contracts)
    sanctum_commit = registry.verify_checkout_and_envelope(envelope)
    selected = {
        entry.minister_id: entry
        for entry in registry.selected_entries(envelope)
    }
    if args.minister_id not in selected:
        raise SanctumFederationError(
            f"Minister is not selected by this envelope: {args.minister_id}"
        )
    entry = selected[args.minister_id]
    report_path = Path(args.report).expanduser().resolve()
    if not report_path.is_file():
        raise SanctumFederationError(
            f"Ministerial Report does not exist: {report_path}"
        )
    result = SecretaryValidator(
        contracts,
        registry,
        secretary_actor_id=args.secretary_actor_id,
        repository_roots={
            entry.repository_full_name: Path(args.minister_repo_root)
        },
        sanctum_commit=sanctum_commit,
    ).validate_report_bytes(
        envelope,
        report_path.read_bytes(),
        entry,
    )
    output = Path(args.output).expanduser().resolve()
    if output.exists():
        raise FileExistsError(
            f"Secretary Validation Record already exists: {output}"
        )
    write_json_exclusive(output, result.record)
    print(output)
    return 0 if result.validated else 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sanctum-federation")
    subcommands = parser.add_subparsers(dest="command", required=True)

    dispatch = subcommands.add_parser(
        "dispatch",
        help=(
            "Validate and dispatch one immutable Inquiry Envelope to selected "
            "minister adapters, then create separate Secretary validations."
        ),
    )
    dispatch.add_argument("--sanctum-root", required=True)
    dispatch.add_argument("--envelope", required=True)
    dispatch.add_argument("--adapter-config", required=True)
    dispatch.add_argument("--output", required=True)
    dispatch.add_argument(
        "--secretary-actor-id",
        default="SANCTUM-CONSTITUTIONAL-SECRETARY",
    )
    dispatch.add_argument("--max-workers", type=int, default=4)
    dispatch.set_defaults(handler=dispatch_command)

    validate = subcommands.add_parser(
        "validate-report",
        help=(
            "Create a separate documentary Secretary Validation Record for "
            "one submitted Ministerial Report."
        ),
    )
    validate.add_argument("--sanctum-root", required=True)
    validate.add_argument("--envelope", required=True)
    validate.add_argument("--report", required=True)
    validate.add_argument("--minister-id", required=True)
    validate.add_argument("--minister-repo-root", required=True)
    validate.add_argument("--output", required=True)
    validate.add_argument(
        "--secretary-actor-id",
        default="SANCTUM-CONSTITUTIONAL-SECRETARY",
    )
    validate.set_defaults(handler=validate_report_command)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (SanctumFederationError, FileExistsError) as exc:
        print(
            json.dumps(
                {
                    "status": "REJECTED",
                    "error": type(exc).__name__,
                    "detail": str(exc),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
