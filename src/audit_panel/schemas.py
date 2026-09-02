"""
schemas.py — Pydantic request/response models for POST /v1/audit_panel.

The response shape mirrors exactly what selector.audit_panel() returns (spec §3),
so FastAPI validates the selector's dict on the way out.
"""

from typing import Dict, List, Optional

try:
    from typing import Literal
except ImportError:  # pragma: no cover
    from typing_extensions import Literal

from pydantic import BaseModel


class AuditRequest(BaseModel):
    incumbent_panel: List[str]                                   # >= 2 pooled model ids
    candidate_pool: List[str]
    benchmark: Literal["MedSimp-JudgeBench"] = "MedSimp-JudgeBench"  # only value accepted at v1
    bootstrap_iters: int = 1000
    seed: int = 42


class IncumbentSummary(BaseModel):
    panel: List[str]
    per_judge_sigma_R: Dict[str, float]
    panel_sigma_B_by_stratum: Dict[str, float]
    Phi_V_by_stratum: Dict[str, float]
    blindest_stratum: str


class RankedCandidate(BaseModel):
    model: str
    worst_stratum_delta_Phi_V: float
    mean_delta_Phi_V: float
    per_stratum_delta_Phi_V: Dict[str, float]
    per_stratum_delta_sigma_B: Dict[str, float]


class Recommendation(BaseModel):
    model: str
    target_blind_spot: str
    expected_Phi_V_lift: float
    ci_95: List[float]
    caveat: Optional[str] = None


class AuditResponse(BaseModel):
    benchmark: str
    incumbent: IncumbentSummary
    candidates_ranked: List[RankedCandidate]
    recommendation: Optional[Recommendation] = None
    unseen_candidates: List[str]
    note: str
