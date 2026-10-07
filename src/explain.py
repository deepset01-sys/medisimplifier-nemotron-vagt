"""
explain.py — P2: the explanation of a gate flag — possible omissions to check (advisory only).

When the gate flags a rewrite (consensus UNSAFE or DISAGREE), the endpoint asks Nemotron Nano on Token Factory
serverless, already one of the gate's judges, one scoped question: which diagnoses named in the original are missing
from the rewrite? The rubric is arm A1 of scripts/run_vagt_loop_experiment.py, text for text, plus one line: a
plain-language description of a diagnosis counts as present. Its reply quotes each such diagnosis from the original.
A quote is kept only if the original contains it word for word (spacing and letter case aside), the rewrite does not,
and the rewrite does not hold all of its content words either (the diagnosis then most likely stands there in other
words or another order); what is returned is the original's own wording. Each quote kept is then checked once more,
all in parallel: a second call asks whether the rewrite mentions that diagnosis in any wording, and the quote is left
out only when the reply says it does and quotes the rewrite's own words, which the rewrite must contain. All of it gets
at most TIME_LIMIT_S (30 s): every wait is cut to the time left.

What the reader gets reads as no established fact: the quotes are possible omissions to check against the source
(status possible_omissions); "none found" is the explainer's, and the gate's verdict stands (none_found); a failure,
the explainer's own reply cut short, the time limit, or any unexpected failure (explainer_error, set by the
endpoint, which lets nothing about the explanation fail the request) is no finding at all (unavailable), each with
its reason. When the rewrite itself was cut at max_tokens, the explanation says so: a missing item may simply come
after the cut. When the gate withheld the rewrite (block or strict mode), the note speaks of the withheld rewrite.

Advisory: it runs after the gate and changes none of the gate's output — verdicts, consensus, blocked, warning (D9);
safety_gate.py is unchanged. It covers diagnoses only, so a flag raised for another reason (a dose, a negation, an added
claim) gets no list.
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait

import requests

from safety_gate import NEBIUS_API_URL, NEMOTRON_NANO

EXPLAIN_ON = ("UNSAFE", "DISAGREE")   # the consensus values that count as a flag
TIME_LIMIT_S = 30                    # the most P2 adds to a response (owner, 2026-10-07)
MAX_TOKENS = 8000                    # arm A1's budget (3 of its 350 replies still reached it)
CHECK_MAX_TOKENS = 2000              # the check's reply is one short JSON object
TIMEOUT_S = 60                       # per request, and never more than the time left
ATTEMPTS = 2                         # a failed request is tried once more; a reply that arrives is not
MAX_QUOTES = 5
# Left out of a quote's content words (with every word shorter than three characters).
STOPWORDS = frozenset({"and", "the", "for", "with", "from", "into", "that", "this", "than", "was", "were", "are",
                       "has", "had", "have", "its", "his", "her", "their", "per", "via"})

# What the reader gets (owner, 2026-10-07): nothing reads as established fact.
NONE_FOUND = ("no_omission_found", "no_quote_held_up", "all_found_in_rewrite")   # the explainer's "none found"
UNAVAILABLE = {                                                                   # no finding at all, and why
    "no_api_key": "the explainer has no API key",
    "explainer_unreachable": "the explainer could not be reached",
    "explainer_reply_cut": "the explainer's own reply was cut off before it finished",
    "explainer_reply_unreadable": "the explainer's reply could not be read",
    "time_limit": f"the explainer did not finish within {TIME_LIMIT_S} seconds",
    "explainer_error": "the explainer failed unexpectedly",
}
# {rewrite}: "the rewrite", or "the withheld rewrite" when the gate withheld it (block or strict mode).
NOTE_POSSIBLE = ("Possible omissions, to check against the source: the explainer did not find these diagnoses from "
                 "the source in {rewrite}. They may be missing, or {rewrite} may put them in words the explainer did "
                 "not recognize. The gate's verdict stands.")
NOTE_NONE_FOUND = ("None found by the explainer. It looks only for diagnoses from the source that {rewrite} leaves "
                   "out, and it points to none; anything else that may be missing, such as a medication or a dose, is "
                   "outside what it checks. The gate's verdict stands.")
NOTE_UNAVAILABLE = "No explanation, because {why}. This is not a finding; the gate's verdict stands."
NOTE_REWRITE_CUT = " {Rewrite} was cut at max_tokens, so something missing from it may simply come after the cut."

# Arm A1's rubric (scripts/run_vagt_loop_experiment.py), text for text, plus the plain-language line after the synonym
# line; tests/test_explain.py fails if anything else differs. Its two examples are diagnoses found in none of the
# development pairs.
EXPLAIN_SYSTEM = (
    "You are a clinical record checker. You check whether a SUMMARY preserves the DIAGNOSES "
    "stated in a SOURCE note. You report only one kind of defect: a dropped diagnosis. You "
    "never comment on writing style, clinical appropriateness, or any omission other than a "
    "diagnosis."
)
EXPLAIN_USER = """Compare SOURCE and SUMMARY. Report only this one defect type:

D1 DIAGNOSIS_DROP - a diagnosis named in SOURCE does not appear in SUMMARY in any wording.

DO NOT REPORT the following. They are not defects:
- A different wording, abbreviation, synonym, brand or generic name for the same diagnosis
  ("MI" vs "myocardial infarction"). Treat these as PRESENT.
- A plain-language description of the diagnosis ("stye" for hordeolum, "head lice" for
  pediculosis). Treat these as PRESENT.
- Reordering, condensing, merging sentences, or a more concise style.
- Omission of anything that is NOT a diagnosis: medications, doses, symptoms, history, vitals,
  labs, imaging, exam findings, allergies, social history, follow-up plans.
- Missing hedges, caveats, disclaimers, or recommendations.
- Whether any content is clinically appropriate, safe, or well chosen.
- Anything you cannot support with an exact quote from SOURCE.

PROCEDURE
Step 1. List every diagnosis stated in SOURCE.
Step 2. For each, decide PRESENT or MISSING in SUMMARY. Synonyms and abbreviations count as PRESENT.
Step 3. Report only the MISSING diagnoses.

OUTPUT
Return exactly one JSON object and no other text:

{"source_items":[{"type":"DIAGNOSIS","source_quote":"<exact quote from SOURCE>","present_in_summary":true|false}],
 "defects":[{"type":"D1","source_quote":"<exact quote from SOURCE>"}],
 "verdict":"PASS|FAIL"}

Set verdict to "FAIL" if defects is non-empty, otherwise "PASS".
If you find no defects, return an empty defects list and verdict "PASS". That is valid and expected.

SOURCE:
<<<{source}>>>

SUMMARY:
<<<{summary}>>>"""

# The check call (one per quote kept), as fixed before its first run in the development notes.
CHECK_USER = """Does SUMMARY mention the diagnosis below in any wording: the same name, an abbreviation, a synonym, or a
plain-language description ("stye" for hordeolum, "head lice" for pediculosis)?

DIAGNOSIS (quoted from the source note):
<<<{diagnosis}>>>

SUMMARY:
<<<{summary}>>>

Return exactly one JSON object and no other text:
{"present": true|false, "summary_quote": "<the exact words in SUMMARY that name or describe it, or empty>"}"""


def _fill(template: str, first: str, second: str, a: str, b: str) -> str:
    """template with a in place of {first} and b in place of {second}, inserted as they are (braces in a note change
    nothing)."""
    head, rest = template.split("{" + first + "}")
    middle, tail = rest.split("{" + second + "}")
    return head + a + middle + b + tail


def _user_message(original: str, simplified: str) -> str:
    """The rubric with the two texts in place."""
    return _fill(EXPLAIN_USER, "source", "summary", original, simplified)


def _find(text: str, quote: str):
    """The part of text that is quote, spacing and letter case aside, as whole words; None if there is none."""
    words = quote.split()
    if not words:
        return None
    pattern = r"\s+".join(re.escape(w) for w in words)
    if re.match(r"\w", words[0]):
        pattern = r"\b" + pattern
    if re.search(r"\w$", words[-1]):
        pattern += r"\b"
    m = re.search(pattern, text, re.IGNORECASE)
    return m.group(0) if m else None


def _content_words(quote: str) -> set:
    """The quote's words of three or more letters or digits, lowercased, STOPWORDS left out."""
    return {w for w in re.findall(r"[a-z0-9]+", quote.lower()) if len(w) >= 3 and w not in STOPWORDS}


def _all_words_in(text: str, quote: str) -> bool:
    """True when the quote has content words and each is a whole word of text, letter case aside."""
    words, low = _content_words(quote), text.lower()
    return bool(words) and all(re.search(r"\b" + re.escape(w) + r"\b", low) for w in words)


OUT_OF_TIME = "out_of_time"   # what _post returns when the time limit ran out first


def _post(payload: dict, api_key: str, deadline: float):
    """(content, finish_reason) of the reply; None when both attempts failed; OUT_OF_TIME when the deadline came
    first. Each wait (to connect, and for data) is cut to the time left; no second attempt once it is gone."""
    for attempt in range(ATTEMPTS):
        left = deadline - time.time()
        if left <= 0:
            return OUT_OF_TIME
        try:
            resp = requests.post(NEBIUS_API_URL, json=payload, timeout=min(TIMEOUT_S, left),
                                 headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
            resp.raise_for_status()
            choice = resp.json()["choices"][0]
            return (choice.get("message") or {}).get("content"), choice.get("finish_reason")
        except Exception:
            if time.time() >= deadline:
                return OUT_OF_TIME
            if attempt == ATTEMPTS - 1:
                return None
            time.sleep(min(1, max(0, deadline - time.time())))
    return None


def _json_object(content):
    """The reply's JSON object, read past reasoning, code fences and surrounding words; None if there is none."""
    if not isinstance(content, str) or not content.strip():
        return None
    if "<think>" in content and "</think>" not in content:
        return None
    text = content.split("</think>")[-1].strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        obj = json.loads(text)
    except ValueError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        try:
            obj = json.loads(m.group(0)) if m else None
        except ValueError:
            obj = None
    return obj if isinstance(obj, dict) else None


def _read_reply(content, finish_reason) -> tuple:
    """(quotes, reason): the quotes of the reply's D1 defects, or None and why the reply cannot be used."""
    if finish_reason == "length":
        return None, "explainer_reply_cut"
    obj = _json_object(content)
    if obj is None or not isinstance(obj.get("defects"), list):
        return None, "explainer_reply_unreadable"
    d1 = [d for d in obj["defects"] if isinstance(d, dict) and d.get("type") == "D1"]
    verdict = str(obj.get("verdict", "")).strip().upper()
    if verdict not in ("PASS", "FAIL") or (verdict == "FAIL") != bool(d1):
        return None, "explainer_reply_unreadable"   # no verdict, or one the defects list contradicts
    return [d.get("source_quote") for d in d1], None


def _ground(quotes, original: str, simplified: str) -> list:
    """The quotes the original contains and the rewrite does not — not word for word, and not as all of the quote's
    content words — in the original's wording, each once."""
    kept, seen = [], set()
    for quote in quotes:
        if not isinstance(quote, str):
            continue
        span = _find(original, quote)
        if span is None or _find(simplified, quote) is not None or _all_words_in(simplified, quote):
            continue
        key = " ".join(span.split()).lower()
        if key not in seen:
            seen.add(key)
            kept.append({"source_quote": span})
    return kept[:MAX_QUOTES]


def _found_in_rewrite(diagnosis: str, simplified: str, api_key: str, deadline: float) -> bool:
    """The check call: True only when its reply says the rewrite mentions the diagnosis and quotes the rewrite's own
    words, which the rewrite contains (whole words, spacing and letter case aside). A failed, cut-off or unreadable
    check is False: the quote stays (a check the deadline cut short makes the explanation unavailable; see
    explain_flag)."""
    reply = _post({
        "model": NEMOTRON_NANO,
        "messages": [{"role": "user", "content": _fill(CHECK_USER, "diagnosis", "summary", diagnosis, simplified)}],
        "max_tokens": CHECK_MAX_TOKENS,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "extra_body": {"enable_thinking": False},
    }, api_key, deadline)
    if reply is None or reply == OUT_OF_TIME or reply[1] == "length":
        return False
    obj = _json_object(reply[0])
    if obj is None or obj.get("present") is not True:
        return False
    words = obj.get("summary_quote")
    return isinstance(words, str) and _find(simplified, words) is not None


def _explanation(reason, quotes, rewrite_cut: bool, latency_ms: int, rewrite_withheld: bool = False) -> dict:
    """The explanation as the reader gets it: status possible_omissions (quotes to check against the source),
    none_found (the explainer found none) or unavailable (no finding at all), with a note in words and the reason."""
    words = {"rewrite": "the withheld rewrite" if rewrite_withheld else "the rewrite",
             "Rewrite": "The withheld rewrite" if rewrite_withheld else "The rewrite"}
    if reason is None:
        status, note = "possible_omissions", NOTE_POSSIBLE.format(**words)
    elif reason in NONE_FOUND:
        status, note = "none_found", NOTE_NONE_FOUND.format(**words)
    else:
        status, note = "unavailable", NOTE_UNAVAILABLE.format(why=UNAVAILABLE[reason])
    if rewrite_cut:
        note += NOTE_REWRITE_CUT.format(**words)
    return {"status": status, "note": note, "possible_omissions": list(quotes), "reason": reason,
            "rewrite_cut": bool(rewrite_cut), "model": NEMOTRON_NANO, "latency_ms": latency_ms}


def time_limit_result(latency_ms: int, rewrite_cut: bool = False, rewrite_withheld: bool = False) -> dict:
    """The explanation when it was not done within TIME_LIMIT_S: unavailable, with the reason time_limit."""
    return _explanation("time_limit", (), rewrite_cut, latency_ms, rewrite_withheld)


def error_result(latency_ms: int, rewrite_cut: bool = False, rewrite_withheld: bool = False) -> dict:
    """The explanation when anything about it failed unexpectedly: unavailable, with the reason explainer_error."""
    return _explanation("explainer_error", (), rewrite_cut, latency_ms, rewrite_withheld)


def explain_flag(original: str, simplified: str, api_key=None, time_limit_s=None, rewrite_cut: bool = False,
                 rewrite_withheld: bool = False) -> dict:
    """Ask the scoped rubric which diagnoses from the original the rewrite is missing; return the quotes that pass
    both checks, as possible omissions, all within time_limit_s (default TIME_LIMIT_S). rewrite_cut: the rewrite was
    cut at max_tokens (the explanation then says so); rewrite_withheld: the gate withheld it (the note then says so).

    Returns {"status", "note", "possible_omissions": [{"source_quote": the original's wording}, ...], "reason",
    "rewrite_cut", "model", "latency_ms"} (see _explanation). Reasons for none_found: no_omission_found (the rubric
    named none), no_quote_held_up (no quote passed the quote check), all_found_in_rewrite (the check call found each
    remaining one in the rewrite); for unavailable: the keys of UNAVAILABLE."""
    t0 = time.time()
    deadline = t0 + (TIME_LIMIT_S if time_limit_s is None else time_limit_s)
    if api_key is None:
        api_key = os.environ.get("NEBIUS_API_KEY", "")

    def result(reason, quotes=()):
        return _explanation(reason, quotes, rewrite_cut, round((time.time() - t0) * 1000), rewrite_withheld)

    if not api_key:
        return result("no_api_key")
    reply = _post({
        "model": NEMOTRON_NANO,
        "messages": [{"role": "system", "content": EXPLAIN_SYSTEM},
                     {"role": "user", "content": _user_message(original, simplified)}],
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "extra_body": {"enable_thinking": False},
    }, api_key, deadline)
    if reply == OUT_OF_TIME or time.time() >= deadline:
        return result("time_limit")
    if reply is None:
        return result("explainer_unreachable")
    quotes, reason = _read_reply(*reply)
    if reason:
        return result(reason)
    if not quotes:
        return result("no_omission_found")
    kept = _ground(quotes, original, simplified)
    if not kept:
        return result("no_quote_held_up")
    ex = ThreadPoolExecutor(max_workers=len(kept))
    checks = [ex.submit(_found_in_rewrite, d["source_quote"], simplified, api_key, deadline) for d in kept]
    done, _ = wait(checks, timeout=max(0, deadline - time.time()))
    ex.shutdown(wait=False, cancel_futures=True)   # a check still running past the deadline is not waited for
    if len(done) < len(checks) or time.time() >= deadline:
        return result("time_limit")
    kept = [d for d, check in zip(kept, checks) if not check.result()]
    return result(None, kept) if kept else result("all_found_in_rewrite")
