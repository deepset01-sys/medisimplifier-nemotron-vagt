"""
Offline tests for P2, the grounded explanation (src/explain.py): the request (arm A1's rubric text for text plus the
plain-language line, the texts inserted as they are, Nemotron Nano, temperature 0, a JSON reply), which replies can be
used, the quote check against the original and the rewrite (word for word, and by content words), the check call on
each quote kept, the time limit, and what the reader gets: possible omissions to check, none found by the explainer,
or unavailable, each with its note and reason, and a note when the rewrite was cut. requests.post is replaced with a
fake; nothing leaves the machine.
"""
import ast
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import explain  # noqa: E402
import safety_gate  # noqa: E402

ORIGINAL = ("Discharge diagnosis: Acute MI.\nPast history: type 2 diabetes mellitus,\n  hypertension.\n"
            "Admitted for chest pain. Medications: metformin 1000 mg BID.")
REWRITE = "You had a heart attack. You also have high blood pressure. Take metformin 1000 mg twice a day."
SYNONYM_LINE = '  ("MI" vs "myocardial infarction"). Treat these as PRESENT.\n'
PLAIN_LANGUAGE_LINE = ('- A plain-language description of the diagnosis ("stye" for hordeolum, "head lice" for\n'
                       '  pediculosis). Treat these as PRESENT.\n')


def _a1_rubric():
    """Arm A1's two prompt constants, read from the experiment script without importing it."""
    tree = ast.parse((REPO / "scripts" / "run_vagt_loop_experiment.py").read_text(encoding="utf-8"))
    return {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
            and n.targets[0].id in ("A1_SYSTEM", "A1_USER")}


class _Resp:
    def __init__(self, content=None, finish="stop", status=200):
        self.status_code, self._content, self._finish = status, content, finish

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {"choices": [{"message": {"content": self._content}, "finish_reason": self._finish}]}


def reply(defects, verdict=None, **extra):
    """A rubric reply as JSON text; the verdict follows the defects list unless given."""
    body = {"source_items": [], "defects": defects, "verdict": verdict or ("FAIL" if defects else "PASS"), **extra}
    return _Resp(json.dumps(body))


def d1(quote):
    return {"type": "D1", "source_quote": quote}


NOT_FOUND = '{"present": false, "summary_quote": ""}'


def checked(present, words=""):
    return _Resp(json.dumps({"present": present, "summary_quote": words}))


class _Calls(list):
    """The rubric calls, in order; .checks holds the check calls (they run in parallel, in no fixed order)."""


@pytest.fixture
def fake_post(monkeypatch):
    """Installs a fake requests.post. Rubric calls get the given replies in order (a function is called first, and an
    exception is raised); a check call gets check(diagnosis) — by default a reply that the rewrite does not mention it.
    Every call is recorded; the pause before a second attempt is skipped (unless the clock fixture keeps the time)."""
    def install(*replies, check=None):
        calls, queue = _Calls(), list(replies)
        calls.checks = []

        def post(url, json=None, headers=None, timeout=None):
            call = {"url": url, "json": json, "headers": headers, "timeout": timeout}
            user = json["messages"][-1]["content"]
            if user.startswith("Does SUMMARY mention"):
                calls.checks.append(call)
                diagnosis = user.split("<<<", 1)[1].split(">>>", 1)[0]
                r = check(diagnosis) if check else _Resp(NOT_FOUND)
            else:
                calls.append(call)
                r = queue.pop(0)
                r = r() if callable(r) else r
            if isinstance(r, Exception):
                raise r
            return r
        monkeypatch.setattr(explain.requests, "post", post)
        if explain.time is time:
            monkeypatch.setattr(explain, "time", SimpleNamespace(time=time.time, sleep=lambda s: None))
        return calls
    return install


@pytest.fixture
def clock(monkeypatch):
    """A clock for explain that only moves when told to (and by its own pauses); returns the function that moves it."""
    now = [1000.0]

    def advance(seconds):
        now[0] += seconds
    monkeypatch.setattr(explain, "time", SimpleNamespace(time=lambda: now[0], sleep=advance))
    return advance


def run(original=ORIGINAL, rewrite=REWRITE):
    return explain.explain_flag(original, rewrite, api_key="test-key")


# ── the request ──────────────────────────────────────────────────────────────

def test_the_rubric_is_arm_a1_plus_the_plain_language_line():
    a1 = _a1_rubric()
    assert a1["A1_USER"].count(SYNONYM_LINE) == 1
    assert explain.EXPLAIN_SYSTEM == a1["A1_SYSTEM"]
    assert explain.EXPLAIN_USER == a1["A1_USER"].replace(SYNONYM_LINE, SYNONYM_LINE + PLAIN_LANGUAGE_LINE)


def test_the_request(fake_post):
    calls = fake_post(reply([]))
    explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key")
    (call,) = calls
    body = call["json"]
    assert call["url"] == safety_gate.NEBIUS_API_URL and call["timeout"] == pytest.approx(30, abs=1)   # the time left
    assert call["headers"]["Authorization"] == "Bearer test-key"
    assert body["model"] == safety_gate.NEMOTRON_NANO == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
    assert (body["temperature"], body["max_tokens"]) == (0, 8000)
    assert body["response_format"] == {"type": "json_object"}
    assert body["extra_body"] == {"enable_thinking": False}
    system, user = body["messages"]
    assert system == {"role": "system", "content": explain.EXPLAIN_SYSTEM}
    expected = explain.EXPLAIN_USER.replace("{source}", ORIGINAL).replace("{summary}", REWRITE)
    assert user == {"role": "user", "content": expected}


def test_the_texts_are_inserted_as_they_are(fake_post):
    calls = fake_post(reply([]))
    original, rewrite = "Dx {summary} and {source}; set {x}", "a {source} b"
    explain.explain_flag(original, rewrite, api_key="test-key")
    user = calls[0]["json"]["messages"][1]["content"]
    assert f"SOURCE:\n<<<{original}>>>\n\nSUMMARY:\n<<<{rewrite}>>>" in user


def test_the_key_comes_from_the_environment(fake_post, monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "env-key")
    calls = fake_post(reply([]))
    explain.explain_flag(ORIGINAL, REWRITE)
    assert calls[0]["headers"]["Authorization"] == "Bearer env-key"


def test_no_key_means_no_request(fake_post, monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    calls = fake_post()
    out = explain.explain_flag(ORIGINAL, REWRITE)
    assert calls == [] and (out["status"], out["reason"]) == ("unavailable", "no_api_key")


# ── a usable reply ───────────────────────────────────────────────────────────

def test_a_grounded_quote_is_the_explanation(fake_post):
    fake_post(reply([d1("type 2 diabetes mellitus")]))
    out = run()
    assert (out["status"], out["reason"]) == ("possible_omissions", None)
    assert out["possible_omissions"] == [{"source_quote": "type 2 diabetes mellitus"}]
    assert out["model"] == safety_gate.NEMOTRON_NANO and isinstance(out["latency_ms"], int)


def test_the_quote_is_returned_in_the_originals_wording(fake_post):
    fake_post(reply([d1("TYPE 2 Diabetes   mellitus"), d1("mellitus, hypertension")]))
    out = run()
    assert out["possible_omissions"] == [{"source_quote": "type 2 diabetes mellitus"},
                                        {"source_quote": "mellitus,\n  hypertension"}]


def test_a_quote_the_original_lacks_is_left_out(fake_post):
    fake_post(reply([d1("chronic kidney disease"), d1("type 2 diabetes mellitus")]))
    assert run()["possible_omissions"] == [{"source_quote": "type 2 diabetes mellitus"}]
    fake_post(reply([d1("chronic kidney disease")]))
    out = run()
    assert (out["status"], out["reason"], out["possible_omissions"]) == ("none_found", "no_quote_held_up", [])


def test_quotes_match_whole_words_only(fake_post):
    fake_post(reply([d1("MI")]))   # in "Acute MI.", not in "admitted"
    assert run()["possible_omissions"] == [{"source_quote": "MI"}]
    fake_post(reply([d1("mit")]))  # only inside "Admitted" and "metformin"
    assert run()["reason"] == "no_quote_held_up"


def test_a_quote_the_rewrite_contains_is_left_out(fake_post):
    fake_post(reply([d1("metformin 1000 mg")]))   # word for word in the rewrite: not dropped
    assert run()["reason"] == "no_quote_held_up"


def test_a_quote_whose_content_words_all_stand_in_the_rewrite_is_left_out(fake_post):
    original = "Biopsy: moderate to severe portal inflammation and marked lobular disarray. History of gout."
    rewrite = "The biopsy showed marked lobular disarray and moderate-to-severe portal inflammation."
    fake_post(reply([d1("moderate to severe portal inflammation and marked lobular disarray"), d1("gout")]))
    assert run(original=original, rewrite=rewrite)["possible_omissions"] == [{"source_quote": "gout"}]


def test_one_missing_content_word_keeps_the_quote(fake_post):
    fake_post(reply([d1("type 2 diabetes mellitus")]))
    out = run(rewrite="You have type 2 diabetes, so your blood sugar runs high.")   # no "mellitus"
    assert out["possible_omissions"] == [{"source_quote": "type 2 diabetes mellitus"}]


def test_content_words():
    assert explain._content_words("Type 2 diabetes mellitus, with the CKD of stage 3") == {
        "type", "diabetes", "mellitus", "ckd", "stage"}
    assert explain._content_words("MI") == set()   # no content word: only the word-for-word check applies
    assert explain._all_words_in("Portal Inflammation, marked.", "marked portal inflammation")
    assert not explain._all_words_in("an adrenal mass", "renal mass")   # whole words only
    assert not explain._all_words_in("anything at all", "MI")


def test_each_quote_once_and_at_most_five(fake_post):
    original = "Diagnoses: " + ", ".join(f"condition {c}" for c in "ABCDEFG") + "."
    quotes = ["condition A", "Condition  A"] + [f"condition {c}" for c in "BCDEFG"]
    fake_post(reply([d1(q) for q in quotes]))
    out = run(original=original, rewrite="You are unwell.")
    assert [d["source_quote"] for d in out["possible_omissions"]] == [f"condition {c}" for c in "ABCDE"]


def test_only_diagnoses_count(fake_post):
    fake_post(reply([{"type": "D2", "source_quote": "metformin"}, d1("type 2 diabetes mellitus")]))
    assert run()["possible_omissions"] == [{"source_quote": "type 2 diabetes mellitus"}]


def test_no_defect_means_none_found(fake_post):
    fake_post(reply([]))
    out = run()
    assert (out["status"], out["reason"], out["possible_omissions"]) == ("none_found", "no_omission_found", [])


@pytest.mark.parametrize("content", [
    '```json\n{"defects": [{"type": "D1", "source_quote": "hypertension"}], "verdict": "FAIL"}\n```',
    '<think>checking</think>{"defects": [{"type": "D1", "source_quote": "hypertension"}], "verdict": "FAIL"}',
    'Here it is: {"defects": [{"type": "D1", "source_quote": "hypertension"}], "verdict": "FAIL"} Done.',
])
def test_fences_reasoning_and_surrounding_words_are_read_past(fake_post, content):
    fake_post(_Resp(content))
    assert run()["possible_omissions"] == [{"source_quote": "hypertension"}]


# ── no explanation, and why ──────────────────────────────────────────────────

@pytest.mark.parametrize("resp, reason", [
    (_Resp('{"defects": [], "verdict": "PASS"}', finish="length"), "explainer_reply_cut"),
    (_Resp(None), "explainer_reply_unreadable"),
    (_Resp("   "), "explainer_reply_unreadable"),
    (_Resp('<think>the reasoning stops here'), "explainer_reply_unreadable"),
    (_Resp("not JSON at all"), "explainer_reply_unreadable"),
    (_Resp('[{"type": "D1", "source_quote": "hypertension"}]'), "explainer_reply_unreadable"),
    (_Resp('{"verdict": "FAIL"}'), "explainer_reply_unreadable"),
    (_Resp('{"defects": [{"type": "D1", "source_quote": "hypertension"}]}'), "explainer_reply_unreadable"),
    (_Resp('{"defects": [], "verdict": "FAIL"}'), "explainer_reply_unreadable"),
    (_Resp('{"defects": [{"type": "D1", "source_quote": "hypertension"}], "verdict": "PASS"}'),
     "explainer_reply_unreadable"),
    (_Resp('{"defects": [{"type": "D2", "source_quote": "metformin"}], "verdict": "FAIL"}'),
     "explainer_reply_unreadable"),
])
def test_an_unusable_reply_gives_no_explanation(fake_post, resp, reason):
    fake_post(resp)
    out = run()
    assert (out["status"], out["reason"], out["possible_omissions"]) == ("unavailable", reason, [])


def test_a_failed_request_is_tried_once_more(fake_post):
    calls = fake_post(RuntimeError("connection reset"), reply([d1("hypertension")]))
    out = run()
    assert len(calls) == 2 and out["possible_omissions"] == [{"source_quote": "hypertension"}]


def test_two_failed_requests_give_no_explanation(fake_post):
    calls = fake_post(_Resp(status=500), RuntimeError("timed out"))
    out = run()
    assert len(calls) == 2 and (out["status"], out["reason"]) == ("unavailable", "explainer_unreachable")


def test_a_reply_that_arrives_is_not_asked_again(fake_post):
    calls = fake_post(_Resp("not JSON at all"), reply([d1("hypertension")]))
    assert run()["reason"] == "explainer_reply_unreadable" and len(calls) == 1


# ── the check call on each quote kept ────────────────────────────────────────

def test_the_check_request(fake_post):
    calls = fake_post(reply([d1("type 2 diabetes mellitus")]))
    run()
    (check,) = calls.checks
    body = check["json"]
    assert check["url"] == safety_gate.NEBIUS_API_URL and check["timeout"] == pytest.approx(30, abs=1)
    assert body["model"] == safety_gate.NEMOTRON_NANO
    assert (body["temperature"], body["max_tokens"]) == (0, 2000)
    assert body["response_format"] == {"type": "json_object"} and body["extra_body"] == {"enable_thinking": False}
    (message,) = body["messages"]
    expected = explain.CHECK_USER.replace("{diagnosis}", "type 2 diabetes mellitus").replace("{summary}", REWRITE)
    assert message == {"role": "user", "content": expected}
    assert '("stye" for hordeolum, "head lice" for pediculosis)' in explain.CHECK_USER


def test_a_diagnosis_the_check_finds_in_the_rewrite_is_left_out(fake_post):
    original, rewrite = "Diagnosis: atrial fibrillation. History: gout.", "Your heartbeat is irregular."
    def check(dx):
        return checked(True, "heartbeat is irregular") if dx == "atrial fibrillation" else checked(False)
    fake_post(reply([d1("atrial fibrillation"), d1("gout")]), check=check)
    assert run(original=original, rewrite=rewrite)["possible_omissions"] == [{"source_quote": "gout"}]
    fake_post(reply([d1("atrial fibrillation")]), check=lambda dx: checked(True, "Heartbeat  is IRREGULAR"))
    out = run(original=original, rewrite=rewrite)
    assert (out["status"], out["reason"], out["possible_omissions"]) == ("none_found", "all_found_in_rewrite", [])


@pytest.mark.parametrize("check_reply", [
    checked(True, "an irregular heart rhythm"),   # words the rewrite does not contain
    checked(True, ""),                             # present, but no words quoted
    checked(False, "heartbeat is irregular"),      # not present
    _Resp('{"present": true, "summary_quote": "heartbeat is irregular"}', finish="length"),
    _Resp("not JSON at all"),
    _Resp('{"summary_quote": "heartbeat is irregular"}'),
    _Resp('{"present": "true", "summary_quote": "heartbeat is irregular"}'),   # not the boolean true
])
def test_the_quote_stays_unless_the_check_grounds_it_in_the_rewrite(fake_post, check_reply):
    fake_post(reply([d1("atrial fibrillation")]), check=lambda dx: check_reply)
    out = run(original="Diagnosis: atrial fibrillation.", rewrite="Your heartbeat is irregular.")
    assert out["possible_omissions"] == [{"source_quote": "atrial fibrillation"}]


def test_a_failed_check_is_tried_once_more_then_keeps_the_quote(fake_post):
    calls = fake_post(reply([d1("atrial fibrillation")]), check=lambda dx: RuntimeError("timed out"))
    out = run(original="Diagnosis: atrial fibrillation.", rewrite="Your heartbeat is irregular.")
    assert len(calls.checks) == 2 and out["possible_omissions"] == [{"source_quote": "atrial fibrillation"}]


def test_one_check_per_quote_kept_and_none_without_one(fake_post):
    calls = fake_post(reply([d1("type 2 diabetes mellitus"), d1("hypertension"), d1("chronic kidney disease")]))
    run()   # "chronic kidney disease" is not in the original: no quote, no check
    checked_dx = sorted(c["json"]["messages"][0]["content"].split("<<<")[1].split(">>>")[0] for c in calls.checks)
    assert checked_dx == ["hypertension", "type 2 diabetes mellitus"]
    calls = fake_post(reply([]))
    run()
    assert calls.checks == []


# ── the time limit: at most 30 s for the whole explanation ──────────────────

def test_the_time_limit_is_30_seconds():
    assert explain.TIME_LIMIT_S == 30


def test_each_wait_is_cut_to_the_time_left(fake_post, clock):
    def after_25_s():
        clock(25)
        return reply([d1("type 2 diabetes mellitus")])
    calls = fake_post(after_25_s)
    out = run()
    assert calls[0]["timeout"] == 30 and calls.checks[0]["timeout"] == pytest.approx(5)   # 30 s, then 30 - 25
    assert out["status"] == "possible_omissions" and out["latency_ms"] == 25000


def test_a_reply_after_the_limit_gives_no_explanation(fake_post, clock):
    def after_31_s():
        clock(31)
        return reply([d1("type 2 diabetes mellitus")])
    calls = fake_post(after_31_s)
    out = run()
    assert (out["status"], out["reason"], out["possible_omissions"]) == ("unavailable", "time_limit", [])
    assert calls.checks == []


def test_no_second_attempt_once_the_time_is_up(fake_post, clock):
    def fails_at(seconds):
        def fail():
            clock(seconds)
            raise RuntimeError("timed out")
        return fail
    calls = fake_post(fails_at(31), reply([]))
    assert run()["reason"] == "time_limit" and len(calls) == 1
    calls = fake_post(fails_at(29.5), reply([]))   # the pause before a second attempt uses up the last 0.5 s
    assert run()["reason"] == "time_limit" and len(calls) == 1


def test_checks_not_done_in_time_give_no_explanation(fake_post, clock):
    def check_after_31_s(dx):
        clock(31)
        return checked(False)
    calls = fake_post(reply([d1("type 2 diabetes mellitus")]), check=check_after_31_s)
    out = run()
    assert len(calls.checks) == 1 and (out["status"], out["reason"]) == ("unavailable", "time_limit")


def test_the_limit_can_be_given_per_call(fake_post, clock):
    def after_5_s():
        clock(5)
        return reply([d1("type 2 diabetes mellitus")])
    fake_post(after_5_s)
    out = explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key", time_limit_s=4)
    assert (out["status"], out["reason"]) == ("unavailable", "time_limit")


def test_the_time_limit_result():
    assert explain.time_limit_result(30012) == {
        "status": "unavailable",
        "note": "No explanation, because the explainer did not finish within 30 seconds. This is not a finding; the "
                "gate's verdict stands.",
        "possible_omissions": [], "reason": "time_limit", "rewrite_cut": False, "model": safety_gate.NEMOTRON_NANO,
        "latency_ms": 30012}
    assert explain.time_limit_result(30012, rewrite_cut=True)["rewrite_cut"] is True


# ── what the reader gets: nothing reads as established fact ──────────────────

def test_possible_omissions_read_as_things_to_check(fake_post):
    fake_post(reply([d1("hypertension")]))
    out = run()
    assert (out["status"], out["note"]) == ("possible_omissions", explain.NOTE_POSSIBLE.format(rewrite="the rewrite"))
    assert out["note"].startswith("Possible omissions, to check against the source:")
    assert out["note"].endswith("The gate's verdict stands.") and "may be missing" in out["note"]
    assert "drop" not in json.dumps(out).lower()   # no word of a drop as a fact


def test_none_found_is_the_explainers_and_the_verdict_stands(fake_post):
    fake_post(reply([]))
    out = run()
    assert out["status"] == "none_found"
    assert out["note"] == ("None found by the explainer. It looks only for diagnoses from the source that the rewrite "
                           "leaves out, and it points to none; anything else that may be missing, such as a medication "
                           "or a dose, is outside what it checks. The gate's verdict stands.")


@pytest.mark.parametrize("replies, reason, why", [
    ((RuntimeError("down"), RuntimeError("down")), "explainer_unreachable", "the explainer could not be reached"),
    ((_Resp('{"defects": [], "verdict": "PASS"}', finish="length"),), "explainer_reply_cut",
     "the explainer's own reply was cut off before it finished"),
    ((_Resp("not JSON at all"),), "explainer_reply_unreadable", "the explainer's reply could not be read"),
])
def test_a_failure_does_not_look_like_none_found(fake_post, replies, reason, why):
    fake_post(*replies)
    out = run()
    assert (out["status"], out["reason"]) == ("unavailable", reason)
    assert out["note"] == f"No explanation, because {why}. This is not a finding; the gate's verdict stands."


def test_no_key_and_time_limit_are_unavailable_too(fake_post, clock):
    assert explain.explain_flag(ORIGINAL, REWRITE, api_key="")["status"] == "unavailable"
    assert "did not finish within 30 seconds" in explain.time_limit_result(30000)["note"]


@pytest.mark.parametrize("make_reply", [lambda: reply([d1("hypertension")]), lambda: reply([]),
                                        lambda: _Resp("not JSON at all")])
def test_a_cut_rewrite_is_named_in_the_note(fake_post, make_reply):
    fake_post(make_reply())
    whole = run()
    fake_post(make_reply())
    cut = explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key", rewrite_cut=True)
    assert (whole["rewrite_cut"], cut["rewrite_cut"]) == (False, True)
    assert cut["note"] == whole["note"] + explain.NOTE_REWRITE_CUT.format(Rewrite="The rewrite")
    assert cut["note"].endswith("The rewrite was cut at max_tokens, so something missing from it may simply come after "
                                "the cut.")


def test_the_rewrite_cut_and_the_explainers_reply_cut_have_different_names(fake_post):
    fake_post(_Resp('{"defects": [], "verdict": "PASS"}', finish="length"))
    out = explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key", rewrite_cut=True)
    assert out["reason"] == "explainer_reply_cut" and out["rewrite_cut"] is True
    assert "explainer's own reply was cut off" in out["note"] and "The rewrite was cut at max_tokens" in out["note"]


def test_every_reason_has_one_status():
    assert not set(explain.NONE_FOUND) & set(explain.UNAVAILABLE)
    for reason in explain.NONE_FOUND:
        assert explain._explanation(reason, (), False, 1)["status"] == "none_found"
    for reason in explain.UNAVAILABLE:
        assert explain._explanation(reason, (), False, 1)["status"] == "unavailable"
    assert list(explain._explanation(None, (), False, 1)) == [
        "status", "note", "possible_omissions", "reason", "rewrite_cut", "model", "latency_ms"]


@pytest.mark.parametrize("make_reply, cut", [(lambda: reply([d1("hypertension")]), False), (lambda: reply([]), False),
                                             (lambda: reply([d1("hypertension")]), True), (lambda: reply([]), True)])
def test_a_withheld_rewrite_is_called_the_withheld_rewrite(fake_post, make_reply, cut):
    fake_post(make_reply())
    shown = explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key", rewrite_cut=cut)
    fake_post(make_reply())
    withheld = explain.explain_flag(ORIGINAL, REWRITE, api_key="test-key", rewrite_cut=cut, rewrite_withheld=True)
    expected = (shown["note"].replace("the rewrite", "the withheld rewrite")
                .replace("The rewrite", "The withheld rewrite"))
    assert withheld["note"] == expected and "withheld" in withheld["note"]
    assert "the rewrite" not in withheld["note"].replace("the withheld rewrite", "")
    same = lambda e: {k: v for k, v in e.items() if k not in ("note", "latency_ms")}
    assert same(withheld) == same(shown)


def test_the_none_found_note_says_what_the_explainer_looks_for():
    note = explain._explanation("no_omission_found", (), False, 1)["note"]
    assert "looks only for diagnoses" in note and "outside what it checks" in note


def test_unavailable_notes_name_no_rewrite_unless_it_was_cut():
    for reason in explain.UNAVAILABLE:
        assert (explain._explanation(reason, (), False, 1, True)["note"]
                == explain._explanation(reason, (), False, 1)["note"])
    assert explain.time_limit_result(1, rewrite_cut=True, rewrite_withheld=True)["note"].endswith(
        "The withheld rewrite was cut at max_tokens, so something missing from it may simply come after the cut.")


def test_the_unexpected_failure_result():
    assert explain.error_result(812, rewrite_cut=True, rewrite_withheld=True) == {
        "status": "unavailable",
        "note": "No explanation, because the explainer failed unexpectedly. This is not a finding; the gate's verdict "
                "stands. The withheld rewrite was cut at max_tokens, so something missing from it may simply come "
                "after the cut.",
        "possible_omissions": [], "reason": "explainer_error", "rewrite_cut": True, "model": safety_gate.NEMOTRON_NANO,
        "latency_ms": 812}
