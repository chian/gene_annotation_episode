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
    )} | {"selected_assessment_count": len(cell.get("selected_components", []))}


def audit(run, *, verify_snapshot=False):
    launch = json.loads((run / "launch.json").read_text())
    connection = sqlite3.connect((run / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    with connection:
        connection.execute("BEGIN")
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        episodes = []
        for row in connection.execute("SELECT episode_id,path,state FROM runtime_episodes ORDER BY rowid"):
            episodes.append(dict(row) | {"path":json.loads(row["path"])})
        roles = {row["episode_id"]:row["path"][-1][0] for row in episodes}
        actions, failures, publications, unfinished = Counter(), [], [], []
        for row in connection.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions ORDER BY rowid"):
            action = json.loads(row["action"])
            outcome = {} if row["result"] is None else json.loads(row["result"])
            name = action.get("tool", action["kind"])
            actions[name] += 1
            if row["result"] is None:
                unfinished.append(dict(episode_id=row["episode_id"], decision_index=row["decision_index"], operation=name))
            if outcome.get("status") in ("invalid", "failed", "error"):
                failures.append(dict(episode_id=row["episode_id"], decision_index=row["decision_index"],
                    operation=name, status=outcome["status"], feedback=outcome.get("feedback")))
            if name in ("literature.intervention_grading.populate", "literature.a106.finalize") and outcome.get("result"):
                result = outcome["result"]
                publications.append(dict(operation=name, sheet_ref=result.get("sheet_ref"),
                    cells=[{key:cell.get(key) for key in ("component", "value", "status", "reasons", "unavailable_reasons")}
                        for cell in result.get("cells", [])]))
        returned_forms = []
        for row in connection.execute("SELECT episode_id,form FROM runtime_forms WHERE form IS NOT NULL ORDER BY rowid"):
            cells = json.loads(row["form"]).get("literature_a106_subscore_cells", [])
            if cells:
                returned_forms.append(dict(episode_id=row["episode_id"], role=roles.get(row["episode_id"]),
                    results=[result_summary(cell) for cell in cells]))
        receipts = []
        if "literature_a106_subscore_received" in tables:
            for row in connection.execute("SELECT episode_id,operation_key,cells FROM literature_a106_subscore_received ORDER BY rowid"):
                receipts.append(dict(episode_id=row["episode_id"], role=roles.get(row["episode_id"]),
                    operation_key=row["operation_key"], cells=json.loads(row["cells"])))
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
        failed_actions=failures, numerical_publications=publications,
        returned_final_score_forms=returned_forms,
        recorded_final_score_receipts=receipts,
        recorded_annotation_parent_values=[cell.get("value") for cell in target_receipts],
        recorded_annotation_parent_results=[result_summary(cell) for cell in target_receipts],
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
        final_parent_values=result["recorded_annotation_parent_values"], failed_actions=len(result["failed_actions"]))))


if __name__ == "__main__":
    main()
