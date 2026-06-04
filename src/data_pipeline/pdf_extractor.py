# ============================================================
# src/data_pipeline/pdf_extractor.py
# Extract raw text from insurance PDF files
# ============================================================

import os
import sys

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import RAW_PDF_HEALTH, RAW_PDF_CAR, SKIP_FILES


def extract_text_from_pdf(pdf_path):
    """
    Extract full raw text from a single PDF file.
    Tries pdfplumber first (better layout preservation),
    falls back to PyPDF2 if pdfplumber fails.

    Args:
        pdf_path : full path to PDF file

    Returns:
        string of extracted text, empty string on failure
    """
    # Try pdfplumber first
    try:
        import pdfplumber
        pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        if pages:
            return "\n".join(pages)
    except Exception:
        pass

    # Fallback to PyPDF2
    try:
        import PyPDF2
        pages = []
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n".join(pages)
    except Exception as e:
        print(f"  Could not extract {pdf_path}: {e}")
        return ""


def extract_text_from_pdf_by_page(pdf_path):
    """
    Extract text page by page, returning list of
    (page_number, text) tuples.

    Args:
        pdf_path : full path to PDF file

    Returns:
        list of (page_num, text) tuples
    """
    pages = []
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                t = page.extract_text()
                if t and t.strip():
                    pages.append((i, t))
    except Exception:
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for i, page in enumerate(reader.pages, 1):
                    t = page.extract_text()
                    if t and t.strip():
                        pages.append((i, t))
        except Exception as e:
            print(f"  Page extraction failed {pdf_path}: {e}")

    return pages


def extract_all_pdfs(health_dir=None, car_dir=None):
    """
    Extract text from all PDFs in both raw_pdf folders.
    Skips files listed in SKIP_FILES config.

    Args:
        health_dir : path to health insurance PDFs folder
                     (default: RAW_PDF_HEALTH from config)
        car_dir    : path to car insurance PDFs folder
                     (default: RAW_PDF_CAR from config)

    Returns:
        list of dicts:
          {filename, insurance_type, text, pdf_path,
           page_texts}
    """
    if health_dir is None:
        health_dir = RAW_PDF_HEALTH
    if car_dir is None:
        car_dir = RAW_PDF_CAR

    docs = []

    folders = [
        (health_dir, "health"),
        (car_dir,    "car"),
    ]

    for folder, ins_type in folders:
        if not os.path.exists(folder):
            print(f"  Folder not found: {folder}")
            continue

        pdfs = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith('.pdf')
        ])

        print(f"\n{ins_type.upper()} ({len(pdfs)} PDFs):")

        for pdf_name in pdfs:
            # Skip files in the skip list
            if any(skip.lower() in pdf_name.lower()
                   for skip in SKIP_FILES):
                print(f"  SKIPPED : {pdf_name}")
                continue

            pdf_path = os.path.join(folder, pdf_name)
            print(f"  Extracting: {pdf_name}")

            text       = extract_text_from_pdf(pdf_path)
            page_texts = extract_text_from_pdf_by_page(
                pdf_path)

            if not text.strip():
                print(f"  WARNING: No text in {pdf_name}")
                continue

            docs.append({
                "filename"      : pdf_name,
                "insurance_type": ins_type,
                "text"          : text,
                "pdf_path"      : pdf_path,
                "page_texts"    : page_texts,
            })

    print(f"\nTotal documents extracted: {len(docs)}")
    return docs
