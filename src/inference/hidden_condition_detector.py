# ============================================================
# src/inference/hidden_condition_detector.py
# Week 4 — Hidden Condition Detection Engine
#
# Purpose:
#   Combine semantic matching + NLI to detect hidden risks:
#
#   Detection Rule (from PROJECT_TRACKER Week 5):
#     Coverage clause EXISTS
#     AND Exclusion on SAME TOPIC (similarity >= 0.65)
#     AND NLI verdict = Contradiction
#     → HIDDEN CONDITION FLAGGED
#
#   Also detects:
#     - Vague/broad exclusion language
#     - Nested conditions
#     - Low-confidence predictions (model uncertain)
#     - Hidden exclusions inside Normal/Coverage clauses
#
# Outputs:
#   hidden_conditions.csv  → all flagged clause pairs
#   detection_report.txt   → human-readable summary
# ============================================================

import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    HIDDEN_COND_DIR, HIDDEN_CONDITION_PHRASES,
    LABEL_NAMES, RISK_WEIGHTS
)

# Output paths
HIDDEN_CONDITIONS_CSV  = os.path.join(
    HIDDEN_COND_DIR, "hidden_conditions.csv")
DETECTION_REPORT_PATH  = os.path.join(
    HIDDEN_COND_DIR, "detection_report.txt")


# ── Rule 1: NLI-based contradiction detection ─────────────

def detect_from_nli_results(nli_results_df,
                             contradiction_threshold=0.5):
    """
    Flag pairs where NLI predicts Contradiction with high confidence.
    These are the most critical hidden conditions.

    Args:
        nli_results_df          : DataFrame from nli_engine
        contradiction_threshold : minimum contradiction score

    Returns:
        list of flagged condition dicts
    """
    flagged = []

    if nli_results_df.empty:
        return flagged

    contradictions = nli_results_df[
        (nli_results_df['is_contradiction'] == True) &
        (nli_results_df['contradiction_score'] >=
         contradiction_threshold)
    ]

    for _, row in contradictions.iterrows():
        severity = _score_to_severity(
            row['contradiction_score'])
        flagged.append({
            'detection_type'       : 'NLI_CONTRADICTION',
            'severity'             : severity,
            'coverage_text'        : row['coverage_text'],
            'exclusion_text'       : row['exclusion_text'],
            'coverage_source'      : row.get(
                'coverage_source', ''),
            'exclusion_source'     : row.get(
                'exclusion_source', ''),
            'same_document'        : row.get(
                'same_document', False),
            'similarity_score'     : row.get(
                'similarity_score', 0.0),
            'contradiction_score'  : row[
                'contradiction_score'],
            'risk_reason'          : (
                f"NLI model detects contradiction "
                f"(score={row['contradiction_score']:.3f}). "
                f"Coverage promise is directly contradicted "
                f"by exclusion clause on same topic."
            ),
        })

    return flagged


# ── Rule 2: Keyword-based hidden exclusion detection ──────

def detect_from_keywords(classified_clauses):
    """
    Flag Normal or Coverage clauses that contain
    exclusion/restriction keywords — these may be
    hiding exclusions in plain sight.

    Args:
        classified_clauses : list of clause dicts

    Returns:
        list of flagged condition dicts
    """
    flagged = []

    for clause in classified_clauses:
        text     = clause.get('clause_text', '').lower()
        label_id = clause.get('label_id', -1)
        flags    = []

        # Only check Normal and Coverage clauses
        if label_id not in [0, 1]:
            continue

        # Check for hidden exclusion phrases
        hits = [
            p for p in HIDDEN_CONDITION_PHRASES
            if p.lower() in text
        ]
        if hits:
            flags.append(
                f"Hidden restriction phrases found: "
                f"{hits[:3]}"
            )

        # Check for negation patterns
        negations = [
            'not covered', 'shall not', 'will not',
            'does not include', 'excluded', 'no coverage',
            'not payable', 'not applicable'
        ]
        neg_hits = [n for n in negations if n in text]
        if neg_hits and label_id == 1:  # Coverage clause
            flags.append(
                f"Negation language in Coverage clause: "
                f"{neg_hits[:2]}"
            )

        if flags:
            flagged.append({
                'detection_type'     : 'KEYWORD_HIDDEN',
                'severity'           : 'Medium',
                'coverage_text'      : clause.get(
                    'clause_text', ''),
                'exclusion_text'     : '',
                'coverage_source'    : clause.get(
                    'source_file', ''),
                'exclusion_source'   : '',
                'same_document'      : True,
                'similarity_score'   : 0.0,
                'contradiction_score': 0.0,
                'risk_reason'        : ' | '.join(flags),
            })

    return flagged


# ── Rule 3: Vague/broad exclusion detection ───────────────

def detect_vague_exclusions(classified_clauses):
    """
    Flag Exclusion clauses that use vague or overly broad
    language — these give the insurer maximum discretion
    to deny claims.

    Args:
        classified_clauses : list of clause dicts

    Returns:
        list of flagged condition dicts
    """
    flagged = []

    vague_patterns = [
        'any and all', 'whatsoever', 'howsoever',
        'including but not limited to', 'at our discretion',
        'as determined by', 'at the discretion of',
        'subject to change', 'may be modified',
        'without prior notice', 'in our sole judgment'
    ]

    for clause in classified_clauses:
        if clause.get('label_id') != 2:  # Only Exclusion
            continue

        text = clause.get('clause_text', '').lower()
        hits = [v for v in vague_patterns if v in text]

        if len(hits) >= 1:
            severity = 'High' if len(hits) >= 2 else 'Medium'
            flagged.append({
                'detection_type'     : 'VAGUE_EXCLUSION',
                'severity'           : severity,
                'coverage_text'      : '',
                'exclusion_text'     : clause.get(
                    'clause_text', ''),
                'coverage_source'    : '',
                'exclusion_source'   : clause.get(
                    'source_file', ''),
                'same_document'      : True,
                'similarity_score'   : 0.0,
                'contradiction_score': 0.0,
                'risk_reason'        : (
                    f"Broad/vague exclusion language: "
                    f"{hits[:3]}"
                ),
            })

    return flagged


# ── Rule 4: Low-confidence prediction flagging ───────────

def detect_uncertain_predictions(classified_clauses,
                                  confidence_threshold=0.55):
    """
    Flag clauses where the model was uncertain.
    Low confidence = ambiguous clause = manual review needed.

    Args:
        classified_clauses      : list of clause dicts
        confidence_threshold    : flag below this confidence

    Returns:
        list of flagged condition dicts
    """
    flagged = []

    for clause in classified_clauses:
        conf = clause.get('confidence', 1.0)
        if conf < confidence_threshold:
            flagged.append({
                'detection_type'     : 'LOW_CONFIDENCE',
                'severity'           : 'Low',
                'coverage_text'      : clause.get(
                    'clause_text', ''),
                'exclusion_text'     : '',
                'coverage_source'    : clause.get(
                    'source_file', ''),
                'exclusion_source'   : '',
                'same_document'      : True,
                'similarity_score'   : 0.0,
                'contradiction_score': 0.0,
                'risk_reason'        : (
                    f"Model uncertain about this clause "
                    f"(confidence={conf:.3f}). "
                    f"Manual review recommended."
                ),
            })

    return flagged


# ── Combine all detections ────────────────────────────────

def detect_hidden_conditions(classified_clauses,
                              nli_results_df=None,
                              include_keyword=True,
                              include_vague=True,
                              include_uncertain=False):
    """
    Master detection function — runs all detection rules
    and combines results into a single list.

    Args:
        classified_clauses : list of clause dicts
        nli_results_df     : DataFrame from nli_engine
                             (None = skip NLI detection)
        include_keyword    : run keyword detection
        include_vague      : run vague exclusion detection
        include_uncertain  : run low-confidence detection

    Returns:
        list of hidden condition dicts, sorted by severity
    """
    all_flagged = []

    # Rule 1 — NLI contradiction (highest priority)
    if nli_results_df is not None and not nli_results_df.empty:
        nli_flags = detect_from_nli_results(nli_results_df)
        print(f"  NLI contradictions    : {len(nli_flags)}")
        all_flagged.extend(nli_flags)

    # Rule 2 — Hidden exclusion keywords
    if include_keyword and classified_clauses:
        kw_flags = detect_from_keywords(classified_clauses)
        print(f"  Keyword detections    : {len(kw_flags)}")
        all_flagged.extend(kw_flags)

    # Rule 3 — Vague/broad exclusion language
    if include_vague and classified_clauses:
        vague_flags = detect_vague_exclusions(
            classified_clauses)
        print(f"  Vague exclusions      : {len(vague_flags)}")
        all_flagged.extend(vague_flags)

    # Rule 4 — Uncertain predictions
    if include_uncertain and classified_clauses:
        unc_flags = detect_uncertain_predictions(
            classified_clauses)
        print(f"  Uncertain predictions : {len(unc_flags)}")
        all_flagged.extend(unc_flags)

    # Sort by severity
    severity_order = {'High': 0, 'Medium': 1, 'Low': 2}
    all_flagged.sort(
        key=lambda x: severity_order.get(
            x.get('severity', 'Low'), 3))

    print(f"\n  Total hidden conditions: {len(all_flagged)}")
    return all_flagged


# ── Save hidden conditions ────────────────────────────────

def save_hidden_conditions(hidden_conditions,
                           save_path=None):
    """
    Save hidden conditions list to CSV.

    Args:
        hidden_conditions : list from detect_hidden_conditions()
        save_path         : output path

    Returns:
        DataFrame
    """
    if save_path is None:
        save_path = HIDDEN_CONDITIONS_CSV

    if not hidden_conditions:
        print("  No hidden conditions to save.")
        return pd.DataFrame()

    df = pd.DataFrame(hidden_conditions)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"  Hidden conditions saved: {save_path}")
    return df


# ── Detection report ──────────────────────────────────────

def save_detection_report(hidden_conditions,
                          classified_clauses,
                          source_name="Policy Document",
                          save_path=None):
    """
    Generate and save a human-readable detection report.

    Args:
        hidden_conditions  : list from detect_hidden_conditions()
        classified_clauses : original classified clauses
        source_name        : document name for report header
        save_path          : output .txt path
    """
    if save_path is None:
        save_path = DETECTION_REPORT_PATH

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    total     = len(classified_clauses)
    high      = sum(1 for h in hidden_conditions
                    if h.get('severity') == 'High')
    medium    = sum(1 for h in hidden_conditions
                    if h.get('severity') == 'Medium')
    low       = sum(1 for h in hidden_conditions
                    if h.get('severity') == 'Low')

    lines = [
        "=" * 60,
        "HIDDEN CONDITION DETECTION REPORT",
        "=" * 60,
        f"Document  : {source_name}",
        f"Generated : {timestamp}",
        f"Clauses   : {total} classified",
        "",
        "DETECTION SUMMARY",
        "-" * 60,
        f"Total hidden conditions : {len(hidden_conditions)}",
        f"  High severity         : {high}",
        f"  Medium severity       : {medium}",
        f"  Low severity          : {low}",
        "",
    ]

    # Group by detection type
    type_groups = {}
    for hc in hidden_conditions:
        dt = hc.get('detection_type', 'UNKNOWN')
        type_groups.setdefault(dt, []).append(hc)

    type_labels = {
        'NLI_CONTRADICTION': 'NLI Contradiction Pairs',
        'KEYWORD_HIDDEN'   : 'Hidden Exclusion Keywords',
        'VAGUE_EXCLUSION'  : 'Vague/Broad Exclusions',
        'LOW_CONFIDENCE'   : 'Uncertain Predictions',
    }

    for dtype, items in type_groups.items():
        label = type_labels.get(dtype, dtype)
        lines += [
            f"{label.upper()} ({len(items)} found)",
            "-" * 60,
        ]
        for i, hc in enumerate(items[:5], 1):
            lines.append(
                f"[{i}] Severity: {hc.get('severity','?')}")
            lines.append(
                f"    Reason: {hc.get('risk_reason','')}")
            cov = hc.get('coverage_text', '')
            exc = hc.get('exclusion_text', '')
            if cov:
                lines.append(
                    f"    Coverage : "
                    f"{cov[:120]}{'...' if len(cov)>120 else ''}")
            if exc:
                lines.append(
                    f"    Exclusion: "
                    f"{exc[:120]}{'...' if len(exc)>120 else ''}")
            lines.append("")

        if len(items) > 5:
            lines.append(
                f"    ... and {len(items)-5} more. "
                f"See hidden_conditions.csv")
            lines.append("")

    lines += [
        "NOTE FOR PAPER:",
        "  Detection uses three-stage pipeline:",
        "  Stage 1: Semantic similarity matching",
        "           (sentence-transformers/all-MiniLM-L6-v2)",
        "  Stage 2: NLI contradiction detection",
        "           (cross-encoder/nli-roberta-base)",
        "  Stage 3: Rule-based vague language detection",
        "=" * 60,
    ]

    report_text = "\n".join(lines)

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"  Detection report saved: {save_path}")
    return report_text


# ── Severity helper ───────────────────────────────────────

def _score_to_severity(contradiction_score):
    """Map contradiction score to severity label."""
    if contradiction_score >= 0.80:
        return 'High'
    elif contradiction_score >= 0.60:
        return 'Medium'
    else:
        return 'Low'


# ── Summarise hidden conditions ───────────────────────────

def summarize_hidden_conditions(hidden_conditions):
    """Print a readable summary to console."""
    if not hidden_conditions:
        print("No hidden conditions detected.")
        return

    print(f"\n{'='*60}")
    print("HIDDEN CONDITIONS SUMMARY")
    print(f"{'='*60}")
    print(f"Total detected: {len(hidden_conditions)}")

    severity_counts = {}
    for hc in hidden_conditions:
        s = hc.get('severity', 'Low')
        severity_counts[s] = severity_counts.get(s, 0) + 1

    for sev in ['High', 'Medium', 'Low']:
        count = severity_counts.get(sev, 0)
        if count:
            print(f"  {sev:<8}: {count}")

    print(f"\nTop findings:")
    for i, hc in enumerate(hidden_conditions[:5], 1):
        print(f"\n[{i}] {hc['detection_type']}"
              f" | Severity: {hc.get('severity','?')}")
        print(f"    {hc.get('risk_reason','')[:120]}")
        cov = hc.get('coverage_text', '')
        exc = hc.get('exclusion_text', '')
        if cov:
            print(f"    Coverage : "
                  f"{cov[:100]}{'...' if len(cov)>100 else ''}")
        if exc:
            print(f"    Exclusion: "
                  f"{exc[:100]}{'...' if len(exc)>100 else ''}")

    print(f"\n{'='*60}")


# ── Full detection pipeline ───────────────────────────────

def run_detection_pipeline(classified_clauses,
                           nli_results_df=None,
                           source_name="Policy Document",
                           save=True):
    """
    Full hidden condition detection pipeline.

    Args:
        classified_clauses : list of clause dicts
        nli_results_df     : DataFrame from nli_engine
        source_name        : document name for reports
        save               : save CSV and report

    Returns:
        hidden_conditions list, hidden_df DataFrame
    """
    print("=" * 60)
    print("WEEK 4 — HIDDEN CONDITION DETECTION")
    print("=" * 60)
    print(f"  Document : {source_name}")
    print(f"  Clauses  : {len(classified_clauses)}")
    print()

    hidden_conditions = detect_hidden_conditions(
        classified_clauses,
        nli_results_df=nli_results_df,
        include_keyword=True,
        include_vague=True,
        include_uncertain=False
    )

    summarize_hidden_conditions(hidden_conditions)

    hidden_df = pd.DataFrame()
    if save and hidden_conditions:
        hidden_df = save_hidden_conditions(hidden_conditions)
        save_detection_report(
            hidden_conditions,
            classified_clauses,
            source_name=source_name
        )

    return hidden_conditions, hidden_df
