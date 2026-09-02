"""
pool_loader.py — Load the committed audit_pool into memory once, ready for VAGT.

Reads audit_pool/ground_truth.json + audit_pool/verdicts/*.json and builds the
merged per-item records vagt_core.stratum() consumes. The rater key for each model
IS its full model id (e.g. "meta-llama/Llama-3.3-70B-Instruct"), so a request's
model-id list maps straight to stratum() rater_keys with no renaming.

Join key is row_id (0..707) — idx is not unique. On load we assert every verdict
file has 708 rows aligned to ground_truth; a misaligned pool raises immediately
rather than silently producing wrong numbers.

Offline: pure JSON + dict work, no network, no key.
"""

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DEFAULT_POOL_DIR = _HERE.parents[1] / "audit_pool"


def _stratum_to_ce(stratum):
    """Reconstruct (condition, error_type) so vagt_core.stratum() works unchanged."""
    if stratum == "clean":
        return "clean", "none"
    return "corrupted", stratum


class Pool:
    """In-memory audit pool: ground truth + per-model verdicts, merged by row_id."""

    def __init__(self, records, models, provenance, ground_truth, benchmark):
        self.records = records          # list of {condition, error_type, "<model_id>": verdict, ...}
        self.models = set(models)       # set of model ids present in the pool
        self.provenance = provenance    # {model_id: prompt_provenance}
        self.ground_truth = ground_truth
        self.benchmark = benchmark

    @classmethod
    def load(cls, pool_dir=None):
        pool_dir = Path(pool_dir) if pool_dir else _DEFAULT_POOL_DIR
        gt = json.loads((pool_dir / "ground_truth.json").read_text(encoding="utf-8"))
        gt_rows = gt["rows"]
        n = gt["n"]
        benchmark = gt.get("benchmark", "MedSimp-JudgeBench")

        # base records keyed by row_id (condition/error_type from ground truth)
        base = {}
        for row in gt_rows:
            cond, etype = _stratum_to_ce(row["stratum"])
            base[row["row_id"]] = {"idx": row["idx"], "condition": cond, "error_type": etype}
        if len(base) != n:
            raise ValueError(f"ground_truth: {len(base)} unique row_ids != declared n={n}")

        models, provenance = [], {}
        verdict_dir = pool_dir / "verdicts"
        for path in sorted(verdict_dir.glob("*.json")):
            vf = json.loads(path.read_text(encoding="utf-8"))
            model = vf["model"]
            if vf["n"] != n or len(vf["verdicts"]) != n:
                raise ValueError(f"{path.name}: n={vf['n']}/{len(vf['verdicts'])} rows != ground_truth n={n}")
            for v in vf["verdicts"]:
                rid = v["row_id"]
                if rid not in base:
                    raise ValueError(f"{path.name}: row_id {rid} not in ground_truth")
                base[rid][model] = v["verdict"]
            models.append(model)
            provenance[model] = vf.get("prompt_provenance", "unknown")

        # every model must have a verdict on every row
        for model in models:
            missing = [rid for rid in base if model not in base[rid]]
            if missing:
                raise ValueError(f"{model}: missing verdicts for {len(missing)} rows")

        records = [base[rid] for rid in sorted(base)]
        return cls(records, models, provenance, gt_rows, benchmark)

    def known(self, ids):
        """Ids present in the pool, in the given order (deduped)."""
        seen, out = set(), []
        for m in ids:
            if m in self.models and m not in seen:
                out.append(m); seen.add(m)
        return out

    def unseen(self, ids):
        """Ids NOT in the pool (cannot be scored), in order (deduped)."""
        seen, out = set(), []
        for m in ids:
            if m not in self.models and m not in seen:
                out.append(m); seen.add(m)
        return out
