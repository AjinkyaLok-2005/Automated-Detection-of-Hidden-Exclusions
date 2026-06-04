# ============================================================
# run_week4.py
# Week 4 Entry Point — Semantic Matching + NLI Pipeline
#
# Usage:
#   # Run on test.csv (default — uses already-classified data)
#   python run_week4.py
#
#   # Run on a specific PDF
#   python run_week4.py --pdf path/to/policy.pdf
#
#   # Run matching only, skip NLI (faster)
#   python run_week4.py --skip-nli
#
#   # Only match within same document
#   python run_week4.py --same-doc
#
# Outputs:
#   outputs/hidden_conditions/matched_pairs.csv
#   outputs/hidden_conditions/nli_results.csv
#   outputs/hidden_conditions/hidden_conditions.csv
#   outputs/hidden_conditions/detection_report.txt
# ============================================================

import argparse
import os
import sys
import time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TEST_PATH, BERT_MODEL_DIR,
    HIDDEN_COND_DIR, LABEL_NAMES
)


def elapsed(start):
    s = int(time.time() - start)
    m, sec = divmod(s, 60)
    return f"{m}m {sec}s" if m else f"{sec}s"


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def load_classified_from_csv(csv_path):
    """
    Load test.csv and convert to list of clause dicts.
    Uses ground-truth labels from CSV as the classification.
    """
    print(f"Loading classified data: {csv_path}")
    df = pd.read_csv(csv_path, encoding='utf-8-sig')
    print(f"Loaded {len(df)} clauses")

    clauses = []
    for _, row in df.iterrows():
        label_id = int(row['label'])
        clauses.append({
            'clause_text'   : str(row['clause_text']),
            'label_id'      : label_id,
            'label_name'    : LABEL_NAMES.get(label_id, '?'),
            'confidence'    : 1.0,  # ground truth
            'source_file'   : str(row.get('source_file', '')),
            'page_number'   : int(row.get('page_number', 0)),
            'section_heading': str(row.get(
                'section_heading', '')),
        })

    # Print distribution
    from collections import Counter
    dist = Counter(c['label_name'] for c in clauses)
    print("Label distribution:")
    for label, count in sorted(dist.items()):
        print(f"  {label:<12}: {count:>5}")

    return clauses


def classify_from_pdf(pdf_path):
    """
    Classify a new PDF using fine-tuned Legal-BERT.
    """
    if not os.path.exists(BERT_MODEL_DIR):
        print(f"ERROR: No trained model at {BERT_MODEL_DIR}")
        print("Run Week 3 training first.")
        sys.exit(1)

    from src.inference.nli_engine import classify_pdf
    return classify_pdf(pdf_path)


def main():
    parser = argparse.ArgumentParser(
        description="Week 4: Semantic Matching + NLI Pipeline"
    )
    parser.add_argument(
        '--pdf', type=str, default=None,
        help='Path to a new insurance PDF to analyse'
    )
    parser.add_argument(
        '--skip-nli', action='store_true',
        help='Skip NLI step (run matching only)'
    )
    parser.add_argument(
        '--same-doc', action='store_true',
        help='Only match pairs within the same document'
    )
    parser.add_argument(
        '--threshold', type=float, default=None,
        help='Cosine similarity threshold (default from config)'
    )
    args = parser.parse_args()

    total_start = time.time()
    header("WEEK 4: SEMANTIC MATCHING + NLI PIPELINE")

    # ── Step 1: Get classified clauses ─────────────────────
    print("\n[1/4] Loading classified clauses...")
    if args.pdf:
        if not os.path.exists(args.pdf):
            print(f"ERROR: PDF not found: {args.pdf}")
            sys.exit(1)
        classified_clauses = classify_from_pdf(args.pdf)
        source_name = os.path.basename(args.pdf)
    else:
        print("No --pdf specified. Using test.csv with ground-truth labels.")
        classified_clauses = load_classified_from_csv(TEST_PATH)
        source_name = "test.csv (ground truth)"

    print(f"  Total clauses: {len(classified_clauses)}")

    # ── Step 2: Semantic matching ───────────────────────────
    print("\n[2/4] Running semantic matching...")
    from src.inference.semantic_matcher import (
        run_semantic_matching)

    pairs_df, sent_model = run_semantic_matching(
        classified_clauses,
        save=True,
        same_doc_only=args.same_doc
    )

    if pairs_df.empty:
        print("\nNo matched pairs found.")
        print("Try lowering --threshold or adding more clauses.")
        sys.exit(0)

    # ── Step 3: NLI contradiction detection ────────────────
    nli_results_df = pd.DataFrame()

    if not args.skip_nli:
        print("\n[3/4] Running NLI contradiction detection...")
        from src.inference.nli_engine import run_nli_pipeline

        nli_results_df, _ = run_nli_pipeline(
            pairs_df, save=True)
    else:
        print("\n[3/4] NLI skipped (--skip-nli flag set).")

    # ── Step 4: Hidden condition detection ─────────────────
    print("\n[4/4] Detecting hidden conditions...")
    from src.inference.hidden_condition_detector import (
        run_detection_pipeline)

    nli_input = (nli_results_df
                 if not nli_results_df.empty else None)

    hidden_conditions, hidden_df = run_detection_pipeline(
        classified_clauses,
        nli_results_df=nli_input,
        source_name=source_name,
        save=True
    )

    # ── Final summary ───────────────────────────────────────
    header("WEEK 4 COMPLETE")
    print(f"  Total time           : {elapsed(total_start)}")
    print(f"  Clauses analysed     : {len(classified_clauses)}")
    print(f"  Matched pairs        : {len(pairs_df)}")

    if not nli_results_df.empty:
        contras = nli_results_df['is_contradiction'].sum()
        print(f"  Contradictions found : {contras}")

    print(f"  Hidden conditions    : {len(hidden_conditions)}")
    print()
    print("  Outputs:")
    print(f"    {HIDDEN_COND_DIR}/matched_pairs.csv")
    print(f"    {HIDDEN_COND_DIR}/nli_results.csv")
    print(f"    {HIDDEN_COND_DIR}/hidden_conditions.csv")
    print(f"    {HIDDEN_COND_DIR}/detection_report.txt")


if __name__ == "__main__":
    main()
