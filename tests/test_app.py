from pathlib import Path
from types import SimpleNamespace

from streamlit.testing.v1 import AppTest

import pipeline
from schemas import AnalysisResult
from telemetry import RunTelemetry
from tests.test_pipeline import make_analyst_report

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def submit_form(monkeypatch, fake_run_analysis):
    monkeypatch.setattr(pipeline, "run_analysis", fake_run_analysis)
    app = AppTest.from_file(APP_PATH, default_timeout=60).run()
    app.text_input[0].set_value("Dehradun")
    return app.button[0].click().run()


def test_structured_result_shows_metric_cards(monkeypatch):
    def fake_run(location, property_type, assumptions):
        crew_output = SimpleNamespace(pydantic=make_analyst_report(), raw="raw text")
        return pipeline.build_result(crew_output, assumptions)

    app = submit_form(monkeypatch, fake_run)

    assert not app.exception
    assert [metric.value for metric in app.metric][:2] == ["-26.69%", "2.99%"]
    assert app.metric[2].value == "6/10"


def test_telemetry_expander_shows_run_details(monkeypatch):
    telemetry = RunTelemetry(
        location="Pune", property_type="Retail", model="gemini-3.1-flash-lite", prompt_version="1"
    )
    telemetry.record_step(SimpleNamespace(agent="Researcher"))
    telemetry.finish(
        SimpleNamespace(
            prompt_tokens=1000, completion_tokens=200, total_tokens=1200, successful_requests=3
        )
    )

    def fake_run(*args):
        return AnalysisResult(
            markdown="report",
            telemetry=telemetry,
            artifacts={"report.md": "s3://bucket/reports/run1/report.md"},
        )

    app = submit_form(monkeypatch, fake_run)

    assert not app.exception
    assert {metric.label: metric.value for metric in app.metric}["Tokens"] == "1,200"
    assert {metric.label: metric.value for metric in app.metric}["Est. Paid Cost"] == "$0.0006"
    assert app.code[0].value == "s3://bucket/reports/run1/report.md"


def test_raw_result_shows_warning_instead_of_cards(monkeypatch):
    app = submit_form(monkeypatch, lambda *args: AnalysisResult(markdown="raw report"))

    assert not app.exception
    assert len(app.metric) == 0
    assert len(app.warning) == 1


def test_failed_run_shows_readable_error(monkeypatch):
    def failing_run(*args):
        raise RuntimeError("503 UNAVAILABLE")

    app = submit_form(monkeypatch, failing_run)

    assert not app.exception
    assert "503 UNAVAILABLE" in app.error[0].value
