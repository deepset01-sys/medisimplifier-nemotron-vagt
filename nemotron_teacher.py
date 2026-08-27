"""nemotron_teacher.py — reference simplifications with Nemotron Super (teacher).

Teacher-model ground-truth generation for MediSimplifier v2. Uses the EXACT
simplification prompt from the original Technion notebook (which used Claude
Opus 4.5 as the teacher), but swaps in NVIDIA Nemotron-3 Super on Nebius Token
Factory.

DATA SOURCE NOTE: the discharge summaries (the `input` field) live in the v1
calibration_verdicts.json — NOT in nemotron_calibration_full.json, whose
per_sample records store only verdicts (idx/condition/error_type + 3 judges), no
text. The 708 JudgeBench records cover only 519 UNIQUE discharge summaries (each
source note recurs as a clean control + corrupted variants), so this script
de-duplicates by idx and generates ONE reference per unique summary → 519 calls.

Prompt is byte-identical to the notebook's assembled
  SIMPLIFY_PROMPT_TEMPLATE.format(instruction=SIMPLIFICATION_INSTRUCTION, complex_text=...)
The persona lives in the single user message — there is NO system prompt.

Intentional differences from the Opus run:
  • model       = nvidia/nemotron-3-super-120b-a12b  (Token Factory)
  • temperature = 0    (pinned for reproducibility; Opus used the API default)
  • max_tokens  = 1024 (same as Opus)

⚠️  Nemotron Super is a REASONING model. Like Nemotron Nano it can spend the
token budget "thinking" and return content=None / finish_reason="length" when
max_tokens is too small. 1024 matches Opus but MAY be too small here. The
--limit 5 smoke test reveals this immediately: empty outputs are recorded in the
`error` field (with finish_reason). If that happens, raise --max-tokens.

Usage:
  python nemotron_teacher.py --limit 5                 # smoke test (5 records)
  python nemotron_teacher.py --workers 12              # full 708
  python nemotron_teacher.py --limit 5 --max-tokens 8000   # if 1024 truncates

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

try:
    from openai import OpenAI
except ImportError:
    sys.exit("The 'openai' package is required (pip install openai).")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

# ── CONFIG ──────────────────────────────────────────────────────────────────
MODEL = "nvidia/nemotron-3-super-120b-a12b"
BASE_URL = "https://api.studio.nebius.ai/v1/"
DEFAULT_MAX_TOKENS = 1024          # same as the Claude Opus teacher run
TEMPERATURE = 0                    # pinned for reproducibility (Opus used default)

# The discharge summaries (idx + `input`) come from the v1 calibration file.
DATA_CANDIDATES = [
    Path(r"D:\Owner\Desktop\assignment_01\medisimplifier-nebius\results\nebius_evidence\calibration_verdicts.json"),
    Path("calibration_verdicts.json"),
]

# ── PROMPT (verbatim assembled prompt from the Technion notebook, cell 25) ───
# Persona + guidelines + template in ONE user message; {complex_text} is the
# discharge summary, substituted by literal replacement (not str.format, so
# stray braces in the clinical note can't break it).
SIMPLIFICATION_INSTRUCTION = """You are a medical communication expert specializing in health literacy. Your task is to simplify medical documents for patients.

Simplify the following medical discharge summary in plain language for patients with no medical background.
Guidelines:
- Replace medical jargon with everyday words (e.g., "hypertension" → "high blood pressure")
- Keep all important information (diagnoses, medications, follow-up instructions)
- Use short, clear sentences (aim for 15-20 words per sentence)
- Aim for a 6th-grade reading level
- Maintain the same structure as the original
- Do not add or omit information
- Keep the same patient reference style (e.g., "The patient" stays "The patient", not "You")
- Output plain text only (no markdown, no bold, no headers, no bullet points)
- Do not include empty lines or separator characters like "---"

Medical Discharge Summary:
---
{complex_text}
---

Simplified Version:"""


def build_prompt(complex_text):
    return SIMPLIFICATION_INSTRUCTION.replace("{complex_text}", complex_text)


# ── SINGLE TEACHER CALL (retry 3x) ───────────────────────────────────────────
# A reasoning model can fail two ways at a given budget: (a) content=None when it
# spends the whole budget thinking, or (b) a NON-EMPTY but TRUNCATED answer when
# reasoning + partial answer hit finish_reason="length". Both are treated as
# errors and retried (raise --max-tokens if they persist) — never silently saved.
def _normalize(text):
    # U+2011 non-breaking hyphen -> plain '-' (prompt asks for plain text)
    return text.replace("‑", "-")


def simplify_text(client, complex_text, max_tokens, max_retries=3):
    """One teacher call for a discharge summary. Returns (simplification, error)."""
    prompt = build_prompt(complex_text)
    last_err = None
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=TEMPERATURE,
            )
            choice = resp.choices[0]
            content = choice.message.content
            finish = choice.finish_reason
            if content is None or not content.strip():
                # reasoning model burned the budget before emitting any output
                last_err = f"empty content (finish_reason={finish})"
                raise ValueError(last_err)
            if finish == "length":
                # non-empty but truncated mid-answer — do NOT save a partial reference
                last_err = f"truncated output (finish_reason=length, {len(content)} chars)"
                raise ValueError(last_err)
            return _normalize(content.strip()), None
        except Exception as e:  # noqa: BLE001 — surface every failure
            last_err = str(e)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None, last_err


def load_records(path_arg):
    """Return ALL source records as an ordered list of (idx, input) — 708 rows,
    duplicates kept — plus the ordered list of UNIQUE input texts to call once."""
    candidates = [Path(path_arg)] if path_arg else DATA_CANDIDATES
    data_path = next((p for p in candidates if p.exists()), None)
    if data_path is None:
        sys.exit(f"data not found. Tried: {', '.join(str(p) for p in candidates)}")
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    recs = raw["per_sample"] if isinstance(raw, dict) else raw
    all_records = [(r["idx"], r["input"]) for r in recs]           # every record (708)
    unique_inputs = list(dict.fromkeys(inp for _, inp in all_records))  # distinct texts
    print(f"Loaded {len(all_records)} records ({len(unique_inputs)} unique input texts) "
          f"from {data_path}")
    return all_records, unique_inputs


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process first N unique inputs (smoke test)")
    ap.add_argument("--workers", type=int, default=12, help="concurrent workers")
    ap.add_argument("--checkpoint-every", type=int, default=50, help="write partial output every N completed calls")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="max output tokens per call")
    ap.add_argument("--data", default=None, help="path to calibration_verdicts.json (idx + input)")
    ap.add_argument("--output", default="nemotron_references.json")
    ap.add_argument("--nebius-api-key", default=os.getenv("NEBIUS_API_KEY"))
    args = ap.parse_args()

    if not args.nebius_api_key:
        sys.exit("ERROR: NEBIUS_API_KEY not set (export it or pass --nebius-api-key)")

    # all_records = every JudgeBench row (708); unique_inputs = distinct texts to call.
    all_records, unique_inputs = load_records(args.data)
    if args.limit is not None:
        unique_inputs = unique_inputs[:args.limit]
        keep = set(unique_inputs)
        all_records = [(i, t) for (i, t) in all_records if t in keep]
    n_calls = len(unique_inputs)          # actual API calls (one per unique input)
    n_out = len(all_records)              # output records (fan-out, incl. duplicates)

    client = OpenAI(base_url=BASE_URL, api_key=args.nebius_api_key)
    out_path = Path(args.output)
    result_map = {}                       # input_text -> (simplification, error)
    lock = threading.Lock()

    print(f"\nGenerating references with {MODEL}")
    print(f"API calls: {n_calls} unique inputs -> fanned out to {n_out} output records")
    print(f"max_tokens={args.max_tokens} temperature={TEMPERATURE} | "
          f"workers={args.workers} | checkpoint every {args.checkpoint_every} | output={args.output}")
    print("(Nemotron Super is a reasoning model; truncated/empty outputs are retried, "
          "not saved — raise --max-tokens if they persist.)", flush=True)

    def build_rows():
        # fan out each unique-input result to every record sharing that input
        rows = []
        for idx, txt in all_records:
            if txt in result_map:
                simp, err = result_map[txt]
                rows.append({"idx": idx, "input": txt,
                             "nemotron_simplification": simp, "error": err})
        return rows

    def write_out():
        out_path.write_text(json.dumps(build_rows(), indent=2, ensure_ascii=False),
                            encoding="utf-8")

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut_to_text = {ex.submit(simplify_text, client, txt, args.max_tokens): txt
                       for txt in unique_inputs}
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
                    print(f"  [{done:>3}/{n_calls}] {tag} "
                          f"elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m errors={n_err}"
                          + (f"  <- {err[:80]}" if err else ""), flush=True)
                if done % args.checkpoint_every == 0 or done == n_calls:
                    write_out()

    write_out()
    rows = build_rows()
    n_call_err = sum(1 for s, e in result_map.values() if e is not None)
    n_call_ok = n_calls - n_call_err
    n_rows_ok = sum(1 for r in rows if r["error"] is None)
    avg_len = (sum(len(r["nemotron_simplification"]) for r in rows if r["error"] is None)
               / max(1, n_rows_ok))
    print("\n" + "=" * 60)
    print("TEACHER GENERATION RESULTS")
    print("=" * 60)
    print(f"Model:            {MODEL}")
    print(f"Output records:   {len(rows)}  (target {n_out})")
    print(f"Unique API calls: {n_call_ok}/{n_calls} succeeded, {n_call_err} errored")
    print(f"Records w/ valid reference: {n_rows_ok}/{len(rows)}")
    print(f"Avg output length: {avg_len:.0f} chars")
    print(f"Saved to:         {out_path.resolve()}")
    if n_call_err == n_calls:
        print("\n>>> FAIL: every call errored. If 'finish_reason=length', raise --max-tokens.")
    elif n_call_err > 0:
        print(f"\n>>> PARTIAL: {n_call_err} unique input(s) errored (see `error` fields).")
    else:
        print("\n>>> PASS: all unique inputs simplified; every record has a reference.")


if __name__ == "__main__":
    main()
