from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def registry_and_schema():
    registry = load_yaml("registry/ministers.yaml")
    schema = json.loads((ROOT / "minister-manifest.schema.json").read_text(encoding="utf-8"))
    return registry, schema


def test_strauss_registry_entry_matches_federation_contract():
    registry, schema = registry_and_schema()
    strauss = next(item for item in registry["ministers"] if item.get("minister_id") == "leo-strauss")
    Draft202012Validator(schema).validate(strauss)
    assert strauss["repository"] == "izzy9118-blip/Strauss"
    assert strauss["manifest_version"] == "1.20.0"
    assert strauss["pinned_commit"] == "fb417d1d4ab7b5d349e801544c0c703d8998a93f"
    assert strauss["participation"] == "universal"
    assert strauss["authorization_ref"] == "governance/repository-authorization.yaml"
    assert strauss["pin_status"] == "OWNER_CERTIFIED"
    assert strauss["pin_certification"]["decision_ref"] == "docs/decisions/0006-repin-current-minister-heads.md"


def test_xenophon_registry_entry_matches_federation_contract():
    registry, schema = registry_and_schema()
    xenophon = next(item for item in registry["ministers"] if item.get("minister_id") == "xenophon")
    Draft202012Validator(schema).validate(xenophon)
    assert xenophon["repository"] == "izzy9118-blip/Xenophon"
    assert xenophon["manifest_path"] == "manifest.yaml"
    assert xenophon["manifest_version"] == "1.71.0"
    assert xenophon["pinned_commit"] == "b665e323d0780431764b565616e629b2e2aec00f"
    assert xenophon["participation"] == "universal"
    assert xenophon["authorization_ref"] == "governance/repository-authorization-r2.yaml"
    assert xenophon["authorization_id"] == "XENOPHON-AUTH-002"
    assert xenophon["pin_status"] == "OWNER_CERTIFIED"
    assert xenophon["pin_certification"]["decision_ref"] == "docs/decisions/0007-register-xenophon-r2-multi-work-minister.md"
    assert xenophon["membership_status"] == "established"
    assert xenophon["semantic_completion"] == "INCOMPLETE"
    scope = xenophon["authorization_scope"]
    assert scope["current_textual_jurisdiction"] == "CONTROLLED_MULTI_WORK_ENGLISH_WITNESS_PRIMARY_SECONDARY_SYNTHESIS"
    assert scope["source_lines"] == ["anabasis", "hieron_on_tyranny"]
    assert scope["authorized_source_witness_pairs"] == 8
    assert scope["registers"] == 6
    assert scope["guards"] == 4
    assert scope["evidence_layers"] == 8
    assert scope["greek_language_review"] == "DEFERRED_BY_OWNER"
    assert scope["greek_dependent_claims"] == "PROHIBITED"
    assert scope["unresolved_question_count"] == 37
    assert scope["final_teaching_authorized"] is False
    assert scope["assembly_dispatch_status"] == "PENDING_END_TO_END_PROVING_INQUIRY"
    summary = xenophon["current_manifest_summary"]
    assert summary["manifest_blob_sha"] == "8f9e0bf4143dc40436f8df4ad683cc7b0b367f4b"
    inventory = summary["operational_inventory"]
    assert inventory["source_lines"] == 2
    assert inventory["source_witness_pairs"] == 8
    assert inventory["hieron_source_roles"] == 6
    assert inventory["registers"] == 6
    assert inventory["guards"] == 4
    assert inventory["evidence_layers"] == 8
    assert inventory["anabasis_unresolved_questions"] == 19
    assert inventory["hieron_unresolved_questions"] == 18
    assert inventory["combined_unresolved_questions"] == 37


def test_registry_contains_two_established_sovereign_ministers():
    registry, _ = registry_and_schema()
    established = [item for item in registry["ministers"] if item.get("membership_status") == "established"]
    assert registry["version"] == "3.2.0"
    assert registry["revision"]["predecessor_version"] == "3.1.0"
    assert registry["revision"]["predecessor_commit"] == "23078c3abc1b72ecec0a280ddea70631a37d3e7c"
    assert [item["minister_id"] for item in established] == ["leo-strauss", "xenophon"]
    assert len({item["repository"] for item in established}) == 2


def test_registry_policy_forbids_upstream_selection():
    registry, _ = registry_and_schema()
    policy = registry["participation_policy"]
    assert policy["mode"] == "universal"
    assert policy["no_upstream_selection"] is True
    assert policy["same_dismantled_intake_for_all"] is True
    assert policy["report_required_from_every_established_minister"] is True
    assert policy["outside_my_ground_is_complete_response"] is True
