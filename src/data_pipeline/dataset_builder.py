# ============================================================
# src/data_pipeline/dataset_builder.py
# Build final CSV dataset from labeled clauses
# ============================================================

import os
import sys
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DATASET_PATH, LABEL_NAMES, PROCESSED_DIR


def build_dataset(labeled_clauses, output_path=None):
    """
    Build and save insurance_clauses_final.csv from
    labeled clause dicts.

    Columns:
        clause_id, clause_text, section_heading,
        section_label, label, insurance_type,
        source_file, page_number

    Quality filters applied:
        - Remove clauses under 8 words
        - Remove clauses over 120 words
        - Remove exact duplicates

    Args:
        labeled_clauses : list of clause dicts from labeler
        output_path     : save path
                          (default: DATASET_PATH from config)

    Returns:
        DataFrame
    """
    if output_path is None:
        output_path = DATASET_PATH

    records = []
    for clause in labeled_clauses:
        records.append({
            "clause_id"      : clause.get('clause_id', 0),
            "clause_text"    : str(clause.get(
                'clause_text', '')).strip(),
            "section_heading": str(clause.get(
                'section_heading', '')),
            "section_label"  : str(clause.get(
                'section_label', '')),
            "label"          : int(clause.get('label', 0)),
            "insurance_type" : str(clause.get(
                'insurance_type', '')),
            "source_file"    : str(clause.get(
                'source_file', '')),
            "page_number"    : int(clause.get(
                'page_number', 0)),
        })

    df = pd.DataFrame(records)

    print(f"\nDataset before filtering: {len(df)}")

    # Quality filters
    df['_wc'] = df['clause_text'].str.split().str.len()
    df = df[df['_wc'] >= 8]
    df = df[df['_wc'] <= 120]
    df = df[df['clause_text'].str.len() >= 30]
    df = df.drop_duplicates(subset=['clause_text'])
    df = df.drop(columns=['_wc'])
    df = df.reset_index(drop=True)
    df['clause_id'] = range(1, len(df) + 1)

    print(f"Dataset after filtering : {len(df)}")

    # Label distribution
    print("\nFinal label distribution:")
    for label_id, name in LABEL_NAMES.items():
        cnt = (df['label'] == label_id).sum()
        pct = cnt / len(df) * 100 if len(df) > 0 else 0
        print(f"  {name:<12}: {cnt:>5}  ({pct:.1f}%)")

    print(f"\nUnique PDFs : {df['source_file'].nunique()}")

    # Save
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Saved: {output_path}")

    return df


def load_dataset(path=None):
    """
    Load the processed dataset CSV.

    Args:
        path : CSV path (default: DATASET_PATH)

    Returns:
        DataFrame
    """
    if path is None:
        path = DATASET_PATH

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            f"Run the data pipeline first: python main.py"
        )

    df = pd.read_csv(path, encoding='utf-8-sig')
    print(f"Loaded dataset: {len(df)} clauses "
          f"from {df['source_file'].nunique()} PDFs")
    return df
