"""nemotron_training_data.py — Nemotron Super references for the FULL training set.

Generates NVIDIA Nemotron-3 Super reference simplifications for every record in
GuyDor007/medisimplifier-dataset (train 7999 / validation 999 / test 1001), so
students can later be fine-tuned on Nemotron references instead of the original
Claude Opus references. Emits BOTH outputs per record for a direct comparison.

Single source of truth: the teacher prompt and the per-call logic (truncation
guard on finish_reason=length, U+2011 hyphen normalization, 3x retry) are
IMPORTED verbatim from nemotron_teacher.py — not re-typed here.

Config (per spec): model nvidia/nemotron-3-super-120b-a12b, max_tokens 16000,
temperature 0, 12 workers, checkpoint every 50. To avoid paying for duplicate
discharge summaries, one API call is made per UNIQUE `input` text and fanned out
to every dataset row sharing it; every row still receives a nemotron_output.

Output: nemotron_training_references.json — list of records:
  {split, index, input, claude_output, nemotron_output, error}

Usage:
  python nemotron_training_data.py --limit 5            # smoke test (5 unique inputs)
  python nemotron_training_data.py --workers 12         # full run
Requires NEBIUS_API_KEY in env (or --nebius-api-key).
"""

import os
import sys
import json
import time
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from datasets import load_dataset
from openai import OpenAI

# EXACT teacher prompt + call logic, imported (single source of truth).
from nemotron_teacher import SIMPLIFICATION_INSTRUCTION, simplify_text, MODEL, BASE_URL, TEMPERATURE

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

DATASET = "GuyDor007/medisimplifier-dataset"
SPLITS = ["train", "validation", "test"]
DEFAULT_MAX_TOKENS = 16000


def load_records():
    """Every dataset row as {split, index, input, claude_output}, plus the ordered
    list of UNIQUE input texts to call once."""
    ds = load_dataset(DATASET)
    records = []
    for split in SPLITS:
        for i, row in enumerate(ds[split]):
            records.append({"split": split, "index": i,
                            "input": row["input"], "claude_output": row["output"]})
    unique_inputs = list(dict.fromkeys(r["input"] for r in records))
    print(f"Loaded {len(records)} records "
          f"({', '.join(f'{s}={len(ds[s])}' for s in SPLITS)}); "
          f"{len(unique_inputs)} unique input texts")
    return records, unique_inputs


def load_existing(out_path):
    """Resume support: preload already-completed inputs from a prior output file.
    Only SUCCESSFUL rows (error is None, non-empty output) are reused; errored
    inputs are left out so they get retried. Returns {input_text: (output, None)}."""
    if not out_path.exists():
        return {}
    try:
        prior = json.loads(out_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        print(f"  (existing {out_path.name} unreadable — starting fresh)")
        return {}
    done = {}
    for r in prior:
        if r.get("error") is None and r.get("nemotron_output"):
            done[r["input"]] = (r["nemotron_output"], None)
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process first N unique inputs (smoke test)")
    ap.add_argument("--workers", type=int, default=12, help="concurrent workers")
    ap.add_argument("--checkpoint-every", type=int, default=50, help="write partial output every N completed calls")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="max output tokens per call")
    ap.add_argument("--output", default="nemotron_training_references.json")
    ap.add_argument("--no-resume", action="store_true", help="ignore any existing output file")
    ap.add_argument("--nebius-api-key", default=os.getenv("NEBIUS_API_KEY"))
    args = ap.parse_args()

    if not args.nebius_api_key:
        sys.exit("ERROR: NEBIUS_API_KEY not set (export it or pass --nebius-api-key)")

    records, unique_inputs = load_records()
    if args.limit is not None:
        unique_inputs = unique_inputs[:args.limit]
        keep = set(unique_inputs)
        records = [r for r in records if r["input"] in keep]
    n_out = len(records)

    client = OpenAI(base_url=BASE_URL, api_key=args.nebius_api_key)
    out_path = Path(args.output)
    lock = threading.Lock()

    # RESUME: preload completed inputs, only call the remainder.
    result_map = {} if args.no_resume else load_existing(out_path)
    todo = [txt for txt in unique_inputs if txt not in result_map]
    n_resumed = len(unique_inputs) - len(todo)
    n_calls = len(todo)

    print(f"\nGenerating Nemotron Super references with {MODEL}")
    if n_resumed:
        print(f"RESUME: {n_resumed} inputs already in {out_path.name}; {n_calls} remaining to call")
    print(f"API calls: {n_calls} unique inputs -> fanned out to {n_out} output records")
    print(f"max_tokens={args.max_tokens} temperature={TEMPERATURE} | "
          f"workers={args.workers} | checkpoint every {args.checkpoint_every} | output={args.output}")
    print("(Nemotron Super is a reasoning model; truncated/empty outputs are retried, "
          "not saved.)", flush=True)

    def build_rows():
        rows = []
        for r in records:
            if r["input"] in result_map:
                simp, err = result_map[r["input"]]
                rows.append({"split": r["split"], "index": r["index"], "input": r["input"],
                             "claude_output": r["claude_output"],
                             "nemotron_output": simp, "error": err})
        return rows

    def write_out():
        out_path.write_text(json.dumps(build_rows(), indent=2, ensure_ascii=False),
                            encoding="utf-8")

    if n_calls == 0:
        print("Nothing to do — all inputs already present in the output file.")
        write_out()
        return

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut_to_text = {ex.submit(simplify_text, client, txt, args.max_tokens): txt
                       for txt in todo}
        done = 0
        for fut in as_completed(fut_to_text):
            txt = fut_to_text[fut]
            simp, err = fut.result()
            with lock:
                result_map[txt] = (simp, err)
                done += 1
                n_err = sum(1 for s, e in result_map.values() if e is not None)
                if done % 10 == 0 or done == n_calls or n_err <= 5:
                    elapsed = time.time() - t0
                    eta = (n_calls - done) / (done / max(1e-9, elapsed)) if done else 0.0
                    tag = "OK " if err is None else "ERR"
                    print(f"  [{done:>4}/{n_calls}] {tag} "
                          f"elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m errors={n_err}"
                          + (f"  <- {err[:80]}" if err else ""), flush=True)
                if done % args.checkpoint_every == 0 or done == n_calls:
                    write_out()

    write_out()
    rows = build_rows()
    n_call_err = sum(1 for s, e in result_map.values() if e is not None)
    n_call_ok = n_calls - n_call_err
    n_rows_ok = sum(1 for r in rows if r["error"] is None)
    avg_nemo = (sum(len(r["nemotron_output"]) for r in rows if r["error"] is None)
                / max(1, n_rows_ok))
    avg_claude = sum(len(r["claude_output"]) for r in rows) / max(1, len(rows))
    print("\n" + "=" * 60)
    print("TRAINING-DATA REFERENCE GENERATION RESULTS")
    print("=" * 60)
    print(f"Model:            {MODEL}")
    print(f"Output records:   {len(rows)}  (target {n_out})")
    print(f"Unique API calls: {n_call_ok}/{n_calls} succeeded, {n_call_err} errored")
    print(f"Records w/ valid nemotron_output: {n_rows_ok}/{len(rows)}")
    print(f"Avg length: nemotron={avg_nemo:.0f} chars vs claude={avg_claude:.0f} chars")
    print(f"Saved to:         {out_path.resolve()}")
    if n_call_err == n_calls:
        print("\n>>> FAIL: every call errored. If 'finish_reason=length', raise --max-tokens.")
    elif n_call_err > 0:
        print(f"\n>>> PARTIAL: {n_call_err} unique input(s) errored (see `error` fields).")
    else:
        print("\n>>> PASS: all unique inputs simplified; every record has a nemotron_output.")


if __name__ == "__main__":
    main()
