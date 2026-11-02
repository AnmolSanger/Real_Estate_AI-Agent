"""Run the crew on fixed markets and score the results.

These make real API calls, so they run by hand, not in CI:
    python -m evals.run_evals
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from evals.scorers import MAX_RENT_SPREAD_PCT, SCORERS, rent_spread_pct, score_run
from pipeline import run_analysis
from tasks import PROMPT_VERSION

# One market per property type. Pune repeats to measure how stable the inputs are.
CASES = [
    ("Pune", "Residential"),
    ("Bengaluru", "Commercial"),
    ("Mumbai", "Retail"),
    ("Chennai", "Industrial"),
    ("Hyderabad", "Mixed-Use"),
    ("Pune", "Residential"),
]

PAUSE_BETWEEN_RUNS_SECONDS = 30
RESULTS_DIR = Path(__file__).parent / "results"


def run_case(location, property_type):
    """Score one run. A failed run counts against every scorer rather than stopping the suite."""
    try:
        result = run_analysis(location, property_type)
    except Exception as error:
        return None, {name: False for name in SCORERS}, str(error)[:200]
    return result, score_run(result), None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=len(CASES), help="Run only the first N cases")
    cases = CASES[: parser.parse_args().cases]

    runs, results = [], []
    for number, (location, property_type) in enumerate(cases, start=1):
        print(f"[{number}/{len(cases)}] {property_type} in {location}", flush=True)
        result, scores, error = run_case(location, property_type)
        telemetry = result.telemetry if result else None
        runs.append(
            {
                "location": location,
                "property_type": property_type,
                "scores": scores,
                "error": error,
                "latency_seconds": telemetry.latency_seconds if telemetry else None,
                "total_tokens": telemetry.total_tokens if telemetry else None,
                "picks": [
                    {
                        "name": pick.name,
                        "price": pick.property_price,
                        "rent": pick.monthly_rent,
                        "source": pick.source_url,
                    }
                    for pick in (result.report.picks if result and result.report else [])
                ],
            }
        )
        if result:
            results.append((location, property_type, result))
        if number < len(cases):
            time.sleep(PAUSE_BETWEEN_RUNS_SECONDS)

    pass_rates = {
        name: round(sum(run["scores"][name] for run in runs) / len(runs) * 100) for name in SCORERS
    }
    repeat = [result for location, kind, result in results if (location, kind) == CASES[0]]

    summary = {
        "prompt_version": PROMPT_VERSION,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "runs_completed": len(results),
        "runs_total": len(runs),
        "pass_rates": pass_rates,
        "rent_spread_pct": rent_spread_pct(repeat),
        "max_rent_spread_pct": MAX_RENT_SPREAD_PCT,
        "runs": runs,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    path = RESULTS_DIR / f"{timestamp}-prompt-v{PROMPT_VERSION}.json"
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\nPrompt v{PROMPT_VERSION}: {len(results)}/{len(runs)} runs completed")
    for name, rate in pass_rates.items():
        print(f"  {name:<24}{rate}%")
    print(f"  {'rent_spread_pct':<24}{summary['rent_spread_pct']} (limit {MAX_RENT_SPREAD_PCT})")
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
