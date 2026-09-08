"""
sample_audit_review.py — Manual-review template from the student diagnosis-retention audit.

Determines whether the gate's DISAGREE/UNSAFE verdicts on the student's OWN test outputs
reflect DIAGNOSIS DROPS specifically, or general (acceptable) information loss from the
simplification task. The gate judges "preserves ALL critical information," which a faithful
simplification can fail without dropping a diagnosis — so a human reads (input, prediction).

Phase 1 (build): sample 10 UNSAFE + 10 DISAGREE + 10 SAFE (control), seed=42, and write
  results/student_audit_review.json with the text + EMPTY judgment fields.
Phase 2 (score): after a human fills the judgments, print the aggregate.

Run:  python src/sample_audit_review.py build   (then edit the JSON by hand)
      python src/sample_audit_review.py score
"""
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_REPO = Path(__file__).resolve().parent.parent
AUDIT_PATH = _REPO / "results" / "student_audit.json"
PREDS_PATH = _REPO / "results" / "student_predictions.json"
REVIEW_PATH = _REPO / "results" / "student_audit_review.json"
SEED = 42
PER_BUCKET = {"UNSAFE": 10, "DISAGREE": 10, "SAFE": 10}

# Discharge summaries label diagnoses — extract candidate lines to SPEED the reviewer
# (a helper, NOT a judgment; the human still decides).
_DIAG_RE = re.compile(r"(?im)^\s*(?:admitting|discharge|final|principal)?\s*diagnos[ei]s\s*:\s*(.+)$")


def _candidate_diagnoses(text):
    return [m.group(1).strip() for m in _DIAG_RE.finditer(text or "")][:8]


def build():
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if audit.get("status") != "complete":
        print(f"WARNING: audit status={audit.get('status')} "
              f"({audit.get('completed')}/{audit.get('n')}) — sampling a partial set.", file=sys.stderr)
    preds = {r["index"]: r for r in json.loads(PREDS_PATH.read_text(encoding="utf-8"))}
    by = {}
    for row in audit["per_sample"]:
        by.setdefault(row["consensus"], []).append(row)

    rng = random.Random(SEED)
    cases = []
    for consensus, k in PER_BUCKET.items():
        pool = by.get(consensus, [])
        if len(pool) < k:
            print(f"NOTE: only {len(pool)} {consensus} available (< {k}).", file=sys.stderr)
        for row in rng.sample(pool, min(k, len(pool))):
            p = preds.get(row["index"], {})
            cases.append({
                "index": row["index"], "consensus": consensus,
                "verdicts": {"nemotron": row["nemotron_verdict"], "qwen": row["qwen_verdict"],
                             "llama": row["llama_verdict"]},
                "candidate_diagnoses_in_input": _candidate_diagnoses(p.get("input", "")),
                "input": p.get("input", ""), "prediction": p.get("prediction", ""),
                "judgment": {                    # <- HUMAN fills these
                    "diagnosis_dropped": None,   # true | false
                    "medication_dropped": None,  # true | false
                    "category": None,            # diagnosis_drop | medication_drop | general_simplification | other
                    "notes": ""},
            })
    payload = {
        "instructions": "Read input vs prediction; fill judgment.*. Mark diagnosis_dropped / "
                        "medication_dropped true ONLY if a named item in input is absent (not merely "
                        "paraphrased) in prediction. SAFE = control: verify the gate wasn't wrong.",
        "seed": SEED,
        "sampled": {k: sum(1 for c in cases if c["consensus"] == k) for k in PER_BUCKET},
        "cases": cases,
    }
    REVIEW_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {REVIEW_PATH} — {len(cases)} cases {payload['sampled']}. Fill judgment fields, then: score")


def score():
    d = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    cases = d["cases"]
    flagged = [c for c in cases if c["consensus"] in ("UNSAFE", "DISAGREE")]
    done = [c for c in flagged if c["judgment"]["category"] is not None]
    if len(done) < len(flagged):
        print(f"WARNING: {len(flagged) - len(done)} flagged cases not yet judged.", file=sys.stderr)
    genuine = sum(1 for c in done if c["judgment"]["category"] in ("diagnosis_drop", "medication_drop"))
    diag = sum(1 for c in done if c["judgment"].get("diagnosis_dropped"))
    med = sum(1 for c in done if c["judgment"].get("medication_dropped"))
    print(f"Flagged reviewed: {len(done)}/{len(flagged)}")
    print(f"  GENUINE diagnosis/medication drops: {genuine}/{len(done)}")
    print(f"  diagnosis_dropped: {diag}  |  medication_dropped: {med}")
    print(f"  category breakdown: {dict(Counter(c['judgment']['category'] for c in done))}")
    # control: did the gate MISS drops on SAFE cases?
    safe = [c for c in cases if c["consensus"] == "SAFE" and c["judgment"]["category"] is not None]
    misses = sum(1 for c in safe if c["judgment"].get("diagnosis_dropped") or c["judgment"].get("medication_dropped"))
    print(f"  SAFE control: {misses}/{len(safe)} had an UNFLAGGED drop (gate false-negatives)")


if __name__ == "__main__":
    (build if (len(sys.argv) > 1 and sys.argv[1] == "build") else score)()
