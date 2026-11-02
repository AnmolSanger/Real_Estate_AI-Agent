import json

from tools import roi_calculator


def test_tool_returns_finance_engine_metrics():
    metrics = json.loads(roi_calculator.run(property_price=1_000_000, monthly_rent=10_000))

    assert metrics["net_operating_income"] == 79_800
    assert metrics["cap_rate_pct"] == 7.98


def test_tool_returns_bad_input_as_text():
    result = roi_calculator.run(property_price=0, monthly_rent=10_000)

    assert result.startswith("Invalid input")
