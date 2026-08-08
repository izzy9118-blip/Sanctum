import copy
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
        "source_requirements": [
            {
                "requirement": "Use promulgated appointment or dismissal instruments where available.",
                "rationale": "The officeholder must be established from the act itself rather than commentary.",
                "acceptable_tiers": ["T1", "T3"],
                "original_language_required": True,
            }
        ],
        "specific_document_requests": [],
        "principal_scope": ["Ukraine"],
        "disallowed_substitutions": ["Do not substitute press characterization for the signed instrument."],
        "reason_for_request": "Command identity changes the material reading of the board.",
        "source_selection_rule": "HORUS_RETAINS_SOURCE_SELECTION_INDEPENDENCE_EXCEPT_EXPLICIT_DOCUMENT_REQUESTS",
        "provenance": {"produced_by": "xenophon", "repository_commit": COMMIT},
    }


def response():
    source = {
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
    return {
        "record_type": "horus_query_response",
        "query_id": "MHQ-INQ1-XEN-001",
        "requesting_minister": "xenophon",
        "request_as_received": query(),
        "status": "GATHERED",
        "sources_searched": [source],
        "sources_used": [source],
        "sources_rejected": [],
        "records_returned": [
            {
                "information_need": "Who currently exercises operational command?",
                "finding": "The named appointment instrument records the officeholder.",
                "source_refs": ["SRC-1"],
                "tier": "T1",
                "language": "Ukrainian",
                "language_state": "ORIGINAL",
            }
        ],
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

    def test_minister_cannot_take_source_selection_authority(self):
        item = query()
        item["source_selection_rule"] = "MINISTER_SELECTS_SOURCES"
        with self.assertRaises(HorusExchangeError):
            required_horus_call(item, lambda _: response())

    def test_used_source_must_have_been_disclosed_as_searched(self):
        item = response()
        item["sources_searched"] = []
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_returned_finding_cannot_cite_an_undisclosed_source(self):
        item = response()
        item["records_returned"][0]["source_refs"] = ["SECRET-SOURCE"]
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)

    def test_not_gathered_is_valid_only_when_the_gap_is_explicit(self):
        item = response()
        item["status"] = "NOT_GATHERED"
        item["sources_used"] = []
        item["records_returned"] = []
        item["unfilled_requests"] = [
            {"information_need": "Who currently exercises operational command?", "reason": "No qualifying source acquired."}
        ]
        self.assertEqual(validate_response(query(), item)["status"], "NOT_GATHERED")

    def test_horus_cannot_self_certify_completeness(self):
        item = response()
        item["completeness"] = "COMPLETE"
        with self.assertRaises(HorusExchangeError):
            validate_response(query(), item)


if __name__ == "__main__":
    unittest.main()
