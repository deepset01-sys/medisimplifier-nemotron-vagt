"""
recount_disagree_708_hand_labels.py — the 708-item DISAGREE false-alarm share, recounted with
the 150 hand labels for the automated diagnosis items.

The published shares (README B5) count every DISAGREE on a corrupted item as a genuine catch:
  deployed gate prompt   34.7% = 51 clean / 147 DISAGREE   (results/gate_calibration_full.json)
  calibration verdicts   33.0% = 67 clean / 203 DISAGREE   (nemotron_calibration_full.json; the
                                                            "Calibration prompt" column of the B5 table)
The hand audit of the 150 automated diagnosis items (results/tau_hand_labels_150.json) found the
diagnosis still present in most of them (128 PRESENT, 13 BORDERLINE, 9 ABSENT). Every one of those
items had a sentence removed; the audit asks whether the diagnosis itself is gone. Here a DISAGREE on
a diagnosis item that does not count as a genuine drop is a false alarm, as one on a clean control is
(the convention of results/tau_recompute_summary.json, where those items are τ = 0). BORDERLINE is
counted both ways:
  strict   — only ABSENT is a genuine drop (BORDERLINE counts with PRESENT)
  generous — ABSENT and BORDERLINE are genuine drops
The negation, lateral and dose items were not hand-audited and keep their automated label
(corrupted = genuine error), so the recount corrects the diagnosis items only.

DISAGREE rule: src/safety_gate.py's consensus (mirrored in gate_rule, as in
scripts/run_prevalence_sensitivity_v2.py): UNSAFE when Qwen says UNSAFE, DISAGREE when Nemotron says
UNSAFE and Qwen SAFE; Llama is advisory and does not enter it. The deployed files' recorded consensus
is checked against the rule on all 708 and all 240 rows.
Join key: (idx, condition "corrupted", error_type "diagnosis") — idx alone is not unique in the
708 set (the same idx carries a clean control and other perturbations).

Also reported:
  - the share at a matched prevalence, with the formula of scripts/run_prevalence_sensitivity_v2.py
    (gate_708_disagree_reference), treating the items without a genuine error (clean controls plus the
    diagnosis items that are not genuine drops) as one class and the rest as the other;
  - the gate's consensus on the corrupted items by error type (why few genuine errors draw a DISAGREE);
  - the same per-class DISAGREE rates on the hand-verified v2 stratum (results/judgebench_v2_panel_gate.json),
    asserted equal to judgebench_v2_prevalence_sensitivity.json gate_operating_characteristics.

Counting only: deterministic, no resampling (SEED is imported for the repo convention and unused),
no API calls. Asserts reproduce the published counts before anything is written.
"""
import io
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
from audit_panel import vagt_core as V  # noqa: E402

SEED = V.SEED   # unused: counting only
RES = _REPO / "results"
HAND = RES / "tau_hand_labels_150.json"
TAU_SUMMARY = RES / "tau_recompute_summary.json"
PREV = RES / "judgebench_v2_prevalence_sensitivity.json"
V2_GATE = RES / "judgebench_v2_panel_gate.json"
PROMPTS = {
    "deployed_gate_prompt": RES / "gate_calibration_full.json",
    "calibration_verdicts": _REPO / "nemotron_calibration_full.json",
}
README_COLUMN = {"deployed_gate_prompt": "Gate prompt (deployed)", "calibration_verdicts": "Calibration prompt"}
OUT = RES / "disagree_708_hand_label_recount.json"

PREVALENCES = [0.50, 0.33, 0.20, 0.10, 0.05]
TYPES = ["diagnosis", "negation", "lateral", "dose"]
LABELS = ["PRESENT", "BORDERLINE", "ABSENT"]
GENUINE = {"strict": {"ABSENT"}, "generous": {"ABSENT", "BORDERLINE"}}
DISAGREE_BRANCH = "disagree_branch (Nano UNSAFE, Qwen SAFE)"


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _rel(p):
    return p.relative_to(_REPO).as_posix()


def wilson(k, n, z=1.96):
    """Same as scripts/run_prevalence_sensitivity_v2.py wilson (percent, 1 dp)."""
    ph = k / n
    den = 1 + z * z / n
    mid = (ph + z * z / (2 * n)) / den
    half = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return [float(round(100 * (mid - half), 1)), float(round(100 * (mid + half), 1))]


def gate_rule(r):
    """src/safety_gate.py consensus rule (Nemotron + Qwen; Llama advisory), as in
    scripts/run_prevalence_sensitivity_v2.py."""
    n, q = r["nemotron_verdict"], r["qwen_verdict"]
    if n == "SAFE" and q == "SAFE":
        return "SAFE"
    if q == "UNSAFE":
        return "UNSAFE"
    if n == "UNSAFE" and q == "SAFE":
        return "DISAGREE"
    return "ERROR" if "ERROR" in (n, q) else "DISAGREE"


def pct(k, n):
    return round(100 * k / n, 1)


def share_at(p, d0, n0, d1, n1):
    """False-alarm share of DISAGREEs at prevalence p (share of items with a genuine error),
    from the two per-class DISAGREE rates — the formula of run_prevalence_sensitivity_v2.py."""
    r0, r1 = d0 / n0, d1 / n1
    return round(100 * r0 * (1 - p) / (r0 * (1 - p) + r1 * p), 1)


def recount(rows, hand):
    diag = [r for r in rows if r["condition"] == "corrupted" and r["error_type"] == "diagnosis"]
    assert len(diag) == 150 and {r["idx"] for r in diag} == set(hand), "diagnosis items != hand-label idx"
    clean = [r for r in rows if r["condition"] == "clean"]
    corr = [r for r in rows if r["condition"] == "corrupted"]
    assert len(rows) == 708 and len(clean) == 200 and len(corr) == 508
    cons = {id(r): gate_rule(r) for r in rows}
    dis = [r for r in rows if cons[id(r)] == "DISAGREE"]
    d_clean = sum(1 for r in dis if r["condition"] == "clean")
    d_type = Counter(r["error_type"] for r in dis if r["condition"] == "corrupted")
    n_type = Counter(r["error_type"] for r in corr)
    d_diag_label = Counter(hand[r["idx"]] for r in dis
                           if r["condition"] == "corrupted" and r["error_type"] == "diagnosis")
    n_diag_label = Counter(hand.values())
    by_type = {t: Counter(cons[id(r)] for r in corr if r["error_type"] == t) for t in TYPES}
    by_label = {k: Counter(cons[id(r)] for r in diag if hand[r["idx"]] == k) for k in LABELS}
    other = sum((by_type[t] for t in TYPES if t != "diagnosis"), Counter())
    out = {
        "n_items": len(rows),
        "disagree_total": len(dis),
        "disagree_on_clean": f"{d_clean}/{len(clean)}",
        "disagree_on_corrupted": f"{len(dis) - d_clean}/{len(corr)}",
        "disagree_on_corrupted_by_error_type": {t: f"{d_type[t]}/{n_type[t]}" for t in TYPES},
        "diagnosis_disagree_by_hand_label": {k: d_diag_label[k] for k in LABELS},
        "diagnosis_items_by_hand_label": {k: n_diag_label[k] for k in LABELS},
        "gate_consensus_on_corrupted_by_error_type": {
            t: {c: by_type[t][c] for c in ("UNSAFE", "DISAGREE", "SAFE", "ERROR")} for t in TYPES},
        "gate_consensus_on_negation_lateral_dose": {
            "items": sum(other.values()),
            **{c: other[c] for c in ("UNSAFE", "DISAGREE", "SAFE", "ERROR")}},
        "gate_consensus_on_diagnosis_by_hand_label": {
            k: {c: by_label[k][c] for c in ("UNSAFE", "DISAGREE", "SAFE", "ERROR")} for k in LABELS},
        "automated_labels": {
            "false_alarms": d_clean,
            "false_alarm_share_pct": pct(d_clean, len(dis)),
            "false_alarm_share_wilson95": wilson(d_clean, len(dis)),
            "items_with_error": f"{len(corr)}/{len(rows)}",
            "prevalence": round(len(corr) / len(rows), 3),
        },
    }
    non_diag_corr = len(corr) - 150
    d_non_diag = len(dis) - d_clean - sum(d_diag_label.values())
    for mode, genuine in GENUINE.items():
        d_diag_genuine = sum(v for k, v in d_diag_label.items() if k in genuine)
        d_diag_other = sum(d_diag_label.values()) - d_diag_genuine
        n_diag_genuine = sum(v for k, v in n_diag_label.items() if k in genuine)
        fa = d_clean + d_diag_other
        n0 = len(clean) + (150 - n_diag_genuine)          # items without a genuine error
        n1 = non_diag_corr + n_diag_genuine                # items with one (non-diagnosis by automated label)
        d1 = d_non_diag + d_diag_genuine
        assert fa + d1 == len(dis) and n0 + n1 == len(rows)
        out[f"hand_labels_{mode}"] = {
            "genuine_diagnosis_drop_labels": sorted(genuine),
            "diagnosis_labels_counted_as_no_error": sorted(set(LABELS) - genuine),
            "false_alarms": fa,
            "false_alarms_on_clean": d_clean,
            "false_alarms_on_diagnosis_items": d_diag_other,
            "genuine_catches": d1,
            "genuine_catches_diagnosis": d_diag_genuine,
            "genuine_catches_other_types_automated_label": d_non_diag,
            "false_alarm_share_pct": pct(fa, len(dis)),
            "false_alarm_share_wilson95": wilson(fa, len(dis)),
            "items_with_error": f"{n1}/{len(rows)}",
            "prevalence": round(n1 / len(rows), 3),
            "disagree_rate_no_error_items": f"{fa}/{n0}",
            "disagree_rate_no_error_items_pct": pct(fa, n0),
            "disagree_rate_error_items": f"{d1}/{n1}",
            "disagree_rate_error_items_pct": pct(d1, n1),
            "false_alarm_share_pct_by_prevalence": {f"{p:.2f}": share_at(p, fa, n0, d1, n1)
                                                    for p in PREVALENCES},
        }
    return out


def v2_reference(prev):
    """The same per-class DISAGREE rates on the hand-verified v2 stratum (deployed prompt)."""
    rows = _load(V2_GATE)["per_sample"]
    assert all(gate_rule(r) == r["consensus"] for r in rows) and len(rows) == 240
    n1 = sum(r["tau"] == 1 for r in rows)
    n0 = sum(r["tau"] == 0 for r in rows)
    d1 = sum(r["tau"] == 1 and r["consensus"] == "DISAGREE" for r in rows)
    d0 = sum(r["tau"] == 0 and r["consensus"] == "DISAGREE" for r in rows)
    ref = prev["gate_operating_characteristics"]["rules"][DISAGREE_BRANCH]
    assert (ref["drops_flagged"], ref["controls_flagged"]) == (f"{d1}/{n1}", f"{d0}/{n0}")
    assert ref["recall_wilson95"] == wilson(d1, n1) and ref["fpr_wilson95"] == wilson(d0, n0)
    assert ref["by_prevalence"]["0.50"]["share_of_flags_false_alarm_pct"] == pct(d0, d0 + d1)
    return {"source": _rel(V2_GATE) + " (deployed prompt, hand-verified labels, 50% drops)",
            "disagree_total": d0 + d1,
            "false_alarm_share_pct": pct(d0, d0 + d1),
            "disagree_rate_no_error_items": f"{d0}/{n0}", "disagree_rate_no_error_items_pct": pct(d0, n0),
            "disagree_rate_error_items": f"{d1}/{n1}", "disagree_rate_error_items_pct": pct(d1, n1),
            "matches": ("results/judgebench_v2_prevalence_sensitivity.json gate_operating_characteristics"
                        f".rules['{DISAGREE_BRANCH}'] (asserted)")}


def main():
    hand_rows = _load(HAND)
    hand = {x["idx"]: x["verdict"] for x in hand_rows}
    assert len(hand) == len(hand_rows) == 150
    assert Counter(hand.values()) == Counter({"PRESENT": 128, "BORDERLINE": 13, "ABSENT": 9})
    assert "128 PRESENT, 9 ABSENT, 13 BORDERLINE" in _load(TAU_SUMMARY)["labels_source"]
    prev = _load(PREV)

    res = {}
    for name, path in PROMPTS.items():
        rows = _load(path)["per_sample"]
        assert all((gate_rule(r) == "DISAGREE") == (r["nemotron_verdict"] == "UNSAFE" and r["qwen_verdict"] == "SAFE")
                   for r in rows)
        if name == "deployed_gate_prompt":        # recorded consensus follows the safety_gate.py rule
            assert all(gate_rule(r) == r["consensus"] for r in rows)
        res[name] = {"source": _rel(path), "readme_b5_column": README_COLUMN[name], **recount(rows, hand)}

    # reproduce the published figures this builds on
    g, c = res["deployed_gate_prompt"], res["calibration_verdicts"]
    assert (g["disagree_total"], g["disagree_on_clean"]) == (147, "51/200")              # README B5
    assert g["automated_labels"]["false_alarm_share_pct"] == 34.7
    assert (c["disagree_total"], c["disagree_on_clean"]) == (203, "67/200")              # README B5
    assert c["automated_labels"]["false_alarm_share_pct"] == 33.0
    assert c["disagree_on_corrupted"] == "136/508" and \
        sum(c["diagnosis_disagree_by_hand_label"].values()) == 81                        # README B5
    ref = prev["gate_708_disagree_reference"]
    assert ref["disagree_on_corrupted"] == g["disagree_on_corrupted"]
    assert ref["disagree_on_clean"] == g["disagree_on_clean"]
    assert all(f"{v['disagree']}/{v['items']}" == g["disagree_on_corrupted_by_error_type"][t]
               for t, v in ref["corrupted_by_error_type"].items())
    assert ref["false_alarm_share_pct_at_own_prevalence"] == g["automated_labels"]["false_alarm_share_pct"]
    assert ref["prevalence"] == g["automated_labels"]["prevalence"]
    assert all(share_at(float(p), 51, 200, 96, 508) == v
               for p, v in ref["false_alarm_share_pct_by_prevalence"].items())
    v2 = v2_reference(prev)
    assert (v2["disagree_total"], v2["false_alarm_share_pct"]) == (99, 45.5)             # README B3: 45 of 99

    out = {
        "purpose": ("The 708-item DISAGREE false-alarm share (README B5: 34.7% deployed gate prompt, 33.0% "
                    "calibration verdicts) recounted with the 150 hand labels for the automated diagnosis items: a DISAGREE "
                    "on a diagnosis item that is not a genuine drop by hand label counts as a false alarm."),
        "disagree_rule": ("src/safety_gate.py consensus: UNSAFE when Qwen says UNSAFE, DISAGREE when Nemotron says "
                          "UNSAFE and Qwen SAFE; Llama does not enter it"),
        "seed": SEED,
        "hand_labels": {"source": _rel(HAND), "PRESENT": 128, "BORDERLINE": 13, "ABSENT": 9,
                        "strict": "only ABSENT is a genuine drop",
                        "generous": "ABSENT and BORDERLINE are genuine drops",
                        "note": ("every hand-labelled item had a sentence removed; PRESENT means the diagnosis "
                                 "itself is still in the text")},
        "scope_note": ("only the 150 diagnosis items were hand-audited; the negation, lateral and dose items "
                       "keep their automated label (corrupted = genuine error)"),
        "prevalence_note": ("prevalence = share of the 708 items with a genuine error by the labels used; "
                            "false_alarm_share_pct_by_prevalence reweights the two per-class DISAGREE rates "
                            "(items without / with a genuine error) with the formula of "
                            "scripts/run_prevalence_sensitivity_v2.py; the automated-label grid is "
                            "results/judgebench_v2_prevalence_sensitivity.json gate_708_disagree_reference"),
        "wilson_note": "95% Wilson intervals in percent, z = 1.96, as in scripts/run_prevalence_sensitivity_v2.py",
        "prompts": res,
        "v2_reference": v2,
        "checks": {"asserted": [
            "hand labels: 150 unique idx, 128 PRESENT / 13 BORDERLINE / 9 ABSENT (tau_recompute_summary.json)",
            "the 150 automated diagnosis items in each verdict file are exactly the hand-labelled idx",
            "gate_rule DISAGREE = Nemotron UNSAFE and Qwen SAFE on every row of both 708-item files",
            "deployed files: recorded consensus equals gate_rule on 708/708 and 240/240 rows",
            "deployed: 147 DISAGREE, 51 on 200 clean, 34.7%; calibration: 203 DISAGREE, 67 on 200 clean, 33.0%, "
            "136 on corrupted items, 81 of them diagnosis (README B5)",
            "deployed per-type counts, 96/508, prevalence 0.718, 34.7% and the by-prevalence grid match "
            "judgebench_v2_prevalence_sensitivity.json gate_708_disagree_reference",
            "v2: DISAGREE on 54/120 drops and 45/120 controls, their Wilson intervals and the 45.5% share match "
            "judgebench_v2_prevalence_sensitivity.json gate_operating_characteristics (README B3: 45 of 99)",
        ]},
    }
    with io.open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("708-set DISAGREE false-alarm share, automated labels vs hand labels (diagnosis items)\n")
    for name, r in res.items():
        a = r["automated_labels"]
        print(f"{name}: {r['disagree_total']} DISAGREE; diagnosis DISAGREEs by hand label "
              f"{r['diagnosis_disagree_by_hand_label']}")
        print(f"  automated labels  {a['false_alarm_share_pct']:5.1f}%  ({r['disagree_on_clean'].split('/')[0]}"
              f"/{r['disagree_total']})  prevalence {a['prevalence']}")
        for mode in GENUINE:
            h = r[f"hand_labels_{mode}"]
            print(f"  hand, {mode:8}  {h['false_alarm_share_pct']:5.1f}%  ({h['false_alarms']}/{r['disagree_total']}) "
                  f"Wilson {h['false_alarm_share_wilson95']}  prevalence {h['prevalence']}  "
                  f"at 0.50: {h['false_alarm_share_pct_by_prevalence']['0.50']}%  "
                  f"DISAGREE rate no-error {h['disagree_rate_no_error_items']} error {h['disagree_rate_error_items']}")
        print(f"  gate consensus on negation/lateral/dose: {r['gate_consensus_on_negation_lateral_dose']}")
    print(f"v2 reference: {v2['false_alarm_share_pct']}%  no-error {v2['disagree_rate_no_error_items']}  "
          f"error {v2['disagree_rate_error_items']}")
    print(f"\nSaved -> {_rel(OUT)}")


if __name__ == "__main__":
    main()
