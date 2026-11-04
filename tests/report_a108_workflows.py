"""Read-only evidence inventory for full A108 runs; this does not grade a case.

Scientific correctness and parent consumption require review of the retained
evidence. Process status is checked against the actual PID/start identity.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


def process_status(run):
    receipt = run / "execution.json"
    if not receipt.exists():
        return {"state": "launch_receipt_missing"}
    execution = json.loads(receipt.read_text())
    stat = Path("/proc") / str(execution["pid"]) / "stat"
    try:
        fields = stat.read_text().rsplit(")", 1)[1].split()
    except FileNotFoundError:
        return {"state": "process_missing", "pid": execution["pid"]}
    if fields[19] != execution["process_start_ticks"]:
        return {"state": "pid_reused", "pid": execution["pid"]}
    return {"state": "terminal_process" if fields[0] in ("Z", "X") else "live",
        "native_state": fields[0], "pid": execution["pid"]}


def capture_prompts(run):
    rows = []
    for path in sorted(run.glob("workflow/providers/*/session-*/call-00001/request.json")):
        request = json.loads(path.read_text())
        instructions_field = "instructions" if isinstance(request.get("instructions"), str) else "model_instructions"
        prompt = "\n\n".join([request.get(instructions_field, "")] +
            [item["text"] for item in request.get("input", []) if item.get("type") == "text"])
        provider, session = path.parents[2].name, path.parents[1].name
        destination = run / "prompt-receipts" / (
            request["episode_id"] + "-" + provider + "-" + session + ".txt")
        destination.parent.mkdir(exist_ok=True)
        destination.write_text(prompt)
        rows.append({"episode_id": request["episode_id"], "request_path": str(path),
            "request_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "provider": provider, "session": session, "instructions_field": instructions_field,
            "input_types": [item.get("type") for item in request.get("input", [])],
            "output_schema_request_field": "output_schema",
            "prompt_path": str(destination), "sha256": hashlib.sha256(prompt.encode()).hexdigest()})
    return rows


def capture_evidence(run, db, tables, report):
    """Export actual retained evidence for review, without recomputing scores."""
    destination = run / "evidence"
    destination.mkdir(exist_ok=True)
    paths = {}
    if "runtime_actions" in tables:
        trace = destination / "actions.jsonl"
        with trace.open("w") as output:
            for episode, index, action, outcome in db.execute(
                    "SELECT episode_id,decision_index,action,result FROM runtime_actions ORDER BY rowid"):
                output.write(json.dumps({"episode_id": episode, "decision_index": index,
                    "action": json.loads(action), "outcome": json.loads(outcome) if outcome else None}) + "\n")
        paths["actions"] = str(trace)
    sources, scientific = [], []
    if "records" in tables:
        for kind, raw in db.execute("SELECT record_type,data FROM records ORDER BY rowid"):
            record = json.loads(raw)
            if kind != "source":
                scientific.append(record)
                continue
            entry = {"record": record, "representations": {}}
            for field in ("artifact_ref", "text_ref"):
                reference = record.get(field)
                if reference is None:
                    continue
                artifact = db.execute("SELECT sha256 FROM artifacts WHERE id=?", (reference,)).fetchone()
                if artifact is None:
                    entry["representations"][field] = {"reference": reference, "missing": True}
                    continue
                original = run / "state/artifacts" / artifact[0][:2] / artifact[0]
                entry["representations"][field] = {"reference": reference,
                    "path": str(original), "sha256": artifact[0]}
            if record.get("provider") in ("literature.experimental.context", "literature.a108.subscore"):
                original = Path(entry["representations"]["artifact_ref"]["path"])
                sheet = destination / (record["id"] + ".json")
                sheet.write_bytes(original.read_bytes())
                entry["saved_sheet_copy"] = str(sheet)
            sources.append(entry)
    for name, value in (("sources", sources), ("scientific-records", scientific),
                        ("parent-returns", report.get("returns", []))):
        path = destination / (name + ".json")
        path.write_text(json.dumps(value, indent=2) + "\n")
        paths[name] = str(path)
    return paths


def inspect_run(run):
    result = {"run_dir": str(run), "observed_at": datetime.now(timezone.utc).isoformat(),
        "process": process_status(run), "workflow_result": None, "workflow_failure": None}
    for file, key in (("result.json", "workflow_result"), ("failure.json", "workflow_failure"),
                      ("launch.json", "launch")):
        if (run / file).exists():
            result[key] = json.loads((run / file).read_text())
    path = run / "state/state.sqlite3"
    if not path.exists():
        return result
    db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result.update(episodes=[], actions={}, failures=[], assessments=[], subscores=[], returns=[])
        if "runtime_episodes" in tables:
            for episode, path, state, completion in db.execute("SELECT episode_id,path,state,completion FROM runtime_episodes"):
                result["episodes"].append({"episode_id": episode, "path": json.loads(path), "state": state,
                    "completion": json.loads(completion) if completion else None})
        counts = Counter()
        if "runtime_actions" in tables:
            for episode, index, action, outcome in db.execute(
                    "SELECT episode_id,decision_index,action,result FROM runtime_actions ORDER BY rowid"):
                action = json.loads(action)
                outcome = json.loads(outcome) if outcome else {}
                name = action.get("tool", action.get("kind", "unknown"))
                counts[(name, str(outcome.get("status")))] += 1
                result["last_action"] = {"episode_id": episode, "decision_index": index,
                    "name": name, "status": outcome.get("status")}
                if outcome.get("status") in ("failed", "invalid") or outcome.get("feedback"):
                    result["failures"].append({**result["last_action"], "arguments": action.get("arguments"),
                        "feedback": outcome.get("feedback"), "result": outcome.get("result")})
        result["execution_failures"] = [{
            "parent_episode_id": item["episode_id"], "decision_index": item["decision_index"],
            "diagnostic_ref": item["feedback"].get("diagnostic_ref"),
            "affected_refs": item["feedback"].get("affected_refs", []),
        } for item in result["failures"]
            if (item.get("feedback") or {}).get("code") == "execution_failed"]
        result["actions"] = [{"name": name, "status": status, "count": count}
            for (name, status), count in sorted(counts.items())]
        for table, key in (("literature_context_operations", "assessments"),
                           ("literature_a108_subscore_operations", "subscores")):
            if table in tables:
                for episode, operation_key, outcome in db.execute(
                        f"SELECT episode_id,operation_key,outcome FROM {table} ORDER BY rowid"):
                    result[key].append({"episode_id": episode, "operation_key": operation_key,
                        "outcome": json.loads(outcome)})
        if "runtime_report_attempts" in tables:
            for parent, child, form, failure, contract in db.execute(
                    "SELECT parent_episode_id,child_episode_id,form,failure,contract FROM runtime_report_attempts ORDER BY rowid"):
                result["returns"].append({"parent_episode_id": parent, "child_episode_id": child,
                    "admitted": form is not None and failure is None,
                    "form": json.loads(form) if form else None,
                    "failure": json.loads(failure) if failure else None,
                    "contract": json.loads(contract) if contract else None})
        result["prompt_receipts"] = capture_prompts(run)
        result["evidence_exports"] = capture_evidence(run, db, tables, result)
    finally:
        db.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    if "runs" not in run.parts:
        parser.error("run must be beneath the repository runs directory")
    report = inspect_run(run)
    destination = run / "evidence-inventory.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"inventory": str(destination), "process": report["process"],
        "workflow_terminal": report["workflow_result"] is not None or report["workflow_failure"] is not None,
        "episodes": report.get("episodes"), "last_action": report.get("last_action"),
        "execution_failures": report.get("execution_failures", []),
        "assessments": len(report.get("assessments", [])), "subscores": len(report.get("subscores", [])),
        "admitted_returns": sum(item["admitted"] for item in report.get("returns", []))}))


if __name__ == "__main__":
    main()
