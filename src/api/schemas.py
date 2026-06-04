# ============================================================
# src/api/schemas.py
# Week 6 — API Request / Response Schemas
# ============================================================

from pydantic import BaseModel, Field
from typing   import List, Optional, Dict, Any


# ── Clause schemas ────────────────────────────────────────

class ClauseResult(BaseModel):
    clause_text      : str
    label_id         : int
    label_name       : str
    confidence       : float
    risk_weight      : float
    is_contradiction : bool       = False
    contradiction_score : float   = 0.0
    section_heading  : str        = ""
    page_number      : int        = 0
    source_file      : str        = ""

    class Config:
        json_schema_extra = {
            "example": {
                "clause_text"     : "Pre-existing conditions "
                                    "are excluded.",
                "label_id"        : 2,
                "label_name"      : "Exclusion",
                "confidence"      : 0.94,
                "risk_weight"     : 0.8,
                "is_contradiction": True,
                "contradiction_score": 0.87,
                "page_number"     : 5,
                "source_file"     : "policy.pdf"
            }
        }


class HiddenCondition(BaseModel):
    detection_type       : str
    severity             : str       # High / Medium / Low
    risk_reason          : str
    coverage_text        : str       = ""
    exclusion_text       : str       = ""
    contradiction_score  : float     = 0.0
    similarity_score     : float     = 0.0
    same_document        : bool      = True


class RiskScoreBreakdown(BaseModel):
    clause_risk_score        : float
    contradiction_risk_score : float
    hidden_risk_score        : float
    clause_weight            : float  = 0.40
    contradiction_weight     : float  = 0.40
    hidden_weight            : float  = 0.20


# ── Main response schema ──────────────────────────────────

class AnalysisResponse(BaseModel):
    """
    Full analysis response returned by POST /analyze_policy.
    Contains everything needed by the frontend.
    """
    # Document identity
    filename          : str
    total_clauses     : int
    processing_time_s : float

    # Risk assessment
    risk_score        : float
    risk_level        : str          # Low/Medium/High/Very High
    risk_breakdown    : RiskScoreBreakdown

    # Clause breakdown counts
    label_distribution : Dict[str, int]
    exclusion_count    : int
    coverage_count     : int
    condition_count    : int
    normal_count       : int

    # NLI results
    contradiction_count       : int
    high_conf_contradictions  : int
    avg_contradiction_confidence : float

    # Hidden conditions
    hidden_conditions_total  : int
    hidden_high_severity     : int
    hidden_medium_severity   : int
    hidden_low_severity      : int

    # Clause details — grouped by label
    coverage_clauses         : List[ClauseResult]
    exclusion_clauses        : List[ClauseResult]
    condition_clauses        : List[ClauseResult]
    hidden_conditions        : List[HiddenCondition]

    # Output files
    highlighted_pdf_url      : Optional[str] = None
    report_txt_url           : Optional[str] = None
    report_json_url          : Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "filename"       : "health_policy.pdf",
                "total_clauses"  : 312,
                "risk_score"     : 0.6446,
                "risk_level"     : "High",
            }
        }


# ── Health check schema ───────────────────────────────────

class HealthResponse(BaseModel):
    status       : str
    model_loaded : bool
    version      : str = "1.0.0"
    message      : str = ""


# ── Error schema ──────────────────────────────────────────

class ErrorResponse(BaseModel):
    error   : str
    detail  : str = ""
    code    : int = 500
