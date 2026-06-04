# src/training/finetune_legal_bert.py
# Fine-tune Legal-BERT on insurance clause data
# Trains on train.csv, evaluates on test.csv
# Saves best model to models/legal_bert_finetuned/

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    accuracy_score
)
import torch
from torch.utils.data import Dataset, DataLoader
# from transformers import (
#     AutoTokenizer,
#     AutoModelForSequenceClassification,
#     AdamW,
#     get_linear_schedule_with_warmup
# )
# REPLACE with this:
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    get_linear_schedule_with_warmup)
from torch.optim import AdamW
from config import (
    TRAIN_PATH, TEST_PATH,
    MODEL_NAME, MAX_LENGTH,
    BATCH_SIZE, EPOCHS,
    LEARNING_RATE, WARMUP_STEPS,
    WEIGHT_DECAY, NUM_LABELS,
    CLASS_WEIGHTS, LABEL_NAMES,
    BERT_MODEL_DIR, FINETUNED_RESULTS,
    FINETUNED_CM_PATH, TRAINING_LOSS_PATH,
    TRAINING_ACC_PATH, RANDOM_SEED,
    COMPARISON_TABLE
)
DROPOUT = 0.1

# ──────────────────────────────────────────────────────────
# PyTorch Dataset
# ──────────────────────────────────────────────────────────

class InsuranceClauseDataset(Dataset):
    """
    PyTorch Dataset that tokenizes clause texts
    and returns tensors ready for model input.
    """

    def __init__(self, texts, labels, tokenizer):
        self.texts     = texts
        self.labels    = labels
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        encoding = self.tokenizer(
            self.texts[idx],
            max_length=MAX_LENGTH,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        return {
            'input_ids'      : encoding['input_ids'].squeeze(),
            'attention_mask' : encoding['attention_mask'].squeeze(),
            'label'          : torch.tensor(
                                   self.labels[idx],
                                   dtype=torch.long)
        }


# ──────────────────────────────────────────────────────────
# Function 1: load_data
# ──────────────────────────────────────────────────────────

def load_data():
    """
    Load train and test CSV files.

    Returns:
        train_df (DataFrame), test_df (DataFrame)
    """
    print(f"Loading train: {TRAIN_PATH}")
    train_df = pd.read_csv(TRAIN_PATH)
    print(f"Train clauses: {len(train_df)}")

    print(f"Loading test : {TEST_PATH}")
    test_df = pd.read_csv(TEST_PATH)
    print(f"Test clauses : {len(test_df)}")

    # Show label distribution
    print("\nLabel distribution (train):")
    label_counts = train_df['label'].value_counts().sort_index()
    for label_id, count in label_counts.items():
        label_name = LABEL_NAMES.get(label_id, f"Label {label_id}")
        pct = count / len(train_df) * 100
        print(f"  {label_name:<12} ({label_id}): {count:>5}  ({pct:.1f}%)")

    return train_df, test_df


# ──────────────────────────────────────────────────────────
# Function 2: load_model_and_tokenizer
# ──────────────────────────────────────────────────────────

def load_model_and_tokenizer():
    """
    Load Legal-BERT tokenizer and sequence classification model.

    Returns:
        tokenizer, model
    """
    print(f"\nLoading model: {MODEL_NAME}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    # FIXED — dropout now applied
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        hidden_dropout_prob=DROPOUT,
        attention_probs_dropout_prob=DROPOUT
    )

    print("Model loaded successfully")
    print(f"Parameters: {model.num_parameters():,}")

    return tokenizer, model


# ──────────────────────────────────────────────────────────
# Function 3: create_data_loaders
# ──────────────────────────────────────────────────────────

def create_data_loaders(train_df, test_df, tokenizer):
    """
    Wrap DataFrames in PyTorch DataLoaders.

    Args:
        train_df  : training DataFrame
        test_df   : test DataFrame
        tokenizer : HuggingFace tokenizer

    Returns:
        train_loader, test_loader
    """
    train_dataset = InsuranceClauseDataset(
        train_df['clause_text'].tolist(),
        train_df['label'].tolist(),
        tokenizer
    )

    test_dataset = InsuranceClauseDataset(
        test_df['clause_text'].tolist(),
        test_df['label'].tolist(),
        tokenizer
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False
    )

    print(f"\nTrain batches : {len(train_loader)}")
    print(f"Test batches  : {len(test_loader)}")

    return train_loader, test_loader


# ──────────────────────────────────────────────────────────
# Function 4: get_class_weights
# ──────────────────────────────────────────────────────────

def get_class_weights(device):
    """
    Convert CLASS_WEIGHTS dict to a tensor on the target device.

    Args:
        device : torch.device

    Returns:
        FloatTensor of shape [NUM_LABELS]
    """
    weights = [
        CLASS_WEIGHTS[0],   # Normal
        CLASS_WEIGHTS[1],   # Coverage
        CLASS_WEIGHTS[2],   # Exclusion
        CLASS_WEIGHTS[3],   # Condition
    ]
    return torch.tensor(weights, dtype=torch.float).to(device)


# ──────────────────────────────────────────────────────────
# Function 5: train_one_epoch
# ──────────────────────────────────────────────────────────

def train_one_epoch(model, train_loader, optimizer,
                    scheduler, criterion, device):
    """
    Run one full pass over the training data.

    Args:
        model        : the BERT model
        train_loader : DataLoader for training set
        optimizer    : AdamW optimizer
        scheduler    : linear warmup scheduler
        criterion    : weighted CrossEntropyLoss
        device       : torch.device

    Returns:
        avg_loss (float), accuracy (float)
    """
    model.train()
    total_loss = 0
    correct    = 0
    total      = 0

    for batch_idx, batch in enumerate(train_loader):
        input_ids      = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels         = batch['label'].to(device)

        optimizer.zero_grad()

        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask
        )

        logits = outputs.logits
        loss   = criterion(logits, labels)

        loss.backward()

        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)

        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        preds    = torch.argmax(logits, dim=1)
        correct += (preds == labels).sum().item()
        total   += labels.size(0)

        if batch_idx % 50 == 0:
            print(f"  Batch {batch_idx}/{len(train_loader)}"
                  f"  Loss: {loss.item():.4f}")

    avg_loss = total_loss / len(train_loader)
    accuracy = correct / total
    return avg_loss, accuracy


# ──────────────────────────────────────────────────────────
# Function 6: evaluate_model
# ──────────────────────────────────────────────────────────

def evaluate_model(model, test_loader, criterion, device):
    """
    Evaluate model on test set — no gradient updates.

    Args:
        model       : the BERT model
        test_loader : DataLoader for test set
        criterion   : loss function
        device      : torch.device

    Returns:
        avg_loss (float), accuracy (float),
        all_preds (list), all_labels (list)
    """
    model.eval()
    total_loss = 0
    all_preds  = []
    all_labels = []

    with torch.no_grad():
        for batch in test_loader:
            input_ids      = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels         = batch['label'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            logits = outputs.logits
            loss   = criterion(logits, labels)

            total_loss += loss.item()
            preds = torch.argmax(logits, dim=1)

            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())

    avg_loss = total_loss / len(test_loader)
    accuracy = accuracy_score(all_labels, all_preds)

    return avg_loss, accuracy, all_preds, all_labels


# ──────────────────────────────────────────────────────────
# Function 7: plot_training_curves
# ──────────────────────────────────────────────────────────

def plot_training_curves(train_losses, train_accs,
                         val_losses, val_accs):
    """
    Save training loss curve and accuracy curve as PNGs.

    Args:
        train_losses : list of train loss per epoch
        train_accs   : list of train accuracy per epoch
        val_losses   : list of val loss per epoch
        val_accs     : list of val accuracy per epoch
    """
    epochs_range = range(1, len(train_losses) + 1)

    # ── Loss curve ──────────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(epochs_range, train_losses,
             label='Train Loss', marker='o', color='#2980b9')
    plt.plot(epochs_range, val_losses,
             label='Val Loss',   marker='s', color='#e74c3c')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(TRAINING_LOSS_PATH, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Loss curve saved: {TRAINING_LOSS_PATH}")

    # ── Accuracy curve ───────────────────────────────
    plt.figure(figsize=(10, 5))
    plt.plot(epochs_range, train_accs,
             label='Train Accuracy', marker='o', color='#27ae60')
    plt.plot(epochs_range, val_accs,
             label='Val Accuracy',   marker='s', color='#f39c12')
    plt.title('Training and Validation Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(TRAINING_ACC_PATH, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Accuracy curve saved: {TRAINING_ACC_PATH}")


# ──────────────────────────────────────────────────────────
# Function 8: save_model
# ──────────────────────────────────────────────────────────

def save_model(model, tokenizer):
    """
    Save fine-tuned model and tokenizer to disk.

    Args:
        model     : trained model
        tokenizer : tokenizer to save alongside
    """
    os.makedirs(BERT_MODEL_DIR, exist_ok=True)
    model.save_pretrained(BERT_MODEL_DIR)
    tokenizer.save_pretrained(BERT_MODEL_DIR)
    print(f"Model saved: {BERT_MODEL_DIR}")


# ──────────────────────────────────────────────────────────
# Function 9: generate_comparison_table
# ──────────────────────────────────────────────────────────

def generate_comparison_table(baseline_metrics, finetuned_metrics):
    """
    Print and save a side-by-side comparison of both models.

    Args:
        baseline_metrics  : dict from run_baseline()
        finetuned_metrics : dict from evaluate_predictions()
    """
    header = (
        f"\n{'='*60}\n"
        f"MODEL COMPARISON TABLE\n"
        f"{'='*60}\n"
        f"{'Metric':<20} {'Zero-Shot':>12} "
        f"{'Legal-BERT':>12} {'Improvement':>12}\n"
        f"{'-'*60}\n"
    )

    metrics_to_compare = [
        ("Accuracy",     "accuracy"),
        ("F1 Normal",    "f1_normal"),
        ("F1 Coverage",  "f1_coverage"),
        ("F1 Exclusion", "f1_exclusion"),
        ("F1 Condition", "f1_condition"),
        ("F1 Macro",     "f1_macro"),
        ("F1 Weighted",  "f1_weighted"),
    ]

    rows = ""
    for label, key in metrics_to_compare:
        base = baseline_metrics[key]
        fine = finetuned_metrics[key]
        diff = fine - base
        sign = "+" if diff >= 0 else ""
        rows += (
            f"{label:<20} {base:>12.4f} "
            f"{fine:>12.4f} "
            f"{sign}{diff:>11.4f}\n"
        )

    table = header + rows + "=" * 60
    print(table)

    with open(COMPARISON_TABLE, 'w') as f:
        f.write(table)
        f.write("\n\nNOTE FOR PAPER:\n")
        f.write(
            "Fine-tuned Legal-BERT trained on "
            "insurance clause training set.\n"
            "Evaluated on completely unseen test clauses "
            "(document-level split).\n"
            "Baseline uses zero-shot classification "
            "with no training.\n"
        )

    print(f"Comparison saved: {COMPARISON_TABLE}")


# ──────────────────────────────────────────────────────────
# Function 10: run_finetuning  (main entry point)
# ──────────────────────────────────────────────────────────

def run_finetuning(baseline_metrics=None):
    """
    Full Legal-BERT fine-tuning pipeline:
      1. Setup device (GPU if available)
      2. Load train/test data
      3. Load Legal-BERT model and tokenizer
      4. Create DataLoaders
      5. Train for EPOCHS with class-weighted loss
      6. Save best checkpoint after each epoch
      7. Final evaluation on best checkpoint
      8. Save confusion matrix, results, curves
      9. Generate comparison table vs baseline

    Args:
        baseline_metrics : dict from run_baseline() — can be None

    Returns:
        finetuned_metrics dict
    """
    print("=" * 50)
    print("LEGAL-BERT FINE-TUNING")
    print("=" * 50)

    # ── Device setup ─────────────────────────────────────
    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )
    print(f"\nDevice: {device}")
    if device.type == "cpu":
        print("WARNING: No GPU detected.")
        print("Training will be slow on CPU.")
        print("Estimated time: 2–4 hours")
        print("Tip: Use Google Colab free GPU to speed this up.")
    else:
        print("GPU detected. Training will be fast (~15–30 min).")

    # ── Set seed for reproducibility ──────────────────────
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # ── Load data ─────────────────────────────────────────
    train_df, test_df = load_data()

    # ── Load model ────────────────────────────────────────
    tokenizer, model = load_model_and_tokenizer()
    model = model.to(device)

    # ── Data loaders ──────────────────────────────────────
    train_loader, test_loader = create_data_loaders(
        train_df, test_df, tokenizer
    )

    # ── Class-weighted loss ───────────────────────────────
    class_weights = get_class_weights(device)
    criterion = torch.nn.CrossEntropyLoss(weight=class_weights)
    print(f"\nClass weights: {class_weights.cpu().tolist()}")

    # ── Optimizer ─────────────────────────────────────────
    optimizer = AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY
    )

    # ── Learning rate scheduler ───────────────────────────
    total_steps = len(train_loader) * EPOCHS
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=WARMUP_STEPS,
        num_training_steps=total_steps
    )
    print(f"Total training steps: {total_steps}")
    print(f"Warmup steps        : {WARMUP_STEPS}")

    # ── Training loop ─────────────────────────────────────
    train_losses = []
    train_accs   = []
    val_losses   = []
    val_accs     = []
    best_val_acc = 0.0
    best_val_f1  = 0.0
    no_improve   = 0
    PATIENCE     = 3
    from sklearn.metrics import f1_score
    for epoch in range(1, EPOCHS + 1):
        print(f"\nEpoch {epoch}/{EPOCHS}")
        print("-" * 30)

        # Train one epoch
        t_loss, t_acc = train_one_epoch(
            model, train_loader,
            optimizer, scheduler,
            criterion, device
        )

        # Evaluate on test set
        v_loss, v_acc, preds, labels = evaluate_model(
            model, test_loader, criterion, device
        )

        train_losses.append(t_loss)
        train_accs.append(t_acc)
        val_losses.append(v_loss)
        val_accs.append(v_acc)

        print(f"  Train Loss: {t_loss:.4f}  Train Acc: {t_acc:.4f}")
        print(f"  Val Loss  : {v_loss:.4f}  Val Acc  : {v_acc:.4f}")

        # Save best checkpoint
        # if v_acc > best_val_acc:
        #     best_val_acc = v_acc
        #     save_model(model, tokenizer)
        #     print(f"  ✓ Best model saved (Val Acc: {v_acc:.4f})")
        
        val_f1 = f1_score(labels, preds, average='macro')
        print(f"  Val Macro F1 : {val_f1:.4f}  (best: {best_val_f1:.4f})")

        # Save best checkpoint on macro F1, not accuracy
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            no_improve  = 0
            save_model(model, tokenizer)
            print(f"  Best model saved (Val F1: {val_f1:.4f})")
        else:
            no_improve += 1
            print(f"  No improvement ({no_improve}/{PATIENCE})")
            if no_improve >= PATIENCE:
                print(f"  Early stopping at epoch {epoch}")
                break

    # ── Load best saved model for final evaluation ────────
    print("\nLoading best saved model for final evaluation...")
    best_model = AutoModelForSequenceClassification.from_pretrained(
        BERT_MODEL_DIR
    )
    best_model = best_model.to(device)

    # ── Final evaluation ──────────────────────────────────
    _, _, final_preds, final_labels = evaluate_model(
        best_model, test_loader, criterion, device
    )

    # ── Import metric helpers from baseline module ────────
    from src.training.baseline_model import (
        evaluate_predictions,
        save_confusion_matrix,
        save_results
    )

    finetuned_metrics = evaluate_predictions(
        final_labels, final_preds,
        "Legal-BERT Fine-Tuned"
    )

    # ── Save confusion matrix ─────────────────────────────
    save_confusion_matrix(
        final_labels, final_preds,
        FINETUNED_CM_PATH,
        "Confusion Matrix — Legal-BERT Fine-Tuned"
    )

    # ── Save results text file ────────────────────────────
    save_results(finetuned_metrics, FINETUNED_RESULTS)

    # ── Plot training curves ──────────────────────────────
    plot_training_curves(
        train_losses, train_accs,
        val_losses, val_accs
    )

    # ── Comparison table ──────────────────────────────────
    if baseline_metrics:
        generate_comparison_table(baseline_metrics, finetuned_metrics)

    print("\nFine-tuning complete.")
    print(f"Best Val Accuracy : {best_val_acc:.4f}")
    print(f"Final Macro F1    : {finetuned_metrics['f1_macro']:.4f}")
    print(f"Exclusion F1      : {finetuned_metrics['f1_exclusion']:.4f}")

    return finetuned_metrics


# ──────────────────────────────────────────────────────────
# Allow running directly: python src/training/finetune_legal_bert.py
# ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_finetuning(baseline_metrics=None)