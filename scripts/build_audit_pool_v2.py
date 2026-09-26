#!/usr/bin/env python3
"""
build_audit_pool_v2.py — build audit_pool_v2/, the v2 clean-stratum /v1/audit_panel pool,
from the committed JudgeBench v2 result files. Offline: no API calls, no key.

Inputs (all committed):
  results/judgebench_v2_panel_gate.json        Llama / Qwen / Nemotron-Nano verdicts (per_sample, 240)
  results/judgebench_v2_pool_<slug>.json  x5   Ultra / Super / gpt-oss / DeepSeek / gemma (240 each)
  results/judgebench_v2_pool_table.json        reference numbers (candidates.yaml annotations + verify)
  results/judgebench_v2_phi_v_recompute.json   reference numbers (verify)

Outputs (same schema pool_loader.Pool.load() reads for audit_pool/):
  <out>/ground_truth.json      240 rows {row_id, idx, tau, stratum}
  <out>/verdicts/<slug>.json   8 files, 240 rows each {row_id, idx, verdict}
  <out>/candidates.yaml        manifest + v2 provenance (documentation; not read by the loader)

stratum is "diagnosis" for tau=1 rows and "clean" for tau=0 rows. pool_loader maps
stratum -> (condition, error_type) and vagt_core.stratum() derives tau from condition,
so labelling the controls "diagnosis" would silently score them as tau=1.

Join key is row_id (0..239): the canonical (tau, idx) order shared by panel_gate and the
pool files. idx is NOT unique (each patient appears as a drop and as its paired control).

Verification (default on; --no-verify to skip, needs numpy): reloads the written pool with
pool_loader and recomputes every candidate's diagnosis dPhi_V + CI exactly as
run_pool_judgebench_v2.build_table did; exits non-zero on any mismatch.
"""
import argparse
import collections
import io
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "results"

PANEL_GATE = RES / "judgebench_v2_panel_gate.json"
POOL_TABLE = RES / "judgebench_v2_pool_table.json"
PHI_RECOMPUTE = RES / "judgebench_v2_phi_v_recompute.json"

BENCHMARK = "MedSimp-JudgeBench-v2"   # v1 pool is "MedSimp-JudgeBench" — clients can tell them apart
N_EXPECTED = 240

# the three base judges, read from panel_gate per_sample (model id -> field)
BASE_MODELS = {
    "meta-llama/Llama-3.3-70B-Instruct": "llama_verdict",
    "Qwen/Qwen3-32B": "qwen_verdict",
    "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B": "nemotron_verdict",
}
# the five pool candidates, each in results/judgebench_v2_pool_<slug>.json
POOL_MODELS = [
    "nvidia/Nemotron-3-Ultra-550b-a55b",
    "nvidia/nemotron-3-super-120b-a12b",
    "openai/gpt-oss-120b",
    "deepseek-ai/DeepSeek-V4-Flash-0731",
    "google/gemma-3-27b-it",
]
INCUMBENT = ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"]   # reference panel of pool_table
VALID = {"SAFE", "UNSAFE", "ERROR"}


def slug(model):
    return model.split("/")[-1]


def load_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(obj, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fail(msg):
    raise SystemExit(f"ERROR: {msg}")


def build_ground_truth(per_sample):
    if len(per_sample) != N_EXPECTED:
        fail(f"panel_gate has {len(per_sample)} rows, expected {N_EXPECTED}")
    rows = []
    for row_id, s in enumerate(per_sample):
        tau = s["tau"]
        if tau == 1 and (s["condition"], s["error_type"]) != ("corrupted", "diagnosis"):
            fail(f"row {row_id}: tau=1 but condition/error_type = {s['condition']}/{s['error_type']}")
        if tau == 0 and s["condition"] != "clean":
            fail(f"row {row_id}: tau=0 but condition = {s['condition']}")
        rows.append({"row_id": row_id, "idx": s["idx"], "tau": tau,
                     "stratum": "diagnosis" if tau == 1 else "clean"})
    keys = [(str(r["idx"]), r["tau"]) for r in rows]
    if len(set(keys)) != len(keys):
        fail("(idx, tau) is not unique in panel_gate")
    return rows


def build_verdicts(gt_rows, panel):
    """model id -> (verdict rows, prompt provenance, source file name). Every pool file is
    checked to be aligned with ground truth on (row_id, idx, tau) before it is accepted."""
    out = {}
    per = panel["per_sample"]
    for model, field in BASE_MODELS.items():
        rows = [{"row_id": g["row_id"], "idx": g["idx"], "verdict": per[g["row_id"]][field]}
                for g in gt_rows]
        out[model] = (rows, f"{panel['prompt_source']} [panel_gate per_sample.{field}]", PANEL_GATE.name)
    for model in POOL_MODELS:
        path = RES / f"judgebench_v2_pool_{slug(model)}.json"
        pf = load_json(path)
        if pf["model"] != model:
            fail(f"{path.name}: model is {pf['model']!r}, expected {model!r}")
        v = pf["verdicts"]
        if len(v) != len(gt_rows):
            fail(f"{path.name}: {len(v)} rows, expected {len(gt_rows)}")
        for g, r in zip(gt_rows, v):
            if r["row_id"] != g["row_id"] or str(r["idx"]) != str(g["idx"]) or r["tau"] != g["tau"]:
                fail(f"{path.name}: row_id {g['row_id']} misaligned with panel_gate")
        rows = [{"row_id": g["row_id"], "idx": g["idx"], "verdict": r["verdict"]}
                for g, r in zip(gt_rows, v)]
        out[model] = (rows, pf["prompt"], path.name)
    for model, (rows, _, _) in out.items():
        bad = {r["verdict"] for r in rows} - VALID
        if bad:
            fail(f"{model}: unexpected verdict values {sorted(bad)}")
    return out


def candidates_yaml(verdicts, table):
    ref = {r["model"]: r for r in table["candidates_ranked"]}
    lines = [
        "# audit_pool_v2/candidates.yaml — /v1/audit_panel pool manifest, JudgeBench v2 (clean stratum).",
        "# GENERATED by scripts/build_audit_pool_v2.py — do not hand-edit; re-run the script.",
        "#",
        "# Stratum: 240 hand-verified items = 120 tau=1 patient-invisible PRIMARY-diagnosis drops",
        "#   + 120 tau=0 primary_paired controls (the pre-edit summary of the same patient).",
        "# Diagnosis ONLY: dose / negation / lateral were not rebuilt on clean labels. The v1 pool",
        "#   (audit_pool/, automated 708-item pass) is kept unchanged and is superseded for diagnosis.",
        "# All 8 judges ran the deployed gate prompt (safety_gate.JUDGE_PROMPT).",
        "# diagnosis_delta_phi_v / ci95: candidate appended to the Llama+Qwen incumbent, copied from",
        "#   results/judgebench_v2_pool_table.json (vagt_core, SEED=42, n_boot=1000, complete-case).",
        "# Recommendation (results/audit_panel_receipt_v2_diagnosis.json): DeepSeek (+0.1238) and",
        "#   gpt-oss (+0.1220) are statistically tied; gpt-oss is selected by fewest ERROR rows (0 vs 7).",
        "#   Specificity (88/120 vs 75/114) is the next key and is not reached. This tie-break was",
        "#   added to the selector after the v2 result was known.",
        f"benchmark: {BENCHMARK}",
        f"n: {N_EXPECTED}",
        "",
        "pooled:",
    ]
    for model in list(BASE_MODELS) + POOL_MODELS:
        rows, prov, src = verdicts[model]
        errors = sum(1 for r in rows if r["verdict"] == "ERROR")
        lines += [
            f"  - slug: {slug(model)}",
            f"    model: {model}",
            f"    source: results/{src}",
            f"    prompt_provenance: {json.dumps(prov, ensure_ascii=False)}",
            f"    error_rows: {errors}",
        ]
        if model in ref:
            r = ref[model]
            lines += [f"    diagnosis_delta_phi_v: {r['delta_phi_v']:.4f}",
                      f"    ci95: [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]"]
        else:
            lines.append(f"    role: incumbent in the reference panel "
                         f"(Llama+Qwen Phi_V {table['incumbent_phi_v_llama_qwen']:.4f})")
    lines += ["", "pending: []", ""]
    return "\n".join(lines)


def verify(out_dir, table, recompute):
    try:
        import numpy as np
    except ImportError:
        fail("verification needs numpy (pip install 'numpy==1.26.*'), or pass --no-verify")
    sys.path.insert(0, str(REPO / "src" / "audit_panel"))
    import vagt_core as V
    from pool_loader import Pool

    pool = Pool.load(out_dir)
    problems = []

    Xi, ti, _ = V.stratum(pool.records, "diagnosis", INCUMBENT)
    phi_inc = round(V.all_stats(Xi, ti)["phi_v"], 4)
    if phi_inc != table["incumbent_phi_v_llama_qwen"]:
        problems.append(f"incumbent Phi_V {phi_inc} != {table['incumbent_phi_v_llama_qwen']}")

    print(f"\nverify vs {POOL_TABLE.name} (incumbent Llama+Qwen Phi_V = {phi_inc:.4f})")
    got_by_model = {}
    for ref in table["candidates_ranked"]:
        model = ref["model"]
        X, tau, dropped = V.stratum(pool.records, "diagnosis", INCUMBENT + [model])
        point, cis = V.paired_delta_cis(X, tau, 2, np.random.default_rng(V.SEED), V.N_BOOT)
        lo, hi = cis["phi_v"]
        got = {"n": int(X.shape[0]), "dropped": int(dropped),
               "delta_phi_v": round(point["phi_v"], 4), "ci95": [round(lo, 4), round(hi, 4)]}
        want = {k: ref[k] for k in got}
        got_by_model[model] = got
        status = "OK " if got == want else "MISMATCH"
        print(f"  {status} {slug(model):32} n={got['n']:>3} drop={got['dropped']} "
              f"dPhi={got['delta_phi_v']:+.4f} CI=[{lo:+.4f}, {hi:+.4f}]")
        if got != want:
            problems.append(f"{model}: got {got}, want {want}")

    nano_ref = recompute["cells"]["deployed_full"]
    nano_got = got_by_model.get("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
    if nano_got is None or [nano_got["delta_phi_v"], nano_got["ci95"]] != [nano_ref["delta_phi_v"], nano_ref["ci95"]]:
        problems.append(f"Nano vs {PHI_RECOMPUTE.name} deployed_full: got {nano_got}, "
                        f"want {nano_ref['delta_phi_v']} {nano_ref['ci95']}")

    if problems:
        fail("verification failed:\n  " + "\n  ".join(problems))
    print(f"VERIFY OK — {len(got_by_model)} candidates reproduce {POOL_TABLE.name}; "
          f"Nano reproduces {PHI_RECOMPUTE.name} deployed_full")


def main():
    ap = argparse.ArgumentParser(description="Build audit_pool_v2/ from committed JudgeBench v2 results.")
    ap.add_argument("--out", default=str(REPO / "audit_pool_v2"), help="output pool directory")
    ap.add_argument("--force", action="store_true", help="write into a non-empty --out directory")
    ap.add_argument("--no-verify", action="store_true", help="skip the numpy reproduction check")
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists() and any(out.iterdir()) and not args.force:
        fail(f"{out} exists and is not empty (use --force to overwrite)")

    panel = load_json(PANEL_GATE)
    table = load_json(POOL_TABLE)
    recompute = load_json(PHI_RECOMPUTE)

    gt_rows = build_ground_truth(panel["per_sample"])
    verdicts = build_verdicts(gt_rows, panel)

    write_json({
        "benchmark": BENCHMARK,
        "n": len(gt_rows),
        "strata": ["diagnosis", "clean"],
        "note": ("JudgeBench v2 clean stratum: 120 tau=1 hand-verified primary-diagnosis drops + "
                 "120 tau=0 primary_paired controls. Join key is row_id; idx is NOT unique (each "
                 "patient appears as a drop and as its paired control). stratum='clean' => tau=0."),
        "rows": gt_rows,
    }, out / "ground_truth.json")

    for model, (rows, prov, src) in verdicts.items():
        write_json({
            "model": model,
            "slug": slug(model),
            "benchmark": BENCHMARK,
            "n": len(rows),
            "prompt_provenance": prov,
            "source": f"results/{src}",
            "verdicts": rows,
        }, out / "verdicts" / f"{slug(model)}.json")

    with io.open(out / "candidates.yaml", "w", encoding="utf-8", newline="\n") as f:
        f.write(candidates_yaml(verdicts, table))

    tau = collections.Counter(r["tau"] for r in gt_rows)
    strata = collections.Counter(r["stratum"] for r in gt_rows)
    print(f"audit_pool_v2 written -> {out}")
    print(f"  rows:   {len(gt_rows)}   tau=1: {tau[1]}   tau=0: {tau[0]}   strata: {dict(strata)}")
    print(f"  models: {len(verdicts)}")
    for model, (rows, _, src) in verdicts.items():
        c = collections.Counter(r["verdict"] for r in rows)
        print(f"    {slug(model):32} SAFE {c['SAFE']:>3}  UNSAFE {c['UNSAFE']:>3}  "
              f"ERROR {c['ERROR']:>2}   <- {src}")

    if not args.no_verify:
        verify(out, table, recompute)


if __name__ == "__main__":
    main()
