"""
gen_pool_verdicts.py — generate one candidate judge's 708-row audit_pool verdict file (Step 6).

Reuses the EXACT judge protocol from nemotron_judge_test.py — JUDGE_SYSTEM + JUDGE_PROMPT,
temp 0, response_format=json_object — imported verbatim, NOT forked. That is the same prompt
that scored the reference third-rater (Nemotron Nano), so a candidate's ΔΦ_V is directly
comparable to the published +0.071 receipt. (The gate prompt in safety_gate.py is the DEPLOYED
artifact and would confound a calibration-pool comparison — deliberately not used here.)

Row order is CANONICAL and comes from audit_pool/ground_truth.json (row_id 0..707) — the pool's
only join key. The (input, perturbed) text per row is looked up from calibration_verdicts.json
by (idx, condition, error_type); that key's uniqueness is ASSERTED and any missing/duplicate key
ABORTS the run (row_id must never be silently misaligned — misalignment corrupts every ΔΦ_V).

Output schema is byte-parity with audit_pool/verdicts/Qwen3-32B.json:
  {model, slug, benchmark, n, prompt_provenance, verdicts:[{row_id, idx, verdict}, ...]}
(in-progress checkpoints add a transient top-level "status"; the COMPLETE file omits it to match.)

Checkpoint/resume: every --checkpoint-every completed calls the full file is rewritten; a re-run
reloads it and re-judges only rows whose verdict is missing or ERROR (valid verdicts are kept).

After a FULL (n=708) run it self-validates with vagt_core:
  (a) the new file's every (row_id, idx) equals ground_truth  -> alignment proof;
  (b) the incumbent Llama+Qwen -> Nemotron diagnosis ΔΦ_V is still 0.071 ± 1e-3 -> harness/pool intact;
  (c) prints THIS candidate's per-stratum ΔΦ_V added to Llama+Qwen (informational).

Smoke:  python src/audit_panel/gen_pool_verdicts.py --model google/gemma-3-27b-it \
            --slug gemma-3-27b-it --max-tokens 4000 --n 20 --output /tmp/smoke_gemma.json
Full:   python src/audit_panel/gen_pool_verdicts.py --model google/gemma-3-27b-it \
            --slug gemma-3-27b-it --max-tokens 4000 --n 708 --workers 12
Requires NEBIUS_API_KEY (or --nebius-api-key).
"""

import argparse
import json
import os
import re
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# --- paths / imports (repo root for the prompt, this dir for vagt_core) ---
_HERE = Path(__file__).resolve().parent          # src/audit_panel
_REPO = _HERE.parents[1]                          # repo root
sys.path.insert(0, str(_REPO))                    # nemotron_judge_test.py lives at repo root
sys.path.insert(0, str(_HERE))                    # vagt_core.py lives here
from nemotron_judge_test import JUDGE_SYSTEM, JUDGE_PROMPT  # noqa: E402  (reuse verbatim)
import vagt_core as vc                                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
POOL_DIR = _REPO / "audit_pool"
GT_PATH = POOL_DIR / "ground_truth.json"
VERDICTS_DIR = POOL_DIR / "verdicts"
VALID = {"SAFE", "UNSAFE"}
PROVENANCE = "nemotron_judge_test.py step-by-step JSON prompt (max_tokens={mt})"

# calibration_verdicts.json (the TEXT source — input/perturbed per row); same locations
# nemotron_judge_test.py uses.
DATA_CANDIDATES = [
    Path(r"D:\Owner\Desktop\assignment_01\medisimplifier-nebius\results"
         r"\nebius_evidence\calibration_verdicts.json"),
    _REPO / "results" / "nebius_evidence" / "calibration_verdicts.json",
]

# Incumbent pool columns (for the 0.071 self-check), mirroring build_pool.py.
INCUMBENTS = {
    "Llama-3.3-70B-Instruct": "Llama-3.3-70B-Instruct_verdict",
    "Qwen3-32B": "Qwen3-32B_verdict",
    "NVIDIA-Nemotron-3-Nano-30B-A3B": "NVIDIA-Nemotron-3-Nano-30B-A3B_verdict",
}


def _stratum_to_ce(stratum):
    """Inverse of build_pool._stratum_of: stratum -> (condition, error_type)."""
    return ("clean", "none") if stratum == "clean" else ("corrupted", stratum)


def load_rows():
    """Canonical rows in row_id order from ground_truth.json: [{row_id, idx, stratum, tau}]."""
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))["rows"]
    return sorted(gt, key=lambda r: r["row_id"])


def load_text_lookup(data_arg):
    """(idx, condition, error_type) -> record; abort if that key is not unique."""
    candidates = [Path(data_arg)] if data_arg else DATA_CANDIDATES
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        sys.exit("calibration_verdicts.json not found; tried: "
                 + ", ".join(str(p) for p in candidates))
    recs = json.loads(path.read_text(encoding="utf-8"))
    lut = {}
    for r in recs:
        key = (r["idx"], r["condition"], r["error_type"])
        if key in lut:
            sys.exit(f"FATAL: duplicate join key {key} in {path.name} — "
                     "(idx, condition, error_type) is not unique, so row_id alignment cannot "
                     "be guaranteed. Aborting rather than risk a corrupted pool.")
        lut[key] = r
    return lut, path


def _parse_verdict(content):
    """Robust extraction: strip reasoning </think> prefix and ```fences, then JSON, then regex."""
    if content is None:
        return "ERROR"
    raw = content
    if "</think>" in raw:
        raw = raw.split("</think>")[-1]
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    obj = None
    try:
        obj = json.loads(raw)
    except Exception:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
            except Exception:
                obj = None
    if not isinstance(obj, dict):
        return "ERROR"
    v = str(obj.get("verdict", "ERROR")).upper()
    return v if v in VALID else "ERROR"


def judge(original, simplified, api_key, model, max_tokens, max_retries=3):
    """One Token Factory judge call (same shape as nemotron_judge_test.llm_judge_eval)."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": JUDGE_PROMPT.format(original=original, simplified=simplified)},
        ],
        "max_tokens": max_tokens,      # reasoners think first — budget must clear that (see plan)
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    for attempt in range(max_retries):
        try:
            r = requests.post(NEBIUS_API_URL, json=payload, headers=headers, timeout=120)
            if not r.ok:
                raise ValueError(f"HTTP {r.status_code}: {r.text[:300]}")
            content = r.json()["choices"][0]["message"]["content"]
            return _parse_verdict(content)
        except Exception:
            if attempt == max_retries - 1:
                return "ERROR"
            time.sleep(2 ** attempt)


def load_existing(out_path):
    """Resume map: row_id -> verdict already recorded (valid or ERROR)."""
    if not out_path.exists():
        return {}
    try:
        d = json.loads(out_path.read_text(encoding="utf-8"))
        return {v["row_id"]: v["verdict"] for v in d.get("verdicts", [])}
    except Exception:
        return {}


def validate(slug):
    """Full-run self-check: alignment vs ground_truth + incumbent 0.071 + candidate ΔΦ_V."""
    gt = json.loads(GT_PATH.read_text(encoding="utf-8"))["rows"]
    merged, gt_idx = {}, {}
    for row in gt:
        cond, etype = _stratum_to_ce(row["stratum"])
        merged[row["row_id"]] = {"idx": row["idx"], "condition": cond, "error_type": etype}
        gt_idx[row["row_id"]] = row["idx"]

    cand_col = f"{slug}_verdict"
    files = {**{s: c for s, c in INCUMBENTS.items()}, slug: cand_col}
    for s, col in files.items():
        vf = json.loads((VERDICTS_DIR / f"{s}.json").read_text(encoding="utf-8"))
        for v in vf["verdicts"]:
            merged[v["row_id"]][col] = v["verdict"]
            # (a) alignment proof — the new file's (row_id, idx) must equal ground_truth
            if s == slug and v["idx"] != gt_idx.get(v["row_id"]):
                print(f"  ALIGNMENT FAIL: row_id {v['row_id']} idx {v['idx']} "
                      f"!= ground_truth idx {gt_idx.get(v['row_id'])}", flush=True)
                return False

    records = [merged[i] for i in sorted(merged)]
    llama, qwen, nemo = (INCUMBENTS["Llama-3.3-70B-Instruct"],
                         INCUMBENTS["Qwen3-32B"],
                         INCUMBENTS["NVIDIA-Nemotron-3-Nano-30B-A3B"])

    # (b) harness/pool intact — incumbent receipt must still reproduce
    inc = vc.delta_by_stratum(records, [llama, qwen], nemo)
    diag = inc["diagnosis"]["delta"]["phi_v"]
    ok = abs(diag - 0.071) <= 1e-3
    print(f"  incumbent diagnosis ΔΦ_V = {diag:+.4f}  | target 0.071 ± 1e-3 -> "
          f"{'PASS ✅' if ok else 'FAIL ❌'}")

    # (c) informational — this candidate added to Llama+Qwen
    cand = vc.delta_by_stratum(records, [llama, qwen], cand_col)
    print(f"\n  Candidate '{slug}' added to Llama+Qwen — ΔΦ_V per stratum:")
    for f in vc.STRATA:
        d = cand[f]["delta"]["phi_v"]
        print(f"    {f:10} n={cand[f]['n']:>3}  ΔΦ_V={d:+.4f}  "
              f"(Φ_V {cand[f]['phi_incumbent']:.3f} -> {cand[f]['phi_full']:.3f})")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="full Token Factory model string")
    ap.add_argument("--slug", required=True, help="verdict filename stem (audit_pool/verdicts/<slug>.json)")
    ap.add_argument("--max-tokens", type=int, required=True, dest="max_tokens")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--n", type=int, default=708, help="rows to judge (first N in row_id order; 20 for smoke)")
    ap.add_argument("--checkpoint-every", type=int, default=50, dest="checkpoint_every")
    ap.add_argument("--data", default=None, help="path to calibration_verdicts.json")
    ap.add_argument("--output", default=None, help="output path (default audit_pool/verdicts/<slug>.json)")
    ap.add_argument("--nebius-api-key", default=os.getenv("NEBIUS_API_KEY"), dest="api_key")
    args = ap.parse_args()

    if not args.api_key:
        sys.exit("ERROR: NEBIUS_API_KEY not set (export it or pass --nebius-api-key).")

    out_path = Path(args.output) if args.output else (VERDICTS_DIR / f"{args.slug}.json")

    rows = load_rows()
    lut, data_path = load_text_lookup(args.data)
    for r in rows:                                   # attach text; abort on any missing row
        cond, etype = _stratum_to_ce(r["stratum"])
        rec = lut.get((r["idx"], cond, etype))
        if rec is None:
            sys.exit(f"FATAL: no text for row_id={r['row_id']} idx={r['idx']} ({cond}, {etype}) "
                     f"in {data_path.name} — cannot judge this row.")
        r["_original"] = rec["input"]
        r["_simplified"] = rec["perturbed"]          # clean rows: perturbed == clean_ref
    rows = rows[:args.n]                             # smoke = first N in canonical order

    done = load_existing(out_path)
    todo = [r for r in rows if done.get(r["row_id"]) not in VALID]
    print(f"{args.slug}: {len(rows)} canonical rows | {len(rows) - len(todo)} already valid | "
          f"{len(todo)} to judge (model={args.model}, max_tokens={args.max_tokens}, "
          f"workers={args.workers}). Text from {data_path.name}.", flush=True)

    results = dict(done)
    lock = threading.Lock()

    def write(status=None):
        verdicts = [{"row_id": r["row_id"], "idx": r["idx"],
                     "verdict": results.get(r["row_id"], "ERROR")} for r in rows]
        payload = {
            "model": args.model, "slug": args.slug, "benchmark": "MedSimp-JudgeBench",
            "n": len(rows), "prompt_provenance": PROVENANCE.format(mt=args.max_tokens),
            "verdicts": verdicts,
        }
        if status is not None:                       # transient key only during the run
            payload["status"] = status
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    t0, completed = time.time(), 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(judge, r["_original"], r["_simplified"], args.api_key,
                          args.model, args.max_tokens): r for r in todo}
        for fut in as_completed(futs):
            r = futs[fut]
            v = fut.result()
            with lock:
                results[r["row_id"]] = v
                completed += 1
                if completed % args.checkpoint_every == 0 or completed == len(todo):
                    write("in_progress")
                    n_err = sum(1 for rr in rows if results.get(rr["row_id"]) not in VALID)
                    print(f"  [{completed}/{len(todo)}] {(time.time()-t0)/60:.1f}m | "
                          f"non-valid so far={n_err}", flush=True)

    write(status=None)                               # final file — exact schema, no status key
    dist = Counter(results.get(r["row_id"], "ERROR") for r in rows)
    n_err = sum(1 for r in rows if results.get(r["row_id"]) not in VALID)
    print(f"\nDONE — wrote {out_path}  (n={len(rows)}, dist={dict(dist)}, non-valid={n_err})")

    if len(rows) == 708 and out_path == VERDICTS_DIR / f"{args.slug}.json":
        print("\nSelf-validation (vagt_core):")
        ok = validate(args.slug)
        print("\n" + ("✅ pool intact + aligned — safe to commit."
                      if ok else "❌ CHECK FAILED — do NOT commit; investigate alignment."))
        return 0 if ok else 1
    else:
        print("\n(Smoke/partial or custom --output: skipped the 708-row vagt_core validation.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
