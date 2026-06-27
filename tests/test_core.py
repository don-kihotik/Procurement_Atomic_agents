"""Тесты детерминированного ядра — без LLM, должны проходить в любой фазе."""
from procurement_agents.core.shouldcost import compute_static, build_should_cost


def test_compute_static_basic():
    r = compute_static(
        bom={"copper": 1.15, "pvc": 0.45, "steel": 0.08},
        prices={"copper": 920.0, "pvc": 180.0, "steel": 75.0},
        structure={"conversion_pct": 0.18, "sga_pct": 0.07, "margin_pct": 0.08},
        actual_price_rub=1850.0,
    )
    # материалы = 1.15*920 + 0.45*180 + 0.08*75 = 1058 + 81 + 6 = 1145
    assert r["materials_total"] == 1145.0
    assert abs(r["target_unit_price"] - 1561.33) < 0.5
    # фактическая 1850 заметно выше should-cost
    assert r["gap_rub"] > 250
    assert r["gap_pct"] > 15


def test_build_should_cost_template():
    r = build_should_cost("cable_power_cu", actual_price_rub=1850.0)
    assert r["template"] == "cable_power_cu"
    assert r["materials_total"] == 1145.0
    assert {l["component"] for l in r["lines"]} == {"copper", "pvc", "steel"}


def test_quantities_override():
    r = build_should_cost("cable_power_cu", quantities_kg={"copper": 2.0})
    # медь переопределена: 2.0*920=1840 + 81 + 6 = 1927
    assert r["materials_total"] == 1927.0
