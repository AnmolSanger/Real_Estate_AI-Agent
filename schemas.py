from typing import Literal

from pydantic import BaseModel, Field, model_validator

from cities import INDIAN_CITIES, is_supported, to_location
from telemetry import RunTelemetry

# Mixed-use was removed: Indian property portals rarely list it, so the agents
# substituted ordinary commercial listings.
PROPERTY_TYPES = ("Residential", "Commercial", "Retail", "Industrial")


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
    unit_description: str = Field(
        description="The one kind of unit every sample describes, for example 2 BHK flat, about 1,000 sq ft"
    )
    price_samples: list[float] = Field(description="2-3 full asking prices for that kind of unit")
    rent_samples: list[float] = Field(description="2-3 monthly rents for that kind of unit")
    currency: str = Field(description="ISO currency code, for example INR")
    source_urls: list[str] = Field(description="The web page for each price and rent sample")


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
    # Averages of the samples, calculated in Python rather than by the LLM.
    property_price: float
    monthly_rent: float
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
    # Only listed Indian cities are accepted, so no free text reaches the prompts.
    state: Literal[tuple(INDIAN_CITIES)]
    city: str
    property_type: Literal[PROPERTY_TYPES]
    assumptions: FinancialAssumptions = Field(default_factory=FinancialAssumptions)

    @model_validator(mode="after")
    def check_city_is_listed(self):
        if not is_supported(self.state, self.city):
            raise ValueError(f"{self.city} is not a supported city in {self.state}")
        return self

    @property
    def location(self):
        return to_location(self.state, self.city)


class Job(BaseModel):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    result: AnalysisResult | None = None
    error: str | None = None
