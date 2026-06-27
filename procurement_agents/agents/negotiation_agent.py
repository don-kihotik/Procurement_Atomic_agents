"""Атомарный агент: контекст -> бриф к переговорам (рычаги + ценовая лестница + возражения).

Детерминированное ядро считает ценовую лестницу от should-cost и приоритет рычагов;
LLM (переключаемый) обосновывает рычаги под ситуацию, готовит возражения и тезисы.
"""
from __future__ import annotations

import os

from ..llm import get_client_and_model, structured_complete
from ..core.negotiation import LEVERS, select_lever_keys, price_ladder
from ..schemas.negotiation import (
    NegotiationInput, NegotiationOutput, NegotiationLLMOutput,
    Lever, Objection, PriceLadder,
)


def _build_system_prompt(inp: NegotiationInput, ladder: dict | None, preferred: list[str]) -> str:
    catalog = "\n".join(f"- {k}: {v['name']} ({v['family']})" for k, v in LEVERS.items())
    pref = ", ".join(preferred)
    ladder_txt = "не задана (нет should-cost или текущей цены)"
    if ladder:
        ladder_txt = (
            f"should-cost {ladder['should_cost']}, текущая цена {ladder['current_price']}, "
            f"переплата {ladder['overpay_gap']}; целевая цена {ladder['target_price']}, "
            f"стартовый запрос {ladder['opening_ask']}, предел {ladder['walk_away']}."
        )
    return (
        "Ты — переговорщик по закупкам. Подготовь бриф к переговорам. Дай:\n"
        "- levers: 3–5 рычагов из каталога (ключ + почему уместен здесь);\n"
        "- objections: вероятные возражения поставщика и наши контраргументы;\n"
        "- talking_points: конкретные тезисы (опирайся на ценовую лестницу ниже);\n"
        "- batna: запасную позицию.\n\n"
        f"Каталог рычагов:\n{catalog}\n\n"
        f"Рекомендованный приоритет рычагов (по силе поставщика): {pref}\n"
        f"Ценовая лестница (детерминированная, от should-cost): {ladder_txt}\n\n"
        "Тезисы должны ссылаться на конкретные числа лестницы, не выдумывай свои."
    )


def _stub_output(inp: NegotiationInput, ladder: dict | None) -> NegotiationLLMOutput:
    tgt = ladder["target_price"] if ladder else "целевой"
    sc = ladder["should_cost"] if ladder else "should-cost"
    return NegotiationLLMOutput(
        levers=[
            Lever(key="target_pricing", rationale=f"Есть оценка should-cost ({sc}) — якорим переговоры на ней, а не на цене поставщика"),
            Lever(key="re_specification", rationale="В спецификации есть завышение (напряжение/броня/бренд) — снятие удешевляет предмет"),
            Lever(key="tendering", rationale="Категория конкурентная — альтернативные поставщики дают рычаг"),
        ],
        objections=[
            Objection(supplier_says="Цена выросла из-за курса и подорожания сырья",
                      our_counter="Привяжем цену к прозрачной индексной формуле — рост докажем индексом, а не словами"),
            Objection(supplier_says="Это эксклюзивная марка, аналогов нет",
                      our_counter="Есть отечественный аналог по тому же ГОСТ/ТУ — бренд-премия не обоснована"),
        ],
        talking_points=[
            f"Наш расчёт себестоимости — около {sc} ₽/ед.; текущая цена это переплата.",
            f"Реалистичная посадка — {tgt} ₽/ед.; начинаем разговор от себестоимости.",
            "Снятие завышенных требований (напряжение, двойная броня, импортная марка) даёт дополнительную экономию.",
        ],
        batna="Запустить тендер со вторым поставщиком и пересмотреть спецификацию (медь→алюминий) — кредитоспособная альтернатива.",
    )


def prepare_negotiation(inp: NegotiationInput) -> NegotiationOutput:
    client, model, mode = get_client_and_model()
    notes: list[str] = []

    ladder = price_ladder(should_cost=inp.should_cost, current_price=inp.current_price)
    preferred = select_lever_keys(inp.supplier_power)
    if ladder:
        notes.append("Ценовая лестница посчитана детерминированным ядром от should-cost.")
    else:
        notes.append("Ценовая лестница пропущена: не заданы should-cost и/или текущая цена.")

    if mode == "stub":
        llm_out = _stub_output(inp, ladder)
        notes.append("LLM-шаг: заглушка (LLM_PROVIDER=stub).")
    else:
        system = _build_system_prompt(inp, ladder, preferred)
        llm_out = structured_complete(
            client, model, mode,
            system=system, user=inp.raw_text, response_model=NegotiationLLMOutput, max_tokens=2500,
        )
        notes.append(f"LLM-шаг: провайдер '{os.getenv('LLM_PROVIDER')}', модель '{model}'.")

    for lev in llm_out.levers:
        lev.name = LEVERS.get(lev.key, {}).get("name", lev.key)

    return NegotiationOutput(
        provider=os.getenv("LLM_PROVIDER", "stub"),
        category=inp.category_hint or "—",
        recommended_levers=llm_out.levers,
        price_ladder=PriceLadder(**ladder) if ladder else None,
        objections=llm_out.objections,
        talking_points=llm_out.talking_points,
        batna=llm_out.batna,
        notes=notes,
    )
