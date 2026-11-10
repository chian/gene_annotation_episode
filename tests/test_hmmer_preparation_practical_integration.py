"""L1 selected practical operations and original-attempt progress integration.

The request matrix uses retained real producer requests. Native cases below run
small installed HMMER operations under the existing 20 GiB / 4 GiB lifecycle.
Contexts and selected actions are engineering fixtures, not model decisions or
the full shared Workflow commissioning/admission proof owned by workload277.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
import pytest

from method_loop.durable import DurableExecutionStore
from gene_annotation_episode import native_lifecycle as native
from gene_annotation_episode.communication import plain
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_monitoring import ProgressProvider
from gene_annotation_episode.execution_progress import ExecutionProgressProvider
from gene_annotation_episode.hmmer_preparation_result_views import (
    preparation_fact_sources, preparation_projection_catalog,
)
from gene_annotation_episode.native_hmmer_preparation_acquisition import capture_local_bundle
from gene_annotation_episode.native_hmmer_preparation_contracts import (
    PROGRAM_MODES, requested_job_from_hmmer_preparation,
)
from gene_annotation_episode.native_hmmer_preparation_local import (
    ATTEMPT_NAME, PLAN_NAME, local_hmmer_preparation_plan,
)
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from gene_annotation_episode.practical_execution_records import (
    ASSIGNMENT_SCHEMA, canonical, digest, validate_assignment,
)
from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
POLICY = {'memory_bytes': 20 * 1024 ** 3, 'scratch_bytes': 4 * 1024 ** 3}
RUN, CHILD, RESOURCE = "workload276", "local-child276", "local276"
FIELDS = ["execution_status", "measurements", "log_windows", "committed_record_refs",
          "dependencies", "result_available"]


def _retained_plans():
    producer = ROOT / "verification/tool_graders_hmmer_preparation_producer_2026-10-26_267/check005/temporary"
    current = ROOT / "verification/tool_graders_hmmer_preparation_capture_2026-10-26_270/check005/temporary"
    paths = {}
    for directory in (producer, current):
        for path in sorted(directory.glob("test_actual_all_selected_modes*/plan.json")):
            job = json.loads(path.read_bytes())["requested_job"]["native_hmmer_preparation"]
            paths[job["program"], job["mode"]] = path
    expected = {(program, mode) for program, modes in PROGRAM_MODES.items() for mode in modes}
    assert set(paths) == expected and len(paths) == 26
    return paths


RETAINED = _retained_plans()


def request(program="hmmconvert", mode="binary"):
    return json.loads(RETAINED[program, mode].read_bytes())["requested_job"]


def configuration(workspace, selected):
    job = selected["native_hmmer_preparation"]
    return {"kind": "local", "workspace": str(workspace), "policy": deepcopy(POLICY),
        "native_hmmer_preparation": [{key: deepcopy(job[key])
            for key in ("program", "mode", "software")} ]}


def assignment(workspace, selected, *, start_index=0, unmatched_output=False):
    attempt = workspace / ".episode-operations" / digest({"run": RUN, "episode": CHILD}) / digest(
        f"{RUN}:{CHILD}:{start_index}") / ATTEMPT_NAME
    outputs = [str(attempt / "bundle.json")]
    if unmatched_output:
        # An unrelated file predicate cannot become a claimed native output.
        outputs.append(str(workspace / "unselected-output"))
    return {"version": "practical_assignment_v1", "assignment_id": "selected-preparation276",
        "resource_kind": "local", "resource_id": RESOURCE, "workspace": str(workspace),
        "endpoint": "completed_job_outputs", "requested_job": deepcopy(selected),
        "progress_requirements": [{"key": "outputs", "credit": 2.5,
            "predicate": {"kind": "requested_job_outputs", "output_paths": outputs}}],
        "completion_keys": ["outputs"], "initial_context": {"revision": 0,
            "cwd": str(workspace / "selected-cwd"), "environment": {"CONTEXT_ONLY": "unchanged"}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}


def forbid(*args, **kwargs):
    pytest.fail("unselected native execution, status, or replay I/O")


@pytest.mark.parametrize("program,mode", list(RETAINED))
def test_all26_retained_requests_validate_without_execution(tmp_path, monkeypatch, program, mode):
    selected = request(program, mode)
    original = deepcopy(selected)
    value = assignment(tmp_path, selected)
    config = configuration(tmp_path, selected)
    for name in ("prepare_job", "start_prepared", "resume_start", "start_job", "status"):
        monkeypatch.setattr(native, name, forbid)
    operations = LocalPracticalOperations(config)
    Draft202012Validator(ASSIGNMENT_SCHEMA).validate(value)
    assert validate_assignment(value) == value
    operations.validate_assignment(value)
    assert "requested_job" not in operations.initial_outcome(value)["facts"]
    assert selected == original and not (tmp_path / ".episode-operations").exists()
    if program == "hmmsim":
        assert "capture_2026-10-26_270/check005" in str(RETAINED[program, mode])


@pytest.mark.parametrize("fault", ["unbound_mode", "software", "version", "missing_resource",
    "hpc", "argv", "allocation", "duplicate_binding"])
def test_wrong_requests_resources_software_and_allocation_reject(tmp_path, fault):
    selected = request()
    config = configuration(tmp_path, selected)
    value = assignment(tmp_path, selected)
    if fault == "unbound_mode":
        value["requested_job"] = request("hmmconvert", "ascii")
    elif fault == "software":
        job = deepcopy(selected["native_hmmer_preparation"])
        job["software"]["sha256"] = "a" * 64
        value["requested_job"] = requested_job_from_hmmer_preparation(job)
    elif fault == "version":
        config["native_hmmer_preparation"][0]["software"]["engine_version"] = "3.3"
    elif fault == "missing_resource":
        del value["resource_id"]
    elif fault == "hpc":
        value["resource_kind"] = "hpc"
    elif fault == "argv":
        value["requested_job"]["argv"].append("--unselected")
    elif fault == "allocation":
        value["constraints"]["allocation"]["memory_bytes"] += 1
    else:
        config["native_hmmer_preparation"].append(deepcopy(config["native_hmmer_preparation"][0]))
    with pytest.raises(ValueError):
        LocalPracticalOperations(config).validate_assignment(validate_assignment(value))
    assert not (tmp_path / ".episode-operations").exists()


@contextmanager
def harness(tmp_path, selected, *, start_index=0, unmatched_output=False):
    workspace = tmp_path / "project"
    (workspace / "selected-cwd").mkdir(parents=True)
    value = assignment(workspace, selected, start_index=start_index, unmatched_output=unmatched_output)
    config = configuration(workspace, selected)
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="MACDEFGHIK", molecule="protein")
        scope = store.validate_scope({"subject_refs": [store.targets()[0]["id"]]})
        message = {"scope": scope, "episode_assignment": value}
        context = BindingContext(RUN, CHILD, "launch_local", (("launch_local", "selected"),),
            scope, value, {"message": message})
        journal = Journal(store, RUN)
        with store.transaction():
            journal.save("runtime_episodes", {"episode_id": CHILD,
                "path": canonical(plain(context.path)), "request": canonical({"message": message}),
                "initial_credit": 0, "state": "running"})
        binding = PracticalResourceEpisodes(None, directory=tmp_path / "runtime",
            resources={"local": config}, store=store)
        state = binding.initialize(context)
        adapter = ExecutionProgressProvider(store, run_id=RUN, directory=tmp_path / "progress",
            resources={RESOURCE: config}, api_execution=None, log_window_bytes=128,
            log_roles=("stdout", "stderr"))
        provider = ProgressProvider(store, DurableExecutionStore(tmp_path / "durable"),
            run_id=RUN, job_provider=adapter)

        def select(index, tool="practical.job.start", arguments=None):
            arguments = {} if arguments is None else arguments
            action = {"kind": "tool", "tool": tool, "arguments": arguments}
            old = journal.row("runtime_actions", CHILD, index)
            if old is None:
                with store.transaction():
                    journal.save("runtime_actions", {"episode_id": CHILD, "decision_index": index,
                        "action": canonical(action), "result": None, "credit": None})
            else:
                assert old["action"] == canonical(action)
            outcome = asyncio.run(binding.execute(context, tool, arguments, f"{RUN}:{CHILD}:{index}"))
            assert outcome["status"] == "completed", outcome
            with store.transaction():
                store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
                    (canonical(outcome), RUN, CHILD, index))
            return outcome

        yield SimpleNamespace(store=store, state=state, binding=binding, context=context,
            assignment=value, config=config, workspace=workspace, select=select,
            adapter=adapter, progress=provider, scope=scope)


def wait_original(outcome):
    execution_id = outcome["result"]["outcome"]["facts"]["requested_job"]["execution_id"]
    handle = native.NativeJobHandle(Path(execution_id))
    result = native.wait_job(handle)
    assert result.metadata["policy"] == POLICY
    assert result.metadata["verified_cgroup"]["memory_max"] == POLICY["memory_bytes"]
    assert 'runtime_max' not in result.metadata["verified_cgroup"]
    return handle, result


def state_bytes(state):
    return {str(path.relative_to(state.directory)): path.read_bytes()
        for path in state.directory.rglob("*.json")}


def test_actual_binary_start_progress_capture_and_exact_replay(tmp_path, monkeypatch):
    with harness(tmp_path, request(), unmatched_output=True) as e:
        assert not (e.workspace / ".episode-operations").exists()
        started = e.select(0)
        handle, result = wait_original(started)
        assert result.returncode == 0
        plan = local_hmmer_preparation_plan(e.assignment, str(handle.path))
        assert plan["identity"]["operation_key"] == f"{RUN}:{CHILD}:0"
        assert plan["requested_job"] == e.assignment["requested_job"]
        assert plan["policy"] == POLICY
        attempt = Path(plan["attempt_directory"])
        binary = attempt / "outputs/converted_models"
        raw = binary.read_bytes()
        assert raw and not raw.startswith(b"HMMER3/")
        reference, = started["record_refs"]
        before = state_bytes(e.state)
        credit = e.state.credit_view()
        original_open = Path.open

        def exclude_binary_read(path, *args, **kwargs):
            if path == binary:
                pytest.fail("binary model artifact opened as a log")
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", exclude_binary_read)
            observed = e.progress.observe(reference, FIELDS, e.scope, operation_key="monitor:binary")
            status = e.select(1, "practical.job.status")
        native_view = observed["execution_status"]["native"]
        assert native_view["state"] == "completed" and observed["result_available"]
        stdout = next(row for row in native_view["outputs"] if row["role"] == "stdout")
        assert stdout == {"role": "stdout", "available": True, "bytes": len(raw), "writer_closed": True}
        assert [row["role"] for row in native_view["logs"]] == ["stderr"]
        assert [row["name"] for row in observed["measurements"]] == ["systemd_service_wall_seconds"]
        assert len(observed["log_windows"]) == 1
        detail = status["result"]["outcome"]["native_outcome"]
        assert set(detail["observed_logs"]) == {"stderr"}
        assert next(row for row in detail["observed_outputs"] if row["role"] == "converted_models")["bytes"] == len(raw)
        fact = status["result"]["outcome"]["facts"]["requested_job"]
        assert str(binary) in fact["output_paths"] and str(attempt / "bundle.json") in fact["output_paths"]
        assert str(e.workspace / "unselected-output") not in fact["output_paths"]
        assert not e.state.completion_proof() and e.state.credit_view()["credit"] == credit["credit"]
        assert all(state_bytes(e.state)[key] == data for key, data in before.items())
        target = e.adapter.targets.read_target(reference, e.scope)
        captured = capture_local_bundle(e.store, target=target, directory=tmp_path / "capture")
        assert captured["complete"] and captured["bundle_validated"]
        aliases = [row for row in captured["artifacts"] if row["direction"] == "output"
            and row["role"] in {"stdout", "converted_models"}]
        assert len(aliases) == 2 and len({row["artifact_ref"] for row in aliases}) == 1
        assert e.store.get_artifact(aliases[0]["artifact_ref"]) == raw
        selector = {"version": "native_hmmer_preparation_result_selector_v1",
            "acquisition": "complete_bound_bundle", "projection": None,
            "artifacts": [{"direction": "output", "role": "converted_models", "ordinal": 0}]}
        described = e.adapter.targets.describe_target(reference, e.scope, selector=selector)
        assert described["output_format"] == "native_hmmer_preparation_bundle_v1"
        assert described["service_or_program"] == "hmmconvert" and described["operation"] == "binary"
        assert described["result_selection"] == selector
        assert described["projection_catalog"] == preparation_projection_catalog("hmmconvert", "binary")
        assert described["acquisition_operations"] == ["execution.results.status", "execution.results.collect"]
        collector = described["extractors"][1]
        assert collector["implementation"] == "gene_annotation_episode.native_hmmer_preparation_results.NativeHmmerPreparationResults.execute"
        assert collector["return_fact_sources"] == ["execution_result_refs", "execution_result_origin", *preparation_fact_sources()]
        assert collector["return_fields"] == ["source_ref", "record_refs", "rows", "artifacts", "population", "failures", "complete"]
        assert collector["scientific_annotation_score"] is False
        wrong = deepcopy(selector)
        wrong["artifacts"][0]["role"] = "hits"
        with pytest.raises(ContractError, match="artifact_role_not_in_operation"):
            e.adapter.targets.describe_target(reference, e.scope, selector=wrong)
        stable = state_bytes(e.state)
        for name in ("prepare_job", "start_prepared", "resume_start", "status"):
            monkeypatch.setattr(native, name, forbid)
        monkeypatch.setattr(e.adapter.targets, "read_target", forbid)
        assert e.select(0) == started
        assert e.progress.observe(reference, FIELDS, e.scope, operation_key="monitor:binary") == observed
        assert state_bytes(e.state) == stable
        assert len(list(e.workspace.rglob("native.json"))) == 1
        (tmp_path / "evidence.json").write_text(json.dumps({"execution_id": str(handle.path),
            "binary_size_bytes": len(raw), "binary_sha256": hashlib.sha256(raw).hexdigest(),
            "measurement": result.metadata["duration_measure"], "elapsed_seconds": result.metadata["elapsed_seconds"],
            "policy": POLICY, "captured_aliases": aliases, "progress": observed}, indent=2) + "\n")


@pytest.mark.parametrize("program,mode", [("hmmstat", "summary"), ("hmmbuild", "build_alignment")])
def test_actual_text_modes_and_caller_cpu_preserved(tmp_path, program, mode):
    selected = request(program, mode)
    if program == "hmmbuild":
        job = selected["native_hmmer_preparation"]
        job["options"][job["options"].index("--cpu") + 1] = "2"
        selected = requested_job_from_hmmer_preparation(job)
    with harness(tmp_path, selected) as e:
        started = e.select(0)
        handle, result = wait_original(started)
        assert result.returncode == 0
        plan = local_hmmer_preparation_plan(e.assignment, str(handle.path))
        bundle = json.loads((Path(plan["attempt_directory"]) / "bundle.json").read_bytes())
        assert bundle["returncode"] == 0 and not bundle["failures"]
        assert bundle["requested_job"] == selected
        assert bundle["environment"].get("CONTEXT_ONLY") is None
        assert bundle["environment"]["TMPDIR"] == str(Path(plan["attempt_directory"]) / "tmp")
        if program == "hmmbuild":
            assert bundle["operation"]["settings"]["--cpu"] == 2
            assert bundle["realized_argv"][bundle["realized_argv"].index("--cpu") + 1] == "2"
        reference, = started["record_refs"]
        before = state_bytes(e.state)
        observed = e.progress.observe(reference, FIELDS, e.scope, operation_key="monitor:text")
        stdout = next(row for row in observed["execution_status"]["native"]["logs"] if row["role"] == "stdout")
        source_path = Path(plan["attempt_directory"]) / next(row["relative_path"] for row in
            selected["native_hmmer_preparation"]["outputs"] if row["role"] == "stdout")
        import base64
        assert base64.b64decode(stdout["bytes_base64"]) == source_path.read_bytes()[-128:]
        assert state_bytes(e.state) == before
        (tmp_path / "evidence.json").write_text(json.dumps({"execution_id": str(handle.path),
            "program": program, "mode": mode, "bundle_identity": bundle["identity"],
            "operation": bundle["operation"], "policy": result.metadata["policy"]}, indent=2) + "\n")


def test_ordinary_preparation_command_does_not_select_hmmer_job(tmp_path):
    with harness(tmp_path, request(), start_index=1) as e:
        outcome = e.select(0, "practical.command.run", {"argv": ["/usr/bin/printf", "ordinary preparation\n"],
            "environment": {"COMMAND_ONLY": "selected"}})
        facts = outcome["result"]["outcome"]["facts"]
        assert "requested_job" not in facts and facts["command"]["returncode"] == 0
        assert facts["command"]["environment"] == {"CONTEXT_ONLY": "unchanged", "COMMAND_ONLY": "selected"}
        assert not list(e.workspace.rglob(PLAN_NAME))
        assert not e.state.completion_proof() and e.state.credit_view()["credit"] == 0


def test_actual_failure_explicit_retry_preserves_old_attempt_and_replay(tmp_path, monkeypatch):
    selected = request("hmmfetch", "single_key")
    selected["native_hmmer_preparation"]["key"] = "NO_SUCH_MODEL_276"
    selected = requested_job_from_hmmer_preparation(selected["native_hmmer_preparation"])
    with harness(tmp_path, selected) as e:
        first = e.select(0)
        first_handle, first_result = wait_original(first)
        assert first_result.returncode == 1
        first_plan = local_hmmer_preparation_plan(e.assignment, str(first_handle.path))
        first_bundle_path = Path(first_plan["attempt_directory"]) / "bundle.json"
        first_bytes = first_bundle_path.read_bytes()
        repeated = e.select(1)
        assert repeated["result"]["outcome"]["facts"]["requested_job"]["execution_id"] == str(first_handle.path)
        assert len(list(e.workspace.rglob("native.json"))) == 1
        rejected = e.select(2, arguments={"retry_failed_execution_id": str(e.workspace / "wrong/native.json")})
        assert rejected["result"]["outcome"]["native_outcome"]["failure"]["code"] == "practical_retry_requires_original_failed_execution"
        retried = e.select(3, arguments={"retry_failed_execution_id": str(first_handle.path)})
        retry_handle, retry_result = wait_original(retried)
        assert retry_result.returncode == 1 and retry_handle.path != first_handle.path
        assert first_bundle_path.read_bytes() == first_bytes
        reference, = first["record_refs"]
        target = e.adapter.targets.read_target(reference, e.scope)
        assert target["execution_id"] == str(first_handle.path)
        observed = e.progress.observe(reference, FIELDS, e.scope, operation_key="monitor:old-failure")
        assert observed["execution_status"]["execution_id"] == str(first_handle.path)
        assert observed["execution_status"]["native"]["state"] == "failed"
        assert len(list(e.workspace.rglob("native.json"))) == 2 and len(e.state.receipts()) == 4
        before = state_bytes(e.state)
        for name in ("prepare_job", "start_prepared", "resume_start", "status"):
            monkeypatch.setattr(native, name, forbid)
        assert e.select(0) == first
        assert e.select(3, arguments={"retry_failed_execution_id": str(first_handle.path)}) == retried
        assert state_bytes(e.state) == before


def test_reservation_owner_and_original_resource_checked_before_observation(tmp_path, monkeypatch):
    with harness(tmp_path, request()) as e:
        # The selected start freezes a real reservation while the controlled
        # fixture leaves its native unit unsubmitted. This is not a native run.
        monkeypatch.setattr(native, "start_prepared", lambda handle: handle)
        started = e.select(0)
        execution_id = started["result"]["outcome"]["facts"]["requested_job"]["execution_id"]
        operations = LocalPracticalOperations(e.config)
        for changed_identity in ({"run_id": "wrong"}, {"origin_episode_id": "wrong"},
                {"attempt_id": "a" * 64}, {"original_operation_key": "wrong"}):
            with pytest.raises(ValueError, match="original_owner_conflict"):
                operations.observe_execution(e.assignment, execution_id, **changed_identity)
        wrong_assignment = deepcopy(e.assignment)
        wrong_assignment["resource_id"] = "other-resource"
        with pytest.raises(ValueError, match="original_attempt_conflict"):
            operations.observe_execution(wrong_assignment, execution_id)
        original = Path(execution_id).parent / "invoke.json"
        original.write_text('{}\n')
        with pytest.raises(ValueError, match="original_attempt_conflict"):
            operations.observe_execution(e.assignment, execution_id)

