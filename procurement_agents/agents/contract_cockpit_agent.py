"""Кокпит-агент: договор → дерево проверки по CUAD (экономическая линза) + провенанс R3.

LLM (переключаемый) даёт по каждой экономической категории статус-светофор + ответ + цитату;
детерминированное ядро привязывает наш бенчмарк/эффект/редлайн и проверяет цитату (R3).
"""
from __future__ import annotations

import os

from ..llm import get_client_and_model, structured_complete
from ..core.contract_cuad import CATEGORIES, CATEGORY_BY_KEY, CLUSTERS, economic_categories
from ..core.contract import quote_found
from ..schemas.cockpit import (
    CockpitInput, CockpitResult, CockpitLLMOutput, CategoryAssessment,
    CategoryResult, ClusterGroup,
)

_VALID = {"GREEN", "YELLOW", "RED", "MISSING", "NA"}


def _build_system_prompt(party: str) -> str:
    lines = []
    for c in economic_categories():
        lines.append(f"- {c['key']}: {c['label']} — проверяем: {c['question']}")
    checklist = "\n".join(lines)
    return (
        f"Ты — закупочный аналитик (НЕ юрист). Защищаешь сторону «{party}». "
        "Это экономический анализ договора: ищем, где договор стоит покупателю денег или "
        "перекладывает на него риск, а не юридические дефекты.\n\n"
        "Сначала определи тип договора (поставка/услуги/аренда/подряд/рамочный/иной).\n"
        "Затем по КАЖДОМУ пункту чек-листа ниже верни оценку:\n"
        "- status: GREEN (условие есть/в норме) · YELLOW (частично/слабее нормы) · "
        "RED (нет защиты ИЛИ есть вредное условие → деньги/риск на нас) · MISSING (в договоре нет);\n"
        "- answer: что по факту в договоре и на кого риск (экономически, кратко);\n"
        "- quote: ДОСЛОВНАЯ цитата из договора (точная подстрока; пусто только при MISSING);\n"
        "- risk_bearer: покупатель | поставщик | обе.\n\n"
        f"Чек-лист (верни оценку для каждого key):\n{checklist}\n\n"
        "КРИТИЧНО: quote — точная подстрока договора, без пересказа, иначе пункт отбраковывается."
    )


def _stub_output() -> CockpitLLMOutput:
    A = CategoryAssessment
    return CockpitLLMOutput(
        contract_type="поставка",
        assessments=[
            A(key="payment_terms", status="RED", risk_bearer="покупатель",
              answer="100% предоплата за 5 дней — весь оборотный капитал и риск невозврата на покупателе.",
              quote="Покупатель производит 100% предоплату в течение 5 (пяти) рабочих дней"),
            A(key="price_indexation", status="RED", risk_bearer="покупатель",
              answer="Поставщик может в одностороннем порядке поднять цену — ценовой риск на нас.",
              quote="Поставщик вправе в одностороннем порядке изменять цену товара"),
            A(key="liability_cap", status="RED", risk_bearer="покупатель",
              answer="Ответственность поставщика ограничена 10 000 ₽ — риск дефекта/срыва на покупателе.",
              quote="Ответственность Поставщика по настоящему договору ограничивается суммой 10 000 рублей"),
            A(key="penalty_symmetry", status="RED", risk_bearer="покупатель",
              answer="Пеня предусмотрена только для покупателя за просрочку оплаты; за срыв поставки — нет.",
              quote="Покупатель уплачивает пеню в размере 0,5% от суммы за каждый день просрочки"),
            A(key="termination", status="RED", risk_bearer="покупатель",
              answer="Автопролонгация без права свободного выхода; termination for convenience нет.",
              quote="автоматически продлевается на каждый следующий календарный год"),
            A(key="volume_rebate", status="MISSING", risk_bearer="покупатель",
              answer="Объёмные ретробонусы не предусмотрены — упущенная скидка."),
            A(key="fx_clause", status="MISSING", answer="Валютной оговорки нет."),
            A(key="mfn", status="MISSING", answer="MFN/прозрачности цен нет."),
            A(key="warranty", status="MISSING", risk_bearer="покупатель",
              answer="Гарантийные обязательства в договоре не зафиксированы."),
            A(key="incoterms", status="MISSING", answer="Incoterms и страхование груза не указаны."),
            A(key="delivery_penalty", status="MISSING", risk_bearer="покупатель",
              answer="Штраф за просрочку поставки не предусмотрен."),
            A(key="retention", status="MISSING", answer="Гарантийное удержание отсутствует."),
            A(key="audit_openbook", status="MISSING", answer="Право аудита/open-book отсутствует."),
            A(key="abac_sanctions", status="MISSING", answer="ABAC и санкционной оговорки нет."),
            A(key="take_or_pay", status="NA", answer="Объёмных обязательств в договоре нет."),
            # намеренно выдуманная цитата → R3 отбракует:
            A(key="quality_control", status="RED", risk_bearer="покупатель",
              answer="(демо галлюцинации) якобы заданы стандарты качества.",
              quote="Поставщик гарантирует соответствие ГОСТ 31943-2012 по всем партиям"),
        ],
    )


def review_contract(inp: CockpitInput) -> CockpitResult:
    client, model, mode = get_client_and_model()
    notes: list[str] = []
    model_name = model or "stub"

    if mode == "stub":
        llm = _stub_output()
        notes.append("LLM-шаг: заглушка (LLM_PROVIDER=stub); включает 1 выдуманную цитату для демо R3.")
    else:
        system = _build_system_prompt(inp.party)
        llm = structured_complete(
            client, model, mode,
            system=system, user=inp.raw_text, response_model=CockpitLLMOutput, max_tokens=4000,
        )
        notes.append(f"LLM-шаг: провайдер '{os.getenv('LLM_PROVIDER')}', модель '{model}'.")

    assessed = {a.key: a for a in llm.assessments}
    rejected: list[CategoryResult] = []
    results_by_key: dict[str, CategoryResult] = {}

    for cat in CATEGORIES:
        a = assessed.get(cat["key"])
        status = (a.status if a and a.status in _VALID else "NA")
        quote = (a.quote or "") if a else ""
        prov_ok = None
        if quote:
            prov_ok = quote_found(quote, inp.raw_text)
        cr = CategoryResult(
            key=cat["key"], label=cat["label"], cluster=cat["cluster"], economic=cat["economic"],
            status=status, severity=cat["severity"], question=cat["question"],
            answer=(a.answer if a else ""), impact=cat.get("impact", ""),
            risk_bearer=(a.risk_bearer if a else ""), benchmark=cat.get("benchmark", ""),
            redline=cat.get("redline", ""), quote=quote, provenance_ok=prov_ok,
        )
        # цитата заявлена, но не найдена в договоре → галлюцинация, в отбракованные
        if quote and prov_ok is False:
            rejected.append(cr)
            # в дереве показываем без цитаты, статус понижаем до «не подтверждено»
            cr_tree = cr.model_copy(update={"quote": "", "status": "NA",
                                            "answer": (cr.answer + " · цитата не подтверждена, исключено")})
            results_by_key[cat["key"]] = cr_tree
        else:
            results_by_key[cat["key"]] = cr

    # сборка по кластерам в порядке таксономии
    clusters: list[ClusterGroup] = []
    for cl in CLUSTERS:
        items = [results_by_key[c["key"]] for c in CATEGORIES if c["cluster"] == cl]
        clusters.append(ClusterGroup(name=cl, items=items))

    flat = [results_by_key[c["key"]] for c in CATEGORIES]
    reds = [r for r in flat if r.status == "RED"]
    high_reds = [r for r in reds if r.severity == "high"]
    summary = {
        "total": len(flat),
        "red": len(reds),
        "yellow": sum(1 for r in flat if r.status == "YELLOW"),
        "green": sum(1 for r in flat if r.status == "GREEN"),
        "missing": sum(1 for r in flat if r.status == "MISSING"),
        "rejected": len(rejected),
        "high": len(high_reds),
    }
    money_note = (
        f"{len(reds)} статей с денежным/рисковым эффектом, из них {len(high_reds)} высокого приоритета. "
        "Каждая несёт оценку эффекта 1–7% — суммарно значимая доля стоимости договора."
        if reds else "Существенных экономических слабостей не выявлено."
    )
    notes.append(f"Провенанс R3: {len(rejected)} цитат отброшено как ненайденные.")

    return CockpitResult(
        provider=os.getenv("LLM_PROVIDER", "stub"),
        model=model_name,
        contract_type=llm.contract_type,
        party=inp.party,
        clusters=clusters,
        rejected=rejected,
        summary=summary,
        money_note=money_note,
        notes=notes,
    )
