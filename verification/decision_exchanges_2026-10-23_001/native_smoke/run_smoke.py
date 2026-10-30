"""One isolated configured-model exchange check with synthetic execution state."""
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


DIRECTORY = Path(__file__).resolve().parent
REPOSITORY = DIRECTORY.parents[2]
sys.path.insert(0, str(REPOSITORY))
sys.path.insert(0, str(REPOSITORY / "tests"))

from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.runtime import run_workflow
from test_runtime import FixtureController, FixtureStore, FixtureTools, fixture_credit


GOAL = """Engineering protocol check using synthetic fixtures only; this is not a
biological investigation. For your FIRST response, use request_context with the
exact own-attempt lookup: view=own_attempts, category=null,
decision_indices=null, offset=0, limit=3. After the decision_lookup_result
arrives, use select_action with selection kind=tool, tool=fixture.measure and
arguments result=completed, page=0, and report_update={}. This is the complete
requested engineering check; choose no other work. The supplied synthetic
controller will stop after the one completed fixture action."""


def now():
    return datetime.now(timezone.utc).isoformat()


def count(store, table):
    present = store.db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone()
    return 0 if present is None else store.db.execute("SELECT count(*) FROM " + table).fetchone()[0]


async def main():
    config = load_config()
    assert config["REASONING"] == {"model": "gpt-6-sol", "reasoning_effort": "medium"}
    store = FixtureStore(DIRECTORY / "synthetic-state.sqlite3")
    tools = FixtureTools(store)
    summary = {"version": "decision_exchange_native_smoke_v1", "started_at": now(),
        "scope": "synthetic engineering protocol check; no biological claims",
        "configured_reasoning": config["REASONING"], "decision_protocol": "decision_exchange_v1",
        "controller": {"fixture": "FixtureController", "stop_after_completed_actions": 1},
        "goal": GOAL, "automatic_retries": 0}
    try:
        async with ModelConnection(config, DIRECTORY / "provider-audit", DIRECTORY) as provider:
            result = await run_workflow(store, tools, provider=provider,
                run_dir=DIRECTORY / "run", controller_factory=lambda episode_path, initial:
                    FixtureController(str(episode_path), initial, 1),
                project_credit=fixture_credit, episode_binding_factories=(),
                decision_protocol="decision_exchange_v1", goal=GOAL)
        summary.update(status="completed", result=result)
    except BaseException as error:
        summary.update(status="failed", failure={"exception_type": type(error).__name__,
            "message": str(error), "diagnostic": getattr(error, "diagnostic", None)})
    finally:
        summary["counts"] = {"logical_decisions": count(store, "runtime_model_calls"),
            "physical_exchanges": count(store, "runtime_decision_exchanges"),
            "actions": count(store, "runtime_actions"),
            "completion_slots": count(store, "runtime_completion_slots"),
            "observations": count(store, "runtime_observations"),
            "fixture_executions": tools.executions, "fixture_commits": tools.commits}
        exchange_rows = store.db.execute("SELECT exchange_index,response,lookup_result FROM "
            "runtime_decision_exchanges ORDER BY decision_index,exchange_index").fetchall()
        summary["public_exchange_results"] = [{"exchange_index": row["exchange_index"],
            "response": None if row["response"] is None else json.loads(row["response"]),
            "lookup_status": None if row["lookup_result"] is None else
                json.loads(row["lookup_result"]).get("status")} for row in exchange_rows]
        # Inspect only provider request/response/session metadata. Never open
        # events.jsonl, private reasoning items or transport event streams.
        requests = list((DIRECTORY / "provider-audit").glob("session-*/call-*/request.json"))
        sessions = [json.loads(path.read_text()) for path in
            (DIRECTORY / "provider-audit").glob("session-*/session-*.json")]
        summary["counts"]["provider_calls"] = len(requests)
        summary["counts"]["native_threads"] = len({item["thread_id"] for item in sessions})
        summary["counts"]["public_typed_responses"] = len(list(
            (DIRECTORY / "provider-audit").glob("session-*/call-*/response.json")))
        summary["completed_at"] = now()
        (DIRECTORY / "smoke-summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
        store.db.close()
        print(json.dumps({key: summary.get(key) for key in ("status", "failure", "counts")}, indent=2))
    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
