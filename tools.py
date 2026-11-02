import json

from crewai.tools import tool
from crewai_tools import SerperDevTool

from finance import calculate_metrics


def create_search_tool():
    return SerperDevTool()


@tool("Real Estate ROI Calculator")
def roi_calculator(
    property_price: float,
    monthly_rent: float,
    down_payment_pct: float = 20,
    annual_interest_rate: float = 8.5,
    loan_term_years: int = 20,
    vacancy_rate_pct: float = 5,
    operating_expense_pct: float = 30,
) -> str:
    """Calculate NOI, Cap Rate, monthly EMI, annual cash flow and Cash-on-Cash Return.

    Always use this tool for financial metrics. Never calculate them yourself.
    Percentages are whole numbers, so 8.5 means 8.5%.
    """
    # Return bad inputs as text so the agent can correct them instead of crashing the run.
    try:
        return json.dumps(
            calculate_metrics(
                property_price,
                monthly_rent,
                down_payment_pct,
                annual_interest_rate,
                loan_term_years,
                vacancy_rate_pct,
                operating_expense_pct,
            )
        )
    except ValueError as error:
        return f"Invalid input: {error}"
