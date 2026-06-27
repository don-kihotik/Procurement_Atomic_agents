"""Детерминированное ядро аналитика договора.

Два проприетарных актива, провайдер-независимых:
  1. CUAD-категории риска (RU-подмножество) + плейбук степени тяжести;
  2. ВАЛИДАТОР ПРОВЕНАНСА (правило R3): цитата находки должна реально присутствовать
     в тексте договора, иначе находка отбрасывается. Это режет галлюцинации модели —
     ключевой барьер устойчивости (чем сильнее модель, тем ценнее проверка).
"""
from __future__ import annotations

import re

# RU-подмножество 41 категории CUAD — наш методический актив.
CUAD_CATEGORIES: dict[str, str] = {
    "termination": "Срок и расторжение",
    "auto_renewal": "Автопродление",
    "liability_cap": "Лимит ответственности",
    "indemnification": "Возмещение убытков",
    "penalties": "Штрафы и пени",
    "payment_terms": "Платёжные условия",
    "price_adjustment": "Изменение цены / индексация",
    "warranty": "Гарантии качества",
    "force_majeure": "Форс-мажор",
    "confidentiality": "Конфиденциальность",
    "governing_law": "Применимое право и подсудность",
    "assignment": "Уступка прав",
}

SEVERITIES = ("low", "medium", "high")


def _normalize(text: str) -> str:
    """Сжать пробелы и привести кавычки/дефисы — для устойчивого поиска подстроки."""
    text = text.replace("«", '"').replace("»", '"').replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace("‐", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def quote_found(quote: str, source: str, *, min_len: int = 12) -> bool:
    """Цитата считается подтверждённой, если нормализованная подстрока есть в тексте."""
    q = _normalize(quote)
    if len(q) < min_len:
        return False
    return q in _normalize(source)


def validate_findings(findings: list, source_text: str) -> tuple[list, list]:
    """Разделить находки на passed / rejected по правилу провенанса R3.

    Каждая находка — объект/словарь с полем `quote` (verbatim-цитата из договора).
    Возвращает (passed, rejected) с проставленным полем provenance_ok.
    """
    passed, rejected = [], []
    for f in findings:
        quote = f.quote if hasattr(f, "quote") else f.get("quote", "")
        ok = quote_found(quote or "", source_text)
        if hasattr(f, "model_copy"):
            f = f.model_copy(update={"provenance_ok": ok})
        else:
            f = {**f, "provenance_ok": ok}
        (passed if ok else rejected).append(f)
    return passed, rejected
