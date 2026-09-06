"""
run_gate_calibration.py — Re-run the 708-item MedSimp-JudgeBench panel through the
DEPLOYED gate prompt (safety_gate.py), so recall / VAGT / the DISAGREE rate can be
recomputed on what the endpoint actually uses — not the calibration harness's
different JSON-CoT prompt (the calibration≠gate gap).

Text source: the v1 repo's calibration_verdicts.json (input -> original,
perturbed -> simplified), same path pattern as run_disagree_capture.py.
nemotron_calibration_full.json holds only verdicts, not text.

Output: results/gate_calibration_full.json in the SAME per_sample schema as
nemotron_calibration_full.json ({idx, error_type, condition, nemotron_verdict,
llama_verdict, qwen_verdict}, plus consensus), so it drops into vagt_core unchanged.

Robust: resumes from an existing partial (skips completed (idx,error_type,condition)
triples — idx alone is NOT unique), checkpoints every 50 items, fails loudly without
NEBIUS_API_KEY.

Run:  python src/run_gate_calibration.py
"""

import json
import os
import sys
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

# Text source (v1 repo) — same pattern as run_disagree_capture.py.
DATA_CANDIDATES = [
    Path(r"D:\Owner\Desktop\assignment_01\medisimplifier-nebius\results"
         r"\nebius_evidence\calibration_verdicts.json"),
    _REPO / "results" / "nebius_evidence" / "calibration_verdicts.json",
    Path("results/nebius_evidence/calibration_verdicts.json"),
]
OUTPUT_PATH = _REPO / "results" / "gate_calibration_full.json"
CHECKPOINT_EVERY = 50


def _load_records():
    for p in DATA_CANDIDATES:
        if p.is_file():
            return json.loads(p.read_text(encoding="utf-8")), p
    raise FileNotFoundError(
        "calibration_verdicts.json not found (v1 repo results/nebius_evidence/). "
        "It holds the input/perturbed text; nemotron_calibration_full.json has only verdicts."
    )


def _key(r):
    # idx is NOT unique (519/708); the (idx, error_type, condition) triple is.
    return (r["idx"], r["error_type"], r["condition"])


def _key_of_record(x):
    return (x["idx"], x["error_type"], x["condition"])


def _load_partial():
    """Resume: return (per_sample list, set of done keys) from an existing output."""
    if OUTPUT_PATH.is_file():
        try:
            prev = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            ps = prev.get("per_sample", [])
            return ps, {(x["idx"], x["error_type"], x["condition"]) for x in ps}
        except Exception:
            pass
    return [], set()


def _save(per_sample, total, status):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": status,
        "prompt_source": "safety_gate.py JUDGE_PROMPT (deployed one-word gate prompt)",
        "n": total,
        "completed": len(per_sample),
        "per_sample": sorted(per_sample, key=_key_of_record),
    }
    tmp = OUTPUT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUTPUT_PATH)   # atomic swap — a crash mid-write can't corrupt the file


def main() -> int:
    if not os.environ.get("NEBIUS_API_KEY", ""):
        print("ERROR: NEBIUS_API_KEY is not set — evaluate_safety would return all-ERROR.",
              file=sys.stderr)
        print("Set it and re-run:  export NEBIUS_API_KEY=...", file=sys.stderr)
        return 2

    records, src = _load_records()
    total = len(records)
    per_sample, done = _load_partial()
    print(f"Gate re-run: {total} items from {src.name} → {OUTPUT_PATH.name}", flush=True)
    if done:
        print(f"Resuming — {len(done)} already done, {total - len(done)} remaining.", flush=True)

    for r in records:
        if _key(r) in done:
            continue
        # REAL gate call — three Token Factory judges (gate prompt) in parallel per item.
        res = evaluate_safety(r["input"], r["perturbed"], safety_mode="flag")
        per_sample.append({
            "idx": r["idx"],
            "error_type": r["error_type"],
            "condition": r["condition"],
            "nemotron_verdict": res.get("nemotron_verdict"),
            "llama_verdict": res.get("llama_verdict"),
            "qwen_verdict": res.get("qwen_verdict"),
            "consensus": res.get("consensus"),
        })
        done.add(_key(r))
        if len(per_sample) % CHECKPOINT_EVERY == 0:
            _save(per_sample, total, "in_progress")
            print(f"  {len(per_sample)}/{total} done (checkpoint saved)", flush=True)

    _save(per_sample, total, "complete")

    # ── quick summary vs the calibration numbers ──
    err = sum(1 for x in per_sample
              if "ERROR" in (x["llama_verdict"], x["qwen_verdict"], x["nemotron_verdict"]))
    disagree = sum(1 for x in per_sample
                   if x["nemotron_verdict"] == "UNSAFE" and x["qwen_verdict"] == "SAFE")
    n = len(per_sample)
    print(f"\nDONE — wrote {OUTPUT_PATH} ({n}/{total})", flush=True)
    print(f"  rows with an ERROR judge: {err}", flush=True)
    print(f"  DISAGREE (Nemotron UNSAFE & Qwen SAFE) under GATE prompt: "
          f"{disagree} ({100*disagree/n:.1f}%)  —  calibration was 203/708 = 28.7%", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
