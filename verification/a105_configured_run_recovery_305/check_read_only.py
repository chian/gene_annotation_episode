"""Read-only preflight for the interrupted configured A105 caller 278.

This program never imports the application, opens the database for writes, or
reads provider request/response bodies. It does not resume inference.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


HERE = Path(__file__).resolve().parent
CASE = HERE.parent / "a105_configured_worksheet_278"
CONFIGURED = CASE / "configured_001"
DB = CONFIGURED / "state" / "state.sqlite3"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def checked_manifest(name: str, base: Path) -> int:
    manifest = json.loads((CASE / name).read_text())
    seen = set()
    for row in manifest["files"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts or row["path"] in seen:
            raise ValueError(f"invalid_{name}_path")
        seen.add(row["path"])
        path = base / relative
        if not path.is_file() or path.stat().st_size != row["bytes"] or digest(path) != row["sha256"]:
            raise ValueError(f"{name}_file_mismatch:{relative}")
    return len(seen)


def process_is_same(identity: dict) -> bool:
    pid = identity["pid"]
    proc = Path(f"/proc/{pid}/stat")
    if not proc.exists():
        return False
    try:
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        stat = proc.read_text()
        start_ticks = stat[stat.rfind(")") + 2 :].split()[19]
    except (FileNotFoundError, PermissionError, IndexError):
        # An uninspectable process cannot be treated as dead.
        return True
    return boot_id == identity["boot_id"] and start_ticks == str(identity["start_ticks"])


def one(db: sqlite3.Connection, statement: str, args: tuple = ()) -> sqlite3.Row:
    rows = db.execute(statement, args).fetchall()
    if len(rows) != 1:
        raise ValueError(f"expected_one_row:{statement.split()[1]}:{len(rows)}")
    return rows[0]


def check() -> dict:
    source_count = checked_manifest("SOURCE_PIN_001.json", CASE / "source_pin_001")
    entrypoint_count = checked_manifest("ENTRYPOINT_PIN_002.json", CASE)
    prepared = json.loads((CONFIGURED / "prepared_caller.json").read_text())
    run_file = json.loads((CONFIGURED / "run" / "run.json").read_text())
    status = json.loads((CASE / "STATUS_002.json").read_text())
    if status["run_id"] != prepared["run_id"] or process_is_same(status["process_identity"]):
        raise ValueError("original_process_identity_still_live_or_run_changed")
    if run_file != {"run_id": prepared["run_id"], **prepared["settings"]}:
        raise ValueError("run_file_differs_from_prepared_settings")
    if prepared["settings"]["decision_protocol"] != "decision_exchange_v1":
        raise ValueError("unexpected_decision_protocol")
    if prepared["settings"]["annotation_child_roles"] != ["literature"]:
        raise ValueError("unexpected_child_roles")
    if prepared["settings"]["directory"] != str(CONFIGURED / "run"):
        raise ValueError("run_directory_differs_from_original")

    uri = f"file:{DB}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        run = one(db, "SELECT * FROM runtime_runs WHERE run_id=?", (prepared["run_id"],))
        if run["state"] != "running" or json.loads(run["settings"]) != prepared["settings"]:
            raise ValueError("saved_run_state_or_settings_mismatch")
        episodes = db.execute("SELECT episode_id,path,request,state,completion FROM runtime_episodes WHERE run_id=?", (prepared["run_id"],)).fetchall()
        roots = [row for row in episodes if json.loads(row["path"]) == [["annotation", "root"]]]
        if len(roots) != 1:
            raise ValueError("root_episode_identity_mismatch")
        root = roots[0]
        request = json.loads(root["request"])
        message = request["message"]
        if (request["goal"]["objective"] != prepared["scientific_question"] or
            message["episode_assignment"] != prepared["assignment"] or
            message["report_contract_declaration"] != prepared["contract_declaration"] or
            message["initial_report"] != prepared["initial_report"] or
            request["report_contract"]["decision"] != prepared["return_purpose"] or
            request["report_contract"]["measurements"]["schema"] != prepared["expanded_form"]):
            raise ValueError("root_original_request_differs_from_prepared_contract")
        if root["state"] != "active" or root["completion"] is not None:
            raise ValueError("root_already_closed")

        pending_calls = db.execute("SELECT episode_id,call_index,purpose FROM runtime_model_calls "
            "WHERE run_id=? AND response IS NULL", (prepared["run_id"],)).fetchall()
        if len(pending_calls) != 1:
            raise ValueError(f"pending_logical_call_count:{len(pending_calls)}")
        pending = pending_calls[0]
        child = one(db, "SELECT path,state,completion FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                    (prepared["run_id"], pending["episode_id"]))
        if (json.loads(child["path"]) != [["annotation", "root"], ["literature", "child_10"]] or
            child["state"] != "active" or child["completion"] is not None or
            pending["call_index"] != 18 or pending["purpose"] != "decision"):
            raise ValueError("pending_child_call_identity_changed")
        pending_exchanges = db.execute("SELECT exchange_index,response,lookup_result FROM runtime_decision_exchanges "
            "WHERE run_id=? AND episode_id=? AND decision_index=? ORDER BY exchange_index",
            (prepared["run_id"], pending["episode_id"], pending["call_index"])).fetchall()
        if (len(pending_exchanges) != 1 or pending_exchanges[0]["exchange_index"] != 0 or
            pending_exchanges[0]["response"] is not None or pending_exchanges[0]["lookup_result"] is not None):
            raise ValueError("pending_physical_exchange_changed")
        root_pending = db.execute("SELECT decision_index,action,result,credit FROM runtime_actions "
            "WHERE run_id=? AND episode_id=? AND result IS NULL",
            (prepared["run_id"], root["episode_id"])).fetchall()
        if (len(root_pending) != 1 or root_pending[0]["decision_index"] != 10 or
            json.loads(root_pending[0]["action"]).get("kind") != "episode_child" or
            root_pending[0]["credit"] is not None):
            raise ValueError("root_pending_child_action_changed")
        attempts = db.execute("SELECT parent_episode_id,decision_index,child_episode_id,form,failure "
            "FROM runtime_report_attempts WHERE run_id=?", (prepared["run_id"],)).fetchall()
        admitted = [row for row in attempts if row["form"] is not None and row["failure"] is None]
        if len(attempts) != 9 or len(admitted) != 9 or any(
                row["parent_episode_id"] != root["episode_id"] or row["decision_index"] == 10
                for row in attempts):
            raise ValueError("child_return_attempts_changed")
        actions = one(db, "SELECT count(*) AS n FROM runtime_actions WHERE run_id=?", (prepared["run_id"],))["n"]
        observations = one(db, "SELECT count(*) AS n FROM runtime_observations WHERE run_id=?", (prepared["run_id"],))["n"]
        calls = one(db, "SELECT count(*) AS n FROM runtime_model_calls WHERE run_id=?", (prepared["run_id"],))["n"]
        root_obs = one(db, "SELECT count(*) AS n FROM runtime_observations WHERE run_id=? AND episode_id=?",
                       (prepared["run_id"], root["episode_id"]))["n"]
        if root_obs != 9:
            raise ValueError("root_observation_count_changed")
        states = Counter(row["state"] for row in episodes)
        changes = db.total_changes
        if changes != 0:
            raise ValueError("read_only_database_connection_changed")
    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "consistent_interrupted_run_candidate_for_replay_review",
        "source_pin_files_verified": source_count,
        "entrypoint_contract_files_verified": entrypoint_count,
        "run_id": prepared["run_id"],
        "root_episode_id": root["episode_id"],
        "pending_child_episode_id": pending["episode_id"],
        "pending_decision_index": pending["call_index"],
        "pending_exchange_index": 0,
        "pending_root_child_decision_index": 10,
        "episode_states": dict(states),
        "actions": actions,
        "observations": observations,
        "model_calls": calls,
        "admitted_child_returns": len(admitted),
        "database_total_changes": changes,
        "live_model_resume_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2, sort_keys=True))
