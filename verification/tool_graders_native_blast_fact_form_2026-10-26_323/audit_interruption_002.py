"""Read the stopped 323 fixture and retain a bounded, additive audit record."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job


packet = Path(__file__).resolve().parent
stopped = packet / "check_20261026T193659761061Z"
handle_path = packet / "observed_interrupted_handle_001.json"
handle = json.loads(handle_path.read_text())
directory = packet / ("interruption_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
directory.mkdir()
policy = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)
command = [value for value in handle["command"] if not value.startswith("--basetemp=")]
command.extend(["--collect-only", "--basetemp=" + str(directory / "tmp")])
result = run_local_job(command, cwd=directory, policy=policy,
    stdout_path=directory / "collection.txt", stderr_path=directory / "collection.stderr.txt",
    env={"PYTHONPATH": str(packet.parents[1]) + ":" + str(packet.parents[1] / "tests"), "PYTHONDONTWRITEBYTECODE": "1"})
nodes = [line for line in result.stdout_path.read_text().splitlines() if "::test_" in line]
progress = (stopped / "stdout.txt").read_text()
completed = sum(line.split(" [", 1)[0].count(".") for line in progress.splitlines())
state = stopped / "tmp/test_public_genome_resolvers_r0/state/state.sqlite3"
db = sqlite3.connect(f"file:{state}?mode=ro", uri=True)
actions = []
for episode, index, raw_action, raw_result in db.execute(
        "SELECT episode_id,decision_index,action,result FROM runtime_actions ORDER BY episode_id,decision_index"):
    action = json.loads(raw_action)
    outcome = json.loads(raw_result) if raw_result is not None else None
    actions.append(dict(episode_id=episode, decision_index=index,
        kind=action.get("kind"), tool=action.get("tool"),
        outcome_status=None if outcome is None else outcome.get("status")))
observations = db.execute("SELECT COUNT(*) FROM runtime_observations").fetchone()[0]
db.close()
record = dict(stopped_directory=str(stopped), selected_handle=str(handle_path),
    selected_unit=handle["unit"], selected_command=handle["command"],
    selected_policy=handle["metadata"]["policy"],
    reason="Operator caught forbidden native homology tests in the selected regression list; cancelled only this run's control group before those tests were reached.",
    terminal_runner_error="AcquisitionError: local_job_execution_error after explicit control-group cancellation; no successful full-run receipt.",
    completed_pass_markers=completed, collected_nodes=nodes,
    completed_nodes_by_collection_order=nodes[:completed],
    next_node_by_collection_order=nodes[completed] if completed < len(nodes) else None,
    fixture_directories=[p.name for p in sorted((stopped / "tmp").iterdir()) if p.is_dir() and not p.is_symlink()],
    fixture_actions=actions, fixture_runtime_observations=observations,
    scientific_execution_evidence="The only created fixture belongs to the controlled GenomeAlignment resolver test. Its service client is an in-memory ControlledClient/NativeClient; that test disables socket.create_connection and urllib.request.OpenerDirector.open before constructing it. Recorded API operation names are real production calls against this fixture, not remote API invocation. No homology fixture directory, homology job database, or nested native job handle was created.",
    collection_receipt=dict(command=command, policy=policy.to_dict(), returncode=result.returncode, metadata=result.metadata),
    evidence_sha256={str(path.relative_to(packet)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (handle_path, stopped / "stdout.txt", stopped / "stderr.txt", state, result.stdout_path, result.stderr_path)})
(directory / "INTERRUPTION_001.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
print(json.dumps(dict(directory=str(directory), completed=completed,
    next_node=record["next_node_by_collection_order"], fixture_actions=actions,
    collection_returncode=result.returncode), indent=2))
