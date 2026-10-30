"""Bounded public runtime snapshots, excluding provider histories and secrets."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys

BASE = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent


def observe(label, expected_start):
    directory = BASE / f"literature_model_run_{label}/live_001"
    process = json.loads((directory / "PROCESS.json").read_bytes())
    pid = process["pid"]
    path = Path("/proc") / str(pid) / "stat"
    fields = path.read_text().rsplit(")", 1)[1].split() if path.exists() else None
    identity = {"pid": pid, "handle_present": fields is not None,
        "state": fields[0] if fields else None, "start_ticks": fields[19] if fields else None,
        "original_start_ticks_match": fields is not None and fields[19] == expected_start}
    with sqlite3.connect((directory / "state/state.sqlite3").resolve().as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("begin")
        tables = {row[0] for row in db.execute("select name from sqlite_master where type='table'")}
        names = ("runtime_actions", "runtime_observations", "runtime_forms", "runtime_report_attempts",
            "runtime_model_calls", "literature_rate_operations", "literature_rate_source_received")
        counts = {name: db.execute("select count(*) from " + name).fetchone()[0] for name in names if name in tables}
        tools = Counter()
        attempts = []
        for row in db.execute("select run_id,episode_id,decision_index,action,result,credit from runtime_actions order by rowid"):
            action = json.loads(row["action"])
            tool = action.get("tool")
            tools[tool or action.get("type", "other")] += 1
            if tool != "literature.rate.source.populate":
                continue
            result = json.loads(row["result"]) if row["result"] else None
            feedback = (result.get("feedback") or {}) if result else {}
            attempts.append({"run_id": row["run_id"], "episode_id": row["episode_id"],
                "decision_index": row["decision_index"], "status": result.get("status") if result else None,
                "error_code": feedback.get("code"), "feedback_keys": sorted(feedback), "credit": row["credit"]})
        populations = []
        if "literature_rate_operations" in tables:
            for row in db.execute("select run_id,episode_id,operation_key,outcome from literature_rate_operations order by rowid"):
                result = json.loads(row["outcome"])["result"]
                cells = result.get("cells", {})
                populations.append({"run_id": row["run_id"], "episode_id": row["episode_id"],
                    "operation_key": row["operation_key"], "sheet_ref": result.get("sheet_ref"),
                    "cell_count": len(cells), "nonnull_cell_count": sum(c.get("value") is not None for c in cells.values()),
                    "cells": {name: {key: cell.get(key) for key in
                        ("value", "threshold", "bound", "status", "unit", "unavailable_reason")}
                        for name, cell in cells.items()}})
    return {"process": identity, "counts": counts, "selected_action_categories": dict(tools),
        "native_population_attempts": attempts, "saved_population_operations": populations,
        "nonnull_numerical_population_present": any(row["nonnull_cell_count"] for row in populations),
        "terminal_result_file_present": (directory / "RESULT.json").exists()}


def main():
    name = sys.argv[1]
    assert name.startswith("BOUNDARY_") and name.endswith(".json") and "/" not in name
    result = {"utc": datetime.now(timezone.utc).isoformat(),
        "meaning": "Coherent read-only public runtime snapshots; no source interpretation, private provider/model history, execution tokens or state mutation",
        "runs": {label: observe(label, start) for label, start in (("024", "82830508"), ("030", "83497104"))}}
    with (OUT / name).open("x") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"utc": result["utc"], "runs": {label: {"process": row["process"],
        "counts": row["counts"], "nonnull_numerical_population_present": row["nonnull_numerical_population_present"],
        "terminal_result_file_present": row["terminal_result_file_present"]} for label, row in result["runs"].items()}}))


if __name__ == "__main__":
    main()
