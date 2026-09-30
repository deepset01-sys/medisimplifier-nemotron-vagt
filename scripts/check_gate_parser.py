#!/usr/bin/env python3
"""
Code-audit #31 check: does the gate's fixed verdict parser read a judge's replies differently from the earlier
last-word parser?

Sends the 240 v2 panel items (120 drops + 120 paired controls, built exactly as scripts/run_panel_judgebench_v2.py
builds them) through safety_gate._call_judge with the "safety_gate" capture log enabled, using the judge's model and
max_tokens as evaluate_safety calls it (Llama: LLAMA_DEDICATED, 2000; Qwen: QWEN_DEDICATED, 8000; the deployed
JUDGE_PROMPT). Each reply's capture record carries the fixed parser's verdict and what the earlier parser would have
returned on the same reply, so the two are compared reply by reply. The verdicts are also compared with the judge's
column in the committed results/judgebench_v2_panel_gate.json; since both parsers read the same replies, a difference
there is run-to-run variation, not parsing.

Paid: 1 probe + 240 calls to the judge's dedicated endpoint, which must be running. Needs NEBIUS_API_KEY in the
environment. Reply text is not written anywhere; the output keeps each reply's length, finish_reason and verdicts.

  python scripts/check_gate_parser.py --judge qwen     # -> results/judgebench_v2_qwen_parser_check.json
  python scripts/check_gate_parser.py --judge llama    # -> results/judgebench_v2_llama_parser_check.json
"""
import argparse
import datetime
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))
import safety_gate as sg                   # noqa: E402
import run_panel_judgebench_v2 as P        # noqa: E402  (the panel run's own item builder)

PANEL_GATE = REPO / "results" / "judgebench_v2_panel_gate.json"
# judge -> (name, model, max_tokens, panel_gate column); model and max_tokens as evaluate_safety calls the judge
JUDGES = {
    "llama": ("Llama-3.3-70B", sg.LLAMA_DEDICATED, 2000, "llama_verdict"),
    "qwen":  ("Qwen3-32B", sg.QWEN_DEDICATED, 8000, "qwen_verdict"),
}
WORKERS = 8


def out_path(judge):
    return REPO / "results" / f"judgebench_v2_{judge}_parser_check.json"


def build_output(judge, rows, meta):
    """The results file, from one row per item: tau, idx, new, legacy, rule, finish_reason, content_len,
    committed_panel_gate."""
    name, model, max_tokens, column = JUDGES[judge]

    def count(key, tau, v="UNSAFE"):
        return sum(r["tau"] == tau and r[key] == v for r in rows)
    legacy_diff = [r for r in rows if r["legacy"] != r["new"]]
    committed_diff = [r for r in rows if r["new"] != r["committed_panel_gate"]]
    return {
        "purpose": f"Code-audit #31 check: {name}'s replies on the 240 v2 panel items under the deployed gate prompt, "
                   "read by the fixed parser (safety_gate._parse_verdict) and by the earlier last-word parser.",
        "method": {"model": model, "prompt": "safety_gate.JUDGE_PROMPT (deployed)", "max_tokens": max_tokens,
                   "items": "results/judgebench_v2_tau1_final.json + results/judgebench_v2_clean_controls.json "
                            "(primary_paired), built by scripts/run_panel_judgebench_v2.py",
                   "compared_with": f"results/judgebench_v2_panel_gate.json {column}"},
        "run": meta,
        "summary": {
            "n_items": len(rows),
            "new_verdicts": {v: sum(r["new"] == v for r in rows) for v in ("SAFE", "UNSAFE", "ERROR")},
            "rules": {k: sum(r["rule"] == k for r in rows) for k in sorted({r["rule"] for r in rows if r["rule"]})},
            "finish_reason": {str(k): sum(r["finish_reason"] == k for r in rows)
                              for k in sorted({str(r["finish_reason"]) for r in rows})},
            "content_len_range": [min(r["content_len"] or 0 for r in rows), max(r["content_len"] or 0 for r in rows)],
            "legacy_vs_new_differ": len(legacy_diff),
            "new_vs_committed_panel_gate_differ": len(committed_diff),
            "recall_on_120_drops": {"committed_panel_gate": count("committed_panel_gate", 1), "this_run": count("new", 1)},
            "false_positives_on_120_controls": {"committed_panel_gate": count("committed_panel_gate", 0),
                                                "this_run": count("new", 0)},
        },
        "legacy_vs_new_differ": legacy_diff,
        "new_vs_committed_panel_gate_differ": committed_diff,
        "note": "Both parsers read the same replies, so legacy_vs_new_differ is the #31 effect on this run; "
                "new_vs_committed_panel_gate_differ is run-to-run variation. Reply text is not stored.",
        "rows": rows,
    }


def main():
    ap = argparse.ArgumentParser(description="Code-audit #31 check of the gate's verdict parser on one judge.")
    ap.add_argument("--judge", required=True, choices=sorted(JUDGES))
    judge = ap.parse_args().judge
    name, model, max_tokens, column = JUDGES[judge]
    key = os.environ.get("NEBIUS_API_KEY", "")
    if not key:
        sys.exit("NEBIUS_API_KEY not set")
    local, lock, records = threading.local(), threading.Lock(), {}

    class Tag(logging.Handler):
        """Keep each capture record, keyed by the item the worker thread is judging (reply text dropped)."""
        def emit(self, record):
            rec = json.loads(record.getMessage())
            rec.pop("head80", None)
            with lock:
                records[(getattr(local, "tau", None), getattr(local, "idx", None))] = rec

    sg.log.setLevel(logging.INFO)
    sg.log.addHandler(Tag())

    local.tau, local.idx = None, "probe"
    probe = sg._call_judge("Patient given aspirin 81 mg daily.", "Patient takes a low-dose aspirin each day.",
                           model, key, max_tokens=max_tokens)
    print("probe verdict:", probe, flush=True)
    if probe not in ("SAFE", "UNSAFE"):
        sys.exit(f"ABORT: the {name} dedicated endpoint did not return a verdict (stopped or cold?)")

    sp, calib = P._raw_original_index()
    items = P._build_items(REPO / "results" / "judgebench_v2_tau1_final.json",
                           REPO / "results" / "judgebench_v2_clean_controls.json", "primary_paired", sp, calib)

    def judge_item(it):
        local.tau, local.idx = it["tau"], str(it["idx"])
        return it, sg._call_judge(it["original"], it["simplified"], model, key, max_tokens=max_tokens)

    t0, verdicts = time.time(), {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        for n, f in enumerate(as_completed([ex.submit(judge_item, it) for it in items]), 1):
            it, v = f.result()
            verdicts[(it["tau"], str(it["idx"]))] = v
            if n % 20 == 0 or n == len(items):
                print(f"{n}/{len(items)} done, {time.time() - t0:.0f}s", flush=True)

    panel = {(r["tau"], str(r["idx"])): r[column]
             for r in json.load(open(PANEL_GATE, encoding="utf-8"))["per_sample"]}
    rows = []
    for k in sorted(verdicts, key=lambda k: (k[0], k[1])):
        rec = records.get(k, {})
        rows.append({"tau": k[0], "idx": k[1], "new": verdicts[k], "legacy": rec.get("legacy_verdict"),
                     "rule": rec.get("rule"), "finish_reason": rec.get("finish_reason"),
                     "content_len": rec.get("content_len"), "committed_panel_gate": panel.get(k)})
    meta = {"date": datetime.date.today().isoformat(), "calls": len(items) + 1, "elapsed_s": round(time.time() - t0),
            "safety_gate_commit": "6ac1678 (the #31 fix) or later"}
    out = build_output(judge, rows, meta)
    with open(out_path(judge), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out["summary"], ensure_ascii=False))
    print(f"Saved -> {out_path(judge)}")


if __name__ == "__main__":
    main()
