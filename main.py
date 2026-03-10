"""
NeuroArousal Exhibit — entry point.

Launches the FastAPI server with Gradio UI mounted at /ui.
The REST API is available at /docs (Swagger) or /redoc.

Usage
-----
    python main.py                      # defaults: host=0.0.0.0, port=7860
    python main.py --port 8000
    python main.py --api-only           # no Gradio, just FastAPI
    python main.py --mobile             # synonym for default (always mobile-ready)
"""

from __future__ import annotations

import argparse
import sys

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NeuroArousal — Coupled excitable system exhibit server"
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument(
        "--api-only", action="store_true",
        help="Run only the FastAPI REST API (no Gradio UI)",
    )
    parser.add_argument(
        "--mobile", action="store_true",
        help="Alias — the UI is always mobile-responsive",
    )
    args = parser.parse_args()

    if args.api_only:
        uvicorn.run(
            "neuro_arousal.api:app",
            host=args.host,
            port=args.port,
            reload=False,
        )
    else:
        from neuro_arousal.api import app
        from neuro_arousal.ui import build_ui
        import gradio as gr

        demo = build_ui()
        app = gr.mount_gradio_app(app, demo, path="/ui")

        print()
        print("  NeuroArousal Exhibit Server")
        print("  ===========================")
        print(f"  Gradio UI (mobile-ready)  → http://{args.host}:{args.port}/ui")
        print(f"  REST API docs (Swagger)   → http://{args.host}:{args.port}/docs")
        print(f"  REST API docs (ReDoc)     → http://{args.host}:{args.port}/redoc")
        print(f"  State inspector           → GET /state/{{step}}")
        print(f"  Alignment                 → GET /alignment")
        print(f"  Narrative arc             → GET /arc")
        print(f"  Character image           → GET /character/image?step=N")
        print(f"  PEFT adapters             → GET /adapters")
        print()

        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
