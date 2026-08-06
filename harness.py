#!/usr/bin/env python3
"""The Sovereign Harness — Station 1 of the sovereign map.

    PULL      git pull the estate; record every repository's HEAD.
    ASSEMBLE  build the context deterministically, in the order fixed by
              standards/assembly-spec.yaml. The parity gate is enforced here,
              as code. HOLD blocks the run.
    CALL      send the context to an endpoint that is a config line.
    WRITE     commit report, run manifest, and parity manifest to the estate.

The harness gathers nothing and judges nothing. It reads committed records,
orders them by law, calls, and writes back. It certifies nothing — including
itself.

No third-party dependency: a dependency is a dependence. Standard library only,
Python 3.9 and up.

Usage:
    harness.py parity --board ukraine
    harness.py run --board ukraine --minister talleyrand [--carry-mark]
                   [--no-pull] [--dry-run] [--provider stub]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SPEC_PATH = "standards/assembly-spec.yaml"
TIERS = ("T1", "T2", "T3", "T4", "T5")
GATE_TIERS = ("T1", "T2", "T4")


# --------------------------------------------------------------------------
# a strict YAML subset, so the estate stays free of dependencies
# --------------------------------------------------------------------------

def yaml_load(text: str):
    """Parse the YAML subset the estate's machine-readable records use.

    Supported: nested mappings, sequences, sequences of mappings, quoted and
    bare scalars, folded and literal block scalars, comments, document markers.
    Anything else raises rather than guessing.
    """
    lines = []
    for raw in text.split("\n"):
        if raw.strip() in ("---", "..."):
            continue
        lines.append(raw)
    value, index = _parse_block(lines, 0, 0)
    index = _next(lines, index)
    if index < len(lines):
        raise ValueError(
            "line %d is outside the supported subset (a plain multi-line scalar, "
            "a flow collection, or a misindented key): %r"
            % (index + 1, lines[index]))
    return value


def _content(lines, i):
    """The i-th line stripped of comments, or None if it carries no content."""
    if i >= len(lines):
        return None
    line = lines[i]
    if not line.strip() or line.lstrip().startswith("#"):
        return None
    out, quote = [], None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and out and out[-1] in " \t":
            break
        else:
            out.append(ch)
    text = "".join(out).rstrip()
    return text if text.strip() else None


def _indent(line):
    return len(line) - len(line.lstrip(" "))


def _next(lines, i):
    while i < len(lines) and _content(lines, i) is None:
        i += 1
    return i


def _parse_block(lines, i, indent):
    i = _next(lines, i)
    if i >= len(lines):
        return None, i
    line = _content(lines, i)
    if _indent(line) < indent:
        return None, i
    return (_parse_seq if line.lstrip().startswith("- ") or line.strip() == "-"
            else _parse_map)(lines, i, _indent(line))


def _parse_seq(lines, i, indent):
    items = []
    while True:
        i = _next(lines, i)
        if i >= len(lines):
            break
        line = _content(lines, i)
        if _indent(line) != indent or not re.match(r"^-(\s|$)", line.strip()):
            break
        rest = line.strip()[1:].strip()
        # the item runs until the next content line at or left of this dash
        end = i + 1
        while end < len(lines):
            nxt = _content(lines, end)
            if nxt is not None and _indent(nxt) <= indent:
                break
            end += 1
        if not rest:
            value = _parse_block(lines[i + 1:end], 0, indent + 1)[0] if end > i + 1 else None
        elif re.match(r"^[^:#]+:(\s|$)", rest):
            # a mapping whose first key shares the dash's line
            body = [" " * (indent + 2) + rest] + lines[i + 1:end]
            value = _parse_map(body, 0, indent + 2)[0]
        else:
            value = _scalar(rest)
        items.append(value)
        i = end
    return items, i


def _parse_map(lines, i, indent):
    mapping = {}
    while True:
        i = _next(lines, i)
        if i >= len(lines):
            break
        line = _content(lines, i)
        if _indent(line) != indent:
            break
        match = re.match(r"^([^:]+):(.*)$", line.strip())
        if not match:
            raise ValueError("cannot parse line %d: %r" % (i + 1, line))
        key = _scalar(match.group(1).strip())
        rest = match.group(2).strip()
        if rest in (">", ">-", "|", "|-", ">+", "|+"):
            value, i = _block_scalar(lines, i + 1, indent, rest)
        elif rest:
            value, i = _scalar(rest), i + 1
        else:
            # a sequence may sit at the key's own indent; a mapping may not
            peek = _next(lines, i + 1)
            nxt = _content(lines, peek) if peek < len(lines) else None
            if nxt is not None and _indent(nxt) == indent and re.match(r"^-(\s|$)", nxt.strip()):
                value, i = _parse_seq(lines, peek, indent)
            else:
                value, i = _parse_block(lines, i + 1, indent + 1)
        mapping[key] = value
    return mapping, i


def _block_scalar(lines, i, indent, style):
    body, j = [], i
    while j < len(lines):
        line = lines[j]
        if line.strip() and _indent(line) <= indent:
            break
        body.append(line[indent + 2:] if len(line) > indent else "")
        j += 1
    while body and not body[-1].strip():
        body.pop()
    if style.startswith("|"):
        text = "\n".join(body)
    else:
        out, run = [], []
        for line in body:
            if line.strip():
                run.append(line.strip())
            else:
                out.append(" ".join(run))
                run = []
        out.append(" ".join(run))
        text = "\n".join(p for p in out if p)
    if style.endswith("+"):
        text += "\n"
    elif not style.endswith("-"):
        text += "\n"
    return text, j


def _scalar(token: str):
    if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'":
        return token[1:-1]
    low = token.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~", ""):
        return None
    if re.match(r"^-?\d+$", token):
        return int(token)
    if re.match(r"^-?\d+\.\d+$", token):
        return float(token)
    return token


def yaml_dump(value, indent=0):
    """Emit the same subset. Used for the run and parity manifests."""
    pad = " " * indent
    out = []
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                out.append("%s%s:" % (pad, key))
                out.append(yaml_dump(item, indent + 2))
            elif isinstance(item, (dict, list)):
                out.append("%s%s: %s" % (pad, key, "{}" if isinstance(item, dict) else "[]"))
            else:
                out.append("%s%s: %s" % (pad, key, _emit_scalar(item)))
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                body = yaml_dump(item, indent + 2).split("\n")
                out.append("%s- %s" % (pad, body[0].strip()))
                out.extend(body[1:])
            elif isinstance(item, list):
                out.append("%s-" % pad)
                out.append(yaml_dump(item, indent + 2))
            else:
                out.append("%s- %s" % (pad, _emit_scalar(item)))
    else:
        out.append("%s%s" % (pad, _emit_scalar(value)))
    return "\n".join(out)


def _emit_scalar(value):
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "" or re.search(r'[:#\n]|^\s|\s$|^[-?&*!|>%@`"\']', text):
        return json.dumps(text)
    return text


# --------------------------------------------------------------------------
# PULL
# --------------------------------------------------------------------------

def git(repo: Path, *args):
    result = subprocess.run(["git", "-C", str(repo)] + list(args),
                            capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def pull(estate: Path, repos, do_pull: bool):
    """Pull every repository of the estate and record where each one stands."""
    state = []
    for name in repos:
        path = estate / name
        entry = {"repository": name}
        if not (path / ".git").exists():
            entry["state"] = "NOT_A_REPOSITORY"
            state.append(entry)
            continue
        if do_pull:
            code, _, err = git(path, "pull", "--ff-only")
            entry["pull"] = "ok" if code == 0 else "failed"
            if code != 0:
                entry["pull_detail"] = err.split("\n")[0][:200]
        else:
            entry["pull"] = "skipped"
        code, head, _ = git(path, "rev-parse", "HEAD")
        entry["head"] = head if code == 0 else "NO_COMMITS"
        code, branch, _ = git(path, "branch", "--show-current")
        entry["branch"] = branch if code == 0 and branch else "detached or unborn"
        code, dirty, _ = git(path, "status", "--porcelain")
        entry["worktree"] = "clean" if code == 0 and not dirty else "modified"
        state.append(entry)
    return state


# --------------------------------------------------------------------------
# the parity gate — a rule, not an opinion
# --------------------------------------------------------------------------

def read_principal_file(path: Path):
    """Read a Horus principal file's header. Tier bodies are not interpreted."""
    header = {"tiers": {}}
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            break
        match = re.match(r"^- (T[1-5]) (last refresh|status|language|language state): (.+)$",
                         line.strip())
        if match:
            tier = header["tiers"].setdefault(match.group(1), {})
            field = {"last refresh": "refreshed", "status": "status",
                     "language": "language", "language state": "language_state"}
            tier[field[match.group(2)]] = match.group(3).strip()
            continue
        match = re.match(r"^- ([A-Za-z ]+): (.+)$", line.strip())
        if match:
            header[match.group(1).strip().lower().replace(" ", "_")] = match.group(2).strip()
    return header


def parity(estate: Path, board: dict, as_of: dt.date):
    """Compute the board's parity manifest. PASS or HOLD, with gaps named."""
    horus = estate / "Horus"
    tolerance = {t: board["decay_tolerance_days"].get(t) for t in TIERS}
    principals, gaps = [], []

    for entry in board["roster"]:
        path = horus / entry["file"]
        record = {"id": entry["id"], "name": entry["name"],
                  "type": entry["type"], "file": entry["file"]}
        if not path.exists():
            record["file_state"] = "ABSENT"
            record["tiers"] = {t: {"status": "NOT_GATHERED"} for t in TIERS}
            gaps.append({
                "principal": entry["name"],
                "gap": "no file: the principal has not been gathered",
                "tiers_required": list(GATE_TIERS),
            })
            principals.append(record)
            continue

        header = read_principal_file(path)
        record["file_state"] = "PRESENT"
        record["assembly_date"] = header.get("assembly_date", "unrecorded")
        record["completeness"] = header.get("completeness", "unrecorded")
        record["tiers"] = {}
        for tier in TIERS:
            found = header["tiers"].get(tier, {})
            status = found.get("status", "UNRECORDED")
            refreshed = found.get("refreshed", "unrecorded")
            age, stale = None, None
            try:
                age = (as_of - dt.date.fromisoformat(refreshed)).days
                stale = age > tolerance[tier]
            except ValueError:
                pass
            cell = {"status": status, "last_refresh": refreshed,
                    "tolerance_days": tolerance[tier]}
            if age is not None:
                cell["age_days"] = age
                cell["staleness"] = "STALE" if stale else "within tolerance"
            else:
                cell["staleness"] = "UNCOMPUTABLE"
            if tier == "T1":
                # the language tooth: a principal heard only in translation has
                # not been heard, however thick the file (charter HORUS-AMD-001)
                cell["language"] = found.get("language", "UNRECORDED")
                cell["language_state"] = found.get("language_state", "UNRECORDED")
                record["heard_in_own_words"] = (
                    status == "FILLED" and cell["language_state"] == "ORIGINAL")
            record["tiers"][tier] = cell

            if tier == "T1" and status == "FILLED" and \
                    cell["language_state"] != "ORIGINAL":
                gaps.append({
                    "principal": entry["name"],
                    "gap": "T1 is declared FILLED but its language state is %s; "
                           "the charter fills T1 only on original-language "
                           "primary matter" % cell["language_state"],
                    "language": cell["language"]})

            if tier in GATE_TIERS:
                if status != "FILLED":
                    gaps.append({"principal": entry["name"],
                                 "gap": "%s is %s; the gate requires FILLED" % (tier, status)})
                elif stale:
                    gaps.append({"principal": entry["name"],
                                 "gap": "%s is STALE: %d days, tolerance %d"
                                        % (tier, age, tolerance[tier])})
                elif stale is None:
                    gaps.append({"principal": entry["name"],
                                 "gap": "%s refresh date unreadable: %r" % (tier, refreshed)})
        principals.append(record)

    verdict = "PASS" if not gaps else "HOLD"
    unheard = [p["name"] for p in principals if not p.get("heard_in_own_words")]
    return {
        "record_type": "horus_parity_manifest",
        "board": board["board"],
        "board_type": board.get("board_type", "unspecified"),
        "as_of": as_of.isoformat(),
        "roster_ref": "boards/%s.yaml" % board["board"],
        "gate_rule": board.get("gate_rule", ""),
        "verdict": verdict,
        "gap_count": len(gaps),
        "gaps": gaps,
        "language_mark": {
            "rule": "charter HORUS-AMD-001: T1 is filled only on original-language "
                    "primary matter; a principal heard only in translation has not "
                    "been heard",
            "heard_in_own_words": [p["name"] for p in principals
                                   if p.get("heard_in_own_words")],
            "not_heard_in_own_words": unheard,
            "carries_mark": bool(unheard),
            "consequence": "No judgment about a principal may rise above the tier "
                           "at which that principal was actually heard. This mark "
                           "travels into any run made across this board.",
        },
        "principals": principals,
        "generated_by": "harness.py, by rule; PASS/HOLD is not an opinion",
        "note": ("A file's silence means NOT GATHERED, never \"nothing there.\" "
                 "Horus certifies nothing; files are graded by owner probing."),
    }


# --------------------------------------------------------------------------
# ASSEMBLE — the order is law
# --------------------------------------------------------------------------

class Context:
    def __init__(self):
        self.parts = []
        self.sources = []

    def segment(self, title, body):
        self.parts.append("=" * 72 + "\n" + title + "\n" + "=" * 72 + "\n\n" + body)

    def file(self, title, repo, path: Path, root: Path):
        text = path.read_text(encoding="utf-8")
        self.sources.append({
            "repository": repo,
            "path": str(path.relative_to(root)),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "bytes": len(text.encode("utf-8")),
        })
        self.segment(title, text)

    def text(self):
        return "\n\n".join(self.parts) + "\n"

    def sha256(self):
        return hashlib.sha256(self.text().encode("utf-8")).hexdigest()


def assemble(estate: Path, spec: dict, house: str, minister: str, board: dict,
             manifest: dict, question: Path, carried_mark):
    """Build the context in the spec's segment order. Nothing is skipped."""
    ctx = Context()
    house_dir = estate / house
    hub = estate / "Sanctum"
    horus = estate / "Horus"

    ctx.segment("HOW THIS CONTEXT WAS ASSEMBLED", (
        "Assembled by harness.py under %s version %s, which is law and lives in "
        "the constitutional repository.\n\nThe order below was not chosen at run "
        "time. Segments: %s.\n\nThe harness gathers nothing and judges nothing."
        % (SPEC_PATH, spec["version"],
           ", ".join(s["name"] for s in spec["segments"]))))

    # 1 — house records, in the house's own load_order
    for item in manifest["load_order"]["records"]:
        if item.endswith("/ in index order"):
            index = yaml_load((house_dir / "deeds" / "index.yaml").read_text(encoding="utf-8"))
            for deed in index["deeds"]:
                ctx.file("DEED %s — %s" % (deed["id"], deed["title"]),
                         house, house_dir / "deeds" / deed["file"], estate)
            continue
        ctx.file("%s / %s" % (house, item), house, house_dir / item, estate)

    # 2 — the manner of reading
    ctx.file("%s / memory_%s/manner-of-reading.md" % (house, house.lower()),
             house, house_dir / ("memory_%s" % house.lower()) / "manner-of-reading.md",
             estate)

    # 3 — the parity manifest, first among the board's records, and a gate
    ctx.file("HORUS PARITY MANIFEST — %s (the gate)" % board["board"],
             "Horus", horus / "manifests" / carried_mark["manifest_file"], estate)
    if carried_mark["carried"]:
        ctx.segment("MARK — THIS RUN CROSSED A HOLD", carried_mark["text"])

    # 4 — the board's files, roster order
    for entry in board["roster"]:
        path = horus / entry["file"]
        title = "HORUS FILE — %s (%s)" % (entry["name"], entry["type"])
        if path.exists():
            ctx.file(title, "Horus", path, estate)
        else:
            ctx.segment(title + " — NOT GATHERED",
                        "No file exists for this principal. Under the Horus "
                        "charter this means NOT GATHERED. It does not mean "
                        "nothing there, and it may not be reasoned across as "
                        "though the record were empty.")

    # 5 — the ledger
    ledger = hub / "ledger" / ("%s.yaml" % minister)
    if ledger.exists():
        ctx.file("LEDGER — %s (open commitments)" % minister, "Sanctum", ledger, estate)
    else:
        ctx.segment("LEDGER — %s" % minister, (
            "NOT_ESTABLISHED. The binding ledger is Station 3 of the map and is "
            "not built. No open commitment is carried into this run, and no "
            "judgment made here is yet bound by one.\n\nThis segment is recorded, "
            "never omitted: silence in a record means NOT ESTABLISHED, never "
            "\"settled elsewhere.\""))

    # 6 — the question, last
    ctx.file("THE BOARD QUESTION", "Sanctum", question, estate)
    return ctx


# --------------------------------------------------------------------------
# CALL — the endpoint is a config line
# --------------------------------------------------------------------------

def call(config: dict, context: str):
    provider = config["provider"]
    if provider == "stub":
        return {
            "text": ("STUB PROVIDER — NO MODEL REASONED.\n\n"
                     "This run exercised PULL, ASSEMBLE, CALL and WRITE against a "
                     "local stub. The context was assembled, ordered by the spec, "
                     "hashed and delivered; no endpoint was reached and no mind "
                     "read it. Nothing below the line is analysis.\n\n"
                     "context sha256: %s\ncontext bytes: %d\nsegments: %d\n"
                     % (hashlib.sha256(context.encode()).hexdigest(),
                        len(context.encode()), context.count("=" * 72) // 2)),
            "model": "stub",
            "usage": {},
        }

    key = os.environ.get(config.get("key_env", ""), "")
    if not key:
        raise SystemExit("CALL: %s is not set in the environment; no key, no call."
                         % config.get("key_env", "<key_env unset>"))

    if provider == "anthropic":
        url = config.get("endpoint", "https://api.anthropic.com/v1/messages")
        body = {"model": config["model"],
                "max_tokens": config.get("max_tokens", 8000),
                "messages": [{"role": "user", "content": context}]}
        headers = {"content-type": "application/json",
                   "x-api-key": key,
                   "anthropic-version": config.get("api_version", "2023-06-01")}
        data = _post(url, body, headers)
        return {"text": "".join(b.get("text", "") for b in data.get("content", [])),
                "model": data.get("model", config["model"]),
                "usage": data.get("usage", {})}

    if provider == "openai_compatible":
        url = config.get("endpoint", "http://localhost:11434/v1/chat/completions")
        body = {"model": config["model"],
                "max_tokens": config.get("max_tokens", 8000),
                "messages": [{"role": "user", "content": context}]}
        headers = {"content-type": "application/json",
                   "authorization": "Bearer %s" % key}
        data = _post(url, body, headers)
        return {"text": data["choices"][0]["message"]["content"],
                "model": data.get("model", config["model"]),
                "usage": data.get("usage", {})}

    raise SystemExit("CALL: unknown provider %r" % provider)


def _post(url, body, headers):
    request = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise SystemExit("CALL failed: HTTP %s — %s"
                         % (error.code, error.read().decode("utf-8")[:500]))
    except urllib.error.URLError as error:
        raise SystemExit("CALL failed: %s" % error.reason)


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def load_config(path: Path):
    return yaml_load(path.read_text(encoding="utf-8"))


def run(args, config):
    estate = Path(config["estate"]).expanduser()
    hub = estate / "Sanctum"
    horus = estate / "Horus"
    as_of = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    stamp = as_of.isoformat()

    spec = yaml_load((hub / SPEC_PATH).read_text(encoding="utf-8"))
    board = yaml_load((horus / "boards" / ("%s.yaml" % args.board)).read_text(encoding="utf-8"))

    ministers = config["ministers"]
    if args.minister not in ministers:
        raise SystemExit("no minister %r in config" % args.minister)
    house = ministers[args.minister]["house"]
    manifest = yaml_load((estate / house / "manifest.yaml").read_text(encoding="utf-8"))

    print("PULL")
    repo_state = pull(estate, config["repositories"], not args.no_pull)
    for entry in repo_state:
        print("  %-12s %-8s %s %s" % (entry["repository"], entry.get("pull", "-"),
                                      entry.get("head", "")[:12], entry.get("worktree", "")))

    print("\nASSEMBLE")
    manifest_name = "%s-%s.yaml" % (args.board, stamp)
    parity_record = parity(estate, board, as_of)
    parity_path = horus / "manifests" / manifest_name
    if not args.dry_run:
        parity_path.parent.mkdir(parents=True, exist_ok=True)
        parity_path.write_text(yaml_dump(parity_record) + "\n", encoding="utf-8")
    print("  parity manifest: Horus/manifests/%s" % manifest_name)
    print("  verdict: %s (%d gaps)" % (parity_record["verdict"], parity_record["gap_count"]))
    for gap in parity_record["gaps"]:
        print("    - %s: %s" % (gap["principal"], gap["gap"]))

    carried = {"carried": False, "manifest_file": manifest_name, "text": ""}
    if parity_record["verdict"] == "HOLD":
        if not args.carry_mark:
            print("\n  THE GATE HOLDS. The run is blocked.")
            print("  No analysis runs on an asymmetric board. Gather the named "
                  "gaps, or\n  re-run with --carry-mark to cross the HOLD as "
                  "owner, which writes the\n  mark into the context, the report, "
                  "and the run manifest.")
            if not args.dry_run:
                print("\n  The parity manifest was written. Nothing else was.")
            return 2
        carried["carried"] = True
        carried["text"] = (
            "This run was carried across a HOLD by explicit owner override.\n\n"
            "The board is asymmetric. The parity gate returned HOLD with %d gaps:\n\n%s\n\n"
            "Under the Parity Law bias enters as the given — including as file "
            "depth. What follows is reasoned on a board whose depth is uneven, "
            "and the unevenness is not incidental to the judgment: the files that "
            "exist are Russian, and the files that do not exist are the other "
            "side of the war. Every judgment in this run carries this mark. Say "
            "plainly, in the report, what you could not see."
            % (parity_record["gap_count"],
               "\n".join("  - %s: %s" % (g["principal"], g["gap"])
                         for g in parity_record["gaps"])))
        print("\n  HOLD CARRIED by --carry-mark. The mark is in the context.")

    question = hub / "boards" / args.board / ("%s-question.md" % stamp)
    if args.question_file:
        # resolve: every source is recorded relative to the estate root, and a
        # relative path given on the command line has no root to be relative to
        question = Path(args.question_file).expanduser().resolve()
    if not question.exists():
        raise SystemExit("ASSEMBLE: no board question at %s" % question)

    ctx = assemble(estate, spec, house, args.minister, board, manifest, question, carried)
    context = ctx.text()
    print("  segments: %d   sources: %d   bytes: %d"
          % (len(ctx.parts), len(ctx.sources), len(context.encode())))
    print("  context sha256: %s" % ctx.sha256())

    if args.dry_run:
        print("\nDRY RUN — no call, no write.")
        if args.emit_context:
            Path(args.emit_context).write_text(context, encoding="utf-8")
            print("  context written to %s" % args.emit_context)
        return 0

    print("\nCALL")
    call_config = dict(config["model"])
    if args.provider:
        call_config["provider"] = args.provider
    print("  provider: %s   model: %s" % (call_config["provider"], call_config.get("model", "-")))
    started = dt.datetime.now(dt.timezone.utc)
    answer = call(call_config, context)
    finished = dt.datetime.now(dt.timezone.utc)
    print("  returned %d bytes in %.1fs" % (len(answer["text"].encode()),
                                            (finished - started).total_seconds()))

    print("\nWRITE")
    out_dir = hub / "reports" / args.board
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / ("%s-%s.md" % (args.minister, stamp))
    run_path = out_dir / ("%s-%s.run.yaml" % (args.minister, stamp))

    head = ["# %s — %s board — %s" % (args.minister.capitalize(), args.board, stamp), ""]
    if carried["carried"]:
        head += ["> **CARRIED ACROSS A HOLD.** The parity gate returned HOLD with "
                 "%d gaps and this run was carried across it by explicit owner "
                 "override. The board is asymmetric. See the run manifest and "
                 "`Horus/manifests/%s`." % (parity_record["gap_count"], manifest_name), ""]
    if call_config["provider"] == "stub":
        head += ["> **STUB PROVIDER — NO MODEL REASONED.** This run proves the "
                 "harness, not a judgment. Nothing below is analysis.", ""]
    head += ["---", "", ""]
    report_path.write_text("\n".join(head) + answer["text"].strip() + "\n", encoding="utf-8")

    run_record = {
        "record_type": "harness_run_manifest",
        "harness": "Sanctum/harness.py",
        "assembly_spec": {"path": SPEC_PATH, "version": spec["version"],
                          "status": spec.get("status", "unrecorded")},
        "run": {
            "board": args.board,
            "minister": args.minister,
            "house": house,
            "date": stamp,
            "started_utc": started.isoformat(),
            "finished_utc": finished.isoformat(),
        },
        "parity": {
            "manifest": "Horus/manifests/%s" % manifest_name,
            "verdict": parity_record["verdict"],
            "gap_count": parity_record["gap_count"],
            "gaps": parity_record["gaps"],
            "carried_across_hold": carried["carried"],
            "override": "--carry-mark, owner" if carried["carried"] else None,
        },
        "context": {
            "sha256": ctx.sha256(),
            "bytes": len(context.encode()),
            "segments": len(ctx.parts),
            "sources": ctx.sources,
        },
        "call": {
            "provider": call_config["provider"],
            "model_requested": call_config.get("model"),
            "model_returned": answer.get("model"),
            "endpoint": call_config.get("endpoint", "provider default"),
            "usage": answer.get("usage", {}),
        },
        "estate": repo_state,
        "outputs": {
            "report": str(report_path.relative_to(hub)),
            "run_manifest": str(run_path.relative_to(hub)),
        },
        "what_this_run_did_not_do": [
            "gather anything - the harness never gathers",
            "judge anything - the harness never judges",
            "extract ledger entries - Station 3 is unbuilt and the schema is the owner's",
            "certify anything, including itself",
        ],
    }
    run_path.write_text(yaml_dump(run_record) + "\n", encoding="utf-8")
    print("  %s" % report_path.relative_to(estate))
    print("  %s" % run_path.relative_to(estate))
    print("  %s" % parity_path.relative_to(estate))
    print("\nNothing was committed. The estate is written, not sealed.")
    return 0


def parity_only(args, config):
    estate = Path(config["estate"]).expanduser()
    as_of = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    board = yaml_load((estate / "Horus" / "boards" / ("%s.yaml" % args.board))
                      .read_text(encoding="utf-8"))
    record = parity(estate, board, as_of)
    print(yaml_dump(record))
    return 0 if record["verdict"] == "PASS" else 2


def main(argv=None):
    parser = argparse.ArgumentParser(description="The Sovereign Harness — Station 1.")
    parser.add_argument("--config", default=str(Path(__file__).resolve().parent.parent / "config.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--board", required=True)
    common.add_argument("--date", help="run date, YYYY-MM-DD (default: today)")

    run_parser = sub.add_parser("run", parents=[common])
    run_parser.add_argument("--minister", required=True)
    run_parser.add_argument("--question-file")
    run_parser.add_argument("--provider", help="override the config's provider")
    run_parser.add_argument("--carry-mark", action="store_true",
                            help="owner override: cross a HOLD, carrying the mark")
    run_parser.add_argument("--no-pull", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--emit-context", help="with --dry-run, write the context here")

    sub.add_parser("parity", parents=[common])

    args = parser.parse_args(argv)
    config = load_config(Path(args.config).expanduser())
    return run(args, config) if args.command == "run" else parity_only(args, config)


if __name__ == "__main__":
    sys.exit(main())
