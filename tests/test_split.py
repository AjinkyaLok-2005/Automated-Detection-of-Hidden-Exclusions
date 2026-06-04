# ============================================
# tests/test_split.py
# Unit tests for train/test split quality
# ============================================
# Run with:
#   python -m pytest tests/test_split.py -v

import os
import sys
import pytest
import pandas as pd

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TRAIN_PATH, TEST_PATH

REQUIRED_COLUMNS = [
    'clause_id', 'clause_text', 'section_heading',
    'section_label', 'label', 'insurance_type',
    'source_file', 'page_number'
]


@pytest.fixture(scope='module')
def train_df():
    assert os.path.exists(TRAIN_PATH), (
        f"train.csv not found at {TRAIN_PATH}. "
        "Run `python run_split.py` first."
    )
    return pd.read_csv(TRAIN_PATH, encoding='utf-8-sig')


@pytest.fixture(scope='module')
def test_df():
    assert os.path.exists(TEST_PATH), (
        f"test.csv not found at {TEST_PATH}. "
        "Run `python run_split.py` first."
    )
    return pd.read_csv(TEST_PATH, encoding='utf-8-sig')


# ─────────────────────────────────────────────
# Test 1: No data leakage between splits
# ─────────────────────────────────────────────
def test_no_data_leakage(train_df, test_df):
    """No PDF should appear in both train and test."""
    train_pdfs = set(train_df['source_file'].unique())
    test_pdfs  = set(test_df['source_file'].unique())
    overlap    = train_pdfs & test_pdfs
    assert overlap == set(), (
        f"DATA LEAKAGE DETECTED! {len(overlap)} PDF(s) in both splits: {overlap}"
    )


# ─────────────────────────────────────────────
# Test 2: All 4 labels present in both splits
# ─────────────────────────────────────────────
def test_all_labels_present(train_df, test_df):
    """Train and test must both contain all 4 labels (0, 1, 2, 3)."""
    required = {0, 1, 2, 3}

    train_labels   = set(train_df['label'].unique())
    missing_train  = required - train_labels
    assert missing_train == set(), (
        f"Train is missing labels: {missing_train}"
    )

    test_labels  = set(test_df['label'].unique())
    missing_test = required - test_labels
    assert missing_test == set(), (
        f"Test is missing labels: {missing_test}"
    )


# ─────────────────────────────────────────────
# Test 3: No null values in either split
# ─────────────────────────────────────────────
def test_no_null_values(train_df, test_df):
    """Neither train nor test should contain any null values."""
    train_nulls = int(train_df.isnull().sum().sum())
    assert train_nulls == 0, (
        f"Train has {train_nulls} null value(s). Check data integrity."
    )

    test_nulls = int(test_df.isnull().sum().sum())
    assert test_nulls == 0, (
        f"Test has {test_nulls} null value(s). Check data integrity."
    )


# ─────────────────────────────────────────────
# Test 4: All 8 original columns present
# ─────────────────────────────────────────────
def test_all_columns_present(train_df):
    """Train CSV must contain all 8 original columns."""
    missing = [col for col in REQUIRED_COLUMNS if col not in train_df.columns]
    assert missing == [], (
        f"Train CSV is missing columns: {missing}"
    )


# ─────────────────────────────────────────────
# Test 5: Both insurance types in test set
# ─────────────────────────────────────────────
def test_insurance_types_in_test(test_df):
    """Test set must contain both 'health' and 'car' insurance types."""
    test_types = set(test_df['insurance_type'].unique())
    missing    = {'health', 'car'} - test_types
    assert missing == set(), (
        f"Test set is missing insurance type(s): {missing}"
    )
