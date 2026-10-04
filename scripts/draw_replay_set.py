"""
Draw the replay set as docs/replay_set.md fixes it, once, before the replay recording: Part A, 12 evaluation inputs
(four per input-length third); Part B, 16 JudgeBench v2 pairs (four per cell of the committed deployed-gate
consensus) after the rule's overlap exclusions. Writes indices only, no text, to results/replay_set_draw.json, with
the rule's commit, the Python version number and the sha256 of each input file (LF line endings, as git stores
them). The file is written with LF line endings and fixed relative paths, so the same Python version gives the same
bytes on any operating system.

    python scripts/draw_replay_set.py
"""
import hashlib
import json
import platform
import random
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREDICTIONS = "results/student_predictions.json"
PANEL = "results/judgebench_v2_panel_gate.json"
RULE = "docs/replay_set.md"
OUT = REPO / "results" / "replay_set_draw.json"
FLAGGED = ("UNSAFE", "DISAGREE")
CELLS = ("drop caught", "drop missed", "control falsely flagged", "control correctly passed")


def load(rel):
    raw = (REPO / rel).read_bytes()
    return json.loads(raw), "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def note_index(idx):
    """The evaluation input a Part B item was built from: idx "hf<N>" and a numeric idx "N" both name index N."""
    return int(idx[2:]) if idx.startswith("hf") else int(idx)


def cell_of(row):
    flagged = row["consensus"] in FLAGGED
    if row["tau"] == 1:
        return "drop caught" if flagged else "drop missed"
    return "control falsely flagged" if flagged else "control correctly passed"


def main():
    rows, sha_rows = load(PREDICTIONS)
    panel, sha_panel = load(PANEL)
    rule_sha = "sha256:" + hashlib.sha256((REPO / RULE).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    rule_commit = subprocess.run(["git", "log", "-1", "--format=%H", "--", RULE], cwd=REPO,
                                 capture_output=True, text=True, check=True).stdout.strip()

    # Part A: the 1,001 inputs by length in characters, ties by index; 334 short, 333 middle, 334 long
    ordered = [r["index"] for r in sorted(rows, key=lambda r: (len(r["input"]), r["index"]))]
    strata = {"short": ordered[:334], "middle": ordered[334:667], "long": ordered[667:]}
    rng_a = random.Random(42)
    part_a = {name: rng_a.sample(sorted(indices), 4) for name, indices in strata.items()}

    # Part B: cells from the committed consensus; items built from Part A's inputs removed; then, before each control
    # cell, every idx already drawn in the two drop cells removed
    assert all(r["consensus"] != "ERROR" for r in panel["per_sample"]), "the rule's cells do not cover ERROR"
    cells = {name: [] for name in CELLS}
    for r in panel["per_sample"]:
        cells[cell_of(r)].append((r["idx"], r["condition"]))
    part_a_indices = {i for picks in part_a.values() for i in picks}
    removed = {"built_from_part_a_inputs": 0, "idx_drawn_as_a_drop": 0}
    rng_b = random.Random(42)
    part_b, drop_idx = {}, set()
    for name in CELLS:
        keys = [k for k in cells[name] if note_index(k[0]) not in part_a_indices]
        removed["built_from_part_a_inputs"] += len(cells[name]) - len(keys)
        if name.startswith("control"):
            kept = [k for k in keys if k[0] not in drop_idx]
            removed["idx_drawn_as_a_drop"] += len(keys) - len(kept)
            keys = kept
        part_b[name] = [list(k) for k in rng_b.sample(sorted(keys), 4)]
        if name.startswith("drop"):
            drop_idx.update(k[0] for k in part_b[name])

    out = {
        "description": "The replay set drawn once by the rule in docs/replay_set.md; identifiers only.",
        "generated_by": "scripts/draw_replay_set.py",
        "rule": {"file": RULE, "commit": rule_commit, "sha256": rule_sha},
        "python": platform.python_version(),
        "sources": {PREDICTIONS: sha_rows, PANEL: sha_panel},
        "sources_note": "sha256 of each file with LF line endings, as stored in git",
        "part_a_index": part_a,
        "part_b_idx_condition": part_b,
        "part_b_removed_before_sampling": removed,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"part_a_index": part_a, "part_b_idx_condition": part_b, "removed": removed}))


if __name__ == "__main__":
    main()
