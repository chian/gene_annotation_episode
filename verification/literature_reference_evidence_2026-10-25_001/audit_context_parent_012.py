"""Independent SQL/artifact audit of the retained controlled A108 examples.

Uses sqlite mode=ro and query_only. Imports no production repository, parser,
calculator, source provider or model. Hashing original bytes is a custody check,
not scientific interpretation. The separate fresh replay forbids those reads.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent.parent
EXAMPLES = BASE / "context_examples_001"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_bytes())


def audit_case(name, replay):
    directory = EXAMPLES / name
    saved = read_json(directory / "RECEIPT.json")
    assert saved["case"] == name and saved["model_backed"] is False
    changed = {path: {"recorded": sha, "current": digest(ROOT / path)}
               for path, sha in saved["code_sha256"].items() if digest(ROOT / path) != sha}
    # Preserve exact historical manifests. Concurrent non-literature edits do
    # not establish exact whole-tree identity and must be reported explicitly.
    allowed_external_changes = {
        "gene_annotation_episode/infernal_preparation_artifacts.py",
        "gene_annotation_episode/infernal_preparation_calculations.py",
        "gene_annotation_episode/infernal_preparation_statistics.py"}
    assert set(changed).issubset(allowed_external_changes), changed
    db = sqlite3.connect((directory / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("BEGIN")

    def artifact(reference):
        row = db.execute("SELECT sha256 FROM artifacts WHERE id=?", (reference,)).fetchone()
        assert row is not None
        path = directory / "state/artifacts" / row[0][:2] / row[0]
        assert digest(path) == row[0]
        return path.read_bytes()

    def record(reference):
        return json.loads(db.execute("SELECT data FROM records WHERE id=?", (reference,)).fetchone()[0])

    try:
        operation, = db.execute("SELECT * FROM literature_context_operations").fetchall()
        outcome = json.loads(operation["outcome"])
        assert operation["run_id"] == saved["run_id"]
        assert outcome == saved["outcome"] and outcome["status"] == "completed"
        source = record(outcome["result"]["sheet_ref"])
        assert source["version"] == "literature_context_record_v1"
        assert source["provider"] == "literature.experimental.context"
        payload = json.loads(artifact(source["artifact_ref"]))
        assert payload == saved["saved_payload"]
        assert payload["prepared_inputs"] == saved["prepared_inputs"] == payload["sheet"]["inputs"]
        extracted = payload["extraction"]["calculation_inputs"]
        assert extracted is None or extracted == payload["prepared_inputs"]
        admission, = db.execute("SELECT * FROM literature_context_received").fetchall()
        attempt, = db.execute("SELECT * FROM runtime_report_attempts").fetchall()
        cells = json.loads(admission["cells"])
        assert attempt["failure"] is None
        assert attempt["child_episode_id"] == operation["episode_id"]
        assert admission["episode_id"] == attempt["parent_episode_id"]
        form = json.loads(attempt["form"])
        assert form == saved["actual_frozen_child_form"]
        assert cells == form["measurements"] == saved["actual_admitted_parent_subset"]
        assert len(cells) == 7
        inputs = payload["prepared_inputs"]
        definitions = [{key: value for key, value in requirement.items() if key != "key"}
                       for requirement in inputs["requirements"]]
        indices = {requirement["key"]: index for index, requirement in enumerate(inputs["requirements"])}
        routes = None if inputs["routes"] is None else [{
            "requirements": [indices[key] for key in route["requirements"]],
            "requirements_complete": route["requirements_complete"],
            "joint_support": route["joint_support"]} for route in inputs["routes"]]
        for cell in cells:
            original = payload["sheet"]["cells"][cell["component"]]
            assert all(cell[key] == original[key] for key in
                       ("value", "unit", "status", "origin", "unavailable_reason", "conditional_on"))
            assert cell["requirement_definitions"] == definitions
            assert cell["route_definitions"] == routes
            assert cell["target_correspondence"] == "not_evaluated"
            assert cell["measurement_corrections"] == "not_applied"
        actions = [{"episode_id": row["episode_id"], "decision_index": row["decision_index"],
                    "selection": json.loads(row["action"]), "credit": row["credit"]}
                   for row in db.execute("SELECT * FROM runtime_actions ORDER BY rowid")]
        observations = [{"episode_id": row["episode_id"], "unit_index": row["unit_index"],
                         "observation": json.loads(row["observation"])}
                        for row in db.execute("SELECT * FROM runtime_observations ORDER BY rowid")]
        assert actions == saved["actual_completed_actions"]
        assert observations == saved["actual_local_observations"]
        assert len(actions) == len(observations) == 3
        assert all(row["credit"] == 0 for row in actions)
        assert len({(row["episode_id"], row["unit_index"]) for row in observations}) == 3
        assert not db.execute("SELECT 1 FROM records WHERE record_type IN ('observation','assessment')").fetchall()
        for ref, hashes in saved["direct_source_sha256"].items():
            original = record(ref)
            assert all(hashlib.sha256(artifact(original[field])).hexdigest() == sha
                       for field, sha in hashes.items())
        assert replay["actual_parent_subset_equals_saved_cells"]
        assert replay["replay_SQL_query_only"] and not replay["original_input_bytes_read"]
        assert len(replay["parsers_calculators_and_identity_helpers_disabled"]) == 57
        assert replay["code_sha256"] == saved["code_sha256"]
        return {"case": name, "status": "passed", "run_id": saved["run_id"],
                "cells": {cell["component"]: cell["value"] for cell in cells},
                "record_version": source["version"],
                "historical_code_files_hashed": len(saved["code_sha256"]),
                "code_files_unchanged": len(saved["code_sha256"]) - len(changed),
                "current_whole_tree_matches_historical_run": not changed,
                "changed_external_tool_files": changed,
                "prepared_inputs_and_numerical_domain_definitions_exact": True,
                "actual_actions": len(actions), "actual_observations": len(observations),
                "actual_admitted_cells": len(cells), "controller_credit": 0,
                "source_artifact_hashes_verified": True, "SQL_query_only": True}
    finally:
        db.rollback()
        db.close()


if __name__ == "__main__":
    reopen = read_json(EXAMPLES / "REOPEN_RECEIPT.json")
    result = {"status": "passed", "written_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "Independent SQL/artifact inspection of controlled examples; no new science or live recovery",
              "model_backed": False,
              "cases": [audit_case(row["case"], row) for row in reopen["cases"]],
              "audit_script_sha256": digest(Path(__file__)),
              "reopen_receipt_sha256": digest(EXAMPLES / "REOPEN_RECEIPT.json")}
    destination = BASE / "PARENT_CHECK_012.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "cases": len(result["cases"]),
                      "unchanged_code_files_each": result["cases"][0]["code_files_unchanged"]}))
