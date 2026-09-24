#!/usr/bin/env python3
"""
verify_tau.py  —  hand-verification harness for the corrupted-diagnosis stratum.

Purpose: establish the TRUE contamination rate of the 150 corrupted-diagnosis
items (does the perturbation actually remove the diagnosis, or just a cue-word
sentence?), so we can rebuild a clean tau and recompute the +0.071 headline.

Method: TWO non-author frontier models (DeepSeek-V4-Pro + Qwen3.5-397B) triage
each item PRESENT/ABSENT/BORDERLINE; a human audits every consequential call.
The LLMs are a validated, AUDITED accelerator — never the sole arbiter.

Three steps, invoked separately (the 85% gate is a HUMAN decision, not automatic):
  --step validate : run both models on the 20 hand-labeled items, compare, report gate
  --step triage    : run both models on all 150 (ONLY after you decide the gate passed)
  --step audit     : build the human-review list from the triage output

Nothing here is committed. Outputs land in results/ as untracked working files.

Run:
  export NEBIUS_API_KEY='...'        # export first (prefix-var gotcha)
  python scripts/verify_tau.py --step validate
"""
import os, re, sys, json, time, random, argparse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding="utf-8")

# ---------- paths ----------
CAL = r"D:/Owner/Desktop/assignment_01/medisimplifier-nebius/results/nebius_evidence/calibration_verdicts.json"
OUT_DIR = r"C:/Users/User/Desktop/medisimplifier-nemotron-vagt/results"
F_AUDIT = os.path.join(OUT_DIR, "tau_human_audit.txt")
def fvalid(tag):  return os.path.join(OUT_DIR, f"tau_validation_20_{tag}.json")
def ftriage(tag): return os.path.join(OUT_DIR, f"tau_triage_150_{tag}.json")

# ---------- models / api ----------
NEBIUS_API_URL = "https://api.studio.nebius.ai/v1/chat/completions"
MODELS = [("deepseek", "deepseek-ai/DeepSeek-V4-Pro"),
          ("qwen",     "Qwen/Qwen3.5-397B-A17B")]
SPLIT   = r'(?<=[.!?])\s+'          # same sentence-split the perturbation used
WORKERS = 8
SEED    = 42

# ---------- our 20 hand labels (gold set for validation) ----------
# PRESENT = diagnosis retained (contaminated tau); ABSENT = genuine drop; BORDERLINE = secondary/partial
GOLD_20 = {
    "36":"PRESENT","47":"PRESENT","49":"PRESENT","131":"PRESENT","132":"PRESENT",
    "138":"PRESENT","168":"PRESENT","276":"PRESENT","293":"PRESENT","347":"PRESENT",
    "368":"PRESENT","437":"PRESENT","684":"PRESENT","867":"PRESENT","931":"PRESENT",
    "341":"ABSENT","665":"ABSENT",
    "145":"BORDERLINE","261":"BORDERLINE","982":"BORDERLINE",
}

# ---------- data ----------
def load_corrupted_diagnosis():
    cal = json.load(open(CAL, encoding="utf-8"))
    recs = [r for r in cal
            if r.get("condition")=="corrupted" and r.get("error_type")=="diagnosis"
            and str(r.get("idx")) != "308"]            # 308 excluded (also a clean control)
    recs.sort(key=lambda r: int(r["idx"]))
    return recs

def dropped_sentences(clean_ref, perturbed):
    ps = set(re.split(SPLIT, perturbed.strip()))
    return [s for s in re.split(SPLIT, clean_ref.strip()) if s not in ps]

# ---------- prompt (asymmetric presence check; .replace only) ----------
SYS = ("You are a clinical reading checker. You decide whether a specific diagnosis stated in a "
       "SOURCE note is still conveyed to a lay reader in a SUMMARY. You judge MEANING, not wording.")

USER_TMPL = """A sentence was removed from the SUMMARY below (shown as DROPPED SENTENCE).
Decide whether the PRIMARY diagnosis from the SOURCE is still conveyed anywhere in the SUMMARY.

Rules:
- PRESENT: the primary diagnosis is still stated or clearly conveyed somewhere in the SUMMARY,
  even if reworded, simplified, or made less technical for a lay audience
  (e.g. "leukemia" -> "blood cancer", "MI" -> "heart attack"). Removing the sentence did NOT eliminate it.
- ABSENT: the primary diagnosis is no longer conveyed anywhere in the SUMMARY — a reader could not
  tell the patient had this condition.
- BORDERLINE: only a SECONDARY diagnosis/finding was removed while the primary remains, OR the
  diagnosis is only partially / ambiguously conveyed.

First identify the primary diagnosis from the SOURCE, then read the WHOLE SUMMARY.

SOURCE:
<<<__INPUT__>>>

DROPPED SENTENCE (removed from SUMMARY):
<<<__DROPPED__>>>

SUMMARY:
<<<__SUMMARY__>>>

Return exactly one JSON object and nothing else:
{"idx":"__IDX__","verdict":"PRESENT|ABSENT|BORDERLINE","diagnosis_in_source":"<exact quote from SOURCE>","reason":"<one sentence>"}
"""

def build_user(rec):
    dropped = " || ".join(dropped_sentences(rec["clean_ref"], rec["perturbed"])) or "(diff found none)"
    return (USER_TMPL
            .replace("__INPUT__",   rec["input"])
            .replace("__DROPPED__", dropped)
            .replace("__SUMMARY__", rec["perturbed"])
            .replace("__IDX__",     str(rec["idx"])))

# ---------- api ----------
def call_model(user, model_id, max_tokens=6000):
    body = json.dumps({
        "model": model_id,
        "messages": [{"role":"system","content":SYS},{"role":"user","content":user}],
        "temperature": 0, "max_tokens": max_tokens,
        "response_format": {"type":"json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(NEBIUS_API_URL, data=body, method="POST", headers={
        "Authorization": "Bearer " + os.environ["NEBIUS_API_KEY"],
        "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read().decode("utf-8"))
    return (data["choices"][0]["message"].get("content") or "")

def strip(raw):
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    raw = raw.replace("```json","").replace("```","").strip()
    i, j = raw.find("{"), raw.rfind("}")
    return raw[i:j+1] if (i!=-1 and j!=-1) else raw

def judge(rec, model_id):
    idx = str(rec["idx"]); user = build_user(rec)
    for mt in (6000, 12000):                       # content=None guard (reasoning-budget lesson)
        try:
            raw = call_model(user, model_id, mt)
            if not raw.strip():
                continue
            obj = json.loads(strip(raw))
            v = str(obj.get("verdict","")).upper()
            if v not in ("PRESENT","ABSENT","BORDERLINE"):
                return {"idx":idx,"verdict":None,"diagnosis_in_source":obj.get("diagnosis_in_source",""),
                        "reason":obj.get("reason",""),"parse_status":"bad_verdict:"+v[:40]}
            return {"idx":idx,"verdict":v,"diagnosis_in_source":obj.get("diagnosis_in_source",""),
                    "reason":obj.get("reason",""),"parse_status":"ok"}
        except (json.JSONDecodeError, KeyError, urllib.error.URLError, urllib.error.HTTPError):
            time.sleep(1)
    return {"idx":idx,"verdict":None,"diagnosis_in_source":"","reason":"","parse_status":"empty_or_error"}

def run_items(recs, out_path, model_id):
    """Resumable: skip idx already in out_path; checkpoint every 25."""
    done = {}
    if os.path.exists(out_path):
        done = {d["idx"]: d for d in json.load(open(out_path, encoding="utf-8"))}
    todo = [r for r in recs if str(r["idx"]) not in done]
    print(f"    {len(done)} cached, {len(todo)} to run")
    if todo:
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(judge, r, model_id): r for r in todo}
            n = 0
            for f in as_completed(futs):
                res = f.result(); done[res["idx"]] = res; n += 1
                if n % 25 == 0:
                    json.dump(list(done.values()), open(out_path,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
                    print(f"      checkpoint {n}/{len(todo)}")
    results = sorted(done.values(), key=lambda d: int(d["idx"]))
    json.dump(results, open(out_path,"w",encoding="utf-8"), indent=2, ensure_ascii=False)
    return results

def metrics(results_by_idx, gold):
    conseq_err = exact = 0; n = len(gold)
    rows = []
    for i in sorted(gold, key=int):
        g = gold[i]; m = (results_by_idx.get(i) or {}).get("verdict") or "PARSE_FAIL"
        exact += (g==m)
        consequential = (g=="PRESENT" and m=="ABSENT") or (g=="ABSENT" and m=="PRESENT")
        conseq_err += consequential
        rows.append((i, g, m, "=" if g==m else ("XX-CONSEQ" if consequential else "x-minor")))
    return rows, exact/n, 1-conseq_err/n, conseq_err

# ---------- step 1: validate ----------
def step_validate():
    recs = {str(r["idx"]): r for r in load_corrupted_diagnosis()}
    sample = [recs[i] for i in GOLD_20 if i in recs]
    per_model = {}
    for tag, mid in MODELS:
        print(f"\nVALIDATE [{tag}] {mid} on {len(sample)} hand-labeled items ...")
        results = run_items(sample, fvalid(tag), mid)
        per_model[tag] = {d["idx"]: d for d in results}

    gate_pass = {}
    for tag, _ in MODELS:
        rows, exact_acc, conseq_agr, conseq_err = metrics(per_model[tag], GOLD_20)
        print(f"\n===== {tag} =====\nidx     gold        model       match")
        for i,g,m,mk in rows:
            print(f"{i:<6}  {g:<10}  {m:<10}  {mk}")
        print(f"  exact-match accuracy    : {exact_acc:.0%}")
        print(f"  consequential agreement : {conseq_agr:.0%}  ({conseq_err} PRESENT<->ABSENT errors)")
        gate_pass[tag] = conseq_agr > 0.85

    # inter-model agreement on the 20
    both = [i for i in GOLD_20 if per_model["deepseek"].get(i) and per_model["qwen"].get(i)]
    agree = sum(1 for i in both if per_model["deepseek"][i]["verdict"]==per_model["qwen"][i]["verdict"])
    print(f"\ninter-model agreement (deepseek vs qwen) on 20: {agree}/{len(both)} = {agree/max(1,len(both)):.0%}")

    print("\n" + "="*60)
    for tag,_ in MODELS:
        print(f"  GATE [{tag}] consequential>85% : {'PASS' if gate_pass[tag] else 'FAIL'}")
    overall = all(gate_pass.values())
    print(f"  OVERALL GATE (both pass)      : {'PASS' if overall else 'FAIL'}")
    print("  -> HUMAN DECISION: only run --step triage if you accept this gate.")

# ---------- step 2: triage ----------
def step_triage():
    from collections import Counter
    recs = load_corrupted_diagnosis()
    per_model = {}
    for tag, mid in MODELS:
        print(f"\nTRIAGE [{tag}] {mid} on {len(recs)} items ...")
        results = run_items(recs, ftriage(tag), mid)
        per_model[tag] = {d["idx"]: d for d in results}
        c = Counter(d["verdict"] for d in results); nf = sum(1 for d in results if d["verdict"] is None)
        print(f"  {tag}: PRESENT={c.get('PRESENT',0)} ABSENT={c.get('ABSENT',0)} "
              f"BORDERLINE={c.get('BORDERLINE',0)} PARSE_FAIL={nf}")
    idxs = [str(r["idx"]) for r in recs]
    both_present = sum(1 for i in idxs
                       if (per_model['deepseek'].get(i) or {}).get('verdict')=='PRESENT'
                       and (per_model['qwen'].get(i) or {}).get('verdict')=='PRESENT')
    agree = sum(1 for i in idxs
                if (per_model['deepseek'].get(i) or {}).get('verdict')
                == (per_model['qwen'].get(i) or {}).get('verdict'))
    print(f"\n  inter-model agreement on 150: {agree}/{len(idxs)} = {agree/len(idxs):.0%}")
    print(f"  both-agree-PRESENT (confident contaminated): {both_present}/{len(idxs)} = {both_present/len(idxs):.0%}")
    print(f"\n  wrote {ftriage('deepseek')} and {ftriage('qwen')}  ->  now run --step audit.")

# ---------- step 3: human audit list ----------
def step_audit():
    ds = {d["idx"]: d for d in json.load(open(ftriage("deepseek"), encoding="utf-8"))}
    qw = {d["idx"]: d for d in json.load(open(ftriage("qwen"),     encoding="utf-8"))}
    recs = {str(r["idx"]): r for r in load_corrupted_diagnosis()}
    idxs = sorted(recs, key=int)

    def v(d): return (d or {}).get("verdict")
    both_present = [i for i in idxs if v(ds.get(i))=="PRESENT" and v(qw.get(i))=="PRESENT"]
    need = [i for i in idxs if i not in both_present]          # any non-present or disagreement or fail
    k = max(1, round(0.10*len(both_present)))
    audit_present = random.Random(SEED).sample(both_present, min(k, len(both_present)))
    review = sorted(set(need) | set(audit_present), key=int)

    def block(i):
        r = recs.get(i, {}); d, q = ds.get(i,{}), qw.get(i,{})
        dropped = " || ".join(dropped_sentences(r.get("clean_ref",""), r.get("perturbed",""))) if r else ""
        why = "BOTH-PRESENT(10% audit)" if i in audit_present else "NEEDS REVIEW"
        return (f"{'='*94}\nidx={i}   [{why}]\n"
                f"  deepseek: {v(d)}  | {d.get('reason','')}\n"
                f"  qwen    : {v(q)}  | {q.get('reason','')}\n"
                f"  dx_in_source: {d.get('diagnosis_in_source','') or q.get('diagnosis_in_source','')}\n"
                f"  DROPPED  : {dropped[:400]}\n\n"
                f"  SOURCE : {' '.join(r.get('input','').split())[:1400]}\n\n"
                f"  SUMMARY: {' '.join(r.get('perturbed','').split())[:1400]}\n\n"
                f"  HUMAN VERDICT (fill in): __________   NOTES: __________\n")

    with open(F_AUDIT, "w", encoding="utf-8") as f:
        f.write("TAU HUMAN-AUDIT LIST  (models: DeepSeek-V4-Pro + Qwen3.5-397B)\n")
        f.write(f"both-agree-PRESENT={len(both_present)} (auditing {len(audit_present)} at 10%); "
                f"needs-review={len(need)}; TOTAL to review={len(review)}\n\n")
        for i in review:
            f.write(block(i))
    print(f"wrote {F_AUDIT}  ({len(review)} items for human eyes)")

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", required=True, choices=["validate","triage","audit"])
    args = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    {"validate":step_validate, "triage":step_triage, "audit":step_audit}[args.step]()
