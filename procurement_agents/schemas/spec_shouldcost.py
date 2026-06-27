"""Pydantic-контракты для прототипа «спецификация + should-cost»."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# --- вход агента ---
class SpecInput(BaseModel):
    raw_text: str = Field(description="Текст технической спецификации / ТЗ")
    category_hint: Optional[str] = Field(default=None, description="Подсказка категории, напр. 'cable'")


# --- то, что извлекает LLM (структурированный ответ) ---
class SpecAttribute(BaseModel):
    name: str
    value: str
    unit: Optional[str] = None


class GoldPlatingFlag(BaseModel):
    attribute: str = Field(description="Какой атрибут завышен")
    issue: str = Field(description="В чём завышение")
    why_excessive: str = Field(description="Почему функционально избыточно")
    suggested_relaxation: str = Field(description="Чем заменить / до чего смягчить")
    severity: str = Field(description="low | medium | high")


class SpecLLMExtraction(BaseModel):
    category: str = Field(description="Распознанная категория")
    attributes: list[SpecAttribute] = Field(default_factory=list)
    gold_plating_flags: list[GoldPlatingFlag] = Field(default_factory=list)
    bom_template: str = Field(description="Ключ известного BOM-шаблона или 'unknown'")
    bom_quantities_kg: dict[str, float] = Field(
        default_factory=dict, description="Переопределение кол-в компонентов (кг на единицу), если выводимо"
    )
    actual_price_rub: Optional[float] = Field(default=None, description="Фактическая цена за единицу, если есть в тексте")


# --- детерминированный результат should-cost ---
class ShouldCostLine(BaseModel):
    component: str
    qty: float
    rub_per_kg: float
    cost_rub: float


class ShouldCost(BaseModel):
    template: str
    lines: list[ShouldCostLine]
    materials_total: float
    conversion_cost: float
    sga_cost: float
    margin_cost: float
    target_unit_price: float
    actual_price_rub: Optional[float] = None
    gap_rub: Optional[float] = None
    gap_pct: Optional[float] = None


# --- итоговый выход агента ---
class SpecOutput(BaseModel):
    provider: str
    category: str
    attributes: list[SpecAttribute] = Field(default_factory=list)
    gold_plating_flags: list[GoldPlatingFlag] = Field(default_factory=list)
    should_cost: Optional[ShouldCost] = None
    notes: list[str] = Field(default_factory=list)
