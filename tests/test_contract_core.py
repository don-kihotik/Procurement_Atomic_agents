"""Тесты валидатора провенанса R3 — детерминированно, без LLM."""
from procurement_agents.core.contract import quote_found, validate_findings
from procurement_agents.schemas.contract import ContractFinding

SRC = (
    "9.1. Договор автоматически продлевается на каждый следующий календарный год, "
    "если ни одна из сторон не уведомит о расторжении."
)


def test_quote_found_normalizes():
    # точная подстрока — найдена (нормализация пробелов/регистра)
    assert quote_found("автоматически продлевается на каждый следующий", SRC)
    # выдуманная цитата — не найдена
    assert not quote_found("Покупатель предоставляет банковскую гарантию", SRC)


def test_quote_found_quotes_dashes():
    src = "Цена фиксированная — изменению не подлежит «в течение срока»."
    assert quote_found("изменению не подлежит - изменению", src) is False
    assert quote_found('не подлежит "в течение срока"', src)


def test_validate_splits_passed_rejected():
    findings = [
        ContractFinding(category="auto_renewal", issue="x", severity="medium",
                        quote="автоматически продлевается на каждый следующий календарный год",
                        recommendation="y"),
        ContractFinding(category="indemnification", issue="x", severity="high",
                        quote="Покупатель возмещает все убытки в безусловном порядке",
                        recommendation="y"),
    ]
    passed, rejected = validate_findings(findings, SRC)
    assert len(passed) == 1 and passed[0].provenance_ok is True
    assert len(rejected) == 1 and rejected[0].provenance_ok is False
