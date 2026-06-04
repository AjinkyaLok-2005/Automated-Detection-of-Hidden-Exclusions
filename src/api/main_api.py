# ============================================================
# src/api/main_api.py
# Week 6 — FastAPI Application
#
# Run with:
#   python run_api.py
#   OR
#   uvicorn src.api.main_api:app --reload --port 8000
#
# Then open:
#   http://localhost:8000/docs      ← interactive Swagger UI
#   http://localhost:8000/redoc     ← ReDoc documentation
# ============================================================

import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(
    os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

from config import BERT_MODEL_DIR, REPORTS_DIR
from src.api.routes import router

# Get frontend directory
FRONTEND_DIR = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(
                os.path.abspath(__file__)))), 'frontend')


# ── Startup / shutdown ────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Run on startup: verify model exists, print status.
    """
    print("\n" + "=" * 56)
    print("  Insurance Policy NLP API — Starting")
    print("=" * 56)

    model_ok = os.path.exists(BERT_MODEL_DIR)
    if model_ok:
        print(f"  Model loaded : {BERT_MODEL_DIR}")
    else:
        print(f"  WARNING: Model not found at {BERT_MODEL_DIR}")
        print("  Run Week 3 training before uploading PDFs.")

    print("  Docs available at : http://localhost:8000/docs")
    print("=" * 56 + "\n")

    yield  # API runs here

    print("\nAPI shutting down.")


# ── App definition ────────────────────────────────────────

app = FastAPI(
    title       = "Insurance Policy Risk Analyser",
    description = (
        "## Automated Detection of Hidden Exclusions\n\n"
        "Upload an insurance policy PDF and receive:\n\n"
        "- **Risk score** (0.0 – 1.0) with breakdown\n"
        "- **Highlighted PDF** colour-coded by clause type\n"
        "- **Hidden conditions** — Coverage clauses "
        "contradicted by exclusions\n"
        "- **NLI contradiction detection** using "
        "cross-encoder/nli-roberta-base\n\n"
        "### Colour Legend\n"
        "| Colour | Label | Meaning |\n"
        "|--------|-------|--------|\n"
        "| 🟢 Green  | Coverage   | What the policy covers |\n"
        "| 🔴 Red    | Exclusion  | What is NOT covered |\n"
        "| 🟠 Orange | Condition  | Policyholder requirements |\n"
        "| 🟣 Purple | Contradiction | Hidden risk detected |\n"
    ),
    version     = "1.0.0",
    lifespan    = lifespan,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)


# ── CORS — allow frontend on any port ─────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],   # restrict in production
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)


# ── Root ──────────────────────────────────────────────────

@app.get("/", tags=["System"])
def root():
    return {
        "service"    : "Insurance Policy Risk Analyser",
        "version"    : "1.0.0",
        "docs"       : "/docs",
        "health"     : "/api/v1/health",
        "analyze"    : "POST /api/v1/analyze_policy",
        "how_to_use" : (
            "POST a PDF file to /api/v1/analyze_policy "
            "to get risk analysis and highlighted PDF"
        )
    }


# ── Routes ────────────────────────────────────────────────

app.include_router(router, prefix="/api/v1")


# ── Serve static frontend files ───────────────────────────

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {FRONTEND_DIR}")
