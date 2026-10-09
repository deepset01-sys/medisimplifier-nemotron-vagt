"""
Record the replay set once, in one session on the final endpoint image, as docs/replay_set.md fixes it (with its
2026-10-09 Corrections entry), into the file Replay mode reads (app/replay_recording.json, once the author's reads
are in). It runs on the build VM in a one-off container of the final image, with a read-only checkout of the image's
commit, started by scripts/record_replay_run.py, which names the image once for the endpoint, the container and
--image, and hands the container its settings on standard input:

    python3 scripts/record_replay_run.py record --endpoint-id <id> --image <repo>@sha256:<digest> --out-dir <dir>

With --settings-stdin it first reads one line from standard input: a JSON object holding exactly ENDPOINT_URL,
NEBIUS_API_KEY, QWEN_JUDGE_MODEL and LLAMA_JUDGE_MODEL, each set. It puts them into its own environment, where the
gate reads them, so Docker holds none of them. A recording takes them no other way: it stops if --settings-stdin is
missing or if one of the four is already in its environment.

Before any case it checks that the endpoint's URL is https and not this machine, that the gate is the image's own
(/app/src) and equal to the checkout's src/, that every committed file it reads is the one pinned below, that /health
is ready with both judge routing keys set, and that scripts/verify_endpoint.py --all passes; otherwise it stops and
records nothing. Part A sends each of the 12 inputs to POST /v1/simplify with the text, max_tokens 1,024 and flag
mode, one case at a time; an attempt that gets a connection error, no answer within 600 s, an HTTP error or an answer
that cannot be read is repeated up to twice, 30 s later, and three failures leave the case not recorded. Before Part B
both dedicated judges are probed with an invented pair, and a failed probe stops the run. Part B calls the image's own
gate, evaluate_safety(original, rewrite, safety_mode="flag"), once per pair. ERROR verdicts are recorded as they are,
never repeated. The file is written after every attempt; the key, the endpoint's URL and the routing keys are never
written, and no text is printed. A stopped session goes on, in the same file, with the same command and --resume:
nothing recorded is sent again, an unfinished case gets only its remaining attempts, and the probe runs again before
Part B.

A rehearsal (--rehearsal) may use a stand-in endpoint, a stand-in gate, an invented checkout and settings from its
environment; its file is marked "rehearsal": true, and the reads step refuses a marked file unless it is given
--rehearsal too.

The author's reads go in afterwards; only each recorded Part A case's added_content changes:

    python scripts/record_replay.py reads --recording <recording> --reads <reads.json> --out <file>

Exit codes: 0 recorded (or reads added); 2 stopped before any case, or reads refused; 3 stopped at the probe, before
Part B; 4 stopped during Part B.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import ipaddress
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import requests

TIMEOUT_S = 600   # how long a Part A attempt waits for its answer
PAUSE_S = 30      # the wait before a failed Part A attempt is repeated
ATTEMPTS = 3      # a Part A call is made at most three times
CONNECT_TIMEOUT = 30
MAX_TOKENS = 1024
CONSENSUS = ("SAFE", "UNSAFE", "DISAGREE", "ERROR")
VERDICT_KEYS = ("llama_verdict", "qwen_verdict", "nemotron_verdict", "consensus")
THIRDS = ("short", "middle", "long")
CELLS = ("drop caught", "drop missed", "control falsely flagged", "control correctly passed")
# Invented, as in the committed run's check of the dedicated judges (scripts/run_panel_judgebench_v2.py).
PROBE = ("Patient given aspirin 81 mg daily.", "Patient takes a low-dose aspirin each day.")
IMAGE_SRC = "/app/src"   # the image's own src/, the only gate a recording may use
SETTINGS = ("ENDPOINT_URL", "NEBIUS_API_KEY", "QWEN_JUDGE_MODEL", "LLAMA_JUDGE_MODEL")   # on standard input
FILES = {
    "draw": "results/replay_set_draw.json",
    "inputs": "results/student_predictions.json",
    "drops": "results/judgebench_v2_tau1_final.json",
    "controls": "results/judgebench_v2_clean_controls.json",
    "gate": "results/judgebench_v2_panel_gate.json",
    "cut": "results/eval_v2_output_truncation.json",
}
# sha256 of every committed file this script reads from the checkout, as git stores it (LF line endings), and of the
# src/ tree (src_tree below), as committed when this script was signed. A recording stops before any case if one
# differs; a change to one of them before the recording needs a signed change here.
COMMITTED = {
    "results/replay_set_draw.json": "41ffc032c40bb38c203f77c47d0bcbf9dfc2fcf2d0928891e599b7607568f1e6",
    "results/student_predictions.json": "8c94bb7c3914cbbe796142331a15ac7ed59658cc42f5c88ae5d5281b69b72557",
    "results/judgebench_v2_tau1_final.json": "87059c6a5eb48dd52b3f5ef082af5f364393ed6a9ddc9ed2179878e2297a7c9c",
    "results/judgebench_v2_clean_controls.json": "c46c93263153abbbb53a3ca4936a0fba002538658dadb6cc715cdcbc5a5df398",
    "results/judgebench_v2_panel_gate.json": "a66b1e05448d56f865d9fc2d9ee6c25d63e907439b7d318486d9288e9225233d",
    "results/eval_v2_output_truncation.json": "a73f8e5cfa9db4820f81bca594cd8beaa70b68509b88195f5513611c949a2c42",
    "scripts/verify_endpoint.py": "fc911c74691a78e628ff31eac5d4ace348d1346d49160dff5a4f7da6f4c16aab",
}
SRC_TREE = "a5cfe9e61e8ff61b01f3a61601364cb1dc86cdbf7b845b493f9ed3dd84ff3f3b"


class Stop(Exception):
    """Ends the run: its message is printed after "STOP:", and its code is the exit code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def say(line):
    print(line, flush=True)


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise Stop(2, f"{path} cannot be read ({type(e).__name__})")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_gate(gate_src):
    """The gate module from the given src/ (the image's own /app/src in the container), loaded by its path."""
    sys.dont_write_bytecode = True
    return load_module("replay_gate", Path(gate_src) / "safety_gate.py")


def note_index(idx):
    """The evaluation input a Part B pair was built from: idx "hf<N>" and a numeric idx "N" both name index N."""
    return int(idx[2:]) if idx.startswith("hf") else int(idx)


def lf_sha256(path):
    """sha256 of a file as git stores it: with LF line endings."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def src_files(src):
    """sha256 of every file under src/, by relative path, leaving out Python's own caches."""
    root = Path(src)
    return {p.relative_to(root).as_posix(): lf_sha256(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"}


def src_tree(files):
    """One sha256 for a src/ tree: over its "path sha256" lines, sorted."""
    return hashlib.sha256("".join(f"{p} {h}\n" for p, h in sorted(files.items())).encode()).hexdigest()


def read_settings(stream, rehearsal):
    """The four settings from one line on standard input, put into this process's environment, where the gate reads
    them; never printed or written. A recording stops if one is already in its environment: Docker would hold it."""
    present = [name for name in SETTINGS if name in os.environ]
    if present and not rehearsal:
        raise Stop(2, f"{', '.join(present)} already in the environment: a recording takes its settings only on "
                      "standard input")
    try:
        settings = json.loads(stream.readline())
    except ValueError:
        settings = None
    if not (isinstance(settings, dict) and set(settings) == set(SETTINGS)
            and all(isinstance(v, str) and v.strip() for v in settings.values())):
        raise Stop(2, f"standard input must hold one line with exactly {', '.join(SETTINGS)}, each set")
    os.environ.update(settings)


def check_endpoint_url(url, rehearsal):
    """A recording talks to the deployed endpoint: https, and not this machine; a rehearsal may use a stand-in."""
    parts = urlsplit(url)
    if rehearsal:
        return
    host = (parts.hostname or "").lower()
    try:
        address = ipaddress.ip_address(host)
        local = address.is_loopback or address.is_unspecified
    except ValueError:
        local = host == "localhost" or host.endswith(".localhost")
    if parts.scheme != "https" or not host or local:
        raise Stop(2, "ENDPOINT_URL must be the endpoint's https URL, not this machine (a stand-in needs --rehearsal)")


def check_committed(checkout):
    """Every committed file this script reads, and the checkout's src/, as pinned in COMMITTED and SRC_TREE."""
    for rel, expected in COMMITTED.items():
        path = Path(checkout) / rel
        if not path.is_file() or lf_sha256(path) != expected:
            raise Stop(2, f"{rel} is not the committed file this script was signed for")
    if src_tree(src_files(Path(checkout) / "src")) != SRC_TREE:
        raise Stop(2, "the checkout's src/ is not the one this script was signed for")


def load_cases(checkout):
    """Part A's 12 cases and Part B's 16 pairs, as the draw names them, with their texts from the committed files."""
    c = Path(checkout)
    draw, inputs, drops, controls, gate, cut = (load_json(c / FILES[k]) for k in
                                               ("draw", "inputs", "drops", "controls", "gate", "cut"))
    text = {row["index"]: row["input"] for row in inputs}
    cut_at_512 = set(cut["stopped_at_cap"]["indices"])
    part_a = []
    for third in THIRDS:
        indices = draw["part_a_index"][third]
        if len(indices) != 4:
            raise Stop(2, f"the draw has {len(indices)} {third} inputs, not 4")
        for index in indices:
            if index not in text:
                raise Stop(2, f"input {index} is missing from {FILES['inputs']}")
            part_a.append({"n": len(part_a) + 1, "index": index, "third": third, "input": text[index],
                           "cut_at_512": index in cut_at_512})
    rewrite = {("corrupted", str(i["idx"])): i["edited_summary"] for i in drops["items"]}
    rewrite.update({("clean", str(i["idx"])): i["clean_ref"] for i in controls["items"]
                    if i["control_type"] == "primary_paired"})
    committed = {(r["condition"], str(r["idx"])): {k: r[k] for k in VERDICT_KEYS} for r in gate["per_sample"]}
    part_b = []
    for cell in CELLS:
        keys = draw["part_b_idx_condition"][cell]
        if len(keys) != 4:
            raise Stop(2, f"the draw has {len(keys)} pairs in the cell {cell}, not 4")
        for idx, condition in keys:
            idx = str(idx)
            key = (condition, idx)
            if note_index(idx) not in text or key not in rewrite or key not in committed:
                raise Stop(2, f"the pair {idx} ({condition}) is missing from the committed files")
            if committed[key]["consensus"] not in CONSENSUS:
                raise Stop(2, f"the pair {idx} ({condition}) has no committed consensus")
            part_b.append({"n": len(part_b) + 1, "idx": idx, "condition": condition, "cell": cell,
                           "original": text[note_index(idx)], "rewrite": rewrite[key], "committed": committed[key]})
    return part_a, part_b


def check_health(url):
    try:
        r = requests.get(url + "/health", timeout=CONNECT_TIMEOUT)
        health = r.json() if r.status_code == 200 else {}
    except (requests.RequestException, ValueError):
        health = {}
    flags = health.get("judge_models_set") if isinstance(health, dict) else None
    if not (isinstance(health, dict) and health.get("ready") is True and isinstance(flags, dict)
            and flags.get("qwen") is True and flags.get("llama") is True):
        raise Stop(2, "/health does not say ready with both judge routing keys set")
    return {"ready": True, "judge_models_set": {"qwen": True, "llama": True}}


def run_verify(checkout, url):
    """scripts/verify_endpoint.py --all from the checkout, in this process; its lines go to the output."""
    verify = load_module("replay_verify", Path(checkout) / "scripts" / "verify_endpoint.py")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = verify.main([url, "--all"])
    for line in out.getvalue().splitlines():
        say("  verify: " + line)
    levels = [line[:4].strip() for line in out.getvalue().splitlines()]
    if code != 0:
        raise Stop(2, "scripts/verify_endpoint.py --all did not pass")
    return {"exit_code": code, "lines": {k: levels.count(k) for k in ("PASS", "WARN", "FAIL", "INFO")}}


def readable(body):
    """Whether Replay mode can show this /v1/simplify answer: a JSON object with a known consensus."""
    safety = body.get("safety") if isinstance(body, dict) else None
    return isinstance(safety, dict) and safety.get("consensus") in CONSENSUS


def attempt(url, text):
    """One Part A attempt: ("response", the answer as returned) or ("error", what went wrong)."""
    try:
        r = requests.post(url + "/v1/simplify", json={"text": text, "max_tokens": MAX_TOKENS, "safety_mode": "flag"},
                          timeout=(CONNECT_TIMEOUT, TIMEOUT_S))
    except requests.ConnectTimeout:
        return "error", "a connection error"
    except requests.Timeout:
        return "error", f"no answer within {TIMEOUT_S} s"
    except requests.RequestException:
        return "error", "a connection error"
    try:
        body = r.json()
    except ValueError:
        body = None
    if r.status_code != 200:
        detail = body.get("detail") if isinstance(body, dict) else None
        return "error", f"HTTP {r.status_code}" + (f": {detail}" if isinstance(detail, str) and detail else "")
    if not readable(body):
        return "error", "an answer that could not be read"
    return "response", body


def record_part_a(url, cases, rec, write):
    """Each case not yet finished in rec: its attempts, until an answer or three failures; saved after each one."""
    started = {c["n"]: c for c in rec["part_a"]}
    for case in cases:
        n = case["n"]
        entry = started.get(n)
        if entry is None:
            entry = {**case, "attempts": [], "added_content": None}
            rec["part_a"].append(entry)
        attempts = entry["attempts"]
        if any("response" in a for a in attempts) or len(attempts) >= ATTEMPTS:
            continue                                  # recorded, or not recorded after three attempts: never sent again
        if attempts:
            time.sleep(PAUSE_S)                       # resumed after a failed attempt
        for i in range(len(attempts) + 1, ATTEMPTS + 1):
            t = utc_now()
            kind, value = attempt(url, case["input"])
            attempts.append({"time_utc": t, kind: value})
            if rec["session"]["start_utc"] is None:
                rec["session"]["start_utc"] = t
            write()
            if kind == "response":
                say(f"A{n}: recorded at attempt {i} ({value['safety']['consensus']})")
                break
            say(f"A{n}: attempt {i}: {value}" + (f"; repeated in {PAUSE_S} s" if i < ATTEMPTS else ""))
            if i < ATTEMPTS:
                time.sleep(PAUSE_S)
        else:
            say(f"A{n}: not recorded: no usable answer in {ATTEMPTS} attempts")


def probe_judges(gate, key):
    """Each dedicated judge's verdict on the invented probe pair, with the time."""
    probe = {"time_utc": utc_now()}
    for name, model in (("qwen", gate.QWEN_DEDICATED), ("llama", gate.LLAMA_DEDICATED)):
        probe[name] = gate._call_judge(PROBE[0], PROBE[1], model, key, max_tokens=2000)
    return probe


def record_part_b(gate, pairs, rec, write):
    """Each pair not yet recorded in rec: one gate call; saved after each one."""
    recorded_n = {p["n"] for p in rec["part_b"]}
    for pair in pairs:
        if pair["n"] in recorded_n:
            continue
        t = utc_now()
        try:
            result = gate.evaluate_safety(pair["original"], pair["rewrite"], safety_mode="flag")
            recorded = {"time_utc": t, **{k: result[k] for k in VERDICT_KEYS}}
        except Exception as e:
            raise Stop(4, f"B{pair['n']}: the gate stopped ({type(e).__name__})")
        if recorded["consensus"] not in CONSENSUS:
            raise Stop(4, f"B{pair['n']}: the gate returned no known consensus")
        rec["part_b"].append({**pair, "recorded": recorded})
        say(f"B{pair['n']}: recorded ({recorded['consensus']})")
        write()


def write_json(path, data):
    tmp = Path(str(path) + ".tmp")
    tmp.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def record(args):
    if args.settings_stdin:
        read_settings(sys.stdin, args.rehearsal)
    elif not args.rehearsal:
        raise Stop(2, "a recording takes its settings on standard input (--settings-stdin), never from its environment")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.image) or not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise Stop(2, "--image must be sha256:<64 hex> and --commit a full commit hash")
    url = os.environ.get("ENDPOINT_URL", "").strip().rstrip("/")
    key = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not re.match(r"https?://", url) or not key:
        raise Stop(2, "ENDPOINT_URL and NEBIUS_API_KEY must both be set")
    check_endpoint_url(url, args.rehearsal)
    if not args.rehearsal and args.gate_src != IMAGE_SRC:
        raise Stop(2, f"the gate must be the image's own ({IMAGE_SRC}); a stand-in gate needs --rehearsal")
    out = Path(args.out)
    if args.resume:
        rec = load_json(out) if out.exists() else None
        try:
            same = (rec["session"]["image"] == args.image and rec["run"]["commit"] == args.commit
                    and rec["session"]["end_utc"] is None and isinstance(rec["run"]["resumed"], list)
                    and rec["session"]["rehearsal"] is args.rehearsal)
        except (KeyError, TypeError):
            same = False
        if not same:
            raise Stop(2, "--resume goes on only with a stopped session of the same image, commit and kind")
    elif out.exists():
        raise Stop(2, f"{out.name} exists: nothing is recorded twice")
    if not args.rehearsal:
        check_committed(args.checkout)
    image_src = src_files(args.gate_src)
    if not image_src or image_src != src_files(Path(args.checkout) / "src"):
        raise Stop(2, "the image's src/ is not the checkout's src/")
    try:
        part_a, part_b = load_cases(args.checkout)
    except (KeyError, TypeError, ValueError) as e:
        raise Stop(2, f"the committed files are not as expected ({type(e).__name__})")
    try:
        gate = load_gate(args.gate_src)
    except Exception as e:
        raise Stop(2, f"the image's gate cannot be loaded ({type(e).__name__})")
    if gate.JUDGE_MODELS_SET != {"qwen": True, "llama": True}:
        raise Stop(2, "QWEN_JUDGE_MODEL and LLAMA_JUDGE_MODEL must both be set for the gate")
    health = check_health(url)
    try:
        verify = run_verify(args.checkout, url)
    except (OSError, ImportError, SyntaxError) as e:
        raise Stop(2, f"scripts/verify_endpoint.py cannot be run ({type(e).__name__})")
    if args.resume:
        rec["run"]["resumed"].append({"time_utc": utc_now(), "health": health, "verify": verify})
    else:
        rec = {"session": {"start_utc": None, "end_utc": None, "image": args.image, "verify_all_passed": True,
                           "rehearsal": args.rehearsal},
               "part_a": [], "part_b": [],
               "run": {"script": "scripts/record_replay.py", "commit": args.commit,
                       "python": platform.python_version(), "src_matches_checkout": True, "health": health,
                       "verify": verify, "probes": [], "resumed": [], "timeout_s": TIMEOUT_S, "pause_s": PAUSE_S}}
    write = lambda: write_json(out, rec)
    say(f"{'rehearsal ' if args.rehearsal else ''}session {'goes on' if args.resume else 'starts'}: "
        f"Part A, {len(part_a)} cases")
    record_part_a(url, part_a, rec, write)
    if len(rec["part_b"]) < len(part_b):
        probe = probe_judges(gate, key)
        rec["run"]["probes"].append(probe)
        write()
        for name in ("qwen", "llama"):
            if probe[name] not in ("SAFE", "UNSAFE"):
                raise Stop(3, f"the {name} judge did not answer the probe ({probe[name]}); Part B not started")
        say(f"probes answered; Part B, {len(part_b)} pairs")
        record_part_b(gate, part_b, rec, write)
    rec["session"]["end_utc"] = utc_now()
    write()
    say("session ends: both parts recorded")


def add_reads(args):
    rec = load_json(args.recording)
    reads = load_json(args.reads)
    if (rec.get("session") or {}).get("rehearsal") is not False and not args.rehearsal:
        raise Stop(2, "this file is a rehearsal (or not marked either way): its reads need --rehearsal")
    cases = rec.get("part_a") or []
    names = {f"A{c['n']}": c for c in cases}
    if not isinstance(reads, dict) or set(reads) - set(names):
        raise Stop(2, "the reads name cases that are not in the recording")
    for name, case in names.items():
        recorded = any("response" in a for a in case["attempts"])
        read = reads.get(name)
        if case.get("added_content") is not None:
            raise Stop(2, f"{name} already carries a read")
        if not recorded:
            if read is not None:
                raise Stop(2, f"{name} is not recorded, so it has no rewrite to read")
            continue
        if not isinstance(read, dict) or not isinstance(read.get("found"), bool):
            raise Stop(2, f"{name} has no read")
        if read["found"] is False and set(read) == {"found"}:
            case["added_content"] = {"found": False}
        elif (read["found"] is True and set(read) == {"found", "what"} and isinstance(read["what"], str)
              and read["what"].strip() == read["what"] and read["what"] and not read["what"].endswith(".")):
            case["added_content"] = {"found": True, "what": read["what"]}
        else:
            raise Stop(2, f"{name}: a read is found false, or found true with what was found (no final period)")
    before = load_json(args.recording)
    strip = lambda r: [{k: v for k, v in c.items() if k != "added_content"} for c in r["part_a"]]
    if strip(before) != strip(rec) or {k: v for k, v in before.items() if k != "part_a"} != \
            {k: v for k, v in rec.items() if k != "part_a"}:
        raise Stop(2, "something other than added_content would change")
    write_json(args.out, rec)
    found = sum(1 for c in cases if (c.get("added_content") or {}).get("found") is True)
    say(f"reads added: {sum(1 for c in cases if c.get('added_content'))} recorded cases, {found} with added content")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record the replay set once, or add the author's reads.")
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="record both parts in one session")
    rec.add_argument("--checkout", required=True, help="a read-only checkout of the final image's commit")
    rec.add_argument("--gate-src", default=IMAGE_SRC, help=f"the image's src/ (default {IMAGE_SRC})")
    rec.add_argument("--image", required=True, help="the final image's digest, sha256:<64 hex>")
    rec.add_argument("--commit", required=True, help="the checkout's commit")
    rec.add_argument("--out", required=True, help="the recording file to write; it must not exist, unless --resume")
    rec.add_argument("--resume", action="store_true",
                     help="go on with a stopped session in --out: nothing recorded is sent again")
    rec.add_argument("--settings-stdin", action="store_true",
                     help="take ENDPOINT_URL, NEBIUS_API_KEY and the two routing keys from one JSON line on standard "
                          "input; a recording takes them only this way")
    rec.add_argument("--rehearsal", action="store_true",
                     help="allow a stand-in endpoint, gate and checkout, and settings from the environment; the file "
                          "is marked as a rehearsal")
    reads = sub.add_parser("reads", help="add the author's full reads of the recorded Part A rewrites")
    reads.add_argument("--recording", required=True)
    reads.add_argument("--reads", required=True, help='{"A1": {"found": false}, "A2": {"found": true, "what": ...}}')
    reads.add_argument("--out", required=True)
    reads.add_argument("--rehearsal", action="store_true", help="allow reads on a file marked as a rehearsal")
    args = parser.parse_args(argv)
    try:
        (record if args.command == "record" else add_reads)(args)
    except Stop as e:
        say(f"STOP: {e}")
        return e.code
    return 0


if __name__ == "__main__":
    sys.exit(main())
