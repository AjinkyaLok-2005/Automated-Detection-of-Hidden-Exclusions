# ============================================================
# src/pdf_processing/pdf_highlighter.py
# Week 6 — PDF Clause Highlighting (FIXED VERSION)
# ============================================================

import os
import sys
import fitz  # PyMuPDF
from pathlib import Path

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from config import LABEL_NAMES


# ── Highlight colours ───────────────────────────────────────

HIGHLIGHT_COLORS = {
    0: None,
    1: (0.00, 0.78, 0.33),           # Coverage
    2: (0.83, 0.18, 0.18),           # Exclusion
    3: (1.00, 0.44, 0.00),           # Condition
    'contradiction': (0.48, 0.11, 0.64),
}

HIGHLIGHT_OPACITY = 0.35

LABEL_TOOLTIPS = {
    0: 'Normal clause',
    1: 'Coverage clause — what policy covers',
    2: 'EXCLUSION — not covered',
    3: 'Condition — requirement on policyholder',
    'contradiction': 'HIDDEN RISK — contradiction detected',
}


# ── Highlight PDF ──────────────────────────────────────────

def highlight_pdf(input_pdf_path,
                  classified_clauses,
                  contradiction_texts=None,
                  output_path=None):

    if contradiction_texts is None:
        contradiction_texts = set()

    if output_path is None:
        stem = Path(input_pdf_path).stem
        parent = Path(input_pdf_path).parent
        output_path = str(parent / f"{stem}_highlighted.pdf")

    doc = fitz.open(input_pdf_path)

    # Handle encrypted PDFs
    if doc.is_encrypted:
        doc.authenticate("")

    text_to_label = {}
    text_to_conf = {}

    for clause in classified_clauses:
        text = clause.get('clause_text', '').strip()
        key = text[:80].lower()
        text_to_label[key] = clause.get('label_id', 0)
        text_to_conf[key] = clause.get('confidence', 1.0)

    highlighted_count = {0: 0, 1: 0, 2: 0, 3: 0, 'contradiction': 0}

    for page in doc:
        blocks = page.get_text("blocks")

        for block in blocks:
            if len(block) < 5:
                continue

            block_text = block[4].strip()
            if not block_text or len(block_text) < 10:
                continue

            block_key = block_text[:80].lower()

            # Check contradiction
            is_contradiction = any(
                ct[:80].lower() in block_key or block_key in ct[:80].lower()
                for ct in contradiction_texts if len(ct) > 10
            )

            label_id = text_to_label.get(block_key)

            # Fuzzy match
            if label_id is None:
                for key, lid in text_to_label.items():
                    if key in block_key or block_key in key:
                        label_id = lid
                        break

            if label_id is None or label_id == 0:
                continue

            # Choose color
            if is_contradiction:
                color = HIGHLIGHT_COLORS['contradiction']
                tooltip = LABEL_TOOLTIPS['contradiction']
                highlighted_count['contradiction'] += 1
            else:
                color = HIGHLIGHT_COLORS.get(label_id)
                tooltip = LABEL_TOOLTIPS.get(label_id, '')
                if color is None:
                    continue
                highlighted_count[label_id] += 1

            rects = page.search_for(block_text[:60])

            for rect in rects:
                annot = page.add_highlight_annot(rect)
                annot.set_colors(stroke=color)
                annot.set_opacity(HIGHLIGHT_OPACITY)
                annot.set_info(
                    title=tooltip,
                    content=f"Label: {LABEL_NAMES.get(label_id, '?')}\n"
                            f"Confidence: {text_to_conf.get(block_key, 0):.3f}"
                )
                annot.update()

    # Save safely
    doc.save(output_path, garbage=4, deflate=True)
    doc.close()

    total = sum(highlighted_count.values())
    print(f"  Highlighted {total} regions")
    print(f"  Saved: {output_path}")

    return output_path, highlighted_count


# ── Add Legend Page (FIXED) ────────────────────────────────

def add_legend_page(pdf_path):
    doc = fitz.open(pdf_path)

    if doc.is_encrypted:
        doc.authenticate("")

    page = doc.new_page(pno=0, width=595, height=200)

    page.insert_textbox(
        fitz.Rect(40, 30, 500, 55),
        "Insurance Policy Risk Analysis — Colour Legend",
        fontsize=14,
        color=(0.1, 0.1, 0.1)
    )

    legend_items = [
        ((0.00, 0.78, 0.33), "Coverage clause", "What the policy covers"),
        ((0.83, 0.18, 0.18), "Exclusion clause", "Not covered"),
        ((1.00, 0.44, 0.00), "Condition clause", "Requirements"),
        ((0.48, 0.11, 0.64), "Contradiction", "Hidden risk"),
    ]

    y = 70
    for color, label, desc in legend_items:
        rect = fitz.Rect(40, y, 70, y + 18)
        page.draw_rect(rect, color=color, fill=color, fill_opacity=0.5)

        page.insert_textbox(
            fitz.Rect(80, y, 300, y + 20),
            label,
            fontsize=11
        )

        page.insert_textbox(
            fitz.Rect(80, y + 15, 400, y + 35),
            desc,
            fontsize=9,
            color=(0.4, 0.4, 0.4)
        )

        y += 40

    # ✅ SAFE SAVE (NO incremental)
    final_path = pdf_path.replace(".pdf", "_final.pdf")
    doc.save(final_path, deflate=True)
    doc.close()

    print("  Legend page added.")
    print(f"  Final file: {final_path}")

    return final_path


# ── Full Pipeline ──────────────────────────────────────────

def create_highlighted_pdf(input_pdf_path,
                           classified_clauses,
                           nli_results_df=None,
                           output_dir=None):

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', '..', 'outputs', 'highlighted_pdfs'
        )

    os.makedirs(output_dir, exist_ok=True)

    stem = Path(input_pdf_path).stem
    output_path = os.path.join(output_dir, f"{stem}_highlighted.pdf")

    contradiction_texts = set()

    if nli_results_df is not None and not nli_results_df.empty:
        contradictions = nli_results_df[
            nli_results_df['is_contradiction'] == True
        ]

        contradiction_texts = (
            set(contradictions['coverage_text']) |
            set(contradictions['exclusion_text'])
        )

        print(f"  Contradiction texts: {len(contradiction_texts)}")

    # Step 1: Highlight
    output_path, highlighted_count = highlight_pdf(
        input_pdf_path,
        classified_clauses,
        contradiction_texts,
        output_path
    )

    # Step 2: Add legend (returns NEW file)
    output_path = add_legend_page(output_path)

    return output_path, highlighted_count