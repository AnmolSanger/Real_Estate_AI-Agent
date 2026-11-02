from dotenv import load_dotenv

load_dotenv()

from crewai import Crew
from agents import (
    create_llm,
    create_property_researcher,
    create_financial_modeler,
    create_property_analyst,
)
from finance import calculate_metrics
from schemas import (
    AnalysisResult,
    FinancialAssumptions,
    InvestmentReportSchema,
    PropertyMetrics,
    ScoredPick,
)
from tasks import create_research_task, create_modeling_task, create_analysis_task

# Gemini's free tier allows 5 requests per minute; stay one under it.
MAX_REQUESTS_PER_MINUTE = 4


def score_pick(pick, assumptions):
    """Compute one property's metrics in Python, whatever the LLM wrote elsewhere."""
    metrics = calculate_metrics(pick.property_price, pick.monthly_rent, **assumptions.model_dump())
    return ScoredPick(**pick.model_dump(), metrics=PropertyMetrics(**metrics))


def build_report(analyst_report, assumptions):
    """Combine the LLM's judgment with Python-computed metrics."""
    if not analyst_report.picks:
        raise ValueError("The analyst returned no property picks")

    picks = [score_pick(pick, assumptions) for pick in analyst_report.picks]
    top_pick = picks[0]

    return InvestmentReportSchema(
        picks=picks,
        assumptions=assumptions,
        roi_pct=top_pick.metrics.cash_on_cash_return_pct,
        cap_rate_pct=top_pick.metrics.cap_rate_pct,
        risk_score=analyst_report.risk_score,
        pros=analyst_report.pros,
        cons=analyst_report.cons,
        markdown_summary=analyst_report.markdown_summary,
    )


def render_metrics_table(report):
    """Markdown table of the computed metrics, added to the end of the LLM's report."""
    assumptions = report.assumptions
    lines = [
        "## Verified Financial Metrics",
        "",
        "Calculated by the EstateMind finance engine, not by the LLM.",
        "",
        "| Property | Price | Monthly rent | NOI | Cap Rate | Monthly EMI | Annual cash flow | Cash-on-Cash |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for pick in report.picks:
        metrics = pick.metrics
        lines.append(
            f"| [{pick.name}]({pick.source_url}) | {pick.currency} {pick.property_price:,.0f} "
            f"| {pick.monthly_rent:,.0f} | {metrics.net_operating_income:,.0f} "
            f"| {metrics.cap_rate_pct:.2f}% | {metrics.monthly_emi:,.0f} "
            f"| {metrics.annual_cash_flow:,.0f} | {metrics.cash_on_cash_return_pct:.2f}% |"
        )

    lines += [
        "",
        f"Assumptions: {assumptions.down_payment_pct:g}% down payment, "
        f"{assumptions.annual_interest_rate:g}% interest, {assumptions.loan_term_years} year loan, "
        f"{assumptions.vacancy_rate_pct:g}% vacancy, {assumptions.operating_expense_pct:g}% operating costs.",
    ]
    return "\n".join(lines)


def build_result(crew_output, assumptions):
    """Use the structured output if it parsed, otherwise fall back to the raw text."""
    if crew_output.pydantic is None:
        return AnalysisResult(markdown=crew_output.raw)

    report = build_report(crew_output.pydantic, assumptions)
    markdown = f"{report.markdown_summary}\n\n{render_metrics_table(report)}"
    return AnalysisResult(markdown=markdown, report=report)


def run_analysis(location, property_type, assumptions=None):
    """Run the crew once and return the report.

    Agents and tasks are built per call so concurrent runs share no state.
    """
    assumptions = assumptions or FinancialAssumptions()

    llm = create_llm()
    researcher = create_property_researcher(llm)
    modeler = create_financial_modeler(llm)
    analyst = create_property_analyst(llm)

    research_task = create_research_task(location, property_type, researcher)
    modeling_task = create_modeling_task(assumptions, modeler, research_task)
    analysis_task = create_analysis_task(location, property_type, analyst, research_task, modeling_task)

    crew = Crew(
        agents=[researcher, modeler, analyst],
        tasks=[research_task, modeling_task, analysis_task],
        max_rpm=MAX_REQUESTS_PER_MINUTE,
        verbose=True,
    )

    return build_result(crew.kickoff(), assumptions)
