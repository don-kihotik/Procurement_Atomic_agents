"""Атомарный агент: договор -> находки риска по CUAD + правки, с проверкой провенанса R3.

LLM (переключаемый) извлекает находки с ДОСЛОВНЫМИ цитатами; детерминированное ядро
проверяет, что каждая цитата реально есть в договоре, и отбрасывает выдуманные.
"""
from __future__ import annotations

import os

from ..llm import get_client_and_model, structured_complete
from ..core.contract import CUAD_CATEGORIES, validate_findings
from ..schemas.contract import (
    ContractInput, ContractOutput, ContractLLMOutput, ContractFinding,
)


def _build_system_prompt(party: str) -> str:
    cats = "\n".join(f"- {k}: {v}" for k, v in CUAD_CATEGORIES.items())
    return (
        f"Ты — юрист по договорам, защищаешь интересы стороны «{party}». "
        "Найди в договоре невыгодные и рискованные условия. По каждой находке укажи:\n"
        "- category: ключ категории из списка ниже;\n"
        "- issue: в чём риск/невыгода;\n"
        "- severity: low | medium | high;\n"
        "- quote: ДОСЛОВНУЮ цитату из текста договора (строго verbatim, без пересказа);\n"
        "- recommendation: предложенную правку.\n\n"
        "Категории риска (CUAD):\n"
        f"{cats}\n\n"
        "КРИТИЧЕСКИ ВАЖНО: поле quote должно быть точной подстрокой договора. "
        "Не перефразируй цитату — иначе находка будет отброшена проверкой."
    )


def _stub_output(inp: ContractInput) -> ContractLLMOutput:
    """Заглушка: 4 реальные находки + 1 с выдуманной цитатой (демонстрирует отбраковку R3)."""
    return ContractLLMOutput(findings=[
        ContractFinding(
            category="payment_terms",
            issue="100% предоплата — весь риск и оборотный капитал на покупателе",
            severity="high",
            quote="Покупатель производит 100% предоплату в течение 5 (пяти) рабочих дней",
            recommendation="Перейти на оплату по факту поставки или 30/70 с отсрочкой",
        ),
        ContractFinding(
            category="price_adjustment",
            issue="Поставщик может в одностороннем порядке поднять цену",
            severity="high",
            quote="Поставщик вправе в одностороннем порядке изменять цену товара",
            recommendation="Зафиксировать цену или привязать к прозрачной индексной формуле",
        ),
        ContractFinding(
            category="liability_cap",
            issue="Ответственность поставщика ограничена символической суммой 10 000 руб.",
            severity="high",
            quote="Ответственность Поставщика по настоящему договору ограничивается суммой 10 000 рублей",
            recommendation="Поднять лимит до суммы договора либо привязать к реальному ущербу",
        ),
        ContractFinding(
            category="auto_renewal",
            issue="Автопролонгация с коротким окном уведомления",
            severity="medium",
            quote="автоматически продлевается на каждый следующий календарный год",
            recommendation="Убрать автопродление или увеличить окно уведомления до 60-90 дней",
        ),
        # намеренно выдуманная цитата (в договоре её НЕТ) — должна быть отброшена R3:
        ContractFinding(
            category="indemnification",
            issue="Якобы безусловное возмещение всех убытков покупателем",
            severity="high",
            quote="Покупатель возмещает Поставщику все убытки в безусловном порядке",
            recommendation="Исключить безусловное возмещение",
        ),
    ])


def analyze_contract(inp: ContractInput) -> ContractOutput:
    client, model, mode = get_client_and_model()
    notes: list[str] = []

    if mode == "stub":
        llm_out = _stub_output(inp)
        notes.append("LLM-шаг: заглушка (LLM_PROVIDER=stub), включает 1 выдуманную цитату для демо R3.")
    else:
        system = _build_system_prompt(inp.party)
        llm_out = structured_complete(
            client, model, mode,
            system=system, user=inp.raw_text, response_model=ContractLLMOutput, max_tokens=3000,
        )
        notes.append(f"LLM-шаг: провайдер '{os.getenv('LLM_PROVIDER')}', модель '{model}'.")

    for f in llm_out.findings:
        f.category_label = CUAD_CATEGORIES.get(f.category, f.category)

    passed, rejected = validate_findings(llm_out.findings, inp.raw_text)
    notes.append(
        f"Провенанс R3: {len(passed)} подтверждено, {len(rejected)} отброшено (цитата не найдена в договоре)."
    )

    summary = {
        "total": len(llm_out.findings),
        "passed": len(passed),
        "rejected": len(rejected),
        "by_severity": {s: sum(1 for f in passed if f.severity == s) for s in ("high", "medium", "low")},
    }
    return ContractOutput(
        provider=os.getenv("LLM_PROVIDER", "stub"),
        party=inp.party,
        findings_passed=passed,
        findings_rejected=rejected,
        summary=summary,
        notes=notes,
    )
