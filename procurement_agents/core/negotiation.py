"""Детерминированное ядро подготовки к переговорам.

Два провайдер-независимых актива:
  1. Каталог рычагов (Purchasing Chessboard, RU-подмножество) + детерминированный отбор
     по балансу силы поставщик/покупатель — наш методический актив;
  2. ЦЕНОВАЯ ЛЕСТНИЦА от should-cost — математика, привязывающая переговоры к себестоимости
     (связка с прототипом #1), а не к «торгу вокруг текущей цены».
"""
from __future__ import annotations

# Каталог рычагов (curated subset Purchasing Chessboard). power: при какой силе уместен.
LEVERS: dict[str, dict] = {
    "target_pricing":   {"name": "Целевая цена от should-cost", "family": "Затраты"},
    "re_specification": {"name": "Пересмотр спецификации (убрать завышение)", "family": "Спрос"},
    "tendering":        {"name": "Конкурентный тендер / редукцион", "family": "Конкуренция"},
    "volume_bundling":  {"name": "Объединение объёма под скидку", "family": "Спрос"},
    "global_sourcing":  {"name": "Глобализация поиска / поставщики из LCC", "family": "Рынок"},
    "dual_sourcing":    {"name": "Второй источник для давления", "family": "Конкуренция"},
    "make_or_buy":      {"name": "Достоверная альтернатива (инсорсинг/замена)", "family": "Рычаг"},
    "index_clause":     {"name": "Индексная оговорка вместо фикс-премии за риск", "family": "Риск"},
    "open_book":        {"name": "Открытая книга затрат (open-book)", "family": "Затраты"},
    "payment_terms":    {"name": "Перенос на отсрочку платежа", "family": "TCO"},
    "rebate":           {"name": "Объёмные ретробонусы", "family": "Цена"},
    "unbundling":       {"name": "Разбить лот для конкуренции", "family": "Конкуренция"},
}

# Приоритет рычагов по силе поставщика (наш методический выбор).
_BY_POWER: dict[str, list[str]] = {
    "high":   ["re_specification", "global_sourcing", "dual_sourcing", "make_or_buy", "target_pricing", "index_clause"],
    "low":    ["tendering", "volume_bundling", "target_pricing", "rebate", "payment_terms", "unbundling"],
    "medium": ["target_pricing", "volume_bundling", "tendering", "re_specification", "payment_terms", "index_clause"],
}


def select_lever_keys(supplier_power: str | None) -> list[str]:
    """Детерминированный приоритет рычагов по балансу силы."""
    return _BY_POWER.get((supplier_power or "medium").lower(), _BY_POWER["medium"])


def price_ladder(
    *,
    should_cost: float | None,
    current_price: float | None,
    realism_haircut: float = 0.5,
) -> dict | None:
    """Ценовая лестница от should-cost.

    opening   — агрессивный якорь у себестоимости (should-cost +5%);
    target    — реалистичная посадка: текущая цена минус половина (haircut) разрыва до should-cost;
    walk_away — не платим дороже текущей цены.
    """
    if should_cost is None or current_price is None:
        return None
    gap = round(current_price - should_cost, 2)
    opening = round(should_cost * 1.05, 2)
    target = round(current_price - gap * realism_haircut, 2)
    saving_pct = round((current_price - target) / current_price * 100, 2) if current_price else 0.0
    return {
        "should_cost": round(float(should_cost), 2),
        "current_price": round(float(current_price), 2),
        "overpay_gap": gap,
        "opening_ask": opening,
        "target_price": target,
        "walk_away": round(float(current_price), 2),
        "expected_saving_pct": saving_pct,
        "realism_haircut": realism_haircut,
    }
