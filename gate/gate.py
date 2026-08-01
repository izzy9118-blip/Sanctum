#!/usr/bin/env python3
"""Sanctum Validation Gate.

Converts candidate records into authoritative memory, or refuses them. Emits
validated / flagged / rejected and never stamps validated on substance it cannot
mechanically verify.

Completed inquiries are judged against the immutable dispatch scope recorded in
their dispatch receipt. New candidate bundles without a receipt are judged against
the current registry. This prevents later minister admissions from rewriting or
invalidating earlier universal dispatches.

Usage: python3 gate.py <inquiry_dir> [schema_dir] [registry_dir]
Exit: 0 if no rejections; 1 if any rejection.
"""
import glob
import os
import sys

import yaml

MAX_RECORD_BYTES = 32 * 1024
PROP_KINDS = {
    "documented_finding",
    "supported_inference",
    "working_hypothesis",
    "comparative_question",
    "unresolved_uncertainty",
}


class Finding:
    def __init__(self, record, check, status, reason):
        self.record = record
        self.check = check
        self.status = status
        self.reason = reason

    def __repr__(self):
        return f"[{self.status.upper():9}] {self.check:22} {self.record}: {self.reason}"


def rej(record, check, why): return Finding(record, check, "reject", why)
def flag(record, check, why): return Finding(record, check, "flag", why)
def ok(record, check, why=""): return Finding(record, check, "pass", why)


def load_schemas(paths):
    defs, types = {}, {}
    for path in paths:
        with open(path, encoding="utf-8") as stream:
            doc = yaml.safe_load(stream)
        for key, value in doc.items():
            if key == "$defs": defs.update(value)
            else: types[key] = value
    return types, defs


def resolve(schema, defs):
    if isinstance(schema, dict) and "$ref" in schema:
        return defs[schema["$ref"].split("/")[-1]]
    return schema


def minivalidate(inst, schema, defs, path=""):
    errs = []
    schema = resolve(schema, defs)
    if not isinstance(schema, dict): return errs
    if "const" in schema and inst != schema["const"]:
        errs.append(f"{path}: must be {schema['const']!r}, got {inst!r}")
    if "enum" in schema and inst not in schema["enum"]:
        errs.append(f"{path}: {inst!r} not in {schema['enum']}")
    if schema.get("type") == "object" and isinstance(inst, dict):
        for req in schema.get("required", []):
            if req not in inst or inst[req] is None or inst[req] == "":
                errs.append(f"{path}: missing required '{req}'")
        for key, sub in schema.get("properties", {}).items():
            if key in inst: errs += minivalidate(inst[key], sub, defs, f"{path}.{key}")
    if schema.get("type") == "array" and isinstance(inst, list) and "items" in schema:
        for index, item in enumerate(inst):
            errs += minivalidate(item, schema["items"], defs, f"{path}[{index}]")
    return errs


def load_bundle(directory):
    records = []
    for path in sorted(glob.glob(os.path.join(directory, "*.yaml"))):
        if os.path.basename(path).startswith("_"): continue
        with open(path, encoding="utf-8") as stream: doc = yaml.safe_load(stream)
        doc["__path__"] = os.path.basename(path)
        doc["__bytes__"] = os.path.getsize(path)
        records.append(doc)
    return records


def rtype(record): return record.get("record_type", "?")
def rid(record): return record.get("__path__", record.get("id", "?"))
def by(records, *types): return [record for record in records if rtype(record) in types]


def load_registry(registry_dir):
    """Load established Assembly membership, never inquiry relevance."""
    if not registry_dir or not os.path.isdir(registry_dir): return []
    result = []
    for path in sorted(glob.glob(os.path.join(registry_dir, "*.yaml"))):
        with open(path, encoding="utf-8") as stream: doc = yaml.safe_load(stream)
        if not isinstance(doc, dict): continue
        if doc.get("record_type") == "minister_manifest":
            result.append(doc); continue
        for item in doc.get("ministers", []):
            if not isinstance(item, dict): continue
            if item.get("membership_status", "established") != "established": continue
            result.append(item)
    return result


def check_A1_schema(records, schemas, defs, *_):
    output = []
    for record in records:
        schema = schemas.get(rtype(record))
        if schema is None:
            output.append(flag(rid(record), "A1-schema", f"unknown record_type '{rtype(record)}' — cannot verify")); continue
        errors = minivalidate(record, schema, defs)
        output += [rej(rid(record), "A1-schema", error) for error in errors] or [ok(rid(record), "A1-schema")]
    return output


def check_A2_size(records, *_):
    return [rej(rid(r), "A2-size", f"{r['__bytes__']}B exceeds {MAX_RECORD_BYTES}B") if r["__bytes__"] > MAX_RECORD_BYTES else ok(rid(r), "A2-size") for r in records]


def check_A3_provenance(records, *_):
    output = []
    for record in records:
        if not record.get("provenance", {}).get("produced_by", {}).get("commit"):
            output.append(rej(rid(record), "A3-provenance", "produced_by.commit missing — which actor, which version?"))
        else: output.append(ok(rid(record), "A3-provenance"))
    return output


def check_B1_dismantling_elements(records, *_):
    required = ["raw_submission", "extracted_claims_and_presuppositions", "framing_sources", "documented_acts_events_material_conditions", "supporting_evidence", "disconfirming_evidence", "unresolved_ambiguities", "transformation_rules_applied", "excluded_material"]
    output = []
    for record in by(records, "dismantling_record"):
        missing = [key for key in required if key not in record or record[key] in (None, "", [], {})]
        output.append(rej(rid(record), "B1-elements", "missing or empty: " + ", ".join(missing)) if missing else ok(rid(record), "B1-elements"))
    return output


def check_B2_exclusions(records, *_):
    output = []
    for record in by(records, "dismantling_record"):
        for exclusion in record.get("excluded_material", []):
            if not exclusion.get("reason"): output.append(rej(rid(record), "B2-exclusion", f"excluded '{exclusion.get('item')}' has no reason"))
        output.append(ok(rid(record), "B2-exclusion"))
    return output


def check_B3_classification(records, *_):
    output = []
    for record in by(records, "dismantling_record"):
        for classification in record.get("classifications", []):
            if not (classification.get("schema") and classification.get("rationale")): output.append(rej(rid(record), "B3-classify", "classification lacks schema/rationale"))
        for juxtaposition in record.get("juxtapositions", []):
            if not juxtaposition.get("rationale"): output.append(rej(rid(record), "B3-classify", "juxtaposition lacks rationale — arrangement is an argument"))
        output.append(ok(rid(record), "B3-classify"))
    return output


def check_B4_rawframing(records, *_):
    output = []
    envelopes = {record.get("id"): record for record in by(records, "inquiry_envelope")}
    for record in by(records, "dismantling_record"):
        raw = record.get("raw_submission")
        if not raw:
            output.append(rej(rid(record), "B4-rawframe", "raw_submission absent — forbidden to remove")); continue
        envelope = envelopes.get(record.get("inquiry_ref", {}).get("ref"))
        output.append(rej(rid(record), "B4-rawframe", "raw_submission altered from envelope raw_situation") if envelope and envelope.get("raw_situation") != raw else ok(rid(record), "B4-rawframe"))
    return output


def check_B5_forbidden_verbs(records, *_):
    output = []
    for record in by(records, "dismantling_record"):
        risk = len(record.get("classifications", [])) + len(record.get("juxtapositions", []))
        output.append(flag(rid(record), "B5-verbs", f"{risk} classification/juxtaposition(s) require outside-ground inspection") if risk else ok(rid(record), "B5-verbs"))
    return output


def check_C1_participation(records, schemas=None, defs=None, registry=None):
    """Verify reports against the dispatch scope that actually governed the inquiry.

    A committed dispatch receipt freezes universal membership for that inquiry. Later
    registry expansion must not retroactively add ministers to completed dispatches.
    Candidate bundles without a receipt are checked against the current registry.
    """
    receipts = by(records, "dispatch_receipt")
    if receipts:
        if len(receipts) != 1:
            return [rej("(bundle)", "C1-participation", "exactly one dispatch receipt is required")]
        receipt = receipts[0]
        dispatched = receipt.get("dispatched_ministers")
        if not isinstance(dispatched, list) or not dispatched:
            return [rej(rid(receipt), "C1-participation", "dispatch receipt has no dispatched ministers")]
        expected = {item.get("minister_id") for item in dispatched if isinstance(item, dict)}
        if None in expected or not expected:
            return [rej(rid(receipt), "C1-participation", "dispatch receipt contains an invalid minister identity")]
        source = f"recorded dispatch registry {receipt.get('registry_state', {}).get('version', '?')}"
    else:
        expected = {manifest.get("id") for manifest in (registry or [])}
        source = "current registry"
        if not expected:
            return [flag("(registry)", "C1-participation", "no registry provided — cannot verify universal participation")]

    reported = {report.get("minister", {}).get("actor") for report in by(records, "ministerial_report")}
    output = []
    for minister in expected - reported:
        output.append(rej("(bundle)", "C1-participation", f"minister '{minister}' in {source} but no report; outside_my_ground also counts"))
    for minister in reported - expected:
        output.append(rej("(bundle)", "C1-participation", f"report from minister '{minister}' not present in {source}"))
    return output or [ok("(bundle)", "C1-participation", f"reports match {source}")]


def check_C2_kinds(records, *_):
    output = []
    for record in by(records, "ministerial_report", "dissent"):
        for index, proposition in enumerate(record.get("propositions") or []):
            kind = proposition.get("kind")
            if kind not in PROP_KINDS: output.append(rej(rid(record), "C2-kinds", f"proposition[{index}] kind {kind!r} invalid"))
            elif kind == "documented_finding" and not proposition.get("grounds"): output.append(rej(rid(record), "C2-kinds", f"proposition[{index}] documented_finding lacks witnesses"))
        output.append(ok(rid(record), "C2-kinds"))
    return output


def check_D1_dissent(records, *_):
    output = []
    identifiers = {record.get("id") for record in records}
    for synthesis in by(records, "synthesis"):
        for ref in synthesis.get("preserved_dissent_refs", []):
            if ref.get("ref") not in identifiers: output.append(rej(rid(synthesis), "D1-dissent", f"referenced dissent '{ref.get('ref')}' is absent"))
    output.append(ok("(bundle)", "D1-dissent")); return output


def check_D2_synthesis_grounds(records, *_):
    output = []
    for synthesis in by(records, "synthesis"):
        if synthesis.get("grounds_converge") is not True: output.append(rej(rid(synthesis), "D2-synth", "synthesis with grounds_converge != true"))
        if not synthesis.get("shared_ground"): output.append(rej(rid(synthesis), "D2-synth", "synthesis lacks shared_ground"))
        for assessment in synthesis.get("convergence_assessment", []):
            if not assessment.get("ground"): output.append(flag(rid(synthesis), "D2-synth", f"minister '{assessment.get('minister')}' lacks a stated ground"))
        output.append(ok(rid(synthesis), "D2-synth"))
    return output


def check_D3_divergence_recorded(records, *_):
    output = []
    inquiries = {report.get("inquiry_ref", {}).get("ref") for report in by(records, "ministerial_report")}
    for inquiry in inquiries:
        reports = [report for report in by(records, "ministerial_report") if report.get("inquiry_ref", {}).get("ref") == inquiry and report.get("mode") == "reasoned"]
        if len(reports) < 2: continue
        has_synthesis = any(s.get("inquiry_ref", {}).get("ref") == inquiry for s in by(records, "synthesis"))
        has_non_synthesis = any(r.get("inquiry_ref", {}).get("ref") == inquiry for r in by(records, "non_synthesis_result"))
        if not (has_synthesis or has_non_synthesis): output.append(rej("(bundle)", "D3-divergence", f"inquiry '{inquiry}' has no synthesis or non_synthesis_result"))
    return output or [ok("(bundle)", "D3-divergence")]


def check_D4_president(records, *_):
    output = []
    for opinion in by(records, "presidential_opinion"):
        if opinion.get("marked_as_own") is not True: output.append(rej(rid(opinion), "D4-president", "Presidential Opinion is not marked_as_own"))
        inquiry = opinion.get("inquiry_ref", {}).get("ref")
        if not any(s.get("inquiry_ref", {}).get("ref") == inquiry for s in by(records, "synthesis")): output.append(rej(rid(opinion), "D4-president", "Presidential Opinion exists without synthesis"))
        output.append(ok(rid(opinion), "D4-president"))
    return output


def check_E1_legible(records, *_):
    return [rej(rid(record), "E1-legible", "record is not text-serialized YAML") if not record.get("__path__", "").endswith((".yaml", ".yml")) else ok(rid(record), "E1-legible") for record in records]


CHECKS = [check_A1_schema, check_A2_size, check_A3_provenance, check_B1_dismantling_elements, check_B2_exclusions, check_B3_classification, check_B4_rawframing, check_B5_forbidden_verbs, check_C1_participation, check_C2_kinds, check_D1_dissent, check_D2_synthesis_grounds, check_D3_divergence_recorded, check_D4_president, check_E1_legible]


def run(inquiry_dir, schema_dir, registry_dir=None):
    schema_paths = sorted(glob.glob(os.path.join(schema_dir, "*.yaml")) + glob.glob(os.path.join(schema_dir, "*.yml")))
    schemas, defs = load_schemas(schema_paths)
    registry = load_registry(registry_dir)
    records = load_bundle(inquiry_dir)
    findings = []
    for check in CHECKS: findings += check(records, schemas, defs, registry)
    rejections = [finding for finding in findings if finding.status == "reject"]
    flags = [finding for finding in findings if finding.status == "flag"]
    outcome = "rejected" if rejections else ("flagged" if flags else "validated")
    result = {
        "record_type": "gate_validation_record",
        "inquiry_dir": str(inquiry_dir),
        "outcome": outcome,
        "rejections": [f"{f.check} | {f.record} | {f.reason}" for f in rejections],
        "flags": [f"{f.check} | {f.record} | {f.reason}" for f in flags],
    }
    with open(os.path.join(inquiry_dir, "_gate_result.yaml"), "w", encoding="utf-8") as stream:
        stream.write(yaml.safe_dump(result, sort_keys=False))
    print(f"\n=== GATE: {outcome.upper()} ===  ({inquiry_dir})")
    for finding in rejections + flags: print(" ", finding)
    if outcome == "validated": print("  all checks passed; candidate may be merged to canonical.")
    print()
    return 1 if rejections else 0


if __name__ == "__main__":
    inquiry = sys.argv[1] if len(sys.argv) > 1 else "."
    schemas = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(inquiry.rstrip("/")), "schemas")
    registry = sys.argv[3] if len(sys.argv) > 3 else None
    sys.exit(run(inquiry, schemas, registry))
