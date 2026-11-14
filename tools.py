import json

from crewai.tools import tool
from crewai_tools import SerperDevTool

from finance import (
    MAX_GROSS_YIELD_PCT,
    MIN_GROSS_YIELD_PCT,
    average,
    calculate_metrics,
    is_plausible_deal,
)


def create_search_tool():
    return SerperDevTool()


@tool("Real Estate ROI Calculator")
def roi_calculator(
    property_prices: list[float],
    monthly_rents: list[float],
    down_payment_pct: float = 20,
    annual_interest_rate: float = 8.5,
    loan_term_years: int = 20,
    vacancy_rate_pct: float = 5,
    operating_expense_pct: float = 30,
    rent_change_pct: float = 0,
) -> str:
    """Average the price and rent samples for one property, then calculate NOI, Cap Rate,
    monthly EMI, annual cash flow and Cash-on-Cash Return.

    Pass every price sample and every rent sample you found for the property.
    For a downside case, set rent_change_pct, for example -10 for rent 10% lower.
    Always use this tool for financial metrics. Never calculate or average them yourself.
    Percentages are whole numbers, so 8.5 means 8.5%.
    """
    price = average(property_prices)
    rent = average(monthly_rents) * (1 + rent_change_pct / 100)

    # Return bad inputs as text so the agent can correct them instead of crashing the run.
    try:
        metrics = calculate_metrics(
            price,
            rent,
            down_payment_pct,
            annual_interest_rate,
            loan_term_years,
            vacancy_rate_pct,
            operating_expense_pct,
        )
    except ValueError as error:
        return f"Invalid input: {error}"

    # Caught here, the candidate is dropped before the Analyst writes about it.
    if not is_plausible_deal(price, rent):
        return (
            "Rejected: these prices and rents cannot describe the same kind of property, because yearly "
            f"rent is outside {MIN_GROSS_YIELD_PCT}-{MAX_GROSS_YIELD_PCT}% of the price. "
            "Check that every sample is for the same kind of unit, otherwise drop this candidate."
        )

    return json.dumps({"average_price": round(price, 2), "average_monthly_rent": round(rent, 2), **metrics})
