"""Pydantic-контракты для кокпита «Аналитик договора» (экономическая линза)."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class CockpitInput(BaseModel):
    raw_text: str = Field(description="Текст договора")
    party: str = Field(default="покупатель", description="Чью сторону защищаем")


# ── то, что возвращает LLM (по каждой экономической категории) ──
class CategoryAssessment(BaseModel):
    key: str = Field(description="Ключ категории из таксономии")
    status: str = Field(description="GREEN | YELLOW | RED | MISSING")
    answer: str = Field(description="Что по факту в договоре и на кого риск (экономически)")
    quote: str = Field(default="", description="Дословная цитата из договора (пусто при MISSING)")
    risk_bearer: str = Field(default="", description="на кого риск: покупатель | поставщик | обе")


class CockpitLLMOutput(BaseModel):
    contract_type: str = Field(description="Тип договора: поставка | услуги | аренда | подряд | рамочный | иной")
    assessments: list[CategoryAssessment] = Field(default_factory=list)


# ── итоговый узел дерева (LLM + наш бенчмарк + провенанс) ──
class CategoryResult(BaseModel):
    key: str
    label: str
    cluster: str
    economic: bool
    status: str                  # GREEN | YELLOW | RED | MISSING | NA
    severity: str
    question: str
    answer: str = ""
    impact: str = ""
    risk_bearer: str = ""
    benchmark: str = ""
    redline: str = ""
    quote: str = ""
    provenance_ok: Optional[bool] = None


class ClusterGroup(BaseModel):
    name: str
    items: list[CategoryResult] = Field(default_factory=list)


class CockpitResult(BaseModel):
    provider: str
    model: str
    contract_type: str
    party: str
    clusters: list[ClusterGroup] = Field(default_factory=list)
    rejected: list[CategoryResult] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    money_note: str = ""
    notes: list[str] = Field(default_factory=list)
