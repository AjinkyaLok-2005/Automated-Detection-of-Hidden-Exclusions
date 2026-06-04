# ============================================================
# src/data_pipeline/labeler.py
# Rule-based labeling of insurance clauses into 4 categories
# ============================================================

import os
import sys
import re

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import LABEL_NAMES

# ── Keyword lists per label ───────────────────────────────

EXCLUSION_KEYWORDS = [
    "not covered", "not cover", "excluded", "exclusion",
    "does not apply", "shall not apply", "no coverage",
    "will not pay", "not payable", "not eligible",
    "not included", "not reimbursed", "we do not cover",
    "this policy does not", "not provided", "exception",
    "except for", "will not be covered", "not applicable",
    "no claim", "cannot claim", "outside the scope",
    "not within", "does not include", "not insured",
]

COVERAGE_KEYWORDS = [
    "covered", "coverage", "covers", "will pay",
    "reimbursed", "payable", "benefit", "entitled to",
    "eligible for", "pays for", "hospitalization",
    "day care", "in-patient", "out-patient",
    "sum insured", "sum assured", "we cover",
    "indemnity", "compensation", "insured event",
    "admissible", "claimable", "reimburse",
]

CONDITION_KEYWORDS = [
    "subject to", "provided that", "condition",
    "must notify", "shall notify", "required to",
    "policyholder must", "insured must", "claimant must",
    "within days", "within hours", "prior approval",
    "pre-authorization", "waiting period", "deductible",
    "co-payment", "co-pay", "premium payment",
    "contingent", "in the event of", "provided however",
    "on condition that", "upon the condition",
]

NORMAL_KEYWORDS = [
    "definition", "means", "refers to", "herein",
    "the term", "for the purpose", "this policy",
    "schedule", "endorsement", "policyholder",
    "insured person", "as defined", "hereafter",
    "introduction", "preamble", "recital",
]

# Section label mappings
SECTION_LABEL_MAP = {
    "exclusion_section" : ["exclusion", "not cover",
                            "except", "limitation"],
    "coverage_section"  : ["coverage", "benefit",
                            "cover", "insured"],
    "condition_section" : ["condition", "requirement",
                            "premium", "waiting"],
    "definition_section": ["definition", "meaning",
                            "interpret"],
    "waiting_section"   : ["waiting", "period"],
    "general_section"   : [],
}


def label_clause(text):
    """
    Assign label to a single clause using keyword matching.

    Priority: Exclusion > Condition > Coverage > Normal

    Args:
        text : clause text string

    Returns:
        int: 0=Normal, 1=Coverage, 2=Exclusion, 3=Condition
    """
    t = text.lower()

    # Count hits per category
    excl_hits = sum(1 for kw in EXCLUSION_KEYWORDS if kw in t)
    cov_hits  = sum(1 for kw in COVERAGE_KEYWORDS  if kw in t)
    cond_hits = sum(1 for kw in CONDITION_KEYWORDS if kw in t)

    # Exclusion takes highest priority
    if excl_hits > 0:
        return 2

    # Condition — needs 2+ hits or 1 hit with no coverage
    if cond_hits >= 2 or (cond_hits > 0 and cov_hits == 0):
        return 3

    # Coverage
    if cov_hits > 0:
        return 1

    # Default: Normal
    return 0


def heading_to_section_label(heading):
    """
    Convert a section heading string to a section_label key.

    Args:
        heading : section heading string

    Returns:
        section_label string
    """
    h = heading.lower()

    for section_label, keywords in SECTION_LABEL_MAP.items():
        if any(kw in h for kw in keywords):
            return section_label

    return "general_section"


def label_all_clauses(clauses):
    """
    Label all clauses. Adds label, section_label,
    and clause_id to each clause dict.

    Args:
        clauses : list of clause dicts from segmentor

    Returns:
        same list with label fields added
    """
    labeled       = []
    label_counts  = {0: 0, 1: 0, 2: 0, 3: 0}

    for idx, clause in enumerate(clauses):
        text    = clause.get('clause_text', '')
        heading = clause.get('section_heading', '')

        label = label_clause(text)

        clause['label']         = label
        clause['clause_id']     = idx + 1
        clause['section_label'] = heading_to_section_label(
            heading)

        labeled.append(clause)
        label_counts[label] += 1

    # Print distribution
    total = len(labeled)
    print("\nLabel distribution after labeling:")
    for label_id, name in LABEL_NAMES.items():
        cnt = label_counts[label_id]
        pct = cnt / total * 100 if total > 0 else 0
        print(f"  {name:<12}: {cnt:>5}  ({pct:.1f}%)")

    return labeled
