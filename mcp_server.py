"""MCP server that lets any MCP client use the EstateMind finance engine."""

from mcp.server.fastmcp import FastMCP

from finance import calculate_metrics

mcp = FastMCP("EstateMind Finance")


@mcp.tool()
def calculate_roi_metrics(
    property_price: float,
    monthly_rent: float,
    down_payment_pct: float = 20,
    annual_interest_rate: float = 8.5,
    loan_term_years: int = 20,
    vacancy_rate_pct: float = 5,
    operating_expense_pct: float = 30,
) -> dict:
    """Calculate NOI, Cap Rate, monthly EMI, annual cash flow and Cash-on-Cash Return.

    Percentages are whole numbers, so 8.5 means 8.5%.
    """
    return calculate_metrics(
        property_price,
        monthly_rent,
        down_payment_pct,
        annual_interest_rate,
        loan_term_years,
        vacancy_rate_pct,
        operating_expense_pct,
    )


if __name__ == "__main__":
    # Stdio is the default transport: the client starts this script and talks over stdin/stdout.
    mcp.run()
