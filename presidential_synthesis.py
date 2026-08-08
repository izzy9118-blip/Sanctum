#!/usr/bin/env python3
"""Conforming Presidential synthesis seam.

There is no direct packages -> synthesis path here. The President must first return a
proposition matrix over the immutable structured minister packages. Only a validated
matrix can be converted into synthesis input.
"""
from __future__ import annotations

import json
from typing import Callable, Dict

from proposition_matrix import required_presidential_matrix_call, synthesis_payload


class PresidentialSynthesisError(RuntimeError):
    pass


def required_presidential_synthesis(
    packages: Dict[str, dict],
    president_align: Callable[[dict], dict],
    president_synthesize: Callable[[dict], dict],
) -> tuple[dict, dict]:
    """Hard two-stage Presidential call: alignment first, synthesis second."""
    matrix = required_presidential_matrix_call(packages, president_align)
    payload = synthesis_payload(packages, matrix)
    result = president_synthesize(json.loads(json.dumps(payload)))
    if not isinstance(result, dict):
        raise PresidentialSynthesisError("Presidential synthesis must return one structured object")
    if result.get("record_type") != "presidential_synthesis":
        raise PresidentialSynthesisError("Presidential synthesis record_type is invalid")
    if result.get("inquiry_id") != matrix["inquiry_id"]:
        raise PresidentialSynthesisError("Presidential synthesis inquiry_id does not match matrix")
    if result.get("matrix_binding_sha256") != __import__("hashlib").sha256(
        json.dumps(matrix, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest():
        raise PresidentialSynthesisError("Presidential synthesis is not bound to the validated matrix")
    if result.get("certification") != "NONE_SELF_CERTIFICATION_PROHIBITED":
        raise PresidentialSynthesisError("Presidential synthesis may not self-certify truth or consensus")
    return matrix, result
