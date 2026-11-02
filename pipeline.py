from dotenv import load_dotenv

load_dotenv()

from crewai import Crew
from agents import (
    create_llm,
    create_property_researcher,
    create_financial_modeler,
    create_property_analyst,
)
from finance import (
    DOWNSIDE_RATE_INCREASE_PCT,
    DOWNSIDE_RENT_DROP_PCT,
    calculate_metrics,
    is_plausible_deal,
)
from schemas import (
    AnalysisResult,
    FinancialAssumptions,
    InvestmentReportSchema,
    PropertyMetrics,
    ScoredPick,
)
from storage import save_run
from tasks import (
    PROMPT_VERSION,
    create_research_task,
    create_modeling_task,
    create_analysis_task,
)
from telemetry import RunTelemetry

# Gemini's free tier allows 5 requests per minute; stay one under it.
MAX_REQUESTS_PER_MINUTE = 4


def score_pick(pick, assumptions):
    """Compute one property's metrics in Python, whatever the LLM wrote elsewhere."""
    metrics = calculate_metrics(pick.property_price, pick.monthly_rent, **assumptions.model_dump())
    return ScoredPick(**pick.model_dump(), metrics=PropertyMetrics(**metrics))


def downside_metrics(pick, assumptions):
    """Stress-test a property with lower rent and a higher interest rate."""
    stressed = assumptions.model_copy(
        update={"annual_interest_rate": assumptions.annual_interest_rate + DOWNSIDE_RATE_INCREASE_PCT}
    )
    lower_rent = pick.monthly_rent * (1 - DOWNSIDE_RENT_DROP_PCT / 100)
    return PropertyMetrics(**calculate_metrics(pick.property_price, lower_rent, **stressed.model_dump()))


def build_report(analyst_report, assumptions):
    """Combine the LLM's judgment with Python-computed metrics."""
    usable = [p for p in analyst_report.picks if is_plausible_deal(p.property_price, p.monthly_rent)]
    rejected = [p.name for p in analyst_report.picks if p not in usable]

    if not usable:
        raise ValueError("No property had a believable price and rent")

    picks = [score_pick(pick, assumptions) for pick in usable]
    top_pick = picks[0]

    return InvestmentReportSchema(
        picks=picks,
        rejected_picks=rejected,
        assumptions=assumptions,
        downside=downside_metrics(top_pick, assumptions),
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
    downside = report.downside
    lines += [
        "",
        f"Downside for {report.picks[0].name} (rent {DOWNSIDE_RENT_DROP_PCT}% lower, interest "
        f"{DOWNSIDE_RATE_INCREASE_PCT} point higher): Cap Rate {downside.cap_rate_pct:.2f}%, "
        f"monthly EMI {downside.monthly_emi:,.0f}, annual cash flow {downside.annual_cash_flow:,.0f}, "
        f"Cash-on-Cash {downside.cash_on_cash_return_pct:.2f}%.",
    ]
    if report.rejected_picks:
        lines += ["", f"Excluded for implausible price and rent data: {', '.join(report.rejected_picks)}."]
    return "\n".join(lines)


def build_result(crew_output, assumptions):
    """Use the structured output if it parsed, otherwise fall back to the raw text."""
    if crew_output.pydantic is None:
        return AnalysisResult(markdown=crew_output.raw)

    try:
        report = build_report(crew_output.pydantic, assumptions)
    except ValueError as error:
        # Keep the written analysis, but show no metrics rather than misleading ones.
        return AnalysisResult(
            markdown=f"{crew_output.pydantic.markdown_summary}\n\n> **Metrics unavailable:** {error}."
        )

    markdown =f"{report.markdown_summary}\n\n{render_metrics_table(report)}"
    return AnalysisResult(markdown=markdown, report=report)


def run_analysis(location, property_type, assumptions=None):
    """Run the crew once and return the report.

    Agents and tasks are built per call so concurrent runs share no state.
    """
    assumptions = assumptions or FinancialAssumptions()

    llm = create_llm()
    telemetry = RunTelemetry(
        location=location,
        property_type=property_type,
        model=llm.model,
        prompt_version=PROMPT_VERSION,
    )

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
        task_callback=telemetry.record_step,
        verbose=True,
    )

    try:
        crew_output = crew.kickoff()
        result = build_result(crew_output, assumptions)
    except Exception as error:
        # Keep a record of failed runs too: they are the ones you need to debug.
        telemetry.fail(error)
        save_run(telemetry.run_id, {"telemetry.json": telemetry.model_dump_json(indent=2)})
        raise

    telemetry.finish(crew_output.token_usage)
    result.telemetry = telemetry

    files = {
        "report.md": result.markdown,
        "telemetry.json": telemetry.model_dump_json(indent=2),
    }
    if result.report:
        files["report.json"] = result.report.model_dump_json(indent=2)
    result.artifacts = save_run(telemetry.run_id, files)

    return result
