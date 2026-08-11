# Decision 0008 — Bind Canonical Horus Acquisition

**Date:** 2026-08-10  
**Status:** `OWNER_CERTIFIED`

## Owner directive

During the first Xenophon R2 proving inquiry, the owner directed the system to fix the Horus retrieval failure exposed by the 2026-08-10 U.S.–Iran test and, after review of the proposed architecture, authorized implementation with: **“Let do it.”**

The failure was procedural rather than evidentiary: 10 August 2026 had been manually rendered as 20 Mordad 1405 instead of 19 Mordad 1405, and ad-hoc external search had been allowed to stand in for a deterministic first-party acquisition procedure. The existing language, provenance, adversarial, and source-absence safeguards correctly exposed a T1 gap but could not prove that the search producing the gap had itself been correctly executed.

## Certified Horus pin

- Repository: `izzy9118-blip/Horus`
- Previous constitutional state: floating checked-out Horus commit recorded by the environment manifest
- New certified pin: `ec82d22f1cb6d7d944b8347f8c7516b1fd38affc`
- Horus amendment: `HORUS-AMD-005 — deterministic primary-source acquisition`
- Response contract: `contracts/horus-query-response.schema.json` / `1.3.0`
- Acquisition receipt contract: `contracts/acquisition-receipt.schema.json`
- Principal source profile contract: `contracts/principal-source-profile.schema.json`
- Canonical acquisition runtime: `runtime/gather.py`
- Acquisition protocol: `HORUS-ACQUISITION-1.0`

## What is now required

A forward reasoned Assembly inquiry must use the Horus repository state pinned by `registry/horus.yaml`. The checked-out Horus repository may not merely be recorded after the fact; its commit must equal the Sanctum-owned pin.

The Horus response must carry a deterministic acquisition receipt binding:

- the pinned principal source profiles used;
- code-generated date normalization, including local-calendar dates where applicable;
- every acquisition attempt separately from every documentary source;
- the required first-party search steps for original-language T1;
- whether the minimum protocol was attempted and whether it was sufficiently reachable;
- the canonical Horus runtime identity; and
- the Horus repository commit that actually produced the response.

For original-language T1, `SEARCHED_NOT_FOUND` is not admissible merely because searches were attempted. Every required first-party acquisition step must have been attempted and reachable enough to return `FOUND` or `NO_MATCH`. Blocked or unavailable first-party routes remain acquisition failures or incomplete acquisition and do not become negative evidence.

## Sanctum enforcement

Sanctum now:

1. rejects Horus responses without `HORUS-ACQUISITION-1.0` receipts;
2. requires acquisition-attempt identifiers for unresolved searched states;
3. rejects `SEARCHED_NOT_FOUND` when a recorded T1 acquisition requirement is unsatisfied;
4. preserves investigative principal and time scope into adversarial MHAQ requests;
5. invokes `<estate>/Horus/runtime/gather.py` by default for production sovereign rounds;
6. treats arbitrary `--horus-command` execution as an explicit test-only override;
7. requires each Horus response provenance commit to equal the exact Horus checkout used by the round; and
8. requires the constitutional environment's Horus checkout and governing artifacts to equal `registry/horus.yaml`.

## Historical preservation

The following predecessors remain preserved rather than overwritten:

- Horus response contract `1.2.0`;
- Sanctum adversarial Horus query contract `1.1.0`;
- Sanctum constitutional environment contract `1.0.0`; and
- Sanctum constitutional environment standard `1.0.0`.

## Constitutional limits preserved

This decision does not certify:

- that every source on the public internet can be found;
- that an inaccessible source is absent;
- that `SEARCHED_NOT_FOUND` proves the underlying thing does not exist;
- that a source is true merely because it is first-party;
- that Horus may judge the meaning of evidence;
- that an acquisition or ministerial report is complete; or
- that the interrupted U.S.–Iran proving inquiry has passed.

Horus remains a gatherer. `completeness: PENDING_PROBE` remains binding. Artificial-intelligence self-certification remains prohibited.

## Next gate

The interrupted U.S.–Iran proving inquiry must be rerun through the new pinned Horus acquisition boundary. The inquiry is not certified by this infrastructure change. Its next legitimate result must show the actual acquisition trace, including the correct Iranian local date and any first-party channel failures or successful acquisitions.

Certification authority: `REPOSITORY_OWNER_DIRECTIVE`  
Certification status: `OWNER_CERTIFIED`
