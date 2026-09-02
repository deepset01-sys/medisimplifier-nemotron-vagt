"""
vagt_core.py — Veridicality-Anchored G-Theory core, generalized to an arbitrary
judge panel. Estimators copied VERBATIM (same math, same SEED=42, same bias
correction) from vagt_nemotron_analysis.py so /v1/audit_panel reuses the exact
statistics that produced the README's published VAGT numbers — no new math.

The ONLY generalization vs. the original: the 2-vs-3 rater comparison is no
longer hardcoded. paired_delta(X, tau, n_incumbent) computes
Φ_V(panel) − Φ_V(incumbent) for an incumbent of ANY size k (the first k columns
of X) plus one appended candidate column — i.e. ΔΦ_V(c) = Φ_V(P ∪ {c}) − Φ_V(P).

SAFE=0 / UNSAFE=1. Ground truth τ = 1 for corrupted-feature items, 0 for clean.
Complete-case: a row enters a stratum only if EVERY rater returned a valid verdict.
"""

import numpy as np

SEED = 42
N_BOOT = 1000
LABEL_TO_INT = {"SAFE": 0, "UNSAFE": 1}
VALID = set(LABEL_TO_INT)
STRATA = ["dose", "negation", "lateral", "diagnosis"]
VAGT_METRICS = ["sigma_tau", "sigma_B", "sigma_R", "sigma_N", "phi_v"]
CONSENSUS_METRICS = ["fleiss", "kripp"]
DELTA_METRICS = ["phi_v", "sigma_B", "fleiss", "kripp"]


# ── consensus (rater-to-rater) statistics — verbatim, general in R ────────────
def cohen_kappa(a, b):
    """Pairwise Cohen's κ on two binary 0/1 arrays."""
    n = a.size
    if n == 0:
        return float("nan")
    po = float(np.mean(a == b))
    pa1, pb1 = a.mean(), b.mean()
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


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
    """Krippendorff's α (nominal, binary) for N units × R raters, no missing."""
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


# ── VAGT decomposition (veridicality-anchored) — verbatim, general in R ───────
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


# ── convenience wrappers ──────────────────────────────────────────────────────
def phi_v(X, tau):
    """Φ_V for the panel formed by the columns of X (n_r = #columns)."""
    return vagt(X, tau, X.shape[1])["phi_v"]


def sigma_decomposition(X, tau):
    """Full {σ²_τ, σ²_B, σ²_R, σ²_N, Φ_V, fleiss, kripp} for the panel of X's columns."""
    return all_stats(X, tau)


# ── paired Δ, GENERALIZED: k-incumbent (first k cols) + 1 appended candidate ──
def paired_delta(X, tau, n_incumbent):
    """Δ = Φ_V(P ∪ {c}) − Φ_V(P) on the SAME items. Incumbent P = first n_incumbent
    columns (n_r = n_incumbent); full panel = all columns (n_r = X.shape[1]). Pairing
    on identical items is what makes a CI on the difference valid. When X has 3 columns
    [Llama, Qwen, Nemotron] and n_incumbent=2 this reproduces the original 2-vs-3 Δ."""
    inc = all_stats(X[:, :n_incumbent], tau)
    full = all_stats(X, tau)
    return {m: full[m] - inc[m] for m in DELTA_METRICS}


def paired_delta_cis(X, tau, n_incumbent, rng, n_boot=N_BOOT):
    """95% percentile CI on each Δ metric via a PAIRED item bootstrap: resample the
    items ONCE per iteration and compute both panels on that same resample."""
    n = X.shape[0]
    acc = {m: np.empty(n_boot) for m in DELTA_METRICS}
    for i in range(n_boot):
        idx = rng.integers(0, n, n)
        d = paired_delta(X[idx], tau[idx], n_incumbent)
        for m in DELTA_METRICS:
            acc[m][i] = d[m]
    point = paired_delta(X, tau, n_incumbent)
    cis = {}
    for m in DELTA_METRICS:
        arr = acc[m][np.isfinite(acc[m])]
        cis[m] = ((float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5)))
                  if arr.size else (float("nan"), float("nan")))
    return point, cis


# ── stratum matrix builder — verbatim, general in rater_keys ──────────────────
def stratum(records, feature, rater_keys):
    """Corrupted-`feature` items (τ=1) + all clean controls (τ=0), keeping only rows
    where EVERY rater in `rater_keys` returned a valid SAFE/UNSAFE verdict. Column
    order follows rater_keys. Returns X (n × len(rater_keys)), tau, n_dropped."""
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


# ── high-level: ΔΦ_V per stratum for one candidate vs an incumbent panel ──────
def delta_by_stratum(records, incumbent_keys, candidate_key, strata=STRATA):
    """For each stratum, build [incumbent... , candidate] and return the paired Δ
    plus incumbent/full Φ_V. Column order = incumbent_keys + [candidate_key], so the
    candidate is the appended rater."""
    keys = list(incumbent_keys) + [candidate_key]
    k = len(incumbent_keys)
    out = {}
    for f in strata:
        X, tau, dropped = stratum(records, f, keys)
        inc = all_stats(X[:, :k], tau)
        full = all_stats(X, tau)
        out[f] = {
            "n": int(X.shape[0]),
            "dropped": dropped,
            "phi_incumbent": inc["phi_v"],
            "phi_full": full["phi_v"],
            "delta": {m: full[m] - inc[m] for m in DELTA_METRICS},
        }
    return out


def incumbent_phi_by_stratum(records, incumbent_keys, strata=STRATA):
    """Φ_V of the incumbent panel per stratum — argmin is the incumbent's blind spot."""
    out = {}
    for f in strata:
        X, tau, _ = stratum(records, f, list(incumbent_keys))
        out[f] = all_stats(X, tau)["phi_v"]
    return out
