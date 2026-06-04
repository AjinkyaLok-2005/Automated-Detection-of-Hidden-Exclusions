# ============================================================
# src/inference/semantic_matcher.py
# Week 4 — Semantic Topic Matching
#
# Purpose:
#   Find Coverage-Exclusion clause pairs that discuss the
#   same topic using sentence embeddings and cosine similarity.
#   These pairs are candidates for NLI contradiction detection.
#
# Input  : classified clauses (list of dicts or DataFrame)
# Output : matched_pairs.csv saved to outputs/hidden_conditions/
# ============================================================

import os
import sys
import numpy as np
import pandas as pd
from itertools import product

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    SIMILARITY_MODEL, SIMILARITY_THRESHOLD,
    HIDDEN_COND_DIR, LABEL_NAMES
)

# Output path
MATCHED_PAIRS_PATH = os.path.join(
    HIDDEN_COND_DIR, "matched_pairs.csv")


# ── Model loader ─────────────────────────────────────────

def load_sentence_model():
    """
    Load sentence-transformers model for clause embeddings.
    Downloads on first call, cached afterwards.
    """
    try:
        from sentence_transformers import SentenceTransformer
        print(f"Loading sentence model: {SIMILARITY_MODEL}")
        model = SentenceTransformer(SIMILARITY_MODEL)
        print("Sentence model loaded.")
        return model
    except ImportError:
        raise ImportError(
            "Install sentence-transformers:\n"
            "pip install sentence-transformers"
        )


# ── Embedding helpers ─────────────────────────────────────

def get_embeddings(texts, model, batch_size=64):
    """
    Encode a list of texts into embedding vectors.

    Args:
        texts      : list of strings
        model      : SentenceTransformer model
        batch_size : encoding batch size

    Returns:
        numpy array of shape (len(texts), embedding_dim)
    """
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 100,
        convert_to_numpy=True
    )
    return embeddings


def cosine_similarity_matrix(emb_a, emb_b):
    """
    Compute cosine similarity between every pair in emb_a x emb_b.

    Returns:
        matrix of shape (len(emb_a), len(emb_b))
    """
    # L2 normalise
    norm_a = emb_a / (np.linalg.norm(emb_a, axis=1, keepdims=True) + 1e-10)
    norm_b = emb_b / (np.linalg.norm(emb_b, axis=1, keepdims=True) + 1e-10)
    return norm_a @ norm_b.T


# ── Main matching function ────────────────────────────────

def find_matched_pairs(classified_clauses, model=None,
                       threshold=None, source_filter=None):
    """
    Find all Coverage-Exclusion clause pairs above the
    similarity threshold. These are same-topic pairs where
    an exclusion may contradict a coverage promise.

    Args:
        classified_clauses : list of dicts, each must have:
                             clause_text, label_id, source_file
                             (output of nli_engine.classify_clauses
                              or a DataFrame row)
        model              : SentenceTransformer (loaded if None)
        threshold          : cosine similarity cutoff (default from config)
        source_filter      : if set, only match within same source_file

    Returns:
        DataFrame of matched pairs with columns:
            coverage_text, exclusion_text,
            coverage_source, exclusion_source,
            similarity_score, same_document
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD

    if model is None:
        model = load_sentence_model()

    # Separate coverage and exclusion clauses
    coverage_clauses  = [c for c in classified_clauses
                         if c.get('label_id') == 1]
    exclusion_clauses = [c for c in classified_clauses
                         if c.get('label_id') == 2]

    print(f"\nSemantic Matching:")
    print(f"  Coverage clauses  : {len(coverage_clauses)}")
    print(f"  Exclusion clauses : {len(exclusion_clauses)}")
    print(f"  Similarity threshold: {threshold}")

    if not coverage_clauses or not exclusion_clauses:
        print("  WARNING: Need both Coverage and Exclusion clauses.")
        return pd.DataFrame()

    # Get texts
    cov_texts = [c['clause_text'] for c in coverage_clauses]
    exc_texts = [c['clause_text'] for c in exclusion_clauses]

    # Compute embeddings
    print("  Computing coverage embeddings...")
    cov_emb = get_embeddings(cov_texts, model)
    print("  Computing exclusion embeddings...")
    exc_emb = get_embeddings(exc_texts, model)

    # Compute similarity matrix
    print("  Computing similarity matrix...")
    sim_matrix = cosine_similarity_matrix(cov_emb, exc_emb)

    # Find pairs above threshold
    pairs = []
    cov_idx, exc_idx = np.where(sim_matrix >= threshold)

    print(f"  Pairs above threshold: {len(cov_idx)}")

    for ci, ei in zip(cov_idx, exc_idx):
        cov = coverage_clauses[ci]
        exc = exclusion_clauses[ei]
        score = float(sim_matrix[ci, ei])

        same_doc = (
            cov.get('source_file', '') ==
            exc.get('source_file', '')
        )

        # If source_filter is set, only keep same-document pairs
        if source_filter and not same_doc:
            continue

        pairs.append({
            'coverage_text'    : cov['clause_text'],
            'exclusion_text'   : exc['clause_text'],
            'coverage_source'  : cov.get('source_file', ''),
            'exclusion_source' : exc.get('source_file', ''),
            'coverage_page'    : cov.get('page_number', 0),
            'exclusion_page'   : exc.get('page_number', 0),
            'similarity_score' : round(score, 4),
            'same_document'    : same_doc,
        })

    if not pairs:
        print("  No pairs found above threshold.")
        return pd.DataFrame()

    pairs_df = pd.DataFrame(pairs)

    # Sort by similarity descending
    pairs_df = pairs_df.sort_values(
        'similarity_score', ascending=False
    ).reset_index(drop=True)

    print(f"\n  Total matched pairs   : {len(pairs_df)}")
    print(f"  Same-document pairs   : {pairs_df['same_document'].sum()}")
    print(f"  Cross-document pairs  : {(~pairs_df['same_document']).sum()}")
    print(f"  Avg similarity score  : {pairs_df['similarity_score'].mean():.4f}")

    return pairs_df


# ── CSV output ────────────────────────────────────────────

def save_matched_pairs(pairs_df, save_path=None):
    """
    Save matched pairs DataFrame to CSV.

    Args:
        pairs_df  : DataFrame from find_matched_pairs()
        save_path : output path (default: MATCHED_PAIRS_PATH)
    """
    if save_path is None:
        save_path = MATCHED_PAIRS_PATH

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    pairs_df.to_csv(save_path, index=False, encoding='utf-8-sig')
    print(f"  Matched pairs saved: {save_path}")
    return save_path


# ── Policy comparison helper ──────────────────────────────

def compare_two_policies(clauses_a, clauses_b,
                         model=None, threshold=None):
    """
    Find clauses in policy B that have no similar match in A.
    These are clauses unique to B — potential hidden additions
    not present in the comparison policy.

    Args:
        clauses_a  : list of clause dicts from policy A
        clauses_b  : list of clause dicts from policy B
        model      : SentenceTransformer
        threshold  : similarity cutoff

    Returns:
        list of dicts — clauses in B with no match in A
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD
    if model is None:
        model = load_sentence_model()

    texts_a = [c['clause_text'] for c in clauses_a]
    texts_b = [c['clause_text'] for c in clauses_b]

    emb_a = get_embeddings(texts_a, model)
    emb_b = get_embeddings(texts_b, model)

    sim = cosine_similarity_matrix(emb_b, emb_a)
    max_scores = sim.max(axis=1)

    unique_in_b = []
    for i, score in enumerate(max_scores):
        if score < threshold:
            unique_in_b.append({
                'clause_text'      : clauses_b[i]['clause_text'],
                'label_id'         : clauses_b[i].get('label_id', -1),
                'label_name'       : LABEL_NAMES.get(
                    clauses_b[i].get('label_id', -1), 'Unknown'),
                'source_file'      : clauses_b[i].get('source_file', ''),
                'best_match_score' : round(float(score), 4),
                'note'             : 'No similar clause in policy A'
            })

    print(f"Clauses unique to policy B: {len(unique_in_b)}")
    return unique_in_b


# ── Summary printer ───────────────────────────────────────

def print_matching_summary(pairs_df):
    """Print a readable summary of matched pairs."""
    if pairs_df.empty:
        print("No matched pairs to summarise.")
        return

    print(f"\n{'='*56}")
    print("SEMANTIC MATCHING SUMMARY")
    print(f"{'='*56}")
    print(f"Total pairs found    : {len(pairs_df)}")
    print(f"Same-document pairs  : {pairs_df['same_document'].sum()}")
    print(f"Avg similarity score : {pairs_df['similarity_score'].mean():.4f}")
    print(f"Max similarity score : {pairs_df['similarity_score'].max():.4f}")
    print(f"\nTop 5 highest-similarity pairs:")
    print("-" * 56)

    for _, row in pairs_df.head(5).iterrows():
        print(f"\n  Similarity : {row['similarity_score']:.4f}"
              f"  Same doc: {row['same_document']}")
        cov = row['coverage_text']
        exc = row['exclusion_text']
        print(f"  Coverage  : {cov[:100]}{'...' if len(cov)>100 else ''}")
        print(f"  Exclusion : {exc[:100]}{'...' if len(exc)>100 else ''}")

    print(f"\n{'='*56}")


# ── Standalone runner ─────────────────────────────────────

def run_semantic_matching(classified_clauses,
                          model=None,
                          save=True,
                          same_doc_only=False):
    """
    Full semantic matching pipeline.

    Args:
        classified_clauses : list of clause dicts
        model              : SentenceTransformer (loaded if None)
        save               : save matched_pairs.csv
        same_doc_only      : only match within same PDF

    Returns:
        pairs_df, model
    """
    print("=" * 56)
    print("WEEK 4 — SEMANTIC MATCHING")
    print("=" * 56)

    if model is None:
        model = load_sentence_model()

    source_filter = same_doc_only or None

    pairs_df = find_matched_pairs(
        classified_clauses,
        model=model,
        source_filter=source_filter
    )

    if not pairs_df.empty:
        print_matching_summary(pairs_df)
        if save:
            save_matched_pairs(pairs_df)

    return pairs_df, model
