import unittest

from adversarial_horus import (
    build_adversarial_query,
    required_adversarial_horus_call,
    validate_adversarial_query,
    validate_adversarial_response,
    validate_provisional_judgment,
)
from minister_horus import HorusExchangeError

COMMIT = "a" * 40
HORUS_COMMIT = "b" * 40


def investigative_query():
    return {
        "principal_scope": ["Ukraine"],
        "time_scope": {"start": "2026-07-22", "end": "2026-08-08"},
    }


def provisional():
    return {
        "record_type": "minister_provisional_judgment",
        "inquiry_id": "INQ-1",
        "minister_id": "xenophon",
        "propositions": [{
            "proposition_id": "P-COMMAND-1",
            "claim": "The command reshuffle materially changes the operational reading.",
            "kind": "supported_inference",
            "disconfirmation_need": "Evidence that the named appointments did not alter effective operational command.",
            "why_it_matters": "If effective command was unchanged, the inference from formal appointment to operational change weakens.",
            "acceptable_tiers": ["T2", "T3", "T4"],
            "original_language_required": False,
        }],
        "provenance": {"produced_by": "xenophon", "repository_commit": COMMIT},
    }


def acquisition(query, result="FOUND"):
    need = query["information_needed"][0]
    return {
        "protocol": "HORUS-ACQUISITION-1.0",
        "plan_sha256": "c" * 64,
        "principal_profiles": [],
        "date_normalizations": [],
        "search_attempts": [{
            "attempt_id": "ATT-ADV-1",
            "information_need": need,
            "principal_id": "ukraine",
            "channel_id": "president-gov-ua",
            "channel_class": "PRIMARY",
            "search_method": "DIRECT_FIRST_PARTY_SITE_SEARCH",
            "language": "uk",
            "canonical_date": "2026-08-08",
            "local_date": "2026-08-08",
            "query": "operational command",
            "url": "https://example.invalid/command",
            "result": result,
            "source_ref": "SRC-ADV-1" if result == "FOUND" else None,
            "detail": None,
            "attempted_at": "2026-08-08T12:00:00Z",
        }],
        "requirements": [],
        "runtime": {
            "engine": "HORUS_CANONICAL_ACQUISITION_ENGINE",
            "engine_path": "runtime/gather.py",
            "mode": "FIXTURE",
        },
    }


def adversarial_response(query):
    source = {
        "source_ref": "SRC-ADV-1",
        "document_identity": "Operational command record",
        "url": "https://example.invalid/command",
        "issuer": "General Staff",
        "date": "2026-07-23",
        "language": "Ukrainian",
        "source_tier": "T4",
        "retrieval_date": "2026-08-08",
        "repository_path": "files/ukraine.md",
        "sha256": None,
        "relevant_locator": "command record",
    }
    return {
        "record_type": "horus_query_response",
        "query_id": query["query_id"],
        "requesting_minister": "xenophon",
        "request_as_received": query,
        "status": "GATHERED",
        "source_absence_taxonomy": "HORUS-SOURCE-STATE-1.0",
        "acquisition": acquisition(query),
        "sources_searched": [source],
        "sources_used": [source],
        "sources_rejected": [],
        "records_returned": [{
            "information_need": query["information_needed"][0],
            "finding": "The record bears directly on whether effective command changed.",
            "evidence_state": "CONTRADICTORY_RECORD",
            "source_refs": ["SRC-ADV-1"],
            "tier": "T4",
            "language": "Ukrainian",
            "language_state": "ORIGINAL",
        }],
        "unfilled_requests": [],
        "provenance": {
            "horus_repository_commit": HORUS_COMMIT,
            "generated_at": "2026-08-08T12:00:00Z",
            "query_log_path": "queries/INQ-1/xenophon/adversarial.json",
        },
        "completeness": "PENDING_PROBE",
    }


class AdversarialHorusCall(unittest.TestCase):
    def test_provisional_requires_disconfirmation_need(self):
        item = provisional(); del item["propositions"][0]["disconfirmation_need"]
        with self.assertRaises(HorusExchangeError):
            validate_provisional_judgment(item)

    def test_adversarial_query_is_deterministic(self):
        one = build_adversarial_query(provisional(), investigative_query()); two = build_adversarial_query(provisional(), investigative_query())
        self.assertEqual(one, two)
        self.assertTrue(one["query_id"].startswith("MHAQ-"))
        self.assertEqual(one["source_absence_taxonomy"], "HORUS-SOURCE-STATE-1.0")

    def test_adversarial_query_inherits_principal_and_time_scope(self):
        item = build_adversarial_query(provisional(), investigative_query())
        self.assertEqual(item["principal_scope"], ["Ukraine"])
        self.assertEqual(item["time_scope"], {"start": "2026-07-22", "end": "2026-08-08"})

    def test_original_language_adversarial_request_requires_inherited_principal_scope(self):
        item = provisional()
        item["propositions"][0]["acceptable_tiers"] = ["T1"]
        item["propositions"][0]["original_language_required"] = True
        with self.assertRaises(HorusExchangeError):
            build_adversarial_query(item)
        self.assertEqual(build_adversarial_query(item, investigative_query())["principal_scope"], ["Ukraine"])

    def test_every_proposition_gets_exactly_one_requirement(self):
        item = build_adversarial_query(provisional(), investigative_query()); item["source_requirements"] = []
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_query(item)

    def test_hard_call_returns_query_and_valid_response(self):
        query, response = required_adversarial_horus_call(provisional(), lambda q: adversarial_response(q), investigative_query())
        self.assertTrue(query["query_id"].startswith("MHAQ-"))
        self.assertEqual(response["status"], "GATHERED")

    def test_adversarial_response_requires_canonical_acquisition(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["acquisition"]["runtime"]["engine"] = "OTHER"
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_response(query, response)

    def test_adversarial_response_must_preserve_request(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["request_as_received"] = dict(query); response["request_as_received"]["principal_scope"] = []
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_response(query, response)

    def test_adversarial_source_use_must_be_disclosed_as_searched(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["sources_searched"] = []
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_response(query, response)

    def test_horus_cannot_self_certify_adversarial_completeness(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["completeness"] = "COMPLETE"
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_response(query, response)

    def test_not_gathered_keeps_typed_disconfirmation_gap_visible(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["status"] = "NOT_GATHERED"
        response["acquisition"] = acquisition(query, result="NO_MATCH")
        response["sources_searched"] = []
        response["sources_used"] = []
        response["records_returned"] = []
        response["unfilled_requests"] = [{
            "information_need": query["information_needed"][0],
            "reason": "No qualifying contradictory record was found in the executed search.",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": [],
            "searched_attempt_refs": ["ATT-ADV-1"],
            "absence_claim": False,
        }]
        self.assertEqual(validate_adversarial_response(query, response)["status"], "NOT_GATHERED")

    def test_not_gathered_cannot_confirm_provisional_judgment(self):
        query = build_adversarial_query(provisional(), investigative_query()); response = adversarial_response(query)
        response["status"] = "NOT_GATHERED"
        response["acquisition"] = acquisition(query, result="NO_MATCH")
        response["sources_searched"] = []
        response["sources_used"] = []
        response["records_returned"] = []
        response["unfilled_requests"] = [{
            "information_need": query["information_needed"][0],
            "reason": "No qualifying contradictory record was found.",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": [],
            "searched_attempt_refs": ["ATT-ADV-1"],
            "absence_claim": True,
        }]
        with self.assertRaises(HorusExchangeError):
            validate_adversarial_response(query, response)


if __name__ == "__main__":
    unittest.main()
