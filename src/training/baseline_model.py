# src/training/baseline_model.py
# Zero-shot baseline model using facebook/bart-large-mnli
# No training — pure pretrained model evaluation

from transformers import pipeline
import pandas as pd
import numpy as np
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
import matplotlib.pyplot as plt
import seaborn as sns
from config import (
    TEST_PATH, BASELINE_MODEL,
    ZERO_SHOT_LABELS, ZERO_SHOT_MAP,
    LABEL_NAMES, BASELINE_RESULTS,
    BASELINE_CM_PATH
)


# ──────────────────────────────────────────────────────────
# Function 1: load_zero_shot_classifier
# ──────────────────────────────────────────────────────────

def load_zero_shot_classifier():
    """
    Load pretrained zero-shot classification pipeline.
    No training involved — uses model weights as-is.

    Returns:
        HuggingFace pipeline object
    """
    print("Loading zero-shot classifier...")
    print(f"Model: {BASELINE_MODEL}")

    classifier = pipeline(
        "zero-shot-classification",
        model=BASELINE_MODEL
    )

    print("Model loaded successfully")
    return classifier


# ──────────────────────────────────────────────────────────
# Function 2: predict_zero_shot
# ──────────────────────────────────────────────────────────

def predict_zero_shot(classifier, clauses, batch_size=32):
    """
    Run zero-shot predictions on a list of clause strings.

    Args:
        classifier : HuggingFace zero-shot pipeline
        clauses    : list of clause text strings
        batch_size : how often to print progress

    Returns:
        list of predicted integer labels (0–3)
    """
    predictions = []
    total = len(clauses)

    for i, clause in enumerate(clauses):
        if i % batch_size == 0:
            print(f"Progress: {i}/{total} clauses processed...")

        try:
            result = classifier(
                clause,
                ZERO_SHOT_LABELS,
                multi_label=False
            )
            top_label = result['labels'][0]
            pred = ZERO_SHOT_MAP[top_label]
            predictions.append(pred)

        except Exception as e:
            print(f"Error on clause {i}: {e}")
            predictions.append(0)  # Default to Normal on error

    print(f"Progress: {total}/{total} clauses processed.")
    return predictions


# ──────────────────────────────────────────────────────────
# Function 3: evaluate_predictions
# ──────────────────────────────────────────────────────────

def evaluate_predictions(true_labels, predictions,
                         model_name="Baseline"):
    """
    Compute and display classification metrics.

    Args:
        true_labels : list of ground-truth integer labels
        predictions : list of predicted integer labels
        model_name  : string label for display

    Returns:
        dict with accuracy, per-class F1, macro F1, weighted F1
    """
    label_names = list(LABEL_NAMES.values())

    accuracy = accuracy_score(true_labels, predictions)

    report = classification_report(
        true_labels,
        predictions,
        target_names=label_names,
        output_dict=True
    )

    report_text = classification_report(
        true_labels,
        predictions,
        target_names=label_names
    )

    print(f"\n{'='*50}")
    print(f"EVALUATION RESULTS: {model_name}")
    print(f"{'='*50}")
    print(f"Overall Accuracy: {accuracy:.4f}")
    print()
    print(report_text)

    metrics = {
        "model"        : model_name,
        "accuracy"     : accuracy,
        "f1_normal"    : report['Normal']['f1-score'],
        "f1_coverage"  : report['Coverage']['f1-score'],
        "f1_exclusion" : report['Exclusion']['f1-score'],
        "f1_condition" : report['Condition']['f1-score'],
        "f1_macro"     : report['macro avg']['f1-score'],
        "f1_weighted"  : report['weighted avg']['f1-score'],
        "report_text"  : report_text
    }

    return metrics


# ──────────────────────────────────────────────────────────
# Function 4: save_confusion_matrix
# ──────────────────────────────────────────────────────────

def save_confusion_matrix(true_labels, predictions,
                          save_path, title):
    """
    Generate a seaborn heatmap confusion matrix and save as PNG.

    Args:
        true_labels : list of ground-truth integer labels
        predictions : list of predicted integer labels
        save_path   : full file path to save PNG
        title       : chart title string
    """
    label_names = list(LABEL_NAMES.values())
    cm = confusion_matrix(true_labels, predictions)

    plt.figure(figsize=(8, 6))
    sns.heatmap(
        cm,
        annot=True,
        fmt='d',
        cmap='Blues',
        xticklabels=label_names,
        yticklabels=label_names
    )
    plt.title(title)
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Confusion matrix saved: {save_path}")


# ──────────────────────────────────────────────────────────
# Function 5: save_results
# ──────────────────────────────────────────────────────────

def save_results(metrics, save_path):
    """
    Write evaluation metrics to a text file.

    Args:
        metrics   : dict returned by evaluate_predictions()
        save_path : full path to output .txt file
    """
    with open(save_path, 'w') as f:
        f.write("=" * 50 + "\n")
        f.write(f"MODEL: {metrics['model']}\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Overall Accuracy : {metrics['accuracy']:.4f}\n")
        f.write(f"Macro F1 Score   : {metrics['f1_macro']:.4f}\n")
        f.write(f"Weighted F1 Score: {metrics['f1_weighted']:.4f}\n\n")
        f.write("Per-Class F1 Scores:\n")
        f.write(f"  Normal    : {metrics['f1_normal']:.4f}\n")
        f.write(f"  Coverage  : {metrics['f1_coverage']:.4f}\n")
        f.write(f"  Exclusion : {metrics['f1_exclusion']:.4f}\n")
        f.write(f"  Condition : {metrics['f1_condition']:.4f}\n\n")
        f.write("Full Classification Report:\n")
        f.write(metrics['report_text'])

    print(f"Results saved: {save_path}")


# ──────────────────────────────────────────────────────────
# Function 6: run_baseline  (main entry point)
# ──────────────────────────────────────────────────────────

def run_baseline():
    """
    Full zero-shot baseline pipeline:
      1. Load test.csv
      2. Load pretrained classifier
      3. Predict on all clauses
      4. Evaluate and print metrics
      5. Save confusion matrix PNG
      6. Save results .txt

    Returns:
        metrics dict
    """
    print("=" * 50)
    print("ZERO-SHOT BASELINE MODEL")
    print("=" * 50)

    # Load test data
    print(f"\nLoading test data: {TEST_PATH}")
    test_df = pd.read_csv(TEST_PATH)
    print(f"Test clauses: {len(test_df)}")

    # Load model
    classifier = load_zero_shot_classifier()

    # Run predictions
    print("\nRunning zero-shot predictions...")
    clauses = test_df['clause_text'].tolist()
    predictions = predict_zero_shot(classifier, clauses)

    # Evaluate
    true_labels = test_df['label'].tolist()
    metrics = evaluate_predictions(
        true_labels, predictions, "Zero-Shot Baseline"
    )

    # Save confusion matrix
    save_confusion_matrix(
        true_labels, predictions,
        BASELINE_CM_PATH,
        "Confusion Matrix — Zero-Shot Baseline"
    )

    # Save results text file
    save_results(metrics, BASELINE_RESULTS)

    print("\nBaseline complete.")
    print(f"Macro F1     : {metrics['f1_macro']:.4f}")
    print(f"Exclusion F1 : {metrics['f1_exclusion']:.4f}")

    return metrics


# ──────────────────────────────────────────────────────────
# Allow running directly: python src/training/baseline_model.py
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_baseline()