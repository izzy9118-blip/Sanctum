import pytest

import federated_proving


PROFILES = [
    {
        "principal_id": "united-states",
        "original_languages": ["en"],
        "channels": [{
            "channel_id": "whitehouse-gov", "channel_class": "PRIMARY",
            "base_url": "https://www.whitehouse.gov/",
            "supported_methods": ["DIRECT_FIRST_PARTY_ARCHIVE"],
        }],
    },
    {
        "principal_id": "iran",
        "original_languages": ["fa"],
        "channels": [{
            "channel_id": "president-ir", "channel_class": "PRIMARY",
            "base_url": "https://president.ir/",
            "supported_methods": ["DIRECT_FIRST_PARTY_ARCHIVE"],
        }],
    },
]

PLAN = {
    "date_normalizations": [
        {"principal_id": "united-states", "canonical_date": "2026-08-10", "local_date": "2026-08-10"},
        {"principal_id": "iran", "canonical_date": "2026-08-10", "local_date": "1405-05-19"},
    ]
}

QUERY = {
    "information_needed": ["positions on reopening"],
    "source_requirements": [{"acceptable_tiers": ["T1"], "original_language_required": True}],
}


def attempt(principal_id, *, result="NO_MATCH", source_ref=None):
    iran = principal_id == "iran"
    value = {
        "attempt_id": f"ATT-{principal_id.upper()}",
        "information_need": "positions on reopening",
        "principal_id": principal_id,
        "channel_id": "president-ir" if iran else "whitehouse-gov",
        "channel_class": "PRIMARY",
        "search_method": "DIRECT_FIRST_PARTY_ARCHIVE",
        "language": "fa" if iran else "en",
        "query": "date-scoped archive query",
        "result": result,
        "attempted_at": "2026-08-31T19:00:00Z",
        "canonical_date": "2026-08-10",
        "local_date": "1405-05-19" if iran else "2026-08-10",
        "url": "https://president.ir/fa/Archive" if iran else "https://www.whitehouse.gov/releases/",
        "detail": "bounded archive attempt",
    }
    if source_ref:
        value["source_ref"] = source_ref
    return value


def source(source_ref, *, language="fa", tier="T1"):
    return {
        "source_ref": source_ref,
        "source_tier": tier,
        "language": language,
        "url": "https://president.ir/fa/record",
    }


def base_result():
    return {
        "status": "PARTIALLY_GATHERED",
        "sources_searched": [],
        "sources_used": [],
        "records_returned": [],
    }


def validate(attempts, result):
    return federated_proving._validate_host_acquisition(
        query=QUERY, attempts=attempts, result=result,
        profiles=PROFILES, canonical_plan=PLAN,
    )


def test_rejects_wrong_solar_hijri_date():
    attempts = [attempt("united-states"), attempt("iran")]
    attempts[1]["local_date"] = "1405-05-20"
    with pytest.raises(federated_proving.FederatedProvingError, match="canonical plan"):
        validate(attempts, base_result())


def test_rejects_off_domain_first_party_attempt():
    attempts = [attempt("united-states"), attempt("iran")]
    attempts[1]["url"] = "https://evil.example/fake"
    with pytest.raises(federated_proving.FederatedProvingError, match="outside registered"):
        validate(attempts, base_result())


def test_rejects_translation_only_t1_source():
    attempts = [attempt("united-states"), attempt("iran", result="FOUND", source_ref="IR-1")]
    result = base_result()
    result["sources_searched"] = [source("IR-1", language="en")]
    result["sources_used"] = [source("IR-1", language="en")]
    with pytest.raises(federated_proving.FederatedProvingError, match="original language"):
        validate(attempts, result)


def test_rejects_one_sided_bilateral_gathered_result():
    attempts = [attempt("united-states"), attempt("iran", result="FOUND", source_ref="IR-1")]
    result = base_result()
    result.update({
        "status": "GATHERED",
        "sources_searched": [source("IR-1")],
        "sources_used": [source("IR-1")],
        "records_returned": [{
            "information_need": "positions on reopening", "source_refs": ["IR-1"],
            "language_state": "ORIGINAL"
        }],
    })
    with pytest.raises(federated_proving.FederatedProvingError, match="united-states"):
        validate(attempts, result)
