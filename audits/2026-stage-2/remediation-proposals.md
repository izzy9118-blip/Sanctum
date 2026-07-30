# Stage 2 Remediation Proposals

These are proposals only. Each requires an owner decision and a later implementation stage.

## R1 — Register Xenophon only after a sovereign interface exists

**Status:** `PROPOSED_PENDING_OWNER_APPROVAL`

**Finding addressed:** `documented_gap` at `registry/ministers.yaml:20-104`.

**Minimal additive proposal:** after the owner identifies the sovereign Xenophon repository and approves its interface, add a new registry revision that pins one manifest, one speech-mechanism locator, one deed-index locator, and one immutable commit. Preserve the current registry version as predecessor history. Do not infer the repository from the Stage 2 prompt.

## R2 — Register Austen only after a sovereign interface exists

**Status:** `PROPOSED_PENDING_OWNER_APPROVAL`

**Finding addressed:** `documented_gap` at `registry/ministers.yaml:20-104`.

**Minimal additive proposal:** after owner review, add a forward registry revision containing the Austen repository, pinned commit, manifest path, adapter path, and evidence-bound output contract. Do not create or modify the minister repository from Sanctum.

## R3 — Register Graham only after a sovereign interface exists

**Status:** `PROPOSED_PENDING_OWNER_APPROVAL`

**Finding addressed:** `documented_gap` at `registry/ministers.yaml:20-104`.

**Minimal additive proposal:** after owner review, add a forward registry revision containing the Graham repository, pinned commit, manifest path, adapter path, and output contract. Preserve all predecessor registry states.

## R4 — Make the Xenophon Stage 2 audit reproducible

**Status:** `PROPOSED_PENDING_OWNER_APPROVAL`

**Finding addressed:** `documented_gap` in `audits/2026-stage-2/xenophon-register-audit.md`, located through `registry/ministers.yaml:20-104`.

**Minimal additive proposal:** once Xenophon is registered, create a successor audit record that cites the exact four register definitions, three guard definitions, all deed bindings, and the pinned repository commit. Keep this unable-to-assess audit unchanged as the historical predecessor.

## R5 — Add an explicit Strauss self-reference guard

**Status:** `PROPOSED_PENDING_OWNER_APPROVAL`

**Finding addressed:** `documented_gap` at `izzy9118-blip/Strauss:speech/speech-mechanism.yaml:377-448` and `izzy9118-blip/Strauss:adapter.py:45-62`.

**Minimal additive proposal:** in a later Strauss-owned change, add one explicit output guard prohibiting reliance on the minister's own works, career, or past as authority, then add one behavioral test that rejects such reliance. The change should be made in the sovereign Strauss repository and consumed by Sanctum only through a later pinned registry revision.

## Non-proposals

No implementation is proposed here for probable gaps. The C6 and C8 Strauss findings require owner reading before any remedy is formulated. Talleyrand remains outside this stage because the registry marks the repository as not yet established.