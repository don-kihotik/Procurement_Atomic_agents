"""Pydantic-контракты для прототипа «Подготовка к переговорам»."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class NegotiationInput(BaseModel):
    raw_text: str = Field(description="Контекст: категория, поставщик, цели, ситуация")
    category_hint: Optional[str] = None
    current_price: Optional[float] = Field(default=None, description="Текущая/предложенная цена за единицу")
    should_cost: Optional[float] = Field(default=None, description="Оценка should-cost за единицу (из прототипа #1)")
    supplier_power: Optional[str] = Field(default=None, description="Сила поставщика: high | medium | low")


class Lever(BaseModel):
    key: str = Field(description="Ключ рычага из каталога")
    name: str = Field(default="", description="Русское название рычага")
    rationale: str = Field(description="Почему этот рычаг уместен здесь")


class Objection(BaseModel):
    supplier_says: str = Field(description="Возможное возражение поставщика")
    our_counter: str = Field(description="Наш контраргумент")


class NegotiationLLMOutput(BaseModel):
    levers: list[Lever] = Field(default_factory=list)
    objections: list[Objection] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    batna: str = Field(default="", description="Запасная позиция (что делаем, если не договорились)")


class PriceLadder(BaseModel):
    should_cost: float
    current_price: float
    overpay_gap: float
    opening_ask: float
    target_price: float
    walk_away: float
    expected_saving_pct: float
    realism_haircut: float


class NegotiationOutput(BaseModel):
    provider: str
    category: str
    recommended_levers: list[Lever] = Field(default_factory=list)
    price_ladder: Optional[PriceLadder] = None
    objections: list[Objection] = Field(default_factory=list)
    talking_points: list[str] = Field(default_factory=list)
    batna: str = ""
    notes: list[str] = Field(default_factory=list)
