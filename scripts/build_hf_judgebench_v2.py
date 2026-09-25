#!/usr/bin/env python3
"""
build_hf_judgebench_v2.py — build the verified HuggingFace release of MedSimp-JudgeBench v2.

Joins every item in the committed v2 files with its source row in
GuyDor007/medisimplifier-dataset (test split, pinned revision) to recover the `input`
field, verifies the join item by item, and writes release files. NO UPLOAD.

Inputs (committed):
  results/judgebench_v2_tau1_final.json      120 τ=1 drops
  results/judgebench_v2_clean_controls.json  292 τ=0 controls (120 primary_paired + 172 supplementary)

Join rule: idx "hf<N>" -> test row N; numeric idx N -> test row N.
Verify rule (every item): item.clean_ref == source_row.output (exact string match).
Any mismatch, missing row, duplicate key, or count deviation -> print details and exit 1
BEFORE writing anything.

Outputs (default --out hf_release/MedSimp-JudgeBench-v2/, not committed):
  data/drops.jsonl      120 rows
  data/controls.jsonl   292 rows
  README.md             docs/README_hf_v2.md with the "[PENDING BUILD CHECK: N / 412 matched]"
                        placeholder replaced by the verified count
  manifest.json         source repo + revision, counts, match result, sha256 of each data file

Run:  python scripts/build_hf_judgebench_v2.py [--out DIR] [--revision SHA]
"""
import argparse
import hashlib
import io
import json
import sys
from pathlib import Path

from datasets import load_dataset

REPO = Path(__file__).resolve().parent.parent
TAU1 = REPO / "results" / "judgebench_v2_tau1_final.json"
CTRL = REPO / "results" / "judgebench_v2_clean_controls.json"
CARD = REPO / "docs" / "README_hf_v2.md"
SOURCE = "GuyDor007/medisimplifier-dataset"
SOURCE_REVISION = "fe6045352eb43aaad80bb1bf740684c0e1730551"   # HF commit at build time
PLACEHOLDER = "[PENDING BUILD CHECK: N / 412 matched]"
EXPECT = {"drops": 120, "controls": 292, "primary_paired": 120, "supplementary_unpaired": 172, "test_rows": 1001}

DROP_FIELDS = ["idx", "origin", "input", "target", "target_type", "clean_ref", "edited_summary",
               "expert_recoverable", "category_retained", "patient_recoverable", "human_verdict", "source_batch"]
CTRL_FIELDS = ["idx", "origin", "input", "clean_ref", "tau", "control_type", "paired_with"]


def fail(msg):
    sys.exit(f"ERROR: {msg}")


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)["items"]


def row_index(idx):
    s = str(idx)
    n = s[2:] if s.startswith("hf") else s
    if not n.isdigit():
        fail(f"unparseable idx {idx!r}")
    return int(n)


def join_and_verify(items, test, kind):
    out, mismatches = [], []
    for it in items:
        n = row_index(it["idx"])
        if n >= len(test):
            fail(f"{kind} idx {it['idx']!r} -> row {n} out of range ({len(test)} rows)")
        src = test[n]
        if src["output"] != it["clean_ref"]:
            mismatches.append((it["idx"], n))
        rec = dict(it)
        rec["idx"] = str(it["idx"])                      # uniform string column (source mixes str/int)
        if rec.get("paired_with") is not None:
            rec["paired_with"] = str(rec["paired_with"])
        rec["input"] = src["input"]
        out.append(rec)
    return out, mismatches


def write_jsonl(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps({k: r.get(k) for k in fields}, ensure_ascii=False) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description="Build the verified HF release of JudgeBench v2 (no upload).")
    ap.add_argument("--out", default=str(REPO / "hf_release" / "MedSimp-JudgeBench-v2"))
    ap.add_argument("--revision", default=SOURCE_REVISION)
    args = ap.parse_args()

    drops, ctrls = load(TAU1), load(CTRL)
    # ---- structural checks (before any network call)
    if len(drops) != EXPECT["drops"] or len(ctrls) != EXPECT["controls"]:
        fail(f"counts {len(drops)} drops / {len(ctrls)} controls, expected 120 / 292")
    types = {t: sum(c["control_type"] == t for c in ctrls) for t in ("primary_paired", "supplementary_unpaired")}
    if types != {"primary_paired": 120, "supplementary_unpaired": 172}:
        fail(f"control types {types}")
    drop_ids = {str(d["idx"]) for d in drops}
    if len(drop_ids) != 120:
        fail("duplicate τ=1 idx")
    for c in ctrls:
        if c["control_type"] == "primary_paired":
            if str(c["paired_with"]) not in drop_ids:
                fail(f"primary control {c['idx']!r} pairs with unknown τ=1 {c['paired_with']!r}")
        elif c["paired_with"] is not None:
            fail(f"supplementary control {c['idx']!r} has paired_with={c['paired_with']!r}")
    if len({str(c["idx"]) for c in ctrls}) != 292:
        fail("duplicate control idx")

    # ---- source (pinned revision)
    test = load_dataset(SOURCE, split="test", revision=args.revision)
    if len(test) != EXPECT["test_rows"]:
        fail(f"source test split has {len(test)} rows, expected 1001")

    drops_out, mm_d = join_and_verify(drops, test, "drop")
    ctrls_out, mm_c = join_and_verify(ctrls, test, "control")
    matched = 412 - len(mm_d) - len(mm_c)
    print(f"join: {matched} / 412 matched (drops {120 - len(mm_d)}/120, controls {292 - len(mm_c)}/292)")
    if mm_d or mm_c:
        for kind, mm in (("drop", mm_d), ("control", mm_c)):
            for idx, n in mm[:10]:
                print(f"  MISMATCH {kind} idx={idx!r} -> row {n}")
        fail("clean_ref != source output for at least one item — nothing written")

    # ---- write (only after 412/412)
    out = Path(args.out)
    sha_d = write_jsonl(out / "data" / "drops.jsonl", drops_out, DROP_FIELDS)
    sha_c = write_jsonl(out / "data" / "controls.jsonl", ctrls_out, CTRL_FIELDS)
    card = io.open(CARD, encoding="utf-8").read()
    if card.count(PLACEHOLDER) != 1:
        fail("card placeholder not found exactly once")
    io.open(out / "README.md", "w", encoding="utf-8", newline="\n").write(
        card.replace(PLACEHOLDER, f"{matched} / 412 matched"))
    manifest = {"source": SOURCE, "source_split": "test", "source_revision": args.revision,
                "counts": {"drops": len(drops_out), "controls": len(ctrls_out), **types},
                "join_matched": f"{matched}/412",
                "files": {"data/drops.jsonl": sha_d, "data/controls.jsonl": sha_c}}
    io.open(out / "manifest.json", "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {out} — drops.jsonl (sha256 {sha_d[:12]}…), controls.jsonl (sha256 {sha_c[:12]}…), README.md, manifest.json")
    print("NO UPLOAD performed.")


if __name__ == "__main__":
    main()
