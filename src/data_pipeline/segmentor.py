# ============================================================
# src/data_pipeline/segmentor.py
# Segment extracted PDF text into individual clauses
# ============================================================

import os
import sys
import re

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Section heading detection patterns ───────────────────

SECTION_PATTERNS = [
    r'^[A-Z][A-Z\s]{3,50}$',                   # ALL CAPS heading
    r'^\d+[\.\)]\s+[A-Z]',                      # 1. Heading
    r'^[IVX]+[\.\)]\s+[A-Z]',                   # Roman numerals
    r'^(SECTION|CLAUSE|ARTICLE|PART)\s+\d+',    # Labelled sections
    r'^(Coverage|Exclusion|Condition|Benefit|'
    r'Definition|General|Special|Standard)',     # Common headings
]

SECTION_RE = re.compile(
    '|'.join(SECTION_PATTERNS), re.MULTILINE)

# Minimum and maximum clause word counts
MIN_WORDS = 8
MAX_WORDS = 120


def segment_text(text, source_file="unknown",
                 page_number=0):
    """
    Segment a single document's text into clauses.

    Strategy:
      1. Split text into lines
      2. Detect section headings
      3. Buffer lines until sentence boundary
      4. Flush complete sentences as clauses

    Args:
        text        : raw extracted text string
        source_file : PDF filename for metadata
        page_number : page number (0 if not tracked)

    Returns:
        list of dicts:
          {clause_text, section_heading,
           source_file, page_number}
    """
    clauses = []
    lines   = [l.strip() for l in text.split('\n')
               if l.strip()]

    current_heading = "General"
    buffer          = []

    for line in lines:
        # Detect section headings
        if (SECTION_RE.match(line) and
                len(line) < 120 and
                len(line.split()) < 12):
            # Flush buffer first
            if buffer:
                clause_text = ' '.join(buffer).strip()
                words       = clause_text.split()
                if MIN_WORDS <= len(words) <= MAX_WORDS:
                    clauses.append({
                        'clause_text'    : clause_text,
                        'section_heading': current_heading,
                        'source_file'    : source_file,
                        'page_number'    : page_number,
                    })
                buffer = []
            current_heading = line.strip()
            continue

        # Skip very short lines (page numbers, footers)
        if len(line.split()) < 3:
            continue

        # Skip lines that are mostly numbers/codes
        if re.match(r'^[\d\s\.\-\/\(\)]+$', line):
            continue

        buffer.append(line)
        joined = ' '.join(buffer)

        # Flush on sentence boundary
        if (re.search(r'[.!?]$', joined) and
                len(joined.split()) >= MIN_WORDS):
            words = joined.strip().split()
            if MIN_WORDS <= len(words) <= MAX_WORDS:
                clauses.append({
                    'clause_text'    : joined.strip(),
                    'section_heading': current_heading,
                    'source_file'    : source_file,
                    'page_number'    : page_number,
                })
            elif len(words) > MAX_WORDS:
                # Too long — split at 100 words
                chunk = ' '.join(words[:100])
                clauses.append({
                    'clause_text'    : chunk,
                    'section_heading': current_heading,
                    'source_file'    : source_file,
                    'page_number'    : page_number,
                })
            buffer = []

    # Flush remaining buffer
    if buffer:
        clause_text = ' '.join(buffer).strip()
        words       = clause_text.split()
        if MIN_WORDS <= len(words) <= MAX_WORDS:
            clauses.append({
                'clause_text'    : clause_text,
                'section_heading': current_heading,
                'source_file'    : source_file,
                'page_number'    : page_number,
            })

    return clauses


def segment_text_by_page(page_texts, source_file="unknown"):
    """
    Segment a document that has already been split by page.
    Preserves page numbers in clause metadata.

    Args:
        page_texts  : list of (page_num, text) tuples
        source_file : PDF filename

    Returns:
        list of clause dicts with correct page_number
    """
    all_clauses = []

    for page_num, text in page_texts:
        page_clauses = segment_text(
            text,
            source_file=source_file,
            page_number=page_num
        )
        all_clauses.extend(page_clauses)

    return all_clauses


def segment_all_documents(raw_docs):
    """
    Segment all extracted documents into clauses.

    Args:
        raw_docs : list of dicts from pdf_extractor
                   {filename, insurance_type, text,
                    pdf_path, page_texts}

    Returns:
        list of clause dicts with insurance_type added
    """
    all_clauses = []

    for doc in raw_docs:
        fname      = doc['filename']
        ins_type   = doc['insurance_type']
        page_texts = doc.get('page_texts', [])

        if page_texts:
            # Use page-aware segmentation
            clauses = segment_text_by_page(
                page_texts, source_file=fname)
        else:
            # Fall back to full-text segmentation
            clauses = segment_text(
                doc['text'], source_file=fname)

        # Add insurance type
        for c in clauses:
            c['insurance_type'] = ins_type

        print(f"  {fname[:50]}: {len(clauses)} clauses")
        all_clauses.extend(clauses)

    print(f"\nTotal clauses segmented: {len(all_clauses)}")
    return all_clauses
