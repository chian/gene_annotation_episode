"""Read actual failed Workflow state through contracted entry points.

No native action is dispatched. The original attempt remains unchanged.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import traceback

from gene_annotation_episode.communication import plain
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

reference = Path(sys.argv[1]).resolve()
output = Path.cwd()
shutil.copytree(reference / "state", output / "diagnostic-state")
store = Store(output / "diagnostic-state")
# Keep the native operand-location identity for read-only proof. The database
# remains the detached copy; artifact reads use the original retained root.
store.path = reference / "state"
row = store.db.execute("SELECT episode_id FROM runtime_actions WHERE json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid LIMIT 1").fetchone()
episode_id = row["episode_id"]
local = store.db.execute("SELECT request FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='launch_local' ORDER BY rowid LIMIT 1").fetchone()
assignment = json.loads(local["request"])["message"]["episode_assignment"]
job = assignment["requested_job"]["native_protein_structure"]
policy = assignment["constraints"]["allocation"]
resources = {assignment["resource_id"]: {"kind": "local", "workspace": assignment["workspace"], "policy": deepcopy(policy),
    "native_protein_structure": [{"operation": "extract_sequence", "scientific_mode": None, "software": job["software"]},
        {"operation": "compare", "scientific_mode": "fit_then_evaluate_ca", "software": job["software"]}]}}
owner = ExecutionEpisodes(None, store=store, run_id="protein-structure-workflow410", directory=reference / "run",
    resources=resources, initial_information={}, tool_registry=ToolRegistry(store, job_limits=policy),
    handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=("stdout", "stderr"))
store.db.execute("PRAGMA query_only=ON")
context = owner.native_protein_structure_returns.context(episode_id)
steps = []
def inspect_step(name, function):
    try:
        result = function()
    except BaseException:
        steps.append({"step": name, "outcome": "rejected", "traceback": traceback.format_exc()})
        (output / "diagnostic.json").write_text(json.dumps(steps, indent=2) + "\n")
        raise
    steps.append({"step": name, "outcome": "accepted"})
    (output / "diagnostic.json").write_text(json.dumps(steps, indent=2) + "\n")
    return result

try:
    inspect_step("catalog", lambda: owner.catalog(context))
    target = inspect_step("target", lambda: owner._target(context))
    inspect_step("selector", lambda: owner._selector(plain(context.assignment), target))
    inspect_step("returns.authenticate", lambda: owner.native_protein_structure_returns.authenticate(context))
    inspect_step("receipts.assignment", lambda: owner.native_protein_structure_results.receipts._assignment(context))
    inspect_step("receipts.intent", lambda: owner.native_protein_structure_results.receipts._intent(context, target,
        "execution.results.collect", {}, f"protein-structure-workflow410:{episode_id}:0"))
    from gene_annotation_episode.execution_contracts import canonical
    from gene_annotation_episode import protein_structure_result_receipts as receipts
    action_directory = owner.native_protein_structure_results.receipts.action_directory(
        episode_id=episode_id, operation_key=f"protein-structure-workflow410:{episode_id}:0")
    raw = (action_directory.parent.parent / "assignment.json").read_bytes()
    steps.append({"step": "shared_assignment_bytes", "canonical_plus_one_newline":
        raw == canonical(json.loads(raw)).encode() + b"\n", "last_byte": raw[-1], "byte_length": len(raw)})
    if sys.argv[2] == "--diagnose-report":
        from gene_annotation_episode.runtime import TypedReportContract
        contract_record = plain(context.request)["report_contract"]
        schema = contract_record["measurements"]["schema"]
        form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (episode_id,)).fetchone()[0])
        contract = TypedReportContract(contract_record["decision"], schema,
            lambda ref, namespace: owner.resolve_received_reference(context, ref, namespace),
            lambda value: owner.validate_report(context, value, schema))
        inspect_step("actual_typed_report_admission", lambda: contract.admit(form,
            audit_identifiers=(episode_id, plain(context.request)["goal"]["goal_id"])))
    else:
        inspect_step("receipts.decode_existing_shared_assignment", lambda: receipts._decode(raw))
finally:
    store.close()
print(json.dumps(steps))
