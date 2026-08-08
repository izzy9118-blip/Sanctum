import copy
import unittest

from evidence_genealogy import GenealogyError, validate_genealogy_package


MINISTER_COMMIT = "a" * 40
EXCHANGE_SHA = "b" * 64
SOURCE_SHA = "c" * 64


def exchange():
    source = {
        "source_ref": "SRC-1",
        "document_identity": "Decree 630/2026",
        "url": "https://example.invalid/630",
        "issuer": "President of Ukraine",
        "date": "2026-07-22",
        "language": "Ukrainian",
        "source_tier": "T1",
        "retrieval_date": "2026-08-08",
        "repository_path": "files/ukraine--zelensky.md",
        "sha256": SOURCE_SHA,
        "relevant_locator": "decree text",
    }
    return {
        "exchange_kind": "investigative",
        "query_id": "MHQ-INQ-XEN-001",
        "exchange_sha256": EXCHANGE_SHA,
        "request": {"query_id": "MHQ-INQ-XEN-001"},
        "response": {
            "query_id": "MHQ-INQ-XEN-001",
            "sources_searched": [source],
            "sources_used": [source],
            "sources_rejected": [],
            "records_returned": [
                {
                    "information_need": "Who exercises operational command?",
                    "finding": "The appointment instrument names the officeholder.",
                    "source_refs": ["SRC-1"],
                }
            ],
            "unfilled_requests": [],
        },
    }


def horus_ground():
    return {
        "origin": "horus_exchange",
        "query_id": "MHQ-INQ-XEN-001",
        "exchange_sha256": EXCHANGE_SHA,
        "source_ref": "SRC-1",
        "document_identity": "Decree 630/2026",
        "locator": "decree text",
        "source_sha256": SOURCE_SHA,
    }


def package():
    return {
        "record_type": "final_judgment_package",
        "inquiry_id": "INQ-1",
        "minister_id": "xenophon",
        "repository": {"full_name": "Xenophon", "git_commit": MINISTER_COMMIT},
        "summary": "A test judgment.",
        "propositions": [
            {
                "proposition_id": "PROP-001",
                "kind": "documented_finding",
                "claim": "The cited instrument names the officeholder.",
                "provisional_disposition": "retained",
                "genealogy": [horus_ground()],
            }
        ],
        "uncertainties": [],
    }


class EvidenceGenealogyTests(unittest.TestCase):
    def test_valid_horus_ground_resolves(self):
        got = validate_genealogy_package(package(), [exchange()])
        self.assertEqual(got["status"], "GENEALOGY_STRUCTURALLY_VALIDATED_NOT_TRUTH_CERTIFIED")
        self.assertEqual(got["proposition_count"], 1)

    def test_substantive_proposition_cannot_have_empty_genealogy(self):
        item = package()
        item["propositions"][0]["genealogy"] = []
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_searched_but_not_used_source_cannot_be_ground(self):
        ex = exchange()
        ex["response"]["sources_used"] = []
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(package(), [ex])

    def test_used_source_without_returned_record_cannot_be_ground(self):
        ex = exchange()
        ex["response"]["records_returned"] = []
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(package(), [ex])

    def test_wrong_exchange_hash_is_rejected(self):
        item = package()
        item["propositions"][0]["genealogy"][0]["exchange_sha256"] = "d" * 64
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_wrong_document_identity_is_rejected(self):
        item = package()
        item["propositions"][0]["genealogy"][0]["document_identity"] = "Press summary"
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_wrong_locator_is_rejected(self):
        item = package()
        item["propositions"][0]["genealogy"][0]["locator"] = "headline"
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_recorded_source_hash_must_match(self):
        item = package()
        item["propositions"][0]["genealogy"][0]["source_sha256"] = "e" * 64
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_minister_repository_ground_uses_pinned_commit(self):
        item = package()
        item["propositions"][0]["genealogy"] = [{
            "origin": "minister_repository",
            "witness_id": "XEN-WIT-PRI-001",
            "source_id": "XEN-SRC-PRI-001",
            "repository_commit": MINISTER_COMMIT,
            "path": "corpus/witnesses/xenophon-anabasis-dakyns.yaml",
            "locator": "Book I, opening sequence",
        }]
        self.assertEqual(validate_genealogy_package(item, [exchange()])["proposition_count"], 1)

    def test_minister_repository_ground_cannot_change_commit(self):
        item = package()
        item["propositions"][0]["genealogy"] = [{
            "origin": "minister_repository",
            "witness_id": "XEN-WIT-PRI-001",
            "source_id": "XEN-SRC-PRI-001",
            "repository_commit": "f" * 40,
            "path": "corpus/witnesses/xenophon-anabasis-dakyns.yaml",
            "locator": "Book I, opening sequence",
        }]
        with self.assertRaises(GenealogyError):
            validate_genealogy_package(item, [exchange()])

    def test_unresolved_uncertainty_may_have_no_positive_ground(self):
        item = package()
        item["propositions"] = [{
            "proposition_id": "PROP-UNC-001",
            "kind": "unresolved_uncertainty",
            "claim": "The available record does not resolve the command relationship.",
            "provisional_disposition": "left_unresolved",
            "genealogy": [],
        }]
        self.assertEqual(validate_genealogy_package(item, [exchange()])["proposition_count"], 1)


if __name__ == "__main__":
    unittest.main()
