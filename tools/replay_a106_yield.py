"""Replay saved A106 continuation decisions without models, tools or networking.

Each candidate uses only the fitted history available at that decision. Later
observations describe what would be omitted on the recorded path, not a forecast
or a claim about how an autonomous parent would respond to an earlier return.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_trace(run):
    db = sqlite3.connect((run / "state/state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        runs = db.execute("SELECT run_id,settings FROM runtime_runs").fetchall()
        if len(runs) != 1:
            raise ValueError("one_original_run_required")
        run_id, settings = runs[0]["run_id"], json.loads(runs[0]["settings"])
        episodes = []
        for episode in db.execute("SELECT episode_id,initial_credit,path FROM runtime_episodes WHERE run_id=?", (run_id,)):
            eid = episode["episode_id"]
            observations = []
            for row in db.execute("SELECT unit_index,observation FROM runtime_observations WHERE run_id=? AND episode_id=? ORDER BY unit_index", (run_id, eid)):
                value = json.loads(row["observation"])
                step = value["step"]
                observations.append(dict(unit_index=row["unit_index"], decision_index=value["decision_index"],
                    credit=step["credit"], marginal_credit=step["marginal_credit"],
                    estimate=step["estimate"], decision=step["decision"]))
            if not observations:
                continue
            actions = [dict(row) for row in db.execute("SELECT decision_index, json_extract(action,'$.kind') AS kind, "
                "json_extract(action,'$.tool') AS tool, json_extract(result,'$.status') AS status, "
                "json_extract(timing,'$.intervals[#-1].ended_at') AS ended_at "
                "FROM runtime_actions WHERE run_id=? AND episode_id=? ORDER BY decision_index", (run_id, eid))]
            first = db.execute("SELECT json_extract(timing,'$.intervals[0].started_at') FROM runtime_model_calls "
                "WHERE run_id=? AND episode_id=? ORDER BY call_index LIMIT 1", (run_id, eid)).fetchone()
            episodes.append(dict(episode_id=eid, path=json.loads(episode["path"]),
                initial_credit=episode["initial_credit"], observations=observations, actions=actions,
                first_decision_started_at=first[0] if first else None))
        return dict(run_directory=str(run), run_id=run_id, controller=settings["controller"], episodes=episodes)
    finally:
        db.close()


def band_at_alpha(estimate, alpha, numerical):
    saved = estimate["expected_next_gain"]
    if saved["status_code"] != numerical.STATUS_NORMAL:
        return numerical.NumericBand(**saved)
    diagnostics = estimate["diagnostics"]
    if "gain_component" in diagnostics:
        gain = band_at_alpha(diagnostics["gain_component"], alpha / 2, numerical)
        loss = band_at_alpha(diagnostics["loss_component"], alpha / 2, numerical)
        return numerical.SignedNumericBand(gain.value-loss.value, gain.lower-loss.upper,
            gain.upper-loss.lower, alpha=alpha)
    return numerical.NumericBand.laplace(saved["value"], diagnostics["next_gain_variance"], alpha)


def validate_trace(episode, numerical):
    previous = episode["initial_credit"]
    actions = {row["decision_index"] for row in episode["actions"]}
    for index, row in enumerate(episode["observations"]):
        if row["unit_index"] != index or row["estimate"]["turns"] != index + 1 or row["decision_index"] not in actions:
            raise ValueError("observation_identity_mismatch")
        if not math.isclose(row["credit"] - previous, row["marginal_credit"], abs_tol=1e-12):
            raise ValueError("raw_credit_delta_mismatch")
        previous = row["credit"]
        estimate = row["estimate"]
        if estimate["provenance"]["estimator"] != numerical.ESTIMATOR_VERSION:
            raise ValueError("original_estimator_version_mismatch")
        band = band_at_alpha(estimate, estimate["parameters"]["uncertainty_alpha"], numerical)
        saved = estimate["expected_next_gain"]
        if any(not math.isclose(getattr(band, key), saved[key], rel_tol=1e-10, abs_tol=1e-12)
               for key in ("value", "lower", "upper")):
            raise ValueError("original_band_replay_mismatch")
        decision = numerical.predicted_gain_upper_bound(band, row["decision"]["continuation_cost"])
        if decision.stop != row["decision"]["stop"]:
            raise ValueError("original_decision_replay_mismatch")


def replay(episode, *, cost, alpha, numerical):
    rows = episode["observations"]
    selected = None
    for index, row in enumerate(rows):
        band = band_at_alpha(row["estimate"], alpha, numerical)
        if numerical.predicted_gain_upper_bound(band, cost).stop:
            selected = (index, row, band)
            break
    if selected is None:
        return dict(cost=cost, alpha=alpha, stop=None)
    index, row, band = selected
    actions = [action for action in episode["actions"] if action["decision_index"] <= row["decision_index"]]
    start, end = episode.get("first_decision_started_at"), actions[-1]["ended_at"]
    elapsed = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).total_seconds() if start and end else None
    return dict(cost=cost, alpha=alpha, stop=dict(observation=index+1, decision_index=row["decision_index"],
        cumulative_credit=row["credit"], upper=band.upper, expected=band.value,
        recorded_action_completion_seconds=elapsed,
        later_recorded_credit=rows[-1]["credit"]-row["credit"],
        later_recorded_observations=len(rows)-index-1,
        completed_grading_actions=sum(a["tool"] == "literature.intervention_grading.populate" and a.get("status") == "completed" for a in actions),
        completed_finalization_actions=sum(a["tool"] == "literature.a106.finalize" and a.get("status") == "completed" for a in actions)))


def discovery_tradeoff(episode, alpha, numerical):
    """Describe the full fixed-cost tradeoff; never use this to make a decision."""
    rows = episode["observations"]
    first = next((i for i, row in enumerate(rows) if row["marginal_credit"] > 0), None)
    if first is None:
        return dict(alpha=alpha, status="no_positive_credit_in_recorded_history")
    def minimum(selected):
        bands = [band_at_alpha(row["estimate"], alpha, numerical) for row in selected]
        available = [band.upper for band in bands if band.status_code == numerical.STATUS_NORMAL]
        return min(available) if available else None
    before, after = minimum(rows[:first]), minimum(rows[first:])
    return dict(alpha=alpha, status="descriptive_retrospective_tradeoff",
        first_positive_decision=rows[first]["decision_index"],
        cost_must_be_strictly_below_to_reach_first_positive=before,
        minimum_cost_that_can_stop_from_first_positive_onward=after,
        fixed_cost_can_reach_first_positive_and_stop_later=(after is not None and (before is None or after < before)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--costs", type=float, nargs="+", default=[.001, .003, .005, .006, .0075, .01, .02, .03, .05, .1, .2, .35])
    parser.add_argument("--alphas", type=float, nargs="+", default=[.05, .1, .2])
    parser.add_argument("--verify-fit-prefixes", type=int, nargs="*", default=[])
    parser.add_argument("--profile", type=Path,
        default=Path(__file__).resolve().parents[1] / "tests/fixtures/a106_evaluation/yield-controller.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output_dir.resolve()
    if not output.is_relative_to(root / "runs"):
        parser.error("output must be beneath runs/")
    original = args.run[0].resolve() / "source"
    pins = json.loads((args.run[0] / "source-pins.json").read_text())
    checked = {}
    for name in ("gene_annotation_episode/numerical.py", "gene_annotation_episode/vendor/nano_rarefaction.py"):
        checked[name] = digest(original / name)
        if pins[name] != checked[name]:
            raise ValueError("original_estimator_source_changed")
    sys.path.insert(0, str(original))
    from gene_annotation_episode import numerical
    profile = json.loads(args.profile.read_text())
    if profile["estimator"] != numerical.ESTIMATOR_VERSION:
        raise ValueError("selected_profile_requires_its_original_estimator")
    profile_settings = profile["controller"]
    numerical.YieldController("profile-validation", 0, profile_settings["cost"],
        {key: value for key, value in profile_settings.items() if key != "cost"})
    report = dict(version="a106_yield_replay_v1", original_source=str(original), source_sha256=checked,
        replay_driver_sha256=digest(Path(__file__)), selected_profile=profile, profile_sha256=digest(args.profile),
        estimator_version=numerical.ESTIMATOR_VERSION, cases=[], fit_checks=[],
        limitations=["Replay assumes recorded actions and credits remain unchanged until the first yield decision.",
            "This is a controller replay, not an autonomous report or parent-return replay.",
            "Later retained credit is descriptive hindsight and is never an input to a candidate decision.",
            "The old trace has no progress_time receipts required by the newer real-time estimator."])
    output.mkdir(parents=True, exist_ok=True)
    for run in args.run:
        trace = read_trace(run)
        if any(digest(run / "source" / name) != sha for name, sha in checked.items()):
            raise ValueError("comparison_run_estimator_source_mismatch:" + str(run))
        (output / (run.name + "-trace.json")).write_text(json.dumps(trace, indent=2) + "\n")
        for episode in trace["episodes"]:
            validate_trace(episode, numerical)
            rows = episode["observations"]
            if any(row["estimate"]["parameters"].get(key) != profile_settings[key]
                   for row in rows for key in ("window_size", "subsample_size")):
                raise ValueError("saved_fit_availability_differs_from_selected_profile")
            result = dict(run_directory=str(run), episode_id=episode["episode_id"], path=episode["path"],
                observations=len(rows), final_credit=rows[-1]["credit"],
                positive_observations=sum(row["marginal_credit"] > 0 for row in rows),
                first_positive_decision=next((r["decision_index"] for r in rows if r["marginal_credit"] > 0), None),
                selected=replay(episode, cost=profile_settings["cost"], alpha=profile_settings["uncertainty_alpha"], numerical=numerical),
                discovery_tradeoffs=[discovery_tradeoff(episode, alpha, numerical) for alpha in args.alphas],
                candidates=[replay(episode, cost=cost, alpha=alpha, numerical=numerical)
                    for alpha in args.alphas for cost in args.costs])
            report["cases"].append(result)
            if run == args.run[0]:
                for count in args.verify_fit_prefixes:
                    if count > len(rows):
                        continue
                    selected = rows[count-1]
                    estimate = numerical.estimate_score_yield([r["marginal_credit"] for r in rows[:count]],
                        selected["estimate"]["parameters"])
                    actual, expected = estimate.expected_next_gain, selected["estimate"]["expected_next_gain"]
                    if actual.status_code != expected["status_code"] or any(
                            not math.isclose(getattr(actual, key), expected[key], rel_tol=1e-7, abs_tol=1e-10)
                            for key in ("value", "lower", "upper")):
                        raise ValueError("original_fit_recomputation_mismatch")
                    report["fit_checks"].append(dict(episode_id=episode["episode_id"], observations=count,
                        expected_next_gain=actual.as_record(), matched=True))
                    print(json.dumps(dict(verified_fit_prefix=count)), flush=True)
    (output / "replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(cases=len(report["cases"]), fit_checks=len(report["fit_checks"]),
        report=str(output / "replay.json"))), flush=True)


if __name__ == "__main__":
    main()
