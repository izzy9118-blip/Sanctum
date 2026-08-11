import unittest

from minister_horus import HorusExchangeError, required_horus_call, validate_response

COMMIT = "a" * 40
HORUS_COMMIT = "b" * 40


def query():
    return {
        "record_type": "minister_horus_query",
        "query_id": "MHQ-INQ1-XEN-001",
        "inquiry_id": "INQ-1",
        "minister_id": "xenophon",
        "information_needed": ["Who currently exercises operational command?"],
        "source_requirements": [{
            "requirement": "Use promulgated appointment or dismissal instruments where available.",
            "rationale": "The officeholder must be established from the act itself rather than commentary.",
            "acceptable_tiers": ["T1", "T3"],
            "original_language_required": True,
        }],
        "specific_document_requests": [],
        "principal_scope": ["Ukraine"],
        "disallowed_substitutions": ["Do not substitute press characterization for the signed instrument."],
        "reason_for_request": "Command identity changes the material reading of the board.",
        "source_selection_rule": "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS",
        "source_absence_taxonomy": "HORUS-SOURCE-STATE-1.0",
        "provenance": {"produced_by": "xenophon", "repository_commit": COMMIT},
    }


def source():
    return {
        "source_ref": "SRC-1",
        "document_identity": "Decree 630/2026",
        "url": "https://example.invalid/630",
        "issuer": "President of Ukraine",
        "date": "2026-07-22",
        "language": "Ukrainian",
        "source_tier": "T1",
        "retrieval_date": "2026-08-07",
        "repository_path": "files/ukraine--zelensky.md",
        "sha256": None,
        "relevant_locator": "decree text",
    }


def acquisition(satisfied=True):
    return {
        "protocol": "HORUS-ACQUISITION-1.0",
        "plan_sha256": "c" * 64,
        "principal_profiles": [{
            "principal_id": "ukraine",
            "profile_path": "registry/principals/ukraine.json",
            "profile_sha256": "d" * 64,
        }],
        "date_normalizations": [],
        "search_attempts": [{
            "attempt_id": "ATT-1",
            "information_need": "Who currently exercises operational command?",
            "principal_id": "ukraine",
            "channel_id": "zakon-rada-gov-ua",
            "channel_class": "OFFICIAL_MIRROR",
            "search_method": "ALTERNATE_FIRST_PARTY_CHANNEL",
            "language": "uk",
            "canonical_date": None,
            "local_date": None,
            "query": "appointment instrument",
            "url": "https://example.invalid/630",
            "result": "FOUND",
            "source_ref": "SRC-1",
            "detail": None,
            "attempted_at": "2026-08-07T12:00:00Z",
        }],
        "requirements": [{
            "information_need": "Who currently exercises operational command?",
            "principal_id": "ukraine",
            "target_tier": "T1",
            "original_language_required": True,
            "required_steps": ["DIRECT_FIRST_PARTY_ARCHIVE", "DIRECT_FIRST_PARTY_SITE_SEARCH", "ALTERNATE_FIRST_PARTY_CHANNEL", "FIRST_PARTY_DOMAIN_RECOVERY"],
            "completed_steps": ["ALTERNATE_FIRST_PARTY_CHANNEL"],
            "minimum_protocol_attempted": False,
            "minimum_protocol_satisfied": satisfied,
        }],
        "runtime": {
            "engine": "HORUS_CANONICAL_ACQUISITION_ENGINE",
            "engine_path": "runtime/gather.py",
            "mode": "FIXTURE",
        },
    }


def response():
    s = source()
    return {
        "record_type": "horus_query_response",
        "query_id": "MHQ-INQ1-XEN-001",
        "requesting_minister": "xenophon",
        "request_as_received": query(),
        "status": "GATHERED",
        "source_absence_taxonomy": "HORUS-SOURCE-STATE-1.0",
        "acquisition": acquisition(),
        "sources_searched": [s],
        "sources_used": [s],
        "sources_rejected": [],
        "records_returned": [{
            "information_need": "Who currently exercises operational command?",
            "finding": "The named appointment instrument records the officeholder.",
            "evidence_state": "SUPPORTED",
            "source_refs": ["SRC-1"],
            "tier": "T1",
            "language": "Ukrainian",
            "language_state": "ORIGINAL",
        }],
        "unfilled_requests": [],
        "provenance": {
            "horus_repository_commit": HORUS_COMMIT,
            "generated_at": "2026-08-07T12:00:00Z",
            "query_log_path": "queries/INQ-1/xenophon/MHQ-INQ1-XEN-001.json",
        },
        "completeness": "PENDING_PROBE",
    }


class MandatoryHorusCall(unittest.TestCase):
    def test_valid_exchange_crosses_the_boundary(self):
        got = required_horus_call(query(), lambda _: response())
        self.assertEqual(got["status"], "GATHERED")

    def test_acquisition_receipt_is_mandatory(self):
        item = response(); del item["acquisition"]
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_noncanonical_acquisition_engine_is_rejected(self):
        item = response(); item["acquisition"]["runtime"]["engine_path"] = "some/other/gatherer.py"
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_response_must_preserve_request_exactly(self):
        item = response(); item["request_as_received"]["reason_for_request"] = "changed"
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_minister_cannot_take_source_selection_authority(self):
        item = query(); item["source_selection_rule"] = "MINISTER_SELECTS_SOURCES"
        with self.assertRaises(HorusExchangeError):
            required_horus_call(item, lambda _: response())

    def test_used_source_must_have_been_disclosed_as_searched(self):
        item = response(); item["sources_searched"] = []
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_returned_finding_cannot_cite_an_undisclosed_source(self):
        item = response(); item["records_returned"][0]["source_refs"] = ["SECRET-SOURCE"]
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_not_gathered_is_valid_only_with_typed_gap(self):
        item = response()
        item["status"] = "NOT_GATHERED"
        item["sources_used"] = []
        item["records_returned"] = []
        item["unfilled_requests"] = [{
            "information_need": "Who currently exercises operational command?",
            "reason": "The identified source exists but could not be acquired.",
            "evidence_state": "SOURCE_EXISTS_NOT_ACQUIRED",
            "searched_source_refs": ["SRC-1"],
            "searched_attempt_refs": ["ATT-1"],
            "absence_claim": False,
        }]
        self.assertEqual(validate_response(query(), item)["status"], "NOT_GATHERED")

    def test_search_failure_requires_satisfied_t1_acquisition_protocol(self):
        item = response()
        item["status"] = "NOT_GATHERED"
        item["sources_used"] = []
        item["records_returned"] = []
        item["acquisition"] = acquisition(satisfied=False)
        item["unfilled_requests"] = [{
            "information_need": "Who currently exercises operational command?",
            "reason": "Search returned no qualifying record.",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": ["SRC-1"],
            "searched_attempt_refs": ["ATT-1"],
            "absence_claim": False,
        }]
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_search_failure_cannot_be_documented_absence(self):
        item = response()
        item["status"] = "NOT_GATHERED"
        item["sources_used"] = []
        item["records_returned"] = []
        item["unfilled_requests"] = [{
            "information_need": "Who currently exercises operational command?",
            "reason": "Search returned no qualifying record.",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": ["SRC-1"],
            "searched_attempt_refs": ["ATT-1"],
            "absence_claim": True,
        }]
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_documented_absence_requires_positive_source_ground(self):
        item = response()
        item["records_returned"][0].update({
            "finding": "The official register documents no appointment in the stated period.",
            "evidence_state": "DOCUMENTED_ABSENCE",
            "absence_scope": "appointments in the official register, 2026-07-01 through 2026-07-31",
            "absence_basis": "The complete official register for the stated period contains no appointment entry.",
        })
        self.assertEqual(validate_response(query(), item)["records_returned"][0]["evidence_state"], "DOCUMENTED_ABSENCE")

    def test_horus_cannot_self_certify_completeness(self):
        item = response(); item["completeness"] = "COMPLETE"
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)


if __name__ == "__main__":
    unittest.main()
