"""Read-only extraction of already completed074 decision evidence.

Run only in529/check081_masking_decision_snapshot. This is an evidence extractor,
not a new scientific/native/model execution or production prompt implementation.
"""
from pathlib import Path
import hashlib
import json
import os
import sqlite3


def _pin(path):
    path = Path(path).resolve(strict=True)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size}


def _decode(row):
    value = dict(row)
    for name, item in list(value.items()):
        if isinstance(item, str) and item[:1] in {"{", "["}:
            try:
                value[name] = json.loads(item)
            except json.JSONDecodeError:
                pass
    return value


def test_extract_original_results_and_scientific_decisions():
    original_db = Path(os.environ["HMMER_NATIVE_ORACLE_ORIGINAL_DB"])
    frozen_db = Path(os.environ["HMMER_NATIVE_ORACLE_FROZEN_DB"])
    original_case = Path(os.environ["HMMER_NATIVE_ORACLE_ORIGINAL_CASE"])
    frozen_case = Path(os.environ["HMMER_NATIVE_ORACLE_FROZEN_CASE"])
    output = Path(os.environ["HMMER_NATIVE_ORACLE_SNAPSHOT_OUTPUT"])
    before = [_pin(path) for path in (original_db, frozen_db, original_case, frozen_case)]
    assert before[0]["sha256"] == before[1]["sha256"]
    assert before[2]["sha256"] == before[3]["sha256"]
    assert not original_db.with_name(original_db.name + "-wal").exists()
    assert not frozen_db.with_name(frozen_db.name + "-wal").exists()
    connection = sqlite3.connect(frozen_db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        episodes = [_decode(row) for row in connection.execute(
            "SELECT * FROM runtime_episodes WHERE run_id=?", ("masking-workflow619",))
            if json.loads(row["path"])[-1][0] in {"results", "scientific_process"}]
        assert len(episodes) == 2
        evidence = []
        for episode in episodes:
            role = episode["path"][-1][0]
            identity = episode["episode_id"]
            item = {"role": role, "episode": episode}
            for table, order in (("runtime_model_calls", "call_index"),
                    ("runtime_actions", "decision_index"),
                    ("runtime_forms", "episode_id"),
                    ("runtime_observations", "unit_index")):
                columns = [row[1] for row in connection.execute("PRAGMA table_info(" + table + ")")]
                order_column = order if order in columns else "rowid"
                item[table] = [_decode(row) for row in connection.execute(
                    "SELECT * FROM " + table + " WHERE run_id=? AND episode_id=? ORDER BY " + order_column,
                    ("masking-workflow619", identity))]
            assert len(item["runtime_model_calls"]) == (1 if role == "results" else 2)
            evidence.append(item)
        results = next(row for row in evidence if row["role"] == "results")
        context = results["runtime_model_calls"][0]["request"]["context"]
        assert context["execution_assignment"]["selector"]["version"] == "native_blast_masking_result_selector_v1"
        assert context["execution_target"]["assignment"]["requested_job"]["native_blast_masking"]["operation"]["program"] == "dustmasker"
        assert results["runtime_actions"][0]["action"]["tool"] == "execution.results.collect"
    finally:
        connection.close()
    after = [_pin(path) for path in (original_db, frozen_db, original_case, frozen_case)]
    assert before == after
    original = json.loads(frozen_case.read_text())
    packet = {"kind": "original074_read_only_decision_evidence_621", "source_pins_before": before,
        "source_pins_after": after, "sqlite_mode": "read-only immutable frozen copy",
        "source_bytes_unchanged": True, "native_work_run": False, "model_work_run": False,
        "episodes": evidence, "case_selected_result": {
            key: original[key] for key in ("program", "mode", "scope", "returned", "forwarded", "histories")}}
    output.parent.mkdir(parents=True, exist_ok=True)
    assert not output.exists()
    output.write_text(json.dumps(packet, indent=2, allow_nan=False) + "\n")
