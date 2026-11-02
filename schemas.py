from typing import Literal

from pydantic import BaseModel, Field

from telemetry import RunTelemetry


class FinancialAssumptions(BaseModel):
    """Loan and running-cost inputs chosen by the user, not the LLM."""

    down_payment_pct: float = Field(default=20.0, gt=0, le=100)
    annual_interest_rate: float = Field(default=8.5, ge=0)
    loan_term_years: int = Field(default=20, gt=0)
    vacancy_rate_pct: float = Field(default=5.0, ge=0, le=100)
    operating_expense_pct: float = Field(default=30.0, ge=0, le=100)


class PropertyPick(BaseModel):
    # No value limits on LLM output: a strict field fails parsing and loses the whole run.
    # build_report checks the values instead, so one bad pick is dropped on its own.
    name: str
    property_price: float
    monthly_rent: float
    currency: str = Field(description="ISO currency code, for example INR")
    source_url: str = Field(description="Web page the price or rent came from")


class AnalystReport(BaseModel):
    """What the LLM fills in. It has no fields for calculated metrics on purpose."""

    picks: list[PropertyPick] = Field(description="1 to 3 properties, best first")
    risk_score: int = Field(description="1 is lowest risk, 10 is highest")
    pros: list[str]
    cons: list[str]
    markdown_summary: str


class PropertyMetrics(BaseModel):
    net_operating_income: float
    cap_rate_pct: float
    monthly_emi: float
    annual_cash_flow: float
    cash_on_cash_return_pct: float


class ScoredPick(PropertyPick):
    metrics: PropertyMetrics


class InvestmentReportSchema(BaseModel):
    """The final report: LLM judgment plus metrics computed by Python."""

    picks: list[ScoredPick]
    rejected_picks: list[str] = Field(
        default_factory=list, description="Picks dropped for implausible price and rent data"
    )
    assumptions: FinancialAssumptions
    downside: PropertyMetrics = Field(description="Top pick under the stress test")
    roi_pct: float = Field(description="Top pick's first-year Cash-on-Cash Return")
    cap_rate_pct: float = Field(description="Top pick's Cap Rate")
    risk_score: int = Field(ge=1, le=10)
    pros: list[str]
    cons: list[str]
    markdown_summary: str


class AnalysisResult(BaseModel):
    """Markdown always exists; report is None if the LLM output could not be parsed."""

    markdown: str
    report: InvestmentReportSchema | None = None
    telemetry: RunTelemetry | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    # Location goes straight into the prompts, so limit it to what a place name needs.
    location: str = Field(
        min_length=2, max_length=100, pattern=r"^[^\W\d_][^\W_]*([ ,.'-]+[^\W_]+)*\.?$"
    )
    property_type: Literal["Residential", "Commercial", "Retail", "Industrial", "Mixed-Use"]
    assumptions: FinancialAssumptions = Field(default_factory=FinancialAssumptions)


class Job(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    result: AnalysisResult | None = None
    error: str | None = None
