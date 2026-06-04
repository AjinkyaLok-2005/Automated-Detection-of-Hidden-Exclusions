# ============================================
# run_split.py
# Entry point for Week 2: Train/Test Split
# ============================================
# Run with:
#   python run_split.py

from src.training.split_dataset import run_split_pipeline

if __name__ == "__main__":
    train_df, test_df = run_split_pipeline()

