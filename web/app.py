"""FastAPI-кокпит «Аналитик договора» (экономическая линза)."""
from __future__ import annotations

import html
import os
import time
from pathlib import Path

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from procurement_agents.agents.contract_cockpit_agent import review_contract
from procurement_agents.schemas.cockpit import CockpitInput
from web.parse import extract_text

BASE = Path(__file__).parent
REPO = BASE.parent
app = FastAPI(title="Аналитик договора")
templates = Jinja2Templates(directory=str(BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

# выбор в UI → (LLM_PROVIDER, ollama-модель)
MODEL_OPTIONS = [
    ("local:gemma4", "local · gemma4 (офлайн, точнее)"),
    ("local:qwen2.5:3b", "local · qwen2.5:3b (офлайн, быстрее)"),
    ("claude", "Claude (нужен ключ)"),
    ("stub", "Пример (мгновенно, демо)"),
]


def _apply_model(choice: str) -> None:
    if choice.startswith("local:"):
        os.environ["LLM_PROVIDER"] = "local"
        os.environ["OLLAMA_MODEL"] = choice.split(":", 1)[1]
    elif choice in ("claude", "stub", "yandex"):
        os.environ["LLM_PROVIDER"] = choice


def _document_html(raw_text: str, items: list) -> str:
    """Экранированный текст договора с подсветкой подтверждённых цитат (<mark id=q-key>)."""
    esc = html.escape(raw_text)
    for it in items:
        if it.quote and it.provenance_ok:
            q = html.escape(it.quote)
            if q in esc:
                mark = f'<mark id="q-{it.key}" class="hl">{q}</mark>'
                esc = esc.replace(q, mark, 1)
    return esc.replace("\n", "<br>")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html", {"models": MODEL_OPTIONS})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    model: str = Form("local:gemma4"),
    party: str = Form("покупатель"),
    pasted: str = Form(""),
    use_sample: str = Form(""),
    file: UploadFile | None = File(None),
):
    raw_text = ""
    source = ""
    if use_sample:
        raw_text = (REPO / "fixtures" / "contract_sample.txt").read_text(encoding="utf-8")
        source = "пример: договор поставки № 17/2026"
        model = "stub"  # пример мгновенный, заготовка под этот образец
    elif file is not None and file.filename:
        data = await file.read()
        raw_text = extract_text(file.filename, data)
        source = file.filename
    elif pasted.strip():
        raw_text = pasted
        source = "вставленный текст"

    if not raw_text.strip():
        return templates.TemplateResponse(
            request, "index.html",
            {"models": MODEL_OPTIONS, "error": "Загрузите файл, вставьте текст или используйте пример."},
        )

    _apply_model(model)
    t0 = time.time()
    result = review_contract(CockpitInput(raw_text=raw_text, party=party))
    elapsed = round(time.time() - t0, 1)

    all_items = [it for cl in result.clusters for it in cl.items]
    doc_html = _document_html(raw_text, all_items)

    return templates.TemplateResponse(
        request, "result.html",
        {"r": result, "doc_html": doc_html, "source": source, "elapsed": elapsed, "party": party},
    )
