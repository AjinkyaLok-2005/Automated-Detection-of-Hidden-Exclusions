# ============================================================
# src/inference/nli_engine.py
# Week 4 — NLI Contradiction Detection
#
# Purpose:
#   Two responsibilities:
#   1. classify_pdf()      — classify clauses in a new PDF
#                            using the fine-tuned Legal-BERT
#   2. run_nli_on_pairs()  — detect contradictions between
#                            Coverage-Exclusion pairs using
#                            cross-encoder/nli-roberta-base
#
# NLI Logic:
#   Coverage clause  = Premise   (what policy promises)
#   Exclusion clause = Hypothesis (what policy takes away)
#   If NLI output = Contradiction → hidden risk detected
#
# Output:
#   nli_results.csv saved to outputs/hidden_conditions/
# ============================================================

import os
import sys
import torch
import numpy as np
import pandas as pd
from collections import Counter

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    BERT_MODEL_DIR, MAX_LENGTH,
    LABEL_NAMES, NLI_MODEL,
    HIDDEN_COND_DIR
)

# Output path
NLI_RESULTS_PATH = os.path.join(
    HIDDEN_COND_DIR, "nli_results.csv")

# NLI label mapping from cross-encoder output
# cross-encoder/nli-roberta-base outputs: contradiction=0, neutral=1, entailment=2
NLI_LABEL_MAP = {
    0: "Contradiction",
    1: "Neutral",
    2: "Entailment"
}


# ── Legal-BERT clause classifier ─────────────────────────

def load_finetuned_model():
    """
    Load saved Legal-BERT classifier and tokenizer.
    Used for classifying clauses in new PDFs.
    """
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification
    )

    if not os.path.exists(BERT_MODEL_DIR):
        raise FileNotFoundError(
            f"No trained model found at: {BERT_MODEL_DIR}\n"
            f"Run Week 3 training first."
        )

    print(f"Loading fine-tuned model: {BERT_MODEL_DIR}")
    tokenizer = AutoTokenizer.from_pretrained(BERT_MODEL_DIR)
    model     = AutoModelForSequenceClassification\
        .from_pretrained(BERT_MODEL_DIR)
    model.eval()

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu")
    model  = model.to(device)

    print(f"Model loaded on: {device}")
    return tokenizer, model, device


def classify_clauses(clause_texts, tokenizer,
                     model, device, batch_size=32):
    """
    Classify a list of clause strings using Legal-BERT.

    Args:
        clause_texts : list of strings
        tokenizer    : Legal-BERT tokenizer
        model        : fine-tuned classification model
        device       : torch device
        batch_size   : inference batch size

    Returns:
        list of dicts with label_id, label_name, confidence,
        per-class probabilities
    """
    results = []

    for i in range(0, len(clause_texts), batch_size):
        batch = clause_texts[i: i + batch_size]

        enc = tokenizer(
            batch,
            max_length=MAX_LENGTH,
            padding=True,
            truncation=True,
            return_tensors='pt'
        )

        ids  = enc['input_ids'].to(device)
        mask = enc['attention_mask'].to(device)

        with torch.no_grad():
            logits = model(
                input_ids=ids,
                attention_mask=mask
            ).logits

        probs = torch.softmax(logits, dim=1).cpu().numpy()
        preds = logits.argmax(dim=1).cpu().numpy()

        for j in range(len(batch)):
            pred = int(preds[j])
            results.append({
                'clause_text'     : batch[j],
                'label_id'        : pred,
                'label_name'      : LABEL_NAMES[pred],
                'confidence'      : round(float(probs[j][pred]), 4),
                'prob_normal'     : round(float(probs[j][0]), 4),
                'prob_coverage'   : round(float(probs[j][1]), 4),
                'prob_exclusion'  : round(float(probs[j][2]), 4),
                'prob_condition'  : round(float(probs[j][3]), 4),
            })

    return results


def classify_pdf(pdf_path, source_file=None):
    """
    Extract clauses from a PDF and classify each one.

    Args:
        pdf_path    : path to insurance PDF file
        source_file : override filename label (optional)

    Returns:
        list of classified clause dicts
    """
    from src.data_pipeline.pdf_extractor import extract_text_from_pdf
    from src.data_pipeline.segmentor     import segment_text

    fname = source_file or os.path.basename(pdf_path)
    print(f"\nClassifying PDF: {fname}")

    text    = extract_text_from_pdf(pdf_path)
    clauses = segment_text(text, source_file=fname)

    clause_texts = [c['clause_text'] for c in clauses]
    print(f"  Extracted {len(clause_texts)} clauses")

    tokenizer, model, device = load_finetuned_model()
    classified = classify_clauses(
        clause_texts, tokenizer, model, device)

    # Merge segmentor metadata with predictions
    for i, r in enumerate(classified):
        if i < len(clauses):
            r['source_file']      = clauses[i].get(
                'source_file', fname)
            r['section_heading']  = clauses[i].get(
                'section_heading', '')
            r['page_number']      = clauses[i].get(
                'page_number', 0)

    # Print distribution
    dist = Counter(r['label_name'] for r in classified)
    print("  Classification summary:")
    for label, count in sorted(dist.items()):
        pct = count / len(classified) * 100
        print(f"    {label:<12}: {count:>4}  ({pct:.1f}%)")

    return classified


# ── NLI cross-encoder ─────────────────────────────────────

def load_nli_model():
    """
    Load cross-encoder NLI model for contradiction detection.
    cross-encoder/nli-roberta-base outputs scores for:
      [contradiction, neutral, entailment]
    """
    try:
        from sentence_transformers import CrossEncoder
        print(f"Loading NLI model: {NLI_MODEL}")
        nli_model = CrossEncoder(
            NLI_MODEL,
            num_labels=3,
            max_length=512
        )
        print("NLI model loaded.")
        return nli_model
    except ImportError:
        raise ImportError(
            "Install sentence-transformers:\n"
            "pip install sentence-transformers"
        )


def run_nli_on_pairs(pairs_df, nli_model=None,
                     batch_size=32):
    """
    Run NLI inference on Coverage-Exclusion pairs.

    For each pair:
      Premise    = Coverage clause (what policy promises)
      Hypothesis = Exclusion clause (what policy restricts)

    NLI verdict:
      Contradiction → exclusion directly contradicts coverage
                      → HIGH RISK hidden condition
      Neutral       → exclusion is on a different sub-topic
                      → worth reviewing
      Entailment    → exclusion is consistent with coverage
                      → normal policy structure

    Args:
        pairs_df   : DataFrame from semantic_matcher
        nli_model  : CrossEncoder (loaded if None)
        batch_size : NLI inference batch size

    Returns:
        DataFrame with NLI columns added
    """
    if pairs_df.empty:
        print("No pairs to run NLI on.")
        return pairs_df

    if nli_model is None:
        nli_model = load_nli_model()

    print(f"\nRunning NLI on {len(pairs_df)} pairs...")
    print(f"  Model: {NLI_MODEL}")
    print(f"  Batch size: {batch_size}")

    # Build sentence pairs: (premise, hypothesis)
    sentence_pairs = list(zip(
        pairs_df['coverage_text'].tolist(),
        pairs_df['exclusion_text'].tolist()
    ))

    # Run inference in batches
    all_scores = []
    for i in range(0, len(sentence_pairs), batch_size):
        batch = sentence_pairs[i: i + batch_size]
        scores = nli_model.predict(
            batch,
            apply_softmax=True,
            show_progress_bar=False
        )
        all_scores.extend(scores)

        if (i // batch_size) % 5 == 0:
            done = min(i + batch_size, len(sentence_pairs))
            print(f"  Progress: {done}/{len(sentence_pairs)}")

    # Parse results
    all_scores = np.array(all_scores)  # shape: (n, 3)

    # cross-encoder/nli-roberta-base order:
    # index 0 = contradiction, 1 = neutral, 2 = entailment
    contradiction_scores = all_scores[:, 0]
    neutral_scores       = all_scores[:, 1]
    entailment_scores    = all_scores[:, 2]
    predicted_labels     = all_scores.argmax(axis=1)

    results_df = pairs_df.copy()
    results_df['nli_verdict']           = [
        NLI_LABEL_MAP[int(l)] for l in predicted_labels]
    results_df['contradiction_score']   = np.round(
        contradiction_scores, 4)
    results_df['neutral_score']         = np.round(
        neutral_scores, 4)
    results_df['entailment_score']      = np.round(
        entailment_scores, 4)
    results_df['is_contradiction']      = (
        results_df['nli_verdict'] == 'Contradiction')

    # Print verdict distribution
    verdict_counts = results_df['nli_verdict'].value_counts()
    print(f"\n  NLI verdict distribution:")
    for verdict, count in verdict_counts.items():
        pct = count / len(results_df) * 100
        print(f"    {verdict:<15}: {count:>4}  ({pct:.1f}%)")

    contradictions = results_df['is_contradiction'].sum()
    print(f"\n  Contradictions found: {contradictions}")
    print(f"  ({contradictions/len(results_df)*100:.1f}% of pairs)")

    return results_df


# ── Save NLI results ──────────────────────────────────────

def save_nli_results(results_df, save_path=None):
    """
    Save NLI results DataFrame to CSV.

    Args:
        results_df : DataFrame from run_nli_on_pairs()
        save_path  : output path (default: NLI_RESULTS_PATH)
    """
    if save_path is None:
        save_path = NLI_RESULTS_PATH

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    results_df.to_csv(
        save_path, index=False, encoding='utf-8-sig')
    print(f"  NLI results saved: {save_path}")
    return save_path


# ── Summary printer ───────────────────────────────────────

def print_nli_summary(results_df):
    """Print a readable NLI results summary."""
    if results_df.empty:
        print("No NLI results to summarise.")
        return

    contradictions = results_df[results_df['is_contradiction']]

    print(f"\n{'='*60}")
    print("NLI CONTRADICTION DETECTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total pairs analysed  : {len(results_df)}")
    print(f"Contradictions found  : {len(contradictions)}")
    print(f"Neutral pairs         : "
          f"{(results_df['nli_verdict']=='Neutral').sum()}")
    print(f"Entailment pairs      : "
          f"{(results_df['nli_verdict']=='Entailment').sum()}")

    if not contradictions.empty:
        print(f"\nTop 5 highest-confidence contradictions:")
        print("-" * 60)
        top = contradictions.nlargest(
            5, 'contradiction_score')
        for _, row in top.iterrows():
            print(f"\n  Similarity   : {row['similarity_score']:.4f}"
                  f"  Contradiction score: {row['contradiction_score']:.4f}")
            print(f"  Same document: {row['same_document']}")
            cov = row['coverage_text']
            exc = row['exclusion_text']
            print(f"  Coverage  : "
                  f"{cov[:110]}{'...' if len(cov)>110 else ''}")
            print(f"  Exclusion : "
                  f"{exc[:110]}{'...' if len(exc)>110 else ''}")

    print(f"\n{'='*60}")


# ── Full Week 4 NLI pipeline ──────────────────────────────

def run_nli_pipeline(pairs_df, nli_model=None, save=True):
    """
    Run the full NLI pipeline on matched pairs.

    Args:
        pairs_df  : DataFrame from semantic_matcher
        nli_model : CrossEncoder (loaded if None)
        save      : save nli_results.csv

    Returns:
        results_df with NLI columns, nli_model
    """
    print("=" * 60)
    print("WEEK 4 — NLI CONTRADICTION DETECTION")
    print("=" * 60)

    if nli_model is None:
        nli_model = load_nli_model()

    results_df = run_nli_on_pairs(pairs_df, nli_model)

    if not results_df.empty:
        print_nli_summary(results_df)
        if save:
            save_nli_results(results_df)

    return results_df, nli_model
