#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix 3 - split-half out-of-sample validation of the deployed gate.

Splits the 708 gate_calibration_full.json items (already scored under the DEPLOYED
one-word gate prompt) into a stratified 50/50 dev/test (seed=42), then:
  - recomputes the B4 5-strategy table on BOTH halves (select on dev, report on test),
  - reports per-stratum recall (Nemotron/Llama/Qwen) on the test half - the gate-prompt
    analogue of the calibration-prompt "68%/14%/7%",
  - reports paired delta-Phi_V(Nemotron | Llama+Qwen) per stratum on the test half.

This converts the deployed rule's operating characteristics and the diagnosis finding
from in-sample to out-of-sample, and - because this file is the gate prompt - also
addresses the "calibration prompt != gate prompt" critique. Same math as vagt_core
(SEED=42, no new estimators).

Output: prints dev-vs-test tables + writes results/split_half_validation.json.
"""
import os
import sys
import json
import random
from collections import defaultdict

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src", "audit_panel"))

import vagt_core as vc            # noqa: E402

SEED = 42
N_BOOT = 1000
INCUMBENT_KEYS = ["llama_verdict", "qwen_verdict"]
CANDIDATE_KEY = "nemotron_verdict"
STRATEGIES = ["nemotron_only", "qwen_only", "llama_only", "majority_2of3", "deployed"]


def _load():
    with open(os.path.join(REPO, "results", "gate_calibration_full.json"), encoding="utf-8") as f:
        return json.load(f)["per_sample"]


# ---- deployed rule (safety_gate.py; Llama advisory, not in the rule) ----
def deployed_consensus(nemo, qwen):
    if nemo == "SAFE" and qwen == "SAFE":
        return "SAFE"
    if nemo == "UNSAFE" and qwen == "UNSAFE":
        return "UNSAFE"
    if qwen == "UNSAFE":            # nemo SAFE + qwen UNSAFE -> trust Qwen specificity
        return "UNSAFE"
    if nemo == "UNSAFE" and qwen == "SAFE":
        return "DISAGREE"
    return "SAFE"


def flagged(r, strat):
    """Does `strat` raise a flag on record r? (flag = catch, incl. DISAGREE for deployed)."""
    n, q, l = r["nemotron_verdict"], r["qwen_verdict"], r["llama_verdict"]
    if strat == "nemotron_only":
        return n == "UNSAFE"
    if strat == "qwen_only":
        return q == "UNSAFE"
    if strat == "llama_only":
        return l == "UNSAFE"
    if strat == "majority_2of3":
        return [n, q, l].count("UNSAFE") >= 2
    if strat == "deployed":
        return deployed_consensus(n, q) in ("UNSAFE", "DISAGREE")
    raise ValueError(strat)


# ---- stratified 50/50 split (seed=42) ----
def split_dev_test(records):
    groups = defaultdict(list)
    for i, r in enumerate(records):
        groups[(r["error_type"], r["condition"])].append(i)
    rng = random.Random(SEED)
    dev_i, test_i = [], []
    for key in sorted(groups):
        idxs = groups[key][:]
        rng.shuffle(idxs)
        half = len(idxs) // 2
        dev_i += idxs[:half]
        test_i += idxs[half:]
    dev = [records[i] for i in sorted(dev_i)]
    test = [records[i] for i in sorted(test_i)]
    return dev, test


def composition(records):
    c = defaultdict(int)
    for r in records:
        c[f"{r['error_type']}/{r['condition']}"] += 1
    return dict(sorted(c.items()))


# ---- B4 5-strategy metrics on a set of records ----
def strategy_metrics(records, strat):
    corr = [r for r in records if r["condition"] == "corrupted"]
    clean = [r for r in records if r["condition"] == "clean"]
    tp = sum(1 for r in corr if flagged(r, strat))
    fp = sum(1 for r in clean if flagged(r, strat))
    recall = tp / len(corr) if corr else float("nan")
    fpr = fp / len(clean) if clean else float("nan")
    flag_rate = sum(1 for r in records if flagged(r, strat)) / len(records)
    bal_acc = (recall + (1 - fpr)) / 2
    return {"n_corr": len(corr), "n_clean": len(clean),
            "recall": round(recall, 4), "fp": round(fpr, 4),
            "flag_rate": round(flag_rate, 4), "bal_acc": round(bal_acc, 4)}


def b4_table(records):
    return {s: strategy_metrics(records, s) for s in STRATEGIES}


# ---- per-stratum per-judge recall (test half) ----
def per_stratum_recall(records):
    out = {}
    for feature in vc.STRATA:
        corr = [r for r in records if r["condition"] == "corrupted" and r["error_type"] == feature]
        row = {"n_corrupted": len(corr)}
        for label, key in (("nemotron", CANDIDATE_KEY), ("llama", "llama_verdict"), ("qwen", "qwen_verdict")):
            row[label] = round(sum(1 for r in corr if r[key] == "UNSAFE") / len(corr), 4) if corr else None
        out[feature] = row
    return out


# ---- delta-Phi_V(Nemotron | Llama+Qwen) per stratum (test half) ----
def delta_phi_v(records):
    keys = INCUMBENT_KEYS + [CANDIDATE_KEY]
    out = {}
    for feature in vc.STRATA:
        X, tau, dropped = vc.stratum(records, feature, keys)
        rng = np.random.default_rng(SEED)
        point, cis = vc.paired_delta_cis(X, tau, n_incumbent=len(INCUMBENT_KEYS), rng=rng, n_boot=N_BOOT)
        lo, hi = cis["phi_v"]
        out[feature] = {"n": int(X.shape[0]), "dropped": int(dropped),
                        "delta_phi_v": round(float(point["phi_v"]), 4),
                        "ci_95": [round(float(lo), 4), round(float(hi), 4)],
                        "ci_width": round(float(hi - lo), 4)}
    return out


CAVEATS = [
    "Single stratified 50/50 split (seed=42), NOT k-fold - a directional out-of-sample check, not a precise re-estimate.",
    "Test-half recall carries Wilson +/-~6-11%; dose (~47) and negation (~56) corrupted counts make their delta-Phi_V CIs wide - report, do not over-read.",
    "This is the DEPLOYED gate prompt: per-stratum recall here will differ from the calibration-prompt headline (68%/14%/7%); Llama's gate-prompt recall is higher, so the incumbent blind spot may look less dramatic - that is the honest deployed number.",
]


def main():
    records = _load()

    # correctness: our deployed rule must reproduce the committed consensus field
    mism = [r["idx"] for r in records if deployed_consensus(r["nemotron_verdict"], r["qwen_verdict"]) != r["consensus"]]
    if mism:
        raise SystemExit(f"deployed_consensus disagrees with committed consensus on {len(mism)} items: {mism[:10]}")
    print(f"deployed-rule check: reproduces committed consensus on all {len(records)} items OK\n")

    dev, test = split_dev_test(records)
    result = {
        "seed": SEED, "n_bootstrap": N_BOOT,
        "prompt_source": "deployed gate prompt (safety_gate.py JUDGE_PROMPT)",
        "split": {"dev_n": len(dev), "test_n": len(test),
                  "dev_composition": composition(dev), "test_composition": composition(test)},
        "b4_strategies": {"dev": b4_table(dev), "test": b4_table(test)},
        "per_stratum_recall_test": per_stratum_recall(test),
        "delta_phi_v_test": delta_phi_v(test),
        "caveats": CAVEATS,
    }

    out = os.path.join(REPO, "results", "split_half_validation.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # ---------- print ----------
    print(f"Split-half validation (deployed gate prompt, seed={SEED}, boot={N_BOOT})")
    print(f"  dev n={len(dev)}   test n={len(test)}")
    print("=" * 84)
    print("B4 5-STRATEGY TABLE - dev vs test  (recall on corrupted | FP on clean)")
    print(f"{'strategy':<16}{'':4}{'recall':>10}{'FP':>10}{'flag-rate':>12}{'bal-acc':>10}")
    for s in STRATEGIES:
        dv, ts = result["b4_strategies"]["dev"][s], result["b4_strategies"]["test"][s]
        print(f"{s:<16}dev {dv['recall']:>9.1%}{dv['fp']:>10.1%}{dv['flag_rate']:>12.1%}{dv['bal_acc']:>10.1%}")
        print(f"{'':<16}tst {ts['recall']:>9.1%}{ts['fp']:>10.1%}{ts['flag_rate']:>12.1%}{ts['bal_acc']:>10.1%}")
        print("-" * 84)

    print("\nPER-STRATUM RECALL - TEST half (gate prompt; cf. calibration 68%/14%/7% on diagnosis):")
    print(f"{'stratum':<12}{'n':>5}{'Nemotron':>12}{'Llama':>10}{'Qwen':>10}")
    for feat in vc.STRATA:
        r = result["per_stratum_recall_test"][feat]
        def pct(x):
            return f"{x:.1%}" if x is not None else "-"
        print(f"{feat:<12}{r['n_corrupted']:>5}{pct(r['nemotron']):>12}{pct(r['llama']):>10}{pct(r['qwen']):>10}")

    print("\ndelta-Phi_V(Nemotron | Llama+Qwen) - TEST half (out-of-sample, gate prompt):")
    print(f"{'stratum':<12}{'n':>5}{'dPhi_V':>10}{'95% CI':>22}{'width':>9}  sig")
    for feat in vc.STRATA:
        d = result["delta_phi_v_test"][feat]
        lo, hi = d["ci_95"]
        sig = "  *" if (lo > 0 or hi < 0) else "  ."
        print(f"{feat:<12}{d['n']:>5}{d['delta_phi_v']:>+10.4f}   [{lo:+.4f}, {hi:+.4f}]{d['ci_width']:>9.4f}{sig}")
    print("*  CI excludes 0    .  straddles 0")

    print("\nCAVEATS:")
    for c in CAVEATS:
        print(f"  - {c}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
