"""
scripts/record_replay.py on an invented checkout: every text here is invented, never one of the 28 replay cases.
requests is replaced with a stand-in endpoint and the gate with a stand-in module, so nothing leaves the machine and
no wait is real. Covers: a call repeated at the second and at the third attempt, a case not recorded, an ERROR verdict
in Part A and in Part B, a stop at a failed probe, the stops before any case, going on after a stop without sending
anything again, the author's reads, and the guards: the deployed endpoint and the image's own gate, the committed
files as pinned, a rehearsal's mark, and the settings taken on standard input only.
"""
import io
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import record_replay as rr  # noqa: E402

IMAGE = "sha256:" + "0" * 64
COMMIT = "0" * 40
URL = "https://endpoint.invented"
KEY = "invented-key-for-the-tests"
QWEN_KEY, LLAMA_KEY = "invented/qwen-routing-key", "invented/llama-routing-key"
HEALTH = {"vllm": True, "token_factory": True, "ready": True, "judge_models_set": {"qwen": True, "llama": True},
          "audit_panel": True, "pool_loaded": True, "pool_error": None}
STANDIN_GATE = '''"""Stand-in gate: invented verdicts from markers in the rewrite; no network."""
import os
QWEN_DEDICATED, LLAMA_DEDICATED = "standin/qwen", "standin/llama"
JUDGE_MODELS_SET = {"qwen": True, "llama": True}
SEEN = {name: os.environ.get(name) for name in ("NEBIUS_API_KEY", "QWEN_JUDGE_MODEL", "LLAMA_JUDGE_MODEL")}
CALLS = []
def _call_judge(original, simplified, model, api_key, max_tokens=2000, max_retries=3):
    return "ERROR" if os.environ.get("STANDIN_PROBE_FAIL") and os.environ["STANDIN_PROBE_FAIL"] in model else "SAFE"
def evaluate_safety(original, simplified, safety_mode="flag"):
    CALLS.append(simplified)
    qwen = "ERROR" if "[qwen ERROR]" in simplified else "UNSAFE" if "[qwen UNSAFE]" in simplified else "SAFE"
    nemotron = "UNSAFE" if "[nemotron UNSAFE]" in simplified else "SAFE"
    consensus = ("ERROR" if qwen == "ERROR" else "UNSAFE" if qwen == "UNSAFE" else
                 "DISAGREE" if nemotron == "UNSAFE" else "SAFE")
    return {"llama_verdict": "SAFE", "qwen_verdict": qwen, "nemotron_verdict": nemotron, "blocked": False,
            "consensus": consensus, "warning": None}
'''
B_MARKS = ["[qwen UNSAFE]", "[nemotron UNSAFE]", "[qwen ERROR]", "[qwen UNSAFE]", "", "", "", "", "[nemotron UNSAFE]",
           "[nemotron UNSAFE]", "[qwen UNSAFE]", "[nemotron UNSAFE]", "", "", "", ""]


def answer(consensus, nemotron="SAFE", qwen="SAFE"):
    return {"simplified_text": "An invented rewrite.", "truncated": False, "blocked": False,
            "safety": {"llama_verdict": "SAFE", "qwen_verdict": qwen, "nemotron_verdict": nemotron, "blocked": False,
                       "consensus": consensus, "warning": None},
            "explanation": None, "latency_ms": {"total_ms": 21000}}


# What the stand-in endpoint does on each attempt, per Part A case (A1 to A12).
SCRIPTS = {
    1: [(200, answer("SAFE"))],
    2: [(503, {"detail": "vLLM generation failed: invented"}), (200, answer("UNSAFE", qwen="UNSAFE"))],
    3: [rr.requests.ReadTimeout(), (400, {"detail": "invented bad request"}), (200, answer("DISAGREE", "UNSAFE"))],
    4: [(200, answer("ERROR", qwen="ERROR"))],
    5: [(200, "not json"), (500, {"detail": "Internal Server Error"}), (422, {"detail": [{"loc": ["body"]}]})],
    6: [rr.requests.ConnectionError(), (200, answer("SAFE"))],
}


def case_no(text):
    """The Part A case an invented input belongs to: "INVENTED INPUT A12: ..." -> 12."""
    return int(text.split(":")[0].rsplit("A", 1)[1])


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body
        self.text = body if isinstance(body, str) else json.dumps(body)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise rr.requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        if isinstance(self._body, str):
            raise ValueError("not JSON")
        return self._body


def write_checkout(root):
    """An invented checkout: the six committed files the script reads, the stand-in gate in src/, verify_endpoint.py."""
    inputs = [{"index": n, "input": f"INVENTED INPUT A{n}: an invented note, not a replay case."} for n in range(1, 13)]
    draw = {"part_a_index": {"short": [1, 2, 3, 4], "middle": [5, 6, 7, 8], "long": [9, 10, 11, 12]},
            "part_b_idx_condition": {}}
    drops, controls, gate = [], [], []
    for b, (cell, condition) in enumerate([(c, "corrupted" if c.startswith("drop") else "clean")
                                           for c in rr.CELLS for _ in range(4)], start=1):
        idx = f"hf{900 + b}"
        draw["part_b_idx_condition"].setdefault(cell, []).append([idx, condition])
        inputs.append({"index": 900 + b, "input": f"INVENTED ORIGINAL B{b}: an invented note."})
        rewrite = f"INVENTED REWRITE B{b} {B_MARKS[b - 1]}".strip()
        if condition == "corrupted":
            drops.append({"idx": idx, "edited_summary": rewrite, "origin": "hf_test"})
        else:
            controls.append({"idx": idx, "control_type": "primary_paired", "clean_ref": rewrite})
        flagged = cell in ("drop caught", "control falsely flagged")
        gate.append({"idx": idx, "condition": condition, "llama_verdict": "SAFE", "qwen_verdict": "SAFE",
                     "nemotron_verdict": "UNSAFE" if flagged else "SAFE",
                     "consensus": "DISAGREE" if flagged else "SAFE"})
    files = {"draw": draw, "inputs": inputs, "drops": {"items": drops}, "controls": {"items": controls},
             "gate": {"per_sample": gate}, "cut": {"stopped_at_cap": {"count": 2, "indices": [6, 10]}}}
    for key, data in files.items():
        path = root / rr.FILES[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "safety_gate.py").write_text(STANDIN_GATE, encoding="utf-8")
    (root / "scripts").mkdir()
    shutil.copy(REPO / "scripts" / "verify_endpoint.py", root / "scripts" / "verify_endpoint.py")


@pytest.fixture
def run(tmp_path, monkeypatch, capsys):
    """Record against the stand-ins; return (exit code, output, the file or None, posted bodies, pauses, the gate).
    A real run by default: the invented checkout's files are pinned as the committed ones, its image copy stands for
    /app/src, and the settings come on standard input, none in the environment unless a test puts them there. It can
    run again in the same test, on the same checkout and file (for --resume)."""
    checkout, gate_src = tmp_path / "checkout", tmp_path / "image_src"
    out = tmp_path / "out" / "replay_recording.json"
    real_load_gate = rr.load_gate                       # each run loads its own copy of the stand-in gate

    def _run(health=HEALTH, probe_fail=None, gate_src_change=None, resume=False, image=IMAGE, url=URL,
             rehearsal=False, other_gate=False, change_file=None, stdin=True, line=None, in_env=()):
        if not checkout.exists():
            write_checkout(checkout)
            shutil.copytree(checkout / "src", gate_src)
            monkeypatch.setattr(rr, "COMMITTED", {rel: rr.lf_sha256(checkout / rel) for rel in rr.COMMITTED})
            monkeypatch.setattr(rr, "SRC_TREE", rr.src_tree(rr.src_files(checkout / "src")))
            monkeypatch.setattr(rr, "IMAGE_SRC", str(gate_src))
        if gate_src_change:
            (gate_src / "safety_gate.py").write_text(STANDIN_GATE + gate_src_change, encoding="utf-8")
        if change_file:
            path = checkout / change_file
            path.write_bytes(path.read_bytes() + b" ")
        used_gate = gate_src
        if other_gate:
            used_gate = tmp_path / "another_src"
            if not used_gate.exists():
                shutil.copytree(gate_src, used_gate)
        settings = {"ENDPOINT_URL": url, "NEBIUS_API_KEY": KEY, "QWEN_JUDGE_MODEL": QWEN_KEY,
                    "LLAMA_JUDGE_MODEL": LLAMA_KEY}
        for name in rr.SETTINGS:              # absent at the start of each run, and again after the test
            monkeypatch.setenv(name, "-")
            monkeypatch.delenv(name)
        for name in in_env:
            monkeypatch.setenv(name, settings[name])
        monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(settings) + "\n" if line is None else line))
        if probe_fail:
            monkeypatch.setenv("STANDIN_PROBE_FAIL", probe_fail)
        else:
            monkeypatch.delenv("STANDIN_PROBE_FAIL", raising=False)
        posted, pauses, tries, loaded = [], [], {}, {}

        def get(url, timeout):
            return _Resp(200, health)

        def post(url, json, timeout):
            posted.append(json)
            if "max_tokens" not in json:      # verify_endpoint.py's own invented example
                return _Resp(200, answer("SAFE"))
            n = case_no(json["text"])
            steps = SCRIPTS.get(n, [(200, answer("SAFE"))])
            step = steps[min(tries.get(n, 0), len(steps) - 1)]
            tries[n] = tries.get(n, 0) + 1
            if isinstance(step, Exception):
                raise step
            return _Resp(*step)

        monkeypatch.setattr(rr.requests, "get", get)
        monkeypatch.setattr(rr.requests, "post", post)
        monkeypatch.setattr(rr.time, "sleep", pauses.append)
        monkeypatch.setattr(rr, "load_gate", lambda src: loaded.setdefault("gate", real_load_gate(src)))
        out.parent.mkdir(exist_ok=True)
        code = rr.main(["record", "--checkout", str(checkout), "--gate-src", str(used_gate), "--image", image,
                        "--commit", COMMIT, "--out", str(out)] + (["--resume"] if resume else [])
                       + (["--rehearsal"] if rehearsal else []) + (["--settings-stdin"] if stdin else []))
        rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
        replay_posts = [p for p in posted if "max_tokens" in p]
        return code, capsys.readouterr().out, rec, replay_posts, pauses, loaded.get("gate")
    _run.out = out
    return _run


def probes(rec):
    return [{k: v for k, v in p.items() if k != "time_utc"} for p in rec["run"]["probes"]]


def test_records_both_parts_with_every_state(run):
    code, out, rec, posts, pauses, gate = run()
    assert code == 0 and "session ends: both parts recorded" in out
    a = {c["n"]: c for c in rec["part_a"]}
    kinds = lambda n: [("response" if "response" in x else "error") for x in a[n]["attempts"]]
    assert kinds(1) == ["response"]
    assert kinds(2) == ["error", "response"]
    assert a[2]["attempts"][0]["error"] == "HTTP 503: vLLM generation failed: invented"
    assert kinds(3) == ["error", "error", "response"]
    assert [x.get("error") for x in a[3]["attempts"][:2]] == [
        "no answer within 600 s", "HTTP 400: invented bad request"]
    assert kinds(5) == ["error"] * 3 and [x["error"] for x in a[5]["attempts"]] == [
        "an answer that could not be read", "HTTP 500: Internal Server Error", "HTTP 422"]
    assert kinds(4) == ["response"] and a[4]["attempts"][0]["response"]["safety"]["consensus"] == "ERROR"
    assert kinds(6) == ["error", "response"] and a[6]["attempts"][0]["error"] == "a connection error"
    assert pauses == [rr.PAUSE_S] * 6                        # A2 once, A3 twice, A5 twice, A6 once; never after a third
    assert len(posts) == 1 + 2 + 3 + 1 + 3 + 2 + 6
    assert all(p == {"text": a[case_no(p["text"])]["input"], "max_tokens": 1024, "safety_mode": "flag"} for p in posts)
    assert [c["cut_at_512"] for c in rec["part_a"]] == [n in (6, 10) for n in range(1, 13)]
    assert all(c["added_content"] is None for c in rec["part_a"])
    b = {p["n"]: p for p in rec["part_b"]}
    assert len(gate.CALLS) == 16 and len(b) == 16                             # one gate call per pair, none repeated
    assert b[3]["recorded"]["consensus"] == "ERROR" and b[3]["recorded"]["qwen_verdict"] == "ERROR"
    assert [b[n]["cell"] for n in (1, 5, 9, 13)] == list(rr.CELLS)
    assert rec["session"]["image"] == IMAGE and rec["session"]["verify_all_passed"] is True
    assert rec["session"]["start_utc"] == rec["part_a"][0]["attempts"][0]["time_utc"] <= rec["session"]["end_utc"]
    assert probes(rec) == [{"qwen": "SAFE", "llama": "SAFE"}] and rec["run"]["verify"]["exit_code"] == 0
    assert rec["run"]["resumed"] == [] and rec["session"]["rehearsal"] is False
    text = json.dumps(rec)
    assert not any(s in text or s in out for s in (URL, KEY, QWEN_KEY, LLAMA_KEY))   # no setting written or printed
    assert "INVENTED INPUT" not in out                                        # no text is printed


def test_stops_at_a_failed_probe(run):
    code, out, rec, posts, pauses, gate = run(probe_fail="qwen")
    assert code == 3 and "STOP: the qwen judge did not answer the probe (ERROR); Part B not started" in out
    assert len(rec["part_a"]) == 12 and rec["part_b"] == [] and gate.CALLS == []
    assert probes(rec) == [{"qwen": "ERROR", "llama": "SAFE"}] and rec["session"]["end_utc"] is None


def test_goes_on_after_a_failed_probe_without_sending_part_a_again(run):
    first = run(probe_fail="qwen")[2]
    code, out, rec, posts, pauses, gate = run(resume=True)
    assert code == 0 and "session goes on" in out and posts == [] and pauses == []
    assert rec["part_a"] == first["part_a"] and len(rec["part_b"]) == 16 and len(gate.CALLS) == 16
    assert probes(rec) == [{"qwen": "ERROR", "llama": "SAFE"}, {"qwen": "SAFE", "llama": "SAFE"}]
    assert len(rec["run"]["resumed"]) == 1 and rec["session"]["start_utc"] == first["session"]["start_utc"]
    assert rec["session"]["end_utc"] is not None


def test_goes_on_with_an_unfinished_case_and_its_remaining_attempts_only(run):
    full = run()[2]
    stopped = dict(full, part_b=[], session=dict(full["session"], end_utc=None), run=dict(full["run"], probes=[]))
    stopped["part_a"] = full["part_a"][:4] + [dict(full["part_a"][4], attempts=full["part_a"][4]["attempts"][:1])]
    run.out.write_text(json.dumps(stopped), encoding="utf-8")            # a stop after A5's first failed attempt
    code, out, rec, posts, pauses, gate = run(resume=True)
    assert code == 0 and [case_no(p["text"]) for p in posts] == [5, 5, 6, 6, 7, 8, 9, 10, 11, 12]
    assert pauses == [rr.PAUSE_S] * 3                                     # before A5's second and third, A6 once
    a = {c["n"]: c for c in rec["part_a"]}
    assert rec["part_a"][:4] == full["part_a"][:4] and len(a[5]["attempts"]) == 3
    assert all("error" in x for x in a[5]["attempts"]) and len(rec["part_b"]) == 16


def test_goes_on_in_part_b_without_scoring_a_recorded_pair_again(run):
    full = run()[2]
    stopped = dict(full, part_b=full["part_b"][:8], session=dict(full["session"], end_utc=None))
    run.out.write_text(json.dumps(stopped), encoding="utf-8")            # a stop after B8
    code, out, rec, posts, pauses, gate = run(resume=True)
    assert code == 0 and posts == [] and rec["part_b"][:8] == full["part_b"][:8]
    assert gate.CALLS == [p["rewrite"] for p in full["part_b"][8:]] and len(rec["part_b"]) == 16


@pytest.mark.parametrize("change", [
    lambda r: r["session"].update(end_utc="2099-01-01T10:28:00Z"),         # a session that ended
    lambda r: r["session"].update(image="sha256:" + "1" * 64),             # another image
    lambda r: r["session"].update(rehearsal=True),                          # a rehearsal resumed as a recording
])
def test_resume_refused(run, change):
    stopped = run(probe_fail="qwen")[2]
    change(stopped)
    run.out.write_text(json.dumps(stopped), encoding="utf-8")
    code, out, rec, posts, pauses, gate = run(resume=True)
    assert code == 2 and "--resume goes on only" in out and posts == [] and gate is None


@pytest.mark.parametrize("health, gate_src_change", [
    (dict(HEALTH, ready=False, vllm=False), None),
    (dict(HEALTH, judge_models_set={"qwen": True, "llama": False}), None),
    (HEALTH, "# a change in the image's copy\n"),
])
def test_stops_before_any_case(run, health, gate_src_change):
    code, out, rec, posts, pauses, gate = run(health=health, gate_src_change=gate_src_change)
    assert code == 2 and "STOP:" in out and rec is None and posts == []


def test_nothing_is_recorded_twice(run, tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "replay_recording.json").write_text("{}", encoding="utf-8")
    code, out, rec, posts, pauses, gate = run()
    assert code == 2 and "nothing is recorded twice" in out and rec == {} and posts == []


def reads_for(rec):
    reads = {f"A{c['n']}": {"found": False} for c in rec["part_a"] if any("response" in a for a in c["attempts"])}
    reads["A2"] = {"found": True, "what": "an invented statement about follow-up care"}
    return reads


def add_reads(tmp_path, rec, reads, rehearsal=False):
    rec_path, reads_path, out = tmp_path / "rec.json", tmp_path / "reads.json", tmp_path / "with_reads.json"
    rec_path.write_text(json.dumps(rec), encoding="utf-8")
    reads_path.write_text(json.dumps(reads), encoding="utf-8")
    out.unlink(missing_ok=True)
    code = rr.main(["reads", "--recording", str(rec_path), "--reads", str(reads_path), "--out", str(out)]
                   + (["--rehearsal"] if rehearsal else []))
    return code, (json.loads(out.read_text(encoding="utf-8")) if out.exists() else None)


def test_reads_change_only_added_content(run, tmp_path):
    rec = run()[2]
    code, after = add_reads(tmp_path, rec, reads_for(rec))
    assert code == 0
    assert after["part_a"][1]["added_content"] == {"found": True, "what": "an invented statement about follow-up care"}
    assert after["part_a"][4]["added_content"] is None                        # A5: not recorded, no rewrite to read
    strip = lambda r: [{k: v for k, v in c.items() if k != "added_content"} for c in r["part_a"]]
    assert strip(after) == strip(rec) and after["part_b"] == rec["part_b"] and after["session"] == rec["session"]


@pytest.mark.parametrize("change", [
    lambda r: r.pop("A1"),                                                    # a recorded case without its read
    lambda r: r.update(A5={"found": False}),                                  # a read for a case not recorded
    lambda r: r.update(A2={"found": True, "what": "ends with a period."}),
    lambda r: r.update(A2={"found": True}),
    lambda r: r.update(A13={"found": False}),
])
def test_reads_refused(run, tmp_path, change):
    rec = run()[2]
    reads = reads_for(rec)
    change(reads)
    code, after = add_reads(tmp_path, rec, reads)
    assert code == 2 and after is None


# Guard 1: a recording talks to the deployed endpoint (https, not this machine) and uses the image's own gate.
@pytest.mark.parametrize("url", ["http://endpoint.invented", "https://127.0.0.1:8443", "https://localhost",
                                 "https://[::1]:8443", "https://0.0.0.0"])
def test_guard_1_refuses_a_stand_in_endpoint(run, url):
    code, out, rec, posts, pauses, gate = run(url=url)
    assert code == 2 and "ENDPOINT_URL must be the endpoint's https URL" in out and rec is None and posts == []


def test_guard_1_refuses_a_gate_other_than_the_images_own(run):
    code, out, rec, posts, pauses, gate = run(other_gate=True)
    assert code == 2 and "the gate must be the image's own" in out and rec is None and posts == [] and gate is None


def test_guard_1_lets_a_rehearsal_use_stand_ins_and_marks_it(run):
    code, out, rec, posts, pauses, gate = run(url="http://127.0.0.1:8766", other_gate=True, rehearsal=True)
    assert code == 0 and "rehearsal session starts" in out and rec["session"]["rehearsal"] is True


# Guard 2: every committed file the script reads, and the checkout's src/, as pinned when it was signed.
@pytest.mark.parametrize("rel", list(rr.COMMITTED) + ["src/safety_gate.py"])
def test_guard_2_refuses_a_checkout_file_that_is_not_the_committed_one(run, rel):
    code, out, rec, posts, pauses, gate = run(change_file=rel)
    assert code == 2 and rec is None and posts == [] and gate is None
    assert (f"{rel} is not the committed file" in out if rel in rr.COMMITTED else "the checkout's src/ is not" in out)


def test_guard_2_pins_are_the_committed_files():
    for rel, expected in rr.COMMITTED.items():
        assert rr.lf_sha256(REPO / rel) == expected, rel
    assert rr.src_tree(rr.src_files(REPO / "src")) == rr.SRC_TREE
    sources = json.loads((REPO / rr.FILES["draw"]).read_text(encoding="utf-8"))["sources"]
    assert all(rr.COMMITTED[rel] == digest.removeprefix("sha256:") for rel, digest in sources.items())


def test_guard_2_does_not_bind_a_rehearsal(run):
    code, out, rec, posts, pauses, gate = run(change_file=rr.FILES["cut"], rehearsal=True)
    assert code == 0 and rec["session"]["rehearsal"] is True


# Guard 3: a rehearsal's file is marked, and its reads need --rehearsal, so it cannot become a recording by mistake.
def test_guard_3_reads_refuse_a_rehearsal_file_without_rehearsal(run, tmp_path):
    rec = run(rehearsal=True)[2]
    assert add_reads(tmp_path, rec, reads_for(rec)) == (2, None)
    code, after = add_reads(tmp_path, rec, reads_for(rec), rehearsal=True)
    assert code == 0 and after["session"]["rehearsal"] is True


def test_guard_3_a_recording_resumed_as_a_rehearsal_is_refused(run):
    run(probe_fail="qwen")
    code, out, rec, posts, pauses, gate = run(resume=True, rehearsal=True)
    assert code == 2 and "--resume goes on only" in out and posts == []


# The settings: a recording takes them on standard input only, so Docker holds none of them.
def test_the_settings_reach_the_gate_from_standard_input(run):
    code, out, rec, posts, pauses, gate = run()
    assert code == 0
    assert gate.SEEN == {"NEBIUS_API_KEY": KEY, "QWEN_JUDGE_MODEL": QWEN_KEY, "LLAMA_JUDGE_MODEL": LLAMA_KEY}


def test_a_recording_takes_its_settings_only_on_standard_input(run):
    code, out, rec, posts, pauses, gate = run(stdin=False, in_env=rr.SETTINGS)
    assert code == 2 and "a recording takes its settings on standard input" in out
    assert rec is None and posts == [] and gate is None


@pytest.mark.parametrize("name", rr.SETTINGS)
def test_a_recording_stops_if_a_setting_is_already_in_its_environment(run, name):
    code, out, rec, posts, pauses, gate = run(in_env=[name])
    assert code == 2 and f"{name} already in the environment" in out and rec is None and posts == [] and gate is None


@pytest.mark.parametrize("line", [
    "",                                                                       # nothing on standard input
    "not json\n",
    json.dumps({"ENDPOINT_URL": URL, "QWEN_JUDGE_MODEL": QWEN_KEY, "LLAMA_JUDGE_MODEL": LLAMA_KEY}) + "\n",   # no key
    json.dumps({"ENDPOINT_URL": URL, "NEBIUS_API_KEY": KEY, "QWEN_JUDGE_MODEL": QWEN_KEY,
                "LLAMA_JUDGE_MODEL": LLAMA_KEY, "ANOTHER": "x"}) + "\n",                                    # one more
    json.dumps({"ENDPOINT_URL": URL, "NEBIUS_API_KEY": " ", "QWEN_JUDGE_MODEL": QWEN_KEY,
                "LLAMA_JUDGE_MODEL": LLAMA_KEY}) + "\n",                                                    # one empty
])
def test_the_settings_line_holds_exactly_the_four_each_set(run, line):
    code, out, rec, posts, pauses, gate = run(line=line)
    assert code == 2 and "standard input must hold one line" in out and rec is None and posts == [] and gate is None
    assert KEY not in out


def test_a_rehearsal_may_take_its_settings_from_the_environment(run):
    code, out, rec, posts, pauses, gate = run(url="http://127.0.0.1:8766", rehearsal=True, stdin=False,
                                              in_env=rr.SETTINGS)
    assert code == 0 and rec["session"]["rehearsal"] is True and gate.SEEN["NEBIUS_API_KEY"] == KEY
