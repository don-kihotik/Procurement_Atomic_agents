"""Pydantic-контракты для прототипа «Аналитик договора»."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ContractInput(BaseModel):
    raw_text: str = Field(description="Текст договора")
    party: str = Field(default="покупатель", description="Чью сторону защищаем: покупатель|поставщик")


class ContractFinding(BaseModel):
    category: str = Field(description="Ключ категории CUAD")
    category_label: str = Field(default="", description="Русское название категории")
    issue: str = Field(description="В чём риск/невыгода")
    severity: str = Field(description="low | medium | high")
    quote: str = Field(description="ДОСЛОВНАЯ цитата из договора (обязательно verbatim)")
    recommendation: str = Field(description="Предложенная правка")
    provenance_ok: Optional[bool] = Field(default=None, description="Прошла ли проверку провенанса R3")


class ContractLLMOutput(BaseModel):
    findings: list[ContractFinding] = Field(default_factory=list)


class ContractOutput(BaseModel):
    provider: str
    party: str
    findings_passed: list[ContractFinding] = Field(default_factory=list)
    findings_rejected: list[ContractFinding] = Field(
        default_factory=list, description="Отброшены: цитата не найдена в договоре (вероятная галлюцинация)"
    )
    summary: dict = Field(default_factory=dict, description="Счётчики по тяжести и провенансу")
    notes: list[str] = Field(default_factory=list)
