# Worldview Anchors — Initial Architecture Map

**Date:** 2026-08-17  
**Status:** DISCOVERY / MAPPING ONLY  
**Authority:** none conferred by this record  
**Implementation status:** NOT AUTHORIZED BY THIS RECORD  
**Completeness:** PENDING_PROBE

## Purpose

This record preserves the first agreed architecture map arising from `worldview-anchors-discovery-record.md` and the subsequent repository inspection of Sanctum and Horus.

It is descriptive and provisional. It does not ratify a worldview constellation, amend an existing constitutional standard, alter Horus evidence handling, modify a minister repository, or authorize runtime implementation.

## Settled correction: the Secretary surrounds the voyage

The Secretary is not merely a late-stage auditor downstream from the President.

The Secretary is the procedural and provenance custodian of the Assembly's lawful movement from beginning to end. The Secretary does not perform Horus gathering, ministerial reasoning, or Presidential synthesis. The Secretary ensures that a later stage cannot acquire constitutional standing unless its required predecessors, bindings, and artifacts exist.

The existing independent final Secretary audit remains distinct and necessary. It is not moved upward or absorbed into runtime execution. The resulting model is:

```text
SECRETARY — PROCEDURAL CUSTODY
        ↓
guards constitutional sequence and required bindings
        ↓
REASONING / GATHERING PROCESS
        ↓
SECRETARY — INDEPENDENT FINAL AUDIT
        ↓
VALIDATION GATE
```

The Secretary therefore surrounds the voyage rather than occupying only one station in it.

## First-order constitutional map

```text
                         OWNER
                           │
                 names / amends the stars
                           │
                           ▼
                ┌─────────────────────┐
                │       SANCTUM       │
                │ constitutional law  │
                │                     │
                │ WORLDVIEW           │
                │ CONSTELLATION       │
                └──────────┬──────────┘
                           │
                    version + hash
                           │
                           ▼
              ┌─────────────────────────┐
              │       SECRETARY         │
              │ procedural custody      │
              │ provenance custody      │
              │ sequence enforcement    │
              └────────────┬────────────┘
                           │
                           ▼
              CONSTITUTIONAL ENVIRONMENT
                           │
                           ▼
                     RAW INQUIRY
                           │
                           ▼
                     DISMANTLING
                           │
                           ▼
                   COMMON GROUND
                           │
                           ▼
                     HORUS / PARITY
                           │
                           ▼
                       MINISTERS
                           │
                    investigative query
                           │
                           ▼
                         HORUS
                           │
                           ▼
                provisional judgments
                           │
                           ▼
                 ADVERSARIAL HORUS
                           │
                           ▼
                 final minister reports
                           │
                           ▼
                 proposition genealogy
                           │
                           ▼
                  PRESIDENTIAL MATRIX
                           │
                           ▼
                 PRESIDENTIAL SYNTHESIS
                           │
                           ▼
              ┌─────────────────────────┐
              │       SECRETARY         │
              │ independent final audit │
              └────────────┬────────────┘
                           │
                           ▼
                    VALIDATION GATE
```

This diagram is still a map, not a final runtime specification. The Secretary should be understood as continuously guarding transition legitimacy even where the diagram shows discrete positions.

## Constitutional ownership of the sky

The current mapping places the worldview constellation in Sanctum constitutional law.

The constellation is not:

- a Horus doctrine;
- a ministerial doctrine;
- a replacement for a minister's reconstructed method;
- an evidence class;
- a truth certification mechanism.

The constellation governs orientation and attention across the voyage.

A minister remains sovereign and may contradict the constellation. A worldview anchor must not silently rewrite the minister's corpus, method, findings, or voice.

## Settled correction: stars are facts; works are the documentary sky-ground

A prior conversational mapping step incorrectly moved the star one level too high by treating a work, or a foundational thesis abstracted from a work, as the star itself. That interpretation is superseded.

**Settled mapping rule:** a star is a fact or carefully bounded historical finding established in the documentary record. A work is documentary ground from which one or more stars may be established. Related factual stars form a constellation.

The structure is therefore:

```text
WORK / SOURCE
      ↓
documentary evidence
      ↓
STAR — FACT OR BOUNDED HISTORICAL FINDING
      ↓
related factual stars
      ↓
CONSTELLATION
      ↓
orientation / navigational attention
```

The constellation's worldview should emerge from the relationship among documented facts rather than from an abstract doctrine imposed on the facts beforehand.

### Example: Curtis / Strauss / neoconservatism

A permissible star would be a bounded historical proposition of this kind:

```text
SOURCE WORK:
Adam Curtis, The Power of Nightmares

STAR / FACT:
Individuals influenced by Leo Strauss became involved in the development of
American neoconservatism and attempted to bring ideas they associated with
Strauss into political practice.

QUALIFICATION:
Whether those individuals correctly understood Strauss is a separate and
contestable question.
```

The factual distinction must be preserved:

```text
ESTABLISHABLE FACT:
They believed, claimed, received, transmitted, or acted upon ideas they
understood as derived from Strauss.

NOT ESTABLISHED MERELY BY THAT FACT:
Their understanding accurately represented Strauss's teaching.
```

The same discipline applies across every constellation. Reception of a thinker is not automatically identical with the thinker; an institution's claim is not automatically the material outcome; a historical relationship is not automatically a causal totalization.

### Provisional star-record shape

The corrected mapping suggests that a future star record would need fields such as:

```text
STAR ID
FACT / BOUNDED HISTORICAL FINDING
SOURCE WORK(S)
UNDERLYING DOCUMENTARY GROUND
DATE / PERIOD
PERSONS / INSTITUTIONS / EVENTS INVOLVED
FACT TYPE
QUALIFICATIONS
DISPUTED ELEMENTS
WHAT THIS STAR DOES NOT ESTABLISH
PROVENANCE
```

This is a mapping proposal only, not an adopted schema.

### Consequence for navigation

The works do not issue runtime commands merely by existing, and Horus is not instructed to "think like" an author. Navigation must arise transparently from the factual constellation and remain distinguishable from the documentary facts that compose it.

The exact transformation from factual constellation to inquiry-specific navigation remains to be mapped. No hidden runtime interpreter is authorized by this record.

### Consequence for reefs

Earlier reef language assumed that an anchor thesis might be contradicted by later findings. Because stars are now mapped as facts or bounded historical findings, the reef model requires a further pass. A later record may:

- contradict the factual status of a star;
- qualify its scope;
- reveal that a relationship was overstated;
- challenge a navigational inference drawn from a constellation without challenging the constituent facts themselves.

These cases must not be collapsed. The existing reef concept remains provisional until this distinction is mapped explicitly.

## Existing binding seam

`constitutional_environment.py` already records and validates the committed constitutional environment for a forward inquiry. It binds, among other things:

- the Sanctum repository commit;
- the governing Assembly specification;
- the minister registry;
- governing Sanctum contracts and standards;
- the pinned Horus repository, runtime, and contracts;
- every established minister's pinned repository and manifest.

The present mapping therefore identifies the constitutional-environment manifest as the probable place where a future worldview constellation's identity, version, and hash would become inquiry-bound and auditable.

This is a mapping conclusion only. No field or contract change is authorized here.

## Existing context seam

The current `harness.assemble()` order is:

```text
minister house records
→ minister manner of reading
→ Horus parity manifest
→ Horus ground files
→ ledger
→ question
```

The discovery record proposes that the worldview constellation be present before the parity manifest. The exact location remains unresolved.

The mapping question is therefore:

```text
minister house records
→ minister manner of reading
→ ? WORLDVIEW CONSTELLATION ?
→ Horus parity manifest
→ Horus ground files
→ ledger
→ question
```

The final placement must preserve both conditions:

1. the minister receives the constitutional orientation governing the common voyage; and
2. the minister's sovereign reconstructed mind is not silently rewritten by that orientation.

## Horus boundary

Horus already has constitutional protections that must remain intact:

- Horus gathers and does not judge;
- own-words and primary-source priority remain independent of worldview preference;
- source selection remains Horus's responsibility except for explicit-document requests;
- search failure and documented absence remain distinct;
- `SEARCHED_NOT_FOUND` may not become proof of absence;
- adversarial gathering does not become confirmation merely because no contrary record was acquired;
- completeness remains `PENDING_PROBE`.

The worldview constellation may eventually guide **what to look for** or **what risks deserve explicit search**, but it must not alter the documentary record returned by Horus.

Operational compression:

> The stars steer the ship; they do not paint the coastline.

## Reef concept

A future contradiction between a star, a constellation-derived navigation inference, and documentary findings must be represented without altering the evidence itself. The corrected star ontology requires this relation to be typed rather than treated as one generic contradiction.

Conceptual form only:

```text
finding
  evidence: unchanged
  sky_relation:
      target: <star-id or navigation-derivation-id>
      relation: <CONTRADICTS | QUALIFIES | LIMITS | ORTHOGONAL>
      reef: true
```

A reef is therefore a possible signal for examining the factual star, its scope, or an inference drawn from its constellation. It is never a license to downgrade, suppress, reinterpret, or relabel contrary evidence.

## President boundary

The Presidential proposition matrix should remain an attributable representation of what the ministers actually reported.

The current map therefore distinguishes:

```text
MINISTERIAL PROPOSITION MATRIX
        ↓
anchor-immune representation of ministerial positions
        ↓
PRESIDENTIAL SYNTHESIS
        ↓
explicit worldview tilt may be declared here if constitutionally authorized
```

The President may orient by the stars, but the matrix should not be rewritten to make ministerial disagreement disappear.

## Secretary responsibilities in the mapped model

### Procedural custody

Before and during the voyage, the Secretary should ensure that required constitutional preconditions are actually present before a dependent stage can acquire constitutional standing.

Examples include:

- inquiry identity exists;
- correct constitutional environment is fixed;
- correct worldview-constellation identity/version/hash is bound, if and when such a constellation is adopted;
- required standards and runtime triggers are loaded;
- established ministers are accounted for;
- pinned Horus identity is preserved;
- required predecessor stages have produced their artifacts;
- outputs consumed by a later stage are the actual persisted outputs of the required earlier stage;
- required investigative, adversarial, genealogy, matrix, and other mandatory stages are not silently skipped.

The Secretary does not execute those other offices' substantive work.

### Independent final audit

The existing independent Secretary audit remains a separate deterministic re-reading of persisted artifacts.

For a future worldview constellation, a final Secretary audit may eventually need to verify such structural questions as:

- was the required constellation loaded;
- was its exact version/hash recorded;
- was it loaded at the constitutionally required stage;
- were navigation records preserved;
- were reef records preserved where produced;
- did Horus evidence remain documentary rather than sky-edited;
- did ministerial contradiction remain visible;
- was any Presidential tilt explicit rather than disguised as consensus.

The Secretary does not decide whether a star is substantively true or whether a minister's contradiction is correct. A challenge to a star's factual status must remain a documentary dispute for owner-visible review, not a Secretary truth judgment.

## Relationship to existing epistemic safeguards

The worldview constellation and the existing contested-information safeguards are mapped as different constitutional species.

```text
WORLDVIEW CONSTELLATION
"What documented relationships orient attention?"

EPISTEMIC / DEFENSIVE STANDARDS
"How must evidence be gathered, classified, genealogized, and preserved?"
```

Existing standards such as provenance-before-prevalence, source genealogy, parity, source-absence taxonomy, adversarial gathering, and domain-specific information-environment safeguards remain independently binding according to their own triggers.

The worldview constellation should not absorb or replace them.

## Current map in one sentence

The sky is composed of constellations of factual stars grounded in documentary works and sources; Sanctum owns the constitutional sky; the constitutional environment binds its exact version; the Secretary guards the lawful sequence and later audits it independently; Horus may navigate under the factual relationships the sky makes visible without altering the coastline; ministers remain sovereign enough to dispute either the facts or their significance; the President may explicitly orient by the sky without manufacturing consensus; and the owner alone admits, amends, or removes stars and constellations.

## Next mapping question

The next mapping step is intentionally narrow:

**Map how a factual constellation can generate transparent inquiry-specific navigation for Horus without inserting a hidden interpreter between the documented stars and the gathering organ.**
