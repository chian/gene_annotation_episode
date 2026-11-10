"""Read-only trace inventory for an autonomous A106 run, not a science grader.

The receipt inventory establishes what the runtime recorded as delivered. Source
adequacy, independence and biological conclusions still require trace review.
Database activity alone does not establish that a process is currently alive.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3


def result_summary(cell):
    """Expose delivery and assessment links without judging their adequacy."""
    return {key: cell.get(key) for key in (
        "sheet_ref", "subject_ref", "assertion_ref", "comparison_ref", "scope_statement",
        "value", "available_value", "status", "unavailable_reasons", "experiments",
        "revises_subscore_ref", "revision_reason",
    )} | {"selected_assessment_count": len(cell.get("selected_components", []))}


def latest_received_score_cells(cells):
    """Inventory delivered revisions once; this does not combine their scores.

    The full receipt history stays in the audit. A predecessor is superseded
    only by an explicitly linked revision that the parent actually received.
    """
    unique = {cell["sheet_ref"]: cell for cell in cells}
    superseded = {cell.get("revises_subscore_ref") for cell in unique.values()}
    return [cell for ref, cell in unique.items() if ref not in superseded]


def returned_score_cells(form, request):
    """Follow the saved typed contract; the parent chooses each field's name."""
    contract = request.get("report_contract") or {}
    properties = contract.get("measurements", {}).get("schema", {}).get("properties", {})
    return [cell for name, schema in properties.items()
        if schema.get("x-source") == "literature_a106_subscore_cells"
        for cell in form.get(name, [])]


def assessment_receipt_inventory(connection, tables, roles):
    """Inventory direct receipts, not saved-only or inherited availability.

    The receipt table keeps the first delivery of each reference to each
    episode, including forward dependencies. Its kind is not a history of
    subsequent report deliveries. Database-current status does not establish
    that the receiver has seen a newer revision or interpreted this one.
    """
    if not {"runtime_record_receipts", "records"} <= tables:
        return []
    current = None
    if "current_revisions" in tables:
        current = {row[0] for row in connection.execute(
            "SELECT record_ref FROM current_revisions WHERE record_type='assessment'")}
    receipts = []
    for row in connection.execute(
            "SELECT r.run_id,r.episode_id,r.record_ref,r.receipt_kind,r.source_index,d.data "
            "FROM runtime_record_receipts r JOIN records d ON d.id=r.record_ref "
            "WHERE d.record_type='assessment' ORDER BY r.receipt_index"):
        record = json.loads(row["data"])
        finding = record.get("investigation_finding") or {}
        receipts.append(dict(run_id=row["run_id"], episode_id=row["episode_id"],
            role=roles.get(row["episode_id"]), record_ref=row["record_ref"],
            first_receipt_kind=row["receipt_kind"], first_source_index=row["source_index"],
            revision=record.get("revision"), observation_ref=record.get("observation_ref"),
            hypothesis_ref=record.get("hypothesis_ref"), relation=record.get("relation"),
            applicability=record.get("applicability"),
            finding_status=finding.get("status"),
            same_source_claim_as_ref=finding.get("same_source_claim_as_ref"),
            replaces_refs=finding.get("replaces_refs", []),
            is_database_current_revision=None if current is None else row["record_ref"] in current))
    return receipts


def audit(run, *, verify_snapshot=False):
    launch = json.loads((run / "launch.json").read_text())
    connection = sqlite3.connect((run / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute("BEGIN")
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        episodes, requests = [], {}
        for row in connection.execute("SELECT episode_id,path,state,request FROM runtime_episodes ORDER BY rowid"):
            episodes.append({key: row[key] for key in ("episode_id", "state")} | {"path":json.loads(row["path"])})
            requests[row["episode_id"]] = json.loads(row["request"])
        roles = {row["episode_id"]:row["path"][-1][0] for row in episodes}
        assessment_receipts = assessment_receipt_inventory(connection, tables, roles)
        rejected_decisions = []
        if "runtime_decision_effects" in tables:
            for row in connection.execute(
                    "SELECT episode_id,decision_index,json_extract(effect,'$.feedback') AS feedback "
                    "FROM runtime_decision_effects WHERE json_extract(effect,'$.state')='rejected' ORDER BY rowid"):
                rejected_decisions.append(dict(episode_id=row["episode_id"],
                    decision_index=row["decision_index"],
                    feedback=None if row["feedback"] is None else json.loads(row["feedback"])))
        actions, failures, publications, unfinished = Counter(), [], [], []
        for row in connection.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions ORDER BY rowid"):
            action = json.loads(row["action"])
            outcome = {} if row["result"] is None else json.loads(row["result"])
            name = action.get("tool", action["kind"])
            actions[name] += 1
            if row["result"] is None:
                unfinished.append(dict(episode_id=row["episode_id"], decision_index=row["decision_index"], operation=name))
            failure_code = outcome.get("failure_code")
            if isinstance(outcome.get("result"), dict):
                failure_code = failure_code or outcome["result"].get("failure_code")
            partial_failure = outcome.get("status") == "partial" and (
                outcome.get("error_code") or outcome.get("errors") or outcome.get("conflicts") or failure_code)
            if outcome.get("status") in ("invalid", "failed", "error") or partial_failure:
                failures.append(dict(episode_id=row["episode_id"], decision_index=row["decision_index"],
                    operation=name, status=outcome["status"], feedback=outcome.get("feedback"),
                    error_code=outcome.get("error_code"), failure_code=failure_code,
                    errors=outcome.get("errors"),
                    conflicts=outcome.get("conflicts"),
                    changed_record_refs=outcome.get("changed_record_refs", [])))
            if name in ("literature.intervention_grading.populate", "literature.a106.finalize") and outcome.get("result"):
                result = outcome["result"]
                publications.append(dict(operation=name, sheet_ref=result.get("sheet_ref"),
                    cells=[{key:cell.get(key) for key in ("component", "value", "status", "reasons", "unavailable_reasons")}
                        for cell in result.get("cells", [])]))
        returned_forms = []
        for row in connection.execute("SELECT episode_id,form FROM runtime_forms WHERE form IS NOT NULL ORDER BY rowid"):
            cells = returned_score_cells(json.loads(row["form"]), requests[row["episode_id"]])
            if cells:
                returned_forms.append(dict(episode_id=row["episode_id"], role=roles.get(row["episode_id"]),
                    results=[result_summary(cell) for cell in cells]))
        receipts = []
        if "literature_a106_subscore_received" in tables:
            for row in connection.execute("SELECT episode_id,operation_key,cells FROM literature_a106_subscore_received ORDER BY rowid"):
                receipts.append(dict(episode_id=row["episode_id"], role=roles.get(row["episode_id"]),
                    operation_key=row["operation_key"], cells=json.loads(row["cells"])))
        deliveries = [dict(parent_episode_id=row["parent_episode_id"],
            child_episode_id=row["child_episode_id"], decision_index=row["decision_index"],
            delivery_ref=row["delivery_ref"], form_present=bool(row["form_present"]),
            failure=None if row["failure"] is None else json.loads(row["failure"]))
            for row in connection.execute("SELECT parent_episode_id,child_episode_id,decision_index,"
                "delivery_ref,form IS NOT NULL AS form_present,failure "
                "FROM runtime_report_attempts ORDER BY rowid")]
        counts = {name:connection.execute("SELECT count(*) FROM " + name).fetchone()[0]
            for name in ("runtime_model_calls", "runtime_decision_exchanges", "runtime_forms")}
    connection.close()
    pins = json.loads((run / "source-pins.json").read_text())
    mismatches = None
    if verify_snapshot:
        mismatches = [name for name, digest in pins.items() if not (run / "source" / name).is_file()
            or hashlib.sha256((run / "source" / name).read_bytes()).hexdigest() != digest]
    target_receipts = [cell for row in receipts if row["role"] == "annotation" for cell in row["cells"]]
    return dict(run=str(run), workflow_result_present=(run / "result.json").exists(),
        failure_file_present=(run / "failure.json").exists(), database_episodes=episodes,
        process_liveness="not_inferred_from_database; poll the original execution handle",
        input_policy={key:launch.get(key) for key in ("input_mode", "external_cutoff", "preloaded_evidence",
            "scripted_model_decisions", "evaluator_expectations_loaded", "bvbrc_execution")},
        input_hash_matches=hashlib.sha256((run / "input.txt").read_text().strip().encode()).hexdigest()
            == launch["sequence_sha256"], source_snapshot_files=len(pins), source_snapshot_mismatches=mismatches,
        counts=counts, action_counts=dict(actions), actions_without_saved_result=unfinished,
        rejected_decisions=rejected_decisions,
        failed_actions=failures, numerical_publications=publications,
        returned_final_score_forms=returned_forms,
        report_delivery_attempts=deliveries,
        recorded_final_score_receipts=receipts,
        recorded_assessment_receipts=assessment_receipts,
        recorded_annotation_parent_values=[cell.get("value") for cell in target_receipts],
        recorded_annotation_parent_results=[result_summary(cell) for cell in target_receipts],
        recorded_annotation_parent_latest_received_results=[result_summary(cell)
            for cell in latest_received_score_cells(target_receipts)],
        scientific_adequacy="Not established by this inventory; inspect the source operands, assumptions and complete trace.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--verify-snapshot", action="store_true")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    root = Path(__file__).resolve().parents[1] / "runs"
    if not run.is_relative_to(root) or run == root:
        parser.error("run_dir must be a separate directory below this repository's runs/")
    result = audit(run, verify_snapshot=args.verify_snapshot)
    output = run / "evaluation-audit.json"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(audit=str(output), input_hash_matches=result["input_hash_matches"],
        source_snapshot_mismatches=result["source_snapshot_mismatches"], counts=result["counts"],
        returned_final_score_forms=len(result["returned_final_score_forms"]),
        rejected_decisions=len(result["rejected_decisions"]),
        final_parent_values=result["recorded_annotation_parent_values"], failed_actions=len(result["failed_actions"]))))


if __name__ == "__main__":
    main()
