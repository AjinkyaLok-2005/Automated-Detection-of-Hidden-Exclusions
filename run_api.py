# ============================================================
# run_api.py
# Week 6 — API Entry Point
#
# Usage:
#   python run_api.py               # default port 8000
#   python run_api.py --port 8080   # custom port
#   python run_api.py --reload      # auto-reload on changes
#
# Then open:
#   http://localhost:8000/docs      ← Swagger UI (test here)
#   http://localhost:8000/redoc     ← ReDoc docs
#   http://localhost:8000/api/v1/health
# ============================================================

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="Insurance NLP API Server"
    )
    parser.add_argument(
        '--port', type=int, default=8000,
        help='Port to run on (default: 8000)'
    )
    parser.add_argument(
        '--host', type=str, default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--reload', action='store_true',
        help='Auto-reload on code changes (dev mode)'
    )
    args = parser.parse_args()

    print(f"\nStarting Insurance Policy NLP API...")
    print(f"  Host   : {args.host}")
    print(f"  Port   : {args.port}")
    print(f"  Reload : {args.reload}")
    print(f"\nOpen in browser:")
    print(f"  http://localhost:{args.port}/docs")
    print(f"  http://localhost:{args.port}/api/v1/health\n")

    import uvicorn
    uvicorn.run(
        "src.api.main_api:app",
        host    = args.host,
        port    = args.port,
        reload  = args.reload,
        workers = 1,     # keep 1 worker — model in memory
    )


if __name__ == "__main__":
    main()
