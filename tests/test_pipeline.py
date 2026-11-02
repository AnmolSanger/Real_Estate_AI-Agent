from types import SimpleNamespace

import pytest

import pipeline
from finance import calculate_metrics
from schemas import AnalystReport, FinancialAssumptions, PropertyPick


def make_analyst_report(picks=None):
    if picks is None:
        picks = [
            PropertyPick(
                name="Rajpur Road",
                property_price=8_000_000,
                monthly_rent=30_000,
                currency="INR",
                source_url="https://example.com/rajpur",
            ),
            PropertyPick(
                name="Sahastradhara Road",
                property_price=5_000_000,
                monthly_rent=25_000,
                currency="INR",
                source_url="https://example.com/sahastradhara",
            ),
        ]
    return AnalystReport(
        picks=picks,
        risk_score=6,
        pros=["Strong demand"],
        cons=["Low rental yield"],
        markdown_summary="# Report",
    )


def test_metrics_come_from_the_finance_engine():
    assumptions = FinancialAssumptions(annual_interest_rate=9)

    report = pipeline.build_report(make_analyst_report(), assumptions)

    expected = calculate_metrics(8_000_000, 30_000, **assumptions.model_dump())
    assert report.picks[0].metrics.model_dump() == expected
    assert report.roi_pct == expected["cash_on_cash_return_pct"]
    assert report.cap_rate_pct == expected["cap_rate_pct"]


def test_top_level_metrics_use_the_first_ranked_pick():
    report = pipeline.build_report(make_analyst_report(), FinancialAssumptions())

    assert report.cap_rate_pct == report.picks[0].metrics.cap_rate_pct
    assert report.cap_rate_pct != report.picks[1].metrics.cap_rate_pct


def test_empty_picks_are_rejected():
    with pytest.raises(ValueError):
        pipeline.build_report(make_analyst_report(picks=[]), FinancialAssumptions())


def test_structured_output_adds_verified_table():
    crew_output = SimpleNamespace(pydantic=make_analyst_report(), raw="raw text")

    result = pipeline.build_result(crew_output, FinancialAssumptions())

    assert result.report is not None
    assert result.markdown.startswith("# Report")
    assert "## Verified Financial Metrics" in result.markdown
    assert "2.99%" in result.markdown


def test_unparsed_output_falls_back_to_raw_text():
    crew_output = SimpleNamespace(pydantic=None, raw="raw text")

    result = pipeline.build_result(crew_output, FinancialAssumptions())

    assert result.report is None
    assert result.markdown == "raw text"


def test_run_analysis_wires_all_three_agents_in_order(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    captured = {}

    class FakeCrew:
        def __init__(self, agents, tasks, max_rpm, verbose):
            captured.update(agents=agents, tasks=tasks, max_rpm=max_rpm)

        def kickoff(self):
            return SimpleNamespace(pydantic=make_analyst_report(), raw="raw text")

    monkeypatch.setattr(pipeline, "Crew", FakeCrew)

    result = pipeline.run_analysis("Dehradun", "Residential")

    assert result.report is not None
    assert [agent.role for agent in captured["agents"]] == [
        "Senior Property Market Researcher",
        "Real Estate Financial Modeler",
        "Senior Investment Report Analyst",
    ]
    assert captured["tasks"][1].context == [captured["tasks"][0]]
    assert captured["tasks"][2].output_pydantic is AnalystReport
    assert captured["max_rpm"] == pipeline.MAX_REQUESTS_PER_MINUTE
