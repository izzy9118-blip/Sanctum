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
    assert strauss["pinned_commit"] == "32c96337cc29413a9f97cc843eaabf56a5ed38d6"
    assert strauss["participation"] == "universal"
    assert strauss["authorization_ref"] == "governance/repository-authorization.yaml"
    assert strauss["pin_status"] == "OWNER_CERTIFIED"


def test_xenophon_registry_entry_matches_federation_contract():
    registry, schema = registry_and_schema()
    xenophon = next(item for item in registry["ministers"] if item.get("minister_id") == "xenophon")
    Draft202012Validator(schema).validate(xenophon)
    assert xenophon["repository"] == "izzy9118-blip/Xenophon"
    assert xenophon["manifest_path"] == "manifest.yaml"
    assert xenophon["manifest_version"] == "1.70.0"
    assert xenophon["pinned_commit"] == "77ae6a2fedc133bbc6ef63b58ab1751ba8ffe1c5"
    assert xenophon["participation"] == "universal"
    assert xenophon["authorization_ref"] == "governance/repository-authorization.yaml"
    assert xenophon["authorization_id"] == "XENOPHON-AUTH-001"
    assert xenophon["pin_status"] == "OWNER_CERTIFIED"
    assert xenophon["membership_status"] == "established"
    assert xenophon["semantic_completion"] == "INCOMPLETE"
    assert xenophon["authorization_scope"]["greek_language_review"] == "DEFERRED_BY_OWNER"
    assert xenophon["authorization_scope"]["greek_dependent_claims"] == "PROHIBITED"
    assert xenophon["authorization_scope"]["unresolved_question_count"] == 19
    assert xenophon["authorization_scope"]["final_teaching_authorized"] is False


def test_registry_contains_two_established_sovereign_ministers():
    registry, _ = registry_and_schema()
    established = [item for item in registry["ministers"] if item.get("membership_status") == "established"]
    assert registry["version"] == "3.0.0"
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
