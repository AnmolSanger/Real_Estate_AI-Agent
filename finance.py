"""Deterministic real estate formulas. Plain Python, no AI: same inputs, same outputs."""

# Yearly rent as a percentage of price. Outside this range, the price and rent
# almost certainly don't describe the same property (for example a per-sq-ft price).
MIN_GROSS_YIELD_PCT = 1
MAX_GROSS_YIELD_PCT = 15

# The stress test for the top pick.
DOWNSIDE_RENT_DROP_PCT = 10
DOWNSIDE_RATE_INCREASE_PCT = 1


def gross_yield_pct(property_price, monthly_rent):
    return monthly_rent * 12 / property_price * 100


def is_plausible_deal(property_price, monthly_rent):
    """Sanity-check LLM-sourced inputs, because correct math on bad inputs is still wrong."""
    return MIN_GROSS_YIELD_PCT <= gross_yield_pct(property_price, monthly_rent) <= MAX_GROSS_YIELD_PCT


def monthly_emi(loan_amount, annual_interest_rate, loan_term_years):
    """Fixed monthly payment: P * r * (1 + r)^n / ((1 + r)^n - 1)."""
    payments = loan_term_years * 12
    monthly_rate = annual_interest_rate / 100 / 12

    # The formula divides by zero at 0% interest, so split the loan evenly instead.
    if monthly_rate == 0:
        return loan_amount / payments

    growth = (1 + monthly_rate) ** payments
    return loan_amount * monthly_rate * growth / (growth - 1)


def net_operating_income(monthly_rent, vacancy_rate_pct, operating_expense_pct):
    """Yearly income after vacancy and running costs, before loan payments."""
    effective_rent = monthly_rent * 12 * (1 - vacancy_rate_pct / 100)
    return effective_rent * (1 - operating_expense_pct / 100)


def cap_rate(noi, property_price):
    """Return on the property's price as a percentage, ignoring the loan."""
    return noi / property_price * 100


def cash_on_cash_return(noi, emi, cash_invested):
    """First-year return on the cash actually invested, as a percentage."""
    annual_cash_flow = noi - emi * 12
    return annual_cash_flow / cash_invested * 100


def calculate_metrics(
    property_price,
    monthly_rent,
    down_payment_pct=20,
    annual_interest_rate=8.5,
    loan_term_years=20,
    vacancy_rate_pct=5,
    operating_expense_pct=30,
):
    """Validate the inputs and return every metric, rounded to 2 decimals."""
    if property_price <= 0 or monthly_rent <= 0:
        raise ValueError("property_price and monthly_rent must be greater than 0")
    if not 0 < down_payment_pct <= 100:
        raise ValueError("down_payment_pct must be above 0 and at most 100")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate cannot be negative")
    if loan_term_years <= 0:
        raise ValueError("loan_term_years must be greater than 0")
    if not 0 <= vacancy_rate_pct <= 100 or not 0 <= operating_expense_pct <= 100:
        raise ValueError("vacancy_rate_pct and operating_expense_pct must be from 0 to 100")

    down_payment = property_price * down_payment_pct / 100
    loan_amount = property_price - down_payment

    emi = monthly_emi(loan_amount, annual_interest_rate, loan_term_years)
    noi = net_operating_income(monthly_rent, vacancy_rate_pct, operating_expense_pct)

    return {
        "net_operating_income": round(noi, 2),
        "cap_rate_pct": round(cap_rate(noi, property_price), 2),
        "monthly_emi": round(emi, 2),
        "annual_cash_flow": round(noi - emi * 12, 2),
        "cash_on_cash_return_pct": round(cash_on_cash_return(noi, emi, down_payment), 2),
    }
