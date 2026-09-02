"""
run_disagree_capture.py — Search for a real DISAGREE case through the live 3-judge gate.

Per disagree_capture_clarification_response.txt (Opus 4.8, self-corrected):
  A DISAGREE is a *synthetic test of the gate's logic*, not live product output —
  our own model preserves diagnoses. Rather than hand-author a drop, we replay REAL
  MedSimp-JudgeBench diagnosis-stratum items (idx 21 primary, idx 146 backup) whose
  CALIBRATION verdicts were Qwen=SAFE, Nemotron=UNSAFE (a recorded 2-judge miss).
  What is REAL here: the gate, the three Token Factory judge calls, the verdicts,
  and the split. CAVEAT: calibration used different judge prompts than safety_gate.py,
  so the split is NOT guaranteed to reproduce live — this is a genuine test, not a replay.

Logic:
  - Load original (`input`) + simplified (`perturbed`) text for idx 21, then idx 146,
    from the v1 repo's calibration_verdicts.json (nemotron_calibration_full.json holds
    only verdicts, NOT the text).
  - For each, call the REAL evaluate_safety(original, simplified).
  - Stop at the first result where nemotron == "UNSAFE" AND qwen == "SAFE"
    (the gate's DISAGREE hinge; Llama is NOT in the consensus logic).
  - If found: assemble {our fields incl. source + benchmark_idx} + {verbatim gate
    output} and write results/disagree_case_gate.json (warning copied EXACTLY).
  - If none split: print an honest report and write nothing. That outcome is
    itself a finding (most diagnosis drops are overt); do NOT force it.

Requires NEBIUS_API_KEY in the environment (the gate silently returns all-ERROR
without it, so we fail loudly here instead).
"""

import json
import os
import sys
from pathlib import Path

# Make stdout UTF-8 on Windows (cp1255 default) so tau/Phi/kappa/em-dashes print.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# src/ on path so `evaluate_safety` imports whether run from repo root or src/.
_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SRC_DIR)
sys.path.insert(0, _SRC_DIR)
from safety_gate import evaluate_safety  # noqa: E402

OUTPUT_PATH = os.path.join(_REPO_ROOT, "results", "disagree_case_gate.json")

# ── Benchmark source (v1 repo): idx -> record with `input`/`perturbed` text ────
# nemotron_calibration_full.json has ONLY verdicts; the original/simplified text
# lives in the v1 repo's calibration_verdicts.json (input=original, perturbed=simplified).
BENCHMARK_DATA_CANDIDATES = [
    Path(r"D:\Owner\Desktop\assignment_01\medisimplifier-nebius\results"
         r"\nebius_evidence\calibration_verdicts.json"),
    Path("results/nebius_evidence/calibration_verdicts.json"),
]

# Real MedSimp-JudgeBench diagnosis-stratum items whose CALIBRATION verdicts were
# Qwen=SAFE, Nemotron=UNSAFE (a recorded 2-judge miss). Primary idx 21, backup idx 146.
# `dropped_diagnosis` is a manual annotation of the injected error (verified by
# diffing clean_ref vs perturbed).
BENCHMARK_ITEMS = [
    {
        "benchmark_idx": 21,
        "label": "prostatic + intracranial TB (idx 21, primary)",
        "dropped_diagnosis": "intracranial TB confirmation (MRI finding)",
    },
    {
        "benchmark_idx": 146,
        "label": "Parkinson disease + comorbid depression (idx 146, backup)",
        "dropped_diagnosis": ("depression (comorbid psychiatric diagnosis) — named in the "
                              "original, absent from the simplified"),
    },
]


def _load_benchmark_records():
    """Return {idx: record} from the v1 repo's calibration_verdicts.json."""
    for p in BENCHMARK_DATA_CANDIDATES:
        if p.is_file():
            recs = json.loads(p.read_text(encoding="utf-8"))
            return {r["idx"]: r for r in recs}
    raise FileNotFoundError(
        "calibration_verdicts.json not found (v1 repo results/nebius_evidence/). "
        "nemotron_calibration_full.json holds only verdicts, not original/simplified text."
    )


def _build_candidates():
    """Attach original (`input`) + simplified (`perturbed`) text to each benchmark item."""
    by_idx = _load_benchmark_records()
    built = []
    for item in BENCHMARK_ITEMS:
        r = by_idx[item["benchmark_idx"]]        # KeyError if idx absent -> caught in main()
        built.append({
            "benchmark_idx": item["benchmark_idx"],
            "label": item["label"],
            "dropped_diagnosis": item["dropped_diagnosis"],
            "original": r["input"],              # clean discharge summary
            "simplified": r["perturbed"],        # corrupted simplification the judges score
        })
    return built


def is_disagree(result: dict) -> bool:
    """The gate's DISAGREE hinge: Nemotron flags, Qwen clears (Llama is not consulted)."""
    return result.get("nemotron_verdict") == "UNSAFE" and result.get("qwen_verdict") == "SAFE"


def main() -> int:
    if not os.environ.get("NEBIUS_API_KEY", ""):
        print("ERROR: NEBIUS_API_KEY is not set. The gate would silently return all-ERROR.",
              file=sys.stderr)
        print("Set it and re-run:  export NEBIUS_API_KEY=...", file=sys.stderr)
        return 2

    try:
        candidates = _build_candidates()
    except (FileNotFoundError, KeyError) as e:
        print(f"ERROR loading benchmark text: {e}", file=sys.stderr)
        return 3

    print(f"Searching for a real DISAGREE across {len(candidates)} benchmark items "
          f"(stop at first Nemotron=UNSAFE & Qwen=SAFE).\n")

    attempted = []
    for cand in candidates:
        print(f"── idx {cand['benchmark_idx']}: {cand['label']}")
        print(f"   dropped: {cand['dropped_diagnosis']}")
        # REAL gate call — three Token Factory judges in parallel.
        result = evaluate_safety(cand["original"], cand["simplified"], safety_mode="flag")
        llama = result.get("llama_verdict")
        qwen = result.get("qwen_verdict")
        nemotron = result.get("nemotron_verdict")
        consensus = result.get("consensus")
        print(f"   Llama={llama}  Qwen={qwen}  Nemotron={nemotron}  ->  consensus={consensus}")
        attempted.append({"benchmark_idx": cand["benchmark_idx"], "label": cand["label"],
                          "llama": llama, "qwen": qwen, "nemotron": nemotron,
                          "consensus": consensus})

        if is_disagree(result):
            print(f"\n✅ SPLIT on idx {cand['benchmark_idx']}: Nemotron=UNSAFE, Qwen=SAFE -> DISAGREE.\n")
            # Assemble our fields + the VERBATIM gate output (warning copied exactly).
            record = {
                "original": cand["original"],
                "simplified": cand["simplified"],
                "dropped_diagnosis": cand["dropped_diagnosis"],
                "source": "MedSimp-JudgeBench diagnosis stratum",
                "benchmark_idx": cand["benchmark_idx"],
                "llama_verdict": llama,
                "qwen_verdict": qwen,
                "nemotron_verdict": nemotron,
                "blocked": result.get("blocked"),
                "consensus": consensus,
                "warning": result.get("warning"),  # exact string from the gate
            }
            os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
                f.write("\n")
            print(f"Wrote {OUTPUT_PATH}")
            print(json.dumps(record, ensure_ascii=False, indent=2))
            return 0

    # No candidate split — honest report, write nothing.
    print("\n❌ No candidate produced a DISAGREE (Nemotron=UNSAFE & Qwen=SAFE).")
    print("Attempts:")
    for a in attempted:
        print(f"  idx {a['benchmark_idx']} ({a['label']}): "
              f"Llama={a['llama']} Qwen={a['qwen']} Nemotron={a['nemotron']} -> {a['consensus']}")
    print("\nHonest outcome: the crafted drops did not split the panel. Per the spec, do NOT")
    print("force it — report that DISAGREE is hard to trigger even by construction (evidence")
    print("that most diagnosis drops are overt) and lean on the VAGT inversion. Nothing written.")
    if any(a["qwen"] == "ERROR" or a["nemotron"] == "ERROR" for a in attempted):
        print("\nNOTE: one or more judges returned ERROR — this is a call failure, NOT a clean")
        print("'no split'. Check NEBIUS_API_KEY / network and re-run before drawing conclusions.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
