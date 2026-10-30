import math
import random
import statistics
from typing import Any

import simpy


REGIONS = ("WR", "SR", "ER", "NR")
STAGES = ("SCRUTINY", "EVC")
ARRIVAL_RATE_PER_DAY = 1.2
SERVICE_MEDIAN_HOURS = {"SCRUTINY": 12.0, "EVC": 20.0}
SERVICE_SIGMA = {"SCRUTINY": 0.5, "EVC": 0.6}


def _percentile(samples: list[float], percentile: float) -> float:
    if not samples:
        return 0.0
    ordered = sorted(samples)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _simulate_queue(
    region: str,
    stage: str,
    officers: int,
    arrival_multiplier: float,
    service_multiplier: float,
    days: int,
    replications: int,
    seed: int,
) -> dict[str, float]:
    completed_times: list[float] = []
    backlog_samples: list[int] = []
    for replication in range(replications):
        rng = random.Random(seed + replication * 1009 + REGIONS.index(region) * 67 + STAGES.index(stage) * 7919)
        env = simpy.Environment()
        queue = simpy.Resource(env, capacity=max(1, officers))
        arrived = 0
        completed = 0

        def case_process(arrival_day: float):
            nonlocal completed
            with queue.request() as request:
                yield request
                service_hours = rng.lognormvariate(
                    math.log(SERVICE_MEDIAN_HOURS[stage] * service_multiplier),
                    SERVICE_SIGMA[stage],
                )
                yield env.timeout(service_hours / 8.0)
                completed_times.append((env.now - arrival_day) * 8.0)
                completed += 1

        def arrivals():
            nonlocal arrived
            while True:
                interval = rng.expovariate(ARRIVAL_RATE_PER_DAY * arrival_multiplier)
                yield env.timeout(interval)
                if env.now > days:
                    return
                arrived += 1
                env.process(case_process(env.now))

        env.process(arrivals())
        env.run(until=days)
        backlog_samples.append(max(0, arrived - completed))

    return {
        "p50_hours": round(_percentile(completed_times, 0.50), 2),
        "p90_hours": round(_percentile(completed_times, 0.90), 2),
        "mean_backlog": round(statistics.mean(backlog_samples), 2) if backlog_samples else 0,
    }


def run_simulation(
    additional_scrutiny_officers: dict[str, int] | None = None,
    arrival_multiplier: float = 1.0,
    service_multiplier: float = 1.0,
    replications: int = 30,
    days: int = 120,
    seed: int = 42,
) -> dict[str, Any]:
    if not 1 <= replications <= 100:
        raise ValueError("replications must be between 1 and 100")
    if not 1 <= days <= 365:
        raise ValueError("days must be between 1 and 365")
    if not 0.1 <= arrival_multiplier <= 5 or not 0.1 <= service_multiplier <= 5:
        raise ValueError("scenario multipliers must be between 0.1 and 5")

    base_officers = {
        "SCRUTINY": {"WR": 3, "SR": 3, "ER": 3, "NR": 2},
        "EVC": {region: 2 for region in REGIONS},
    }
    changed_officers = {stage: dict(region_counts) for stage, region_counts in base_officers.items()}
    for region, count in (additional_scrutiny_officers or {}).items():
        if region not in REGIONS or not 0 <= count <= 20:
            raise ValueError(f"invalid additional officer count for region {region}")
        changed_officers["SCRUTINY"][region] += count

    def evaluate(officer_counts: dict[str, dict[str, int]]) -> dict[str, dict[str, dict[str, float]]]:
        return {
            region: {
                stage: _simulate_queue(
                    region,
                    stage,
                    officer_counts[stage][region],
                    arrival_multiplier,
                    service_multiplier,
                    days,
                    replications,
                    seed,
                )
                for stage in STAGES
            }
            for region in REGIONS
        }

    return {
        "data_source": "synthetic",
        "notice": "Simulation under stated assumptions, not a forecast.",
        "assumptions": {
            "arrival_rate_per_working_day_per_region": ARRIVAL_RATE_PER_DAY,
            "service_median_hours": SERVICE_MEDIAN_HOURS,
            "service_sigma": SERVICE_SIGMA,
            "replications": replications,
            "working_days": days,
            "seed": seed,
            "additional_scrutiny_officers": additional_scrutiny_officers or {},
        },
        "baseline": evaluate(base_officers),
        "scenario": evaluate(changed_officers),
    }
