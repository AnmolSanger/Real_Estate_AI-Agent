from types import SimpleNamespace

import pytest

import pipeline
from evals import scorers
from schemas import AnalysisResult, FinancialAssumptions
from telemetry import RunTelemetry, StepRecord
from tests.test_pipeline import make_analyst_report, make_pick

GOOD_SUMMARY = """## Executive Summary
Demand is strong, but cash flow is negative after 2024 price growth of 12 percent.
## Top Investment Picks
## Market Overview
## Risk Matrix
## Final Recommendation"""


def make_result(modeler_tool_calls=3, summary=GOOD_SUMMARY, picks=None):
    analyst_report = make_analyst_report(picks)
    analyst_report.markdown_summary = summary
    result = pipeline.build_result(
        SimpleNamespace(pydantic=analyst_report, raw="raw"), FinancialAssumptions()
    )
    result.telemetry = RunTelemetry(
        location="Pune",
        property_type="Retail",
        model="test",
        prompt_version="1",
        steps=[
            StepRecord(agent="Researcher", finished_after_seconds=1, tool_calls=5),
            StepRecord(agent="Modeler", finished_after_seconds=2, tool_calls=modeler_tool_calls),
            StepRecord(agent="Analyst", finished_after_seconds=3),
        ],
    )
    return result


def test_a_good_run_passes_every_scorer():
    scores = scorers.score_run(make_result())

    assert all(scores.values()), scores


def test_a_run_without_a_report_fails_every_scorer():
    scores = scorers.score_run(AnalysisResult(markdown="raw text"))

    assert not any(scores.values())


def test_skipping_the_finance_tool_fails():
    assert not scorers.finance_tool_used(make_result(modeler_tool_calls=0))


def test_researcher_searches_do_not_count_as_finance_tool_calls():
    result = make_result(modeler_tool_calls=1)

    assert not scorers.finance_tool_used(result)


def test_changed_metric_fails_the_recalculation():
    result = make_result()
    result.report.picks[0].metrics.cap_rate_pct = 99

    assert not scorers.numbers_match_engine(result)


@pytest.mark.parametrize(
    "text",
    [
        "The Cap Rate is about 7.5% here.",
        "It offers a 7.5% cap rate.",
        "Monthly EMI: ₹55,000",
        "ROI of -12%",
        "**NOI**: 2,39,400",
    ],
)
def test_metric_written_by_the_llm_fails(text):
    result = make_result(summary=f"{GOOD_SUMMARY}\n{text}")

    assert not scorers.no_metrics_in_text(result)


@pytest.mark.parametrize(
    "text",
    [
        "Cash flow is negative after 2024 price growth of 12 percent.",
        "The ROI improves over 5 years.",
        "The EMI burden is high.",
    ],
)
def test_metric_mentioned_without_a_figure_passes(text):
    result = make_result(summary=f"{GOOD_SUMMARY}\n{text}")

    assert scorers.no_metrics_in_text(result)


def test_missing_section_fails():
    result = make_result(summary=GOOD_SUMMARY.replace("## Risk Matrix", ""))

    assert not scorers.sections_present(result)


def test_social_media_source_fails():
    result = make_result()
    result.report.picks[1].source_url = "https://www.instagram.com/reel/abc/"

    assert not scorers.reliable_sources(result)


def test_lookalike_domain_is_not_treated_as_social():
    assert scorers.is_reliable_source("https://www.netflix.com/title")
    assert scorers.is_reliable_source("https://www.99acres.com/property")
    assert not scorers.is_reliable_source("not a url")


def test_rent_spread_compares_the_same_property_across_runs():
    first = make_result(picks=[make_pick("Baner", 5_000_000, 20_000)])
    second = make_result(picks=[make_pick("baner ", 5_000_000, 30_000)])

    assert scorers.rent_spread_pct([first, second]) == 50


def test_rent_spread_is_none_without_repeated_properties():
    only = make_result(picks=[make_pick("Baner", 5_000_000, 20_000)])

    assert scorers.rent_spread_pct([only]) is None
