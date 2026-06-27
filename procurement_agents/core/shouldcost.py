"""Детерминированное ядро should-cost — статическая декомпозиция себестоимости.

Порт сути `should-cost` skill (`compute_static`): материалы x цены + передел + SG&A + маржа.
Чистая математика, без LLM и без привязки к engagement-папке — провайдер-независима.
"""
from __future__ import annotations

from .data import BOM_TEMPLATES, SEED_PRICES_RUB_PER_KG


class ShouldCostError(ValueError):
    pass


def compute_static(
    *,
    bom: dict[str, float],
    prices: dict[str, float],
    structure: dict[str, float],
    actual_price_rub: float | None = None,
) -> dict:
    """Статическая декомпозиция. bom: компонент->кг; prices: компонент->₽/кг."""
    conversion_pct = float(structure.get("conversion_pct", 0.15))
    sga_pct = float(structure.get("sga_pct", 0.07))
    margin_pct = float(structure.get("margin_pct", 0.08))

    lines: list[dict] = []
    materials_total = 0.0
    for comp, kg in bom.items():
        ppk = prices.get(comp)
        if ppk is None:
            raise ShouldCostError(f"нет цены для компонента '{comp}'")
        cost = round(kg * ppk, 2)
        lines.append({
            "component": comp,
            "qty": round(float(kg), 4),
            "rub_per_kg": round(float(ppk), 2),
            "cost_rub": cost,
        })
        materials_total += cost

    materials_total = round(materials_total, 2)
    conversion_cost = round(materials_total * conversion_pct, 2)
    sga_cost = round((materials_total + conversion_cost) * sga_pct, 2)
    cost_before_margin = materials_total + conversion_cost + sga_cost
    margin_cost = round(cost_before_margin * margin_pct, 2)
    target = round(cost_before_margin + margin_cost, 2)

    out = {
        "lines": lines,
        "materials_total": materials_total,
        "conversion_cost": conversion_cost,
        "sga_cost": sga_cost,
        "margin_cost": margin_cost,
        "target_unit_price": target,
    }
    if actual_price_rub is not None:
        gap = round(actual_price_rub - target, 2)
        out["actual_price_rub"] = round(float(actual_price_rub), 2)
        out["gap_rub"] = gap
        out["gap_pct"] = round((gap / target * 100) if target else 0.0, 2)
    return out


def guess_template(text: str, category: str | None = None) -> str | None:
    """Детерминированный подбор BOM-шаблона по ключевым словам.

    Страховка на случай, когда слабая модель не выбрала шаблон сама.
    """
    blob = f"{text} {category or ''}".lower()
    if "кабел" in blob:
        if any(k in blob for k in ("алюмин", "alumin", " al ", "ал.")):
            return "cable_power_al"
        if any(k in blob for k in ("медн", "медь", "copper", " cu")):
            return "cable_power_cu"
        return "cable_power_cu"
    return None


def build_should_cost(
    template_key: str,
    *,
    quantities_kg: dict[str, float] | None = None,
    prices: dict[str, float] | None = None,
    actual_price_rub: float | None = None,
) -> dict:
    """Собрать should-cost по ключу BOM-шаблона (с опциональным переопределением кол-в)."""
    tmpl = BOM_TEMPLATES.get(template_key)
    if tmpl is None:
        raise ShouldCostError(f"неизвестный BOM-шаблон '{template_key}'")
    bom = dict(tmpl["bom"])
    if quantities_kg:
        # переопределяем только известные компоненты шаблона
        for comp, kg in quantities_kg.items():
            if comp in bom and kg:
                bom[comp] = float(kg)
    result = compute_static(
        bom=bom,
        prices=prices or SEED_PRICES_RUB_PER_KG,
        structure=tmpl["structure"],
        actual_price_rub=actual_price_rub,
    )
    result["template"] = template_key
    return result
