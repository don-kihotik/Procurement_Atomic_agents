"""Запуск агентов из консоли.

  python cli.py spec fixtures/spec_cable.txt --provider stub
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Windows-консоль по умолчанию cp1252 — кириллица в stdout падает; форсируем UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser(description="Procurement Atomic Agents")
    ap.add_argument("agent", choices=["spec"], help="какой агент запустить")
    ap.add_argument("file", help="путь к входному документу (текст)")
    ap.add_argument("--provider", help="переопределить LLM_PROVIDER: local|stub|claude|yandex")
    ap.add_argument("--category", help="подсказка категории, напр. cable")
    args = ap.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    with open(args.file, encoding="utf-8") as f:
        text = f.read()

    if args.agent == "spec":
        from procurement_agents.agents.spec_shouldcost_agent import analyze_spec
        from procurement_agents.schemas.spec_shouldcost import SpecInput
        out = analyze_spec(SpecInput(raw_text=text, category_hint=args.category))
        print(json.dumps(out.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
