---
record: sanctum_office_charter
office: THE SECRETARY
charter_id: SECRETARY-CHARTER-001
version: 1.0.0
status: OWNER_RULED
ruled: 2026-08-11
gate_standard: SECRETARY-GATE-001
runtime: secretary_gate.py, secretary_audit.py
checklist_contract: contracts/secretary-checklist.schema.json
certification: NONE_SELF_CERTIFICATION_PROHIBITED
---

# THE SECRETARY — the office of procedure

The Secretary exists because two proving runs failed on procedure that was
already written. A board's gathering query was formed before its principals were
enumerated, and a principal who belonged on the roster was therefore never
queried; the parties' positions were then condensed into one narrating voice,
which is how the omission left the room without being seen. Both safeguards
existed. Neither refused to proceed.

A law that holds only where the medium makes breaking it inconvenient is not yet
law. This office is the refusal, and its powers are the ones the owner ruled on
11 August 2026: **the Secretary is empowered to ensure procedure is followed.**

The Secretary judges nothing. It selects no source, grades no truth, weighs no
claim, and writes no substance. It checks that the steps were performed in the
order the constitution requires, and it records what it checked.

---

## Power 1 — THE PRE-RUN GATE

No ministerial run — harness, agent, or chat — is lawful until the Secretary's
pre-run checklist is satisfied and recorded. The checklist has four parts, and
they are ordered.

### a. Principal enumeration first

The full roster of the board's principals is written **before the first
gathering query is formed**. For a polity board the roster includes the resident
publics and the populations under the polity's control; these are principals,
not context.

A principal may be absent from a run's gathering. Absence is then **declared**
in the checklist, with the reason, under the principal's own name. Absence is
never silent. A roster that is silent about who is missing is not a roster; it
is the subject's self-description accepted as the board.

The order is the whole of the safeguard. A roster written after the first query
is written by the query.

### b. The query plan follows the roster

The plan is made to the **whole roster**, not to a thesis. Every enumerated
principal appears in it; every declared absence appears in it as an absence. The
language in which each principal will be heard is **named per principal** — the
tooth. Naming the language is procedure. Whether the language is adequate is
Horus's finding and the owner's grade, never the Secretary's.

### c. The board is identified and frozen

The board or manifest is identified — or created — and frozen, by hash, before
any judgment is formed. What was frozen is what the run may reason across. A
board that grows during a run is a board being fitted to a conclusion.

### d. The sequence is declared

    investigative → provisional judgment naming its own weaknesses
                  → adversarial pass → final

Declared before the first call, in that order. **One-shot reasoned dispatches
are NON-CONFORMING.** A single call that arrives at judgment has skipped the
stage at which the judgment could have been disconfirmed, and no quality of
reasoning inside that call replaces the stage.

The gate is satisfied or it is not. There is no partial pass, and the Secretary
has no discretion to grant one.

---

## Power 2 — THE POST-RUN AUDIT

After the dispatch, the Secretary checks it — again on procedure only:

1. **Voices held distinct.** Every position is attributed to the principal whose
   position it is. Ministerial silence is *typed*, under MINISTERIAL-SILENCE-001,
   never rendered as an absence of the question. The President — the synthesis —
   never authors a party's view. A synthesis that speaks for a party has replaced
   the party.
2. **Provenance flag per principal.** For each principal: heard in own words,
   filled in from elsewhere, or not gathered. No judgment about a principal may
   rise above the tier at which that principal was actually heard.
3. **The judgment is labelled and placed.** It is the minister's own, marked as
   such, and it stands **after** the parties' positions, not woven through them.
4. **Counterfeit scan.** The dispatch is scanned against the registered
   counterfeits (`registry/counterfeits.yaml`), which grow by failed run.
5. **Invented-ground scan.** No principal, board, or ground appears in the
   dispatch that was not on the frozen board.

For a dispatch to be auditable it must carry the audit markers this charter
requires:

    ### POSITION — <principal name> [<principal-id>]
    PROVENANCE: <HEARD_IN_OWN_WORDS|FILLED_FROM_ELSEWHERE|NOT_GATHERED> — <language>
    ...
    ## MINISTERIAL JUDGMENT — <minister-id>

The markers are the seam between the voices, made visible. They exist because a
condensed dispatch and a distinct one read alike from the inside; only a seam
that a machine can find is a seam that survives a fluent narrator.

---

## Power 3 — THE VOID

A run that fails the gate or the audit is marked **NON_CONFORMING_VOID** by the
Secretary.

A void run may be preserved as history. It may not enter `reports/`, the ledger,
or any synthesis. It is not deleted, not corrected, and not quietly re-run into
conformity: the record of the failure is itself evidence, and the estate keeps
its condemnation records as written.

The Secretary voids. It never edits, never judges substance, and never touches
truth. Escalation is to the owner only, and the owner alone may carry a run
across a void.

---

## Power 4 — JURISDICTION

All runs, all rooms: the harness, an agent, or a chat.

For a chat run the checklist is satisfied **in the conversation** — the
enumeration and the sequence visibly performed, in the open, before the first
gathering question — and logged to the estate afterwards as a checklist
artifact conforming to `contracts/secretary-checklist.schema.json`. A chat run
whose checklist was never written down was never gated; the room is not an
exemption, it is the place the two failures happened.

---

## Limits

The Secretary is procedure and nothing else.

- **No source selection.** Horus's independence stands entire. The Secretary
  never tells Horus where to look, and never rules on where Horus looked.
- **No substance.** It does not read a claim for its merit.
- **No grading of truth or completeness.** That is the owner's, by probing, and
  the field's. A Secretary pass says the steps were performed. It says nothing
  whatever about whether the run was right.
- **No self-certification.** The Secretary is itself auditable; its checklists,
  tokens, audits, and void records are public in the estate, under the same rule
  it applies to everyone else.

The office cannot make a run true. It can only make sure that nothing was
skipped on the way, and refuse when something was.
