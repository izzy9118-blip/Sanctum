# Decision 0011 — Repin Horus Acquisition-Ground Binding

**Date:** 2026-09-01  
**Status:** `OWNER_CERTIFIED`

## Owner directive

The owner directed the Assembly to fix the Horus acquisition defects one at a
time and authorized this hardening with: **“do it.”**

## Certified Horus pin

- Repository: `izzy9118-blip/Horus`
- Previous pin: `ec82d22f1cb6d7d944b8347f8c7516b1fd38affc`
- New pin: `38718c226116ee59f7d6cb9a75f3b90c4943ecf2`
- Horus amendment: `HORUS-AMD-006 — acquisition-ground binding`
- Acquisition protocol: `HORUS-ACQUISITION-1.0`
- Canonical runtime: `runtime/gather.py`

## Defects closed

The prior runtime recorded acquisition fields without binding them tightly enough
to its deterministic plan and principal registry. It could accept an incorrect
local-calendar date, an unregistered URL host, or a host-asserted channel class.
Its staged documentary result was not required to trace back to FOUND attempts,
so translated or one-sided material could be represented as complete bilateral
original-language T1 ground.

The new pin requires:

1. every day in a bounded time scope to be normalized by code;
2. every attempt's canonical/local date pair to match that plan;
3. channel class, method, and language to match the pinned principal profile;
4. attempt and final-source URLs to remain on the registered channel or an
   explicitly allowed redirect host;
5. every searched documentary source to trace to a FOUND attempt for the same
   information need; and
6. every `GATHERED` original-language T1 response to cite qualifying ground for
   every information need and every principal in scope.

The Iran Geneva mission profile now records its observed canonical host
`geneva.mfa.gov.ir` and explicitly permits the legacy redirect host
`geneva.mfa.ir`.

## Constitutional limits preserved

This repin certifies the repository identity and enforcement boundary. It does not
certify that a source is true, that every relevant source can be found, that an
unavailable endpoint is a negative finding, or that the pending U.S.–Iran inquiry
has passed. Horus remains a gatherer and retains `completeness: PENDING_PROBE`.

Certification authority: `REPOSITORY_OWNER_DIRECTIVE`  
Certification status: `OWNER_CERTIFIED`
