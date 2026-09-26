#!/usr/bin/env python3
"""
check_deepseek_budget_v2.py — is DeepSeek-V4-Flash's 7-ERROR result on the JudgeBench v2
diagnosis stratum a token-budget artifact?

Context. The committed pool run (scripts/run_pool_judgebench_v2.py) judged DeepSeek-V4-Flash at
max_tokens=4000 and gpt-oss-120b at 8000. DeepSeek returned 7 ERROR verdicts, gpt-oss 0, and the
selector's reliability tie-break (fewest ERROR verdicts) is what picks gpt-oss over DeepSeek. The
committed pool file stores only the verdict string, so an ERROR there cannot be attributed.

Two phases, same prompt/payload as the deployed gate (safety_gate.JUDGE_PROMPT; temperature 0;
the same payload keys, including the literal "extra_body" key safety_gate sends):
  A  mechanism — the 7 committed ERROR rows, at max_tokens 4000 and 8000, 3 repeats each, one
     attempt per call with a long client timeout (300 s) so the true completion is observed.
     Per call: HTTP status, elapsed seconds, finish_reason, usage, whether content is empty,
     whether a SAFE/UNSAFE word is present, and what production _call_judge would have returned
     for that attempt (its timeout is 60 s).
  B  matched-budget re-run — all 240 rows at max_tokens 4000 and at 8000, each with a
     production-faithful replica of safety_gate._call_judge (60 s timeout, 3 attempts, same
     backoff and parse), recording the same diagnostics per attempt. Same day, same serving
     conditions, so the only difference between the two columns is the budget.

Analysis (offline, no API): for the committed column and each re-run column — ERROR count,
recall on tau=1, specificity on tau=0, paired Delta Phi_V vs the Llama+Qwen incumbent (vagt_core
verbatim, SEED=42, n_boot=1000), and the /v1/audit_panel recommendation with that DeepSeek column
swapped into a temporary copy of audit_pool_v2/ (the repo copy is never modified). Plus a bound:
the recommendation under every SAFE/UNSAFE fill-in of the committed ERROR rows (2^7 = 128).

  python scripts/check_deepseek_budget_v2.py --selftest   # offline, committed files only: must reproduce
                                                          # +0.1238 [0.1024, 0.1440], 7 ERROR, gpt-oss pick
  python scripts/check_deepseek_budget_v2.py --phases A   # live run (NEBIUS_API_KEY in the environment or the
                                                          # gitignored .env; raw notes from the same local
                                                          # inputs as run_pool_judgebench_v2.py). Phase B is
                                                          # implemented but has not been run.
Output: results/judgebench_v2_deepseek_budget_check.json (refuses to overwrite without --force;
checkpoints to <out>.partial.json and resumes from it).
"""
import argparse, datetime, io, json, os, re, shutil, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import requests

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "src" / "audit_panel"))   # selector/pool_loader import vagt_core flat (as the tests do)
sys.path.insert(0, str(_REPO / "scripts"))
from safety_gate import JUDGE_PROMPT, NEBIUS_API_URL             # noqa: E402
import vagt_core as V                                             # noqa: E402
from pool_loader import Pool                                      # noqa: E402
from selector import audit_panel                                  # noqa: E402
import run_pool_judgebench_v2 as POOL                             # noqa: E402

MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
BUDGETS = (4000, 8000)
REPEATS_A = 3
OBS_TIMEOUT = 300          # phase A: observe the full completion
PROD_TIMEOUT = 60          # safety_gate._call_judge
PROD_ATTEMPTS = 3          # safety_gate._call_judge max_retries
TAU1 = _REPO / "results" / "judgebench_v2_tau1_final.json"
CTRL = _REPO / "results" / "judgebench_v2_clean_controls.json"
PANEL = _REPO / "results" / "judgebench_v2_panel_gate.json"
COMMITTED = _REPO / "results" / "judgebench_v2_pool_DeepSeek-V4-Flash-0731.json"
POOL_DIR = _REPO / "audit_pool_v2"
LLAMA, QWEN = "meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen3-32B"


# ---------------- API key (never printed)
def api_key():
    k = os.environ.get("NEBIUS_API_KEY", "").strip()
    env = _REPO / ".env"
    if not k and env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            m = re.match(r'\s*(?:export\s+)?NEBIUS_API_KEY\s*=\s*["\']?([^"\'\s]+)', line)
            if m:
                k = m.group(1)
    if not k:
        sys.exit("ERROR: NEBIUS_API_KEY not set (environment or .env).")
    return k


# ---------------- one instrumented attempt, same payload as safety_gate._call_judge
def _payload(original, simplified, max_tokens):
    return {"model": MODEL,
            "messages": [{"role": "user", "content": JUDGE_PROMPT.format(original=original, simplified=simplified)}],
            "max_tokens": max_tokens, "temperature": 0,
            "extra_body": {"enable_thinking": False}}


def _parse(raw):
    """safety_gate._call_judge's parse, verbatim."""
    if "</think>" in raw:
        raw = raw.split("</think>")[-1]
    m = re.findall(r"\b(SAFE|UNSAFE)\b", raw, re.IGNORECASE)
    return m[-1].upper() if m else "ERROR"


def attempt(key, original, simplified, max_tokens, timeout):
    t0 = time.monotonic()
    d = {"max_tokens": max_tokens, "timeout_s": timeout}
    try:
        r = requests.post(NEBIUS_API_URL, json=_payload(original, simplified, max_tokens), timeout=timeout,
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        d["elapsed_s"] = round(time.monotonic() - t0, 2)
        d["http_status"] = r.status_code
        if r.status_code != 200:
            d["outcome"] = "http_error"
            d["body_head"] = r.text[:200]
            return d, None
        j = r.json()
        ch = j["choices"][0]
        msg = ch.get("message") or {}
        content = msg.get("content")
        reasoning = msg.get("reasoning_content") or msg.get("reasoning") or ""
        d.update({"finish_reason": ch.get("finish_reason"), "usage": j.get("usage"),
                  "content_is_none": content is None, "content_len": len(content or ""),
                  "reasoning_len": len(reasoning), "has_think_tag": "</think>" in (content or ""),
                  "content_tail": (content or "")[-240:]})
        if content is None:            # production: TypeError on '"</think>" in None' -> retry
            d["outcome"] = "empty_content"
            return d, None
        v = _parse(content)
        d["outcome"] = "verdict" if v != "ERROR" else "no_verdict_word"   # production returns ERROR, no retry
        d["verdict"] = v
        return d, v
    except requests.exceptions.Timeout:
        d.update({"elapsed_s": round(time.monotonic() - t0, 2), "outcome": "timeout"})
        return d, None
    except Exception as e:  # noqa: BLE001 — recorded, not swallowed
        d.update({"elapsed_s": round(time.monotonic() - t0, 2), "outcome": "exception",
                  "exception": f"{type(e).__name__}: {str(e)[:160]}"})
        return d, None


def production_replica(key, original, simplified, max_tokens):
    """safety_gate._call_judge semantics: up to 3 attempts; retry on exception / empty content;
    a reply without SAFE/UNSAFE returns ERROR immediately; backoff 2**attempt."""
    tries = []
    for a in range(PROD_ATTEMPTS):
        d, v = attempt(key, original, simplified, max_tokens, PROD_TIMEOUT)
        tries.append(d)
        if d["outcome"] == "verdict":
            return v, tries
        if d["outcome"] == "no_verdict_word":
            return "ERROR", tries
        if a < PROD_ATTEMPTS - 1:
            time.sleep(2 ** a)
    return "ERROR", tries


def phase_a_view(d):
    """What production _call_judge would have made of this single observed attempt."""
    if d["outcome"] == "verdict":
        return d["verdict"] if d["elapsed_s"] <= PROD_TIMEOUT else "TIMEOUT@60s"
    return {"empty_content": "EMPTY(retry)", "no_verdict_word": "ERROR(no word)",
            "timeout": "TIMEOUT", "http_error": "HTTP", "exception": "EXC"}[d["outcome"]]


# ---------------- analysis (offline)
def analyse(items, column, label):
    """column: {row_id: verdict}. Delta Phi_V vs Llama+Qwen exactly as run_pool.build_table."""
    base = {(str(x["idx"]), x["tau"]): x for x in json.load(io.open(PANEL, encoding="utf-8"))["per_sample"]}
    recs = []
    for it in items:
        b = base[(str(it["idx"]), it["tau"])]
        recs.append({"condition": it["condition"], "error_type": it["error_type"],
                     "llama_verdict": b["llama_verdict"], "qwen_verdict": b["qwen_verdict"],
                     "cand_verdict": column[it["row_id"]]})
    X, tau, dropped = V.stratum(recs, "diagnosis", ["llama_verdict", "qwen_verdict", "cand_verdict"])
    point, cis = V.paired_delta_cis(X, tau, 2, np.random.default_rng(V.SEED), V.N_BOOT)
    pos = [r["cand_verdict"] for r in recs if r["condition"] == "corrupted"]
    neg = [r["cand_verdict"] for r in recs if r["condition"] == "clean"]
    out = {"label": label, "n": int(X.shape[0]), "dropped": int(dropped),
           "errors": sum(v not in ("SAFE", "UNSAFE") for v in column.values()),
           "errors_tau1": sum(v not in ("SAFE", "UNSAFE") for v in pos),
           "errors_tau0": sum(v not in ("SAFE", "UNSAFE") for v in neg),
           "recall_tau1": f"{pos.count('UNSAFE')}/{sum(v in ('SAFE', 'UNSAFE') for v in pos)}",
           "spec_tau0": f"{neg.count('SAFE')}/{sum(v in ('SAFE', 'UNSAFE') for v in neg)}",
           "delta_phi_v": round(point["phi_v"], 4),
           "ci95": [round(cis["phi_v"][0], 4), round(cis["phi_v"][1], 4)]}
    out["selector"] = selector_with(items, column)
    return out


def selector_with(items, column):
    """/v1/audit_panel on a temp copy of audit_pool_v2 with this DeepSeek column swapped in."""
    tmp = Path(tempfile.mkdtemp(prefix="dsbudget_"))
    try:
        shutil.copytree(POOL_DIR, tmp / "pool")
        vf_path = tmp / "pool" / "verdicts" / "DeepSeek-V4-Flash-0731.json"
        vf = json.load(io.open(vf_path, encoding="utf-8"))
        by_row = {it["row_id"]: it for it in items}
        for v in vf["verdicts"]:
            assert str(by_row[v["row_id"]]["idx"]) == str(v["idx"]), "pool row_id/idx misaligned"
            v["verdict"] = column[v["row_id"]]
        json.dump(vf, io.open(vf_path, "w", encoding="utf-8"), ensure_ascii=False)
        pool = Pool.load(tmp / "pool")
        cands = sorted(m for m in pool.models if m not in (LLAMA, QWEN))
        res = audit_panel(pool, [LLAMA, QWEN], cands)
        rec = res["recommendation"]
        return {"recommended": rec["model"], "lift": rec["expected_Phi_V_lift"], "ci_95": rec["ci_95"],
                "tied_top": rec["tied_top_candidates"],
                "top2": [{k: r[k] for k in ("model", "error_rows", "specificity_clean")} | {
                         "delta": r["per_stratum_delta_Phi_V"]["diagnosis"]} for r in res["candidates_ranked"][:2]]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def completion_bound(items, committed):
    """Offline bound: every SAFE/UNSAFE fill-in of the committed ERROR rows (2^7 = 128), rest unchanged.
    Which model would /v1/audit_panel pick if those rows had returned verdicts?"""
    import itertools
    err = sorted(r for r, v in committed.items() if v not in ("SAFE", "UNSAFE"))
    by_row = {it["row_id"]: it for it in items}
    tmp = Path(tempfile.mkdtemp(prefix="dsbound_"))
    try:
        shutil.copytree(POOL_DIR, tmp / "pool")
        vf_path = tmp / "pool" / "verdicts" / "DeepSeek-V4-Flash-0731.json"
        vf = json.load(io.open(vf_path, encoding="utf-8"))
        picks, cases = {}, []
        for combo in itertools.product(("SAFE", "UNSAFE"), repeat=len(err)):
            col = dict(committed)
            col.update(zip(err, combo))
            for v in vf["verdicts"]:
                v["verdict"] = col[v["row_id"]]
            json.dump(vf, io.open(vf_path, "w", encoding="utf-8"), ensure_ascii=False)
            pool = Pool.load(tmp / "pool")
            res = audit_panel(pool, [LLAMA, QWEN], sorted(m for m in pool.models if m not in (LLAMA, QWEN)),
                              bootstrap_iters=2)   # ranking uses point estimates; the CI is not used here
            ds = next(r for r in res["candidates_ranked"] if r["model"] == MODEL)
            pick = res["recommendation"]["model"]
            picks[pick] = picks.get(pick, 0) + 1
            cases.append({"fill": {f"{by_row[r]['idx']}/tau{by_row[r]['tau']}": v for r, v in zip(err, combo)},
                          "deepseek_delta": ds["per_stratum_delta_Phi_V"]["diagnosis"],
                          "deepseek_spec": ds["specificity_clean"], "pick": pick})
        d = [c["deepseek_delta"] for c in cases]
        s = [c["deepseek_spec"] for c in cases]
        return {"n_fills": len(cases), "picks": picks,
                "deepseek_delta_range": [min(d), max(d)], "deepseek_spec_range": [min(s), max(s)],
                "fills_picking_deepseek": [c for c in cases if c["pick"] == MODEL]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def light_items():
    """The 240 canonical items WITHOUT raw note text — committed files only, so --selftest runs on a
    fresh clone. Same order and row_id as run_pool_judgebench_v2.canonical_items: sort by (tau, str(idx))."""
    items = [{"idx": t["idx"], "tau": 1, "error_type": "diagnosis", "condition": "corrupted"}
             for t in json.load(io.open(TAU1, encoding="utf-8"))["items"]]
    items += [{"idx": c["idx"], "tau": 0, "error_type": "none", "condition": "clean"}
              for c in json.load(io.open(CTRL, encoding="utf-8"))["items"] if c.get("control_type") == "primary_paired"]
    items.sort(key=lambda it: (it["tau"], str(it["idx"])))
    for i, it in enumerate(items):
        it["row_id"] = i
    return items


def load_committed(items):
    vf = json.load(io.open(COMMITTED, encoding="utf-8"))
    col = {}
    for v, it in zip(vf["verdicts"], items):
        assert v["row_id"] == it["row_id"] and str(v["idx"]) == str(it["idx"]) and v["tau"] == it["tau"], \
            f"committed row {v['row_id']} misaligned with canonical items"
        col[v["row_id"]] = v["verdict"]
    assert len(col) == 240
    return col


# ---------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="offline: reproduce the committed analysis only")
    ap.add_argument("--out", default=str(_REPO / "results" / "judgebench_v2_deepseek_budget_check.json"))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--phases", default="AB", choices=["A", "B", "AB"],
                    help="A = the committed ERROR rows only; B = full 240-row re-run at both budgets")
    args = ap.parse_args()

    items = light_items()
    committed = load_committed(items)
    base = analyse(items, committed, "committed (max_tokens=4000, pool run)")
    print(json.dumps(base, indent=1))
    ok = (base["delta_phi_v"] == 0.1238 and base["ci95"] == [0.1024, 0.144] and base["errors"] == 7
          and base["selector"]["recommended"] == "openai/gpt-oss-120b")
    print("SELFTEST", "PASS" if ok else "FAIL")
    if not ok:
        sys.exit(1)
    bound = completion_bound(items, committed)
    print("bound over ERROR-row fill-ins:", json.dumps({k: v for k, v in bound.items()
                                                         if k != "fills_picking_deepseek"}),
          "| fills picking DeepSeek:", [c["fill"] for c in bound["fills_picking_deepseek"]])
    if args.selftest:
        sys.exit(0)

    out = Path(args.out)
    if out.exists() and not args.force:
        sys.exit(f"ERROR: {out} exists — pass --force to overwrite.")
    key = api_key()
    probe, _ = attempt(key, "Patient given aspirin 81 mg daily.", "Patient takes low-dose aspirin daily.", 4000, 120)
    print("probe:", {k: probe.get(k) for k in ("http_status", "outcome", "finish_reason", "elapsed_s")})
    if probe.get("http_status") != 200:
        sys.exit("ABORT: probe did not return HTTP 200 (key / model availability).")

    # live calls need the raw original notes: same (untracked, local) inputs as run_pool_judgebench_v2.py
    full = POOL.canonical_items(str(TAU1), str(CTRL), "primary_paired")
    assert [(it["row_id"], str(it["idx"]), it["tau"]) for it in full] == \
           [(it["row_id"], str(it["idx"]), it["tau"]) for it in items], "canonical order mismatch"
    partial = Path(str(out) + ".partial.json")
    state = json.load(io.open(partial, encoding="utf-8")) if partial.is_file() else {"A": {}, "B": {}}
    by_row = {it["row_id"]: it for it in full}
    err_rows = sorted(r for r, v in committed.items() if v not in ("SAFE", "UNSAFE"))

    def save():
        tmp = Path(str(partial) + ".tmp")
        json.dump(state, io.open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, partial)

    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    jobs = []
    for mt in BUDGETS:
        if "A" in args.phases:
            for r in err_rows:
                for k in range(REPEATS_A):
                    jobs.append(("A", f"{mt}|{r}|{k}", mt, r))
        if "B" in args.phases:
            for r in range(240):
                jobs.append(("B", f"{mt}|{r}", mt, r))
    todo = [j for j in jobs if j[1] not in state[j[0]]]
    print(f"calls to make: {len(todo)} (resumed {len(jobs) - len(todo)})", flush=True)

    def run(job):
        phase, jk, mt, r = job
        it = by_row[r]
        if phase == "A":
            d, _ = attempt(key, it["original"], it["simplified"], mt, OBS_TIMEOUT)
            d["production_view"] = phase_a_view(d)
            return phase, jk, d
        v, tries = production_replica(key, it["original"], it["simplified"], mt)
        return phase, jk, {"verdict": v, "attempts": [{k: t.get(k) for k in (
            "outcome", "elapsed_s", "http_status", "finish_reason", "usage", "content_is_none", "content_len",
            "reasoning_len")} for t in tries]}

    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for f in as_completed([ex.submit(run, j) for j in todo]):
            phase, jk, rec = f.result()
            state[phase][jk] = rec
            done += 1
            if done % 20 == 0 or done == len(todo):
                save()
                print(f"  {done}/{len(todo)}", flush=True)

    def patched_at(mt):
        """Minimal counterfactual: committed column with its ERROR rows replaced by the phase-A
        majority verdict at this budget (ERROR if no repeat returned a verdict)."""
        col = dict(committed)
        for r in err_rows:
            vs = [state["A"][f"{mt}|{r}|{k}"].get("verdict") for k in range(REPEATS_A)]
            vs = [v for v in vs if v in ("SAFE", "UNSAFE")]
            col[r] = max(sorted(set(vs)), key=vs.count) if vs else "ERROR"
        return col

    analysis = [base]
    phase_a = []
    if "A" in args.phases:
        for mt in BUDGETS:
            analysis.append(analyse(items, patched_at(mt),
                                    f"committed, 7 ERROR rows replaced by phase-A majority @{mt}"))
            for r in err_rows:
                for k in range(REPEATS_A):
                    d = state["A"][f"{mt}|{r}|{k}"]
                    phase_a.append({"row_id": r, "idx": str(by_row[r]["idx"]), "tau": by_row[r]["tau"],
                                    "max_tokens": mt, "repeat": k} | d)
    cols = {}
    if "B" in args.phases:
        cols = {mt: {r: state["B"][f"{mt}|{r}"]["verdict"] for r in range(240)} for mt in BUDGETS}
        analysis += [analyse(items, cols[4000], "re-run, max_tokens=4000"),
                     analyse(items, cols[8000], "re-run, max_tokens=8000 (matched to gpt-oss)")]
    payload = {
        "purpose": "Is DeepSeek-V4-Flash's 7-ERROR result on JudgeBench v2 a max_tokens artifact (4000 vs gpt-oss 8000)?",
        "model": MODEL, "prompt": "deployed (safety_gate.JUDGE_PROMPT), temperature 0, payload keys as safety_gate._call_judge",
        "started_utc": started,
        "finished_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "phase_a": {"rows": err_rows, "budgets": list(BUDGETS), "repeats": REPEATS_A,
                    "client_timeout_s": OBS_TIMEOUT, "production_timeout_s": PROD_TIMEOUT, "calls": phase_a},
        "phases_run": args.phases,
        "phase_b": None if "B" not in args.phases else {
            "budgets": list(BUDGETS), "semantics": "safety_gate._call_judge replica: 60 s timeout, 3 attempts",
            "verdicts": {str(mt): [{"row_id": r, "idx": str(by_row[r]["idx"]), "tau": by_row[r]["tau"],
                                    "verdict": cols[mt][r],
                                    "attempts": state["B"][f"{mt}|{r}"]["attempts"]} for r in range(240)]
                         for mt in BUDGETS}},
        "committed_error_fill_bound": bound,
        "analysis": analysis,
    }
    tmp = Path(str(out) + ".tmp")
    json.dump(payload, io.open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, out)
    partial.unlink(missing_ok=True)
    for a in payload["analysis"]:
        s = a["selector"]
        print(f"{a['label']:62} err={a['errors']:>2} spec={a['spec_tau0']:>7} dPhi={a['delta_phi_v']:+.4f} "
              f"{a['ci95']} -> {s['recommended']}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
