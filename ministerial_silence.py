import copy


STANDARD_ID = "MINISTERIAL-SILENCE-001"
STATES = {
    "NOT_ADDRESSED",
    "NOT_ASKED",
    "OUTSIDE_MY_GROUND",
    "UNCERTAIN",
    "REJECTED",
    "AFFIRMED",
}


class MinisterialSilenceError(ValueError):
    pass


def _props(package):
    return {p["proposition_id"]: p for p in package.get("propositions", [])}


def validate_silence_semantics(package):
    if package.get("silence_semantics_standard") != STANDARD_ID:
        raise MinisterialSilenceError("missing or wrong silence semantics standard")
    issues = package.get("issue_register")
    states = package.get("issue_states")
    if not isinstance(issues, list) or not issues:
        raise MinisterialSilenceError("issue_register must be a non-empty list")
    if not isinstance(states, list):
        raise MinisterialSilenceError("issue_states must be a list")

    issue_ids = [i.get("issue_id") for i in issues]
    if any(not x for x in issue_ids) or len(issue_ids) != len(set(issue_ids)):
        raise MinisterialSilenceError("issue_register contains missing or duplicate issue_id")
    state_ids = [s.get("issue_id") for s in states]
    if len(state_ids) != len(set(state_ids)):
        raise MinisterialSilenceError("duplicate issue state")
    if set(state_ids) != set(issue_ids):
        raise MinisterialSilenceError("every registered issue requires exactly one state")

    propositions = _props(package)
    uncertainties = package.get("uncertainties", [])
    for item in states:
        state = item.get("state")
        if state not in STATES:
            raise MinisterialSilenceError(f"invalid ministerial state: {state}")
        refs = item.get("proposition_refs", [])
        if not isinstance(refs, list) or len(refs) != len(set(refs)):
            raise MinisterialSilenceError("proposition_refs must be a unique list")
        unknown = set(refs) - set(propositions)
        if unknown:
            raise MinisterialSilenceError(f"unknown proposition refs: {sorted(unknown)}")

        if state in {"AFFIRMED", "REJECTED"} and not refs:
            raise MinisterialSilenceError(f"{state} requires proposition evidence")
        if state in {"NOT_ADDRESSED", "NOT_ASKED"} and refs:
            raise MinisterialSilenceError(f"{state} may not carry proposition refs")
        if state == "UNCERTAIN" and not refs and not item.get("uncertainty_ref"):
            raise MinisterialSilenceError("UNCERTAIN requires a proposition or uncertainty reference")
        if item.get("uncertainty_ref") is not None:
            ref = item["uncertainty_ref"]
            if not isinstance(ref, int) or ref < 0 or ref >= len(uncertainties):
                raise MinisterialSilenceError("uncertainty_ref does not resolve")
        if state == "OUTSIDE_MY_GROUND" and not item.get("basis"):
            raise MinisterialSilenceError("OUTSIDE_MY_GROUND requires an explicit basis")

    out = copy.deepcopy(package)
    out["silence_semantics_validated"] = True
    return out


def issue_state_map(package):
    validated = validate_silence_semantics(package)
    return {x["issue_id"]: x["state"] for x in validated["issue_states"]}
