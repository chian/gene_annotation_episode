"""Read-only trace of the eight retained receipt-regression failures.

This is an evidence extractor, not a test rerun. It imports no application code,
opens only the eight named retained SQLite files in mode=ro, and writes only to
this workload's new evidence directory. No provider conversations are opened.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
BASE = ROOT / "verification/tool_graders_infernal_preparation_2026-10-26_247/shared_receipts_008"
CASES = [
    ("test_runtime_credits_only_requested_child_information_and_replay_keeps_history[False]", "test_runtime_credits_only_requ0"),
    ("test_runtime_credits_only_requested_child_information_and_replay_keeps_history[True]", "test_runtime_credits_only_requ1"),
    ("test_native_workbook_pages_return_one_finding_through_child_form_and_replay", "test_native_workbook_pages_ret0"),
    ("test_selected_state_read_delivers_existing_findings_but_detail_read_does_not[False]", "test_selected_state_read_deliv0"),
    ("test_selected_state_read_delivers_existing_findings_but_detail_read_does_not[True]", "test_selected_state_read_deliv1"),
    ("test_different_parent_scalar_does_not_remove_child_inherited_information", "test_different_parent_scalar_d0"),
    ("test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary[False]", "test_failed_form_repair_and_in0"),
    ("test_failed_form_repair_and_interruption_preserve_work_and_observation_boundary[True]", "test_failed_form_repair_and_in1"),
]
KEY = {"provider": "episode.execution_result", "version": "native_infernal_preparation_bundle_v1"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(value):
    return None if value is None else json.loads(value)


def extract(name, directory, failure):
    path = BASE / "temporary/pytest" / directory / "workspace/state.sqlite3"
    before = digest(path)
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    result = {
        "test": "tests/test_episode_receipts.py::" + name,
        "retained_directory": directory,
        "database": str(path.relative_to(ROOT)),
        "database_sha256_before_read": before,
        "junit_failure": failure,
        "branch_key": KEY,
        "predicate_matches_by_store_table": {},
        "sources": [],
        "calls": [],
        "actions": [],
        "observations": [],
        "report_attempts": [],
        "assessment_receipts": [],
        "received_source_provider_versions": [],
    }
    for table in ("records", "inputs", "material_members"):
        if table in tables:
            result["predicate_matches_by_store_table"][table] = db.execute(
                f"SELECT count(*) FROM {table} WHERE json_extract(data,'$.provider')=? "
                "AND json_extract(data,'$.version')=?", tuple(KEY.values())).fetchone()[0]
    for row in db.execute("SELECT data FROM records WHERE record_type='source' ORDER BY id"):
        source = parse(row[0])
        result["sources"].append({key: source.get(key) for key in
            ("id", "provider", "version", "accession", "artifact_ref", "parent_source_refs")})
    result["runtime_constructed"] = "runtime_model_calls" in tables
    if result["runtime_constructed"]:
        settings = parse(db.execute("SELECT settings FROM runtime_runs").fetchone()[0])
        result["root_action_boundary"] = settings.get("root_action_boundary")
        result["scientific_knowledge"] = settings.get("scientific_knowledge")
        result["episodes"] = [dict(row) for row in db.execute(
            "SELECT episode_id,path,initial_credit,state FROM runtime_episodes ORDER BY rowid")]
        roles = {}
        for episode in result["episodes"]:
            episode["path"] = parse(episode["path"])
            roles[episode["episode_id"]] = "/".join(part[0] for part in episode["path"])
        for row in db.execute("SELECT * FROM runtime_model_calls ORDER BY rowid"):
            request = parse(row["request"])
            response = parse(row["response"])
            context = request["context"]
            selection = None if response is None else response.get("selection")
            branches = request["schema"]["properties"]["selection"]["anyOf"]
            tools = [branch["properties"]["tool"]["const"] for branch in branches
                     if "tool" in branch.get("properties", {})]
            result["calls"].append({
                "episode_id": row["episode_id"], "episode_role_path": roles[row["episode_id"]],
                "call_index": row["call_index"],
                "request_sha256": hashlib.sha256(row["request"].encode()).hexdigest(),
                "response_present": response is not None,
                "selected_kind": None if selection is None else selection.get("kind"),
                "selected_tool": None if selection is None else selection.get("tool"),
                "selected_tool_arguments": (selection.get("arguments") if selection is not None
                                            and selection.get("kind") == "tool" else None),
                "report_update": None if response is None else response.get("report_update"),
                "current_credit": context.get("current_credit"),
                "controller": context.get("controller"), "feedback": context.get("feedback"),
                "working_assessment_refs": [item["id"] for item in
                    context.get("working_state", {}).get("assessments", [])],
                "child_reports": context.get("child_reports"),
                "investigation_progress": context.get("investigation_progress"),
                "allowed_selection_kinds": sorted({branch["properties"]["kind"]["const"]
                                                    for branch in branches}),
                "allowed_tool_names": tools,
                "selected_tool_in_saved_schema": None if selection is None or selection.get("kind") != "tool"
                    else selection.get("tool") in tools,
            })
        for row in db.execute("SELECT * FROM runtime_actions ORDER BY rowid"):
            action, outcome = parse(row["action"]), parse(row["result"])
            result["actions"].append({
                "episode_id": row["episode_id"], "episode_role_path": roles[row["episode_id"]],
                "decision_index": row["decision_index"], "kind": action.get("kind"),
                "tool": action.get("tool"), "credit": row["credit"],
                "outcome": None if outcome is None else {key: outcome.get(key) for key in
                    ("status", "record_refs", "changed_record_refs", "feedback")},
            })
        for row in db.execute("SELECT * FROM runtime_observations ORDER BY rowid"):
            observation = parse(row["observation"])
            result["observations"].append({
                "episode_id": row["episode_id"], "episode_role_path": roles[row["episode_id"]],
                "unit_index": row["unit_index"], "decision_index": observation.get("decision_index"),
                "step": observation.get("step"), "credit": observation.get("credit"),
            })
        for row in db.execute("SELECT * FROM runtime_report_attempts ORDER BY rowid"):
            result["report_attempts"].append({key: parse(row[key]) if key in ("form", "failure") else row[key]
                for key in ("parent_episode_id", "decision_index", "delivery_ref", "child_episode_id", "form", "failure")})
        for row in db.execute("SELECT * FROM runtime_record_receipts WHERE record_ref LIKE 'assessment_%' ORDER BY receipt_index"):
            result["assessment_receipts"].append({**dict(row), "episode_role_path": roles[row["episode_id"]]})
        for row in db.execute(
                "SELECT rr.episode_id, rr.receipt_kind, json_extract(r.data,'$.provider') provider, "
                "json_extract(r.data,'$.version') version, count(*) count FROM runtime_record_receipts rr "
                "JOIN records r ON r.id=rr.record_ref WHERE r.record_type='source' GROUP BY 1,2,3,4"):
            result["received_source_provider_versions"].append({**dict(row), "episode_role_path": roles[row["episode_id"]]})
        result["counts"] = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("runtime_actions", "runtime_observations", "runtime_record_receipts",
                          "runtime_report_attempts", "reasoning_commits", "tool_operations") if table in tables}
    db.close()
    result["database_sha256_after_read"] = digest(path)
    if before != result["database_sha256_after_read"]:
        raise RuntimeError("retained database changed during extraction: " + directory)
    return result


def main():
    receipt = json.loads((BASE / "receipt.json").read_text())
    xml = ET.parse(BASE / "tests.xml")
    failures = {case.attrib["name"]: case.find("failure").text
                for case in xml.iter("testcase") if case.find("failure") is not None}
    assert set(failures) == {name for name, _ in CASES}
    pinned = ["tests/test_episode_receipts.py", "gene_annotation_episode/episode_receipts.py", "gene_annotation_episode/runtime.py"]
    code_hashes = [{"path": name, "current_sha256": digest(ROOT / name),
        "captured_before_sha256": receipt["source_hashes_before"].get(name),
        "captured_after_sha256": receipt["source_hashes_after"].get(name)} for name in pinned]
    for row in code_hashes:
        assert row["current_sha256"] == row["captured_before_sha256"] == row["captured_after_sha256"]
    evidence = {
        "version": "receipt_regression_retained_trace_v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Only the eight retained tests/test_episode_receipts.py failures; no test rerun or application execution.",
        "authoritative_goal": "/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt",
        "authoritative_goal_sha256": digest(Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")),
        "retained_run": str(BASE.relative_to(ROOT)),
        "retained_run_policy": receipt["policy"],
        "retained_result": {"passed": 49, "failed": 8, "returncode": receipt["returncode"]},
        "retained_artifacts_sha256": {name: digest(BASE / name) for name in ("receipt.json", "stdout.log", "tests.xml")},
        "frozen_code_hash_comparison": code_hashes,
        "current_additional_code_sha256": {name: digest(ROOT / name) for name in (
            "gene_annotation_episode/composition_information.py", "gene_annotation_episode/credit.py",
            "gene_annotation_episode/scientific_credit.py", "gene_annotation_episode/investigation_progress.py",
            "gene_annotation_episode/state.py", "tests/test_runtime.py")},
        "cases": [extract(name, directory, failures[name]) for name, directory in CASES],
    }
    destination = OUTPUT / "retained_evidence_001.json"
    with destination.open("x") as handle:
        json.dump(evidence, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"evidence": str(destination.relative_to(ROOT)), "cases": len(evidence["cases"]),
        "branch_predicate_matches": sum(sum(case["predicate_matches_by_store_table"].values()) for case in evidence["cases"]),
        "retained_databases_unchanged": True, "test_reruns": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
