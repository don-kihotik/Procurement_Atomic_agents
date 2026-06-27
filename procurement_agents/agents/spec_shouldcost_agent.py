"""Атомарный агент: спецификация -> оспаривание завышения (S1) + should-cost.

Разделение, реализующее тезис устойчивости:
  - LLM (переключаемый провайдер) делает ИЗВЛЕЧЕНИЕ и СУЖДЕНИЕ (атрибуты, флаги завышения,
    выбор BOM-шаблона) — это легко мигрирует local -> claude -> yandex;
  - детерминированное ядро (наш Python + данные) считает ЧИСЛА (should-cost) — провайдер-независимо.
"""
from __future__ import annotations

import os

from ..llm import get_client_and_model, structured_complete
from ..core.data import BOM_TEMPLATES, norms_for
from ..core.shouldcost import build_should_cost, guess_template, ShouldCostError
from ..schemas.spec_shouldcost import (
    SpecInput, SpecOutput, SpecLLMExtraction, SpecAttribute, GoldPlatingFlag, ShouldCost,
)


def _build_system_prompt(category_hint: str | None) -> str:
    norms = "\n".join(f"- {n}" for n in norms_for(category_hint))
    templates = "\n".join(
        f"- {k}: {v['label']} (компоненты: {', '.join(v['bom'])})"
        for k, v in BOM_TEMPLATES.items()
    )
    return (
        "Ты — закупочный инженер. Твоя задача по технической спецификации:\n"
        "1) извлечь ключевые атрибуты;\n"
        "2) найти ЗАВЫШЕНИЕ требований (gold-plating): допуски/классы/опции/бренд выше функционально "
        "необходимого — по каждому дай флаг с обоснованием и предложением, до чего смягчить;\n"
        "3) выбрать подходящий BOM-шаблон из списка ниже (или 'unknown') и, если выводимо из текста, "
        "оценить кол-ва компонентов в кг на единицу; извлечь фактическую цену, если она есть.\n\n"
        "Нормы категории (используй как ориентир для завышения):\n"
        f"{norms}\n\n"
        "Известные BOM-шаблоны:\n"
        f"{templates}\n\n"
        "Отвечай строго по схеме. Не выдумывай числа, которых нет в тексте; "
        "для кол-в компонентов оставляй пусто, если их нельзя обоснованно вывести."
    )


def _stub_extraction(inp: SpecInput) -> SpecLLMExtraction:
    """Детерминированная заглушка для офлайн-прогона (фикстура кабеля)."""
    return SpecLLMExtraction(
        category="cable",
        attributes=[
            SpecAttribute(name="Сечение жилы", value="3x50", unit="мм²"),
            SpecAttribute(name="Класс напряжения", value="6/10", unit="кВ"),
            SpecAttribute(name="Класс гибкости жилы", value="5"),
            SpecAttribute(name="Броня", value="двойная (КбБбШв)"),
            SpecAttribute(name="Марка", value="импортная"),
        ],
        gold_plating_flags=[
            GoldPlatingFlag(
                attribute="Класс напряжения",
                issue="Указан 6/10 кВ для сети, которая по описанию НН (до 1 кВ)",
                why_excessive="Изоляция на 6/10 кВ кратно дороже, для НН не нужна",
                suggested_relaxation="Снизить до 0,66/1 кВ",
                severity="high",
            ),
            GoldPlatingFlag(
                attribute="Класс гибкости жилы",
                issue="Класс 5 (гибкая) для стационарной прокладки",
                why_excessive="Гибкость нужна только для подвижного монтажа",
                suggested_relaxation="Класс 1–2 (жёсткая жила)",
                severity="medium",
            ),
            GoldPlatingFlag(
                attribute="Броня",
                issue="Двойная броня в кабельном лотке",
                why_excessive="Двойная броня оправдана при риске мехповреждений, не в лотке",
                suggested_relaxation="Одинарная броня или без брони",
                severity="medium",
            ),
        ],
        bom_template="cable_power_cu",
        bom_quantities_kg={},
        actual_price_rub=1850.0,
    )


def analyze_spec(inp: SpecInput) -> SpecOutput:
    client, model, mode = get_client_and_model()
    notes: list[str] = []

    if mode == "stub":
        extraction = _stub_extraction(inp)
        notes.append("LLM-шаг: заглушка (LLM_PROVIDER=stub).")
    else:
        system = _build_system_prompt(inp.category_hint)
        extraction = structured_complete(
            client, model, mode,
            system=system, user=inp.raw_text, response_model=SpecLLMExtraction,
        )
        notes.append(f"LLM-шаг: провайдер '{os.getenv('LLM_PROVIDER')}', модель '{model}'.")

    # если модель не выбрала валидный шаблон — подбираем эвристикой по тексту
    template_key = extraction.bom_template
    if template_key not in BOM_TEMPLATES:
        guessed = guess_template(inp.raw_text, extraction.category)
        if guessed:
            template_key = guessed
            extraction.bom_template = guessed
            notes.append(f"BOM-шаблон подобран эвристикой ядра: '{guessed}'.")

    should_cost = None
    if template_key in BOM_TEMPLATES:
        try:
            sc = build_should_cost(
                extraction.bom_template,
                quantities_kg=extraction.bom_quantities_kg or None,
                actual_price_rub=extraction.actual_price_rub,
            )
            should_cost = ShouldCost(**sc)
            notes.append("Should-cost посчитан детерминированным ядром (сидовые цены).")
        except ShouldCostError as e:
            notes.append(f"Should-cost пропущен: {e}")
    else:
        notes.append(f"BOM-шаблон '{extraction.bom_template}' неизвестен — should-cost пропущен.")

    return SpecOutput(
        provider=os.getenv("LLM_PROVIDER", "stub"),
        category=extraction.category,
        attributes=extraction.attributes,
        gold_plating_flags=extraction.gold_plating_flags,
        should_cost=should_cost,
        notes=notes,
    )
