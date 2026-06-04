# ============================================================
# src/scoring/risk_scorer.py
# Week 5 — Risk Scoring Engine
#
# Purpose:
#   Compute a normalised 0.0–1.0 risk score for an insurance
#   policy document by combining:
#     - Clause-level label weights
#     - NLI contradiction weight (highest — 1.0)
#     - Hidden condition severity multipliers
#     - Confidence-weighted scoring
#
# Risk Weights (from PROJECT_TRACKER Week 5):
#   Normal      = 0.1
#   Coverage    = 0.2
#   Condition   = 0.5
#   Exclusion   = 0.8
#   Contradiction = 1.0   ← NEW in Week 5
#
# Formula:
#   Risk Score = Sum(clause_weight × confidence) /
#                Max_possible_score  → normalised 0.0–1.0
#
# Outputs:
#   outputs/reports/{document}_risk_report.txt
#   outputs/reports/{document}_risk_report.json
#   outputs/reports/risk_summary.csv   (all documents)
# ============================================================

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime
from collections import Counter

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    RISK_WEIGHTS, RISK_LEVELS,
    LABEL_NAMES, HIDDEN_COND_DIR,
    REPORTS_DIR
)

# ── Risk weight constants ─────────────────────────────────
# From PROJECT_TRACKER Week 5 specification
CONTRADICTION_WEIGHT = 1.0   # highest risk signal
SEVERITY_MULTIPLIER  = {
    'High'  : 1.0,
    'Medium': 0.6,
    'Low'   : 0.3
}

# Output paths
RISK_SUMMARY_PATH = os.path.join(REPORTS_DIR, "risk_summary.csv")


# ── Core risk computation ─────────────────────────────────

def compute_clause_risk(classified_clauses):
    """
    Compute weighted risk contribution from all clauses.

    Each clause contributes:
      weight = RISK_WEIGHTS[label_id] × confidence

    Args:
        classified_clauses : list of clause dicts

    Returns:
        dict with raw_score, normalised_score,
              label_counts, weighted_sum, max_possible
    """
    if not classified_clauses:
        return {
            'raw_score'       : 0.0,
            'normalised_score': 0.0,
            'label_counts'    : {},
            'weighted_sum'    : 0.0,
            'max_possible'    : 0.0
        }

    weighted_sum  = 0.0
    max_possible  = 0.0
    label_counts  = Counter()

    for clause in classified_clauses:
        label_id   = clause.get('label_id', 0)
        confidence = clause.get('confidence', 1.0)
        base_weight = RISK_WEIGHTS.get(label_id, 0.1)

        weighted_sum += base_weight * confidence
        max_possible += RISK_WEIGHTS[2]  # max = Exclusion weight
        label_counts[LABEL_NAMES.get(label_id, '?')] += 1

    normalised = (weighted_sum / max_possible
                  if max_possible > 0 else 0.0)
    normalised = min(normalised, 1.0)

    return {
        'raw_score'       : round(weighted_sum, 4),
        'normalised_score': round(normalised, 4),
        'label_counts'    : dict(label_counts),
        'weighted_sum'    : round(weighted_sum, 4),
        'max_possible'    : round(max_possible, 4)
    }


def compute_contradiction_risk(nli_results_df):
    """
    Compute additional risk from NLI-detected contradictions.
    Contradictions carry weight 1.0 — highest in the system.

    Args:
        nli_results_df : DataFrame from nli_engine

    Returns:
        dict with contradiction_score, contradiction_count,
              high_conf_contradictions
    """
    if nli_results_df is None or nli_results_df.empty:
        return {
            'contradiction_score'      : 0.0,
            'contradiction_count'      : 0,
            'high_conf_contradictions' : 0,
            'avg_contradiction_conf'   : 0.0
        }

    contradictions = nli_results_df[
        nli_results_df['is_contradiction'] == True
    ]
    count      = len(contradictions)
    high_conf  = (contradictions['contradiction_score'] >= 0.80
                  ).sum() if count > 0 else 0
    avg_conf   = (contradictions['contradiction_score'].mean()
                  if count > 0 else 0.0)

    # Score: each contradiction contributes CONTRADICTION_WEIGHT
    # scaled by its confidence, normalised by clause count
    if count > 0:
        contra_weighted = (
            contradictions['contradiction_score'].sum() *
            CONTRADICTION_WEIGHT
        )
        # Normalise: cap at 1.0 when contradictions are numerous
        contra_score = min(contra_weighted / (count + 10), 1.0)
    else:
        contra_score = 0.0

    return {
        'contradiction_score'      : round(contra_score, 4),
        'contradiction_count'      : int(count),
        'high_conf_contradictions' : int(high_conf),
        'avg_contradiction_conf'   : round(float(avg_conf), 4)
    }


def compute_hidden_condition_risk(hidden_conditions):
    """
    Compute risk contribution from detected hidden conditions.

    Args:
        hidden_conditions : list from hidden_condition_detector

    Returns:
        dict with hidden_risk_score, counts by severity
    """
    if not hidden_conditions:
        return {
            'hidden_risk_score': 0.0,
            'high_count'       : 0,
            'medium_count'     : 0,
            'low_count'        : 0,
            'total_count'      : 0
        }

    high   = sum(1 for h in hidden_conditions
                 if h.get('severity') == 'High')
    medium = sum(1 for h in hidden_conditions
                 if h.get('severity') == 'Medium')
    low    = sum(1 for h in hidden_conditions
                 if h.get('severity') == 'Low')
    total  = len(hidden_conditions)

    # Weighted hidden risk
    hidden_weighted = (
        high   * SEVERITY_MULTIPLIER['High'] +
        medium * SEVERITY_MULTIPLIER['Medium'] +
        low    * SEVERITY_MULTIPLIER['Low']
    )
    # Normalise — cap grows with document size
    max_hidden = total * SEVERITY_MULTIPLIER['High']
    hidden_score = (hidden_weighted / max_hidden
                    if max_hidden > 0 else 0.0)
    hidden_score = min(hidden_score, 1.0)

    return {
        'hidden_risk_score': round(hidden_score, 4),
        'high_count'       : int(high),
        'medium_count'     : int(medium),
        'low_count'        : int(low),
        'total_count'      : int(total)
    }


def get_risk_level(risk_score):
    """Map numeric 0–1 risk score to named risk level."""
    for level, (low, high) in RISK_LEVELS.items():
        if low <= risk_score < high:
            return level
    return "Very High"


# ── Master scoring function ───────────────────────────────

def score_document(classified_clauses,
                   hidden_conditions=None,
                   nli_results_df=None,
                   document_name="Policy Document",
                   weights=None):
    """
    Compute the final composite risk score for one document.

    Combines three risk signals:
      1. Clause-level label risk   (weight: 0.40)
      2. Contradiction risk        (weight: 0.40)
      3. Hidden condition risk     (weight: 0.20)

    Args:
        classified_clauses : list of clause dicts
        hidden_conditions  : list from hidden_condition_detector
        nli_results_df     : DataFrame from nli_engine
        document_name      : name for reports
        weights            : dict with 'clause', 'contradiction',
                             'hidden' keys (default: 0.40/0.40/0.20)

    Returns:
        dict with all score components and final risk_score
    """
    # Default combination weights
    if weights is None:
        weights = {
            'clause'       : 0.40,
            'contradiction': 0.40,
            'hidden'       : 0.20
        }

    # Component scores
    clause_risk  = compute_clause_risk(classified_clauses)
    contra_risk  = compute_contradiction_risk(nli_results_df)
    hidden_risk  = compute_hidden_condition_risk(
        hidden_conditions or [])

    # Composite score
    final_score = (
        weights['clause']        * clause_risk['normalised_score'] +
        weights['contradiction'] * contra_risk['contradiction_score'] +
        weights['hidden']        * hidden_risk['hidden_risk_score']
    )
    final_score = round(min(final_score, 1.0), 4)
    risk_level  = get_risk_level(final_score)

    # Top exclusion clauses
    exclusions = sorted(
        [c for c in classified_clauses
         if c.get('label_id') == 2],
        key=lambda x: x.get('confidence', 0),
        reverse=True
    )[:10]

    result = {
        # Identity
        'document_name'            : document_name,
        'timestamp'                : datetime.now().strftime(
            '%Y-%m-%d %H:%M:%S'),
        'total_clauses'            : len(classified_clauses),

        # Final score
        'risk_score'               : final_score,
        'risk_level'               : risk_level,

        # Component scores
        'clause_risk_score'        : clause_risk['normalised_score'],
        'contradiction_risk_score' : contra_risk['contradiction_score'],
        'hidden_risk_score'        : hidden_risk['hidden_risk_score'],

        # Clause breakdown
        'label_distribution'       : clause_risk['label_counts'],
        'exclusion_count'          : clause_risk['label_counts'].get(
            'Exclusion', 0),
        'coverage_count'           : clause_risk['label_counts'].get(
            'Coverage', 0),

        # Contradiction details
        'contradiction_count'      : contra_risk['contradiction_count'],
        'high_conf_contradictions' : contra_risk['high_conf_contradictions'],
        'avg_contradiction_conf'   : contra_risk['avg_contradiction_conf'],

        # Hidden condition details
        'hidden_conditions_total'  : hidden_risk['total_count'],
        'hidden_high_severity'     : hidden_risk['high_count'],
        'hidden_medium_severity'   : hidden_risk['medium_count'],
        'hidden_low_severity'      : hidden_risk['low_count'],

        # Top exclusions for report
        'top_exclusions'           : [
            {
                'text'      : e['clause_text'][:300],
                'confidence': e.get('confidence', 0),
                'source'    : e.get('source_file', '')
            }
            for e in exclusions
        ]
    }

    return result


# ── Score multiple documents ──────────────────────────────

def score_multiple_documents(document_results):
    """
    Score a list of documents and return a comparison DataFrame.

    Args:
        document_results : list of dicts from score_document()

    Returns:
        DataFrame sorted by risk_score descending
    """
    rows = []
    for r in document_results:
        rows.append({
            'document_name'           : r['document_name'],
            'risk_score'              : r['risk_score'],
            'risk_level'              : r['risk_level'],
            'total_clauses'           : r['total_clauses'],
            'exclusion_count'         : r['exclusion_count'],
            'contradiction_count'     : r['contradiction_count'],
            'hidden_conditions_total' : r['hidden_conditions_total'],
            'hidden_high_severity'    : r['hidden_high_severity'],
            'clause_risk_score'       : r['clause_risk_score'],
            'contradiction_risk_score': r['contradiction_risk_score'],
            'hidden_risk_score'       : r['hidden_risk_score'],
        })

    df = pd.DataFrame(rows).sort_values(
        'risk_score', ascending=False
    ).reset_index(drop=True)

    return df


# ── Report generation ─────────────────────────────────────

def generate_risk_report(score_result, save_dir=None):
    """
    Generate and save a human-readable risk report (.txt)
    and machine-readable report (.json) for one document.

    Args:
        score_result : dict from score_document()
        save_dir     : directory to save reports (default: REPORTS_DIR)

    Returns:
        dict with report_path, json_path
    """
    if save_dir is None:
        save_dir = REPORTS_DIR
    os.makedirs(save_dir, exist_ok=True)

    doc_name   = score_result['document_name']
    safe_name  = (doc_name.replace('.pdf', '')
                           .replace(' ', '_')
                           .replace('/', '_')[:50])
    timestamp  = datetime.now().strftime('%Y%m%d_%H%M%S')

    risk_score = score_result['risk_score']
    risk_level = score_result['risk_level']

    # ── Risk bar visualisation ──────────────────────────────
    bar_filled = int(risk_score * 20)
    bar_empty  = 20 - bar_filled
    risk_bar   = f"[{'█' * bar_filled}{'░' * bar_empty}]"

    # ── Build report text ───────────────────────────────────
    lines = [
        "=" * 60,
        "INSURANCE POLICY RISK REPORT",
        "=" * 60,
        f"Document  : {doc_name}",
        f"Generated : {score_result['timestamp']}",
        f"Clauses   : {score_result['total_clauses']}",
        "",
        "RISK ASSESSMENT",
        "-" * 60,
        f"Risk Score : {risk_score:.4f}  {risk_bar}",
        f"Risk Level : {risk_level}",
        "",
        "SCORE BREAKDOWN",
        "-" * 60,
        f"  Clause-level risk      : "
        f"{score_result['clause_risk_score']:.4f}  "
        f"(weight 40%)",
        f"  Contradiction risk     : "
        f"{score_result['contradiction_risk_score']:.4f}  "
        f"(weight 40%)",
        f"  Hidden condition risk  : "
        f"{score_result['hidden_risk_score']:.4f}  "
        f"(weight 20%)",
        "",
        "CLAUSE DISTRIBUTION",
        "-" * 60,
    ]

    label_dist = score_result.get('label_distribution', {})
    total      = score_result['total_clauses']
    for label_name in ['Normal', 'Coverage',
                       'Exclusion', 'Condition']:
        count   = label_dist.get(label_name, 0)
        pct     = count / total * 100 if total > 0 else 0
        weight  = {
            'Normal': 0.1, 'Coverage': 0.2,
            'Exclusion': 0.8, 'Condition': 0.5
        }[label_name]
        lines.append(
            f"  {label_name:<12}: {count:>4} clauses "
            f"({pct:>5.1f}%)  risk weight={weight}"
        )

    lines += [
        "",
        "HIDDEN CONDITIONS & CONTRADICTIONS",
        "-" * 60,
        f"  NLI contradictions     : "
        f"{score_result['contradiction_count']}",
        f"  High-confidence (≥0.80): "
        f"{score_result['high_conf_contradictions']}",
        f"  Avg contradiction conf : "
        f"{score_result['avg_contradiction_conf']:.4f}",
        f"  Total hidden conditions: "
        f"{score_result['hidden_conditions_total']}",
        f"    High severity        : "
        f"{score_result['hidden_high_severity']}",
        f"    Medium severity      : "
        f"{score_result['hidden_medium_severity']}",
        f"    Low severity         : "
        f"{score_result['hidden_low_severity']}",
    ]

    # Top exclusion clauses
    top_excl = score_result.get('top_exclusions', [])
    if top_excl:
        lines += [
            "",
            "TOP EXCLUSION CLAUSES (highest confidence)",
            "-" * 60,
        ]
        for i, exc in enumerate(top_excl[:5], 1):
            text = exc['text']
            lines.append(
                f"[{i}] Confidence: {exc['confidence']:.3f}"
                f"  Source: {exc['source'][:30]}")
            lines.append(
                f"    {text[:160]}"
                f"{'...' if len(text) > 160 else ''}")

    lines += [
        "",
        "RISK SCALE",
        "-" * 60,
        "  0.0 – 0.3 : Low        — standard policy",
        "  0.3 – 0.6 : Medium     — notable exclusions",
        "  0.6 – 0.8 : High       — significant risk",
        "  0.8 – 1.0 : Very High  — extensive exclusions",
        "",
        "NOTE FOR PAPER:",
        "  Risk score combines clause-level weights,",
        "  NLI contradiction detection (weight=1.0),",
        "  and hidden condition severity scoring.",
        "  Formula: 0.40×clause + 0.40×contradiction",
        "           + 0.20×hidden_condition",
        "=" * 60,
    ]

    report_text = "\n".join(lines)

    # Save .txt
    report_path = os.path.join(
        save_dir, f"risk_report_{safe_name}_{timestamp}.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    # Save .json (for API use)
    json_result = {k: v for k, v in score_result.items()
                   if k != 'top_exclusions'}
    json_result['top_exclusions'] = [
        {'text': e['text'][:300],
         'confidence': e['confidence'],
         'source': e['source']}
        for e in top_excl
    ]

    json_path = os.path.join(
        save_dir, f"risk_report_{safe_name}_{timestamp}.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_result, f, indent=2)

    print(f"  Risk report saved : {report_path}")
    print(f"  JSON report saved : {json_path}")

    return {
        'report_path': report_path,
        'json_path'  : json_path,
        'report_text': report_text
    }


# ── Risk summary across documents ─────────────────────────

def save_risk_summary(summary_df, save_path=None):
    """
    Save the risk summary DataFrame to CSV.

    Args:
        summary_df : DataFrame from score_multiple_documents()
        save_path  : output path (default: RISK_SUMMARY_PATH)
    """
    if save_path is None:
        save_path = RISK_SUMMARY_PATH

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    summary_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"  Risk summary saved: {save_path}")
    return save_path


# ── Console output ────────────────────────────────────────

def print_risk_summary(score_result):
    """Print a concise risk summary to console."""
    doc   = score_result['document_name']
    score = score_result['risk_score']
    level = score_result['risk_level']
    bar_filled = int(score * 20)
    bar   = f"[{'█' * bar_filled}{'░' * (20-bar_filled)}]"

    print(f"\n{'='*60}")
    print(f"RISK SCORE: {score:.4f}  {bar}")
    print(f"RISK LEVEL: {level}")
    print(f"Document  : {doc}")
    print(f"{'='*60}")
    print(f"  Clause risk      : "
          f"{score_result['clause_risk_score']:.4f}")
    print(f"  Contradiction    : "
          f"{score_result['contradiction_risk_score']:.4f}"
          f"  ({score_result['contradiction_count']} found)")
    print(f"  Hidden cond.     : "
          f"{score_result['hidden_risk_score']:.4f}"
          f"  ({score_result['hidden_conditions_total']} found)")
    print(f"{'='*60}")


# ── Full Week 5 pipeline ──────────────────────────────────

def run_scoring_pipeline(classified_clauses,
                         hidden_conditions=None,
                         nli_results_df=None,
                         document_name="Policy Document",
                         save=True):
    """
    Full risk scoring pipeline for one document.

    Args:
        classified_clauses : list of clause dicts
        hidden_conditions  : list from hidden_condition_detector
        nli_results_df     : DataFrame from nli_engine
        document_name      : name for reports
        save               : save report files

    Returns:
        score_result dict, report_paths dict
    """
    print("=" * 60)
    print("WEEK 5 — RISK SCORING ENGINE")
    print("=" * 60)
    print(f"  Document : {document_name}")
    print(f"  Clauses  : {len(classified_clauses)}")

    if nli_results_df is not None:
        print(f"  NLI pairs: {len(nli_results_df)}")
    if hidden_conditions:
        print(f"  Hidden   : {len(hidden_conditions)}")

    # Compute score
    score_result = score_document(
        classified_clauses,
        hidden_conditions=hidden_conditions,
        nli_results_df=nli_results_df,
        document_name=document_name
    )

    # Print summary
    print_risk_summary(score_result)

    # Save reports
    report_paths = {}
    if save:
        report_paths = generate_risk_report(score_result)

    print("\nRisk scoring complete.")
    return score_result, report_paths
