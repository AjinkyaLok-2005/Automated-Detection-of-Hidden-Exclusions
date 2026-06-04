# ============================================================
# config.py — Central configuration for entire project
# ============================================================

import os

# ── Project root ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Data paths ───────────────────────────────────────────
DATA_DIR         = os.path.join(BASE_DIR, "data")
RAW_PDF_HEALTH   = os.path.join(DATA_DIR, "raw_pdfs", "Health insurance")
RAW_PDF_CAR      = os.path.join(DATA_DIR, "raw_pdfs", "CAR Insurance")
PROCESSED_DIR    = os.path.join(DATA_DIR, "processed")
VERIFICATION_DIR = os.path.join(DATA_DIR, "verification")

DATASET_PATH = os.path.join(PROCESSED_DIR, "insurance_clauses_final_NEW.csv")
TRAIN_PATH   = os.path.join(PROCESSED_DIR, "train.csv")
TEST_PATH    = os.path.join(PROCESSED_DIR, "test.csv")

# ── Output paths ─────────────────────────────────────────
OUTPUTS_DIR     = os.path.join(BASE_DIR, "outputs")
SPLITS_DIR      = os.path.join(OUTPUTS_DIR, "splits")
CHARTS_DIR      = os.path.join(OUTPUTS_DIR, "charts")
EVALUATION_DIR  = os.path.join(OUTPUTS_DIR, "evaluation")
HIDDEN_COND_DIR = os.path.join(OUTPUTS_DIR, "hidden_conditions")
REPORTS_DIR     = os.path.join(OUTPUTS_DIR, "reports")

# ── Model paths ──────────────────────────────────────────
MODELS_DIR     = os.path.join(BASE_DIR, "models")
BERT_MODEL_DIR = os.path.join(MODELS_DIR, "legal_bert_finetuned")
SENT_MODEL_DIR = os.path.join(MODELS_DIR, "sentence_transformer")

# ── Split settings ───────────────────────────────────────
TEST_SIZE   = 0.2
RANDOM_SEED = 42

# ── Label mapping ────────────────────────────────────────
LABEL_NAMES = {
    0: "Normal",
    1: "Coverage",
    2: "Exclusion",
    3: "Condition"
}
INT_TO_LABEL = {
    0: "normal",
    1: "coverage",
    2: "exclusion",
    3: "condition"
}
LABEL_TO_INT = {v: k for k, v in INT_TO_LABEL.items()}

# ── Baseline model (zero-shot, no training) ───────────────
BASELINE_MODEL   = "facebook/bart-large-mnli"
ZERO_SHOT_LABELS = [
    "normal clause",
    "coverage clause",
    "exclusion clause",
    "condition clause"
]
ZERO_SHOT_MAP = {
    "normal clause"    : 0,
    "coverage clause"  : 1,
    "exclusion clause" : 2,
    "condition clause" : 3
}

# ── Legal-BERT fine-tuning settings ──────────────────────
MODEL_NAME    = "nlpaueb/legal-bert-base-uncased"
MAX_LENGTH    = 256
BATCH_SIZE    = 16
EPOCHS        = 6
LEARNING_RATE = 3e-5
WARMUP_STEPS  = 500
WEIGHT_DECAY  = 0.01
DROPOUT       = 0.1
NUM_LABELS    = 4

# Class weights — calibrated for dataset distribution:
# Normal=33.1%, Coverage=24.5%, Exclusion=13.1%, Condition=29.3%
CLASS_WEIGHTS = {
    0: 1.5,   # Normal    — boost, F1 was only 0.32 last run
    1: 1.0,   # Coverage  — balanced, F1 was 0.47
    2: 2.0,   # Exclusion — highest, most critical for paper
    3: 1.0    # Condition — balanced, F1 was 0.49
}

# ── Evaluation output paths ──────────────────────────────
BASELINE_RESULTS   = os.path.join(EVALUATION_DIR, "baseline_results.txt")
FINETUNED_RESULTS  = os.path.join(EVALUATION_DIR, "finetuned_results.txt")
COMPARISON_TABLE   = os.path.join(EVALUATION_DIR, "comparison_table.txt")
BASELINE_CM_PATH   = os.path.join(EVALUATION_DIR, "confusion_matrices",
                                   "baseline_cm.png")
FINETUNED_CM_PATH  = os.path.join(EVALUATION_DIR, "confusion_matrices",
                                   "finetuned_cm.png")
TRAINING_LOSS_PATH = os.path.join(CHARTS_DIR, "training_loss.png")
TRAINING_ACC_PATH  = os.path.join(CHARTS_DIR, "training_accuracy.png")

# ── Inference / similarity settings ─────────────────────
SIMILARITY_THRESHOLD     = 0.65
SIMILARITY_MODEL         = "all-MiniLM-L6-v2"
NLI_MODEL                = "cross-encoder/nli-roberta-base"
HIDDEN_CONDITION_PHRASES = [
    "subject to", "provided that", "unless", "except when",
    "notwithstanding", "in the event that", "contingent upon",
    "only if", "in no case", "under no circumstances",
    "shall not apply", "does not cover", "not covered",
    "excluded from", "limitation applies", "restricted to"
]

# ── Risk scoring ─────────────────────────────────────────
RISK_WEIGHTS = {0: 0.1, 1: 0.2, 2: 0.8, 3: 0.5}
RISK_LEVELS  = {
    "Low"      : (0.0, 0.3),
    "Medium"   : (0.3, 0.6),
    "High"     : (0.6, 0.8),
    "Very High": (0.8, 1.0)
}

# ── API settings ─────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000

# ── Files to skip during PDF processing ──────────────────
SKIP_FILES = [
    "LIC_Jeevan",
    "Health Insurance Coverage in India"
]

# ── Create all directories on import ─────────────────────
for _dir in [
    PROCESSED_DIR, VERIFICATION_DIR,
    SPLITS_DIR, CHARTS_DIR, EVALUATION_DIR,
    HIDDEN_COND_DIR, REPORTS_DIR,
    MODELS_DIR, BERT_MODEL_DIR, SENT_MODEL_DIR,
    os.path.join(EVALUATION_DIR, "confusion_matrices")
]:
    os.makedirs(_dir, exist_ok=True)

# # ============================================
# # config.py
# # Central configuration for entire project
# # ============================================

# import os

# # ── Project root ──────────────────────────
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# # ── Data paths ────────────────────────────
# DATA_DIR         = os.path.join(BASE_DIR, "data")
# RAW_PDF_HEALTH   = os.path.join(DATA_DIR, "raw_pdfs", "Health insurance")
# RAW_PDF_CAR      = os.path.join(DATA_DIR, "raw_pdfs", "CAR Insurance")
# PROCESSED_DIR    = os.path.join(DATA_DIR, "processed")
# VERIFICATION_DIR = os.path.join(DATA_DIR, "verification")

# DATASET_PATH = os.path.join(PROCESSED_DIR, "insurance_clauses_final (1).csv")
# TRAIN_PATH   = os.path.join(PROCESSED_DIR, "train.csv")
# TEST_PATH    = os.path.join(PROCESSED_DIR, "test.csv")

# # ── Output paths ─────────────────────────
# OUTPUTS_DIR     = os.path.join(BASE_DIR, "outputs")
# SPLITS_DIR      = os.path.join(OUTPUTS_DIR, "splits")
# CHARTS_DIR      = os.path.join(OUTPUTS_DIR, "charts")
# EVALUATION_DIR  = os.path.join(OUTPUTS_DIR, "evaluation")
# HIDDEN_COND_DIR = os.path.join(OUTPUTS_DIR, "hidden_conditions")

# # ── Model paths ──────────────────────────
# MODELS_DIR     = os.path.join(BASE_DIR, "models")
# BERT_MODEL_DIR = os.path.join(MODELS_DIR, "legal_bert_finetuned")
# SENT_MODEL_DIR = os.path.join(MODELS_DIR, "sentence_transformer")

# # ── Split settings ───────────────────────
# TEST_SIZE   = 0.2
# RANDOM_SEED = 42

# # ── Model settings ───────────────────────
# MODEL_NAME    = "nlpaueb/legal-bert-base-uncased"
# MAX_LENGTH    = 256
# BATCH_SIZE    = 16
# EPOCHS        = 6
# LEARNING_RATE = 3e-5
# DROPOUT = 0.1


# # ── Similarity settings ──────────────────
# SIMILARITY_THRESHOLD = 0.65
# SIMILARITY_MODEL     = "all-MiniLM-L6-v2"

# # ── NLI settings ─────────────────────────
# NLI_MODEL = "cross-encoder/nli-roberta-base"

# # ── Risk score weights ───────────────────
# RISK_WEIGHTS = {
#     0: 0.1,
#     1: 0.2,
#     2: 0.8,
#     3: 0.5
# }

# # ── Risk level thresholds ────────────────
# RISK_LEVELS = {
#     "Low"      : (0.0, 0.3),
#     "Medium"   : (0.3, 0.6),
#     "High"     : (0.6, 0.8),
#     "Very High": (0.8, 1.0)
# }

# # ── Label mapping ────────────────────────
# LABEL_NAMES = {
#     0: "Normal",
#     1: "Coverage",
#     2: "Exclusion",
#     3: "Condition"
# }

# INT_TO_LABEL = {
#     0: "normal",
#     1: "coverage",
#     2: "exclusion",
#     3: "condition"
# }

# LABEL_TO_INT = {v: k for k, v in INT_TO_LABEL.items()}

# # ── Files to skip ────────────────────────
# SKIP_FILES = [
#     "LIC_Jeevan",
#     "Health Insurance Coverage in India"
# ]

# # ── API settings ─────────────────────────
# API_HOST = "0.0.0.0"
# API_PORT = 8000

# # ── Create all directories on import ─────
# for _directory in [
#     PROCESSED_DIR, VERIFICATION_DIR,
#     SPLITS_DIR, CHARTS_DIR, EVALUATION_DIR,
#     HIDDEN_COND_DIR, MODELS_DIR,
#     BERT_MODEL_DIR, SENT_MODEL_DIR
# ]:
#     os.makedirs(_directory, exist_ok=True)


# # Baseline model (zero-shot, no training)
# BASELINE_MODEL   = "facebook/bart-large-mnli"
# ZERO_SHOT_LABELS = [
#     "normal clause",
#     "coverage clause",
#     "exclusion clause",
#     "condition clause"
# ]
# ZERO_SHOT_MAP = {
#     "normal clause"    : 0,
#     "coverage clause"  : 1,
#     "exclusion clause" : 2,
#     "condition clause" : 3
# }
 
# # Legal-BERT fine-tuning settings
# MODEL_NAME    = "nlpaueb/legal-bert-base-uncased"
# MAX_LENGTH    = 256
# BATCH_SIZE    = 16
# EPOCHS        = 6          # increased from 3
# LEARNING_RATE = 3e-5       # increased from 2e-5
# WARMUP_STEPS  = 500        # increased from 200
# WEIGHT_DECAY  = 0.01
# DROPOUT = 0.1      # fixed typo from DROUP_OUT
# NUM_LABELS    = 4

# # Class weights — calibrated for NEW dataset distribution:
# # Normal=33.1%, Coverage=24.5%, Exclusion=13.1%, Condition=29.3%
# # Normal had F1=0.32 last run — needs boost not reduction
# # Exclusion is most critical for paper — keep highest
# CLASS_WEIGHTS = {
#     0: 1.5,   # Normal    — was 0.5, INCREASE, F1 was only 0.32
#     1: 1.0,   # Coverage  — balanced, F1 was 0.47
#     2: 2.0,   # Exclusion — keep highest, most important for paper
#     3: 1.0    # Condition — balanced, F1 was 0.49
# }
 
# # Evaluation output paths
# BASELINE_RESULTS  = os.path.join(EVALUATION_DIR, "baseline_results.txt")
# FINETUNED_RESULTS = os.path.join(EVALUATION_DIR, "finetuned_results.txt")
# COMPARISON_TABLE  = os.path.join(EVALUATION_DIR, "comparison_table.txt")
# BASELINE_CM_PATH  = os.path.join(
#     EVALUATION_DIR, "confusion_matrices", "baseline_cm.png")
# FINETUNED_CM_PATH = os.path.join(
#     EVALUATION_DIR, "confusion_matrices", "finetuned_cm.png")
# TRAINING_LOSS_PATH = os.path.join(CHARTS_DIR, "training_loss.png")
# TRAINING_ACC_PATH  = os.path.join(CHARTS_DIR, "training_accuracy.png")
 
# # Create confusion matrices subdirectory
# os.makedirs(os.path.join(EVALUATION_DIR, "confusion_matrices"),
#             exist_ok=True)

