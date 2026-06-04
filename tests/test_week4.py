# ============================================================
# tests/test_week4.py
# Week 4 Tests — Semantic Matching + NLI Pipeline
#
# Run after: python run_week4.py
# Usage    : python -m pytest tests/test_week4.py -v
# ============================================================

import pytest
import os
import pandas as pd

# ── Path constants ────────────────────────────────────────
try:
    from config import HIDDEN_COND_DIR
except ImportError:
    HIDDEN_COND_DIR = os.path.join(
        os.path.dirname(__file__), '..', 'outputs',
        'hidden_conditions')

MATCHED_PAIRS_PATH    = os.path.join(
    HIDDEN_COND_DIR, "matched_pairs.csv")
NLI_RESULTS_PATH      = os.path.join(
    HIDDEN_COND_DIR, "nli_results.csv")
HIDDEN_CONDITIONS_CSV = os.path.join(
    HIDDEN_COND_DIR, "hidden_conditions.csv")
DETECTION_REPORT_PATH = os.path.join(
    HIDDEN_COND_DIR, "detection_report.txt")


# ── File existence tests ──────────────────────────────────

def test_matched_pairs_exists():
    assert os.path.exists(MATCHED_PAIRS_PATH), \
        f"matched_pairs.csv not found: {MATCHED_PAIRS_PATH}"

def test_nli_results_exists():
    assert os.path.exists(NLI_RESULTS_PATH), \
        f"nli_results.csv not found: {NLI_RESULTS_PATH}"

def test_hidden_conditions_exists():
    assert os.path.exists(HIDDEN_CONDITIONS_CSV), \
        f"hidden_conditions.csv not found: {HIDDEN_CONDITIONS_CSV}"

def test_detection_report_exists():
    assert os.path.exists(DETECTION_REPORT_PATH), \
        f"detection_report.txt not found: {DETECTION_REPORT_PATH}"


# ── Schema / content tests ────────────────────────────────

def test_matched_pairs_schema():
    """matched_pairs.csv must have required columns."""
    df = pd.read_csv(MATCHED_PAIRS_PATH)
    required = [
        'coverage_text', 'exclusion_text',
        'coverage_source', 'exclusion_source',
        'similarity_score', 'same_document'
    ]
    for col in required:
        assert col in df.columns, \
            f"Missing column in matched_pairs.csv: {col}"

def test_matched_pairs_not_empty():
    """Must have found at least one matched pair."""
    df = pd.read_csv(MATCHED_PAIRS_PATH)
    assert len(df) > 0, \
        "matched_pairs.csv is empty — no pairs found"

def test_matched_pairs_similarity_range():
    """All similarity scores must be between 0 and 1."""
    df = pd.read_csv(MATCHED_PAIRS_PATH)
    assert (df['similarity_score'] >= 0).all() and \
           (df['similarity_score'] <= 1).all(), \
        "Similarity scores out of range [0, 1]"

def test_matched_pairs_above_threshold():
    """All pairs must be above the similarity threshold."""
    try:
        from config import SIMILARITY_THRESHOLD
    except ImportError:
        SIMILARITY_THRESHOLD = 0.65
    df = pd.read_csv(MATCHED_PAIRS_PATH)
    below = (df['similarity_score'] < SIMILARITY_THRESHOLD).sum()
    assert below == 0, \
        f"{below} pairs below threshold {SIMILARITY_THRESHOLD}"

def test_nli_results_schema():
    """nli_results.csv must have NLI columns."""
    df = pd.read_csv(NLI_RESULTS_PATH)
    required = [
        'coverage_text', 'exclusion_text',
        'nli_verdict', 'contradiction_score',
        'is_contradiction', 'similarity_score'
    ]
    for col in required:
        assert col in df.columns, \
            f"Missing column in nli_results.csv: {col}"

def test_nli_verdicts_valid():
    """NLI verdicts must be one of the 3 valid labels."""
    df = pd.read_csv(NLI_RESULTS_PATH)
    valid = {'Contradiction', 'Neutral', 'Entailment'}
    invalid = set(df['nli_verdict'].unique()) - valid
    assert not invalid, \
        f"Invalid NLI verdicts found: {invalid}"

def test_nli_has_contradictions():
    """Pipeline must detect at least some contradictions."""
    df = pd.read_csv(NLI_RESULTS_PATH)
    contradictions = df['is_contradiction'].sum()
    assert contradictions > 0, \
        ("No contradictions detected. "
         "Check NLI model or lower similarity threshold.")

def test_hidden_conditions_schema():
    """hidden_conditions.csv must have required columns."""
    df = pd.read_csv(HIDDEN_CONDITIONS_CSV)
    required = [
        'detection_type', 'severity',
        'risk_reason', 'coverage_text'
    ]
    for col in required:
        assert col in df.columns, \
            f"Missing column in hidden_conditions.csv: {col}"

def test_hidden_conditions_severity_valid():
    """Severity must be High, Medium, or Low."""
    df = pd.read_csv(HIDDEN_CONDITIONS_CSV)
    valid = {'High', 'Medium', 'Low'}
    invalid = set(df['severity'].unique()) - valid
    assert not invalid, \
        f"Invalid severity values: {invalid}"

def test_detection_report_content():
    """Detection report must contain key sections."""
    with open(DETECTION_REPORT_PATH, encoding='utf-8') as f:
        content = f.read()
    required_sections = [
        'HIDDEN CONDITION DETECTION REPORT',
        'DETECTION SUMMARY',
        'Total hidden conditions',
        'NOTE FOR PAPER'
    ]
    for section in required_sections:
        assert section in content, \
            f"Detection report missing section: {section}"

def test_nli_scores_are_probabilities():
    """NLI scores must sum to approximately 1 per row."""
    df = pd.read_csv(NLI_RESULTS_PATH)
    total = (df['contradiction_score'] +
             df['neutral_score'] +
             df['entailment_score'])
    off = (abs(total - 1.0) > 0.05).sum()
    assert off == 0, \
        f"{off} rows have NLI scores that don't sum to ~1.0"
