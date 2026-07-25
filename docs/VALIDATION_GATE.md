# Sanctum — The Validation Gate (Layer One enforcement)

**Status:** CURRENT. This document governs the Validation Gate that enforces the Assembly's constitutional guarantees at the boundary to authoritative memory.

---

## 1. What the gate is

The gate is the enforcement form of the Secretary's validation. It is the single
act that confers authority. The runtime may calculate and *propose*, but a
proposed record is **inert** until it passes the gate and is merged to the
canonical record. So authority is not conferred by the runtime writing a file —
it is conferred by the gate passing it. This is what makes *"only Git may
remember authoritatively"* physically real: the gate is the "only."

A directory tree is passive — it can hold a dissent file but cannot refuse a
synthesis that buried one. The gate is the active guard that makes the tree's
guarantees real rather than aspirational.

---

## 2. Where it runs, and how authority is conferred

```
runtime emits           gate validates          merge to canonical
CANDIDATE record   -->   (this document)   -->   = AUTHORITATIVE
(inert, staged)          pass / fail / flag       (Layer One truth)
```

- Candidates live in a staging state (a proposal branch / PR region). They carry
  no authority and are never read as truth.
- The gate runs as a required check at the boundary to the canonical record.
- On **pass**, the candidate may be merged; the merge is the authority-conferring
  act.
- On **fail**, the candidate is rejected — and the rejection is itself recorded
  (see §5). It is never silently dropped.
- On **flag** (see §4), the record is routed to the outside ground for human
  judgment; the gate does not pretend to have decided what it cannot.

---

## 3. The check catalog (each derived from a guarantee)

### A. Structural conformance
- **A1 schema-valid** — every record validates against its committed schema in
  `schemas/`. A record that doesn't conform is not a record.
- **A2 bounded size** — every record is within the size bound, because a record
  the LLM runtime cannot fit in context is unusable to the thing that must read
  it. Bounded records are a condition of the runtime working at all.
- **A3 provenance present** — every record carries its producer identity pinned
  by commit (minister repo + SHA), the pinned records it consumed, and — for
  runtime outputs — the projection version it read, so a reader can confirm the
  LLM reasoned against a faithful rendering of the real record.

### B. Dismantling-organ guarantees
- **B1 nine elements present** — the dismantling-record contains all nine
  required elements, none empty.
- **B2 exclusion-with-reason** — every excluded item carries a recorded reason.
  Reject on any exclusion lacking rationale. *This is the check that makes
  omission auditable rather than invisible.*
- **B3 classification-with-rationale** — every classification and juxtaposition
  carries its schema and rationale, so a framing smuggled inside a category is as
  visible as an outright exclusion.
- **B4 raw framing preserved** — the raw submission is present and unaltered;
  removal is forbidden, so the dismantling can always be checked against what it
  started from.
- **B5 permitted-verbs only** — mechanically detectable forbidden-verb outputs
  (a declared "correct interpretation," a pre-synthesis of ministers, a ranked
  political end, an inference committed as fact) are rejected. What is not
  mechanically detectable is **flagged**, not passed (see §4).

### C. Participation & ministerial
- **C1 universal participation** — a report exists for every registered minister
  for this inquiry; none silently dropped. A recorded *"outside my ground, for
  these reasons"* is a complete report and satisfies this check.
- **C2 kind-typing** — every proposition is typed by kind, and none exceeds its
  kind (a `documented_finding` must cite fixed witnesses; a concealment/inner
  claim is capped at `working_hypothesis` or below). Rhetoric is not a field.

### D. Synthesis & dissent
- **D1 dissent is first-class** — dissent is a separately-committed object with
  its own history. A synthesis whose validity requires an absent or deleted
  dissent is rejected. You cannot lose a dissent that exists as its own object.
- **D2 synthesis shows its work** — where synthesis is present, it states each
  minister's conclusion *and ground*; a convergence of conclusions over divergent
  grounds is flagged, not passed as unanimity.
- **D3 divergence recorded as result** — where grounds diverge, an affirmative
  non-synthesis result exists, so the record distinguishes "preserved because
  they disagreed" from "missing because something failed."
- **D4 presidential opinion marked as own** — it is recorded as the President's
  own voice, distinct from the ministerial reports and never as consensus.

### E. Meta-guarantee (the outside ground)
- **E1 legible** — the record is human-readable, text-serialized, diffable.
  Since we have forgotten the external schemas, legibility to the outside ground
  is the last architectural check we have; it is non-negotiable.
- **E2 rejections auditable** — every gate rejection is recorded with its reason
  (§5). The gate cannot capture by silent rejection any more than the dismantling
  organ may capture by silent exclusion.

---

## 4. The checkable / uncheckable split (the gate's honesty)

The gate enforces what is **mechanically checkable** and must never pretend to
have verified what it cannot. Structural guarantees (an exclusion has a reason
field; a dissent object exists; a proposition carries a kind) are checkable.
Substantive guarantees (did the dismantling organ *actually* resolve a contested
meaning inside a permitted verb? is this classification honest?) are only partly
checkable.

So every record resolves to one of three states, not two:
- **verified conformant** — passed mechanical checks;
- **flagged — not mechanically verifiable** — routed to the outside ground;
- **rejected** — failed a mechanical check, with recorded reason.

A gate that collapsed "flagged" into "passed" — that stamped a green check on
substance it never verified — would be the capture we fear wearing the costume of
validation. The three-state output is the gate telling the truth about the limit
of its own sight. This is the disconfirmation discipline applied to the gate
itself.

---

## 5. The gate is a power, and is bound like every other

The gate guards the memory, so it could capture by wrongful rejection. It is
bound by the same pattern as every organ: granted its function, denied the
adjacent authority, obliged to show its work.

- **Rejections and flags are recorded** with reasons, as auditable objects. A
  captured gate cannot quietly reject the record that would embarrass a framing,
  because its rejection is itself in the record.
- **The outside ground sits above the gate.** The human can inspect any
  rejection or flag and override it; the override is recorded. The gate serves
  the outside ground, it does not outrank it.
- **The gate cannot silently change what it enforces.** Amending the schemas or
  the gate's own rules is itself a gated, recorded, human-reviewed act in
  `constitution/` and `schemas/`. The rules the gate enforces have the same
  visible-history guarantee as everything else.

---

## 6. Implemented dependencies

The committed record schemas live in `schemas/record-schemas.yml` and
`schemas/record-schemas-batch2.yml`. The executable gate lives in
`gate/gate.py`, and the required pull-request workflow lives in
`.github/workflows/gate.yml`.

The gate enforces structural conformance, record size, provenance, dismantling
constraints, universal participation, proposition typing, dissent preservation,
synthesis/non-synthesis requirements, and the distinct status of Presidential
Opinions. Substantive judgments that cannot be mechanically verified remain
flagged for the outside ground rather than silently passed.
