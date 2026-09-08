"""
run_student_audit.py — Diagnosis-retention audit of the v2 student's OWN test outputs.

Runs the deployed 3-judge safety gate (safety_gate.py) over each (input, prediction)
pair from the student's test-set generations, to MEASURE how often the gate flags the
student's own simplifications — i.e., whether "our model preserves diagnoses" holds.

Source: results/student_predictions.json — [{index, input, prediction, claude_output}, ...]
        input = original discharge summary; prediction = the v2 student's simplification.
Output: results/student_audit.json — {status, n, completed, counts, per_sample:[...]}.

NOTE: the test set has NO injected-error ground truth, so a DISAGREE/UNSAFE here cannot be
auto-labeled "genuine catch vs false alarm." Flagged items are saved (index) for manual
review; the calibration false-alarm rate (~1-in-3 DISAGREE on faithful text, B5) is the prior.

Robust: resumes from an existing partial (skips completed index), checkpoints every 50,
fails loudly without NEBIUS_API_KEY. Run:  python src/run_student_audit.py
"""

import json
import os
import sys
from collections import Counter
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SRC = Path(__file__).resolve().parent
_REPO = _SRC.parent
sys.path.insert(0, str(_SRC))
from safety_gate import evaluate_safety  # noqa: E402

PREDICTIONS_PATH = _REPO / "results" / "student_predictions.json"
OUTPUT_PATH = _REPO / "results" / "student_audit.json"
CHECKPOINT_EVERY = 50


def _load_records():
    if not PREDICTIONS_PATH.is_file():
        raise FileNotFoundError(
            f"{PREDICTIONS_PATH} not found — retrieve it via aws s3 cp from "
            "s3://medisimplifier-adapters-v2/eval_v2_nemotron/predictions.json"
        )
    return json.loads(PREDICTIONS_PATH.read_text(encoding="utf-8"))


def _load_partial():
    if OUTPUT_PATH.is_file():
        try:
            prev = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            ps = prev.get("per_sample", [])
            return ps, {x["index"] for x in ps}
        except Exception:
            pass
    return [], set()


def _counts(per_sample):
    return dict(Counter(x["consensus"] for x in per_sample))


def _save(per_sample, total, status):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "source": "results/student_predictions.json (v2 student test-set generations)",
        "gate": "safety_gate.py 3-judge gate (Qwen3-32B dedicated endpoint)",
        "n": total,
        "completed": len(per_sample),
        "counts": _counts(per_sample),
        "per_sample": sorted(per_sample, key=lambda x: x["index"]),
    }
    tmp = OUTPUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUTPUT_PATH)   # atomic swap


def main() -> int:
    if not os.environ.get("NEBIUS_API_KEY", ""):
        print("ERROR: NEBIUS_API_KEY is not set — evaluate_safety would return all-ERROR.",
              file=sys.stderr)
        return 2

    records = _load_records()
    total = len(records)
    per_sample, done = _load_partial()
    print(f"Student audit: {total} test outputs -> {OUTPUT_PATH.name}", flush=True)
    if done:
        print(f"Resuming — {len(done)} done, {total - len(done)} remaining.", flush=True)

    for r in records:
        idx = r["index"]
        if idx in done:
            continue
        original = (r.get("input") or "")
        simplified = (r.get("prediction") or "")
        if not simplified.strip():           # empty gen (prompt leak/truncation) — not a gate call
            per_sample.append({"index": idx, "consensus": "SKIPPED_EMPTY",
                               "nemotron_verdict": None, "llama_verdict": None,
                               "qwen_verdict": None, "warning": "empty prediction"})
            done.add(idx)
            continue
        res = evaluate_safety(original, simplified, safety_mode="flag")
        per_sample.append({
            "index": idx,
            "consensus": res.get("consensus"),
            "nemotron_verdict": res.get("nemotron_verdict"),
            "llama_verdict": res.get("llama_verdict"),
            "qwen_verdict": res.get("qwen_verdict"),
            "warning": res.get("warning"),
        })
        done.add(idx)
        if len(per_sample) % CHECKPOINT_EVERY == 0:
            _save(per_sample, total, "in_progress")
            print(f"  {len(per_sample)}/{total}  {_counts(per_sample)}", flush=True)

    _save(per_sample, total, "complete")

    # ── final summary ──
    n = len(per_sample)
    counts = _counts(per_sample)
    graded = [x for x in per_sample if x["consensus"] != "SKIPPED_EMPTY"]
    ng = len(graded) or 1
    safe = counts.get("SAFE", 0)
    disagree = [x for x in graded if x["consensus"] == "DISAGREE"]
    unsafe = [x for x in graded if x["consensus"] == "UNSAFE"]
    err = counts.get("ERROR", 0)
    print(f"\nDONE — wrote {OUTPUT_PATH} ({n}/{total})", flush=True)
    print(f"  counts: {counts}", flush=True)
    print(f"  of {ng} graded:  SAFE {safe} ({100*safe/ng:.1f}%)  "
          f"DISAGREE {len(disagree)} ({100*len(disagree)/ng:.1f}%)  "
          f"UNSAFE {len(unsafe)} ({100*len(unsafe)/ng:.1f}%)  ERROR {err}", flush=True)
    print(f"  Flagged (DISAGREE+UNSAFE): {len(disagree)+len(unsafe)} — indices in per_sample "
          f"for manual review; NO auto genuine-vs-FP (no ground truth on real outputs).", flush=True)
    print(f"  Interpret vs the gate's KNOWN false-alarm rate on faithful text (~1-in-3 DISAGREE, "
          f"35.2% Nemotron clean FP) — NOT vs zero.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
