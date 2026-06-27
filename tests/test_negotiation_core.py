"""Тесты ядра подготовки к переговорам — детерминированно, без LLM."""
from procurement_agents.core.negotiation import price_ladder, select_lever_keys, LEVERS


def test_price_ladder_math():
    r = price_ladder(should_cost=1561.0, current_price=1850.0, realism_haircut=0.5)
    assert r["overpay_gap"] == 289.0
    assert r["opening_ask"] == round(1561.0 * 1.05, 2)   # 1639.05
    assert r["target_price"] == 1705.5                    # 1850 - 289*0.5
    assert r["walk_away"] == 1850.0
    assert 7.0 < r["expected_saving_pct"] < 8.5


def test_price_ladder_skipped_without_inputs():
    assert price_ladder(should_cost=None, current_price=1850.0) is None
    assert price_ladder(should_cost=1561.0, current_price=None) is None


def test_select_levers_by_power():
    high = select_lever_keys("high")
    low = select_lever_keys("low")
    assert high[0] == "re_specification"
    assert "tendering" in low
    # все выбранные ключи есть в каталоге
    assert all(k in LEVERS for k in high + low)
