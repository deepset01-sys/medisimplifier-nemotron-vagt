"""
run_pool_judgebench_v2.py — 6-candidate audit-pool recompute on the JudgeBench v2
diagnosis stratum (120 tau=1 + 120 primary_paired tau=0), DEPLOYED gate prompt.

Base (Llama + Qwen + Nemotron-Nano) is REUSED from the panel_gate file (identical
deployed prompt) — NOT re-run. Five new candidate judges are each run one model at a
time via safety_gate._call_judge (same JUDGE_PROMPT + params as panel_gate), then
vagt_core computes each candidate's paired Delta Phi_V appended to the Llama+Qwen incumbent.

Phase 1 (run):   5 candidates x 240 items -> <out-dir>/judgebench_v2_pool_<slug>.json
Phase 2 (table): merge base + candidates  -> <out-dir>/judgebench_v2_pool_table.json

--limit N  : SMOKE mode — first ceil(N/2) tau=1 + floor(N/2) tau=0; writes smoke_-prefixed
             candidate files (never the canonical ones, so a later full run's resume is safe);
             prints a per-candidate verdict grid and SKIPS the (meaningless) n=N Phi_V table.
--analyze-only : rebuild the table from existing candidate files, no API calls.
Resumable per candidate (keep valid rows; re-judge only missing/ERROR).
"""
import argparse, json, io, os, sys, math
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "scripts"))
from safety_gate import _call_judge                 # deployed JUDGE_PROMPT judge (verbatim)  # noqa: E402
from audit_panel import vagt_core as V              # noqa: E402
import run_panel_judgebench_v2 as PANEL             # reuse join/build (raw-original + pairs)  # noqa: E402

CANDIDATES = {   # model -> max_tokens (reasoning models get 8000; enable_thinking=False in _call_judge)
    "nvidia/Nemotron-3-Ultra-550b-a55b": 8000,
    "nvidia/nemotron-3-super-120b-a12b": 8000,
    "openai/gpt-oss-120b":               8000,
    "deepseek-ai/DeepSeek-V4-Flash-0731": 4000,
    "google/gemma-3-27b-it":              4000,
}
NANO_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"   # already in panel_gate (nemotron_verdict)
INCUMBENT = ["llama_verdict", "qwen_verdict"]          # n_incumbent = 2


def slug(m):
    return m.split("/")[-1]


def canonical_items(tau1, controls, controls_filter):
    """240 items in canonical (tau, idx) order (matches panel_gate), each with a row_id."""
    sp, calib = PANEL._raw_original_index()
    items = PANEL._build_items(tau1, controls, controls_filter, sp, calib)
    items.sort(key=lambda it: (it["tau"], str(it["idx"])))
    for i, it in enumerate(items):
        it["row_id"] = i
    return items


def _save_candidate(path, model, items, results):
    payload = {"model": model, "slug": slug(model), "benchmark": "judgebench_v2",
               "prompt": "deployed (safety_gate.JUDGE_PROMPT, enable_thinking=False)",
               "n": len(items),
               "verdicts": [{"row_id": it["row_id"], "idx": it["idx"], "tau": it["tau"],
                             "verdict": results.get(it["row_id"], "ERROR")} for it in items]}
    tmp = str(path) + ".tmp"
    json.dump(payload, io.open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def run_candidate(model, items, api_key, workers, out_dir, prefix=""):
    out = Path(out_dir) / f"judgebench_v2_pool_{prefix}{slug(model)}.json"
    mt = CANDIDATES[model]
    results = {}
    if out.is_file():  # resume: keep valid rows
        for r in json.load(io.open(out, encoding="utf-8")).get("verdicts", []):
            if r["verdict"] in ("SAFE", "UNSAFE"):
                results[r["row_id"]] = r["verdict"]
    todo = [it for it in items if it["row_id"] not in results]
    print(f"  [{slug(model)}] to judge {len(todo)} (kept {len(results)}), max_tokens={mt}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fut = {ex.submit(_call_judge, it["original"], it["simplified"], model, api_key, mt): it
               for it in todo}
        done = 0
        for f in as_completed(fut):
            it = fut[f]
            results[it["row_id"]] = f.result()
            done += 1
            if done % 25 == 0 or done == len(todo):
                _save_candidate(out, model, items, results)
    _save_candidate(out, model, items, results)
    errs = sum(1 for v in results.values() if v not in ("SAFE", "UNSAFE"))
    print(f"  [{slug(model)}] done, ERROR rows = {errs} -> {out.name}", flush=True)
    return results


def band(d, lo, hi):
    if d >= 0.05 and lo > 0:
        return "POSITIVE"
    if d <= -0.02 and hi < 0:
        return "NEGATIVE"
    return "NULL/ATTENUATED"


def build_table(items, panel_path, out_dir):
    base = {(str(x["idx"]), x["tau"]): x
            for x in json.load(io.open(panel_path, encoding="utf-8"))["per_sample"]}
    cand = {}
    for m in CANDIDATES:
        p = Path(out_dir) / f"judgebench_v2_pool_{slug(m)}.json"
        cand[m] = {(str(r["idx"]), r["tau"]): r["verdict"]
                   for r in json.load(io.open(p, encoding="utf-8"))["verdicts"]}

    recs_b = [{"condition": it["condition"], "error_type": it["error_type"],
               "llama_verdict": base[(str(it["idx"]), it["tau"])]["llama_verdict"],
               "qwen_verdict":  base[(str(it["idx"]), it["tau"])]["qwen_verdict"]} for it in items]
    Xb, taub, _ = V.stratum(recs_b, "diagnosis", INCUMBENT)
    phi_inc = V.all_stats(Xb, taub)["phi_v"]

    rows = []
    for model in [NANO_MODEL] + list(CANDIDATES):     # Nano reused from base, then the 5
        recs = []
        for it in items:
            b = base[(str(it["idx"]), it["tau"])]
            cv = b["nemotron_verdict"] if model == NANO_MODEL else cand[model][(str(it["idx"]), it["tau"])]
            recs.append({"condition": it["condition"], "error_type": it["error_type"],
                         "llama_verdict": b["llama_verdict"], "qwen_verdict": b["qwen_verdict"],
                         "cand_verdict": cv})
        X, tau, dropped = V.stratum(recs, "diagnosis", INCUMBENT + ["cand_verdict"])
        point, cis = V.paired_delta_cis(X, tau, 2, np.random.default_rng(V.SEED), V.N_BOOT)
        phi_full = V.all_stats(X, tau)["phi_v"]
        pos = [r for r in recs if r["condition"] == "corrupted" and r["cand_verdict"] in ("SAFE", "UNSAFE")]
        neg = [r for r in recs if r["condition"] == "clean" and r["cand_verdict"] in ("SAFE", "UNSAFE")]
        rec = sum(1 for r in pos if r["cand_verdict"] == "UNSAFE")
        spc = sum(1 for r in neg if r["cand_verdict"] == "SAFE")
        lo, hi = cis["phi_v"]
        rows.append({"model": model, "slug": slug(model), "n": int(X.shape[0]), "dropped": int(dropped),
                     "candidate_recall_tau1": f"{rec}/{len(pos)}", "candidate_spec_tau0": f"{spc}/{len(neg)}",
                     "phi_incumbent_llama_qwen": round(phi_inc, 4), "phi_full": round(phi_full, 4),
                     "delta_phi_v": round(point["phi_v"], 4), "ci95": [round(lo, 4), round(hi, 4)],
                     "band": band(point["phi_v"], lo, hi)})
    rows.sort(key=lambda r: r["delta_phi_v"], reverse=True)
    payload = {"purpose": "6-candidate audit-pool delta-Phi_V recompute on clean JudgeBench v2 diagnosis stratum",
               "method": "vagt_core verbatim; incumbent Llama+Qwen from panel_gate; SEED=42 n_boot=1000; deployed prompt",
               "incumbent_phi_v_llama_qwen": round(phi_inc, 4),
               "recommended": rows[0]["model"], "candidates_ranked": rows}
    outp = Path(out_dir) / "judgebench_v2_pool_table.json"
    json.dump(payload, io.open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"\nincumbent Phi_V (Llama+Qwen) = {phi_inc:.4f}")
    print(f"{'candidate':34} {'n':>4} {'drop':>4} {'recT1':>7} {'specT0':>8} {'dPhi':>8} {'95% CI':>18}  band")
    for r in rows:
        ci = f"[{r['ci95'][0]:+.4f},{r['ci95'][1]:+.4f}]"
        print(f"{r['slug']:34} {r['n']:>4} {r['dropped']:>4} {r['candidate_recall_tau1']:>7} "
              f"{r['candidate_spec_tau0']:>8} {r['delta_phi_v']:>+8.4f} {ci:>18}  {r['band']}")
    print(f"\nrecommended (max dPhi): {rows[0]['slug']}\nSaved -> {outp}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tau1", default=str(_REPO / "results" / "judgebench_v2_tau1_final.json"))
    ap.add_argument("--controls", default=str(_REPO / "results" / "judgebench_v2_clean_controls.json"))
    ap.add_argument("--controls-filter", default="primary_paired")
    ap.add_argument("--panel", default=str(_REPO / "results" / "judgebench_v2_panel_gate.json"))
    ap.add_argument("--item-workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out-dir", default=str(_REPO / "results"))
    ap.add_argument("--analyze-only", action="store_true")
    args = ap.parse_args()

    items = canonical_items(args.tau1, args.controls, args.controls_filter)

    if args.analyze_only:
        build_table(items, args.panel, args.out_dir)
        return

    smoke = args.limit is not None
    if smoke:  # mixed subset: half tau=1, half tau=0; renumber row_id for the subset
        pos = [it for it in items if it["tau"] == 1][: math.ceil(args.limit / 2)]
        neg = [it for it in items if it["tau"] == 0][: args.limit // 2]
        items = pos + neg
        for i, it in enumerate(items):
            it["row_id"] = i

    api_key = os.environ.get("NEBIUS_API_KEY", "")
    if not api_key:
        sys.exit("ERROR: NEBIUS_API_KEY not set.")

    # fail-fast availability/param probe through _call_judge (catches 403 + enable_thinking 400s)
    for m in CANDIDATES:
        v = _call_judge("Patient given aspirin 81 mg daily.",
                        "Patient takes low-dose aspirin daily.", m, api_key, CANDIDATES[m])
        print(f"probe {slug(m):34} -> {v}", flush=True)
        if v not in ("SAFE", "UNSAFE"):
            sys.exit(f"ABORT: {m} probe returned {v} (403/param error?) — resolve before running.")

    prefix = "smoke_" if smoke else ""
    per_cand = {}
    for m in CANDIDATES:
        per_cand[m] = run_candidate(m, items, api_key, args.item_workers, args.out_dir, prefix)

    if smoke:
        # per-candidate verdict grid on the smoke items
        print("\n=== SMOKE VERDICT GRID ===")
        hdr = f"{'idx':10} {'tau':>3} | " + " ".join(f"{slug(m)[:14]:14}" for m in CANDIDATES)
        print(hdr)
        print("-" * len(hdr))
        for it in items:
            cells = " ".join(f"{per_cand[m].get(it['row_id'], 'MISSING'):14}" for m in CANDIDATES)
            print(f"{str(it['idx']):10} {it['tau']:>3} | {cells}")
        for m in CANDIDATES:
            errs = sum(1 for v in per_cand[m].values() if v not in ("SAFE", "UNSAFE"))
            print(f"  {slug(m):34} ERROR rows: {errs}")
        print("\nSMOKE DONE — verify all candidates returned SAFE/UNSAFE (not ERROR). Full pool NOT run.")
    else:
        build_table(items, args.panel, args.out_dir)


if __name__ == "__main__":
    main()
