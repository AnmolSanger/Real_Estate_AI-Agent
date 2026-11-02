import pytest

from finance import calculate_metrics, cap_rate, monthly_emi, net_operating_income


def test_emi_matches_known_value():
    # Standard reference value: 1,00,000 at 12% for 20 years is 1,101.09 a month.
    assert monthly_emi(100_000, 12, 20) == pytest.approx(1101.09, abs=0.01)


def test_emi_at_zero_interest_splits_loan_evenly():
    assert monthly_emi(120_000, 0, 10) == 1000


def test_noi_applies_vacancy_then_expenses():
    # 120,000 rent -> 114,000 after 5% vacancy -> 79,800 after 30% expenses.
    assert net_operating_income(10_000, 5, 30) == pytest.approx(79_800)


def test_cap_rate():
    assert cap_rate(79_800, 1_000_000) == pytest.approx(7.98)


def test_calculate_metrics_with_negative_cash_flow():
    metrics = calculate_metrics(
        property_price=1_000_000,
        monthly_rent=10_000,
        annual_interest_rate=0,
        loan_term_years=10,
    )

    # 800,000 loan over 10 years costs 80,000 a year, just above the 79,800 NOI.
    assert metrics == {
        "net_operating_income": 79_800,
        "cap_rate_pct": 7.98,
        "monthly_emi": 6666.67,
        "annual_cash_flow": -200,
        "cash_on_cash_return_pct": -0.1,
    }


def test_full_cash_purchase_has_no_loan_payment():
    metrics = calculate_metrics(1_000_000, 10_000, down_payment_pct=100)

    assert metrics["monthly_emi"] == 0
    assert metrics["cash_on_cash_return_pct"] == metrics["cap_rate_pct"]


@pytest.mark.parametrize(
    "bad_input",
    [
        {"property_price": 0},
        {"monthly_rent": -1},
        {"down_payment_pct": 0},
        {"down_payment_pct": 101},
        {"annual_interest_rate": -1},
        {"loan_term_years": 0},
        {"vacancy_rate_pct": 101},
        {"operating_expense_pct": -1},
    ],
)
def test_rejects_invalid_inputs(bad_input):
    inputs = {"property_price": 1_000_000, "monthly_rent": 10_000, **bad_input}

    with pytest.raises(ValueError):
        calculate_metrics(**inputs)
