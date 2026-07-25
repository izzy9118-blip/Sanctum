#!/usr/bin/env python3
"""Sanctum end-to-end constitutional articulation harness.

Runs one bounded, disposable inquiry through:

    raw intake -> dismantling -> universal participation
               -> disconfirming retrieval -> synthesis -> Validation Gate

The harness writes only to a temporary workspace. It never mutates the committed
registry, corpus, inquiries, or projections. Success means the organs exchange
cross-referenced records that the Gate accepts.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import sys
import tempfile

import yaml

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / "gate"))
sys.path.insert(0, str(BASE / "projection"))

import gate  # type: ignore  # noqa: E402
import projection  # type: ignore  # noqa: E402

ENV_COMMIT = "env01"


def prov(actor: str, commit: str, consumed=None, projection_version=None):
    value = {
        "produced_by": {"actor": actor, "commit": commit},
        "consumed_records": consumed or [],
    }
    if projection_version:
        value["projection_version"] = projection_version
    return value


def intake(raw: str):
    return {
        "record_type": "inquiry_envelope",
        "id": "inq-e2e",
        "raw_situation": raw,
        "source": "e2e-harness",
        "provenance": prov("intake", ENV_COMMIT),
    }


def dismantling_organ(envelope):
    return {
        "record_type": "dismantling_record",
        "id": "dis-e2e",
        "inquiry_ref": {"ref": envelope["id"], "commit": ENV_COMMIT},
        "raw_submission": envelope["raw_situation"],
        "extracted_claims_and_presuppositions": [
            "the situation asserts a necessity"
        ],
        "framing_sources": ["e2e-harness"],
        "documented_acts_events_material_conditions": [
            "a bounded, trivial fact"
        ],
        "supporting_evidence": [
            {"for": "the fact", "evidence": "harness-fixed"}
        ],
        "disconfirming_evidence": [
            {
                "complicates": "the necessity claim",
                "evidence": "the same words could equally serve appetite",
            }
        ],
        "unresolved_ambiguities": ["none material for a trivial run"],
        "transformation_rules_applied": [
            "stripped rhetoric to an attributed claim"
        ],
        "excluded_material": [
            {"item": "harness noise", "reason": "not documentary"}
        ],
        "classifications": [],
        "juxtapositions": [],
        "provenance": prov(
            "dismantling-organ",
            "dis01",
            [{"ref": envelope["id"], "commit": ENV_COMMIT}],
        ),
    }


def registry():
    return [
        {
            "record_type": "minister_manifest",
            "id": minister_id,
            "title": "Placeholder Minister",
            "jurisdiction": "a distinct test ground",
            "gate_posture": "dual_gate_foundational",
            "proposition_kinds": [
                "documented_finding",
                "supported_inference",
            ],
            "provenance": prov("registry", "reg01"),
        }
        for minister_id in ("alpha", "beta")
    ]


def _write_fixture_corpus(corpus_dir: Path) -> None:
    corpus_dir.mkdir(parents=True, exist_ok=True)
    deed = {
        "record_type": "decision_object",
        "id": "deed-disconfirming",
        "commit": "deed01",
        "condition": "height",
        "embarrasses": ["maximal-victory-is-the-aim"],
        "conclusion": "durability may require denying force its immediate winnings",
        "propositions": [
            {
                "kind": "documented_finding",
                "claim": "a bounded deed complicates the maximal-victory framing",
            }
        ],
    }
    (corpus_dir / "deed-disconfirming.yaml").write_text(
        yaml.safe_dump(deed, sort_keys=False), encoding="utf-8"
    )


def minister_reason(manifest, dismantling, projections):
    disconfirming = projection.retrieve_disconfirming(
        "height", ["maximal-victory-is-the-aim"], projections
    )
    if not disconfirming:
        raise RuntimeError("the disconfirming retrieval fixture returned no deed")
    deed = disconfirming[0]
    consumed = [
        {"ref": dismantling["id"], "commit": "dis01"},
        {
            "ref": deed["projects"]["ref"],
            "commit": deed["projects"]["commit"],
        },
    ]
    return {
        "record_type": "ministerial_report",
        "id": f"rep-{manifest['id']}",
        "inquiry_ref": {"ref": "inq-e2e", "commit": ENV_COMMIT},
        "minister": {"actor": manifest["id"], "manifest_commit": "reg01"},
        "mode": "reasoned",
        "propositions": [
            {
                "kind": "documented_finding",
                "claim": "a bounded fact obtains",
                "grounds": [{"ref": "harness-fixed", "commit": "h1"}],
            },
            {
                "kind": "supported_inference",
                "claim": "deny force its winnings — the durable reading",
                "confronted_with": deed["projects"]["ref"],
            },
        ],
        "provenance": prov(
            manifest["id"],
            f"{manifest['id']}01",
            consumed,
            deed["projection_version"],
        ),
    }


def secretary(reports):
    assessment = [
        {
            "minister": report["minister"]["actor"],
            "conclusion": "deny force its winnings",
            "ground": (
                f"{report['minister']['actor']} reaches it from the durability "
                "of a lawful order"
            ),
        }
        for report in reports
    ]
    return {
        "record_type": "synthesis",
        "id": "syn-e2e",
        "inquiry_ref": {"ref": "inq-e2e", "commit": ENV_COMMIT},
        "convergence_assessment": assessment,
        "grounds_converge": True,
        "shared_ground": (
            "both reach the same conclusion independently from the durability "
            "of a lawful order"
        ),
        "converging_ministers": [
            report["minister"]["actor"] for report in reports
        ],
        "provenance": prov(
            "secretary",
            "sec01",
            [
                {
                    "ref": report["id"],
                    "commit": f"{report['minister']['actor']}01",
                }
                for report in reports
            ],
        ),
    }


def _emit(inquiry_dir: Path, record, name: str, seams: list[str]) -> None:
    if record["record_type"] != "inquiry_envelope":
        ref = record.get("inquiry_ref", {}).get("ref")
        if ref != "inq-e2e":
            seams.append(
                f"{name}: inquiry_ref {ref!r} does not match envelope 'inq-e2e'"
            )
    (inquiry_dir / name).write_text(
        yaml.safe_dump(record, sort_keys=False), encoding="utf-8"
    )


def run_assembly(raw: str) -> int:
    workspace = Path(tempfile.mkdtemp(prefix="sanctum-e2e-"))
    try:
        inquiry_dir = workspace / "inquiries" / "e2e"
        registry_dir = workspace / "registry"
        corpus_dir = workspace / "corpus"
        projection_dir = workspace / "projections"
        inquiry_dir.mkdir(parents=True)
        registry_dir.mkdir(parents=True)
        _write_fixture_corpus(corpus_dir)
        projections = projection.build(corpus_dir, projection_dir)

        seams: list[str] = []
        envelope = intake(raw)
        _emit(inquiry_dir, envelope, "00-envelope.yaml", seams)
        dismantling = dismantling_organ(envelope)
        _emit(inquiry_dir, dismantling, "01-dismantling.yaml", seams)

        ministers = registry()
        for manifest in ministers:
            (registry_dir / f"man-{manifest['id']}.yaml").write_text(
                yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8"
            )

        reports = [
            minister_reason(manifest, dismantling, projections)
            for manifest in ministers
        ]
        for report in reports:
            _emit(
                inquiry_dir,
                report,
                f"rep-{report['minister']['actor']}.yaml",
                seams,
            )

        synthesis = secretary(reports)
        _emit(inquiry_dir, synthesis, "synthesis.yaml", seams)

        print("=== ORGAN ARTICULATION ===")
        if seams:
            for seam in seams:
                print("  SEAM:", seam)
        else:
            print("  organs exchanged well-formed, cross-referenced records.")

        confronted = reports[0]["propositions"][1]["confronted_with"]
        print("\n=== RETRIEVAL WIRED INTO UNIVERSAL DISPATCH ===")
        print(f"  every minister was confronted with: {confronted}")

        print("\n=== THE GATE ===")
        return gate.run(
            str(inquiry_dir),
            str(BASE / "schemas"),
            str(registry_dir),
        )
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(
        run_assembly(
            "A party asserts a necessity that its own words could equally serve as appetite."
        )
    )
