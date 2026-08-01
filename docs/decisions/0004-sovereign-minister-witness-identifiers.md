# Decision 0004 — Preserve sovereign minister witness identifiers

**Status:** Adopted for federation contract revision

## Problem

The ministerial-report schema previously required every evidence witness to use the federation-local pattern `CORPUS-WIT-###`. Sovereign minister repositories already assign stable, auditable witness identifiers within their own documentary systems. Xenophon, for example, has admitted `XEN-WIT-PRI-001` and `XEN-WIT-SEC-001`.

Creating a second unregistered alias only to satisfy Sanctum would divide identity, obscure provenance, and make Sanctum the silent owner of ministerial evidence.

## Decision

Sanctum accepts the stable witness identifiers assigned by a sovereign minister repository when a ministerial report also carries the exact source identifier, repository commit, and repository path.

The federation contract therefore validates structured sovereign identifiers such as `CORPUS-WIT-001` and `XEN-WIT-PRI-001` without rewriting one into the other.

## Safeguards

- The identifier must already belong to the reporting repository's admitted corpus.
- The report must include `source_id`, `repository_commit`, and `path`.
- Sanctum may validate and preserve the identifier but may not silently rename it.
- An identifier accepted by syntax alone is not thereby admitted; admission remains a sovereign repository act.
- Existing reports and `CORPUS-WIT-###` identifiers remain valid.
- Artificial-intelligence self-certification remains prohibited.

## Consequence

`ministerial-report.schema.json` advances from contract version 1.2.0 to 1.3.0. This resolves `SANCTUM-XENOPHON-WITNESS-ID-COMPATIBILITY-001` at the federation-contract level. Xenophon must still prove that each transmitted witness ID is admitted in its own pinned corpus.
