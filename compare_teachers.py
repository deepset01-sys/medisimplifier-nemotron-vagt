"""compare_teachers.py — Claude Opus vs Nemotron Super as teacher (ROUGE-L).

Reads nemotron_training_references.json (records:
  {split, index, input, claude_output, nemotron_output, error})
and measures ROUGE-L between the two teachers' outputs for every record where
both are present.

What this measures: AGREEMENT between the two teacher models, NOT quality against
a human gold standard. High ROUGE-L => the teachers produced similar simplified
text; low => they diverged (different phrasing, structure, or content). ROUGE-L
f-measure is symmetric in (reference, candidate); here claude_output is passed as
the reference and nemotron_output as the candidate (same prompt for both, so any
divergence reflects the model, not the instructions).

Output: teacher_comparison.json + a stdout summary.
Usage: python compare_teachers.py [--input nemotron_training_references.json]
                                   [--output teacher_comparison.json] [--examples 5]
"""

import sys
import json
import argparse
from pathlib import Path

try:
    from rouge_score import rouge_scorer
except ImportError:
    sys.exit("rouge-score not installed — run: pip install rouge-score")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BUCKETS = [(i / 10, (i + 1) / 10) for i in range(10)]  # [0.0,0.1) ... [0.9,1.0]


def bucket_label(lo, hi):
    return f"{lo:.1f}-{hi:.1f}"


def assign_bucket(score):
    for lo, hi in BUCKETS:
        # last bucket is inclusive of 1.0
        if (lo <= score < hi) or (hi == 1.0 and score == 1.0):
            return bucket_label(lo, hi)
    return bucket_label(*BUCKETS[-1])


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def median(xs):
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5


def snippet(text, n=300):
    text = " ".join((text or "").split())
    return text[:n] + ("…" if len(text) > n else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="nemotron_training_references.json")
    ap.add_argument("--output", default="teacher_comparison.json")
    ap.add_argument("--examples", type=int, default=5, help="N most-divergent / most-similar to show")
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"input not found: {in_path} (run nemotron_training_data.py first)")
    records = json.loads(in_path.read_text(encoding="utf-8"))

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)  # matches v1 evaluate.py

    scored = []          # per-record {split, index, rougeL}
    skipped = 0
    for r in records:
        c, n = r.get("claude_output"), r.get("nemotron_output")
        if r.get("error") is not None or not c or not n:
            skipped += 1
            continue
        f = scorer.score(c, n)["rougeL"].fmeasure   # claude=reference, nemotron=candidate
        scored.append({"split": r["split"], "index": r["index"], "rougeL": round(f, 4),
                       "_claude": c, "_nemotron": n, "_input": r.get("input", "")})

    if not scored:
        sys.exit("No scorable records (all missing an output or errored).")

    vals = [s["rougeL"] for s in scored]

    # per-split means
    splits = {}
    for s in scored:
        splits.setdefault(s["split"], []).append(s["rougeL"])
    per_split = {sp: {"n": len(v), "mean_rougeL": round(mean(v), 4),
                      "median_rougeL": round(median(v), 4)} for sp, v in sorted(splits.items())}

    # histogram
    hist = {bucket_label(lo, hi): 0 for lo, hi in BUCKETS}
    for v in vals:
        hist[assign_bucket(v)] += 1

    # most-divergent (lowest) and most-similar (highest)
    ordered = sorted(scored, key=lambda s: s["rougeL"])
    def ex(s):
        return {"split": s["split"], "index": s["index"], "rougeL": s["rougeL"],
                "input": snippet(s["_input"]), "claude_output": snippet(s["_claude"]),
                "nemotron_output": snippet(s["_nemotron"])}
    lowest = [ex(s) for s in ordered[:args.examples]]
    highest = [ex(s) for s in ordered[::-1][:args.examples]]

    summary = {
        "input_file": str(in_path),
        "records_total": len(records),
        "records_scored": len(scored),
        "records_skipped": skipped,
        "overall": {
            "mean_rougeL": round(mean(vals), 4),
            "median_rougeL": round(median(vals), 4),
            "std_rougeL": round(stdev(vals), 4),
            "min_rougeL": round(min(vals), 4),
            "max_rougeL": round(max(vals), 4),
        },
        "per_split": per_split,
        "histogram": hist,
        "most_divergent": lowest,       # lowest ROUGE-L = teachers disagree most
        "most_similar": highest,        # highest ROUGE-L = teachers agree most
        "per_record": [{"split": s["split"], "index": s["index"], "rougeL": s["rougeL"]} for s in scored],
    }
    Path(args.output).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── stdout summary ───────────────────────────────────────────────────────
    print("=" * 64)
    print("TEACHER COMPARISON — Claude Opus vs Nemotron Super (ROUGE-L)")
    print("=" * 64)
    print(f"Input: {in_path.name}  |  scored {len(scored)}/{len(records)} "
          f"(skipped {skipped}: errored or missing an output)")
    o = summary["overall"]
    print(f"\nMean ROUGE-L:   {o['mean_rougeL']:.4f}   "
          f"(median {o['median_rougeL']:.4f}, std {o['std_rougeL']:.4f}, "
          f"min {o['min_rougeL']:.4f}, max {o['max_rougeL']:.4f})")
    print("  (agreement between the two teachers — not quality vs a human gold standard)")

    print("\nPer-split ROUGE-L:")
    for sp, d in per_split.items():
        print(f"  {sp:<11} n={d['n']:<5} mean={d['mean_rougeL']:.4f}  median={d['median_rougeL']:.4f}")

    print("\nDistribution (ROUGE-L histogram):")
    peak = max(hist.values()) or 1
    for label, count in hist.items():
        bar = "#" * int(40 * count / peak)
        print(f"  {label}  {count:>5}  {bar}")

    print(f"\n{args.examples} MOST DIVERGENT (lowest ROUGE-L — teachers disagree most):")
    for e in lowest:
        print(f"  [{e['split']}/{e['index']}] ROUGE-L={e['rougeL']:.4f}")
        print(f"     claude:   {e['claude_output'][:160]}")
        print(f"     nemotron: {e['nemotron_output'][:160]}")

    print(f"\n{args.examples} MOST SIMILAR (highest ROUGE-L — teachers agree most):")
    for e in highest:
        print(f"  [{e['split']}/{e['index']}] ROUGE-L={e['rougeL']:.4f}")

    print(f"\nSaved detailed results to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
