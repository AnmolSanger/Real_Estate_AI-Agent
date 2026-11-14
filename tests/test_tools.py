import json

from tools import roi_calculator


def test_tool_returns_finance_engine_metrics():
    metrics = json.loads(roi_calculator.run(property_prices=[1_000_000], monthly_rents=[10_000]))

    assert metrics["net_operating_income"] == 79_800
    assert metrics["cap_rate_pct"] == 7.98


def test_tool_averages_the_samples():
    metrics = json.loads(
        roi_calculator.run(property_prices=[900_000, 1_100_000], monthly_rents=[9_000, 11_000, 0])
    )

    assert metrics["average_price"] == 1_000_000
    assert metrics["average_monthly_rent"] == 10_000
    assert metrics["cap_rate_pct"] == 7.98


def test_tool_applies_the_downside_rent_change():
    metrics = json.loads(
        roi_calculator.run(property_prices=[1_000_000], monthly_rents=[10_000], rent_change_pct=-10)
    )

    assert metrics["average_monthly_rent"] == 9_000


def test_tool_rejects_per_square_foot_price():
    result = roi_calculator.run(property_prices=[6_136], monthly_rents=[30_000])

    assert result.startswith("Rejected")


def test_tool_returns_bad_input_as_text():
    result = roi_calculator.run(property_prices=[0], monthly_rents=[10_000])

    assert result.startswith("Invalid input")
