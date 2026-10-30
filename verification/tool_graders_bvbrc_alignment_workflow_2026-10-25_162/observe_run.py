"""Retain a bounded read-only operator snapshot; this is not an episode action."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
OWNED = Path(__file__).resolve().parent
RUNS = ROOT / "verification/tool_graders_bvbrc_alignment_episode_flow_2026-10-25/runs"


def main():
    earlier = set(json.loads((OWNED / "EXISTING_RUN_DIRECTORIES.json").read_text()))
    start = json.loads((OWNED / "process-start.json").read_text())
    try:
        os.kill(start["pid"], 0)
        alive = True
    except ProcessLookupError:
        alive = False
    log = (OWNED / "pytest.log").read_text()
    result = {"observed_at": datetime.now(timezone.utc).isoformat(), "pytest_pid": start["pid"],
        "process_exists": alive, "pytest_terminal_receipt_present": (OWNED / "process-terminal.json").exists(),
        "passed_test_lines": [line for line in log.splitlines() if " PASSED " in line],
        "failed_or_error_test_lines": [line for line in log.splitlines()
                                      if " FAILED " in line or " ERROR " in line],
        "new_cases": []}
    for directory in sorted(RUNS.iterdir()):
        if not directory.is_dir() or directory.name in earlier:
            continue
        case = {"directory": str(directory.relative_to(ROOT)), "episodes": [],
                "workflow_closed_receipt_present": (directory / "SOURCE_GUARD_WORKFLOW_CLOSED.json").exists(),
                "after_tests_guard_present": (directory / "SOURCE_GUARD_AFTER_TESTS.json").exists()}
        database = directory / "state/state.sqlite3"
        if database.is_file():
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                for row in db.execute("SELECT episode_id,path,state,completion FROM runtime_episodes ORDER BY rowid"):
                    episode = dict(row)
                    episode["path"] = json.loads(episode["path"])
                    episode["role"] = episode["path"][-1][0]
                    episode["completion"] = json.loads(episode["completion"]) if episode["completion"] else None
                    episode["completed_actions"] = db.execute(
                        "SELECT count(*) FROM runtime_actions WHERE episode_id=? AND result IS NOT NULL",
                        (episode["episode_id"],)).fetchone()[0]
                    episode["observations"] = db.execute(
                        "SELECT count(*) FROM runtime_observations WHERE episode_id=?",
                        (episode["episode_id"],)).fetchone()[0]
                    episode["model_calls"] = db.execute(
                        "SELECT count(*) FROM runtime_model_calls WHERE episode_id=?",
                        (episode["episode_id"],)).fetchone()[0]
                    case["episodes"].append(episode)
        result["new_cases"].append(case)
    index = len(list(OWNED.glob("progress-[0-9][0-9][0-9].json"))) + 1
    output = OWNED / f"progress-{index:03}.json"
    with output.open("x") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"receipt": str(output.relative_to(ROOT)), "observed_at": result["observed_at"],
        "process_exists": alive, "passed_tests": len(result["passed_test_lines"]),
        "failed_or_error_tests": len(result["failed_or_error_test_lines"]),
        "cases": [{"directory": case["directory"], "after_tests_guard": case["after_tests_guard_present"],
            "episodes": [{key: episode[key] for key in ("role", "state", "completed_actions", "observations", "model_calls")}
                         for episode in case["episodes"]]} for case in result["new_cases"]]}))


if __name__ == "__main__":
    main()
