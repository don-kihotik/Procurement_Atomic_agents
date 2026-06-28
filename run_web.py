"""Запуск кокпита «Аналитик договора» на localhost.

    python run_web.py            # http://127.0.0.1:8800
    python run_web.py --port 9000 --reload
"""
from __future__ import annotations

import argparse
import webbrowser

import uvicorn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8800)
    ap.add_argument("--reload", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    if not args.no_browser and not args.reload:
        try:
            webbrowser.open(f"http://{args.host}:{args.port}/")
        except Exception:
            pass

    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
