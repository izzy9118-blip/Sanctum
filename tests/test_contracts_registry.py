from __future__ import annotations

from copy import deepcopy

import pytest

from sanctum_federation.contracts import ContractSet
from sanctum_federation.errors import SanctumFederationError
from sanctum_federation.integrity import (
    object_sha256_without_integrity,
    verify_object_integrity,
)
from sanctum_federation.registry import RegistrySnapshot

from .helpers import SANCTUM_ROOT, envelope


def test_contracts_compile_and_active_registry_entry_is_valid():
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)

    assert registry.version == "1.1.0"
    assert len(registry.entries) == 1
    assert registry.entries[0].minister_id == "MIN-000000001"
    assert registry.entries[0].routing_status == "AVAILABLE"


def test_envelope_binds_exact_registry_and_available_minister():
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    value = envelope(registry)

    contracts.validate_envelope(value)
    verify_object_integrity(value, "envelope_sha256", "Inquiry Envelope")
    commit = registry.verify_checkout_and_envelope(
        value,
        verify_checkout=False,
    )
    selected = registry.selected_entries(value)

    assert commit == value["routing"]["registry_snapshot"]["git_commit"]
    assert [entry.minister_id for entry in selected] == ["MIN-000000001"]


def test_wrong_release_selection_is_rejected_even_with_valid_envelope_hash():
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    value = deepcopy(envelope(registry))
    value["routing"]["selected_ministers"][0]["repository_commit"] = "0" * 40
    value["integrity"]["envelope_sha256"] = (
        object_sha256_without_integrity(value)
    )

    contracts.validate_envelope(value)
    with pytest.raises(
        SanctumFederationError,
        match="pinned registry entry",
    ):
        registry.selected_entries(value)


def test_nonisolated_dispatch_is_rejected_by_existing_contract():
    contracts = ContractSet.load(SANCTUM_ROOT)
    registry = RegistrySnapshot.load(SANCTUM_ROOT, contracts)
    value = deepcopy(envelope(registry))
    value["dispatch_policy"]["isolated_context_required"] = False
    value["integrity"]["envelope_sha256"] = (
        object_sha256_without_integrity(value)
    )

    with pytest.raises(
        SanctumFederationError,
        match="schema validation",
    ):
        contracts.validate_envelope(value)
