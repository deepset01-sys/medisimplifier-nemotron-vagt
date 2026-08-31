"""vagt_nemotron_analysis.py — VAGT decomposition with Nemotron Nano as a third rater.

Mirrors vagt_medsimplifier_demo.py (Veridicality-Anchored G-Theory on
MedSimp-JudgeBench), but extends the panel from TWO judges (Llama, Qwen) to
THREE by adding NVIDIA Nemotron-3 Nano. For each injected error type it reports
the full variance decomposition {σ²_τ, σ²_B, σ²_R, σ²_N, Φ_V} plus multi-rater
consensus statistics (Fleiss' κ, Krippendorff's α, pairwise Cohen's κ), each
with a 95% bootstrap CI (n_boot=1000, seed=42, items resampled with replacement).

The headline question this answers: does adding Nemotron — a high-sensitivity,
low-specificity judge (full-set: 84.2% recall on corrupted, 35.2% false-positive
on clean) — REDUCE the shared blind spot (σ²_B) that VAGT flags on `diagnosis`,
where Llama and Qwen both miss the omission? So each stratum is decomposed twice:
  • 2-rater baseline  {Llama, Qwen}          (n_r = 2)
  • 3-rater panel     {Llama, Qwen, Nemotron} (n_r = 3)
and the change in Φ_V and σ²_B is printed explicitly.

Data: nemotron_calibration_full.json (this repo) — per-sample verdicts for all
three judges on the no-CoT (v2) condition, produced by nemotron_judge_test.py.
Ground truth τ = injected error type / condition (corrupted-f → τ=1; clean → τ=0).
Complete-case: only items where ALL THREE judges returned a valid SAFE/UNSAFE
verdict enter a stratum (ERROR verdicts drop the item; the count is reported).

Decomposition (UNDIVIDED shared bias; matches vagt_section.md §3 / the demo):
  consensus   c_i  = mean_r X_{ir}
  shared bias b_i  = c_i − τ_i ;  σ²_B = mean_i b_i²  −  σ²_N / R   (bias-corrected)
  rater bias  α_r  = X̄_{·r} − X̄ ; σ²_R = mean_r α_r²
  noise       ε_ir = X_{ir} − c_i − α_r ; σ²_N = mean ε²
  σ²_τ = π(1−π) ;  Φ_V = σ²_τ / (σ²_τ + σ²_B + (σ²_R + σ²_N)/n_r)

SAFE=0 / UNSAFE=1. With a third, diverging rater σ²_R is now genuinely non-zero
(unlike the demo's illustrative two-rater σ²_R), so the panel is more informative.
"""

import json
import sys
from pathlib import Path

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

HERE = Path(__file__).resolve().parent
CANDIDATES = [
    HERE / "nemotron_calibration_full.json",
    Path(r"C:\Users\User\Desktop\medisimplifier-nemotron-vagt\nemotron_calibration_full.json"),
]
DATA = next((p for p in CANDIDATES if p.exists()), None)
if DATA is None:
    sys.exit("nemotron_calibration_full.json not found (run nemotron_judge_test.py --n 708 first)")

LABEL_TO_INT = {"SAFE": 0, "UNSAFE": 1}
VALID = set(LABEL_TO_INT)
FEATURES = ["dose", "negation", "lateral", "diagnosis"]
# rater key in per_sample -> display label. Order fixes the columns of X.
RATERS = [("llama_verdict", "Llama"), ("qwen_verdict", "Qwen"), ("nemotron_verdict", "Nemotron")]
N_BOOT = 1000
SEED = 42
VAGT_METRICS = ["sigma_tau", "sigma_B", "sigma_R", "sigma_N", "phi_v"]
CONSENSUS_METRICS = ["fleiss", "kripp"]
DELTA_METRICS = ["phi_v", "sigma_B", "fleiss", "kripp"]   # reported as 3-rater − 2-rater


# ── consensus (rater-to-rater) statistics — generalized to R raters ──────────
def cohen_kappa(a, b):
    """Pairwise Cohen's κ on two binary 0/1 arrays."""
    n = a.size
    if n == 0:
        return float("nan")
    po = float(np.mean(a == b))
    pa1, pb1 = a.mean(), b.mean()
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def pabak(a, b):
    return 2 * float(np.mean(a == b)) - 1


def fleiss_kappa(X):
    """Fleiss' κ for N units × R raters, binary categories {0,1}."""
    N, R = X.shape
    if N == 0 or R < 2:
        return float("nan")
    n1 = X.sum(axis=1)
    n0 = R - n1
    P_i = (n0 * (n0 - 1) + n1 * (n1 - 1)) / (R * (R - 1))
    P_bar = float(P_i.mean())
    p1 = X.sum() / (N * R)
    P_e = p1 ** 2 + (1 - p1) ** 2
    return float("nan") if P_e == 1 else (P_bar - P_e) / (1 - P_e)


def krippendorff_alpha_binary(X):
    """Krippendorff's α (nominal, binary) for N units × R raters, no missing.

    Coincidence-matrix form; reduces exactly to the demo's 2-rater formula when R=2.
    α = 1 − (n−1) · Σ_u [n_u0·n_u1/(R−1)] / (n_0·n_1),  n = N·R total values.
    """
    N, R = X.shape
    if N == 0 or R < 2:
        return float("nan")
    n1_u = X.sum(axis=1)
    n0_u = R - n1_u
    S = float(np.sum(n0_u * n1_u)) / (R - 1)
    n_total = N * R
    n_1 = int(X.sum())
    n_0 = n_total - n_1
    if n_0 == 0 or n_1 == 0:
        return float("nan")
    return 1 - (n_total - 1) * S / (n_0 * n_1)


# ── VAGT decomposition (veridicality-anchored) — general in R ────────────────
def vagt(X, tau, n_r):
    R = X.shape[1]
    c = X.mean(axis=1)
    b = c - tau
    sigma_B_naive = float(np.mean(b ** 2))
    grand = X.mean()
    alpha = X.mean(axis=0) - grand           # per-rater bias (leniency/strictness)
    sigma_R = float(np.mean(alpha ** 2))
    eps = X - (c[:, None] + alpha[None, :])
    sigma_N = float(np.mean(eps ** 2))
    # σ²_B = mean(b²) − σ²_N/R  (R-rater consensus sampling-variance correction; §3)
    sigma_B = max(0.0, sigma_B_naive - sigma_N / R)
    p = float(tau.mean())
    sigma_tau = p * (1 - p)
    denom = sigma_tau + sigma_B + (sigma_R + sigma_N) / n_r
    phi_v = sigma_tau / denom if denom > 0 else float("nan")
    return dict(sigma_tau=sigma_tau, sigma_B=sigma_B, sigma_R=sigma_R,
                sigma_N=sigma_N, phi_v=phi_v, alpha=alpha)


def all_stats(X, tau):
    """VAGT (n_r = #columns of X) + multi-rater consensus stats."""
    v = vagt(X, tau, n_r=X.shape[1])
    out = {m: v[m] for m in VAGT_METRICS}
    out["fleiss"] = fleiss_kappa(X)
    out["kripp"] = krippendorff_alpha_binary(X)
    return out


def bootstrap_cis(X, tau, rng, metrics, n_boot=N_BOOT):
    """95% percentile bootstrap CI per metric (items resampled with replacement)."""
    n = X.shape[0]
    acc = {m: np.empty(n_boot) for m in metrics}
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        s = all_stats(X[idx], tau[idx])
        for m in metrics:
            acc[m][i] = s[m]
    cis = {}
    for m in metrics:
        arr = acc[m][np.isfinite(acc[m])]
        cis[m] = (np.percentile(arr, 2.5), np.percentile(arr, 97.5)) if arr.size else (np.nan, np.nan)
    return cis


def paired_delta(X3, tau3):
    """Δ = 3-rater − 2-rater on the SAME items (the 3-rater complete-case stratum).
    2-rater panel = Llama+Qwen (first two columns, n_r=2); 3-rater = all three (n_r=3).
    Pairing on identical items is what makes a CI on the difference valid — unlike the
    per-panel CIs above, which resample the (differently-sized) 2- and 3-rater strata
    independently and so cannot be differenced."""
    s2 = all_stats(X3[:, :2], tau3)
    s3 = all_stats(X3, tau3)
    return {m: s3[m] - s2[m] for m in DELTA_METRICS}


def paired_delta_cis(X3, tau3, rng, n_boot=N_BOOT):
    """95% percentile CI on each Δ metric via a PAIRED item bootstrap: resample the
    items ONCE per iteration and compute both panels on that same resample."""
    n = X3.shape[0]
    acc = {m: np.empty(n_boot) for m in DELTA_METRICS}
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        d = paired_delta(X3[idx], tau3[idx])
        for m in DELTA_METRICS:
            acc[m][i] = d[m]
    point = paired_delta(X3, tau3)
    cis = {}
    for m in DELTA_METRICS:
        arr = acc[m][np.isfinite(acc[m])]
        cis[m] = ((float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))
                  if arr.size else (float("nan"), float("nan")))
    return point, cis


def stratum(records, feature, rater_keys):
    """Corrupted-`feature` items (τ=1) + all clean controls (τ=0), keeping only
    rows where EVERY rater in `rater_keys` returned a valid SAFE/UNSAFE verdict.
    Returns X (n × len(rater_keys)), tau, and n_dropped (any-ERROR rows)."""
    rows, taus, dropped = [], [], 0
    for r in records:
        if r["condition"] == "corrupted" and r["error_type"] == feature:
            t = 1
        elif r["condition"] == "clean":
            t = 0
        else:
            continue
        vals = [r.get(k) for k in rater_keys]
        if all(v in VALID for v in vals):
            rows.append([LABEL_TO_INT[v] for v in vals])
            taus.append(t)
        else:
            dropped += 1
    return np.array(rows, dtype=float), np.array(taus, dtype=float), dropped


def main():
    recs = json.loads(DATA.read_text(encoding="utf-8"))
    per_sample = recs["per_sample"] if isinstance(recs, dict) else recs
    rng = np.random.default_rng(SEED)
    rng_delta = np.random.default_rng(SEED)  # dedicated stream → level-CI bootstrap above stays bit-identical on re-run

    two_keys = ["llama_verdict", "qwen_verdict"]
    three_keys = ["llama_verdict", "qwen_verdict", "nemotron_verdict"]
    three_labels = ["Llama", "Qwen", "Nemotron"]

    print("VAGT decomposition on MedSimp-JudgeBench — Llama + Qwen + Nemotron Nano")
    print(f"Source: {DATA.name} ({len(per_sample)} records, no-CoT / v2 condition).")
    print(f"Point estimate [2.5%, 97.5%] via {N_BOOT}-item bootstrap, seed={SEED}. "
          f"SAFE=0/UNSAFE=1.")
    print("Each stratum = corrupted-feature items (τ=1) + shared clean controls (τ=0).")
    print("Two panels per feature: 2-rater {Llama,Qwen} baseline vs 3-rater {+Nemotron}.\n")

    summary = {}
    delta_out = {}
    for f in FEATURES:
        X2, tau2, drop2 = stratum(per_sample, f, two_keys)
        X3, tau3, drop3 = stratum(per_sample, f, three_keys)

        s2 = all_stats(X2, tau2)
        c2 = bootstrap_cis(X2, tau2, rng, VAGT_METRICS + CONSENSUS_METRICS)
        s3 = all_stats(X3, tau3)
        c3 = bootstrap_cis(X3, tau3, rng, VAGT_METRICS + CONSENSUS_METRICS)
        v3 = vagt(X3, tau3, n_r=3)  # for per-rater α

        def fmt(s, c, m):
            return f"{s[m]:.3f} [{c[m][0]:.3f}, {c[m][1]:.3f}]"

        print("=" * 72)
        print(f"FEATURE: {f}   (3-rater n={X3.shape[0]}, corrupted prevalence="
              f"{tau3.mean():.2f}, dropped-for-ERROR={drop3})")
        print("=" * 72)
        print(f"  {'metric':10} {'2-rater {L,Q}':>26}   {'3-rater {L,Q,Nemo}':>26}")
        for m, lab in [("sigma_tau", "σ²_τ"), ("sigma_B", "σ²_B (shared bias)"),
                       ("sigma_R", "σ²_R (rater)"), ("sigma_N", "σ²_N (noise)"),
                       ("phi_v", "Φ_V"), ("fleiss", "Fleiss κ"), ("kripp", "Kripp α")]:
            print(f"  {lab:20} {fmt(s2, c2, m):>26}   {fmt(s3, c3, m):>26}")

        # pairwise Cohen's κ among the three raters (3-rater stratum)
        cols = {lab: X3[:, i] for i, lab in enumerate(three_labels)}
        print("  pairwise Cohen κ:  "
              f"L–Q={cohen_kappa(cols['Llama'], cols['Qwen']):.3f}   "
              f"L–Nemo={cohen_kappa(cols['Llama'], cols['Nemotron']):.3f}   "
              f"Q–Nemo={cohen_kappa(cols['Qwen'], cols['Nemotron']):.3f}")
        # per-rater bias α_r (positive = flags UNSAFE more than panel mean = stricter)
        arates = X3.mean(axis=0)
        print("  UNSAFE rate / α_r:  " + "   ".join(
            f"{lab}={arates[i]:.2f}/{v3['alpha'][i]:+.2f}" for i, lab in enumerate(three_labels)))

        d_phi = s3["phi_v"] - s2["phi_v"]
        d_sB = s3["sigma_B"] - s2["sigma_B"]
        print(f"  Δ adding Nemotron:  ΔΦ_V={d_phi:+.3f}   Δσ²_B={d_sB:+.3f}   "
              f"({'blind spot reduced' if d_sB < 0 else 'shared bias up'}; "
              f"{'dependability up' if d_phi > 0 else 'dependability down'})")
        # Paired-bootstrap CI on Δ = 3-rater − 2-rater (same items; 2-rater = Llama+Qwen)
        dpoint, dcis = paired_delta_cis(X3, tau3, rng_delta)
        print(f"  Δ paired 95% CI:    "
              f"ΔΦ_V={dpoint['phi_v']:+.3f} [{dcis['phi_v'][0]:+.3f}, {dcis['phi_v'][1]:+.3f}]   "
              f"Δσ²_B={dpoint['sigma_B']:+.3f} [{dcis['sigma_B'][0]:+.3f}, {dcis['sigma_B'][1]:+.3f}]   "
              f"ΔFleiss κ={dpoint['fleiss']:+.3f} [{dcis['fleiss'][0]:+.3f}, {dcis['fleiss'][1]:+.3f}]")
        delta_out[f] = {"n": int(X3.shape[0]),
                        **{f"delta_{m}": {"point": round(dpoint[m], 4),
                                          "ci95": [round(dcis[m][0], 4), round(dcis[m][1], 4)]}
                           for m in DELTA_METRICS}}
        print()
        summary[f] = dict(phi2=s2["phi_v"], phi3=s3["phi_v"], sB2=s2["sigma_B"],
                          sB3=s3["sigma_B"], dphi=d_phi, dsB=d_sB)

    # ── cross-feature summary ────────────────────────────────────────────────
    print("=" * 72)
    print("SUMMARY — effect of adding Nemotron as a third rater")
    print("=" * 72)
    print(f"  {'feature':10} {'Φ_V(2)':>8} {'Φ_V(3)':>8} {'ΔΦ_V':>8}   "
          f"{'σ²_B(2)':>8} {'σ²_B(3)':>8} {'Δσ²_B':>8}")
    for f in FEATURES:
        s = summary[f]
        print(f"  {f:10} {s['phi2']:>8.3f} {s['phi3']:>8.3f} {s['dphi']:>+8.3f}   "
              f"{s['sB2']:>8.3f} {s['sB3']:>8.3f} {s['dsB']:>+8.3f}")

    worst2 = min(FEATURES, key=lambda f: summary[f]["phi2"])
    worst3 = min(FEATURES, key=lambda f: summary[f]["phi3"])
    best_gain = min(FEATURES, key=lambda f: summary[f]["dsB"])  # most-negative Δσ²_B
    print(f"\n  Lowest Φ_V (worst-calibrated feature): 2-rater={worst2}, 3-rater={worst3}.")
    print(f"  Largest shared-bias reduction from Nemotron: {best_gain} "
          f"(Δσ²_B={summary[best_gain]['dsB']:+.3f}, ΔΦ_V={summary[best_gain]['dphi']:+.3f}).")
    print("\n  Interpretation: Nemotron's high sensitivity pulls the consensus toward")
    print("  ground truth on features where Llama+Qwen share a blind spot (shrinking σ²_B),")
    print("  but its divergence raises rater variance σ²_R. Φ_V nets these effects; a")
    print("  positive ΔΦ_V means the veridicality gain outweighs the added rater noise.")

    # ── Emit paired-delta 95% CIs as a committable artifact ──────────────────
    out_path = HERE / "vagt_bootstrap_cis.json"
    out_path.write_text(json.dumps({
        "meta": {"source": DATA.name, "n_boot": N_BOOT, "seed": SEED,
                 "method": ("paired item bootstrap; Delta = 3-rater minus 2-rater on the "
                            "3-rater complete-case stratum; 2-rater panel = Llama+Qwen")},
        "features": delta_out,
    }, indent=2), encoding="utf-8")
    print(f"\n  Wrote paired-delta 95% CIs -> {out_path.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
