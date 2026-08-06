# Finding — The Custos Naming Collision

**Date:** 5 August 2026. **Resolved by:** owner ruling. **Status:** SETTLED.
This record certifies nothing beyond what it reports.

## The collision

The per-house memory pattern was founded as `custos_<house>` and laid down in
three repositories: `custos_sanctum`, `custos_horus`, `custos_talleyrand`. The
name was chosen for its sense — the keeper of a house's manner of reading — and
it was chosen without checking what already held it.

`izzy9118-blip/custos` already existed. It is the working Strauss Reader engine,
an operating repository with its own protocol, sources and tests. The pattern
and the engine were unrelated in function and identical in name, and the estate
had no way to say "custos" and be understood.

The collision was accidental, not doctrinal. Nothing in the memory pattern was
derived from the Reader, and nothing in the Reader anticipated the pattern.

## The ruling

The Reader keeps the name. It was there first, it is a working engine, and it is
named for what it does. The memory pattern is renamed to `memory_<house>`.

The pattern gave way because it is a pattern — a naming convention held in three
young folders — while the Reader is a running thing with a history. Between a
convention and an engine, the convention moves.

## What was done

Three renames by `git mv`, contents unchanged:

| repository | from | to |
| --- | --- | --- |
| Sanctum | `custos_sanctum/` | `memory_sanctum/` |
| Horus | `custos_horus/` | `memory_horus/` |
| Talleyrand | `custos_talleyrand/` | `memory_talleyrand/` |

Path references were updated where a path is load-bearing: `harness.py` (which
constructs the segment-2 path from the house name), `standards/assembly-spec.yaml`
(which declares it), this folder's `manner-of-reading.md`, and Talleyrand's
`manifest.yaml`, `README.md` and `keel.md`. Horus referenced its own folder
nowhere and needed only the rename.

`memory_strauss` and `memory_xenophon` do not exist. They did not exist under the
old name either; those houses have never carried the pattern.

## What was deliberately not changed

**The Ukraine run receipt** (`reports/ukraine/talleyrand-2026-08-05.run.yaml`)
still records `Talleyrand/custos_talleyrand/manner-of-reading.md`. That run
happened, and at that hour the path was true. A receipt rewritten to match a
later world is no longer a receipt.

**The third-epoch first sailing** (`first-sailing-third-epoch.md`) still names
the pattern `CUSTOS_<HOUSE>` and still says "per the Custos pattern". It is a
preserved first sailing, and this folder's own manner of reading holds that such
a record is preserved, never overwritten. This finding supersedes its naming; it
does not edit it.

**The word as vocabulary.** Talleyrand's `manifest.yaml` still keys the record
`custos:`, and the assembly spec still names segment 2 `custos_manner_of_reading`.
These name a record type, not a location, so nothing breaks. Whether the estate's
vocabulary should also drop the word is a separate question and remains open for
the owner.

## The lesson

A naming law is not established by being coherent. It is established by being
checked against what already occupies the name. The pattern was laid across three
repositories before anyone asked whether "custos" was free — and it was not free,
in this same estate, in a repository the harness config already lists.

Before a name is made law across houses, the estate is searched for it first.
