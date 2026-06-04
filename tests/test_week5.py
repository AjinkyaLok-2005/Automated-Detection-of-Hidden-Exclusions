# ============================================================
# tests/test_week5.py
# Week 5 Tests — Risk Scoring Engine
#
# Run after: python run_week5.py
# Usage    : python -m pytest tests/test_week5.py -v
# ============================================================

import pytest
import os
import json
import pandas as pd

try:
    from config import REPORTS_DIR, HIDDEN_COND_DIR, RISK_LEVELS
except ImportError:
    REPORTS_DIR    = os.path.join('outputs', 'reports')
    HIDDEN_COND_DIR = os.path.join('outputs', 'hidden_conditions')
    RISK_LEVELS    = {
        'Low': (0.0, 0.3), 'Medium': (0.3, 0.6),
        'High': (0.6, 0.8), 'Very High': (0.8, 1.0)
    }

RISK_SUMMARY_PATH = os.path.join(REPORTS_DIR, "risk_summary.csv")


# ── Helper: find latest report files ─────────────────────

def get_latest_txt_report():
    """Find the most recently created .txt risk report."""
    if not os.path.exists(REPORTS_DIR):
        return None
    txts = [
        os.path.join(REPORTS_DIR, f)
        for f in os.listdir(REPORTS_DIR)
        if f.startswith('risk_report') and f.endswith('.txt')
    ]
    if not txts:
        return None
    return max(txts, key=os.path.getctime)


def get_latest_json_report():
    """Find the most recently created .json risk report."""
    if not os.path.exists(REPORTS_DIR):
        return None
    jsons = [
        os.path.join(REPORTS_DIR, f)
        for f in os.listdir(REPORTS_DIR)
        if f.startswith('risk_report') and f.endswith('.json')
    ]
    if not jsons:
        return None
    return max(jsons, key=os.path.getctime)


# ── File existence tests ──────────────────────────────────

def test_reports_dir_exists():
    assert os.path.exists(REPORTS_DIR), \
        f"Reports directory not found: {REPORTS_DIR}"

def test_risk_summary_exists():
    assert os.path.exists(RISK_SUMMARY_PATH), \
        f"risk_summary.csv not found: {RISK_SUMMARY_PATH}"

def test_txt_report_exists():
    report = get_latest_txt_report()
    assert report is not None, \
        f"No risk_report*.txt found in {REPORTS_DIR}"

def test_json_report_exists():
    report = get_latest_json_report()
    assert report is not None, \
        f"No risk_report*.json found in {REPORTS_DIR}"


# ── risk_summary.csv tests ────────────────────────────────

def test_risk_summary_schema():
    """risk_summary.csv must have required columns."""
    df = pd.read_csv(RISK_SUMMARY_PATH)
    required = [
        'document_name', 'risk_score', 'risk_level',
        'total_clauses', 'exclusion_count',
        'contradiction_count', 'hidden_conditions_total',
        'clause_risk_score', 'contradiction_risk_score',
        'hidden_risk_score'
    ]
    for col in required:
        assert col in df.columns, \
            f"Missing column in risk_summary.csv: {col}"

def test_risk_summary_not_empty():
    df = pd.read_csv(RISK_SUMMARY_PATH)
    assert len(df) > 0, "risk_summary.csv is empty"

def test_risk_scores_in_range():
    """All risk scores must be between 0.0 and 1.0."""
    df = pd.read_csv(RISK_SUMMARY_PATH)
    assert (df['risk_score'] >= 0.0).all() and \
           (df['risk_score'] <= 1.0).all(), \
        "Risk scores out of range [0.0, 1.0]"

def test_risk_levels_valid():
    """Risk levels must be one of the 4 valid levels."""
    df = pd.read_csv(RISK_SUMMARY_PATH)
    valid = set(RISK_LEVELS.keys())
    invalid = set(df['risk_level'].unique()) - valid
    assert not invalid, \
        f"Invalid risk levels in summary: {invalid}"

def test_component_scores_in_range():
    """All component scores must be between 0 and 1."""
    df = pd.read_csv(RISK_SUMMARY_PATH)
    for col in ['clause_risk_score',
                'contradiction_risk_score',
                'hidden_risk_score']:
        out = ((df[col] < 0) | (df[col] > 1)).sum()
        assert out == 0, \
            f"{col} has {out} values outside [0, 1]"

def test_risk_score_reflects_exclusions():
    """
    Documents with more exclusions should generally have
    higher clause risk scores than those with fewer.
    This is a sanity check on the weighting formula.
    """
    df = pd.read_csv(RISK_SUMMARY_PATH)
    if len(df) < 2:
        pytest.skip("Need at least 2 documents to compare")

    high_excl = df.nlargest(1, 'exclusion_count').iloc[0]
    low_excl  = df.nsmallest(1, 'exclusion_count').iloc[0]

    assert (high_excl['clause_risk_score'] >=
            low_excl['clause_risk_score']), \
        ("Document with most exclusions should have "
         "higher clause risk score")


# ── .txt report content tests ─────────────────────────────

def test_txt_report_content():
    """Text report must contain all required sections."""
    report = get_latest_txt_report()
    assert report is not None
    with open(report, encoding='utf-8') as f:
        content = f.read()

    required = [
        'INSURANCE POLICY RISK REPORT',
        'RISK ASSESSMENT',
        'Risk Score',
        'Risk Level',
        'SCORE BREAKDOWN',
        'Clause-level risk',
        'Contradiction risk',
        'Hidden condition risk',
        'CLAUSE DISTRIBUTION',
        'RISK SCALE',
        'NOTE FOR PAPER',
    ]
    for section in required:
        assert section in content, \
            f"Report missing section: {section}"

def test_txt_report_has_risk_bar():
    """Report must contain the visual risk bar."""
    report = get_latest_txt_report()
    with open(report, encoding='utf-8') as f:
        content = f.read()
    assert '█' in content or '░' in content, \
        "Risk bar visualisation missing from report"


# ── .json report tests ────────────────────────────────────

def test_json_report_valid():
    """JSON report must be valid JSON with required keys."""
    report = get_latest_json_report()
    assert report is not None
    with open(report, encoding='utf-8') as f:
        data = json.load(f)

    required = [
        'document_name', 'risk_score', 'risk_level',
        'total_clauses', 'contradiction_count',
        'hidden_conditions_total', 'clause_risk_score',
        'contradiction_risk_score', 'hidden_risk_score',
        'top_exclusions'
    ]
    for key in required:
        assert key in data, \
            f"JSON report missing key: {key}"

def test_json_risk_score_range():
    """JSON risk score must be 0.0–1.0."""
    report = get_latest_json_report()
    with open(report, encoding='utf-8') as f:
        data = json.load(f)
    score = data['risk_score']
    assert 0.0 <= score <= 1.0, \
        f"JSON risk score {score} outside [0.0, 1.0]"

def test_json_top_exclusions_structure():
    """top_exclusions in JSON must have text and confidence."""
    report = get_latest_json_report()
    with open(report, encoding='utf-8') as f:
        data = json.load(f)
    excl = data.get('top_exclusions', [])
    for e in excl:
        assert 'text' in e, \
            "top_exclusions item missing 'text'"
        assert 'confidence' in e, \
            "top_exclusions item missing 'confidence'"


# ── Risk scorer unit tests ────────────────────────────────

def test_risk_scorer_imports():
    """risk_scorer.py must import without errors."""
    try:
        from src.scoring.risk_scorer import (
            compute_clause_risk,
            compute_contradiction_risk,
            compute_hidden_condition_risk,
            score_document,
            get_risk_level
        )
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

def test_risk_scorer_score_document_basic():
    """score_document must return valid result with dummy data."""
    from src.scoring.risk_scorer import score_document

    dummy_clauses = [
        {'label_id': 0, 'confidence': 0.9,
         'clause_text': 'Normal clause', 'source_file': 'test.pdf'},
        {'label_id': 1, 'confidence': 0.8,
         'clause_text': 'Coverage clause', 'source_file': 'test.pdf'},
        {'label_id': 2, 'confidence': 0.95,
         'clause_text': 'Exclusion clause', 'source_file': 'test.pdf'},
        {'label_id': 3, 'confidence': 0.7,
         'clause_text': 'Condition clause', 'source_file': 'test.pdf'},
    ]

    result = score_document(
        dummy_clauses, document_name="unit_test")

    assert 'risk_score'  in result
    assert 'risk_level'  in result
    assert 0.0 <= result['risk_score'] <= 1.0
    assert result['risk_level'] in [
        'Low', 'Medium', 'High', 'Very High']
    assert result['total_clauses'] == 4

def test_get_risk_level_boundaries():
    """get_risk_level must correctly map score to level."""
    from src.scoring.risk_scorer import get_risk_level
    assert get_risk_level(0.0)  == 'Low'
    assert get_risk_level(0.15) == 'Low'
    assert get_risk_level(0.3)  == 'Medium'
    assert get_risk_level(0.5)  == 'Medium'
    assert get_risk_level(0.6)  == 'High'
    assert get_risk_level(0.75) == 'High'
    assert get_risk_level(0.8)  == 'Very High'
    assert get_risk_level(0.99) == 'Very High'
