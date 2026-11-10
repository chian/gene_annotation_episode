"""Explicit measured-clock operands for numerical contract fixtures."""


def progress_time(seconds, *, first_seconds=10., decision_index=0,
                  run_id="fixture-run", episode_id="fixture-episode", query=False):
    origin = 1_000_000_000
    return {"version": "episode_progress_time_v1", "status": "available",
        "run_id": run_id, "episode_id": episode_id,
        "original_decision_index": None if query else decision_index,
        "point_kind": "decision_query" if query else "progress_receipt",
        "boot_id": "fixture-boot", "origin_decision_index": 0,
        "origin_monotonic_ns": origin,
        "observed_monotonic_ns": origin + round(seconds * 1e9),
        "reference_observation_monotonic_ns": origin + round(first_seconds * 1e9),
        "elapsed_seconds": seconds, "reference_elapsed_seconds": first_seconds,
        "unavailable_reason": None}


def contexts_at(seconds, *, first_seconds=10.):
    return tuple({"progress_time": progress_time(value, first_seconds=first_seconds,
                   decision_index=index)} for index, value in enumerate(seconds))
