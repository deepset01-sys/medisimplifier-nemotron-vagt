#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Merge filled physician review sheet(s) with the de-blinding key.

Run this once the physicians return their filled copies of physician_review.csv
(each physician fills the four label columns: Safe_or_Unsafe, Category, Note, Confidence).

Usage:
    python scripts/merge_physician_labels.py FILLED1.csv [FILLED2.csv ...] \\
        [--key results/physician_review_KEY.csv] \\
        [--out results/physician_labels_merged.csv]

Output (results/physician_labels_merged.csv):
    orig_index | stratum | source | case_num | safe_or_unsafe | category | note | confidence
(a `rater` column is inserted after case_num when more than one filled sheet is given.)

Also prints:
    - count per category (A/B/C/D/E) across all labels
    - pairwise agreement rate on Safe/Unsafe        (when 2+ raters)
    - pairwise Cohen's kappa on Safe/Unsafe          (when 2+ raters)

Cohen's kappa is computed with no external dependencies.
"""
import csv
import os
import sys
import argparse
import itertools
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def read_key(path):
    key = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            key[str(row["Case#"]).strip()] = {
                "orig_index": row["orig_index"].strip(),
                "stratum": row["stratum"].strip(),
                "source": row["source"].strip(),
            }
    return key


def norm_su(v):
    v = (v or "").strip().lower()
    if v.startswith("s"):
        return "SAFE"
    if v.startswith("u"):
        return "UNSAFE"
    return ""  # unlabeled


def norm_cat(v, su):
    v = (v or "").strip().upper()
    if v[:1] in ("A", "B", "C", "D"):
        return v[:1]
    if su == "SAFE":
        return "E"  # convention: a Safe verdict is category E
    return ""


def read_filled(path):
    labels = {}
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            case = str(row.get("Case #", row.get("Case#", ""))).strip()
            if not case:
                continue
            su = norm_su(row.get("Safe_or_Unsafe"))
            labels[case] = {
                "safe_or_unsafe": su,
                "category": norm_cat(row.get("Category"), su),
                "note": (row.get("Note") or "").strip(),
                "confidence": (row.get("Confidence") or "").strip(),
            }
    return labels


def cohen_kappa(pairs):
    """pairs: list of (label_a, label_b). Returns Cohen's kappa or None if empty."""
    n = len(pairs)
    if n == 0:
        return None
    cats = set()
    for a, b in pairs:
        cats.update((a, b))
    po = sum(1 for a, b in pairs if a == b) / n
    ca = Counter(a for a, _ in pairs)
    cb = Counter(b for _, b in pairs)
    pe = sum((ca[c] / n) * (cb[c] / n) for c in cats)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def main():
    ap = argparse.ArgumentParser(description="Merge filled physician sheets with the de-blinding key.")
    ap.add_argument("filled", nargs="+", help="one or more filled physician_review.csv copies")
    ap.add_argument("--key", default=os.path.join(REPO, "results", "physician_review_KEY.csv"))
    ap.add_argument("--out", default=os.path.join(REPO, "results", "physician_labels_merged.csv"))
    args = ap.parse_args()

    key = read_key(args.key)
    raters = {}
    for p in args.filled:
        name = os.path.splitext(os.path.basename(p))[0]
        raters[name] = read_filled(p)
    multi = len(raters) > 1

    header = ["orig_index", "stratum", "source", "case_num",
              "safe_or_unsafe", "category", "note", "confidence"]
    if multi:
        header.insert(4, "rater")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for case in sorted(key, key=lambda c: int(c)):
            k = key[case]
            for rname, labs in raters.items():
                lab = labs.get(case, {"safe_or_unsafe": "", "category": "", "note": "", "confidence": ""})
                base = [k["orig_index"], k["stratum"], k["source"], case]
                tail = [lab["safe_or_unsafe"], lab["category"], lab["note"], lab["confidence"]]
                w.writerow(base + ([rname] + tail if multi else tail))
    print(f"Wrote {args.out}  ({len(key)} cases x {len(raters)} rater(s))")

    # category counts (A/B/C/D/E) across all labels
    catc = Counter()
    for labs in raters.values():
        for lab in labs.values():
            if lab["category"]:
                catc[lab["category"]] += 1
    print("\nCategory counts (all raters):")
    for c in ("A", "B", "C", "D", "E"):
        print(f"  {c}: {catc.get(c, 0)}")

    # inter-rater agreement + Cohen's kappa on Safe/Unsafe
    if not multi:
        print("\nOnly one rater provided - skipping agreement / Cohen's kappa.")
        return
    names = list(raters.keys())
    print("\nInter-rater agreement on Safe/Unsafe (cases both physicians labeled):")
    for a, b in itertools.combinations(names, 2):
        pairs = []
        for case in key:
            la = raters[a].get(case, {}).get("safe_or_unsafe", "")
            lb = raters[b].get(case, {}).get("safe_or_unsafe", "")
            if la and lb:
                pairs.append((la, lb))
        if not pairs:
            print(f"  {a} vs {b}: no shared labeled cases")
            continue
        agree = sum(1 for x, y in pairs if x == y) / len(pairs)
        kappa = cohen_kappa(pairs)
        print(f"  {a} vs {b}: n={len(pairs)}  agreement={agree:.1%}  Cohen's kappa={kappa:+.3f}")


if __name__ == "__main__":
    main()
