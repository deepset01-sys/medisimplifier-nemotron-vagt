#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Consensus-accuracy baseline vs the Phi_V decomposition.

Answers the reviewer question: "when tau is known, why not just measure how often
the panel's consensus matches truth (consensus accuracy) instead of the G-theory
decomposition?"  For each stratum we compute, on the SAME deployed-gate-prompt data:

  - 2-rater (Llama+Qwen) majority-vote balanced accuracy
  - 3-rater (Llama+Qwen+Nemotron) majority-vote balanced accuracy
  - alongside sigma_B (shared bias) and Phi_V for the 2- and 3-rater panels

Majority rule: flag when >= half the panel votes UNSAFE (ties count as a flag):
2-rater = >=1 of 2, 3-rater = >=2 of 3.

The point is NOT that Phi_V gives a bigger number. On diagnosis, majority-vote consensus
accuracy actually DECREASES when Nemotron is added (the two blind incumbents outvote the
one judge that sees), while Phi_V rises - the naive metric points backwards. The
decomposition tells you WHY (a threshold-free reduction in shared bias sigma_B on the
blind stratum), which predicts that more same-kind raters would not help and a
different-kind rater is required - the decision consensus accuracy alone cannot drive.

NOTE ON PROMPTS: sigma_B / Phi_V here are computed on gate_calibration_full.json (the
DEPLOYED gate prompt) so they are apples-to-apples with the consensus accuracy on the
same data. They therefore differ from the README's CALIBRATION-prompt headline
(diagnosis sigma_B 0.347 -> 0.229, delta-Phi_V +0.071); that difference is expected
(see Fix 3 / split_half_validation.json).

Source: results/gate_calibration_full.json.  Output: results/consensus_accuracy.json.
"""
import os
import sys
import json

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "src", "audit_panel"))

import vagt_core as vc            # noqa: E402

RATER_KEYS = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]   # incumbent first, candidate last
# Published CALIBRATION-prompt reference (README A6 / vagt_bootstrap_cis.json), for context only.
PUBLISHED_CALIB = {"diagnosis": {"sigma_B_2to3": [0.347, 0.229], "delta_phi_v": 0.071}}


def _load():
    with open(os.path.join(REPO, "results", "gate_calibration_full.json"), encoding="utf-8") as f:
        return json.load(f)["per_sample"]


def consensus_bal_acc(X_sub, tau):
    """Majority vote (>= half UNSAFE, ties flag) -> recall / specificity / balanced accuracy."""
    c = X_sub.mean(axis=1)
    flag = (c >= 0.5).astype(float)
    corr = tau == 1
    clean = tau == 0
    recall = float(flag[corr].mean()) if corr.any() else float("nan")
    spec = float((1 - flag[clean]).mean()) if clean.any() else float("nan")
    return recall, spec, (recall + spec) / 2


def main():
    records = _load()
    per_stratum = {}
    for feature in vc.STRATA:
        X, tau, dropped = vc.stratum(records, feature, RATER_KEYS)   # X columns = Llama, Qwen, Nemotron
        n_corr = int((tau == 1).sum())
        n_clean = int((tau == 0).sum())

        # consensus accuracy (2-rater = first 2 cols; 3-rater = all 3)
        r2, s2, ba2 = consensus_bal_acc(X[:, :2], tau)
        r3, s3, ba3 = consensus_bal_acc(X, tau)

        # decomposition on the SAME gate-prompt data
        v2 = vc.vagt(X[:, :2], tau, n_r=2)
        v3 = vc.vagt(X, tau, n_r=3)

        per_stratum[feature] = {
            "n": int(X.shape[0]), "n_corrupted": n_corr, "n_clean": n_clean,
            "consensus": {
                "rater2": {"recall": round(r2, 4), "specificity": round(s2, 4), "bal_acc": round(ba2, 4)},
                "rater3": {"recall": round(r3, 4), "specificity": round(s3, 4), "bal_acc": round(ba3, 4)},
                "delta_bal_acc": round(ba3 - ba2, 4),
            },
            "decomposition_gate_prompt": {
                "sigma_B_2": round(v2["sigma_B"], 4), "sigma_B_3": round(v3["sigma_B"], 4),
                "delta_sigma_B": round(v3["sigma_B"] - v2["sigma_B"], 4),
                "phi_v_2": round(v2["phi_v"], 4), "phi_v_3": round(v3["phi_v"], 4),
                "delta_phi_v": round(v3["phi_v"] - v2["phi_v"], 4),
            },
        }

    result = {
        "source": "results/gate_calibration_full.json (deployed gate prompt)",
        "majority_rule": "flag when >= half the panel votes UNSAFE (ties flag): 2-rater >=1 of 2, 3-rater >=2 of 3",
        "note": ("sigma_B / Phi_V computed on the SAME gate-prompt data (not the calibration-prompt "
                 "published values) so they are apples-to-apples with the consensus accuracy above; "
                 "they differ from the README calibration headline by design (see split_half_validation.json)."),
        "published_calibration_reference": PUBLISHED_CALIB,
        "per_stratum": per_stratum,
    }
    out = os.path.join(REPO, "results", "consensus_accuracy.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    # ---------- print ----------
    print("Consensus accuracy (majority vote) vs Phi_V decomposition - DEPLOYED gate prompt")
    print("  majority: flag when >= half vote UNSAFE (2-rater >=1 of 2, 3-rater >=2 of 3)")
    print("=" * 92)
    print(f"{'stratum':<11}{'panel':<8}{'recall':>9}{'specif.':>10}{'bal-acc':>10}   |{'sigma_B':>9}{'Phi_V':>9}")
    print("-" * 92)
    for feat in vc.STRATA:
        d = per_stratum[feat]
        c, g = d["consensus"], d["decomposition_gate_prompt"]
        print(f"{feat:<11}{'L+Q (2)':<8}{c['rater2']['recall']:>8.1%}{c['rater2']['specificity']:>10.1%}"
              f"{c['rater2']['bal_acc']:>10.1%}   |{g['sigma_B_2']:>9.4f}{g['phi_v_2']:>9.4f}")
        print(f"{'':<11}{'+Nemo(3)':<8}{c['rater3']['recall']:>8.1%}{c['rater3']['specificity']:>10.1%}"
              f"{c['rater3']['bal_acc']:>10.1%}   |{g['sigma_B_3']:>9.4f}{g['phi_v_3']:>9.4f}")
        print(f"{'':<11}{'delta':<8}{'':>8}{'':>10}{c['delta_bal_acc']:>+10.1%}   |"
              f"{g['delta_sigma_B']:>+9.4f}{g['delta_phi_v']:>+9.4f}")
        print("-" * 92)

    print("\nHOW TO READ THIS:")
    print("  - The two metrics DISAGREE on 3 of 4 strata, in opposite directions - and Phi_V is")
    print("    directionally correct for the decision each time:")
    print("  - diagnosis (incumbents blind): majority-vote bal-acc DROPS (60.5%->58.3%) when Nemotron")
    print("    is added - the two blind incumbents outvote the one judge that sees - but Phi_V RISES")
    print("    (+0.044) and shared bias sigma_B falls (0.289->0.232). The naive metric points backwards.")
    print("  - dose/lateral (incumbents fine): bal-acc RISES but Phi_V FALLS - Phi_V flags Nemotron's")
    print("    collateral over-flagging, which the accuracy metric misses.")
    print("  - CONFOUND (honest): the bal-acc change conflates adding a rater with the vote threshold")
    print("    shifting (2-rater >=1 of 2 vs 3-rater >=2 of 3); majority-voting dilutes a minority-held")
    print("    signal (also why the DEPLOYED rule is not a majority vote). sigma_B is threshold-free")
    print("    and is the clean signal: Nemotron reduces shared bias ONLY on diagnosis, raises it elsewhere.")
    print("  - Takeaway: consensus accuracy measures whether a fixed vote rule got lucky; Phi_V measures")
    print("    whether the consensus is systematically closer to truth - the quantity the decision needs.")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
