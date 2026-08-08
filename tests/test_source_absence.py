import unittest

from source_absence import SourceStateError, validate_source_states


def source(ref="SRC-1"):
    return {"source_ref": ref}


def base_response():
    return {
        "sources_searched": [source()],
        "sources_used": [source()],
        "records_returned": [{
            "information_need": "Need",
            "finding": "Finding",
            "evidence_state": "SUPPORTED",
            "source_refs": ["SRC-1"],
        }],
        "unfilled_requests": [],
    }


class SourceAbsenceTaxonomy(unittest.TestCase):
    def test_supported_record_passes(self):
        self.assertEqual(validate_source_states(base_response())["records_returned"][0]["evidence_state"], "SUPPORTED")

    def test_documented_absence_requires_scope_and_basis(self):
        item = base_response()
        item["records_returned"][0]["evidence_state"] = "DOCUMENTED_ABSENCE"
        with self.assertRaises(SourceStateError):
            validate_source_states(item)

    def test_documented_absence_with_positive_ground_passes(self):
        item = base_response()
        item["records_returned"][0].update({
            "evidence_state": "DOCUMENTED_ABSENCE",
            "absence_scope": "official register for July 2026",
            "absence_basis": "complete register contains no entry",
        })
        validate_source_states(item)

    def test_not_searched_may_not_fake_search_refs(self):
        item = base_response()
        item["records_returned"] = []
        item["sources_used"] = []
        item["unfilled_requests"] = [{
            "information_need": "Need",
            "reason": "Not searched",
            "evidence_state": "NOT_SEARCHED",
            "searched_source_refs": ["SRC-1"],
            "absence_claim": False,
        }]
        with self.assertRaises(SourceStateError):
            validate_source_states(item)

    def test_searched_not_found_requires_search_ref(self):
        item = base_response()
        item["records_returned"] = []
        item["sources_used"] = []
        item["unfilled_requests"] = [{
            "information_need": "Need",
            "reason": "No qualifying record found",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": [],
            "absence_claim": False,
        }]
        with self.assertRaises(SourceStateError):
            validate_source_states(item)

    def test_unresolved_state_may_not_assert_absence(self):
        item = base_response()
        item["records_returned"] = []
        item["sources_used"] = []
        item["unfilled_requests"] = [{
            "information_need": "Need",
            "reason": "No qualifying record found",
            "evidence_state": "SEARCHED_NOT_FOUND",
            "searched_source_refs": ["SRC-1"],
            "absence_claim": True,
        }]
        with self.assertRaises(SourceStateError):
            validate_source_states(item)

    def test_unfilled_may_not_use_documented_absence(self):
        item = base_response()
        item["records_returned"] = []
        item["sources_used"] = []
        item["unfilled_requests"] = [{
            "information_need": "Need",
            "reason": "Bad encoding",
            "evidence_state": "DOCUMENTED_ABSENCE",
            "searched_source_refs": ["SRC-1"],
            "absence_claim": False,
        }]
        with self.assertRaises(SourceStateError):
            validate_source_states(item)


if __name__ == "__main__":
    unittest.main()
