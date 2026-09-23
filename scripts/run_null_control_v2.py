"""
run_null_control_v2.py — τ-blind permutation null for the pool ΔΦ_V.

Tests whether each candidate's Φ_V lift is DETECTION-specific (verdict correlated with τ)
vs. merely the effect of appending a column with that flag-rate. Permutes the candidate's
verdict column across complete-case rows (exact UNSAFE count preserved, τ-correlation
destroyed), recomputes ΔΦ_V vs the Llama+Qwen incumbent, N_PERM×. SEED=42, no API.

Base (Llama+Qwen) + Nemotron-Nano come from panel_gate.json; the other 5 candidates from
their pool verdict files. All 6 candidates are evaluated.
"""
import json, io, sys
from pathlib import Path
import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from audit_panel import vagt_core as V                          # noqa: E402

GATE = _REPO / "results" / "judgebench_v2_panel_gate.json"
N_PERM = 1000
L2I = {"SAFE": 0, "UNSAFE": 1}

# candidate slug -> (model id, source): source "panel" uses base nemotron_verdict; "pool" uses the pool file
CANDIDATES = [
    ("NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "panel"),
    ("Nemotron-3-Ultra-550b-a55b",     "nvidia/Nemotron-3-Ultra-550b-a55b",     "pool"),
    ("nemotron-3-super-120b-a12b",     "nvidia/nemotron-3-super-120b-a12b",     "pool"),
    ("gpt-oss-120b",                   "openai/gpt-oss-120b",                   "pool"),
    ("DeepSeek-V4-Flash-0731",         "deepseek-ai/DeepSeek-V4-Flash-0731",    "pool"),
    ("gemma-3-27b-it",                 "google/gemma-3-27b-it",                 "pool"),
]


def load_base():
    return {(str(x["idx"]), x["tau"]): x
            for x in json.load(io.open(GATE, encoding="utf-8"))["per_sample"]}


def cand_lookup(slug, source, base):
    if source == "panel":
        return {k: b["nemotron_verdict"] for k, b in base.items()}
    p = _REPO / "results" / f"judgebench_v2_pool_{slug}.json"
    return {(str(r["idx"]), r["tau"]): r["verdict"]
            for r in json.load(io.open(p, encoding="utf-8"))["verdicts"]}


def complete_case(base, cand):
    llama, qwen, c, tau = [], [], [], []
    for k, b in base.items():
        lv, qv, cv = b["llama_verdict"], b["qwen_verdict"], cand.get(k, "ERROR")
        if lv in L2I and qv in L2I and cv in L2I:                # complete-case
            llama.append(L2I[lv]); qwen.append(L2I[qv]); c.append(L2I[cv]); tau.append(b["tau"])
    return (np.array(llama, float), np.array(qwen, float),
            np.array(c, float), np.array(tau, float))


def phi(cols, tau):
    X = np.column_stack(cols)
    return V.vagt(X, tau, X.shape[1])["phi_v"]                   # same estimator as vagt_core


def main():
    base = load_base()
    rng = np.random.default_rng(V.SEED)                          # SEED=42
    out = {"seed": V.SEED, "n_perm": N_PERM,
           "method": "τ-blind permutation of candidate verdict column; incumbent=Llama+Qwen; "
                     "flag-rate preserved, τ-correlation destroyed",
           "candidates": {}}
    rows = []
    for slug, model, source in CANDIDATES:
        cand = cand_lookup(slug, source, base)
        llama, qwen, c, tau = complete_case(base, cand)
        phi_inc = phi([llama, qwen], tau)
        real = phi([llama, qwen, c], tau) - phi_inc
        nulls = np.empty(N_PERM)
        for i in range(N_PERM):
            nulls[i] = phi([llama, qwen, rng.permutation(c)], tau) - phi_inc
        lo, hi = np.percentile(nulls, [2.5, 97.5])
        p_perm = float((np.sum(nulls >= real) + 1) / (N_PERM + 1))
        rec = {"model": model, "source": source, "n": int(len(tau)),
               "real_delta_phi_v": round(float(real), 4),
               "null_mean": round(float(nulls.mean()), 4),
               "null_95_range": [round(float(lo), 4), round(float(hi), 4)],
               "null_min": round(float(nulls.min()), 4), "null_max": round(float(nulls.max()), 4),
               "real_outside_null_95": bool(real > hi or real < lo),
               "perm_p_value": round(p_perm, 4)}
        out["candidates"][slug] = rec
        rows.append((slug, rec))
    json.dump(out, io.open(_REPO / "results" / "judgebench_v2_null_control.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"τ-blind permutation null  (SEED={V.SEED}, N_PERM={N_PERM}, incumbent=Llama+Qwen)\n")
    hdr = f"{'candidate':32} {'n':>4} {'real ΔΦ_V':>10} {'null mean':>10} {'null 95% range':>20} {'p':>7}  outside95"
    print(hdr); print("-" * len(hdr))
    for slug, r in rows:
        rng95 = f"[{r['null_95_range'][0]:+.4f},{r['null_95_range'][1]:+.4f}]"
        print(f"{slug:32} {r['n']:>4} {r['real_delta_phi_v']:>+10.4f} {r['null_mean']:>+10.4f} "
              f"{rng95:>20} {r['perm_p_value']:>7.4f}  {r['real_outside_null_95']}")
    print("\nSaved -> results/judgebench_v2_null_control.json")


if __name__ == "__main__":
    main()
