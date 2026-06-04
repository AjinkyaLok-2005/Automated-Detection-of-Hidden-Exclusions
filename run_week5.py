# ============================================================
# run_week5.py
# Week 5 Entry Point — Risk Scoring Engine
#
# Usage:
#   # Score test.csv using Week 4 outputs (default)
#   python run_week5.py
#
#   # Score a specific PDF end-to-end
#   python run_week5.py --pdf path/to/policy.pdf
#
#   # Score all PDFs in a folder
#   python run_week5.py --folder data/raw_pdfs/Health\ insurance/
#
#   # Re-score using saved Week 4 CSV outputs
#   python run_week5.py --from-csv
#
# Outputs:
#   outputs/reports/risk_report_{name}_{timestamp}.txt
#   outputs/reports/risk_report_{name}_{timestamp}.json
#   outputs/reports/risk_summary.csv
# ============================================================

import argparse
import os
import sys
import time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TEST_PATH, HIDDEN_COND_DIR, REPORTS_DIR,
    LABEL_NAMES
)

MATCHED_PAIRS_PATH    = os.path.join(
    HIDDEN_COND_DIR, "matched_pairs.csv")
NLI_RESULTS_PATH      = os.path.join(
    HIDDEN_COND_DIR, "nli_results.csv")
HIDDEN_CONDITIONS_CSV = os.path.join(
    HIDDEN_COND_DIR, "hidden_conditions.csv")


def elapsed(start):
    s = int(time.time() - start)
    m, sec = divmod(s, 60)
    return f"{m}m {sec}s" if m else f"{sec}s"


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ── Loaders ───────────────────────────────────────────────

def load_clauses_from_csv(csv_path):
    """Load test.csv as classified clause list."""
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    clauses = []
    for _, row in df.iterrows():
        label_id = int(row['label'])
        clauses.append({
            'clause_text'    : str(row['clause_text']),
            'label_id'       : label_id,
            'label_name'     : LABEL_NAMES.get(label_id, '?'),
            'confidence'     : 1.0,
            'source_file'    : str(row.get('source_file', '')),
            'page_number'    : int(row.get('page_number', 0)),
            'section_heading': str(row.get('section_heading', '')),
        })
    return clauses


def load_nli_results():
    """Load nli_results.csv from Week 4 output."""
    if not os.path.exists(NLI_RESULTS_PATH):
        print(f"  WARNING: {NLI_RESULTS_PATH} not found.")
        print("  Run run_week4.py first to generate NLI results.")
        return pd.DataFrame()
    df = pd.read_csv(NLI_RESULTS_PATH, encoding='utf-8-sig')
    print(f"  NLI results loaded: {len(df)} pairs")
    return df


def load_hidden_conditions():
    """Load hidden_conditions.csv from Week 4 output."""
    if not os.path.exists(HIDDEN_CONDITIONS_CSV):
        print(f"  WARNING: {HIDDEN_CONDITIONS_CSV} not found.")
        return []
    df = pd.read_csv(HIDDEN_CONDITIONS_CSV, encoding='utf-8-sig')
    conditions = df.to_dict('records')
    print(f"  Hidden conditions loaded: {len(conditions)}")
    return conditions


# ── Single document scoring ───────────────────────────────

def score_single_document(classified_clauses,
                           hidden_conditions,
                           nli_results_df,
                           document_name):
    """Score one document and save its report."""
    from src.scoring.risk_scorer import run_scoring_pipeline
    score_result, report_paths = run_scoring_pipeline(
        classified_clauses,
        hidden_conditions=hidden_conditions,
        nli_results_df=nli_results_df,
        document_name=document_name,
        save=True
    )
    return score_result


# ── Multi-document scoring ────────────────────────────────

def score_by_source_file(classified_clauses,
                          hidden_conditions,
                          nli_results_df):
    """
    Break classified_clauses by source_file and score each
    document separately. Produces one report per PDF.
    """
    from src.scoring.risk_scorer import (
        run_scoring_pipeline, score_multiple_documents,
        save_risk_summary)

    # Group clauses by source file
    source_groups = {}
    for clause in classified_clauses:
        src = clause.get('source_file', 'unknown')
        source_groups.setdefault(src, []).append(clause)

    print(f"\n  Scoring {len(source_groups)} documents...")

    # Group hidden conditions by source
    hc_by_source = {}
    for hc in (hidden_conditions or []):
        src = (hc.get('coverage_source') or
               hc.get('exclusion_source') or 'unknown')
        hc_by_source.setdefault(src, []).append(hc)

    all_scores = []
    for source_file, clauses in source_groups.items():
        print(f"\n  [{source_file[:45]}]")
        hc_subset = hc_by_source.get(source_file, [])

        # Filter NLI results for this document
        nli_subset = pd.DataFrame()
        if nli_results_df is not None and not nli_results_df.empty:
            mask = (
                (nli_results_df['coverage_source'] == source_file) |
                (nli_results_df['exclusion_source'] == source_file)
            )
            nli_subset = nli_results_df[mask]

        score_result, _ = run_scoring_pipeline(
            clauses,
            hidden_conditions=hc_subset,
            nli_results_df=nli_subset,
            document_name=source_file,
            save=True
        )
        all_scores.append(score_result)

    # Aggregate summary
    summary_df = score_multiple_documents(all_scores)
    save_risk_summary(summary_df)

    return all_scores, summary_df


# ── Main ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Week 5: Risk Scoring Engine"
    )
    parser.add_argument(
        '--pdf', type=str, default=None,
        help='Score a specific PDF end-to-end'
    )
    parser.add_argument(
        '--folder', type=str, default=None,
        help='Score all PDFs in a folder'
    )
    parser.add_argument(
        '--from-csv', action='store_true',
        help='Re-score using existing Week 4 CSV outputs'
    )
    parser.add_argument(
        '--per-document', action='store_true',
        help='Score each source PDF separately'
    )
    args = parser.parse_args()

    total_start = time.time()
    header("WEEK 5: RISK SCORING ENGINE")

    # ── Load Week 4 outputs ─────────────────────────────────
    print("\n[1/3] Loading Week 4 outputs...")
    nli_results_df    = load_nli_results()
    hidden_conditions = load_hidden_conditions()

    # ── Get classified clauses ──────────────────────────────
    print("\n[2/3] Loading classified clauses...")

    if args.pdf:
        # Classify a new PDF using Legal-BERT
        if not os.path.exists(args.pdf):
            print(f"ERROR: PDF not found: {args.pdf}")
            sys.exit(1)
        from src.inference.nli_engine import classify_pdf
        classified_clauses = classify_pdf(args.pdf)
        document_name      = os.path.basename(args.pdf)

    elif args.folder:
        # Score all PDFs in a folder
        pdfs = [
            os.path.join(args.folder, f)
            for f in os.listdir(args.folder)
            if f.lower().endswith('.pdf')
        ]
        if not pdfs:
            print(f"No PDFs found in: {args.folder}")
            sys.exit(1)
        print(f"Found {len(pdfs)} PDFs in {args.folder}")
        all_clauses = []
        from src.inference.nli_engine import classify_pdf
        for pdf_path in pdfs:
            clauses = classify_pdf(pdf_path)
            all_clauses.extend(clauses)
        classified_clauses = all_clauses
        document_name      = os.path.basename(args.folder)

    else:
        # Default: use test.csv with ground-truth labels
        print(f"Loading test.csv: {TEST_PATH}")
        classified_clauses = load_clauses_from_csv(TEST_PATH)
        document_name      = "test.csv (ground truth)"

    print(f"  Total clauses: {len(classified_clauses)}")

    # ── Score ───────────────────────────────────────────────
    print("\n[3/3] Computing risk scores...")
    from src.scoring.risk_scorer import (
        score_multiple_documents, save_risk_summary)

    if args.per_document or args.folder:
        all_scores, summary_df = score_by_source_file(
            classified_clauses,
            hidden_conditions,
            nli_results_df
        )
    else:
        # Score as a single combined document
        score_result = score_single_document(
            classified_clauses,
            hidden_conditions,
            nli_results_df,
            document_name
        )
        all_scores  = [score_result]
        summary_df  = score_multiple_documents(all_scores)
        save_risk_summary(summary_df)

    # ── Final summary ───────────────────────────────────────
    header("WEEK 5 COMPLETE")
    print(f"  Total time        : {elapsed(total_start)}")
    print(f"  Documents scored  : {len(all_scores)}")
    print()

    if len(all_scores) == 1:
        r = all_scores[0]
        print(f"  Risk Score  : {r['risk_score']:.4f}")
        print(f"  Risk Level  : {r['risk_level']}")
        print(f"  Contradictions : {r['contradiction_count']}")
        print(f"  Hidden conditions: {r['hidden_conditions_total']}")
    else:
        print("  Risk Score Summary:")
        print(f"  {'Document':<40} {'Score':>7} {'Level'}")
        print("  " + "-" * 58)
        for _, row in summary_df.head(10).iterrows():
            name = str(row['document_name'])[:38]
            print(f"  {name:<40} "
                  f"{row['risk_score']:>7.4f}  "
                  f"{row['risk_level']}")

    print()
    print("  Outputs saved to: outputs/reports/")
    print(f"    risk_summary.csv")
    print(f"    risk_report_*.txt")
    print(f"    risk_report_*.json")


if __name__ == "__main__":
    main()
