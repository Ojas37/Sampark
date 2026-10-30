from datetime import datetime, timezone
from datetime import date

from backend.app.services.workflow import business_seconds
from backend.app.services.simulator import run_simulation


def test_business_seconds_counts_only_workday_overlap() -> None:
    start = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 2, 8, 0, tzinfo=timezone.utc)
    assert business_seconds(start, end) == 8 * 60 * 60


def test_business_seconds_clips_partial_workday() -> None:
    start = datetime(2026, 10, 30, 3, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 30, 8, 0, tzinfo=timezone.utc)
    assert business_seconds(start, end) == int(3.5 * 60 * 60)


def test_business_seconds_skips_configured_holiday() -> None:
    start = datetime(2026, 11, 2, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 11, 3, 0, 0, tzinfo=timezone.utc)
    assert business_seconds(start, end, frozenset({date(2026, 11, 2)})) == 0


def test_simulation_is_deterministic_and_added_nr_capacity_reduces_p90() -> None:
    baseline = run_simulation(replications=3, days=40, seed=42)
    scenario = run_simulation(additional_scrutiny_officers={"NR": 2}, replications=3, days=40, seed=42)
    assert baseline["scenario"] == run_simulation(replications=3, days=40, seed=42)["scenario"]
    assert scenario["scenario"]["NR"]["SCRUTINY"]["p90_hours"] <= baseline["baseline"]["NR"]["SCRUTINY"]["p90_hours"]
