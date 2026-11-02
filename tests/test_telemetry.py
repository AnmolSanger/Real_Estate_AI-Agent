from types import SimpleNamespace

from telemetry import RunTelemetry, estimate_cost


def make_telemetry(model="gemini-3.1-flash-lite"):
    return RunTelemetry(location="Pune", property_type="Retail", model=model, prompt_version="1")


def test_cost_uses_separate_input_and_output_prices():
    # 1M input at $0.25 plus 1M output at $1.50.
    assert estimate_cost("gemini-3.1-flash-lite", 1_000_000, 1_000_000) == 1.75


def test_unknown_model_has_no_cost_rather_than_a_guess():
    assert estimate_cost("some-new-model", 1000, 1000) is None


def test_finish_records_usage():
    telemetry = make_telemetry()
    usage = SimpleNamespace(
        prompt_tokens=1000, completion_tokens=200, total_tokens=1200, successful_requests=3
    )

    telemetry.finish(usage)

    assert telemetry.status == "success"
    assert telemetry.total_tokens == 1200
    assert telemetry.estimated_cost_usd == 0.00055
    assert telemetry.latency_seconds >= 0


def test_fail_records_a_shortened_error():
    telemetry = make_telemetry()

    telemetry.fail("x" * 1000)

    assert telemetry.status == "failed"
    assert len(telemetry.error) == 300


def test_runs_get_unique_ids():
    assert make_telemetry().run_id != make_telemetry().run_id
