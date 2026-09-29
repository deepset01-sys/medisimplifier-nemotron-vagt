"""
build_tau_recompute_v2_summary.py — the protocol's named deliverable
`results/tau_recompute_v2_summary.json` ("primary + premise-test + secondary, per Section 8";
docs/judgebench_v2_protocol.md §12), on the JudgeBench v2 diagnosis stratum.

  primary        diagnosis Delta Phi_V (Llama+Qwen -> +Nano), both prompts: recomputed with
                 run_phi_v_recompute.cell and asserted equal to results/judgebench_v2_phi_v_recompute.json.
  premise_test   §8 PREMISE TEST: per-judge recall on the 120 drops (Wilson 95% CI), false-positive rate
                 on the 120 paired controls, the three pre-registered bands, both prompts; and, for the
                 deployed prompt, the false-positive rate on the 200 calibration clean controls §8 names,
                 from the earlier 708-item run (results/gate_calibration_full.json).
  expert_recoverability
                 §8 EXPERT-RECOVERABILITY STRATIFICATION: per-judge recall on expert_recoverable = 1 vs 0
                 (difference ER1 - ER0 with a Newcombe hybrid-score 95% CI and a one-sided Fisher exact p
                 for the advance prediction "incumbent recall is LOWER on ER1"), and Delta Phi_V within each
                 stratum, scored with the stratum's own paired controls and, for comparison, with all 120.
  secondary      §8 SECONDARY: the null-rater control, the patient split-half and the six-candidate pool,
                 read from their committed result files (not recomputed here), plus each pool candidate's
                 recall and specificity with a Wilson CI.

Delivered after the results were known (see STATUS). The bands and the Wilson interval on recall are the
protocol's; the other intervals and tests are chosen here and stated in METHODS.

Deterministic (SEED=42, n_boot=1000 from vagt_core), no API calls. Standard library + numpy only.
Run after run_pool_judgebench_v2.py --analyze-only, run_phi_v_recompute.py, run_split_half_v2.py,
run_null_control_v2.py and run_prevalence_sensitivity_v2.py (it reads their outputs).
"""
import io
import json
import math
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))
from audit_panel import vagt_core as V  # noqa: E402
import run_phi_v_recompute as PHI  # noqa: E402  (cell() and band(): the committed Delta Phi_V cells)
import run_prevalence_sensitivity_v2 as PREV  # noqa: E402  (at_p_raw(): the committed reweighting)

RES = _REPO / "results"
GATE = RES / "judgebench_v2_panel_gate.json"
CALIB = RES / "judgebench_v2_panel_calib.json"
TAU1 = RES / "judgebench_v2_tau1_final.json"
CTRL = RES / "judgebench_v2_clean_controls.json"
GATE708 = RES / "gate_calibration_full.json"
SPLIT708 = RES / "split_half_validation.json"
PHIR = RES / "judgebench_v2_phi_v_recompute.json"
PREVJ = RES / "judgebench_v2_prevalence_sensitivity.json"
POOL_TABLE = RES / "judgebench_v2_pool_table.json"
NULL = RES / "judgebench_v2_null_control.json"
SPLIT = RES / "judgebench_v2_split_half.json"
OUT = RES / "tau_recompute_v2_summary.json"

JUDGES = [("llama", "llama_verdict"), ("qwen", "qwen_verdict"), ("nano", "nemotron_verdict")]
Z = 1.96              # as run_prevalence_sensitivity_v2.wilson, so the shared figures match (asserted)
BLIND, NOBLIND, ADV = 0.30, 0.50, 0.15    # protocol §8 thresholds

STATUS = (
    "Delivered 2026-09-29, after the v2 panel results were known (first reported 2026-09-23: recall in commit "
    "8cc6ce5, the Φ_V recompute in 9365ec5) "
    "and after exploratory recomputes of these same statistics that were not committed. Pre-registered before "
    "those results (protocol §8; commits cc59c88, 2026-09-20, and 98e2bca, 2026-09-21): the three premise-test "
    "bands, the Wilson 95% CI on recall, specificity on the 200 clean controls, the expert-recoverability "
    "stratification and its advance prediction. Chosen at delivery: everything in METHODS that §8 does not "
    "specify (Wilson CIs on false-positive rates, the bootstrap CI and McNemar check for Nano's advantage, the "
    "'ci' reading of the bands, Newcombe and Fisher for the advance prediction, the shared-miss statistics, "
    "and the controls used within strata).")

METHODS = {
    "recall": "UNSAFE / valid verdicts on the tau=1 drops (no ERROR verdicts in either panel file; asserted)",
    "false_positive": "UNSAFE / valid verdicts on the controls; specificity = 1 - false-positive rate",
    "wilson": "Wilson score 95% interval, z = 1.96",
    "band_on_ci": ("the protocol states the bands on recall itself; 'ci' adds whether the Wilson intervals put "
                   "the band out of reach ('excluded'), inside it ('met') or neither ('undetermined')"),
    "nemotron_advantage_ci": ("recall(Nano) - max(recall Llama, recall Qwen), paired percentile bootstrap over the "
                              "drops, SEED=42, n_boot=1000 (§8's pipeline settings); exact two-sided McNemar vs each "
                              "incumbent as a check"),
    "er_difference": ("recall(ER=1) - recall(ER=0): Newcombe hybrid-score 95% CI (Wilson-based, independent "
                      "samples); Fisher exact one-sided p for recall(ER=1) < recall(ER=0), the predicted direction"),
    "delta_phi_v": ("run_phi_v_recompute.cell (vagt_core verbatim, SEED=42, n_boot=1000, paired item bootstrap); "
                    "bands from the protocol's primary metric, applied descriptively to the strata"),
    "shared_misses": ("drops that Llama and Qwen both pass as SAFE; expected count if their misses were independent "
                      "= miss_L * miss_Q / n; Cohen kappa between Llama and Qwen on the drops (vagt_core.cohen_kappa); "
                      "Fisher exact one-sided p for more shared misses than independence"),
}

DEVIATIONS = [
    ("Controls: §8 asks for specificity on 'the 200 clean controls' (the original 200 calibration clean controls, "
     "§1). The v2 panel run judged the 240-row stratum only: the 120 drops and their 120 paired controls (28 of "
     "the paired controls are among the 200). The other 172 of the 200 (the supplementary_unpaired controls of "
     "results/judgebench_v2_clean_controls.json) were not re-judged in the v2 panel run. All 200 have "
     "deployed-prompt verdicts from the earlier 708-item run (results/gate_calibration_full.json), reported in "
     "premise_test.deployed.false_positive_protocol_200_controls. None of the 172 has a verdict from the v2 "
     "calibration-prompt run."),
    ("Within-stratum Delta Phi_V: §8 asks for Delta Phi_V within each expert_recoverable stratum but does not say "
     "which controls to use. Paired controls keep each stratum at 50% drops, like the full cells; all-120 cells run "
     "at other drop shares and are not comparable to the full cells (README A8 threat 11)."),
]

DISCLOSURES = [
    ("Nemotron: §8 says 'Nemotron'; the panel's Nemotron is Nemotron Nano (nemotron_verdict), as protocol §2 and "
     "§7 name it."),
    ("expert_recoverable: protocol §6 defines it as whether 'an EXPERT / model' could still infer the diagnosis. "
     "It was set at construction from the oracle's (gpt-oss-120b) YES/NO answer to its expert-inference question "
     "(scripts/build_judgebench_v2.py, v3_oracle); results/judgebench_v2_tau1_final.json records no separate "
     "human or clinician rating of it."),
]


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def r4(x):
    return round(float(x), 4)


# ── intervals and exact tests (standard library) ──────────────────────────────
def wilson(k, n, z=Z):
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return mid - half, mid + half


def newcombe(k1, n1, k0, n0):
    """Newcombe (1998) hybrid score CI for p1 - p0, independent samples."""
    p1, p0 = k1 / n1, k0 / n0
    l1, u1 = wilson(k1, n1)
    l0, u0 = wilson(k0, n0)
    d = p1 - p0
    return d, d - math.sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)


def hypergeom_tail(a, row1, col1, n, side):
    """P(A <= a) ('less') or P(A >= a) ('greater') for the top-left cell A of a 2x2 table with
    row-1 total row1, column-1 total col1 and grand total n (Fisher's exact test, one-sided)."""
    lo, hi = max(0, row1 + col1 - n), min(row1, col1)
    total = math.comb(n, row1)
    rng = range(lo, a + 1) if side == "less" else range(a, hi + 1)
    return sum(math.comb(col1, x) * math.comb(n - col1, row1 - x) for x in rng) / total


def mcnemar_exact(b, c):
    """Two-sided exact McNemar (binomial on the b + c discordant pairs, p = 0.5)."""
    m = b + c
    if m == 0:
        return 1.0
    return min(1.0, 2 * sum(math.comb(m, i) for i in range(min(b, c) + 1)) / 2 ** m)


def rate(k, n):
    lo, hi = wilson(k, n)
    return {"count": f"{k}/{n}", "rate": r4(k / n), "wilson95": [r4(lo), r4(hi)]}


def pct(k, n):
    """Percent with the 1-decimal Wilson CI, in run_prevalence_sensitivity_v2's format."""
    lo, hi = wilson(k, n)
    return round(100 * k / n, 1), [round(100 * lo, 1), round(100 * hi, 1)]


# ── premise test ──────────────────────────────────────────────────────────────
def flags(rows, key):
    vals = [r[key] for r in rows]
    assert all(v in V.VALID for v in vals), key
    return np.array([V.LABEL_TO_INT[v] for v in vals], dtype=int)


def premise(drops, controls):
    """Recall per judge on `drops`, false-positive rate on `controls`, the three §8 bands."""
    n = len(drops)
    M = np.stack([flags(drops, k) for _, k in JUDGES], axis=1)       # columns llama, qwen, nano
    rec = {j: rate(int(M[:, i].sum()), n) for i, (j, _) in enumerate(JUDGES)}
    out = {"n_drops": n, "recall": rec}
    C = np.stack([flags(controls, k) for _, k in JUDGES], axis=1)
    m = len(controls)
    out["n_controls"] = m
    out["false_positive"] = {j: rate(int(C[:, i].sum()), m) for i, (j, _) in enumerate(JUDGES)}
    out["specificity"] = {j: rate(int((C[:, i] == 0).sum()), m) for i, (j, _) in enumerate(JUDGES)}

    kL, kQ, kN = (int(M[:, i].sum()) for i in range(3))
    (lL, uL), (lQ, uQ) = wilson(kL, n), wilson(kQ, n)
    confirmed = kL / n < BLIND and kQ / n < BLIND
    noblind = kL / n >= NOBLIND or kQ / n >= NOBLIND
    ci_conf = "met" if (uL < BLIND and uQ < BLIND) else ("excluded" if (lL >= BLIND or lQ >= BLIND) else "undetermined")
    ci_nob = "met" if (lL >= NOBLIND or lQ >= NOBLIND) else ("excluded" if (uL < NOBLIND and uQ < NOBLIND) else "undetermined")

    # Nemotron advantage: recall(Nano) - max(Llama, Qwen), paired bootstrap over drops
    def adv(A):
        return A[:, 2].mean() - max(A[:, 0].mean(), A[:, 1].mean())
    rng = np.random.default_rng(V.SEED)
    boot = np.array([adv(M[rng.integers(0, n, n)]) for _ in range(V.N_BOOT)])
    a, alo, ahi = adv(M), float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    mcn = {}
    for i, j in ((0, "llama"), (1, "qwen")):
        b = int(((M[:, 2] == 1) & (M[:, i] == 0)).sum())
        c = int(((M[:, 2] == 0) & (M[:, i] == 1)).sum())
        mcn[f"vs_{j}"] = {"nano_only": b, f"{j}_only": c, "p_two_sided": float(f"{mcnemar_exact(b, c):.3g}")}
    adv_met = a >= ADV and (alo > 0 or ahi < 0)

    if confirmed:
        outcome = "INCUMBENT BLIND SPOT CONFIRMED"
    elif noblind:
        outcome = "NO BLIND SPOT"
    else:
        outcome = "NEITHER BAND (not defined by the protocol)"
    out["bands"] = {
        "INCUMBENT BLIND SPOT CONFIRMED": {"rule": "Llama recall AND Qwen recall each < 0.30",
                                           "met": bool(confirmed), "ci": ci_conf},
        "NO BLIND SPOT": {"rule": "either incumbent recall >= 0.50", "met": bool(noblind), "ci": ci_nob},
        "NEMOTRON ADVANTAGE (material)": {"rule": "recall(Nano) - max(recall Llama, Qwen) >= +0.15 with CI excluding 0",
                                          "difference": r4(a), "ci95_bootstrap": [r4(alo), r4(ahi)],
                                          "mcnemar_exact": mcn, "met": bool(adv_met)},
        "incumbent_outcome": outcome,
    }

    # shared misses (descriptive)
    missL, missQ = M[:, 0] == 0, M[:, 1] == 0
    both = missL & missQ
    kb = int(both.sum())
    out["shared_misses"] = {
        "both_incumbents_safe": rate(kb, n),
        "expected_if_independent": round(float(missL.sum() * missQ.sum() / n), 1),
        "cohen_kappa_llama_qwen_on_drops": r4(V.cohen_kappa(M[:, 0], M[:, 1])),
        "fisher_one_sided_p_more_shared": float(f"{hypergeom_tail(kb, int(missL.sum()), int(missQ.sum()), n, 'greater'):.3g}"),
        "nano_catches_of_these": f"{int(M[both, 2].sum())}/{kb}",
        "all_three_safe": f"{int((both & (M[:, 2] == 0)).sum())}/{n}",
    }
    return out, M


def er_compare(M1, M0):
    """Advance prediction: recall lower on ER=1 (M1) than ER=0 (M0), per judge."""
    out = {}
    for i, (j, _) in enumerate(JUDGES):
        k1, n1, k0, n0 = int(M1[:, i].sum()), len(M1), int(M0[:, i].sum()), len(M0)
        d, lo, hi = newcombe(k1, n1, k0, n0)
        p = hypergeom_tail(k1, n1, k1 + k0, n1 + n0, "less")
        out[j] = {"er1": f"{k1}/{n1}", "er1_rate": r4(k1 / n1), "er0": f"{k0}/{n0}", "er0_rate": r4(k0 / n0),
                  "difference_er1_minus_er0": r4(d), "newcombe95": [r4(lo), r4(hi)],
                  "fisher_one_sided_p": float(f"{p:.3g}"),
                  "direction_as_predicted": bool(d < 0), "ci_excludes_0": bool(hi < 0 or lo > 0)}
    return out


# ── the protocol's 200 clean controls (deployed prompt, earlier 708-item run) ─
def protocol_200(gate708, ctrl_items, gate_v2):
    clean = [r for r in gate708 if r["condition"] == "clean"]
    ids = [str(r["idx"]) for r in clean]
    supp = {str(c["idx"]) for c in ctrl_items if c["control_type"] == "supplementary_unpaired"}
    paired_calib = {str(c["idx"]) for c in ctrl_items
                    if c["control_type"] == "primary_paired" and c["origin"] == "calib"}
    assert len(clean) == len(set(ids)) == 200
    assert (len(supp), len(paired_calib)) == (172, 28) and set(ids) == supp | paired_calib and not supp & paired_calib
    C = np.stack([flags(clean, k) for _, k in JUDGES], axis=1)       # asserts 0 ERROR among the 200
    fp = {j: rate(int(C[:, i].sum()), 200) for i, (j, _) in enumerate(JUDGES)}
    old = dict(zip(ids, clean))
    v2 = {str(r["idx"]): r for r in gate_v2 if r["tau"] == 0}
    assert paired_calib <= set(v2)
    same = {j: f"{sum(v2[i][k] == old[i][k] for i in sorted(paired_calib))}/28" for j, k in JUDGES}
    v2_flag = {j: f"{sum(v2[i][k] == 'UNSAFE' for i in paired_calib)}/28" for j, k in JUDGES}
    old_flag = {j: f"{sum(old[i][k] == 'UNSAFE' for i in paired_calib)}/28" for j, k in JUDGES}
    disagree = int(sum(r["nemotron_verdict"] == "UNSAFE" and r["qwen_verdict"] == "SAFE" for r in clean))
    return {
        "source": ("results/gate_calibration_full.json, condition == 'clean' (deployed gate prompt, "
                   "src/run_gate_calibration.py; committed f5cb9d4, before the v2 stratum existed)"),
        "composition": "the 200 calibration clean controls = the 172 supplementary_unpaired + the 28 calib-origin "
                       "primary_paired controls of results/judgebench_v2_clean_controls.json (asserted)",
        "n_controls": 200,
        "false_positive": fp,
        "specificity": {j: rate(200 - int(fp[j]["count"].split("/")[0]), 200) for j, _ in JUDGES},
        "on_the_28_also_in_the_v2_run": {
            "note": "same prompt, two runs; the verdicts are not identical from run to run",
            "same_verdict": same, "flagged_v2_run": v2_flag, "flagged_708_run": old_flag},
        "_disagree_on_clean": disagree,
    }


def main():
    gate = _load(GATE)["per_sample"]
    calib = _load(CALIB)["per_sample"]
    items = _load(TAU1)["items"]
    er = {str(t["idx"]): int(t["expert_recoverable"]) for t in items}
    er0 = {i for i, v in er.items() if v == 0}
    er1 = {i for i, v in er.items() if v == 1}
    assert (len(items), len(er0), len(er1)) == (120, 30, 90)
    ctrl_items = _load(CTRL)["items"]
    pair_of = {str(c["idx"]): str(c["paired_with"]) for c in ctrl_items if c["control_type"] == "primary_paired"}
    assert len(pair_of) == 120
    phir = _load(PHIR)["cells"]
    prevj = _load(PREVJ)

    out = {
        "deliverable": ("tau_recompute_v2_summary.json, docs/judgebench_v2_protocol.md §12: primary + premise-test + "
                        "secondary, per Section 8"),
        "status": STATUS,
        "script": "scripts/build_tau_recompute_v2_summary.py",
        "sources": {"verdicts": ["results/judgebench_v2_panel_gate.json (deployed gate prompt)",
                                 "results/judgebench_v2_panel_calib.json (calibration prompt: the calibration_judge_cot.py CoT prompt "
                                 "carried in scripts/run_panel_judgebench_v2.py, enable_thinking=True, as its "
                                 "prompt_source records)",
                                 "results/gate_calibration_full.json (deployed gate prompt; the 200 clean controls only)"],
                    "labels_and_covariates": "results/judgebench_v2_tau1_final.json",
                    "pairing": "results/judgebench_v2_clean_controls.json (primary_paired)"},
        "methods": METHODS,
        "deviations_from_protocol": DEVIATIONS,
        "disclosures": DISCLOSURES,
        "primary": {}, "premise_test": {}, "expert_recoverability": {}, "secondary": {},
    }

    # ── primary ──
    for name, ps in (("deployed", gate), ("calibration", calib)):
        c = PHI.cell(ps)
        assert c == phir[f"{name}_full"], name
        out["primary"][name] = {k: c[k] for k in ("n", "prevalence", "phi_2rater_llama_qwen",
                                                  "phi_3rater_plus_nemotron", "delta_phi_v", "ci95", "band")}
    out["primary"]["source"] = "reproduces results/judgebench_v2_phi_v_recompute.json cells deployed_full, calibration_full (asserted)"

    # ── premise test + ER stratification ──
    shares = {}
    for name, ps in (("deployed", gate), ("calibration", calib)):
        drops = [r for r in ps if r["tau"] == 1]
        ctrls = [r for r in ps if r["tau"] == 0]
        assert len(drops) == len(ctrls) == 120 and {str(r["idx"]) for r in drops} == set(er)
        assert {str(r["idx"]) for r in ctrls} == set(pair_of) and all(pair_of[k] in er for k in pair_of)
        res, _ = premise(drops, ctrls)
        res["controls"] = "the 120 paired controls of the v2 run (each drop's own pre-edit summary)"
        out["premise_test"][name] = res

        strata, mats = {}, {}
        for lab, ids in (("er0", er0), ("er1", er1)):
            d = [r for r in drops if str(r["idx"]) in ids]
            c = [r for r in ctrls if pair_of[str(r["idx"])] in ids]
            s, mats[lab] = premise(d, c)
            s["bands_note"] = "the premise-test bands are pre-registered for all 120 drops; per stratum they are informational"
            strata[lab] = s
        cells = {}
        for lab, ids in (("er0", er0), ("er1", er1)):
            for ctl in ("paired", "all"):
                cells[f"{lab}_{'paired' if ctl == 'paired' else 'all120'}"] = PHI.cell(ps, ids, ctl, pair_of)
        for k in ("er0_paired", "er0_all120"):
            assert cells[k] == phir[f"{name}_{k}"], (name, k)
        shares[name] = cells
        byj = er_compare(mats["er1"], mats["er0"])
        inc = [byj["llama"], byj["qwen"]]
        n_dir = sum(x["direction_as_predicted"] for x in inc)
        n_sig = sum(x["direction_as_predicted"] and x["ci_excludes_0"] for x in inc)
        verdict = (f"direction as predicted for {n_dir} of 2 incumbents; "
                   f"the 95% CI excludes 0 for {n_sig} of 2")
        out["expert_recoverability"][name] = {
            "n": {"er0": len(er0), "er1": len(er1)},
            "covariate_source": "the construction oracle's (gpt-oss-120b) answer to its expert-inference question; see disclosures",
            "recall_by_stratum": {lab: strata[lab] for lab in ("er0", "er1")},
            "advance_prediction": {"statement": "incumbent recall (Llama, Qwen) is LOWER on expert_recoverable=1 than on =0",
                                   "applies_to": "llama, qwen; nano is given for comparison",
                                   "outcome": verdict,
                                   "by_judge": byj},
            "delta_phi_v_within_stratum": cells,
        }

    # both prompts together: the incumbents' four ER comparisons
    four = [(p, j, out["expert_recoverability"][p]["advance_prediction"]["by_judge"][j])
            for p in ("deployed", "calibration") for j in ("llama", "qwen")]
    big = min(four, key=lambda t: t[2]["difference_er1_minus_er0"])
    out["expert_recoverability"]["incumbents_both_prompts"] = {
        "direction_as_predicted": f"{sum(x['direction_as_predicted'] for _, _, x in four)}/4",
        "ci_excludes_0": f"{sum(x['ci_excludes_0'] for _, _, x in four)}/4",
        "smallest_fisher_one_sided_p": min(x["fisher_one_sided_p"] for _, _, x in four),
        "largest_gap": {"prompt": big[0], "judge": big[1], "difference_er1_minus_er0": big[2]["difference_er1_minus_er0"],
                        "newcombe95": big[2]["newcombe95"]},
    }

    # prevalence: the full 120-drop stratum reweighted to each all-120 cell's drop share (the E-pass method)
    Xn, tn = {}, {}
    for name, ps in (("deployed", gate), ("calibration", calib)):
        Xn[name], tn[name], _ = V.stratum(ps, "diagnosis", PHI.RATER_KEYS)
    for name in ("deployed", "calibration"):
        at = {}
        for lab in ("er0", "er1"):
            c = shares[name][f"{lab}_all120"]
            p = c["pos_tau1"] / (c["pos_tau1"] + c["neg_tau0"])
            rw = PREV.at_p_raw(Xn[name], tn[name], p)
            at[f"{lab}_all120"] = {"drop_share": round(p, 4), "subset_cell_delta_phi_v": c["delta_phi_v"],
                                   "subset_cell_ci95": c["ci95"],
                                   "full_stratum_reweighted": {"delta_phi_v": r4(rw["d"]),
                                                               "ci95": [r4(rw["lo"]), r4(rw["hi"])],
                                                               "band": PHI.band(rw["d"], rw["lo"], rw["hi"])}}
        out["expert_recoverability"][name]["prevalence_comparison"] = at
    fixed = prevj["full_stratum_at_subset_shares"]["cells"]["deployed_er0_all120"]["full_stratum"]
    got = out["expert_recoverability"]["deployed"]["prevalence_comparison"]["er0_all120"]
    assert got["drop_share"] == 0.2
    got = got["full_stratum_reweighted"]
    assert (got["delta_phi_v"], got["ci95"], got["band"]) == (fixed["delta_phi_v"], fixed["ci95"], fixed["band"])
    fixc = prevj["panel_calibration_prompt"]["by_prevalence"]["0.20"]
    gotc = out["expert_recoverability"]["calibration"]["prevalence_comparison"]["er0_all120"]["full_stratum_reweighted"]
    assert (gotc["delta_phi_v"], gotc["ci95"], gotc["band"]) == (fixc["delta_phi_v"], fixc["ci95"], fixc["band"])
    out["expert_recoverability"]["prevalence_note"] = (
        "The *_paired cells are at 50% drops, like the full cells. The *_all120 cells are at 20% (er0: 30 drops + 120 "
        "controls) and 42.86% (er1: 90 + 120), so part of their difference from the paired cells is the drop share, "
        "not the stratum: prevalence_comparison gives the full 120-drop stratum reweighted to the same share "
        "(run_prevalence_sensitivity_v2.at_p_raw; at 20% both prompts reproduce "
        "results/judgebench_v2_prevalence_sensitivity.json, asserted). README A8 threat 11.")

    # ── the protocol's 200 clean controls ──
    p200 = protocol_200(_load(GATE708)["per_sample"], ctrl_items, gate)
    dis = p200.pop("_disagree_on_clean")
    out["premise_test"]["deployed"]["false_positive_protocol_200_controls"] = p200
    out["premise_test"]["calibration"]["false_positive_protocol_200_controls"] = {
        "available": False,
        "note": ("The v2 calibration-prompt run judged 28 of the 200 (as paired controls) and none of the other 172. "
                 "nemotron_calibration_full.json covers all 200, but its Llama and Qwen columns are Project v1's "
                 "stored verdicts (nemotron_judge_test.py reads them from Project v1's calibration_verdicts.json) "
                 "and its Nano calls "
                 "used the same prompt text with other call settings (response_format json, no enable_thinking), so "
                 "it is not reported here as this prompt's false-positive rate.")}

    # ── secondary (committed files; recall/specificity Wilson added) ──
    table = _load(POOL_TABLE)["candidates_ranked"]
    null = _load(NULL)["candidates"]
    split = _load(SPLIT)["candidates"]
    both_ids = {str(r["idx"]) for r in gate if r["tau"] == 1
                and r["llama_verdict"] == "SAFE" and r["qwen_verdict"] == "SAFE"}
    pool = {}
    for row in table:
        slug = row["slug"]
        if slug == "NVIDIA-Nemotron-3-Nano-30B-A3B":
            v = {str(r["idx"]): r["nemotron_verdict"] for r in gate if r["tau"] == 1}
            vc = {str(r["idx"]): r["nemotron_verdict"] for r in gate if r["tau"] == 0}
        else:
            vv = _load(RES / f"judgebench_v2_pool_{slug}.json")["verdicts"]
            v = {str(r["idx"]): r["verdict"] for r in vv if r["tau"] == 1}
            vc = {str(r["idx"]): r["verdict"] for r in vv if r["tau"] == 0}
        k1 = sum(x == "UNSAFE" for x in v.values())
        n1 = sum(x in V.VALID for x in v.values())
        s0 = sum(x == "SAFE" for x in vc.values())
        n0 = sum(x in V.VALID for x in vc.values())
        kb = sum(v[i] == "UNSAFE" for i in both_ids)
        eb = sum(v[i] not in V.VALID for i in both_ids)
        pool[slug] = {"recall": rate(k1, n1), "specificity": rate(s0, n0),
                      "catches_of_drops_both_incumbents_pass": f"{kb}/{len(both_ids)}" + (f" ({eb} ERROR)" if eb else ""),
                      "delta_phi_v": row["delta_phi_v"], "ci95": row["ci95"], "band": row["band"], "n": row["n"],
                      "null_control": {k: null[slug][k] for k in ("real_delta_phi_v", "null_95_range", "perm_p_value")},
                      "split_half": {h: {k: split[slug][h][k] for k in ("delta_phi_v", "ci95", "band")}
                                     for h in ("halfA", "halfB")}}
    assert pool["NVIDIA-Nemotron-3-Nano-30B-A3B"]["delta_phi_v"] == out["primary"]["deployed"]["delta_phi_v"]
    out["secondary"] = {
        "sources": {"pool": "results/judgebench_v2_pool_table.json candidates_ranked",
                    "null_control": "results/judgebench_v2_null_control.json candidates",
                    "split_half": "results/judgebench_v2_split_half.json candidates"},
        "scope": ("deployed gate prompt, each candidate added to Llama+Qwen on the 240-row stratum (DeepSeek-V4-Flash on "
                  "its 233 complete rows); all at 50% drops (51% for DeepSeek), README A8 threat 11; the pool ranking "
                  "is partly by construction for gpt-oss-120b and DeepSeek-V4-Flash, README A8 threat 10"),
        "candidates": pool,
    }

    # ── checks against committed figures ──
    ops = prevj["gate_operating_characteristics"]["rules"]
    dep = out["premise_test"]["deployed"]
    for j, rule in (("llama", "llama_alone (advisory)"), ("qwen", "block_consensus_unsafe (= Qwen UNSAFE)"),
                    ("nano", "nano_alone")):
        k, n = map(int, dep["recall"][j]["count"].split("/"))
        assert (ops[rule]["drops_flagged"], [ops[rule]["recall_pct"], ops[rule]["recall_wilson95"]]) == \
            (dep["recall"][j]["count"], list(pct(k, n))), j
        kf, nf = map(int, dep["false_positive"][j]["count"].split("/"))
        assert (ops[rule]["controls_flagged"], [ops[rule]["false_positive_rate_pct"], ops[rule]["fpr_wilson95"]]) == \
            (dep["false_positive"][j]["count"], list(pct(kf, nf))), j
    for name, key in (("deployed", "deployed_prompt"), ("calibration", "calibration_prompt")):
        cf = prevj["controls_flagged_by_judge"][key]
        assert {j: out["premise_test"][name]["false_positive"][j]["count"] for j in ("llama", "qwen", "nano")} == cf
    pc = prevj["panel_calibration_prompt"]
    cal = out["premise_test"]["calibration"]
    assert (pc["recall"], pc["specificity"]) == (cal["recall"]["nano"]["count"], cal["specificity"]["nano"]["count"])
    for row in table:
        rec, spec = pool[row["slug"]]["recall"]["count"], pool[row["slug"]]["specificity"]["count"]
        assert (rec, spec) == (row["candidate_recall_tau1"], row["candidate_spec_tau0"]), row["slug"]
    assert dep["shared_misses"]["both_incumbents_safe"]["count"] == "41/120"          # README B4, NEMOTRON_INSIGHTS
    assert dep["shared_misses"]["nano_catches_of_these"] == "33/41"                   # NEMOTRON_INSIGHTS Finding 1
    assert pool["gpt-oss-120b"]["catches_of_drops_both_incumbents_pass"] == "38/41"   # NEMOTRON_INSIGHTS Finding 1
    # the 200 clean controls: counts equal the two committed 100-control halves of the same file, and Nano-UNSAFE /
    # Qwen-SAFE on them equals the committed 51/200 (README B4 table: Llama 19/200, Qwen 19/200, Nano 61/200)
    b4 = _load(SPLIT708)["b4_strategies"]
    assert all(b4[h][s]["n_clean"] == 100 for h in ("dev", "test") for s in ("llama_only", "qwen_only", "nemotron_only"))
    for j, s in (("llama", "llama_only"), ("qwen", "qwen_only"), ("nano", "nemotron_only")):
        k200 = sum(round(b4[h][s]["fp"] * 100) for h in ("dev", "test"))
        assert p200["false_positive"][j]["count"] == f"{k200}/200", j
    assert prevj["gate_708_disagree_reference"]["disagree_on_clean"] == f"{dis}/200"
    out["checks"] = [
        "primary cells reproduce results/judgebench_v2_phi_v_recompute.json deployed_full / calibration_full",
        "er0 paired and all-120 cells reproduce the committed deployed_/calibration_er0_* cells",
        "deployed recall and false-positive counts and Wilson CIs for Llama, Qwen and Nano reproduce "
        "results/judgebench_v2_prevalence_sensitivity.json gate_operating_characteristics (llama_alone, "
        "block_consensus_unsafe = Qwen UNSAFE, nano_alone)",
        "controls flagged per judge, both prompts, reproduce prevalence_sensitivity controls_flagged_by_judge; "
        "calibration Nano recall and specificity reproduce panel_calibration_prompt",
        "each pool candidate's recall and specificity counts reproduce results/judgebench_v2_pool_table.json",
        "deployed: both incumbents pass 41/120, Nano catches 33 of them, gpt-oss-120b 38 (README B4, NEMOTRON_INSIGHTS)",
        "full stratum reweighted to 20% reproduces prevalence_sensitivity full_stratum_at_subset_shares "
        "deployed_er0_all120 (deployed) and panel_calibration_prompt by_prevalence 0.20 (calibration)",
        "the 200 clean controls of results/gate_calibration_full.json are the 172 supplementary + 28 calib-origin paired "
        "controls; per-judge counts flagged equal the sum of results/split_half_validation.json b4_strategies dev + test "
        "(19, 19, 61 of 200, as in README B4) and Nano-UNSAFE/Qwen-SAFE equals prevalence_sensitivity "
        "gate_708_disagree_reference disagree_on_clean (51/200)",
        "no ERROR verdicts among Llama, Qwen, Nano in either panel file or among the 200 clean controls",
    ]
    json.dump(out, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # ── print ──
    for name in ("deployed", "calibration"):
        p = out["premise_test"][name]
        print(f"== {name} prompt: premise test ({p['n_drops']} drops, {p['n_controls']} paired controls)")
        for j in ("llama", "qwen", "nano"):
            r, f = p["recall"][j], p["false_positive"][j]
            print(f"   {j:6} recall {r['count']:>7} {r['rate']:.3f} [{r['wilson95'][0]:.3f},{r['wilson95'][1]:.3f}]"
                  f"   FP {f['count']:>7} {f['rate']:.3f} [{f['wilson95'][0]:.3f},{f['wilson95'][1]:.3f}]")
        f2 = p["false_positive_protocol_200_controls"]
        if f2.get("available", True):
            for j in ("llama", "qwen", "nano"):
                f = f2["false_positive"][j]
                print(f"   {j:6} FP on the 200: {f['count']} {f['rate']:.3f} [{f['wilson95'][0]:.3f},{f['wilson95'][1]:.3f}]")
            print(f"   on the 28 in both runs: {f2['on_the_28_also_in_the_v2_run']}")
        b = p["bands"]
        a = b["NEMOTRON ADVANTAGE (material)"]
        print(f"   outcome: {b['incumbent_outcome']}  (confirmed ci: {b['INCUMBENT BLIND SPOT CONFIRMED']['ci']}, "
              f"no-blind-spot ci: {b['NO BLIND SPOT']['ci']})")
        print(f"   Nano advantage {a['difference']:+.4f} [{a['ci95_bootstrap'][0]:+.4f},{a['ci95_bootstrap'][1]:+.4f}] "
              f"met={a['met']}  McNemar {a['mcnemar_exact']}")
        print(f"   shared misses {p['shared_misses']}")
        e = out["expert_recoverability"][name]
        for j, v in e["advance_prediction"]["by_judge"].items():
            print(f"   ER {j:6} {v['er1']} vs {v['er0']}  d={v['difference_er1_minus_er0']:+.4f} "
                  f"[{v['newcombe95'][0]:+.4f},{v['newcombe95'][1]:+.4f}] p1={v['fisher_one_sided_p']}")
        for k, c in e["delta_phi_v_within_stratum"].items():
            print(f"   dPhi {k:11} n={c['n']:3} prev={c['prevalence']:.2f} {c['delta_phi_v']:+.4f} "
                  f"[{c['ci95'][0]:+.4f},{c['ci95'][1]:+.4f}] {c['band']}")
        for k, c in e["prevalence_comparison"].items():
            f = c["full_stratum_reweighted"]
            print(f"   at share {c['drop_share']:.4f}: subset {c['subset_cell_delta_phi_v']:+.4f} vs full "
                  f"{f['delta_phi_v']:+.4f} [{f['ci95'][0]:+.4f},{f['ci95'][1]:+.4f}] {f['band']}")
    print(f"   incumbents, both prompts: {out['expert_recoverability']['incumbents_both_prompts']}")
    for s, c in out["secondary"]["candidates"].items():
        print(f"   {s:32} recall {c['recall']['count']} [{c['recall']['wilson95'][0]:.3f},{c['recall']['wilson95'][1]:.3f}]"
              f" spec {c['specificity']['count']}  both-miss caught {c['catches_of_drops_both_incumbents_pass']}")
    print(f"\nSaved -> {OUT}")


if __name__ == "__main__":
    main()
