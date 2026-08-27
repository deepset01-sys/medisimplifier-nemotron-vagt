"""prepare_hf_dataset.py — build the v2 Nemotron-taught HuggingFace dataset.

Converts nemotron_training_references.json into a HuggingFace DatasetDict that
matches the GuyDor007/medisimplifier-dataset schema, with the TEACHER SWAPPED:

  instruction  — copied verbatim from GuyDor007/medisimplifier-dataset. train.py
                 DROPS this column (its remove_columns list), but the column must
                 EXIST or that map() call KeyErrors — so we reproduce it exactly.
  input        — the original discharge summary (unchanged from v1).
  output       — nemotron_output. This is the whole point: the Claude Opus 4.5
                 reference is replaced by the Nemotron Super reference.

Splits train/validation/test are preserved (same names and row indices as
GuyDor007). Records whose nemotron_output is null or errored are SKIPPED, and the
filtered count is reported per split. A per-record input-match check against the
source dataset guards against index misalignment.

Pushes to:  chambul/medisimplifier-nemotron-dataset   (HuggingFace, free)

Requires HF_TOKEN with write access (or `huggingface-cli login`).

Usage:
  python prepare_hf_dataset.py --dry-run     # build + validate locally, no push
  python prepare_hf_dataset.py               # build + push to the Hub
"""

import os
import sys
import json
import argparse
from pathlib import Path

from datasets import load_dataset, Dataset, DatasetDict

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

SPLITS = ["train", "validation", "test"]
SRC_DATASET = "GuyDor007/medisimplifier-dataset"
TARGET_REPO = "chambul/medisimplifier-nemotron-dataset"


def load_source_lookup():
    """{(split, index): {'instruction':..., 'input':...}} from GuyDor007 — for the
    instruction column (copied) and an input-alignment sanity check."""
    ds = load_dataset(SRC_DATASET)
    lut = {}
    for split in SPLITS:
        for i, row in enumerate(ds[split]):
            lut[(split, i)] = {"instruction": row["instruction"], "input": row["input"]}
    print(f"Source {SRC_DATASET}: " + ", ".join(f"{s}={len(ds[s])}" for s in SPLITS))
    return lut


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="nemotron_training_references.json")
    ap.add_argument("--repo", default=TARGET_REPO)
    ap.add_argument("--dry-run", action="store_true", help="build + validate, do NOT push")
    ap.add_argument("--private", action="store_true", help="push as a private dataset")
    ap.add_argument("--hf-token", default=os.getenv("HF_TOKEN"))
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        sys.exit(f"input not found: {in_path} (run nemotron_training_data.py first)")
    records = json.loads(in_path.read_text(encoding="utf-8"))
    print(f"Loaded {len(records)} records from {in_path.name}")

    src = load_source_lookup()

    rows = {s: [] for s in SPLITS}          # kept rows, per split
    filtered = {s: 0 for s in SPLITS}       # skipped (null/errored output)
    mismatch = 0                            # input didn't match source (misalignment)
    missing_key = 0                         # (split,index) not in source

    for r in records:
        split, idx = r["split"], r["index"]
        # filter: skip errored / empty outputs
        if r.get("error") is not None or not r.get("nemotron_output"):
            filtered[split] = filtered.get(split, 0) + 1
            continue
        key = (split, idx)
        if key not in src:
            missing_key += 1
            continue
        if r["input"] != src[key]["input"]:      # index-alignment guard
            mismatch += 1
            continue
        rows[split].append({
            "instruction": src[key]["instruction"],   # copied from GuyDor007 (content irrelevant)
            "input": r["input"],                       # unchanged discharge summary
            "output": r["nemotron_output"],            # TEACHER SWAP: Nemotron Super
        })

    # ── report ───────────────────────────────────────────────────────────────
    print("\nBuild summary (kept / filtered per split):")
    total_kept = 0
    for s in SPLITS:
        total_kept += len(rows[s])
        print(f"  {s:<11} kept={len(rows[s]):<6} filtered(null/error)={filtered[s]}")
    print(f"  TOTAL kept={total_kept}  filtered={sum(filtered.values())}")
    if mismatch:
        print(f"  ⚠️  {mismatch} records dropped for input mismatch vs source (index misalignment!)")
    if missing_key:
        print(f"  ⚠️  {missing_key} records had a (split,index) not present in {SRC_DATASET}")

    if total_kept == 0:
        sys.exit("Nothing to push — all records filtered.")

    dd = DatasetDict({s: Dataset.from_list(rows[s]) for s in SPLITS})
    print(f"\nDatasetDict built. Features: {dd['train'].features}")
    ex = dd["train"][0]
    print("Example[train][0]:")
    print(f"  instruction[:60]: {ex['instruction'][:60]!r}")
    print(f"  input[:60]:       {ex['input'][:60]!r}")
    print(f"  output[:60]:      {ex['output'][:60]!r}")

    if args.dry_run:
        print("\n--dry-run: built and validated locally. NOT pushed.")
        return

    if not args.hf_token:
        sys.exit("HF_TOKEN not set — export it or pass --hf-token (or `huggingface-cli login`).")

    print(f"\nPushing to https://huggingface.co/datasets/{args.repo} "
          f"({'private' if args.private else 'public'}) ...")
    dd.push_to_hub(args.repo, token=args.hf_token, private=args.private)
    print("✓ Pushed. Update train.py line 109 to load this repo for the v2 run.")


if __name__ == "__main__":
    main()
