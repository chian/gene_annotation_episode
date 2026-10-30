"""Read-only observations of the original broad run; never attach or signal."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ORIGINAL = ROOT / "verification/tool_graders_blast_geometry_2026-10-26_295/checks_003"


def read(path):
    try:
        return Path(path).read_text()
    except OSError as error:
        return {"unknown": type(error).__name__, "reason": str(error)}


def process(pid):
    base = Path("/proc") / str(pid)
    return {"pid": pid, "source": str(base), "cmdline": read(base / "cmdline"),
            "stat": read(base / "stat"), "status": read(base / "status"),
            "io": read(base / "io"), "wchan": read(base / "wchan"),
            "kernel_stack": read(base / "stack")}


def main():
    result = {"observed_at": datetime.now(timezone.utc).isoformat(),
              "original_run": str(ORIGINAL), "processes": [process(p) for p in (1674733, 1674741)],
              "source_access": "read_only_proc_and_sqlite_mode_ro_query_only"}
    db_path = ORIGINAL / "temporary/pytest/homology-shared-workflow0/state/state.sqlite3"
    connection = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    connection.row_factory = sqlite3.Row
    tables = ("runtime_actions", "runtime_model_calls", "runtime_observations", "runtime_episodes", "runtime_forms")
    result["database"] = {"source": str(db_path), "counts": {
        table: connection.execute("SELECT count(*) FROM " + table).fetchone()[0] for table in tables}}
    actions = []
    for row in connection.execute("SELECT episode_id,decision_index,action,result,credit FROM runtime_actions ORDER BY rowid"):
        item = dict(row)
        item["action"] = json.loads(item["action"])
        outcome = json.loads(item.pop("result")) if row["result"] is not None else None
        item["result_status"] = outcome.get("status") if outcome else None
        item["record_refs_count"] = len(outcome.get("record_refs", [])) if outcome else None
        item["result_keys"] = list((outcome.get("result") or {}).keys()) if outcome else None
        actions.append(item)
    result["database"]["actions"] = actions
    result["database"]["episodes"] = [dict(row) for row in connection.execute(
        "SELECT episode_id,path,state FROM runtime_episodes")]
    result["database"]["forms"] = [
        {"episode_id": row["episode_id"], "facts_bytes": len(row["facts"]),
         "form_bytes": len(row["form"]) if row["form"] is not None else None}
        for row in connection.execute("SELECT episode_id,facts,form FROM runtime_forms")]
    connection.close()
    opened = Counter()
    start = time.monotonic()
    for _ in range(100):
        directory = Path("/proc/1674741/fd")
        try:
            for entry in directory.iterdir():
                try:
                    opened[os.readlink(entry)] += 1
                except OSError:
                    pass
        except OSError:
            break
        time.sleep(.02)
    result["fd_sampling"] = {"source": "/proc/1674741/fd", "duration_seconds": time.monotonic() - start,
                             "sample_count": 100, "observed_paths": dict(opened)}
    result["processes_after_sampling"] = [process(p) for p in (1674733,1674741)]
    result["stdout"] = {"source": str(ORIGINAL / "stdout.txt"), "text": read(ORIGINAL / "stdout.txt")}
    result["python_stack"] = {"status": "unknown", "reason": "No attach or signal permitted; proc kernel stack availability is recorded separately."}
    destination = HERE / (sys.argv[1] + ".json")
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"path": str(destination), "counts": result["database"]["counts"],
                      "fd_paths": len(opened), "observed_at": result["observed_at"]}, sort_keys=True))


if __name__ == "__main__":
    main()
