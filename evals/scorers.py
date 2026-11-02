"""Quality checks for one finished run. Each scorer returns True (pass) or False (fail)."""

import re
from urllib.parse import urlparse

from finance import calculate_metrics, is_plausible_deal

REQUIRED_SECTIONS = [
    "Executive Summary",
    "Top Investment Picks",
    "Market Overview",
    "Risk Matrix",
    "Final Recommendation",
]

# Useful for sentiment, but not a reliable source for a price or a rent.
SOCIAL_DOMAINS = ("youtube.com", "youtu.be", "instagram.com", "facebook.com", "x.com", "tiktok.com", "reddit.com")

# A calculated metric stated as a figure, like "Cap Rate is about 7.5" or "7.5% ROI".
# The LLM must not write these, but it may mention a metric without a number.
METRIC_NAME = r"(?:cap rates?|noi|net operating income|emi|cash[- ]on[- ]cash(?: return)?|cash flow|roi)"
METRIC_IN_TEXT = re.compile(
    rf"\b{METRIC_NAME}\b[\s:=~*(]*(?:(?:is|of|at|about|around|approximately|nearly|near)\s+)*[-−]?[₹$€£]?\s?\d"
    rf"|\d\s?%\s+{METRIC_NAME}\b",
    re.IGNORECASE,
)

MAX_RENT_SPREAD_PCT = 25


def schema_valid(result):
    return result.report is not None


def finance_tool_used(result):
    """The Modeler must have called the tool at least once for each pick."""
    if not result.report or not result.telemetry:
        return False
    return sum(step.tool_calls for step in result.telemetry.steps[1:2]) >= len(result.report.picks)


def numbers_match_engine(result):
    """Recalculate every metric independently of the pipeline."""
    if not result.report:
        return False
    assumptions = result.report.assumptions.model_dump()
    return all(
        pick.metrics.model_dump()
        == calculate_metrics(pick.property_price, pick.monthly_rent, **assumptions)
        for pick in result.report.picks
    )


def no_metrics_in_text(result):
    return bool(result.report) and not METRIC_IN_TEXT.search(result.report.markdown_summary)


def sections_present(result):
    return bool(result.report) and all(
        section.lower() in result.report.markdown_summary.lower() for section in REQUIRED_SECTIONS
    )


def plausible_inputs(result):
    return bool(result.report) and all(
        is_plausible_deal(pick.property_price, pick.monthly_rent) for pick in result.report.picks
    )


def is_reliable_source(url):
    parts = urlparse(url)
    host = parts.netloc.lower().removeprefix("www.")
    # Match whole domains, so netflix.com is not mistaken for x.com.
    is_social = any(host == domain or host.endswith(f".{domain}") for domain in SOCIAL_DOMAINS)
    return parts.scheme in ("http", "https") and bool(host) and not is_social


def reliable_sources(result):
    return bool(result.report) and all(
        is_reliable_source(pick.source_url) for pick in result.report.picks
    )


SCORERS = {
    "schema_valid": schema_valid,
    "finance_tool_used": finance_tool_used,
    "numbers_match_engine": numbers_match_engine,
    "no_metrics_in_text": no_metrics_in_text,
    "sections_present": sections_present,
    "plausible_inputs": plausible_inputs,
    "reliable_sources": reliable_sources,
}


def score_run(result):
    return {name: scorer(result) for name, scorer in SCORERS.items()}


def rent_spread_pct(results):
    """Largest rent difference for the same property across repeat runs of one market."""
    rents = {}
    for result in results:
        if result.report:
            for pick in result.report.picks:
                rents.setdefault(pick.name.strip().lower(), []).append(pick.monthly_rent)

    repeated = [values for values in rents.values() if len(values) > 1]
    if not repeated:
        return None
    return round(max((max(v) - min(v)) / min(v) * 100 for v in repeated), 1)
