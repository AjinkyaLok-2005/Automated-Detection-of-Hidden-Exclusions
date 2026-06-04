# tests/test_models.py
# Run after python run_training.py completes
#
# Usage:
#   python -m pytest tests/test_models.py -v

import pytest
import os
import re
from config import (
    TEST_PATH,
    BASELINE_RESULTS,
    FINETUNED_RESULTS,
    COMPARISON_TABLE,
    BERT_MODEL_DIR,
    BASELINE_CM_PATH,
    FINETUNED_CM_PATH
)


# ──────────────────────────────────────────────────────────
# File existence tests
# ──────────────────────────────────────────────────────────

def test_baseline_results_exist():
    """Baseline results text file must be present."""
    assert os.path.exists(BASELINE_RESULTS), \
        f"Baseline results file not found: {BASELINE_RESULTS}"


def test_finetuned_results_exist():
    """Fine-tuned results text file must be present."""
    assert os.path.exists(FINETUNED_RESULTS), \
        f"Fine-tuned results file not found: {FINETUNED_RESULTS}"


def test_comparison_table_exists():
    """Comparison table text file must be present."""
    assert os.path.exists(COMPARISON_TABLE), \
        f"Comparison table not found: {COMPARISON_TABLE}"


def test_model_files_saved():
    """Model directory and config.json must be present."""
    assert os.path.exists(BERT_MODEL_DIR), \
        f"Model directory not found: {BERT_MODEL_DIR}"

    config_file = os.path.join(BERT_MODEL_DIR, "config.json")
    assert os.path.exists(config_file), \
        f"Model config.json not found: {config_file}"


def test_confusion_matrices_exist():
    """Both confusion matrix PNGs must be present."""
    assert os.path.exists(BASELINE_CM_PATH), \
        f"Baseline confusion matrix not found: {BASELINE_CM_PATH}"
    assert os.path.exists(FINETUNED_CM_PATH), \
        f"Fine-tuned confusion matrix not found: {FINETUNED_CM_PATH}"


# ──────────────────────────────────────────────────────────
# Content / quality tests
# ──────────────────────────────────────────────────────────

def extract_macro_f1(text):
    """
    Extract macro avg F1 score from a classification report text.
    Searches for the line containing 'macro avg' and returns
    the last float on that line (which is the F1 score).

    Returns 0.0 if not found.
    """
    for line in text.split('\n'):
        if 'macro avg' in line.lower():
            parts = line.split()
            for part in reversed(parts):
                try:
                    return float(part)
                except ValueError:
                    continue
    return 0.0


def test_baseline_results_not_empty():
    """Baseline results file must contain actual content."""
    with open(BASELINE_RESULTS) as f:
        content = f.read()
    assert len(content) > 100, \
        "Baseline results file appears empty or too short."
    assert "Accuracy" in content or "accuracy" in content, \
        "Baseline results file does not contain accuracy metrics."


def test_finetuned_results_not_empty():
    """Fine-tuned results file must contain actual content."""
    with open(FINETUNED_RESULTS) as f:
        content = f.read()
    assert len(content) > 100, \
        "Fine-tuned results file appears empty or too short."
    assert "Accuracy" in content or "accuracy" in content, \
        "Fine-tuned results file does not contain accuracy metrics."


def test_comparison_table_has_all_metrics():
    """Comparison table must contain all required metric rows."""
    with open(COMPARISON_TABLE) as f:
        content = f.read()

    required = [
        "Accuracy",
        "F1 Normal",
        "F1 Coverage",
        "F1 Exclusion",
        "F1 Condition",
        "F1 Macro",
        "F1 Weighted",
    ]
    for metric in required:
        assert metric in content, \
            f"Missing metric in comparison table: {metric}"


def test_finetuned_beats_baseline():
    """
    Fine-tuned Macro F1 must be >= Baseline Macro F1.
    This is the core success criterion for Week 3.
    """
    with open(BASELINE_RESULTS) as f:
        base_text = f.read()
    with open(FINETUNED_RESULTS) as f:
        fine_text = f.read()

    base_f1 = extract_macro_f1(base_text)
    fine_f1 = extract_macro_f1(fine_text)

    assert base_f1 > 0, \
        "Could not extract Macro F1 from baseline results."
    assert fine_f1 > 0, \
        "Could not extract Macro F1 from fine-tuned results."

    assert fine_f1 >= base_f1, (
        f"Fine-tuned F1 ({fine_f1:.4f}) did not beat "
        f"baseline ({base_f1:.4f}). "
        f"Check training settings or class weights."
    )


def test_exclusion_f1_threshold():
    """
    Exclusion class F1 must be >= 0.50 in the fine-tuned model.
    Exclusion is the most critical class for insurance risk detection.
    """
    with open(FINETUNED_RESULTS) as f:
        content = f.read()

    # Look for "Exclusion" line in classification report
    exclusion_f1 = None
    for line in content.split('\n'):
        if 'Exclusion' in line:
            parts = line.split()
            # classification_report format: name  prec  rec  f1  support
            for part in parts:
                try:
                    val = float(part)
                    if 0.0 <= val <= 1.0:
                        exclusion_f1 = val  # Last valid float = F1
                except ValueError:
                    continue

    assert exclusion_f1 is not None, \
        "Could not find Exclusion F1 in fine-tuned results."
    assert exclusion_f1 >= 0.50, (
        f"Exclusion F1 ({exclusion_f1:.4f}) is below 0.50 threshold. "
        f"Consider increasing class weight for Exclusion label."
    )


def test_model_weights_file_exists():
    """
    pytorch_model.bin OR model.safetensors must exist in model dir.
    Newer transformers versions use safetensors format.
    """
    bin_path        = os.path.join(BERT_MODEL_DIR, "pytorch_model.bin")
    safetensors_path = os.path.join(BERT_MODEL_DIR, "model.safetensors")

    assert os.path.exists(bin_path) or os.path.exists(safetensors_path), (
        f"No model weights file found in {BERT_MODEL_DIR}. "
        f"Expected pytorch_model.bin or model.safetensors."
    )


def test_tokenizer_files_saved():
    """Tokenizer vocab file must be saved with the model."""
    vocab_path = os.path.join(BERT_MODEL_DIR, "vocab.txt")
    tokenizer_config_path = os.path.join(
        BERT_MODEL_DIR, "tokenizer_config.json"
    )
    assert os.path.exists(vocab_path) or \
           os.path.exists(tokenizer_config_path), (
        f"No tokenizer files found in {BERT_MODEL_DIR}."
    )