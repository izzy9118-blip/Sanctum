# Decision 0010: Register Stars as a bounded research corpus

Date: 2026-09-01
Status: Owner authorized

## Decision

Sanctum registers `izzy9118-blip/Stars` at commit
`44d05c09aa75a043497930863abf82364dd8ab6a` as a first-class, read-only
research and provenance corpus in the constitutional estate.

Stars is neither a minister nor a live acquisition organ. It therefore does not
join the universal minister roster, receive an inquiry automatically, produce a
ministerial report, or replace Horus. Its structured Stars, narratives, source
records, and audits are available only through an explicit, pin-bound context
selection followed by the evidence-admission rules of the inquiry.

## Constitutional boundary

Every forward constitutional environment manifest binds:

- the exact Stars repository commit and Sanctum registry pin;
- the Stars source-witness method;
- the allowed `stars`, `narratives`, and `sources` roots;
- a deterministic digest covering every tracked file in those roots; and
- a hash-bound catalog of every structured `STAR-*.yaml` record.

The Stars checkout must be clean and must equal the immutable Sanctum pin. A
missing repository, changed commit, dirty checkout, altered artifact, missing
method, or catalog mismatch fails closed.

## Evidentiary meaning

`status: FACT` inside a Star is the Stars repository's internal editorial state.
It does not become a Sanctum truth certification merely because the repository
is registered or the file is hash-bound.

Stars may supply historical context, research architecture, provenance leads,
source classifications, and explicit rival-witness controls. It may not, by
itself, satisfy Horus live-acquisition receipts, current official-position
requirements, principal coverage, original-language requirements, date cutoffs,
or source-absence claims. Absolute local source paths recorded in Stars remain
locator metadata; they do not prove that an inquiry acquired the source bytes.

Automatic prompt injection is prohibited. A later context-admission interface
must record exactly which Star artifacts and propositions were selected for a
particular inquiry before any model sees them.

## Certification

This decision certifies repository identity, role, and reproducibility only.
It certifies neither the truth nor the completeness of the Stars corpus.
