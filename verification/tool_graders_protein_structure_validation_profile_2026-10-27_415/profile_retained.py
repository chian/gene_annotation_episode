"""Profile the actual retained packet410 diagnostic without native dispatch.

The diagnostic statements are copied from packet410/diagnose_retained.py.
Only timing, cProfile recording and a fail-closed subprocess/network guard are
added. The detached database and original Store.path semantics are retained.
"""
import cProfile
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import time
import traceback

output = Path.cwd()
reference = Path(sys.argv[1]).resolve()
stages, steps, blocked_calls = [], [], []


def forbid_native(event, arguments):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork", "os.forkpty", "socket.connect"}:
        blocked_calls.append({"event": event})
        raise RuntimeError("profile_diagnostic_native_or_network_dispatch_forbidden:" + event)


sys.addaudithook(forbid_native)


@contextmanager
def stage(name):
    wall_start, cpu_start = time.perf_counter(), time.process_time()
    row = {"stage": name, "outcome": "incomplete"}
    try:
        yield
    except BaseException:
        row.update(outcome="rejected", traceback=traceback.format_exc())
        raise
    else:
        row["outcome"] = "accepted"
    finally:
        row.update(wall_seconds=time.perf_counter() - wall_start,
                   process_cpu_seconds=time.process_time() - cpu_start)
        stages.append(row)
        (output / "profile_stages.json").write_text(json.dumps(stages, indent=2) + "\n")


def inspect_step(name, function):
    try:
        with stage(name):
            result = function()
    except BaseException:
        steps.append({"step": name, "outcome": "rejected", "traceback": traceback.format_exc()})
        (output / "diagnostic.json").write_text(json.dumps(steps, indent=2) + "\n")
        raise
    steps.append({"step": name, "outcome": "accepted"})
    (output / "diagnostic.json").write_text(json.dumps(steps, indent=2) + "\n")
    return result


def run_diagnostic():
    with stage("imports"):
        from copy import deepcopy
        import shutil
        from gene_annotation_episode.communication import plain
        from gene_annotation_episode.execution_episodes import ExecutionEpisodes
        from gene_annotation_episode.state import Store
        from gene_annotation_episode.tools import ToolRegistry
    with stage("copy_fixture_state"):
        shutil.copytree(reference / "state", output / "diagnostic-state")
    with stage("initialize_detached_store"):
        store = Store(output / "diagnostic-state")
        # Native operand-location identity is original; the DB is detached.
        store.path = reference / "state"
    try:
        with stage("read_assignment"):
            row = store.db.execute("SELECT episode_id FROM runtime_actions WHERE json_extract(action,'$.tool')='execution.results.collect' ORDER BY rowid LIMIT 1").fetchone()
            episode_id = row["episode_id"]
            local = store.db.execute("SELECT request FROM runtime_episodes WHERE json_extract(path,'$[#-1][0]')='launch_local' ORDER BY rowid LIMIT 1").fetchone()
            assignment = json.loads(local["request"])["message"]["episode_assignment"]
            job = assignment["requested_job"]["native_protein_structure"]
            policy = assignment["constraints"]["allocation"]
            resources = {assignment["resource_id"]: {"kind": "local", "workspace": assignment["workspace"], "policy": deepcopy(policy),
                "native_protein_structure": [{"operation": "extract_sequence", "scientific_mode": None, "software": job["software"]},
                    {"operation": "compare", "scientific_mode": "fit_then_evaluate_ca", "software": job["software"]}]}}
        with stage("construct_execution_owner"):
            owner = ExecutionEpisodes(None, store=store, run_id="protein-structure-workflow410", directory=reference / "run",
                resources=resources, initial_information={}, tool_registry=ToolRegistry(store, job_limits=policy),
                handoff_unit=3, acquired_record_unit=2, log_window_bytes=128, log_roles=("stdout", "stderr"))
        with stage("construct_authenticated_context"):
            store.db.execute("PRAGMA query_only=ON")
            context = owner.native_protein_structure_returns.context(episode_id)
        inspect_step("catalog", lambda: owner.catalog(context))
        target = inspect_step("target", lambda: owner._target(context))
        inspect_step("selector", lambda: owner._selector(plain(context.assignment), target))
        inspect_step("returns.authenticate", lambda: owner.native_protein_structure_returns.authenticate(context))
        inspect_step("receipts.assignment", lambda: owner.native_protein_structure_results.receipts._assignment(context))
        inspect_step("receipts.intent", lambda: owner.native_protein_structure_results.receipts._intent(context, target,
            "execution.results.collect", {}, f"protein-structure-workflow410:{episode_id}:0"))
        with stage("shared_assignment_bytes"):
            from gene_annotation_episode.execution_contracts import canonical
            action_directory = owner.native_protein_structure_results.receipts.action_directory(
                episode_id=episode_id, operation_key=f"protein-structure-workflow410:{episode_id}:0")
            raw = (action_directory.parent.parent / "assignment.json").read_bytes()
            steps.append({"step": "shared_assignment_bytes", "canonical_plus_one_newline":
                raw == canonical(json.loads(raw)).encode() + b"\n", "last_byte": raw[-1], "byte_length": len(raw)})
        with stage("construct_typed_report_contract"):
            from gene_annotation_episode.runtime import TypedReportContract
            contract_record = plain(context.request)["report_contract"]
            schema = contract_record["measurements"]["schema"]
            form = json.loads(store.db.execute("SELECT form FROM runtime_forms WHERE episode_id=?", (episode_id,)).fetchone()[0])
            contract = TypedReportContract(contract_record["decision"], schema,
                lambda ref, namespace: owner.resolve_received_reference(context, ref, namespace),
                lambda value: owner.validate_report(context, value, schema))
        inspect_step("actual_typed_report_admission", lambda: contract.admit(form,
            audit_identifiers=(episode_id, plain(context.request)["goal"]["goal_id"])))
    finally:
        with stage("close_detached_store"):
            store.close()


profiler = cProfile.Profile()
wall_start, cpu_start = time.perf_counter(), time.process_time()
profiler.enable()
try:
    run_diagnostic()
finally:
    profiler.disable()
    measured = {"wall_seconds": time.perf_counter() - wall_start,
        "process_cpu_seconds": time.process_time() - cpu_start,
        "blocked_dispatch_calls": blocked_calls,
        "scope": "single fresh-process retained-result diagnostic; no native scientific work rerun; not the full Workflow",
        "profile_timer": "cProfile default elapsed timer; overhead included; process CPU measured separately",
        "bootstrap_exclusion": "stdlib timing/profile helper imports before profiler.enable; process launcher and snapshot/input hashing also excluded"}
    profiler.dump_stats(str(output / "diagnostic.prof"))
    (output / "profile_measurement.json").write_text(json.dumps(measured, indent=2) + "\n")
print(json.dumps(steps))
