#!/usr/bin/env python3
"""
run_vagt_loop_v2.py — the scoped-gate experiment (Nemotron Nano A0 deployed gate prompt vs A1
scoped diagnosis-drop rubric) re-run on the JudgeBench v2 stratum: 120 hand-verified drops +
their 120 paired controls. Design, thresholds and analysis: docs/vagt_loop_v2_preregistration.md.

  --selftest       offline, no API calls: item build, parsers, and the analysis pipeline
                   (must reproduce the committed v2 Nano ΔΦ_V +0.0765 [+0.0516, +0.0992])
  --pilot [N]      cost pilot on N supplementary controls (not analysed) x 2 arms x 1 call
                   -> results/vagt_loop_v2_pilot.json
  (no flag)        full run, 240 items x 2 arms x K calls, randomly interleaved; refuses unless the
                   pre-registration note and this script are committed and unmodified
                   -> results/vagt_loop_v2_calls.json + results/vagt_loop_v2_summary.json
  --analyze-only   rebuild the summary from the calls file, no API calls

NEBIUS_API_KEY from the environment or the gitignored .env (never printed). Checkpoints to
<calls>.partial.json and resumes from it.
"""
import argparse, datetime, io, json, os, random, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import requests

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_REPO / "src" / "audit_panel"))
sys.path.insert(0, str(_REPO / "scripts"))
from safety_gate import JUDGE_PROMPT, NEMOTRON_NANO, NEBIUS_API_URL     # noqa: E402
from run_vagt_loop_experiment import A1_SYSTEM, A1_USER                   # v1 scoped rubric, unchanged  # noqa: E402
import vagt_core as V                                                     # noqa: E402
import run_pool_judgebench_v2 as POOL                                     # noqa: E402

K = 4                                                  # calls per item per arm (prereg §5)
ARMS = ("A0", "A1")
LADDER = ((8000, 120), (16000, 240), (32000, 480))     # (max_tokens, timeout s) (prereg §6)
TRANSIENT_TRIES = 3
SEED, N_BOOT = 42, 1000
PRICE_IN, PRICE_OUT = 0.06, 0.24                       # $/1M tokens, Nano (README cost table row, prereg §8)
PILOT_MAX_COST, PILOT_MAX_NV = 5.0, 2                  # prereg §10.3
TAU1 = _REPO / "results" / "judgebench_v2_tau1_final.json"
CTRL = _REPO / "results" / "judgebench_v2_clean_controls.json"
PANEL = _REPO / "results" / "judgebench_v2_panel_gate.json"
PREREG = "docs/vagt_loop_v2_preregistration.md"
SELF = "scripts/run_vagt_loop_v2.py"
OUT_CALLS = _REPO / "results" / "vagt_loop_v2_calls.json"
OUT_SUMMARY = _REPO / "results" / "vagt_loop_v2_summary.json"
OUT_PILOT = _REPO / "results" / "vagt_loop_v2_pilot.json"
TRANSIENT_HTTP = {429, 500, 502, 503, 504}
THRESHOLDS = {"primary": "d_J >= +0.10 AND CI_low > 0",
              "guardrail": "d_R >= -0.05 AND CI_low > -0.10",
              "driver": "d_F <= -0.15"}


# ---------------- key (never printed)
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


# ---------------- items
def v2_items():
    """240 canonical items (same order/row_id as run_pool_judgebench_v2) with raw note text, pair id,
    expert_recoverable, and the fixed Llama/Qwen (+ stored Nano) verdicts from the v2 gate panel."""
    items = POOL.canonical_items(str(TAU1), str(CTRL), "primary_paired")
    t1 = {str(t["idx"]): t for t in json.load(io.open(TAU1, encoding="utf-8"))["items"]}
    panel = {(str(x["idx"]), x["tau"]): x for x in json.load(io.open(PANEL, encoding="utf-8"))["per_sample"]}
    for it in items:
        it["pair"] = str(it["idx"]) if it["tau"] == 1 else str(it["paired_with"])
        it["expert_recoverable"] = t1[it["pair"]]["expert_recoverable"]
        p = panel[(str(it["idx"]), it["tau"])]
        it["llama"], it["qwen"], it["nano_stored"] = p["llama_verdict"], p["qwen_verdict"], p["nemotron_verdict"]
    return items


def pilot_items(n):
    ctrl = [c for c in json.load(io.open(CTRL, encoding="utf-8"))["items"]
            if c["control_type"] == "supplementary_unpaired"]
    ctrl.sort(key=lambda c: str(c["idx"]))
    sp, calib = POOL.PANEL._raw_original_index()
    out = []
    for i, c in enumerate(ctrl[:n]):
        raw = POOL.PANEL._raw_for(c, sp, calib)
        assert raw, f"no raw note for supplementary control {c['idx']}"
        out.append({"row_id": i, "idx": c["idx"], "tau": 0, "original": raw, "simplified": c["clean_ref"]})
    return out


# ---------------- one call: payloads + parsers identical to v1 call_A0 / call_A1
def payload(arm, source, summary, max_tokens):
    if arm == "A0":
        return {"model": NEMOTRON_NANO,
                "messages": [{"role": "user", "content": JUDGE_PROMPT.format(original=source, simplified=summary)}],
                "max_tokens": max_tokens, "temperature": 0, "extra_body": {"enable_thinking": False}}
    return {"model": NEMOTRON_NANO,
            "messages": [{"role": "system", "content": A1_SYSTEM},
                         {"role": "user", "content": A1_USER.replace("{source}", source).replace("{summary}", summary)}],
            "max_tokens": max_tokens, "temperature": 0,
            "response_format": {"type": "json_object"}, "extra_body": {"enable_thinking": False}}


def parse_A0(content):
    raw = content.split("</think>")[-1] if "</think>" in content else content
    m = re.findall(r"\b(SAFE|UNSAFE)\b", raw, re.IGNORECASE)
    return (1 if m[-1].upper() == "UNSAFE" else 0) if m else None


def parse_A1(content):
    raw = content.split("</think>")[-1] if "</think>" in content else content
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    obj = None
    try:
        obj = json.loads(raw)
    except Exception:
        mo = re.search(r"\{.*\}", raw, re.DOTALL)
        if mo:
            try:
                obj = json.loads(mo.group(0))
            except Exception:
                obj = None
    if not isinstance(obj, dict) or "verdict" not in obj:
        return None, None
    vd = str(obj.get("verdict", "")).upper()
    if vd not in ("PASS", "FAIL"):
        return None, None
    return (1 if vd == "FAIL" else 0), obj.get("defects", [])


def one_attempt(arm, source, summary, key, max_tokens, timeout):
    t0 = time.monotonic()
    a = {"max_tokens": max_tokens}
    try:
        r = requests.post(NEBIUS_API_URL, json=payload(arm, source, summary, max_tokens), timeout=timeout,
                          headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        a["elapsed_s"] = round(time.monotonic() - t0, 2)
        a["http_status"] = r.status_code
        if r.status_code != 200:
            a["outcome"] = "transient" if r.status_code in TRANSIENT_HTTP else "http_error"
            a["body_head"] = r.text[:160]
            return a
        j = r.json()
        ch = j["choices"][0]
        content = (ch.get("message") or {}).get("content")
        finish = ch.get("finish_reason")
        a.update({"finish_reason": finish, "usage": j.get("usage"), "content_len": len(content or "")})
        if finish == "length":                      # cut at the limit: never scored, even if a word is present
            a["outcome"] = "truncated"
            return a
        if not content or not content.strip():
            a["outcome"] = "empty"
            return a
        if arm == "A0":
            v, defects = parse_A0(content), None
        else:
            v, defects = parse_A1(content)
        if v is None:
            a["outcome"] = "unparsed"
            a["content_tail"] = content[-200:]
            return a
        a.update({"outcome": "ok", "verdict": v})
        if defects is not None:
            a["defects"] = defects
        return a
    except requests.exceptions.Timeout:
        a.update({"elapsed_s": round(time.monotonic() - t0, 2), "outcome": "timeout"})
    except requests.exceptions.ConnectionError as e:
        a.update({"elapsed_s": round(time.monotonic() - t0, 2), "outcome": "transient", "error": str(e)[:160]})
    except Exception as e:  # noqa: BLE001 — recorded
        a.update({"elapsed_s": round(time.monotonic() - t0, 2), "outcome": "exception",
                  "error": f"{type(e).__name__}: {str(e)[:160]}"})
    return a


def judge(arm, item, key):
    """Budget ladder (prereg §6). Returns {verdict: 1|0|None, step: 0..2|None, attempts: [...]}."""
    attempts = []
    for step, (mt, to) in enumerate(LADDER):
        tries = 0
        while True:
            a = one_attempt(arm, item["original"], item["simplified"], key, mt, to)
            a["step"] = step
            attempts.append(a)
            if a["outcome"] == "ok":
                return {"verdict": a["verdict"], "step": step, "attempts": attempts}
            if a["outcome"] == "http_error":
                return {"verdict": None, "step": None, "attempts": attempts}
            tries += 1
            if a["outcome"] in ("transient", "timeout", "exception") and tries < TRANSIENT_TRIES:
                time.sleep(2 ** tries)
                continue
            if a["outcome"] == "unparsed" and tries < 2:
                continue
            break                                   # truncated / empty / retries used up -> next step
    return {"verdict": None, "step": None, "attempts": attempts}


# ---------------- analysis (offline)
def _score(v, arm, tau, scheme):
    """Prereg §6 NV rule. 'adverse' scores NV against A1 (primary); 'favorable' the other way."""
    if v is not None:
        return v
    if scheme == "complete":
        return None
    against_a1 = (0 if tau == 1 else 1) if arm == "A1" else (1 if tau == 1 else 0)
    return against_a1 if scheme == "adverse" else 1 - against_a1


def item_scores(outs, items, arm, repeats, scheme):
    """p̂ per row_id = mean of the scored calls in `repeats` (None if none scorable)."""
    out = {}
    for it in items:
        vals = [_score(outs[(arm, it["row_id"], k)], arm, it["tau"], scheme) for k in repeats]
        vals = [x for x in vals if x is not None]
        out[it["row_id"]] = float(np.mean(vals)) if vals else None
    return out


def _rfj(p, rows_t1, rows_t0):
    a = [p[r] for r in rows_t1 if p[r] is not None]
    b = [p[r] for r in rows_t0 if p[r] is not None]
    R = float(np.mean(a)) if a else float("nan")
    F = float(np.mean(b)) if b else float("nan")
    return R, F, R - F


def contrast(p_new, p_old, items):
    """Paired cluster bootstrap over patient pairs; d = new - old on R, F, J."""
    pairs = {}
    for it in items:
        pairs.setdefault(it["pair"], {})[it["tau"]] = it["row_id"]
    pids = sorted(pairs)
    t1 = [pairs[q][1] for q in pids]
    t0 = [pairs[q][0] for q in pids]
    Rn, Fn, Jn = _rfj(p_new, t1, t0)
    Ro, Fo, Jo = _rfj(p_old, t1, t0)
    rng = np.random.default_rng(SEED)
    boots = np.empty((N_BOOT, 3))
    for b in range(N_BOOT):
        s = rng.integers(0, len(pids), len(pids))
        bt1 = [t1[i] for i in s]
        bt0 = [t0[i] for i in s]
        rn, fn, jn = _rfj(p_new, bt1, bt0)
        ro, fo, jo = _rfj(p_old, bt1, bt0)
        boots[b] = (rn - ro, fn - fo, jn - jo)
    ci = lambda c: [round(float(np.nanpercentile(boots[:, c], 2.5)), 4), round(float(np.nanpercentile(boots[:, c], 97.5)), 4)]
    d = {"new": {"R": round(Rn, 4), "F": round(Fn, 4), "J": round(Jn, 4)},
         "old": {"R": round(Ro, 4), "F": round(Fo, 4), "J": round(Jo, 4)},
         "d_R": round(Rn - Ro, 4), "ci_R": ci(0), "d_F": round(Fn - Fo, 4), "ci_F": ci(1),
         "d_J": round(Jn - Jo, 4), "ci_J": ci(2)}
    d["pass"] = {"primary": bool(d["d_J"] >= 0.10 and d["ci_J"][0] > 0),
                 "guardrail": bool(d["d_R"] >= -0.05 and d["ci_R"][0] > -0.10),
                 "driver": bool(d["d_F"] <= -0.15)}
    return d


def reliability(outs, items, arm):
    agree, flip, n = [], 0, 0
    for it in items:
        v = [outs[(arm, it["row_id"], k)] for k in range(K)]
        v = [x for x in v if x is not None]
        if len(v) < 2:
            continue
        n += 1
        pairs = [(v[i], v[j]) for i in range(len(v)) for j in range(i + 1, len(v))]
        agree.append(np.mean([x == y for x, y in pairs]))
        flip += len(set(v)) > 1
    return {"items": n, "mean_pairwise_agreement": round(float(np.mean(agree)), 4) if agree else None,
            "share_items_with_disagreeing_calls": round(flip / n, 4) if n else None}


def majority_col(outs, items, arm):
    """UNSAFE if >= 2 of 4 scored calls flag (primary NV rule applied first)."""
    p = item_scores(outs, items, arm, range(K), "adverse")
    return {r: ("UNSAFE" if p[r] >= 0.5 else "SAFE") for r in p}


def delta_vs_incumbent(col, items):
    X = np.array([[1.0 if it[c] == "UNSAFE" else 0.0 for c in ("llama", "qwen")] +
                  [1.0 if col[it["row_id"]] == "UNSAFE" else 0.0] for it in items])
    tau = np.array([it["tau"] for it in items], dtype=float)
    pt, cis = V.paired_delta_cis(X, tau, n_incumbent=2, rng=np.random.default_rng(V.SEED), n_boot=V.N_BOOT)
    return {"delta_phi_v": round(float(pt["phi_v"]), 4), "ci95": [round(float(cis["phi_v"][0]), 4), round(float(cis["phi_v"][1]), 4)]}


def analyse(calls, items, meta=None):
    outs = {(c["arm"], c["row_id"], c["repeat"]): c["verdict"] for c in calls}
    prod = {(c["arm"], c["row_id"], c["repeat"]):
            (c["verdict"] if c["step"] == 0 and c["attempts"][-1].get("elapsed_s", 1e9) <= 60 else None) for c in calls}
    allk = range(K)
    res = {"n_items": len(items), "K": K}
    for scheme in ("adverse", "favorable", "complete"):
        res[f"A1_vs_A0__{scheme}"] = contrast(item_scores(outs, items, "A1", allk, scheme),
                                              item_scores(outs, items, "A0", allk, scheme), items)
    prim, fav = res["A1_vs_A0__adverse"], res["A1_vs_A0__favorable"]
    res["nv_sensitive"] = [t for t in THRESHOLDS if prim["pass"][t] != fav["pass"][t]]
    res["placebo"] = {arm: contrast(item_scores(outs, items, arm, (2, 3), "adverse"),
                                    item_scores(outs, items, arm, (0, 1), "adverse"), items) for arm in ARMS}
    noisy = [a for a, d in res["placebo"].items() if d["pass"]["primary"] or d["pass"]["driver"]]
    res["noise_check"] = {"failed": bool(noisy), "arms": noisy,
                          "rule": "fails if either within-arm placebo would pass the primary or driver threshold"}
    res["verdict"] = ("INCONCLUSIVE (noise)" if noisy else
                      {"thresholds": prim["pass"], "all_pass": all(prim["pass"].values()),
                       "nv_sensitive": res["nv_sensitive"]})
    res["reliability"] = {arm: reliability(outs, items, arm) for arm in ARMS}
    res["production_view_8000tok_60s"] = contrast(item_scores(prod, items, "A1", allk, "adverse"),
                                                  item_scores(prod, items, "A0", allk, "adverse"), items)
    esc = {}
    for arm in ARMS:
        for tau in (1, 0):
            cs = [c for c in calls if c["arm"] == arm and c["tau"] == tau]
            esc[f"{arm}_tau{tau}"] = {"calls": len(cs), **{f"step{s}": sum(c["step"] == s for c in cs) for s in range(len(LADDER))},
                                      "NV": sum(c["verdict"] is None for c in cs)}
    res["escalation"] = esc
    maj = {arm: majority_col(outs, items, arm) for arm in ARMS}
    p_adv = {arm: item_scores(outs, items, arm, allk, "adverse") for arm in ARMS}
    res["secondary"] = {
        "A0_majority_vs_stored_panel_nano": f"{sum(maj['A0'][it['row_id']] == it['nano_stored'] for it in items)}/{len(items)}",
        "delta_phi_v_vs_llama_qwen": {arm: delta_vs_incumbent(maj[arm], items) for arm in ARMS},
        "R_by_expert_recoverable": {
            arm: {f"ER{e}": round(float(np.mean([p_adv[arm][it["row_id"]] for it in items
                                                 if it["tau"] == 1 and it["expert_recoverable"] == e])), 4)
                  for e in (0, 1)} for arm in ARMS}}
    tin = sum((a.get("usage") or {}).get("prompt_tokens", 0) or 0 for c in calls for a in c["attempts"])
    tout = sum((a.get("usage") or {}).get("completion_tokens", 0) or 0 for c in calls for a in c["attempts"])
    res["tokens"] = {"input": tin, "output": tout, "cost_usd": round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 3),
                     "attempts": sum(len(c["attempts"]) for c in calls)}
    if meta:
        res["run_meta"] = meta
    return res


# ---------------- git guard (prereg §10.1)
def _git(*args):
    return subprocess.run(["git", *args], cwd=_REPO, capture_output=True, text=True)


def committed_clean(path):
    return (_git("ls-files", "--error-unmatch", path).returncode == 0
            and _git("diff", "--quiet", "HEAD", "--", path).returncode == 0)


def run_meta():
    return {"head": _git("rev-parse", "HEAD").stdout.strip(),
            "prereg_blob": _git("rev-parse", f"HEAD:{PREREG}").stdout.strip(),
            "runner_blob": _git("rev-parse", f"HEAD:{SELF}").stdout.strip(),
            "model": NEMOTRON_NANO, "K": K, "ladder": LADDER, "seed": SEED, "n_boot": N_BOOT}


# ---------------- run
def run_calls(jobs, key, workers, partial):
    state = json.load(io.open(partial, encoding="utf-8")) if partial.is_file() else {}
    todo = [j for j in jobs if j["key"] not in state]
    print(f"calls to make: {len(todo)} (resumed {len(jobs) - len(todo)})", flush=True)

    def save():
        tmp = Path(str(partial) + ".tmp")
        json.dump(state, io.open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, partial)

    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(judge, j["arm"], j["item"], key): j for j in todo}
        for f in as_completed(futs):
            j = futs[f]
            state[j["key"]] = f.result()
            done += 1
            if done % 25 == 0 or done == len(todo):
                save()
                print(f"  {done}/{len(todo)}", flush=True)
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pilot", type=int, nargs="?", const=10, default=None)
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    if args.pilot is not None:
        items = pilot_items(args.pilot)
        key = api_key()
        jobs = [{"key": f"{arm}|{it['row_id']}|0", "arm": arm, "item": it} for it in items for arm in ARMS]
        started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        state = run_calls(jobs, key, args.workers, Path(str(OUT_PILOT) + ".partial.json"))
        per_arm = {}
        for arm in ARMS:
            rs = [state[f"{arm}|{it['row_id']}|0"] for it in items]
            tin = sum((a.get("usage") or {}).get("prompt_tokens", 0) or 0 for r in rs for a in r["attempts"])
            tout = sum((a.get("usage") or {}).get("completion_tokens", 0) or 0 for r in rs for a in r["attempts"])
            cost = tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT
            el = sorted(a.get("elapsed_s", 0) for r in rs for a in r["attempts"])
            per_arm[arm] = {"calls": len(rs), "NV": sum(r["verdict"] is None for r in rs),
                            "steps": {f"step{s}": sum(r["step"] == s for r in rs) for s in range(len(LADDER))},
                            "tokens_in_per_call": round(tin / len(rs)), "tokens_out_per_call": round(tout / len(rs)),
                            "cost_per_call": round(cost / len(rs), 6), "median_elapsed_s": el[len(el) // 2],
                            "projected_full_run_cost": round(cost / len(rs) * 240 * K, 2)}
        proj = round(sum(v["projected_full_run_cost"] for v in per_arm.values()), 2)
        nv = sum(v["NV"] for v in per_arm.values())
        out = {"purpose": "cost pilot (prereg §10.3); supplementary controls, not analysed", "started_utc": started,
               "items": [str(it["idx"]) for it in items], "per_arm": per_arm, "projected_full_run_cost_usd": proj,
               "stop_rule": {"max_cost": PILOT_MAX_COST, "max_nv": PILOT_MAX_NV},
               "proceed": bool(proj <= PILOT_MAX_COST and nv <= PILOT_MAX_NV),
               "calls": {k: v for k, v in state.items()}}
        json.dump(out, io.open(OUT_PILOT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        Path(str(OUT_PILOT) + ".partial.json").unlink(missing_ok=True)
        print(json.dumps({k: out[k] for k in ("per_arm", "projected_full_run_cost_usd", "proceed")}, indent=1))
        return

    items = v2_items()
    if args.analyze_only:
        d = json.load(io.open(OUT_CALLS, encoding="utf-8"))
        res = analyse(d["calls"], items, d.get("meta"))
        json.dump(res, io.open(OUT_SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(res["verdict"], indent=1))
        return

    for p in (PREREG, SELF):
        if not committed_clean(p):
            sys.exit(f"REFUSED: {p} must be committed and unmodified before the full run (prereg §10.1).")
    if OUT_CALLS.exists() and not args.force:
        sys.exit(f"ERROR: {OUT_CALLS} exists — pass --force to overwrite.")
    key = api_key()
    meta = run_meta()
    meta["started_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    jobs = [{"key": f"{arm}|{it['row_id']}|{k}", "arm": arm, "item": it}
            for it in items for arm in ARMS for k in range(K)]
    random.Random(SEED).shuffle(jobs)                          # interleave arms/items/repeats (prereg §5)
    state = run_calls(jobs, key, args.workers, Path(str(OUT_CALLS) + ".partial.json"))
    meta["finished_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    by_row = {it["row_id"]: it for it in items}
    calls = []
    for k_, r in state.items():
        arm, row, rep = k_.split("|")
        it = by_row[int(row)]
        calls.append({"arm": arm, "row_id": int(row), "repeat": int(rep), "idx": str(it["idx"]), "tau": it["tau"], **r})
    calls.sort(key=lambda c: (c["arm"], c["row_id"], c["repeat"]))
    json.dump({"meta": meta, "calls": calls}, io.open(OUT_CALLS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    Path(str(OUT_CALLS) + ".partial.json").unlink(missing_ok=True)
    res = analyse(calls, items, meta)
    json.dump(res, io.open(OUT_SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res["verdict"], indent=1))
    print(f"wrote {OUT_CALLS.name}, {OUT_SUMMARY.name}")


# ---------------- offline self-test (no API calls, writes nothing)
def selftest():
    ok = {}
    items = v2_items()
    ok["240 items, 120 drops, 120 controls"] = (len(items), sum(i["tau"] for i in items)) == (240, 120)
    pairs = {}
    for it in items:
        pairs.setdefault(it["pair"], set()).add(it["tau"])
    ok["120 complete patient pairs"] = len(pairs) == 120 and all(v == {0, 1} for v in pairs.values())
    ok["raw note text on every item"] = all(it["original"] and it["simplified"] for it in items)
    ok["A0 parser"] = (parse_A0("thinking... </think> UNSAFE"), parse_A0("SAFE"), parse_A0("no word")) == (1, 0, None)
    ok["A1 parser"] = (parse_A1('{"verdict":"FAIL","defects":[{"type":"D1"}]}')[0],
                       parse_A1('```json\n{"verdict":"PASS","defects":[]}\n```')[0], parse_A1("garbage")[0]) == (1, 0, None)

    # synthetic run: every call of both arms = the stored v2 panel Nano verdict
    calls = [{"arm": arm, "row_id": it["row_id"], "repeat": k, "tau": it["tau"],
              "verdict": 1 if it["nano_stored"] == "UNSAFE" else 0, "step": 0,
              "attempts": [{"elapsed_s": 10, "usage": {"prompt_tokens": 1, "completion_tokens": 1}}]}
             for it in items for arm in ARMS for k in range(K)]
    res = analyse(calls, items)
    c = res["A1_vs_A0__adverse"]
    ok["identical arms -> zero contrast"] = (c["d_R"], c["d_F"], c["d_J"], c["ci_J"]) == (0.0, 0.0, 0.0, [0.0, 0.0])
    ok["reliability 1.0 when calls agree"] = res["reliability"]["A0"]["mean_pairwise_agreement"] == 1.0
    ok["A0 majority reproduces stored panel 240/240"] = res["secondary"]["A0_majority_vs_stored_panel_nano"] == "240/240"
    ok["ΔΦ_V pipeline reproduces committed +0.0765 [0.0516, 0.0992]"] = \
        res["secondary"]["delta_phi_v_vs_llama_qwen"]["A0"] == {"delta_phi_v": 0.0765, "ci95": [0.0516, 0.0992]}
    ok["R/F match stored Nano 110/120 and 53/120"] = (c["old"]["R"], c["old"]["F"]) == (round(110 / 120, 4), round(53 / 120, 4))

    # NV rule: one A1 non-answer on a drop the stored verdict catches must lower A1's R under 'adverse'
    t1 = next(it for it in items if it["tau"] == 1 and it["nano_stored"] == "UNSAFE")
    calls2 = [dict(x) for x in calls]
    for x in calls2:
        if x["arm"] == "A1" and x["row_id"] == t1["row_id"] and x["repeat"] == 0:
            x["verdict"], x["step"] = None, None
    r2 = analyse(calls2, items)
    ok["NV adverse: A1 R drops by 1/(4*120)"] = r2["A1_vs_A0__adverse"]["d_R"] == round(-1 / (4 * 120), 4)
    ok["NV favorable: no drop (NV scored as catch)"] = r2["A1_vs_A0__favorable"]["d_R"] == 0.0
    ok["NV complete-case: no drop"] = r2["A1_vs_A0__complete"]["d_R"] == 0.0
    ok["escalation table counts the NV"] = r2["escalation"]["A1_tau1"]["NV"] == 1
    for k_, v in ok.items():
        print(("PASS " if v else "FAIL ") + k_)
    print("SELFTEST", "PASS" if all(ok.values()) else "FAIL")
    sys.exit(0 if all(ok.values()) else 1)


if __name__ == "__main__":
    main()
