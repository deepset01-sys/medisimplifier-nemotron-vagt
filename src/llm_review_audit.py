"""
llm_review_audit.py — Dual-auditor LLM review of the flagged student outputs (Option A).

Auto-classifies the 30 sampled cases in results/student_audit_review.json with TWO
independent, non-project frontier auditors:
    * Claude Sonnet 5   (Anthropic,  ANTHROPIC_API_KEY)
    * Gemini 2.5 Pro    (Google,     GOOGLE_API_KEY)
Both get the IDENTICAL prompt at temperature 0. Per case we store each auditor's
{diagnosis_dropped, medication_dropped, category, notes} plus an agreement flag
(same category). Disagreements are surfaced as a contested list for HUMAN adjudication.

Why two external families: Nemotron is the student's teacher; Llama/Qwen are the
diagnosis-blind gate judges — none is an independent auditor. Claude + Gemini are
different providers/lineages with no role in the pipeline, so their errors are
independent. This is an LLM-ASSISTED cross-check + human adjudication of disagreements,
NOT a human census — report it as a 30-case SAMPLE, never extrapolated to all 521 flagged.

Neither auditor runs on Nebius — this is a one-time METHODOLOGY check, not a product
endpoint (keeping competitor-cloud models out of the Nebius×NVIDIA product surface).

Checkpoints per case (resume-capable). Run:
    python src/llm_review_audit.py          # judge all 30 with both auditors
    python src/llm_review_audit.py report   # re-print agreement + contested (no API calls)
"""
import json, os, re, sys, time
from pathlib import Path
import requests

try:
    sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_REPO = Path(__file__).resolve().parent.parent
REVIEW_PATH = _REPO / "results" / "student_audit_review.json"

CLAUDE_MODEL = "claude-sonnet-5"
GEMINI_MODEL = "gemini-2.5-pro"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
VALID_CATS = {"diagnosis_drop", "medication_drop", "general_simplification", "other"}

PROMPT = """You are a medical information auditor.
Read the original discharge summary and the simplified version.

Original: {input}
Simplified: {prediction}

Answer these questions:
1. Is any diagnosis mentioned in the original ABSENT (not merely paraphrased) in the simplified version? (yes/no)
2. Is any medication mentioned in the original ABSENT in the simplified version? (yes/no)
3. Category: diagnosis_drop / medication_drop / general_simplification / other

Respond in JSON only:
{{
  "diagnosis_dropped": true/false,
  "medication_dropped": true/false,
  "category": "...",
  "notes": "brief explanation"
}}"""


# ---------- parsing helpers ----------
def _norm(v):
    if isinstance(v, bool): return v
    if isinstance(v, str):  return v.strip().lower() in ("yes", "true")
    return None


def _parse(raw):
    """Extract the JSON object from a model reply (strip fences / reasoning prefix)."""
    if raw is None:
        raise ValueError("empty response")
    if "</think>" in raw:
        raw = raw.split("</think>")[-1]
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in response")
    d = json.loads(m.group(0))
    cat = d.get("category")
    return {
        "diagnosis_dropped": _norm(d.get("diagnosis_dropped")),
        "medication_dropped": _norm(d.get("medication_dropped")),
        "category": cat if cat in VALID_CATS else "other",
        "notes": str(d.get("notes", ""))[:500],
    }


# ---------- provider callers (return raw text) ----------
def _call_claude(text, key, max_retries=3):
    payload = {"model": CLAUDE_MODEL, "max_tokens": 2048,   # temperature deprecated for Sonnet 5 — omitted
               "messages": [{"role": "user", "content": text}]}
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for attempt in range(max_retries):
        try:
            r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=120)
            if not r.ok:                                  # surface the actual API error body
                raise ValueError(f"HTTP {r.status_code}: {r.text[:400]}")
            return "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


def _call_gemini(text, key, max_retries=3):
    # Gemini 2.5 Pro reasons internally; give generous output budget so thinking
    # doesn't truncate the JSON. responseMimeType forces a JSON body.
    payload = {"contents": [{"parts": [{"text": text}]}],
               "generationConfig": {"temperature": 0, "maxOutputTokens": 8192,
                                     "responseMimeType": "application/json"}}
    for attempt in range(max_retries):
        try:
            r = requests.post(GEMINI_URL, params={"key": key},
                              headers={"content-type": "application/json"}, json=payload, timeout=120)
            r.raise_for_status()
            cands = r.json().get("candidates", [])
            if not cands:
                raise ValueError("no candidates (possibly safety-blocked)")
            return "".join(p.get("text", "") for p in cands[0]["content"]["parts"])
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


def _judge(caller, text, key):
    """Call one provider; return a judgment dict, or {'_error': ...} on failure."""
    try:
        return _parse(caller(text, key))
    except Exception as e:
        return {"_error": str(e)[:400]}


# ---------- reusable core ----------
def audit_panel(original, simplified, anthropic_key, google_key):
    """Judge one (original, simplified) pair with both auditors. Reusable if later wrapped
    in an endpoint. Returns {claude_judgment, gemini_judgment, agreement}."""
    text = PROMPT.format(input=original, prediction=simplified)
    claude = _judge(_call_claude, text, anthropic_key)
    gemini = _judge(_call_gemini, text, google_key)
    ok = "_error" not in claude and "_error" not in gemini
    agreement = (claude.get("category") == gemini.get("category")) if ok else None
    return {"claude_judgment": claude, "gemini_judgment": gemini, "agreement": agreement}


# ---------- reporting ----------
def _report(d):
    cases = d["cases"]
    flagged = [c for c in cases if c["consensus"] in ("UNSAFE", "DISAGREE")]
    judged = [c for c in flagged if c.get("agreement") is not None]
    agree = [c for c in judged if c["agreement"]]
    print(f"\n=== Dual-auditor review — {CLAUDE_MODEL} + {GEMINI_MODEL} (30-case SAMPLE) ===")
    print(f"Flagged cases judged by both: {len(judged)}/{len(flagged)}")
    if judged:
        print(f"Agreement (same category): {len(agree)}/{len(judged)} = {len(agree)/len(judged):.0%}")
    # where BOTH auditors independently call it a drop -> high-confidence genuine drop
    def is_drop(j): return j.get("category") in ("diagnosis_drop", "medication_drop")
    both_drop = [c for c in agree if is_drop(c["claude_judgment"])]
    print(f"BOTH agree genuine diagnosis/medication drop: {len(both_drop)}/{len(judged)}"
          f"  (indices: {[c['index'] for c in both_drop]})")
    # contested -> HUMAN adjudication
    contested = [c for c in judged if not c["agreement"]]
    print(f"\nContested — need human adjudication: {len(contested)}")
    for c in contested:
        print(f"  idx {c['index']} [{c['consensus']}]: "
              f"claude={c['claude_judgment'].get('category')} | "
              f"gemini={c['gemini_judgment'].get('category')}")
    errs = [c for c in flagged if c.get("agreement") is None
            and ("_error" in c.get("claude_judgment", {}) or "_error" in c.get("gemini_judgment", {}))]
    if errs:
        print(f"\nErrors (re-run to retry): {[c['index'] for c in errs]}")


def _needs(field, c):
    """A provider judgment needs (re)running only if it's missing or recorded an error.
    Good judgments are kept as-is — so a re-run retries only the failed provider."""
    j = c.get(field)
    return j is None or "_error" in j


def _agreement(cj, gj):
    ok = cj is not None and gj is not None and "_error" not in cj and "_error" not in gj
    return (cj.get("category") == gj.get("category")) if ok else None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        _report(json.loads(REVIEW_PATH.read_text(encoding="utf-8")))
        return 0
    d = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    cases = d["cases"]
    need_c = [c for c in cases if _needs("claude_judgment", c)]
    need_g = [c for c in cases if _needs("gemini_judgment", c)]
    ak = os.environ.get("ANTHROPIC_API_KEY", "")
    gk = os.environ.get("GOOGLE_API_KEY", "")
    if need_c and not ak:
        print("ERROR: ANTHROPIC_API_KEY not set (Claude judgments to (re)run).", file=sys.stderr); return 2
    if need_g and not gk:
        print("ERROR: GOOGLE_API_KEY not set (Gemini judgments to (re)run).", file=sys.stderr); return 2
    print(f"Resume: Claude {len(need_c)}/{len(cases)} to (re)run | Gemini {len(need_g)}/{len(cases)} "
          f"({CLAUDE_MODEL} + {GEMINI_MODEL}); existing good judgments kept as-is.", flush=True)
    for i, c in enumerate(cases, 1):
        changed = False
        text = PROMPT.format(input=c["input"], prediction=c["prediction"])
        if _needs("claude_judgment", c):
            c["claude_judgment"] = _judge(_call_claude, text, ak); changed = True
        if _needs("gemini_judgment", c):
            c["gemini_judgment"] = _judge(_call_gemini, text, gk); changed = True
        if not changed:
            continue
        cj, gj = c.get("claude_judgment", {}), c.get("gemini_judgment", {})
        c["agreement"] = ag = _agreement(cj, gj)
        tag = ("agree" if ag else "CONTESTED") if ag is not None else "ERROR"
        print(f"  [{i}/{len(cases)}] idx {c['index']} [{c['consensus']}] {tag}: "
              f"claude={cj.get('category', cj.get('_error'))} | "
              f"gemini={gj.get('category', gj.get('_error'))}", flush=True)
        REVIEW_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")  # checkpoint
    d["review_method"] = (f"LLM-assisted dual auditor ({CLAUDE_MODEL} + {GEMINI_MODEL}), temp=0; "
                          f"independent non-project families; agreement + human adjudication of "
                          f"disagreements; 30-case SAMPLE (not a census of all flagged).")
    REVIEW_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    _report(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
