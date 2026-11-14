"""Scripted decisions through the actual shared Workflow and native bindings.

The inputs and scientific continuation horizons are engineering fixtures. All
resource selections, native outputs, receipts, typed returns and operational
endpoint estimators use production paths. No positive authority is injected.
"""
import asyncio
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from method_loop.archive import iter_json

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode.communication import plain, validate_closed_schema
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.execution_episodes import RESULTS_VERSION
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.native_protein_structure_acquisition import retained_protein_structure_file
from gene_annotation_episode.native_protein_structure_contracts import (
    POLICY, output_files, required_input_files, requested_job_from_protein_structure,
)
from gene_annotation_episode.native_protein_structure_local import local_protein_structure_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.protein_structure_formats import parse_pdb_structure
from gene_annotation_episode.protein_structure_result_views import protein_structure_fact_sources
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

A = import_module("verification.tool_graders_protein_structure_inputs_2026-10-27_386.fixture_helpers")
F = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")
ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
RUN_ID = "protein-structure-workflow410"
SOURCES = {name: "execution_protein_structure_" + suffix for name, suffix in (
    ("sequences", "sequences"), ("summary", "projections"), ("saved", "saved_sheets"), ("failures", "failures"))}
SUMMARY_FIELDS = ["alignment_score", "mapped_pair_count", "fit_used_count", "evaluation_used_count",
                  "evaluation_sse", "evaluation_rmsd"]


def result_form(*fields, completed=False):
    definitions = protein_structure_fact_sources()
    properties = {name: {**definitions[SOURCES[name]]["report_schema"], "x-source": SOURCES[name]} for name in fields}
    if completed:
        properties["completed"] = {"type": "boolean", "x-source": "execution_completed"}
    return validate_closed_schema({"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False})


HANDOFF_FORM = {"type": "object", "additionalProperties": False, "properties": {
    "completed": {"type": "boolean", "x-source": "execution_completed"},
    "references": {"type": "array", "uniqueItems": True, "items": {"type": "string", "format": "reference",
        "x-reference-namespace": "execution_handoff"}, "x-source": "execution_handoff_refs"}},
    "required": ["completed", "references"]}


def selector(*, saved=None, parameters=None, summary=False, return_saved=False, sequence=False):
    return {"version": "protein_structure_result_selector_v1",
        "acquisition": "retained_sheet_only" if saved is not None else "complete_bound_bundle",
        "saved_sheet": deepcopy(saved), "parameters": deepcopy(parameters),
        "projections": [{"projection_id": "requested_numerical_comparison", "family": "comparison_summary",
            "members": {"kind": "comparison"}, "fields": list(SUMMARY_FIELDS), "window": None,
            "delivery_kind": "values"}] if summary else [], "return_saved_sheet": return_saved,
        "sequence_allowed_uses": ["sequence_align", "structure_correspondence"] if sequence else []}


def action(name, arguments=None):
    return {"selection": {"kind": "tool", "tool": name, "arguments": arguments or {}}, "report_update": {}}


def commission(role, assignment, scope, form, *, objective):
    return {"selection": {"kind": "episode_child", "role": role,
        "goal": objective, "scope": scope,
        "purpose": "Return the requested typed facts with their original numerical meanings and custody.",
        "assignment": assignment, "schema_json": json.dumps(form), "initial_report_json": "{}"}, "report_update": {}}


def provider_value(value, schema):
    """Use the actual provider's existing JSON-object transport contract."""
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            candidate = provider_value(value, branch)
            if Draft202012Validator(branch).is_valid(candidate):
                return candidate
        return value
    if schema.get("type") == "string" and isinstance(value, dict) and schema.get("description", "").startswith("JSON encoding"):
        return json.dumps(value)
    if schema.get("type") == "object" and isinstance(value, dict):
        result = dict(value)
        for name, field in schema.get("properties", {}).items():
            if name in result:
                result[name] = provider_value(result[name], field)
            elif name in schema.get("required", []) and Draft202012Validator(field).is_valid(None):
                result[name] = None
        return result
    if isinstance(value, list) and "items" in schema:
        return [provider_value(item, schema["items"]) for item in value]
    return value


def walk(record):
    yield record
    for unit in record["units"]:
        if unit.get("child") is not None:
            yield from walk(unit["child"])


def history(record):
    return [unit["controller_step"]["marginal_credit"] for unit in record["units"]]


def file_identity(store, reference, format):
    metadata = store.get(reference)
    return {"artifact_ref": reference, "sha256": metadata["sha256"], "byte_length": metadata["size"], "format": format}


def selected_job(store, request, software):
    files = [{"input_id": "input_" + str(i), "role": role, "file_identity": deepcopy(identity),
        "path": str(retained_protein_structure_file(store, identity)), "staged_relative_path": "inputs/input_" + str(i)}
        for i, (role, identity) in enumerate(required_input_files(request))]
    return {"version": "native_protein_structure_job_v1", "program": "protein_structure_python",
        "request": deepcopy(request), "software": deepcopy(software), "inputs": files,
        "outputs": output_files(request["operation"]), "environment": {"PYTHONPATH": str(ROOT)}}


def launch_assignment(job, workspace, label):
    practical = {"version": "practical_assignment_v1", "assignment_id": label,
        "resource_id": "here", "resource_kind": "local", "workspace": str(workspace),
        "endpoint": "usable_handoff", "requested_job": requested_job_from_protein_structure(job),
        "progress_requirements": [{"key": "handoff", "credit": 7, "predicate": {"kind": "requested_job_handoff"}}],
        "completion_keys": ["handoff"], "initial_context": {"revision": 0, "cwd": str(workspace), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
    return {"version": "execution_launch_assignment_v1", "requests": {"here": practical},
        "immutable_input_versions": [], "constraints": {"allowed_resource_ids": ["here"],
            "allowed_kinds": ["local"], "allocation": deepcopy(POLICY)}}


def alignment_descriptor(store, context, arguments):
    """Describe the existing own native alignment; create no records or result."""
    key = f"{context.run_id}:{context.episode_id}:0"
    row = store.db.execute("SELECT action,result FROM runtime_actions WHERE run_id=? AND episode_id=? AND decision_index=0",
        (context.run_id, context.episode_id)).fetchone()
    assert json.loads(row["action"]) == action("sequence.align", arguments)["selection"]
    outcome = json.loads(row["result"])
    assert outcome["status"] == "completed", outcome
    body = outcome["result"]
    source = store.get(body["source_ref"])
    descriptor = {"version": "structure_alignment_descriptor_v1", "observation_ref": body["observation_ref"],
        "source_ref": source["id"], "original_operation_key": key,
        "query_reference_ref": arguments["query_ref"], "reference_reference_ref": arguments["reference_ref"],
        "native_file": file_identity(store, source["artifact_ref"], "biopython_pairwise_json"),
        "grading_file": file_identity(store, source["auxiliary_artifact_refs"][0], "tool_grading_artifact_v1"),
        "molecule": "protein", "mode": arguments["mode"], "traceback_selection": "explicit_retained",
        "producer_traceback_selection": "first_native_optimal_returned", "optimal_alternative_count": None}
    return descriptor, outcome


def workflow_case(directory, *, same_file=False, orientation="fixed_is_query", saved=True, before_saved=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / "state")
    store.create_problem(raw_sequence="AGST", molecule="protein")
    scope = store.validate_scope()
    fixed = A.pdb_bytes(coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], chain="A")
    moving = A.pdb_bytes(coordinates=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [2, 0, 1]], chain="B")
    if same_file:
        fixed = moving = fixed.removesuffix(b"END\n") + b"TER\n" + b"\n".join(moving.splitlines()[1:]) + b"\n"
    requests, initial_refs = [], []
    for i, raw in enumerate((fixed, moving)):
        ref = store.artifact(raw, "chemical/x-pdb")
        initial_refs.append(ref)
        identity = file_identity(store, ref, "pdb_3x_text")
        parsed = parse_pdb_structure(raw, file_identity=identity)
        requests.append({"version": "protein_structure_extract_request_v1", "operation": "extract_sequence",
            "selection": A.selection(parsed, role="single", chain_index=i if same_file else 0), "supplied_metadata_files": []})
    initial_refs = list(dict.fromkeys(initial_refs))
    workspace = directory / "workspace"
    workspace.mkdir()
    software = F.software()
    resources = {"here": {"kind": "local", "workspace": str(workspace), "policy": deepcopy(POLICY),
        "native_protein_structure": [{"operation": operation, "scientific_mode": mode, "software": deepcopy(software)}
            for operation, mode in (("extract_sequence", None), ("compare", "fit_then_evaluate_ca"))]}}
    jobs = [selected_job(store, request, software) for request in requests]
    launches = [launch_assignment(job, workspace, label) for job, label in zip(jobs, ("extract-fixed", "extract-moving"))]
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / "run", tool_registry=tools)
    binding = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
        tool_catalog=tools.catalog(), child_roles=("scientific_process", "launch", "results"),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / "run/scientific-process-library")
    extraction_form = result_form("sequences", "failures", completed=True)
    comparison_form = result_form("summary", "saved", "failures", completed=True)
    parent_form = result_form("summary")
    early_form = validate_closed_schema({"type": "object", "properties": {
        "credit": {"type": "number", "x-source": "credit"}}, "required": ["credit"], "additionalProperties": False})

    def science_assignment(label, names, refs):
        return {"selection": {"version": "scientific_process_selection_v3", "evidence_axis": library.reference("A101"),
            "thought_pattern": library.reference("P01"), "child_tool_info": [{"name": name, "resources": "local"} for name in names]},
            "evidence_refs": list(refs), "constraints": {"no_external_acquisition": True, "allocation": deepcopy(POLICY)},
            "context": {"fixture_phase": label, "supplied_sequence": "AGST", "molecule": "protein",
                "supplied_structure_requests": deepcopy(requests),
                "candidate_annotation_required": False}}

    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            if len(path) == 1:
                horizon = 2
            elif len(path) == 2:
                horizon = 1 if path[-1][1] == "child_0" else 5
            else:
                horizon = 4 if saved else 3
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {"fixture": "caller_selected_scientific_test_horizon_only"})
        return YieldController(str(path), initial, 0, YieldParameters(100, 50),
            estimate_with_context=estimate if path[-1][0] in {"annotation", "scientific_process"} else None)

    class Choices:
        def __init__(self):
            self.calls, self.turns, self.descriptors, self.plans, self.handoffs = [], {}, [], [], []
            self.alignment = self.alignment_outcome = self.comparison_job = self.original_return = None

        async def completed_handoff(self, current):
            handoff, = current["child_reports"][-1]["references"]
            assert current["child_reports"][-1]["completed"]
            target = owner.job_progress_provider.targets.read_target(handoff, scope)
            # Test-driver synchronization of the already selected native unit;
            # it is not an episode monitor, a production itinerary or credit.
            outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                native_lifecycle.NativeJobHandle(Path(target["execution_id"])))
            assert outcome.returncode == 0, outcome
            plan = local_protein_structure_plan(target["assignment"], target["execution_id"])
            self.handoffs.append(handoff)
            self.plans.append(plan)
            return handoff

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({"episode_id": episode_id, "role": role, "context": deepcopy(current)})
            (directory / f"decision-{len(self.calls) - 1}.json").write_text(json.dumps(self.calls[-1], indent=2) + "\n")
            assert not current.get("feedback"), current.get("feedback")
            self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
            turn = self.turns[episode_id]
            if "practical_assignment" in current:
                assert turn == 1
                assert current["practical_assignment"]["constraints"]["allocation"] == POLICY
                answer = action("practical.job.start")
            elif current.get("execution_assignment", {}).get("version") == "execution_launch_assignment_v1":
                assert turn == 1
                original = current["execution_assignment"]["requests"]["here"]
                answer = commission("launch_local", original, scope, HANDOFF_FORM,
                    objective="Execute this exact native protein job on the caller-selected local resource.")
            elif current.get("execution_assignment", {}).get("version") == RESULTS_VERSION:
                assert turn == 1
                answer = action("execution.results.collect")
            elif "scientific_process" not in current:
                label = "earlier" if turn == 1 else "coordinate"
                names = ["sequence.inspect"] if turn == 1 else ["extract_protein_structure_sequence", "compare_protein_structures"]
                answer = commission("scientific_process", science_assignment(label, names, scope["subject_refs"]),
                    scope, early_form if turn == 1 else parent_form,
                    objective="Inspect the supplied sequence." if turn == 1 else
                        "Extract both supplied structure sequences, then investigate their alignment and selected CA comparison.")
            else:
                phase = current["scientific_process"]["assignment"]["context"]["fixture_phase"]
                if phase == "earlier":
                    assert turn == 1
                    answer = action("sequence.inspect", {"subject_ref": scope["subject_refs"][0]})
                elif phase == "coordinate":
                    if turn in (1, 3):
                        if turn == 3:
                            returned = current["child_reports"][-1]
                            assert returned["completed"] and not returned["failures"], returned
                            self.descriptors.append(returned["sequences"][0])
                        answer = commission("launch", launches[0 if turn == 1 else 1], scope, HANDOFF_FORM,
                            objective="Extract the selected supplied structure sequence through local native execution.")
                    elif turn in (2, 4):
                        handoff = await self.completed_handoff(current)
                        answer = commission("results", {"version": RESULTS_VERSION, "handoff_ref": handoff,
                            "selector": selector(sequence=True)}, scope, extraction_form,
                            objective="Acquire the sealed original extraction and return its unchanged sequence descriptor.")
                    else:
                        assert turn == 5
                        returned = current["child_reports"][-1]
                        assert returned["completed"] and not returned["failures"], returned
                        self.descriptors.append(returned["sequences"][0])
                        assignment = science_assignment("align_compare", ["sequence.align", "compare_protein_structures"], scope["subject_refs"])
                        assignment["context"]["received_structure_sequences"] = deepcopy(self.descriptors)
                        answer = commission("scientific_process", assignment,
                            scope, parent_form, objective="Align the two actually received structure sequences, fit the first three CA pairs, and evaluate the held-out fourth pair.")
                else:
                    assert phase == "align_compare"
                    fixed_descriptor, moving_descriptor = self.descriptors
                    query, reference = (fixed_descriptor, moving_descriptor) if orientation == "fixed_is_query" else (moving_descriptor, fixed_descriptor)
                    args = {"query_ref": query["reference_ref"], "reference_ref": reference["reference_ref"], "molecule": "protein", "mode": "global"}
                    if turn == 1:
                        answer = action("sequence.align", args)
                    elif turn == 2:
                        context = owner.native_protein_structure_returns.context(episode_id)
                        self.alignment, self.alignment_outcome = alignment_descriptor(store, context, args)
                        parameters = A.fit_parameters()
                        parameters["fit_selection"] = {"kind": "explicit", "members": [
                            {"kind": "correspondence_id", "correspondence_id": "column_" + str(i)} for i in range(3)]}
                        parameters["evaluation_selection"] = {"kind": "explicit", "members": [
                            {"kind": "correspondence_id", "correspondence_id": "column_3"}]}
                        request = {"version": "protein_structure_compare_request_v1", "operation": "compare",
                            "fixed_selection": {**deepcopy(fixed_descriptor["selection"]), "structure_role": "fixed"},
                            "moving_selection": {**deepcopy(moving_descriptor["selection"]), "structure_role": "moving"},
                            "correspondence": {"kind": "retained_alignment", "alignment": deepcopy(self.alignment),
                                "fixed_sequence_descriptor": deepcopy(fixed_descriptor), "moving_sequence_descriptor": deepcopy(moving_descriptor),
                                "orientation": orientation}, "parameters": parameters, "supplied_metadata_files": []}
                        self.comparison_job = selected_job(store, request, software)
                        answer = commission("launch", launch_assignment(self.comparison_job, workspace, "compare-held-out"),
                            scope, HANDOFF_FORM, objective="Compare the explicitly selected residue populations using the retained native alignment.")
                    elif turn == 3:
                        handoff = await self.completed_handoff(current)
                        answer = commission("results", {"version": RESULTS_VERSION, "handoff_ref": handoff,
                            "selector": selector(summary=True, return_saved=True)}, scope, comparison_form,
                            objective="Return only the requested comparison quantities and the saved-sheet descriptor.")
                    else:
                        assert saved and turn == 4
                        self.original_return = deepcopy(current["child_reports"][-1])
                        assert self.original_return["completed"] and not self.original_return["failures"], self.original_return
                        descriptor, = self.original_return["saved"]
                        parameters = deepcopy(self.comparison_job["request"]["parameters"])
                        parameters["evaluation_selection"] = {"kind": "all_mapped_pairs"}
                        parameters["distance_threshold_A"] = 1.5
                        if before_saved is not None:
                            before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                                workspace=workspace, descriptor=descriptor, plans=deepcopy(self.plans),
                                original_return=deepcopy(self.original_return), provider=self))
                        answer = commission("results", {"version": RESULTS_VERSION, "handoff_ref": self.handoffs[-1],
                            "selector": selector(saved=descriptor, parameters=parameters, summary=True, return_saved=True)},
                            scope, comparison_form, objective="Recalculate only the received saved sheet over all four mapped pairs with the explicit new parameters.")
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow = Workflow(store, tools, provider, directory / "run", RUN_ID, controller_factory=controller,
        project_credit=lambda *_args, **_kwargs: 0, annotation_child_roles=("scientific_process",),
        episode_record_receipts=True, initial_known_record_refs=initial_refs,
        episode_binding_descriptors=(binding, *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    owner = flow.episode_bindings.for_role("results")
    root = flow.build("annotation", "root", "Investigate the supplied sequence and two explicit synthetic structure files.", scope)
    async def execute():
        record = await root.run_async(flow.context)
        await root.build_result(record)
        return record
    try:
        record = asyncio.run(execute())
    except BaseException:
        store.close()
        raise
    records = list(walk(json.loads("".join(iter_json(record.as_record())))))
    contexts = {r["episode_id"]: owner.native_protein_structure_returns.context(r["episode_id"]) for r in records}
    by_role = {}
    for row in records:
        by_role.setdefault(contexts[row["episode_id"]].role, []).append(row)
    result_contexts = [contexts[row["episode_id"]] for row in by_role["results"]]
    returned = [json.loads(flow.journal.row("runtime_forms", c.episode_id)["form"]) for c in result_contexts]
    outcomes = [json.loads(flow.journal.row("runtime_actions", c.episode_id, 0)["result"]) for c in result_contexts]
    science_contexts = [contexts[row["episode_id"]] for row in by_role["scientific_process"]]
    forwarded = [json.loads(flow.journal.row("runtime_forms", c.episode_id)["form"]) for c in science_contexts]
    case = SimpleNamespace(store=store, flow=flow, owner=owner, provider=provider, root=root, record=record,
        records=records, contexts=contexts, by_role=by_role, result_contexts=result_contexts, returned=returned,
        outcomes=outcomes, science_contexts=science_contexts, forwarded=forwarded, scope=scope,
        root_context=contexts[record.episode_id], workspace=workspace, resources=resources,
        initial_refs=initial_refs, same_file=same_file, orientation=orientation, saved=saved)
    (directory / "CASE.json").write_text(json.dumps({"scope": "synthetic engineering inputs and scripted scientific choices; actual native execution and Workflow communication",
        "same_file": same_file, "orientation": orientation, "saved": saved, "native_plans": provider.plans,
        "alignment": provider.alignment, "alignment_outcome": provider.alignment_outcome,
        "returned": returned, "forwarded": forwarded,
        "histories": {role: [r["controller_state"] for r in rows] for role, rows in by_role.items()}}, indent=2) + "\n")
    return case
