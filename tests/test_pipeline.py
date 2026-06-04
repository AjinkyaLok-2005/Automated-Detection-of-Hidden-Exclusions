# ============================================================
# src/pdf_processing/pdf_highlighter.py
# Week 6 — PDF Clause Highlighting
#
# Purpose:
#   Take a PDF and a list of classified clauses, then
#   produce a highlighted version where each clause is
#   colour-coded by its risk label:
#
#     Normal      → no highlight (clean)
#     Coverage    → green  (#00C853)
#     Exclusion   → red    (#D32F2F)
#     Condition   → orange (#FF6F00)
#     Contradiction → purple (#7B1FA2) — highest risk
#
# Uses PyMuPDF (fitz) for PDF annotation.
# ============================================================

import os
import sys
import fitz          # PyMuPDF
from pathlib import Path

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from config import LABEL_NAMES

# ── Highlight colours (RGB 0–1 floats for PyMuPDF) ───────

HIGHLIGHT_COLORS = {
    0: None,                          # Normal — no highlight
    1: (0.00, 0.78, 0.33),           # Coverage  — green
    2: (0.83, 0.18, 0.18),           # Exclusion — red
    3: (1.00, 0.44, 0.00),           # Condition — orange
    'contradiction': (0.48, 0.11, 0.64),  # Contradiction — purple
}

# Opacity for highlights (0=transparent, 1=solid)
HIGHLIGHT_OPACITY = 0.35

# Tooltip prefix per label
LABEL_TOOLTIPS = {
    0: 'Normal clause',
    1: 'Coverage clause — what policy covers',
    2: 'EXCLUSION — not covered',
    3: 'Condition — requirement on policyholder',
    'contradiction': 'HIDDEN RISK — contradiction detected',
}


# ── Core highlighting function ────────────────────────────

def highlight_pdf(input_pdf_path,
                  classified_clauses,
                  contradiction_texts=None,
                  output_path=None):
    """
    Produce a highlighted copy of the PDF where clauses
    are colour-coded by risk label.

    Args:
        input_pdf_path      : path to original PDF
        classified_clauses  : list of clause dicts with
                              clause_text, label_id,
                              confidence
        contradiction_texts : set of clause texts that
                              are NLI contradictions
                              (highlighted purple)
        output_path         : where to save highlighted PDF
                              (default: {name}_highlighted.pdf)

    Returns:
        output_path (str)
    """
    if contradiction_texts is None:
        contradiction_texts = set()

    # Default output path
    if output_path is None:
        stem       = Path(input_pdf_path).stem
        parent     = Path(input_pdf_path).parent
        output_path = str(parent / f"{stem}_highlighted.pdf")

    doc = fitz.open(input_pdf_path)

    # Build lookup: text snippet → label_id
    # Use first 80 chars as key to handle partial matches
    text_to_label = {}
    text_to_conf  = {}
    for clause in classified_clauses:
        text = clause.get('clause_text', '').strip()
        key  = text[:80].lower()
        text_to_label[key] = clause.get('label_id', 0)
        text_to_conf[key]  = clause.get('confidence', 1.0)

    # Track which clauses were actually found in PDF
    highlighted_count = {0: 0, 1: 0, 2: 0, 3: 0,
                         'contradiction': 0}

    for page_num, page in enumerate(doc):
        page_text = page.get_text("blocks")

        for block in page_text:
            if len(block) < 5:
                continue

            block_text = block[4].strip()
            if not block_text or len(block_text) < 10:
                continue

            block_key = block_text[:80].lower()

            # Determine label — check contradiction first
            is_contradiction = any(
                ct[:80].lower() in block_key or
                block_key in ct[:80].lower()
                for ct in contradiction_texts
                if len(ct) > 10
            )

            label_id = text_to_label.get(block_key, None)

            # Fuzzy match — check if block is a substring
            if label_id is None:
                for key, lid in text_to_label.items():
                    if (key in block_key or
                            block_key in key):
                        label_id = lid
                        break

            # Skip Normal or unmatched blocks
            if label_id is None or label_id == 0:
                continue

            # Choose colour
            if is_contradiction:
                color   = HIGHLIGHT_COLORS['contradiction']
                tooltip = LABEL_TOOLTIPS['contradiction']
                highlighted_count['contradiction'] += 1
            else:
                color   = HIGHLIGHT_COLORS.get(label_id)
                tooltip = LABEL_TOOLTIPS.get(
                    label_id, LABEL_NAMES.get(label_id, ''))
                if color is None:
                    continue
                highlighted_count[label_id] += 1

            # Search for text on page and highlight
            rects = page.search_for(
                block_text[:60], quads=False)

            for rect in rects:
                # Add highlight annotation
                highlight = page.add_highlight_annot(rect)
                highlight.set_colors(
                    stroke=color)
                highlight.set_opacity(HIGHLIGHT_OPACITY)
                highlight.set_info(
                    title=tooltip,
                    content=(
                        f"Label: "
                        f"{LABEL_NAMES.get(label_id, '?')}\n"
                        f"Confidence: "
                        f"{text_to_conf.get(block_key, 0):.3f}"
                    )
                )
                highlight.update()

    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    total = sum(highlighted_count.values())
    print(f"  Highlighted {total} text regions:")
    for label_id, count in highlighted_count.items():
        if count > 0:
            name = (LABEL_NAMES.get(label_id, 'Contradiction')
                    if label_id != 'contradiction'
                    else 'Contradiction')
            print(f"    {name:<15}: {count}")
    print(f"  Saved: {output_path}")

    return output_path, highlighted_count


def add_legend_page(pdf_path):
    """
    Add a colour legend as the first page of the PDF.

    Args:
        pdf_path : path to already-highlighted PDF
    """
    doc  = fitz.open(pdf_path)
    page = doc.new_page(pno=0, width=595, height=200)

    # Title
    page.insert_text(
        (40, 40),
        "Insurance Policy Risk Analysis — Colour Legend",
        fontsize=14, fontname="helv",
        color=(0.1, 0.1, 0.1)
    )

    legend_items = [
        ((0.00, 0.78, 0.33), "Coverage clause",
         "What the policy covers and pays for"),
        ((0.83, 0.18, 0.18), "Exclusion clause",
         "What is NOT covered — read carefully"),
        ((1.00, 0.44, 0.00), "Condition clause",
         "Requirements the policyholder must meet"),
        ((0.48, 0.11, 0.64), "Contradiction (Hidden Risk)",
         "Coverage promise contradicted by exclusion"),
    ]

    y = 70
    for color, label, description in legend_items:
        # Colour swatch
        rect = fitz.Rect(40, y, 70, y + 18)
        page.draw_rect(rect, color=color,
                       fill=color, fill_opacity=0.5)
        # Label
        page.insert_text(
            (78, y + 13), f"{label}",
            fontsize=11, fontname="helv-b",
            color=(0.1, 0.1, 0.1)
        )
        # Description
        page.insert_text(
            (78, y + 26), description,
            fontsize=9, fontname="helv",
            color=(0.4, 0.4, 0.4)
        )
        y += 44

    doc.save(pdf_path, garbage=4, deflate=True,
             incremental=False)
    doc.close()
    print("  Legend page added.")


def create_highlighted_pdf(input_pdf_path,
                           classified_clauses,
                           nli_results_df=None,
                           output_dir=None):
    """
    Full pipeline: highlight PDF and add legend page.

    Args:
        input_pdf_path     : original PDF
        classified_clauses : list of clause dicts
        nli_results_df     : DataFrame from nli_engine
                             (used to mark contradictions)
        output_dir         : where to save output

    Returns:
        output_path (str), highlighted_count (dict)
    """
    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', 'outputs', 'highlighted_pdfs')

    os.makedirs(output_dir, exist_ok=True)

    stem        = Path(input_pdf_path).stem
    output_path = os.path.join(
        output_dir, f"{stem}_highlighted.pdf")

    # Extract contradiction texts for purple highlighting
    contradiction_texts = set()
    if nli_results_df is not None and not nli_results_df.empty:
        contradictions = nli_results_df[
            nli_results_df['is_contradiction'] == True
        ]
        contradiction_texts = (
            set(contradictions['coverage_text'].tolist()) |
            set(contradictions['exclusion_text'].tolist())
        )
        print(f"  Contradiction texts to highlight: "
              f"{len(contradiction_texts)}")

    # Highlight
    output_path, highlighted_count = highlight_pdf(
        input_pdf_path,
        classified_clauses,
        contradiction_texts=contradiction_texts,
        output_path=output_path
    )

    # Add legend
    add_legend_page(output_path)

    return output_path, highlighted_count
