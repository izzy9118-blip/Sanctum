#!/usr/bin/env python3
"""
Sanctum projection + retrieval layer (Layer Two reads through this).

Two jobs:
  1. Build authority-free PROJECTIONS from committed corpus deeds — compact,
     tagged, and verifiable against their source (so the LLM reasons against a
     faithful rendering, not a stale one). Projections carry no authority; they
     are rebuildable from the commits, which remain the truth.
  2. RETRIEVE the deed that EMBARRASSES the current reading — indexed by
     condition and by what each deed contradicts, NOT by similarity to the
     query. Similarity retrieval returns what confirms; this returns what
     disconfirms. That is the anti-capture engine made mechanical.

Usage:  python3 projection.py build   <corpus_dir> <projections_dir>
        python3 projection.py demo    <corpus_dir> <projections_dir>
"""
import sys, os, glob, hashlib, yaml


def content_hash(rec):
    body = {k: v for k, v in rec.items() if not k.startswith("__")}
    return hashlib.sha256(yaml.safe_dump(body, sort_keys=True).encode()).hexdigest()[:12]


def build(corpus_dir, proj_dir):
    os.makedirs(proj_dir, exist_ok=True)
    built = []
    for p in sorted(glob.glob(os.path.join(corpus_dir, "*.yaml"))):
        deed = yaml.safe_load(open(p))
        if deed.get("record_type") != "decision_object":
            continue
        src_hash = content_hash(deed)
        commit = deed.get("commit", "uncommitted")
        proj = {
            "record_type": "projection",
            "projects": {"ref": deed["id"], "commit": commit},
            "projection_version": hashlib.sha256(f"{commit}:{src_hash}".encode()).hexdigest()[:12],
            "source_hash": src_hash,
            "condition": deed.get("condition"),
            "embarrasses": deed.get("embarrasses", []),
            "conclusion": deed.get("conclusion", ""),
            "claims": deed.get("propositions", []),
        }
        out = os.path.join(proj_dir, f"proj-{deed['id']}.yaml")
        open(out, "w").write(yaml.safe_dump(proj, sort_keys=False))
        built.append(proj)
    return built


def load_projections(proj_dir):
    return [yaml.safe_load(open(p)) for p in sorted(glob.glob(os.path.join(proj_dir, "*.yaml")))]


def verify(proj, corpus_dir):
    src_path = os.path.join(corpus_dir, f"{proj['projects']['ref']}.yaml")
    if not os.path.exists(src_path):
        return False, "source record absent"
    if content_hash(yaml.safe_load(open(src_path))) != proj["source_hash"]:
        return False, "STALE/LOSSY — source changed since projection; must not be reasoned against"
    return True, "faithful"


def naive_similar(framing_text, projections):
    """The efficient default — returns what CONFIRMS the framing. Included only
    to show what the constitutional retrieval refuses."""
    fw = set(framing_text.lower().split())
    return max(projections, key=lambda p: len(fw & set(p.get("conclusion", "").lower().split())), default=None)


def retrieve_disconfirming(condition, framing_tags, projections):
    """Return the deed built to embarrass this reading.

    Rank direct contradictors first, then same-condition deeds. Never rank by
    lexical similarity to the framing.
    """
    framing = set(framing_tags)
    direct = [p for p in projections if framing & set(p.get("embarrasses", []))]
    same_cond = [p for p in projections if p.get("condition") == condition and p not in direct]
    return sorted(direct, key=lambda p: len(framing & set(p["embarrasses"])), reverse=True) + same_cond


def demo(corpus_dir, proj_dir):
    projs = build(corpus_dir, proj_dir)
    print(f"built {len(projs)} projection(s); each verifiable against source.\n")

    reading_text = "not-taking is weakness; his own foresight makes his own luck"
    framing_tags = ["the-statesman-makes-his-own-luck"]
    condition = "powerlessness"

    print("CURRENT READING (possibly captured):")
    print(f"  '{reading_text}'\n")

    conf = naive_similar(reading_text, projs)
    print("what SIMILARITY retrieval would surface (confirms the framing):")
    print(f"  {conf['projects']['ref']}: {conf['conclusion']}\n")

    dis = retrieve_disconfirming(condition, framing_tags, projs)
    print("what DISCONFIRMING retrieval surfaces (obligated to embarrass the reading):")
    for p in dis:
        print(f"  {p['projects']['ref']}: {p['conclusion']}")
        print(f"      (embarrasses: {', '.join(p['embarrasses'])})")
    print()

    captured = conf["projects"]["ref"]
    corrective = dis[0]["projects"]["ref"] if dis else None
    print(f"similarity returned {captured} — the lexical neighbour, NOT the contradictor.")
    print(f"disconfirming returned {corrective} — the deed tagged to embarrass this belief,")
    print("   which similarity missed because it shares no vocabulary with the framing.")
    print("=> retrieval is tag/condition-driven, not lexical; it finds the contradictor")
    print("   the surface words would have hidden.\n")

    ok, why = verify(dis[0], corpus_dir) if dis else (True, "")
    print(f"verify({corrective}): {why}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    corpus = sys.argv[2] if len(sys.argv) > 2 else "corpus"
    pdir = sys.argv[3] if len(sys.argv) > 3 else "projections"
    if cmd == "build":
        n = build(corpus, pdir)
        print(f"built {len(n)} projections into {pdir}")
    else:
        demo(corpus, pdir)
