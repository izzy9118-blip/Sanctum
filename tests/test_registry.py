from pathlib import Path
import json
import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_strauss_registry_entry_matches_federation_contract():
    registry = load_yaml("registry/ministers.yaml")
    strauss = next(item for item in registry["ministers"] if item.get("minister_id") == "leo-strauss")
    schema = json.loads((ROOT / "minister-manifest.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(strauss)
    assert strauss["repository"] == "izzy9118-blip/Strauss"
    assert strauss["manifest_path"] == "manifest.yaml"
    assert strauss["manifest_version"] == "1.20.0"
    assert strauss["pinned_commit"] == "32c96337cc29413a9f97cc843eaabf56a5ed38d6"
    assert strauss["participation"] == "universal"
    assert strauss["authorization_ref"] == "governance/repository-authorization.yaml"
    assert strauss["pin_status"] == "OWNER_CERTIFIED"
    assert strauss["pin_certification"]["authority"] == "REPOSITORY_OWNER_DIRECTIVE"


def test_registry_policy_forbids_upstream_selection():
    registry = load_yaml("registry/ministers.yaml")
    policy = registry["participation_policy"]
    assert policy["mode"] == "universal"
    assert policy["no_upstream_selection"] is True
    assert policy["report_required_from_every_established_minister"] is True
