#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the blinded 50-case physician review sheet + de-blinding key.

Deterministic (seed=42). Reproduces, byte-for-byte, the committed files:
  - results/physician_review.csv       (blinded: Case #1-50, Original, Simplified, 4 empty label cols)
  - results/physician_review_KEY.csv   (de-blinding: Case# -> orig_index / stratum / source)

Sources (all committed):
  - results/student_audit_review.json  6 contested cases (input + prediction text)
  - results/student_audit.json          gate verdicts, used for stratified sampling
  - results/student_predictions.json    input + prediction text for the 44 new cases

Sample = 6 contested + 44 new (20 UNSAFE, 15 DISAGREE, 9 SAFE), shuffled so the
contested cases are not identifiable by position. idx 44 (demo hero) is included.
"""
import json
import csv
import random
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

CONTESTED = [47, 56, 287, 393, 421, 442]
SAMPLE = {"UNSAFE": 20, "DISAGREE": 15, "SAFE": 9}  # dict order fixes the RNG call sequence
SEED = 42


def _load(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as f:
        return json.load(f)


def _clean(t):
    """Strip chat-template artifacts and surrounding whitespace."""
    t = t or ""
    for tok in ("<|im_end|>", "<|endoftext|>"):
        i = t.find(tok)
        if i != -1:
            t = t[:i]
    return t.strip()


def main():
    review = {c["index"]: c for c in _load("results/student_audit_review.json")["cases"]}
    preds = {r["index"]: r for r in _load("results/student_predictions.json")}
    audit = _load("results/student_audit.json")["per_sample"]

    # stratified pools (exclude the contested cases so they are not double-drawn)
    pools = {k: [] for k in SAMPLE}
    for r in audit:
        if r["index"] in CONTESTED:
            continue
        if r["consensus"] in pools:
            pools[r["consensus"]].append(r["index"])

    rng = random.Random(SEED)
    picked = {strat: rng.sample(sorted(pools[strat]), k) for strat, k in SAMPLE.items()}
    assert 44 in picked["DISAGREE"], "idx 44 (demo hero) must be in the DISAGREE sample"

    rows = []
    for idx in CONTESTED:
        c = review[idx]
        rows.append({"orig_index": idx, "stratum": c["consensus"], "src": "contested",
                     "original": _clean(c["input"]), "simplified": _clean(c["prediction"])})
    for strat in ("UNSAFE", "DISAGREE", "SAFE"):
        for idx in sorted(picked[strat]):
            p = preds[idx]
            rows.append({"orig_index": idx, "stratum": strat, "src": "new",
                         "original": _clean(p["input"]), "simplified": _clean(p["prediction"])})
    assert len(rows) == 50, len(rows)

    random.Random(SEED).shuffle(rows)  # independent seed=42 shuffle
    for i, r in enumerate(rows, start=1):
        r["case"] = i

    sheet = os.path.join(REPO, "results", "physician_review.csv")
    with open(sheet, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Case #", "Original", "Simplified", "Safe_or_Unsafe", "Category", "Note", "Confidence"])
        for r in rows:
            w.writerow([r["case"], r["original"], r["simplified"], "", "", "", ""])

    key = os.path.join(REPO, "results", "physician_review_KEY.csv")
    with open(key, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Case#", "orig_index", "stratum", "source"])
        for r in sorted(rows, key=lambda x: x["case"]):
            source = "contested" if r["src"] == "contested" else "new_" + r["stratum"]
            w.writerow([r["case"], r["orig_index"], r["stratum"], source])

    print(f"Wrote {sheet} (50 rows) and {key}")


if __name__ == "__main__":
    main()
