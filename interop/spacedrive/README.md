# Sanctum Portable Context Contract

This directory defines the interoperability layer between Sanctum, Spacedrive, and replaceable LLM runtimes.

GitHub remains canonical. Spacedrive provides distributed discovery, content identity, synchronization, and controlled agent access. LLMs consume deterministic Portable Inquiry Capsules rather than relying on chat memory.

## Authority boundary

This layer does not replace repository admission, correction, certification, or Git history. Imported model output remains candidate material until admitted through Sanctum's governing process.

## Local use

```bash
python interop/spacedrive/scripts/export_capsule.py --source . --output dist/sanctum-capsule
python interop/spacedrive/scripts/verify_capsule.py dist/sanctum-capsule
```
