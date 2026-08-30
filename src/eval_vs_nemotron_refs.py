"""
eval_vs_nemotron_refs.py — Score v2 student predictions against NEMOTRON references.

The default eval (results/eval_v2_results.json) scores the student against CLAUDE
references — but the student was TRAINED on Nemotron references, so that understates
fidelity. This re-scores the SAME student predictions against nemotron_output (the
references it was actually taught to imitate), giving the "fair second yardstick".

Runs anywhere the metric libs exist (the train-v30 image, or a local env with
rouge_score / textstat / bert_score / easse). Use --fast to skip BERTScore + SARI.
"""
import json, argparse
from pathlib import Path
import numpy as np


def compute_rouge_l(predictions, references):
    from rouge_score import rouge_scorer
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    scores = [scorer.score(ref, pred)["rougeL"].fmeasure
              for pred, ref in zip(predictions, references)]
    return float(np.mean(scores)), [float(s) for s in scores]


def compute_fk_grade(texts):
    import textstat
    out = []
    for t in texts:
        try:
            out.append(textstat.flesch_kincaid_grade(t))
        except Exception as e:
            print(f"Warning: FK-Grade failed for a sample: {e}")
    return float(np.mean(out)) if out else 0.0


def compute_bertscore(predictions, references):
    import torch
    from bert_score import score as bert_score
    P, R, F1 = bert_score(predictions, references, lang="en",
                          model_type="roberta-large",
                          device="cuda" if torch.cuda.is_available() else "cpu",
                          verbose=False)
    return float(F1.mean())


def compute_sari(sources, predictions, references):
    from easse.sari import corpus_sari
    return corpus_sari(orig_sents=sources, sys_sents=predictions, refs_sents=[references])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="eval_v2_nemotron/predictions.json",
                    help="predictions.json from the eval job (--save-predictions)")
    ap.add_argument("--refs", default="nemotron_training_references.json",
                    help="local file with nemotron_output per record")
    ap.add_argument("--split", default="test")
    ap.add_argument("--output", default="results/eval_v2_nemotron_results.json")
    ap.add_argument("--fast", action="store_true", help="skip BERTScore + SARI")
    args = ap.parse_args()

    preds = json.load(open(args.predictions, encoding="utf-8"))
    refs_all = json.load(open(args.refs, encoding="utf-8"))
    ref_by_index = {r["index"]: r for r in refs_all if r.get("split") == args.split}

    sources, predictions, references = [], [], []
    n_err, n_missing, n_mismatch = 0, 0, 0
    for p in preds:
        r = ref_by_index.get(p["index"])
        if r is None:
            n_missing += 1; continue
        nem = (r.get("nemotron_output") or "").strip()
        if not nem or r.get("error"):
            n_err += 1; continue
        # sanity: same source input aligns index<->index
        if (r.get("input", "").strip()[:200] != p.get("input", "").strip()[:200]):
            n_mismatch += 1; continue
        sources.append(p["input"])
        predictions.append(p.get("prediction", "") or "")
        references.append(nem)

    n = len(predictions)
    print(f"Matched {n} pairs | skipped errored={n_err} missing={n_missing} mismatched={n_mismatch}")
    if n == 0:
        raise SystemExit("No aligned pairs — check --predictions / --refs / --split.")

    print("Computing ROUGE-L...")
    rouge, rouge_ps = compute_rouge_l(predictions, references)
    print("Computing FK-Grade...")
    fk = compute_fk_grade(predictions)
    if args.fast:
        bert, sari = None, None
    else:
        print("Computing BERTScore...")
        bert = compute_bertscore(predictions, references)
        print("Computing SARI...")
        sari = compute_sari(sources, predictions, references)

    results = {
        "model": "openbio",
        "split": args.split,
        "reference_type": "nemotron",          # <-- distinguishes from eval_v2_results.json (claude)
        "n_samples": n,
        "n_skipped_errored": n_err,
        "n_skipped_missing": n_missing,
        "n_mismatched": n_mismatch,
        "rouge_l": rouge,
        "rouge_l_per_sample": rouge_ps,
        "bertscore": bert,
        "sari": sari,
        "fk_grade": fk,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print("\n-- Results (vs Nemotron references) --")
    for k, v in results.items():
        if k != "rouge_l_per_sample":
            print(f"  {k}: {v}")
    print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
