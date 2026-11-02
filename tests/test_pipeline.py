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


def make_pick(name, price, rent):
    return PropertyPick(
        name=name,
        property_price=price,
        monthly_rent=rent,
        currency="INR",
        source_url="https://example.com",
    )


def test_empty_picks_are_rejected():
    with pytest.raises(ValueError):
        pipeline.build_report(make_analyst_report(picks=[]), FinancialAssumptions())


def test_per_square_foot_price_is_excluded():
    # Seen in a live run: a price of 6,136 per sq ft treated as the whole price.
    picks = [make_pick("Per Sq Ft", 6_136, 30_000), make_pick("Real Price", 5_000_000, 25_000)]

    report = pipeline.build_report(make_analyst_report(picks), FinancialAssumptions())

    assert [pick.name for pick in report.picks] == ["Real Price"]
    assert report.rejected_picks == ["Per Sq Ft"]
    assert report.cap_rate_pct == 3.99


def test_mismatched_price_and_rent_is_excluded():
    picks = [make_pick("Mismatch", 43_800_000, 15_000), make_pick("Real Price", 5_000_000, 25_000)]

    report = pipeline.build_report(make_analyst_report(picks), FinancialAssumptions())

    assert report.rejected_picks == ["Mismatch"]


def test_all_implausible_picks_keep_the_text_but_show_no_metrics():
    crew_output = SimpleNamespace(
        pydantic=make_analyst_report([make_pick("Per Sq Ft", 6_136, 30_000)]), raw="raw text"
    )

    result = pipeline.build_result(crew_output, FinancialAssumptions())

    assert result.report is None
    assert result.markdown.startswith("# Report")
    assert "Metrics unavailable" in result.markdown


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


TOKEN_USAGE = SimpleNamespace(
    prompt_tokens=1_000_000,
    completion_tokens=100_000,
    total_tokens=1_100_000,
    successful_requests=9,
)


def patch_crew(monkeypatch, kickoff_error=None):
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("SERPER_API_KEY", "test-key")
    captured = {"saved": []}

    class FakeCrew:
        def __init__(self, agents, tasks, max_rpm, task_callback, verbose):
            captured.update(agents=agents, tasks=tasks, max_rpm=max_rpm)
            self.task_callback = task_callback

        def kickoff(self):
            if kickoff_error:
                raise kickoff_error
            self.task_callback(SimpleNamespace(agent="Researcher"))
            return SimpleNamespace(
                pydantic=make_analyst_report(), raw="raw text", token_usage=TOKEN_USAGE
            )

    def fake_save_run(run_id, files):
        captured["saved"].append(files)
        return {name: f"saved/{name}" for name in files}

    monkeypatch.setattr(pipeline, "Crew", FakeCrew)
    monkeypatch.setattr(pipeline, "save_run", fake_save_run)
    return captured


def test_run_analysis_records_telemetry_and_saves_artifacts(monkeypatch):
    captured = patch_crew(monkeypatch)

    result = pipeline.run_analysis("Dehradun", "Residential")

    assert result.telemetry.status == "success"
    assert result.telemetry.total_tokens == 1_100_000
    assert result.telemetry.llm_requests == 9
    assert [step.agent for step in result.telemetry.steps] == ["Researcher"]
    assert set(captured["saved"][0]) == {"report.md", "report.json", "telemetry.json"}
    assert result.artifacts["report.md"] == "saved/report.md"


def test_failed_run_saves_telemetry_and_raises(monkeypatch):
    captured = patch_crew(monkeypatch, kickoff_error=RuntimeError("503 UNAVAILABLE"))

    with pytest.raises(RuntimeError):
        pipeline.run_analysis("Dehradun", "Residential")

    saved = captured["saved"][0]
    assert list(saved) == ["telemetry.json"]
    assert '"status": "failed"' in saved["telemetry.json"]
    assert "503 UNAVAILABLE" in saved["telemetry.json"]


def test_run_analysis_wires_all_three_agents_in_order(monkeypatch):
    captured = patch_crew(monkeypatch)

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
