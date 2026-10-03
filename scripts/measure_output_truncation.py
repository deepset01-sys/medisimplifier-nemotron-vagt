"""
Which of the 1,001 saved v2 evaluation outputs stopped at the 512-token generation cap (src/evaluate.py,
max_new_tokens=512), and how the gate flagged them.

The fine-tuned model ends a finished answer with the literal "<|im_end|>" marker, so an output without it was cut at
the cap. Offline, no tokenizer: reads results/student_predictions.json (the outputs), results/student_audit.json (the
gate over the same 1,001 outputs) and results/student_audit_review.json (the 30-case audit), and writes
results/eval_v2_output_truncation.json with the sha256 of each input.

    python scripts/measure_output_truncation.py
"""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PREDICTIONS = "results/student_predictions.json"
AUDIT = "results/student_audit.json"
REVIEW = "results/student_audit_review.json"
OUT = REPO / "results" / "eval_v2_output_truncation.json"
END_MARKER = "<|im_end|>"
SENTENCE_END = ".!?\"')"
FLAGGED = ("UNSAFE", "DISAGREE")


def load(rel):
    """The parsed file and the sha256 of its bytes with LF line endings, as git stores them (a Windows checkout may
    hold CRLF copies, which would otherwise hash differently)."""
    raw = (REPO / rel).read_bytes()
    return json.loads(raw), "sha256:" + hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def flag_counts(indices, consensus):
    rated = [consensus[i] for i in indices if consensus[i] != "ERROR"]
    flagged = sum(c in FLAGGED for c in rated)
    return {"outputs": len(indices), "gate_error": len(indices) - len(rated), "rated": len(rated),
            "flagged": flagged, "flagged_share": round(flagged / len(rated), 4)}


def main():
    rows, sha_rows = load(PREDICTIONS)
    audit, sha_audit = load(AUDIT)
    review, sha_review = load(REVIEW)

    cut = sorted(r["index"] for r in rows if END_MARKER not in r["prediction"])
    mid = sorted(r["index"] for r in rows
                 if END_MARKER not in r["prediction"] and r["prediction"].rstrip()[-1:] not in SENTENCE_END)
    cut_set = set(cut)
    complete = sorted(r["index"] for r in rows if r["index"] not in cut_set)
    consensus = {s["index"]: s["consensus"] for s in audit["per_sample"]}
    assert sorted(consensus) == sorted(r["index"] for r in rows), "the gate run must cover the same 1,001 outputs"

    audited = [c["index"] for c in review["cases"]]
    audited_cut = [i for i in audited if i in cut_set]
    out = {
        "description": "Saved v2 evaluation outputs that stopped at the 512-token generation cap, and the gate's flags "
                       "on cut vs complete outputs.",
        "generated_by": "scripts/measure_output_truncation.py",
        "sources": {PREDICTIONS: sha_rows, AUDIT: sha_audit, REVIEW: sha_review},
        "sources_note": "sha256 of each file with LF line endings, as stored in git",
        "generation_cap": "max_new_tokens=512 (src/evaluate.py)",
        "rule": "An output without the end-of-answer marker <|im_end|> stopped at the cap. Mid-sentence: its last "
                "character is not one of . ! ? \" ' )",
        "outputs": len(rows),
        "stopped_at_cap": {"count": len(cut), "indices": cut},
        "stopped_mid_sentence": {"count": len(mid), "indices": mid},
        "gate_flags": {
            "note": "From results/student_audit.json; flagged = consensus UNSAFE or DISAGREE; ERROR is not rated.",
            "stopped_at_cap": flag_counts(cut, consensus),
            "complete": flag_counts(complete, consensus),
        },
        "audited_sample": {
            "note": "The 30-case dual-auditor sample in results/student_audit_review.json.",
            "cases": len(audited),
            "stopped_at_cap": len(audited_cut),
            "indices": audited_cut,
            "all_flagged_by_the_gate": all(consensus[i] in FLAGGED for i in audited_cut),
        },
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(cut)} of {len(rows)} stopped at the cap ({len(mid)} mid-sentence); "
          f"flagged {out['gate_flags']['stopped_at_cap']['flagged']}/{out['gate_flags']['stopped_at_cap']['rated']} "
          f"vs {out['gate_flags']['complete']['flagged']}/{out['gate_flags']['complete']['rated']}; "
          f"audited and cut: {audited_cut}")


if __name__ == "__main__":
    main()
