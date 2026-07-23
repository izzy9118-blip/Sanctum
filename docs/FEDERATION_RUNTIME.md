# Sanctum Federation Runtime

## Scope

This runtime implements two bounded Assembly mechanisms:

1. The dispatcher delivers one immutable Inquiry Envelope to each selected
   minister in a separate execution directory.
2. The Constitutional Secretary independently validates every returned
   Ministerial Report and writes a separate validation record.

It does not select ministers, create evidence bundles, judge ministerial
findings, synthesize a Presidential Opinion, certify an inquiry, or admit any
record to a permanent archive.

## Authority Boundary

Git remains canonical. The dispatcher accepts a minister only when:

- the Inquiry Envelope is schema-valid and its self-hash is correct;
- the envelope pins the exact Sanctum registry commit and file hash;
- the selected minister exactly matches an `AVAILABLE` registry entry;
- the local minister checkout is clean and at the registered release commit;
- the local adapter command is supplied separately by the operator.

The constitutional registry never supplies an executable command. This keeps
canonical data from becoming an implicit code-execution mechanism.

## Local Dispatch Config

The local config is operational input, not a constitutional record. Every
command is an argument array and is executed directly without a shell. Four
complete-argument placeholders are required:

- `{repository_root}`
- `{repository_commit}`
- `{envelope_path}`
- `{output_dir}`

Example for the released Custos adapter:

```json
{
  "config_version": "1.0.0",
  "adapters": [
    {
      "minister_id": "MIN-000000001",
      "repository_full_name": "izzy9118-blip/custos",
      "repository_root": "/absolute/path/to/custos",
      "command": [
        "custos-inquiry",
        "federation-run",
        "--repo-root",
        "{repository_root}",
        "--release-commit",
        "{repository_commit}",
        "--envelope",
        "{envelope_path}",
        "--evidence-bundle",
        "/absolute/path/to/evidence-bundle.json",
        "--output",
        "{output_dir}",
        "--reasoner-command",
        "/absolute/path/to/reasoner",
        "--reasoner-provider",
        "PROVIDER",
        "--reasoner-model",
        "MODEL",
        "--prompt-id",
        "PROMPT-ID",
        "--prompt-version",
        "1.0"
      ],
      "report_relative_path": "ministerial-report.json",
      "timeout_seconds": 1800
    }
  ]
}
```

Runtime credentials remain in the process environment. They must not be placed
in this config or committed to Git.

## Dispatch

```bash
sanctum-federation dispatch \
  --sanctum-root /path/to/Sanctum \
  --envelope /path/to/inquiry-envelope.json \
  --adapter-config /path/to/dispatch-config.json \
  --output /path/to/new-dispatch-record
```

The destination must not already exist. Sanctum retains only:

- the exact Inquiry Envelope;
- each bounded Ministerial Report;
- each separate Secretary Validation Record;
- the integrity-bearing Dispatch Receipt.

Minister-private execution packages and corpora are deleted after validation.
Adapter stdout and stderr are not archived; the Dispatch Receipt preserves only
their byte counts and SHA-256 digests so operational logs cannot silently carry
credentials or private model output into the Assembly record.

## Secretary Validation

The Secretary independently checks:

- JSON and schema validity;
- report and envelope self-hashes;
- exact envelope and question binding;
- exact registry, minister, repository, release, and adapter binding;
- governing-manifest Git bytes and blob identity;
- execution chronology;
- reference integrity;
- evidence excerpts re-read and hashed from reachable Git commits;
- termination consistency;
- the boundary between ministerial submission and Assembly authority.

A report with a ministerial termination status of `FAILED`,
`INSUFFICIENT_EVIDENCE`, or `OUT_OF_JURISDICTION` may still pass documentary
validation. Such validation means the report is authentic and internally
well-formed; it does not mean the inquiry succeeded.

Every validation record states:

```text
constitutional_effect: PROVENANCE_VALIDATION_ONLY
certification_status: NOT_CERTIFIED
```

Certification and Presidential synthesis remain later, distinct mechanisms.
