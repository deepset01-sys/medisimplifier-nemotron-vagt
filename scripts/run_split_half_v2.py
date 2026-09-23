"""
run_split_half_v2.py — patient-level split-half validation of the pool ΔΦ_V.

Split the 120 patients (each = a τ=1 drop + its paired τ=0 control) 60/60 (SEED=42),
recompute ΔΦ_V per half per candidate (vagt_core, bootstrap CI n_boot=1000), classify by
the pre-registered bands. Both halves POSITIVE => holds out-of-sample. No API.

Base (Llama+Qwen) + Nemotron-Nano from panel_gate.json; other 5 candidates from pool files.
"""
import json, io, sys
from pathlib import Path
import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from audit_panel import vagt_core as V                          # noqa: E402

GATE = _REPO / "results" / "judgebench_v2_panel_gate.json"
INCUMBENT = ["llama_verdict", "qwen_verdict"]
CANDIDATES = [
    ("NVIDIA-Nemotron-3-Nano-30B-A3B", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "panel"),
    ("Nemotron-3-Ultra-550b-a55b",     "nvidia/Nemotron-3-Ultra-550b-a55b",     "pool"),
    ("nemotron-3-super-120b-a12b",     "nvidia/nemotron-3-super-120b-a12b",     "pool"),
    ("gpt-oss-120b",                   "openai/gpt-oss-120b",                   "pool"),
    ("DeepSeek-V4-Flash-0731",         "deepseek-ai/DeepSeek-V4-Flash-0731",    "pool"),
    ("gemma-3-27b-it",                 "google/gemma-3-27b-it",                 "pool"),
]


def band(d, lo, hi):
    if d >= 0.05 and lo > 0:
        return "POSITIVE"
    if d <= -0.02 and hi < 0:
        return "NEGATIVE"
    return "NULL/ATTENUATED"


def both_verdict(a, b):
    if a["band"] == "POSITIVE" and b["band"] == "POSITIVE":
        return "POSITIVE"
    if a["band"] == "NEGATIVE" or b["band"] == "NEGATIVE":
        return "FAIL"
    return "NULL"   # at least one half not POSITIVE, none NEGATIVE


def load_base():
    return {(str(x["idx"]), x["tau"]): x
            for x in json.load(io.open(GATE, encoding="utf-8"))["per_sample"]}


def cand_lookup(slug, source, base):
    if source == "panel":
        return {k: b["nemotron_verdict"] for k, b in base.items()}
    p = _REPO / "results" / f"judgebench_v2_pool_{slug}.json"
    return {(str(r["idx"]), r["tau"]): r["verdict"]
            for r in json.load(io.open(p, encoding="utf-8"))["verdicts"]}


def delta_ci(base, cand, idx_set):
    recs = []
    for (idx, tau), b in base.items():
        if idx not in idx_set:
            continue
        recs.append({"condition": "corrupted" if tau == 1 else "clean",
                     "error_type": "diagnosis" if tau == 1 else "none",
                     "llama_verdict": b["llama_verdict"], "qwen_verdict": b["qwen_verdict"],
                     "cand_verdict": cand[(idx, tau)]})
    X, tau, dropped = V.stratum(recs, "diagnosis", INCUMBENT + ["cand_verdict"])
    point, cis = V.paired_delta_cis(X, tau, 2, np.random.default_rng(V.SEED), V.N_BOOT)
    lo, hi = cis["phi_v"]
    return {"n": int(X.shape[0]), "dropped": int(dropped),
            "delta_phi_v": round(float(point["phi_v"]), 4),
            "ci95": [round(lo, 4), round(hi, 4)], "band": band(point["phi_v"], lo, hi)}


def main():
    base = load_base()
    patients = sorted({idx for (idx, tau) in base if tau == 1})     # 120 patient idxs
    rng = np.random.default_rng(V.SEED)
    perm = rng.permutation(len(patients))
    half = len(patients) // 2
    A = {patients[i] for i in perm[:half]}
    B = {patients[i] for i in perm[half:]}
    out = {"seed": V.SEED, "n_boot": V.N_BOOT, "split_unit": "patient (pair)",
           "halfA_patients": len(A), "halfB_patients": len(B),
           "note": "each half n≈120 (vs 240 full) → CIs ~sqrt(2) wider; mid-tier near +0.05 may read "
                   "ATTENUATED from reduced n, not a genuine out-of-sample failure.",
           "candidates": {}}
    print(f"patient-level split-half  (SEED={V.SEED}, n_boot={V.N_BOOT}, halves {len(A)}/{len(B)} patients)\n")
    hdr = (f"{'candidate':32} | {'A ΔΦ_V':>8} {'A 95% CI':>18} {'A band':>16} | "
           f"{'B ΔΦ_V':>8} {'B 95% CI':>18} {'B band':>16} | both")
    print(hdr)
    print("-" * len(hdr))
    for slug, model, source in CANDIDATES:
        cand = cand_lookup(slug, source, base)
        a = delta_ci(base, cand, A)
        b = delta_ci(base, cand, B)
        bv = both_verdict(a, b)
        out["candidates"][slug] = {"model": model, "halfA": a, "halfB": b, "both_halves": bv}
        cia = f"[{a['ci95'][0]:+.4f},{a['ci95'][1]:+.4f}]"
        cib = f"[{b['ci95'][0]:+.4f},{b['ci95'][1]:+.4f}]"
        print(f"{slug:32} | {a['delta_phi_v']:>+8.4f} {cia:>18} {a['band']:>16} | "
              f"{b['delta_phi_v']:>+8.4f} {cib:>18} {b['band']:>16} | {bv}")
    json.dump(out, io.open(_REPO / "results" / "judgebench_v2_split_half.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("\nSaved -> results/judgebench_v2_split_half.json")


if __name__ == "__main__":
    main()
