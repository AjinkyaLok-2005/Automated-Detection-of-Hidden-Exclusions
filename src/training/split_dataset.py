# ============================================
# src/training/split_dataset.py
# Train/Test Split Pipeline — PDF-wise split
# Updated for new multi-type insurance dataset
# ============================================

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn.model_selection import train_test_split

# Ensure project root is on path so config.py can be found
sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    DATASET_PATH, TRAIN_PATH, TEST_PATH,
    SPLITS_DIR, CHARTS_DIR,
    LABEL_NAMES, TEST_SIZE, RANDOM_SEED
)


# ─────────────────────────────────────────────
# Function 1: load_and_analyze
# ─────────────────────────────────────────────
def load_and_analyze(dataset_path):
    """Load dataset CSV and print analysis summary."""
    df = pd.read_csv(dataset_path, encoding='utf-8-sig')

    total_clauses = len(df)
    unique_pdfs   = df['source_file'].nunique()

    print("=" * 50)
    print("DATASET ANALYSIS BEFORE SPLIT")
    print("=" * 50)
    print(f"  Total clauses         : {total_clauses}")
    print(f"  Total unique PDFs     : {unique_pdfs}")
    print()
    print("  Insurance Type Distribution:")
    for itype, count in df['insurance_type'].value_counts().items():
        pct = count / total_clauses * 100
        pdfs = df[df['insurance_type'] == itype]['source_file'].nunique()
        print(f"    {itype:<20}: {count:>5} clauses ({pct:>5.1f}%)  |  {pdfs} PDFs")
    print()
    print("  Label Distribution:")
    for label_int, label_name in LABEL_NAMES.items():
        count = (df['label'] == label_int).sum()
        pct   = count / total_clauses * 100
        print(f"    Label {label_int} {label_name:<10}: {count:>5}  ({pct:>5.1f}%)")
    print()
    print("  Clauses per PDF (top 10):")
    clauses_per_pdf = (
        df.groupby('source_file')
          .size()
          .sort_values(ascending=False)
    )
    for filename, count in list(clauses_per_pdf.items())[:10]:
        print(f"    {count:>4} | {filename}")
    if len(clauses_per_pdf) > 10:
        print(f"    ... and {len(clauses_per_pdf) - 10} more PDFs")
    print("=" * 50)

    return df


# ─────────────────────────────────────────────
# Function 2: build_pdf_summary
# ─────────────────────────────────────────────
def build_pdf_summary(df):
    """Build one-row-per-PDF summary with label counts and dominant label."""
    records = []
    for source_file, group in df.groupby('source_file'):
        insurance_type = group['insurance_type'].iloc[0]
        clause_count   = len(group)
        label_counts   = [
            (group['label'] == i).sum() for i in range(4)
        ]
        dominant_label = int(np.argmax(label_counts))
        records.append({
            'source_file'   : source_file,
            'insurance_type': insurance_type,
            'clause_count'  : clause_count,
            'label_0_count' : label_counts[0],
            'label_1_count' : label_counts[1],
            'label_2_count' : label_counts[2],
            'label_3_count' : label_counts[3],
            'dominant_label': dominant_label,
        })

    pdf_summary = pd.DataFrame(records)
    return pdf_summary


# ─────────────────────────────────────────────
# Function 3: perform_split
# ─────────────────────────────────────────────
def perform_split(pdf_summary):
    """Split PDF filenames into train/test using stratified split."""
    pdf_summary = pdf_summary.copy()

    # Stratify on insurance_type + dominant_label
    pdf_summary['stratify_key'] = (
        pdf_summary['insurance_type'] + '_' +
        pdf_summary['dominant_label'].astype(str)
    )

    # Drop strata with only 1 member (can't split)
    strata_counts = pdf_summary['stratify_key'].value_counts()
    singleton_strata = strata_counts[strata_counts < 2].index.tolist()
    if singleton_strata:
        print(f"  NOTE: {len(singleton_strata)} singleton strata merged to insurance_type only")
        pdf_summary.loc[
            pdf_summary['stratify_key'].isin(singleton_strata), 'stratify_key'
        ] = pdf_summary.loc[
            pdf_summary['stratify_key'].isin(singleton_strata), 'insurance_type'
        ]

    try:
        train_pdfs, test_pdfs = train_test_split(
            pdf_summary['source_file'].values,
            test_size=TEST_SIZE,
            random_state=RANDOM_SEED,
            stratify=pdf_summary['stratify_key'].values
        )
        print("  Split method: Stratified on insurance_type + dominant_label")
    except ValueError as e:
        print(f"  WARNING: Full stratification failed ({e}), falling back to insurance_type only")
        train_pdfs, test_pdfs = train_test_split(
            pdf_summary['source_file'].values,
            test_size=TEST_SIZE,
            random_state=RANDOM_SEED,
            stratify=pdf_summary['insurance_type'].values
        )
        print("  Split method: Stratified on insurance_type only")

    return list(train_pdfs), list(test_pdfs)


# ─────────────────────────────────────────────
# Function 4: build_split_dataframes
# ─────────────────────────────────────────────
def build_split_dataframes(df, train_pdfs, test_pdfs):
    """Filter full dataframe into train and test subsets by PDF."""
    train_df = df[df['source_file'].isin(train_pdfs)].copy().reset_index(drop=True)
    test_df  = df[df['source_file'].isin(test_pdfs)].copy().reset_index(drop=True)
    return train_df, test_df


# ─────────────────────────────────────────────
# Function 5: validate_split
# ─────────────────────────────────────────────
def validate_split(df, train_df, test_df):
    """Run quality checks on the split. Returns True if all critical checks pass."""
    all_insurance_types = set(df['insurance_type'].unique())

    print()
    print("=" * 50)
    print("SPLIT VALIDATION")
    print("=" * 50)

    all_passed = True

    # CHECK 1 — Zero data leakage (CRITICAL)
    train_set = set(train_df['source_file'].unique())
    test_set  = set(test_df['source_file'].unique())
    overlap   = train_set & test_set
    if overlap:
        print(f"  CRITICAL ERROR: Data leakage! Overlapping PDFs: {overlap}")
        all_passed = False
    else:
        print("  CHECK 1 PASSED: Zero data leakage")

    # CHECK 2 — All 4 labels in train (CRITICAL)
    train_labels = set(train_df['label'].unique())
    if not {0, 1, 2, 3}.issubset(train_labels):
        missing = {0, 1, 2, 3} - train_labels
        print(f"  CRITICAL ERROR: Train missing labels: {missing}")
        all_passed = False
    else:
        print("  CHECK 2 PASSED: All labels in train")

    # CHECK 3 — All 4 labels in test (CRITICAL)
    test_labels = set(test_df['label'].unique())
    if not {0, 1, 2, 3}.issubset(test_labels):
        missing = {0, 1, 2, 3} - test_labels
        print(f"  CRITICAL ERROR: Test missing labels: {missing}")
        all_passed = False
    else:
        print("  CHECK 3 PASSED: All labels in test")

    # CHECK 4 — All insurance types in test (WARNING)
    test_types = set(test_df['insurance_type'].unique())
    if not all_insurance_types.issubset(test_types):
        missing = all_insurance_types - test_types
        print(f"  WARNING: Test missing insurance type(s): {missing}")
    else:
        print(f"  CHECK 4 PASSED: All {len(all_insurance_types)} insurance types in test")

    # CHECK 5 — Test size between 15% and 25% (WARNING)
    test_pct = len(test_df) / len(df) * 100
    if not (15 <= test_pct <= 25):
        print(f"  WARNING: Test is {test_pct:.1f}% (expected 15–25%)")
    else:
        print(f"  CHECK 5 PASSED: Test is {test_pct:.1f}%")

    print("=" * 50)
    return all_passed


# ─────────────────────────────────────────────
# Function 6: save_split_files
# ─────────────────────────────────────────────
def save_split_files(train_df, test_df, train_pdfs, test_pdfs):
    """Save train.csv and test.csv to PROCESSED_DIR (via TRAIN_PATH/TEST_PATH),
    and train_files.txt / test_files.txt to SPLITS_DIR — as defined in config.py."""
    train_df.to_csv(TRAIN_PATH, index=False, encoding='utf-8-sig')
    print(f"  Train saved : {TRAIN_PATH}")

    test_df.to_csv(TEST_PATH, index=False, encoding='utf-8-sig')
    print(f"  Test saved  : {TEST_PATH}")

    train_files_path = os.path.join(SPLITS_DIR, "train_files.txt")
    with open(train_files_path, 'w', encoding='utf-8') as f:
        for pdf in sorted(train_pdfs):
            count = (train_df['source_file'] == pdf).sum()
            f.write(f"{pdf} ({count} clauses)\n")
    print(f"  Train list  : {train_files_path}")

    test_files_path = os.path.join(SPLITS_DIR, "test_files.txt")
    with open(test_files_path, 'w', encoding='utf-8') as f:
        for pdf in sorted(test_pdfs):
            count = (test_df['source_file'] == pdf).sum()
            f.write(f"{pdf} ({count} clauses)\n")
    print(f"  Test list   : {test_files_path}")


# ─────────────────────────────────────────────
# Function 7: generate_charts
# ─────────────────────────────────────────────
def generate_charts(train_df, test_df, insurance_types):
    """Generate and save charts for the split analysis."""

    LABEL_COLORS = {
        0: '#95a5a6',
        1: '#27ae60',
        2: '#e74c3c',
        3: '#f39c12',
    }
    TRAIN_COLOR = '#2980b9'
    TEST_COLOR  = '#e67e22'

    label_list  = [0, 1, 2, 3]
    label_names = [LABEL_NAMES[i] for i in label_list]

    # ── CHART 1: Label distribution — Train ──
    train_counts = [int((train_df['label'] == i).sum()) for i in label_list]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(label_names, train_counts,
                  color=[LABEL_COLORS[i] for i in label_list], edgecolor='white')
    for bar, count in zip(bars, train_counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(train_counts) * 0.01,
                str(count), ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_title("Label Distribution — Train Set", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("Label"); ax.set_ylabel("Clause Count")
    ax.set_ylim(0, max(train_counts) * 1.15)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path1 = os.path.join(CHARTS_DIR, "label_dist_train.png")
    plt.savefig(path1, dpi=150, bbox_inches='tight'); plt.close()
    print(f"  Chart saved : {path1}")

    # ── CHART 2: Label distribution — Test ──
    test_counts = [int((test_df['label'] == i).sum()) for i in label_list]
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(label_names, test_counts,
                  color=[LABEL_COLORS[i] for i in label_list], edgecolor='white')
    for bar, count in zip(bars, test_counts):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(test_counts) * 0.01,
                str(count), ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_title("Label Distribution — Test Set", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("Label"); ax.set_ylabel("Clause Count")
    ax.set_ylim(0, max(test_counts) * 1.15)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path2 = os.path.join(CHARTS_DIR, "label_dist_test.png")
    plt.savefig(path2, dpi=150, bbox_inches='tight'); plt.close()
    print(f"  Chart saved : {path2}")

    # ── CHART 3: Insurance type comparison (all 6 types) ──
    type_colors = ['#1abc9c','#9b59b6','#3498db','#e74c3c','#f39c12','#34495e']
    train_type_counts = [int((train_df['insurance_type'] == t).sum()) for t in insurance_types]
    test_type_counts  = [int((test_df['insurance_type']  == t).sum()) for t in insurance_types]

    x     = np.arange(len(insurance_types))
    width = 0.35
    fig, ax = plt.subplots(figsize=(11, 5))
    bars_tr = ax.bar(x - width/2, train_type_counts, width, label='Train',
                     color=TRAIN_COLOR, edgecolor='white')
    bars_te = ax.bar(x + width/2, test_type_counts,  width, label='Test',
                     color=TEST_COLOR,  edgecolor='white')
    for bar in list(bars_tr) + list(bars_te):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 10,
                str(int(bar.get_height())),
                ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax.set_title("Insurance Type — Train vs Test", fontsize=14, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels([t.replace('_', '\n') for t in insurance_types], fontsize=10)
    ax.set_ylabel("Clause Count"); ax.legend(fontsize=11)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path3 = os.path.join(CHARTS_DIR, "insurance_type_split.png")
    plt.savefig(path3, dpi=150, bbox_inches='tight'); plt.close()
    print(f"  Chart saved : {path3}")

    # ── CHART 4: Clauses per PDF ──
    train_pdf_counts = train_df.groupby('source_file').size().reset_index(name='count')
    train_pdf_counts['split'] = 'Train'
    test_pdf_counts  = test_df.groupby('source_file').size().reset_index(name='count')
    test_pdf_counts['split']  = 'Test'

    all_pdfs = pd.concat([train_pdf_counts, test_pdf_counts]).sort_values('count', ascending=True)

    fig_height = max(8, len(all_pdfs) * 0.22)
    fig, ax = plt.subplots(figsize=(12, fig_height))
    colors = [TRAIN_COLOR if s == 'Train' else TEST_COLOR for s in all_pdfs['split']]
    labels = [n[:40] for n in all_pdfs['source_file']]
    ax.barh(labels, all_pdfs['count'], color=colors, edgecolor='white', height=0.7)

    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=TRAIN_COLOR, label='Train'),
                        Patch(facecolor=TEST_COLOR,  label='Test')],
              fontsize=11, loc='lower right')
    ax.set_title("Clauses per PDF", fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel("Clause Count")
    ax.tick_params(axis='y', labelsize=7)
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    plt.tight_layout()
    path4 = os.path.join(CHARTS_DIR, "clauses_per_pdf.png")
    plt.savefig(path4, dpi=150, bbox_inches='tight'); plt.close()
    print(f"  Chart saved : {path4}")


# ─────────────────────────────────────────────
# Function 8: save_split_report
# ─────────────────────────────────────────────
def save_split_report(df, train_df, test_df, train_pdfs, test_pdfs, validation_passed, insurance_types):
    """Print and save the full split report to SPLITS_DIR/split_report.txt (per config.py)."""

    train_pct = len(train_df) / len(df) * 100
    test_pct  = len(test_df)  / len(df) * 100

    def label_row(label_int, t_df, e_df):
        name    = LABEL_NAMES[label_int]
        t_count = int((t_df['label'] == label_int).sum())
        t_pct   = t_count / len(t_df) * 100
        e_count = int((e_df['label'] == label_int).sum())
        e_pct   = e_count / len(e_df) * 100
        return (f"  {name:<12}  {t_count:>5}  {t_pct:>6.1f}%"
                f"     {e_count:>5}  {e_pct:>6.1f}%")

    def type_row(type_name, t_df, e_df):
        t_count = int((t_df['insurance_type'] == type_name).sum())
        t_pct   = t_count / len(t_df) * 100
        e_count = int((e_df['insurance_type'] == type_name).sum())
        e_pct   = e_count / len(e_df) * 100
        return (f"  {type_name:<20}  {t_count:>5}  {t_pct:>6.1f}%"
                f"     {e_count:>5}  {e_pct:>6.1f}%")

    train_set  = set(train_df['source_file'].unique())
    test_set   = set(test_df['source_file'].unique())
    overlap    = train_set & test_set
    check1     = "PASSED" if not overlap else "FAILED"
    check2     = "PASSED" if {0,1,2,3}.issubset(set(train_df['label'].unique())) else "FAILED"
    check3     = "PASSED" if {0,1,2,3}.issubset(set(test_df['label'].unique()))  else "FAILED"
    all_types  = set(df['insurance_type'].unique())
    check4     = "PASSED" if all_types.issubset(set(test_df['insurance_type'].unique())) else "WARNING"
    check5     = "PASSED" if 15 <= test_pct <= 25 else "WARNING"
    overall    = "ALL CHECKS PASSED" if validation_passed else "CRITICAL FAILURE DETECTED"

    train_pdf_counts = train_df.groupby('source_file').size()
    test_pdf_counts  = test_df.groupby('source_file').size()

    lines = [
        "=" * 50,
        "TRAIN TEST SPLIT REPORT",
        "=" * 50,
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "SPLIT CONFIGURATION:",
        "  Method      : PDF-wise stratified split",
        f"  Test size   : {int(TEST_SIZE*100)}%",
        f"  Random seed : {RANDOM_SEED}",
        "  Stratify on : insurance_type + dominant_label",
        "",
        "DATASET OVERVIEW:",
        f"  Total clauses     : {len(df)}",
        f"  Train clauses     : {len(train_df)} ({train_pct:.1f}%)",
        f"  Test clauses      : {len(test_df)}  ({test_pct:.1f}%)",
        f"  Total PDFs        : {df['source_file'].nunique()}",
        f"  Train PDFs        : {len(train_pdfs)}",
        f"  Test PDFs         : {len(test_pdfs)}",
        f"  Insurance types   : {len(insurance_types)} ({', '.join(sorted(insurance_types))})",
        "",
        "LABEL DISTRIBUTION:",
        "                Train              Test",
        "  Label       Count    %       Count    %",
        label_row(0, train_df, test_df),
        label_row(1, train_df, test_df),
        label_row(2, train_df, test_df),
        label_row(3, train_df, test_df),
        "",
        "INSURANCE TYPE DISTRIBUTION:",
        "                        Train              Test",
        "  Type              Count    %       Count    %",
    ]
    for t in sorted(insurance_types):
        lines.append(type_row(t, train_df, test_df))

    lines += [
        "",
        f"TRAIN PDFs ({len(train_pdfs)} files):",
    ]
    for pdf in sorted(train_pdfs):
        lines.append(f"  {train_pdf_counts.get(pdf, 0):>4} clauses | {pdf}")

    lines += ["", f"TEST PDFs ({len(test_pdfs)} files):"]
    for pdf in sorted(test_pdfs):
        lines.append(f"  {test_pdf_counts.get(pdf, 0):>4} clauses | {pdf}")

    lines += [
        "",
        "VALIDATION RESULTS:",
        f"  CHECK 1 Data leakage  : {check1}",
        f"  CHECK 2 Train labels  : {check2}",
        f"  CHECK 3 Test labels   : {check3}",
        f"  CHECK 4 Type coverage : {check4}",
        f"  CHECK 5 Test size     : {check5}",
        "",
        f"  Overall status: {overall}",
        "",
        "NOTE FOR RESEARCH PAPER:",
        "  Dataset split at document level to prevent",
        "  data leakage. Train and test sets contain",
        "  clauses from entirely different PDF documents.",
        "  Model evaluated on completely unseen policies",
        "  confirming true generalization capability.",
        "",
        "=" * 50,
    ]

    report_text = "\n".join(lines)
    print()
    print(report_text)

    report_path = os.path.join(SPLITS_DIR, "split_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\n  Report saved: {report_path}")


# ─────────────────────────────────────────────
# Function 9: run_split_pipeline
# ─────────────────────────────────────────────
def run_split_pipeline():
    """Main pipeline: runs all split steps in order."""
    print("=" * 50)
    print("TRAIN TEST SPLIT PIPELINE")
    print("=" * 50)

    df = load_and_analyze(DATASET_PATH)
    insurance_types = set(df['insurance_type'].unique())

    pdf_summary = build_pdf_summary(df)

    print()
    print("PERFORMING SPLIT:")
    train_pdfs, test_pdfs = perform_split(pdf_summary)

    train_df, test_df = build_split_dataframes(df, train_pdfs, test_pdfs)

    passed = validate_split(df, train_df, test_df)

    if not passed:
        print("PIPELINE STOPPED: Fix critical errors above")
        return None, None

    print()
    print("SAVING FILES:")
    save_split_files(train_df, test_df, train_pdfs, test_pdfs)

    print()
    print("GENERATING CHARTS:")
    generate_charts(train_df, test_df, sorted(insurance_types))

    save_split_report(df, train_df, test_df, train_pdfs, test_pdfs, passed, insurance_types)

    print()
    print("=" * 50)
    print("SPLIT PIPELINE COMPLETE")
    print(f"  Train : {len(train_df)} clauses  ({len(train_pdfs)} PDFs)")
    print(f"  Test  : {len(test_df)} clauses   ({len(test_pdfs)} PDFs)")
    print(f"  Types : {len(insurance_types)}")
    print("=" * 50)

    return train_df, test_df


if __name__ == "__main__":
    run_split_pipeline()