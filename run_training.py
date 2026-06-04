# run_training.py
# Week 3 entry point — run this from the project root
#
# Usage:
#   python run_training.py
#
# What it does:
#   Part A: Zero-shot baseline (no training, benchmark)
#   Part B: Legal-BERT fine-tuning (trains on train.csv)
#   Saves all results to outputs/evaluation/

from src.training.baseline_model import run_baseline
from src.training.finetune_legal_bert import run_finetuning



def main():
    print("=" * 50)
    print("WEEK 3: MODEL TRAINING PIPELINE")
    print("=" * 50)
    print()

    # ── Part A: Zero-shot baseline ──────────────────────
    print("PART A: ZERO-SHOT BASELINE")
    print("-" * 50)
    baseline_metrics = run_baseline()

    print()
    print("=" * 50)
    print()

    # ── Part B: Legal-BERT fine-tuning ──────────────────
    print("PART B: LEGAL-BERT FINE-TUNING")
    print("-" * 50)
    finetuned_metrics = run_finetuning(baseline_metrics)

    # ── Final summary ────────────────────────────────────
    print()
    print("=" * 50)
    print("WEEK 3 COMPLETE")
    print("=" * 50)
    print()
    print("Results saved to  : outputs/evaluation/")
    print("Model saved to    : models/legal_bert_finetuned/")
    print()
    print("Summary:")
    print(f"  Baseline Macro F1  : {baseline_metrics['f1_macro']:.4f}")
    print(f"  Fine-tuned Macro F1: {finetuned_metrics['f1_macro']:.4f}")

    improvement = (
        finetuned_metrics['f1_macro'] - baseline_metrics['f1_macro']
    )
    sign = "+" if improvement >= 0 else ""
    print(f"  Improvement        : {sign}{improvement:.4f}")
    print()

    if improvement > 0:
        print("✓ Fine-tuned model beats baseline. Ready for Week 4.")
    else:
        print("✗ Fine-tuned model did NOT beat baseline.")
        print("  Check: class weights, learning rate, epochs.")
        print("  Suggestions: try lr=3e-5, epochs=8")


if __name__ == "__main__":
    main()