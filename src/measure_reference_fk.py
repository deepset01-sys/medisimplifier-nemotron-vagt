"""
measure_reference_fk.py — FK-Grade (Flesch-Kincaid) of the two reference sets.

Backs the A7 "Honest interpretation" claim: Nemotron Super references read at a higher
grade level than the Claude references. Measures flesch_kincaid_grade on the 9,976 matched
pairs (records where BOTH claude_output and nemotron_output are non-empty; 23 teacher
generations errored and are excluded) from nemotron_training_references.json.

Output: results/reference_fk_grade.json —
    {source, metric, textstat_version, n_pairs, claude_refs_mean_fk,
     nemotron_refs_mean_fk, delta_nemotron_minus_claude}

Reproducible: pin textstat==0.7.13 (grade values shift across textstat builds — the
student's published FK 8.87 was scored with the train-v32 image's textstat and is NOT
directly comparable to these reference figures). Run:  python src/measure_reference_fk.py
"""

import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import textstat  # noqa: E402

_REPO = Path(__file__).resolve().parent.parent
REFS_PATH = _REPO / "nemotron_training_references.json"
OUTPUT_PATH = _REPO / "results" / "reference_fk_grade.json"


def _version() -> str:
    v = textstat.__version__
    return ".".join(map(str, v)) if isinstance(v, tuple) else str(v)


def main() -> int:
    recs = json.loads(REFS_PATH.read_text(encoding="utf-8"))
    pairs = [(r["claude_output"], r["nemotron_output"]) for r in recs
             if (r.get("claude_output") or "").strip()
             and (r.get("nemotron_output") or "").strip()]
    n = len(pairs)
    if n == 0:
        print("ERROR: no matched (claude_output, nemotron_output) pairs found.", file=sys.stderr)
        return 1

    claude = [textstat.flesch_kincaid_grade(c) for c, _ in pairs]
    nemo = [textstat.flesch_kincaid_grade(nn) for _, nn in pairs]
    cm, nm = sum(claude) / n, sum(nemo) / n

    out = {
        "source": "nemotron_training_references.json (9,976 matched pairs)",
        "metric": "flesch_kincaid_grade",
        "textstat_version": _version(),
        "n_pairs": n,
        "claude_refs_mean_fk": round(cm, 2),
        "nemotron_refs_mean_fk": round(nm, 2),
        "delta_nemotron_minus_claude": round(nm - cm, 2),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("Saved:", json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
