# ============================================================
# src/api/routes.py
# Week 6 — API Routes
#
# Endpoints:
#   GET  /health              → API status
#   POST /analyze_policy      → upload PDF, get full analysis
#   GET  /download/{filename} → download highlighted PDF
#   GET  /report/{filename}   → download text report
# ============================================================

import os
import sys
import time
import shutil
import tempfile
import pandas as pd
from pathlib import Path
from typing  import Optional

from fastapi import (
    APIRouter, UploadFile, File,
    HTTPException, BackgroundTasks)
from fastapi.responses import FileResponse

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from config import (
    BERT_MODEL_DIR, LABEL_NAMES,
    RISK_WEIGHTS, REPORTS_DIR,
    HIDDEN_COND_DIR
)
from src.api.schemas import (
    AnalysisResponse, HealthResponse,
    ClauseResult, HiddenCondition,
    RiskScoreBreakdown
)

router = APIRouter()

# Upload/output directories
UPLOAD_DIR      = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'outputs', 'uploads')
HIGHLIGHTED_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'outputs', 'highlighted_pdfs')

os.makedirs(UPLOAD_DIR,      exist_ok=True)
os.makedirs(HIGHLIGHTED_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR,     exist_ok=True)


# ── GET /health ───────────────────────────────────────────

@router.get(
    "/health",
    response_model=HealthResponse,
    summary="API health check",
    tags=["System"]
)
def health_check():
    """
    Check if API is running and model is loaded.
    """
    model_loaded = os.path.exists(BERT_MODEL_DIR)
    return HealthResponse(
        status       = "ok",
        model_loaded = model_loaded,
        version      = "1.0.0",
        message      = (
            "Model ready." if model_loaded
            else f"Model not found at {BERT_MODEL_DIR}. "
                 f"Run Week 3 training first."
        )
    )


# ── POST /analyze_policy ──────────────────────────────────

@router.post(
    "/analyze_policy",
    response_model=AnalysisResponse,
    summary="Analyse an insurance policy PDF",
    tags=["Analysis"]
)
async def analyze_policy(
    file: UploadFile = File(
        ...,
        description="Insurance policy PDF file"
    )
):
    """
    Upload a PDF and receive:
    - Risk score (0.0 – 1.0) and risk level
    - All clauses classified by label
    - Hidden conditions and NLI contradictions
    - URL to download colour-highlighted PDF
    - URL to download risk report

    Colour coding in highlighted PDF:
    - Green  = Coverage clause
    - Red    = Exclusion clause
    - Orange = Condition clause
    - Purple = Contradiction (hidden risk)
    """
    start_time = time.time()

    # ── Validate file type ──────────────────────────────
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted."
        )

    if not os.path.exists(BERT_MODEL_DIR):
        raise HTTPException(
            status_code=503,
            detail=(
                f"Trained model not found at {BERT_MODEL_DIR}. "
                f"Run Week 3 training first."
            )
        )

    # ── Save uploaded PDF ───────────────────────────────
    pdf_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # ── Stage 1: Extract and classify clauses ───────
        import pdfplumber, re as _re
        from src.inference.nli_engine import (
            load_finetuned_model, classify_clauses)

        # Extract text directly — no import from data_pipeline
        raw_text = ""
        try:
            with pdfplumber.open(pdf_path) as _pdf:
                for _page in _pdf.pages:
                    _t = _page.extract_text()
                    if _t:
                        raw_text += _t + "\n"
        except Exception as _e:
            raise HTTPException(
                status_code=422,
                detail=f"Could not read PDF: {str(_e)}"
            )

        if not raw_text.strip():
            raise HTTPException(
                status_code=422,
                detail=(
                    "No text found in PDF. "
                    "File may be scanned or image-only."
                )
            )

        # Segment inline — no import from data_pipeline
        def _segment(text, source_file):
            clauses = []
            lines   = [l.strip() for l in text.split('\n')
                       if l.strip()]
            buffer  = []
            heading = "General"
            _sec_re = _re.compile(
                r'^[A-Z][A-Z\s]{3,50}$|'
                r'^\d+[\.\)]\s+[A-Z]|'
                r'^(SECTION|CLAUSE|ARTICLE)\s+\d+',
                _re.MULTILINE
            )
            for line in lines:
                if (_sec_re.match(line) and
                        len(line) < 120 and
                        len(line.split()) < 12):
                    if buffer:
                        ct = ' '.join(buffer).strip()
                        if 8 <= len(ct.split()) <= 120:
                            clauses.append({
                                'clause_text'    : ct,
                                'section_heading': heading,
                                'source_file'    : source_file,
                                'page_number'    : 0,
                            })
                        buffer = []
                    heading = line.strip()
                    continue
                if len(line.split()) < 3:
                    continue
                if _re.match(r'^[\d\s\.\-\/\(\)]+$', line):
                    continue
                buffer.append(line)
                joined = ' '.join(buffer)
                if (_re.search(r'[.!?]$', joined) and
                        len(joined.split()) >= 8):
                    words = joined.split()
                    ct    = ' '.join(words[:120]).strip()
                    if len(ct.split()) >= 8:
                        clauses.append({
                            'clause_text'    : ct,
                            'section_heading': heading,
                            'source_file'    : source_file,
                            'page_number'    : 0,
                        })
                    buffer = []
            if buffer:
                ct = ' '.join(buffer).strip()
                if 8 <= len(ct.split()) <= 120:
                    clauses.append({
                        'clause_text'    : ct,
                        'section_heading': heading,
                        'source_file'    : source_file,
                        'page_number'    : 0,
                    })
            return clauses

        segments     = _segment(raw_text, file.filename)
        clause_texts = [s['clause_text'] for s in segments]

        if not clause_texts:
            raise HTTPException(
                status_code=422,
                detail="Could not extract any clauses from PDF."
            )

        tokenizer, model, device = load_finetuned_model()
        classified = classify_clauses(
            clause_texts, tokenizer, model, device)

        # Merge segmentor metadata
        for i, c in enumerate(classified):
            if i < len(segments):
                c['source_file']     = file.filename
                c['page_number']     = segments[i].get(
                    'page_number', 0)
                c['section_heading'] = segments[i].get(
                    'section_heading', '')

        # ── Stage 2: Semantic matching ───────────────────
        from src.inference.semantic_matcher import (
            run_semantic_matching)

        pairs_df, sent_model = run_semantic_matching(
            classified, save=False)

        # ── Stage 3: NLI contradiction detection ─────────
        nli_results_df = pd.DataFrame()
        if not pairs_df.empty:
            from src.inference.nli_engine import run_nli_pipeline
            nli_results_df, _ = run_nli_pipeline(
                pairs_df, save=False)

        # ── Stage 4: Hidden condition detection ──────────
        from src.inference.hidden_condition_detector import (
            detect_hidden_conditions)

        nli_input = (nli_results_df
                     if not nli_results_df.empty else None)
        hidden_conditions = detect_hidden_conditions(
            classified,
            nli_results_df=nli_input,
            include_keyword=True,
            include_vague=True,
            include_uncertain=False
        )

        # ── Stage 5: Risk scoring ────────────────────────
        from src.scoring.risk_scorer import (
            score_document, generate_risk_report)

        score_result = score_document(
            classified,
            hidden_conditions=hidden_conditions,
            nli_results_df=nli_results_df,
            document_name=file.filename
        )

        # ── Stage 6: Highlight PDF ───────────────────────
        # COMMENTED OUT: Highlighted PDF generation not needed
        # All results will be displayed in the frontend instead
        # from src.pdf_processing.pdf_highlighter import (
        #     create_highlighted_pdf)
        #
        # highlighted_path, _ = create_highlighted_pdf(
        #     pdf_path,
        #     classified,
        #     nli_results_df=nli_results_df,
        #     output_dir=HIGHLIGHTED_DIR
        # )

        # ── Stage 7: Generate reports ────────────────────
        report_paths = generate_risk_report(
            score_result, save_dir=REPORTS_DIR)

        # ── Build contradiction lookup set ───────────────
        contradiction_texts = set()
        if not nli_results_df.empty:
            contra = nli_results_df[
                nli_results_df['is_contradiction'] == True]
            contradiction_texts = (
                set(contra['coverage_text'].tolist()) |
                set(contra['exclusion_text'].tolist())
            )

        # ── Build per-clause NLI scores ──────────────────
        clause_contra_scores = {}
        if not nli_results_df.empty:
            contra = nli_results_df[
                nli_results_df['is_contradiction'] == True]
            for _, row in contra.iterrows():
                score = float(row['contradiction_score'])
                clause_contra_scores[
                    row['coverage_text'][:80]] = score
                clause_contra_scores[
                    row['exclusion_text'][:80]] = score

        # ── Assemble clause lists ─────────────────────────
        def build_clause_result(c):
            text     = c.get('clause_text', '')
            key      = text[:80]
            label_id = c.get('label_id', 0)
            is_contra = text in contradiction_texts
            return ClauseResult(
                clause_text         = text,
                label_id            = label_id,
                label_name          = LABEL_NAMES.get(
                    label_id, 'Unknown'),
                confidence          = round(
                    c.get('confidence', 0), 4),
                risk_weight         = RISK_WEIGHTS.get(
                    label_id, 0.1),
                is_contradiction    = is_contra,
                contradiction_score = clause_contra_scores.get(
                    key, 0.0),
                section_heading     = c.get(
                    'section_heading', ''),
                page_number         = c.get('page_number', 0),
                source_file         = c.get('source_file', '')
            )

        coverage_clauses  = [
            build_clause_result(c) for c in classified
            if c.get('label_id') == 1
        ]
        exclusion_clauses = [
            build_clause_result(c) for c in classified
            if c.get('label_id') == 2
        ]
        condition_clauses = [
            build_clause_result(c) for c in classified
            if c.get('label_id') == 3
        ]

        # Sort exclusions by confidence desc
        exclusion_clauses.sort(
            key=lambda x: x.confidence, reverse=True)

        # ── Hidden conditions list ────────────────────────
        hidden_list = [
            HiddenCondition(
                detection_type      = h.get(
                    'detection_type', ''),
                severity            = h.get('severity', 'Low'),
                risk_reason         = h.get('risk_reason', ''),
                coverage_text       = h.get(
                    'coverage_text', '')[:500],
                exclusion_text      = h.get(
                    'exclusion_text', '')[:500],
                contradiction_score = float(h.get(
                    'contradiction_score', 0.0)),
                similarity_score    = float(h.get(
                    'similarity_score', 0.0)),
                same_document       = bool(h.get(
                    'same_document', True))
            )
            for h in hidden_conditions
        ]

        # ── Label distribution ────────────────────────────
        from collections import Counter
        label_dist = Counter(
            LABEL_NAMES.get(c.get('label_id', 0), 'Unknown')
            for c in classified
        )

        # ── Processing time ───────────────────────────────
        proc_time = round(time.time() - start_time, 2)

        # ── Build filenames for download URLs ─────────────
        # highlighted_filename = Path(highlighted_path).name  # COMMENTED OUT
        report_filename      = Path(
            report_paths.get('report_path', '')).name

        return AnalysisResponse(
            filename           = file.filename,
            total_clauses      = len(classified),
            processing_time_s  = proc_time,

            risk_score         = score_result['risk_score'],
            risk_level         = score_result['risk_level'],
            risk_breakdown     = RiskScoreBreakdown(
                clause_risk_score        = score_result[
                    'clause_risk_score'],
                contradiction_risk_score = score_result[
                    'contradiction_risk_score'],
                hidden_risk_score        = score_result[
                    'hidden_risk_score'],
            ),

            label_distribution = dict(label_dist),
            exclusion_count    = label_dist.get('Exclusion', 0),
            coverage_count     = label_dist.get('Coverage', 0),
            condition_count    = label_dist.get('Condition', 0),
            normal_count       = label_dist.get('Normal', 0),

            contradiction_count           = score_result[
                'contradiction_count'],
            high_conf_contradictions      = score_result[
                'high_conf_contradictions'],
            avg_contradiction_confidence  = score_result[
                'avg_contradiction_conf'],

            hidden_conditions_total  = score_result[
                'hidden_conditions_total'],
            hidden_high_severity     = score_result[
                'hidden_high_severity'],
            hidden_medium_severity   = score_result[
                'hidden_medium_severity'],
            hidden_low_severity      = score_result[
                'hidden_low_severity'],

            coverage_clauses  = coverage_clauses[:50],
            exclusion_clauses = exclusion_clauses[:50],
            condition_clauses = condition_clauses[:50],
            hidden_conditions = hidden_list[:100],

            # COMMENTED OUT: Not using highlighted PDF anymore
            # highlighted_pdf_url = (
            #     f"/api/v1/download/{highlighted_filename}"),
            report_txt_url      = (
                f"/api/v1/report/{report_filename}"
                if report_filename else None),
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


# ── GET /download/{filename} ──────────────────────────────

@router.get(
    "/download/{filename}",
    summary="Download highlighted PDF",
    tags=["Downloads"]
)
def download_highlighted_pdf(filename: str):
    """
    Download the colour-highlighted PDF produced after analysis.
    """
    file_path = os.path.join(HIGHLIGHTED_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: {filename}"
        )

    return FileResponse(
        path         = file_path,
        media_type   = "application/pdf",
        filename     = filename,
        headers      = {
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        }
    )


# ── GET /report/{filename} ────────────────────────────────

@router.get(
    "/report/{filename}",
    summary="Download risk report",
    tags=["Downloads"]
)
def download_report(filename: str):
    """
    Download the text risk report produced after analysis.
    """
    file_path = os.path.join(REPORTS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Report not found: {filename}"
        )

    return FileResponse(
        path       = file_path,
        media_type = "text/plain",
        filename   = filename
    )


# ── GET /model-info ───────────────────────────────────────

@router.get(
    "/model-info",
    summary="Show loaded model information",
    tags=["System"]
)
def model_info():
    """Return information about the loaded model."""
    model_exists = os.path.exists(BERT_MODEL_DIR)
    config_path  = os.path.join(BERT_MODEL_DIR, "config.json")

    model_config = {}
    if os.path.exists(config_path):
        import json
        with open(config_path) as f:
            raw = json.load(f)
            model_config = {
                'model_type'   : raw.get('model_type', ''),
                'num_labels'   : raw.get('num_labels', 0),
                'hidden_size'  : raw.get('hidden_size', 0),
            }

    return {
        "base_model"        : "nlpaueb/legal-bert-base-uncased",
        "model_path"        : BERT_MODEL_DIR,
        "model_ready"       : model_exists,
        "model_config"      : model_config,
        "label_names"       : LABEL_NAMES,
        "risk_weights"      : RISK_WEIGHTS,
    }