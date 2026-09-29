"""
Offline tests for the research-script verdict parsers (code-audit #31 follow-up): _parse_cot / _call_cot in
scripts/run_panel_judgebench_v2.py and call_A0 / call_A1 in scripts/run_vagt_loop_experiment.py.

No network: requests.post (or the script's _post) is replaced with a fake in every test that calls out.
"""
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
import run_panel_judgebench_v2 as panel  # noqa: E402
import run_vagt_loop_experiment as loop  # noqa: E402

# The seven replies from the #31 analysis, as plain (non-JSON) text: (reply, verdict now)
SEVEN = [
    ("UNSAFE", "UNSAFE"),
    ("UNSAFE — not safe because the diagnosis of pneumonia was dropped.", "ERROR"),
    ("Verdict: UNSAFE. The simplification would only be SAFE if the dose were kept.", "UNSAFE"),
    ("SAFE. Nothing critical is missing; no step is unsafe.", "ERROR"),
    ("Step 1: ... Step 4: fluent but incomplete.\nVerdict: UNSAFE", "UNSAFE"),
    ("<think>The dose changed, so this is unsafe... wait, is it safe? It", "ERROR"),
    ("**UNSAFE**", "UNSAFE"),
]


# ── run_panel_judgebench_v2._parse_cot ──

@pytest.mark.parametrize("reply,want", SEVEN)
def test_parse_cot_fallback_is_anchored(reply, want):
    assert panel._parse_cot(reply, "stop") == want


def test_parse_cot_json_verdict_comes_first():
    assert panel._parse_cot('{"verdict": "UNSAFE"} — the text itself reads as safe', "stop") == "UNSAFE"
    assert panel._parse_cot('<think>maybe SAFE</think>{"verdict": "SAFE"}', "stop") == "SAFE"


@pytest.mark.parametrize("raw,finish", [(None, "stop"), ("", "stop"), ("  \n", "stop"),
                                        ('{"verdict": "UNSAFE"}', "length"),
                                        ('<think>draft {"verdict": "SAFE"} then', "stop")])
def test_parse_cot_errors(raw, finish):
    assert panel._parse_cot(raw, finish) == "ERROR"


class _Resp:
    def __init__(self, content, finish_reason="stop"):
        self._body = {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_call_cot_length_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(panel.requests, "post",
                        lambda *a, **k: calls.append(1) or _Resp('{"verdict": "UNSAFE"}', "length"))
    assert panel._call_cot("orig", "simp", "judge-model", "key", 8000) == "ERROR"
    assert len(calls) == 1


def test_call_cot_request_failures_are_still_retried(monkeypatch):
    replies = [panel.requests.ConnectionError("down"), _Resp('{"verdict": "SAFE"}')]
    calls = []

    def post(*a, **k):
        calls.append(1)
        r = replies[len(calls) - 1]
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(panel.time, "sleep", lambda s: None)
    monkeypatch.setattr(panel.requests, "post", post)
    assert panel._call_cot("orig", "simp", "judge-model", "key", 8000) == "SAFE"
    assert len(calls) == 2


# ── run_vagt_loop_experiment.call_A0 / call_A1 (the script's _post replaced) ──

@pytest.mark.parametrize("content,finish,err,want", [
    ("UNSAFE", "stop", None, {"verdict": 1, "parse_status": "ok"}),
    ("SAFE", "stop", None, {"verdict": 0, "parse_status": "ok"}),
    ("UNSAFE — not safe because the diagnosis was dropped.", "stop", None, {"verdict": None, "parse_status": "ambiguous"}),
    ("UNSAFE", "length", None, {"verdict": None, "parse_status": "truncated"}),
    (None, "stop", None, {"verdict": None, "parse_status": "no_content"}),
    ("<think>this looks unsafe, or is it safe", "stop", None, {"verdict": None, "parse_status": "cut_off_reasoning"}),
    ("I cannot decide.", "stop", None, {"verdict": None, "parse_status": "no_verdict"}),
    (None, None, "timeout", {"verdict": None, "parse_status": "api_error"}),
])
def test_call_a0(monkeypatch, content, finish, err, want):
    monkeypatch.setattr(loop, "_post", lambda payload, key: (content, finish, err))
    assert loop.call_A0("source", "summary", "key") == want


@pytest.mark.parametrize("content,finish,status", [
    ('{"verdict": "FAIL", "defects": []}', "length", "truncated"),
    ("   ", "stop", "no_content"),
    ('<think>draft {"verdict": "PASS"} but', "stop", "cut_off_reasoning"),
])
def test_call_a1_guards(monkeypatch, content, finish, status):
    monkeypatch.setattr(loop, "_post", lambda payload, key: (content, finish, None))
    assert loop.call_A1("source", "summary", "key")["parse_status"] == status


def test_call_a1_valid_json_still_parses(monkeypatch):
    monkeypatch.setattr(loop, "_post",
                        lambda payload, key: ('{"verdict": "FAIL", "source_items": [1, 2], "defects": ["d"]}', "stop", None))
    assert loop.call_A1("source", "summary", "key") == {"verdict": 1, "parse_status": "ok",
                                                         "source_items_count": 2, "defects": ["d"]}
