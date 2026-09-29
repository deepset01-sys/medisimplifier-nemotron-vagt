"""
Offline tests for the safety gate's verdict parser (code-audit #31) and its capture log.

No network: every test that reaches _call_judge or evaluate_safety replaces requests.post with a fake.
"""
import json
import logging
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import safety_gate as sg  # noqa: E402

# The seven replies from the #31 analysis: (reply, earlier parser, new parser, deciding rule)
SEVEN = [
    ("UNSAFE", "UNSAFE", "UNSAFE", "single_word"),
    ("UNSAFE — not safe because the diagnosis of pneumonia was dropped.", "SAFE", "ERROR", "ambiguous"),
    ("Verdict: UNSAFE. The simplification would only be SAFE if the dose were kept.", "SAFE", "UNSAFE", "verdict_line"),
    ("SAFE. Nothing critical is missing; no step is unsafe.", "UNSAFE", "ERROR", "ambiguous"),
    ("Step 1: ... Step 4: fluent but incomplete.\nVerdict: UNSAFE", "UNSAFE", "UNSAFE", "all_agree"),
    ("<think>The dose changed, so this is unsafe... wait, is it safe? It", "SAFE", "ERROR", "cut_off_reasoning"),
    ("**UNSAFE**", "UNSAFE", "UNSAFE", "single_word"),
]


@pytest.mark.parametrize("reply,earlier,new,rule", SEVEN)
def test_seven_replies(reply, earlier, new, rule):
    assert sg._legacy_parse(reply) == earlier          # what the deployed parser returns today
    assert sg._parse_verdict(reply, "stop") == (new, rule)


@pytest.mark.parametrize("content", [None, "", "   \n", 42])
def test_null_or_empty_content_is_error(content):
    assert sg._parse_verdict(content, "stop") == ("ERROR", "empty")


def test_length_is_error_even_with_a_verdict_word():
    assert sg._parse_verdict("UNSAFE", "length") == ("ERROR", "truncated")


def test_cut_off_reasoning_is_error():
    assert sg._parse_verdict("<think>looks unsafe to me", "stop") == ("ERROR", "cut_off_reasoning")


def test_verdict_is_read_after_closed_reasoning():
    assert sg._parse_verdict("<think>maybe SAFE, maybe not</think>\nUNSAFE", "stop") == ("UNSAFE", "single_word")
    assert sg._parse_verdict("<think>thinking</think>", "stop") == ("ERROR", "empty")


def test_single_word_variants():
    for reply, want in (("SAFE\n", "SAFE"), ("unsafe.", "UNSAFE"), ("  Safe  ", "SAFE")):
        assert sg._parse_verdict(reply, "stop") == (want, "single_word")


def test_two_verdict_lines_are_ambiguous():
    assert sg._parse_verdict("Verdict: SAFE\nOn reflection:\nVerdict: UNSAFE", "stop") == ("ERROR", "ambiguous")


def test_no_verdict_word():
    assert sg._parse_verdict("I cannot decide.", "stop") == ("ERROR", "no_verdict")


# ── _call_judge with a fake requests.post ──

class _Resp:
    def __init__(self, content, finish_reason="stop", status=200):
        self.status_code = status
        self._body = {"choices": [{"message": {"content": content}, "finish_reason": finish_reason}]}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise sg.requests.HTTPError(str(self.status_code))

    def json(self):
        return self._body


def _fake_post(replies, calls):
    def post(*args, **kwargs):
        calls.append(kwargs.get("json"))
        reply = replies[min(len(calls), len(replies)) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply
    return post


def test_length_is_not_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(sg.requests, "post", _fake_post([_Resp("UNSAFE", "length")], calls))
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "ERROR"
    assert len(calls) == 1


def test_null_content_is_error_without_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(sg.requests, "post", _fake_post([_Resp(None)], calls))
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "ERROR"
    assert len(calls) == 1


def test_request_failures_are_still_retried(monkeypatch):
    calls = []
    monkeypatch.setattr(sg.time, "sleep", lambda s: None)
    monkeypatch.setattr(sg.requests, "post",
                        _fake_post([sg.requests.ConnectionError("down"), _Resp("UNSAFE")], calls))
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "UNSAFE"
    assert len(calls) == 2


# ── capture log ──

def test_capture_record_when_enabled(monkeypatch, caplog):
    reply = "UNSAFE — not safe because " + "x" * 100
    monkeypatch.setattr(sg.requests, "post", _fake_post([_Resp(reply)], []))
    caplog.set_level(logging.INFO, logger="safety_gate")
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "ERROR"
    rec = json.loads([r for r in caplog.records if r.name == "safety_gate"][-1].getMessage())
    assert rec == {"model": "judge-model", "finish_reason": "stop", "content_len": len(reply),
                   "head80": reply[:80], "verdict": "ERROR", "rule": "ambiguous", "legacy_verdict": "SAFE"}


def test_capture_records_a_failed_request(monkeypatch, caplog):
    monkeypatch.setattr(sg.time, "sleep", lambda s: None)
    monkeypatch.setattr(sg.requests, "post", _fake_post([sg.requests.Timeout("slow")], []))
    caplog.set_level(logging.INFO, logger="safety_gate")
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "ERROR"
    rec = json.loads([r for r in caplog.records if r.name == "safety_gate"][-1].getMessage())
    assert (rec["rule"], rec["content_len"], rec["head80"]) == ("request_failed", None, None)


def test_capture_silent_when_not_enabled(monkeypatch, caplog):
    monkeypatch.setattr(sg.requests, "post", _fake_post([_Resp("UNSAFE")], []))
    caplog.set_level(logging.WARNING, logger="safety_gate")
    assert sg._call_judge("orig", "simp", "judge-model", "key") == "UNSAFE"
    assert not [r for r in caplog.records if r.name == "safety_gate"]


def test_api_response_unchanged(monkeypatch, caplog):
    """The capture stays internal: evaluate_safety returns the same keys, and no reply text."""
    caplog.set_level(logging.INFO, logger="safety_gate")
    monkeypatch.setenv("NEBIUS_API_KEY", "dummy")
    monkeypatch.setattr(sg.requests, "post", lambda *a, **k: _Resp("UNSAFE — flagged because of the dose"))
    out = sg.evaluate_safety("orig", "simp")
    assert set(out) == {"llama_verdict", "qwen_verdict", "nemotron_verdict", "blocked", "consensus", "warning"}
    assert "flagged because" not in json.dumps(out)
