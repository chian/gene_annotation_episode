"""A107/A110 saved-carrier engineering port; see PRIVATE_SAVED_CARRIERS.md.

This helper never selects or executes a model/native/scientific action. The
actual runtime publishes the run's descriptor list and writes closed archives.
Initialization and the completed unit/live projection are controlled metadata
inputs. Authentication, receipt prefixes, closed reads and resume descriptor
comparison are the actual implementations. No old digest is made current.
"""
from __future__ import annotations

import asyncio
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
import hashlib
import importlib
import json
from pathlib import Path
import traceback
from unittest.mock import patch

from gene_annotation_episode.episodic_workflow.root.tests.hpc_prediction_inputs import resources, commission
from gene_annotation_episode.episodic_workflow.root.tests.scientific_head_boundaries import write_instruction_source


AXES = ("a107", "a110")
PARENTS = ("hpc_work_planning", "hpc_work_planning/hpc_allocation_execution",
    "scientific_process/hpc_work_planning",
    "scientific_process/hpc_work_planning/hpc_allocation_execution")
HOMES = tuple((parent + "/" + leaf, role) for parent in PARENTS for leaf, role in (
    ("execution_job_submission", "launch"), ("execution_result_acquisition", "results")))
CLOSED = "execution_closed_operational_credit_v1"
SCHEMA = {"type": "object", "properties": {"completed": {
    "type": "boolean", "x-source": "execution_completed"}},
    "required": ["completed"], "additionalProperties": False}
VIEW = {"credit": 3, "operational_credit": 3, "new_handoff_count": 1,
    "new_acquired_record_count": 0, "operational_credit_binding": {
        "version": "controlled_saved_carrier_projection_v1", "handoff_unit": 3,
        "acquired_record_unit": 2, "scientific_credit": False, "monitoring_credit": False}}


def module(axis, name):
    if axis not in AXES:
        raise ValueError("reviewed_axis_required")
    return importlib.import_module("gene_annotation_episode.episodic_workflow.root."
        + axis + "." + name.replace("/", "."))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def failure(error):
    return {"status": "raised", "type": type(error).__module__ + "." + type(error).__qualname__,
        "message": str(error), "failure": getattr(error, "failure", None),
        "traceback": traceback.format_exc()}


def forbidden(*_args, **_kwargs):
    raise AssertionError("saved_carrier_probe_crossed_controlled_execution_port")


def controller_factory(*_args, **_kwargs):
    # No loop is run. An unexpected request for a continuation controller is
    # an error, not an alternate stopping policy.
    return forbidden(*_args, **_kwargs)


def project_credit(*_args, **_kwargs):
    return 0


class BeforeRootBuild(Exception):
    pass


def factories(axis, directory):
    """Literal reviewed factory paths; never import a descriptor-supplied name."""
    library = module(axis, "scientific_process_library").ScientificProcessLibrary(
        directory / "scientific-process-library")
    tool_library = module(axis, "scientific_tool_library").ScientificToolLibrary(
        directory / "scientific-tool-library")
    result = []

    def science(services):
        return module(axis, "scientific_process/episode").ScientificProcessEpisode(services,
            library=library, tool_library=tool_library, child_roles=("scientific_process", "hpc"))
    result.append(science)

    def constructor(home, kind):
        def build(services):
            workflow = services.workflow
            if kind == "monitor":
                return module(axis, home + "/episode").MonitorEpisode(services)
            options = dict(store=workflow.store, run_id=workflow.run_id,
                directory=workflow.directory, resources=resources())
            if kind == "hpc":
                return module(axis, home + "/episode").HPCEpisode(services,
                    **options, commissions={"commission": commission()})
            return module(axis, home + "/episode").ExecutionEpisode(services, **options,
                initial_information={}, tool_registry=None, handoff_unit=3,
                acquired_record_unit=2, log_window_bytes=1024, log_roles=("stdout", "stderr"))
        return build

    native = (("api_job_execution", "local_job_execution", "hpc_job_execution")
        if axis == "a107" else ("local_job_execution", "hpc_job_execution"))
    for parent in PARENTS:
        result.append(constructor(parent, "hpc"))
        result.append(constructor(parent + "/execution_job_submission", "execution"))
        for leaf in native:
            result.append(constructor(parent + "/execution_job_submission/" + leaf, "execution"))
        result.append(constructor(parent + "/execution_result_acquisition", "execution"))
        result.append(constructor(parent + "/execution_progress_assessment", "monitor"))
    for parent in (PARENTS[0], PARENTS[2]):
        result.append(constructor(parent + "/hpc_resource_prediction", "hpc"))
    assert len(result) == (31 if axis == "a107" else 27)
    return result


def published_workflow(axis, store, directory, *, resume=False, descriptors=False):
    """Stop only after real runtime run/settings publication or resume checks."""
    runtime = module(axis, "runtime")
    captured = []
    def intercept(workflow, *args, **kwargs):
        assert args[:2] == ("annotation", "root")
        captured.append(workflow)
        raise BeforeRootBuild()
    options = ({"episode_binding_descriptors": json.loads((directory / "workflow" / "run.json")
        .read_text())["episode_bindings"]} if descriptors else
        {"episode_binding_factories": factories(axis, directory)})
    with patch.object(runtime.Workflow, "build", intercept):
        try:
            asyncio.run(runtime._run_bound_workflow(store, module(axis, "tools").ToolRegistry(store),
                provider=object(), run_dir=directory / "workflow", resume=resume,
                controller_factory=controller_factory, project_credit=project_credit,
                episode_record_receipts=True, initial_known_record_refs=[],
                annotation_child_roles=("hpc", "scientific_process"), decision_protocol=None, **options))
        except BeforeRootBuild:
            assert len(captured) == 1
            return captured[0]
    raise AssertionError("runtime_did_not_reach_reviewed_pre_action_boundary")


def metadata(store):
    """Whole logical Store custody, including run descriptors and receipts."""
    result = {}
    for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = row[0]
        quoted = '"' + name.replace('"', '""') + '"'
        values = [list(value) for value in store.db.execute("SELECT * FROM " + quoted)]
        # Source bodies are text; retain an explicit encoding if a future schema
        # stores bytes. No filesystem/native payload read is needed here.
        values = [[{"blob_sha256": sha(v)} if isinstance(v, bytes) else v for v in value]
            for value in values]
        result[name] = {"rows": len(values), "sha256": sha(canonical(
            sorted(values, key=canonical)).encode())}
    return result


def source_manifest(axis):
    directory = Path(module(axis, "runtime").__file__).parent
    return {str(path.relative_to(directory)): sha(path.read_bytes())
        for path in sorted(directory.rglob("*.py")) if "tests" not in path.parts}


def ancestor(workflow, axis, path, scope, *, parent=None):
    """Controlled ancestor request, genuine typed identity/receipt/Journal row.

    This is not a prepared scientific invocation or an executed HPC commission.
    The closure probe needs authenticated ancestor request custody only.
    """
    runtime = module(axis, "runtime")
    episode_id = module(axis, "method_loop.identities").EpisodeRef(workflow.run_id, path).episode_id
    existing = workflow.journal.row("runtime_episodes", episode_id)
    assignment = {"commission_id": "commission"} if path[-1][0] in ("hpc", "hpc_execution") else {}
    goal = runtime.EpisodeGoal.root(objective="Controlled saved carrier ancestor", result_contract={})
    message = {"scope": scope, "initial_report": {}, "episode_assignment": assignment,
        "knowledge_inheritance": workflow.receipts.bind(episode_id,
            None if parent is None else parent.episode_id)}
    request = runtime.EpisodeRequest(goal, runtime.Record(message), None).as_record()
    if existing is None:
        workflow.journal.save("runtime_episodes", {"episode_id": episode_id,
            "path": canonical(path), "request": canonical(request), "initial_credit": 0,
            "state": "active", "completion": None, "archive": None})
        if parent is None:
            workflow.receipts.receive(episode_id, scope["subject_refs"], kind="initial")
    else:
        assert json.loads(existing["request"]) == request
    context = module(axis, "episode_bindings").BindingContext(workflow.run_id, episode_id,
        path[-1][0], path, scope, assignment, request)
    return context, goal


def close_carrier(axis, workflow, owner, home, role, scope):
    runtime = module(axis, "runtime")
    scientific = home.startswith("scientific_process/")
    allocation = "/hpc_allocation_execution/" in home
    ancestry = (("annotation", "root"),)
    if scientific:
        ancestry += (("scientific_process", "controlled_science"),)
    ancestry += (("hpc", "controlled_hpc"),)
    if allocation:
        ancestry += (("hpc_execution", "controlled_allocation"),)
    parent = None
    for depth in range(1, len(ancestry) + 1):
        parent, parent_goal = ancestor(workflow, axis, ancestry[:depth], scope, parent=parent)
    # The assignment is explicitly a controlled metadata operand. Admission and
    # native handoff authentication are covered by the separate connected tests.
    assignment = ({"version": "execution_launch_assignment_v1", "requests": {},
        "immutable_input_versions": [], "constraints": {}} if role == "launch" else
        {"version": "execution_results_assignment_v1", "handoff_ref": scope["subject_refs"][0],
            "selector": {"path": "controlled-metadata-only.txt", "offset": 0, "limit": 1}})
    index = 0 if role == "launch" else 1
    contract = runtime.TypedReportContract("Return the controlled incomplete status", SCHEMA, lambda *_: True)
    calls = []
    live = {**deepcopy(VIEW), "credit": 0, "operational_credit": 0, "new_handoff_count": 0}
    def projection(context, selection):
        calls.append({"context": context.as_record(), "selection": deepcopy(selection)})
        return deepcopy(live)
    with ExitStack() as ports:
        ports.enter_context(patch.object(owner, "initialize", lambda *_: None))
        ports.enter_context(patch.object(owner, "_live_project_credit", projection))
        ports.enter_context(patch.object(owner, "_live_facts", lambda *_: {"execution_completed": False}))
        ports.enter_context(patch.object(workflow.episode_bindings, "initial_references", lambda *_: ()))
        ports.enter_context(patch.object(workflow.episode_bindings, "received_report_facts", lambda *a, **k: {}))
        ports.enter_context(patch.object(workflow, "receive_tool_attributions", lambda *a, **k: []))
        ports.enter_context(patch.object(workflow, "validate_report", lambda *a, **k: None))
        child = workflow.build(role, "child_" + str(index), "Controlled closed carrier", scope,
            parent=parent_goal, parent_path=ancestry, contract=contract, episode_assignment=assignment)
        context = workflow.binding_context(child.source)
        assert workflow.specialist(child.source) is owner
        selection = {"kind": "episode_child", "role": role, "scope": scope,
            "assignment": assignment, "purpose": contract.decision, "goal": "Controlled closed carrier",
            "initial_report_json": "{}", "schema_json": canonical(SCHEMA)}
        workflow.journal.save("runtime_actions", {"episode_id": parent.episode_id,
            "decision_index": index, "action": canonical(selection), "result": None, "credit": None})
        live = deepcopy(VIEW)
        calls.clear()
        unit_ref = module(axis, "method_loop.identities").UnitRef(context.episode_id, 0)
        unit = module(axis, "method_loop.episode").UnitRecord("controlled:0", {"credit": 3},
            None, "controlled_saved_carrier_epoch", unit_ref)
        record = module(axis, "method_loop.episode").EpisodeRecord(role, "child_" + str(index), 1,
            "incomplete", (unit,), None, child.request, path=child.source.path,
            end_reason="",
            episode_ref=module(axis, "method_loop.identities").EpisodeRef(workflow.run_id, child.source.path))
        outcome = {"status": "unavailable", "record_refs": [], "changed_record_refs": [],
            "feedback": {"category": "controlled_saved_carrier_probe", "code": "no_native_operation"}}
        workflow.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": 0,
            "action": canonical({"kind": "tool", "tool": ("execution.capabilities"
                if role == "launch" else "execution.results.status"), "arguments": {}}),
            "result": canonical(outcome), "credit": 3})
        slot = workflow.completions.stage(context.episode_id, 0, label=unit.unit_label,
            kind="own_action", controller_input=runtime.Record({"credit": 3}), child_return=None)
        assert slot["sequence"] == 0
        workflow.completions.confirm_observed(context.episode_id, 0,
            {"label": unit.unit_label, "unit_ref": unit_ref.as_record(),
                "credit": {"credit": 3}, "step": None, "decision_index": 0})
        workflow.completions.checkpoint_source(context.episode_id, expected_revision=None,
            latest_effect_index=None, last_outcome_index=0, feedback=outcome["feedback"])
        child.source.last_outcome, child.source.last_outcome_index = outcome, 0
        child.on_close(record)
        facts = workflow.facts(child.source, completion_record=record)
        assert len(calls) == 1 and facts[CLOSED]["view"] == VIEW
        form = module(axis, "communication").form_with_facts({}, SCHEMA, facts)
        assert form == {"completed": False}
        workflow.journal.save("runtime_forms", {"episode_id": context.episode_id,
            "facts": canonical({**facts, "interpretations": {}}), "form": canonical(form)})
    # A rejected/incomplete parent delivery is explicit. Closed operational
    # credit must survive independently of successful report admission.
    workflow.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id,
        "decision_index": index, "delivery_ref": "delivery_controlled_" + context.episode_id,
        "child_episode_id": context.episode_id, "contract": canonical(contract.as_record()),
        "form": None, "failure": canonical({"category": "controlled_rejected_report"})})
    selected = {**workflow.record_selection(context.episode_id), **workflow.progress_selection(child.source)}
    with patch.object(owner, "_live_project_credit", forbidden), patch.object(workflow.store, "get_artifact", forbidden):
        assert owner.credit_view(context, selected) == VIEW
        assert owner.project_credit(context, selected) == VIEW
    descriptor = owner.as_record()
    assert module(axis, "execution_contracts").digest(descriptor) == facts[CLOSED]["binding_sha256"]
    return {"home": home, "role": role, "context": context.as_record(), "selection": selected,
        "parent_context": parent.as_record(), "selected_parent_action": selection,
        "original_operation_key": f"{workflow.run_id}:{parent.episode_id}:{index}",
        "descriptor": descriptor, "closed_carrier": facts[CLOSED], "form": form,
        "controlled_outcome": outcome, "live_projection_calls_at_closure": len(calls)}


def rebuild_saved_child(axis, workflow, saved):
    """Actual immutable request and completed-action cursor restoration.

    Keep the same controlled admission ports as capture. This tests a saved
    private source's reconstruction and original completion cursor, without
    selecting/replaying a provider call or executing another unit.
    """
    runtime = module(axis, "runtime")
    request = saved["context"]["request"]
    scope, assignment = request["message"]["scope"], request["message"]["episode_assignment"]
    parent = saved["parent_context"]
    parent_goal = runtime.EpisodeGoal.from_record(parent["request"]["goal"])
    original_goal = runtime.EpisodeGoal.from_record(request["goal"])
    declared = request["report_contract"]
    contract = runtime.TypedReportContract(declared["decision"], declared["measurements"]["schema"], lambda *_: True)
    assert contract.as_record() == declared
    owner = workflow.episode_bindings._by_path[saved["home"]]
    with ExitStack() as ports:
        ports.enter_context(patch.object(owner, "initialize", lambda *_: None))
        ports.enter_context(patch.object(owner, "_live_project_credit", forbidden))
        ports.enter_context(patch.object(owner, "_live_facts", forbidden))
        ports.enter_context(patch.object(workflow.store, "get_artifact", forbidden))
        ports.enter_context(patch.object(workflow.episode_bindings, "initial_references", lambda *_: ()))
        ports.enter_context(patch.object(workflow, "receive_tool_attributions", lambda *a, **k: []))
        ports.enter_context(patch.object(workflow, "validate_report", lambda *a, **k: None))
        child = workflow.build(saved["role"], saved["context"]["path"][-1][1], original_goal.objective,
            scope, parent=parent_goal, parent_path=tuple(tuple(value) for value in parent["path"]),
            contract=contract, initial=request["message"]["initial_report"], episode_assignment=assignment)
        assert child.request.as_record() == request
        assert workflow.binding_context(child.source).as_record() == saved["context"]
        child.source.restore()
        child.source.restore_checkpoint()
        assert child.source.last_outcome_index == 0
        assert child.source.last_outcome == saved["controlled_outcome"]
        assert child.source._unfinished_own_actions == []
        assert workflow.source_credit_view(child.source) == VIEW
        return {"status": "restored_exact_request_completed_outcome_and_closed_credit",
            "source_type": type(child.source).__module__ + "." + type(child.source).__qualname__,
            "episode_id": child.source.episode_id, "last_outcome_index": child.source.last_outcome_index,
            "unfinished_own_action_indices": list(child.source._unfinished_own_actions)}


def capture(axis, directory):
    directory.mkdir(parents=True)
    write_instruction_source(directory / "instruction-source", axis)
    module(axis, "scientific_process_library").ScientificProcessLibrary.freeze(
        directory / "scientific-process-library", source=directory / "instruction-source")
    module(axis, "scientific_tool_library").ScientificToolLibrary.freeze(
        directory / "scientific-tool-library", catalog=[])
    write(directory / "source_manifest.json", source_manifest(axis))
    with module(axis, "state").Store(directory / "state") as store:
        scope = {"subject_refs": store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")["subject_refs"]}
        workflow = published_workflow(axis, store, directory)
        descriptors = workflow.episode_bindings.as_record()
        rows = []
        for home, role in HOMES:
            owner, = [binding for binding in workflow.episode_bindings._bindings if binding.binding_path == home]
            rows.append(close_carrier(axis, workflow, owner, home, role, scope))
            write(directory / "captured_carriers.json", rows)
        run = dict(workflow.journal.row("runtime_runs"))
        assert json.loads(run["settings"])["episode_bindings"] == descriptors
        assert json.loads((directory / "workflow" / "run.json").read_text())["episode_bindings"] == descriptors
        assert all(row["descriptor"] in descriptors for row in rows)
        snapshot = metadata(store)
        result = {"axis": axis, "run_id": workflow.run_id, "carriers": rows,
            "runtime_run_row": run, "metadata": snapshot,
            "run_json_sha256": sha((directory / "workflow" / "run.json").read_bytes()),
            "archives": {str(path.relative_to(directory)): sha(path.read_bytes())
                for path in sorted((directory / "workflow" / "archive").rglob("*")) if path.is_file()},
            "source_manifest_sha256": sha((directory / "source_manifest.json").read_bytes()),
            "native_or_model_actions": 0, "scope": "Controlled closed-carrier and original descriptor custody"}
        write(directory / "capture.json", result)
    return {"axis": axis, "captured": len(rows), "run_id": result["run_id"]}


def read_probe(axis, captured, output):
    original = json.loads((captured / "capture.json").read_text())
    assert original["axis"] == axis
    assert sha((captured / "source_manifest.json").read_bytes()) == original["source_manifest_sha256"]
    assert sha((captured / "workflow" / "run.json").read_bytes()) == original["run_json_sha256"]
    assert all(sha((captured / path).read_bytes()) == digest
        for path, digest in original["archives"].items())
    output.mkdir(parents=True)
    rows = []
    with module(axis, "state").Store(captured / "state") as store:
        before = metadata(store)
        assert before == original["metadata"], "original_saved_state_changed_before_probe"
        # Use the actual current constructors with the same explicit operands.
        # Standard runtime reconstruction is tested separately below, since its
        # fail-closed descriptor check must not be bypassed to call these reads.
        from types import SimpleNamespace
        services = SimpleNamespace(workflow=SimpleNamespace(store=store,
            run_id=original["run_id"], directory=captured / "workflow"),
            annotation_task_required=lambda: False)
        for saved in original["carriers"]:
            row = {"home": saved["home"], "role": saved["role"],
                "original_descriptor": saved["descriptor"]}
            try:
                # The path is checked against the literal reviewed set before
                # importing; no module/class operand comes from a descriptor.
                assert (saved["home"], saved["role"]) in HOMES
                owner = module(axis, saved["home"] + "/episode").ExecutionEpisode(services,
                    store=store, run_id=original["run_id"], directory=captured / "workflow",
                    resources=resources(), initial_information={}, tool_registry=None,
                    handoff_unit=3, acquired_record_unit=2, log_window_bytes=1024,
                    log_roles=("stdout", "stderr"))
                row["current_descriptor"] = owner.as_record()
                row["same_descriptor"] = row["current_descriptor"] == saved["descriptor"]
                context = module(axis, "episode_bindings").BindingContext(**saved["context"])
                with patch.object(owner, "_live_project_credit", forbidden), patch.object(store, "get_artifact", forbidden):
                    value = owner.credit_view(context, deepcopy(saved["selection"]))
                    assert value == VIEW
                    assert owner.project_credit(context, deepcopy(saved["selection"])) == VIEW
                    row["closed_read"] = "returned_exact_original_view_without_live_projection"
                    # Refusing unrelated context/descriptor operands remains a
                    # distinct safety check; no historical identity is aliased.
                    rejected = replace(context, assignment={**dict(context.assignment), "unrelated": True})
                    try:
                        owner.credit_view(rejected, deepcopy(saved["selection"]))
                    except ValueError:
                        row["unrelated_context"] = "rejected"
                    else:
                        raise AssertionError("unrelated_closed_context_was_accepted")
            except Exception as error:
                row["read_result"] = failure(error)
            rows.append(row)
        resume = {}
        for kind in ("factories", "saved_descriptors"):
            try:
                workflow = published_workflow(axis, store, captured, resume=True,
                    descriptors=kind == "saved_descriptors")
                assert workflow.run_id == original["run_id"]
                resume[kind] = {"status": "passed_runtime_resume_checks_before_root_build",
                    "bindings": workflow.episode_bindings.as_record()}
                restored = []
                for saved in original["carriers"]:
                    try:
                        restored.append({"home": saved["home"],
                            **rebuild_saved_child(axis, workflow, saved)})
                    except Exception as error:
                        restored.append({"home": saved["home"], **failure(error)})
                resume[kind]["saved_child_reconstruction"] = restored
            except Exception as error:
                resume[kind] = failure(error)
            assert metadata(store) == before, "resume_probe_mutated_saved_store"
            assert sha((captured / "workflow" / "run.json").read_bytes()) == original["run_json_sha256"]
        assert metadata(store) == before
    result = {"axis": axis, "carriers": rows, "standard_runtime_reopen": resume,
        "saved_metadata_unchanged": True, "native_or_model_actions": 0,
        "scope": "Closed credit reads and runtime reconstruction checks; not full iterator replay"}
    write(output / "probe.json", result)
    write(output / "current_source_manifest.json", source_manifest(axis))
    return {"axis": axis, "read": sum(row.get("closed_read") is not None for row in rows),
        "total": len(rows), "probe": str(output / "probe.json")}
