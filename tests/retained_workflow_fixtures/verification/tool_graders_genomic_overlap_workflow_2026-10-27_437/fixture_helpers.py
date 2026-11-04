"""Fresh synthetic inputs, scripted choices, actual Workflow/native operations.

No helper writes a runtime action, completion, return form, observation or
positive authority. Those are produced only by the production Workflow.
"""
from __future__ import annotations

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
from gene_annotation_episode.genomic_overlap_return_views import (
    PROJECTION_SOURCE, SAVED_SOURCE, FAILURE_SOURCE, genomic_overlap_fact_sources,
)
from gene_annotation_episode.native_genomic_overlap_contracts import (
    POLICY, genomic_overlap_output_files, requested_job_from_genomic_overlap,
)
from gene_annotation_episode.native_genomic_overlap_local import local_genomic_overlap_plan
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

# Reuse the existing provider transport and shared Workflow archive mechanics.
MECHANICS = import_module("verification.tool_graders_protein_structure_workflow_2026-10-27_410.fixture_helpers")
NATIVE = import_module("verification.tool_graders_genomic_overlap_native_driver_2026-10-27_427.fixture_helpers")
action, commission = MECHANICS.action, MECHANICS.commission
provider_value, walk, history = MECHANICS.provider_value, MECHANICS.walk, MECHANICS.history
HANDOFF_FORM = deepcopy(MECHANICS.HANDOFF_FORM)
ROOT = Path(__file__).resolve().parents[2]
PUBLICATION = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
GOAL = "Compare all pairs of the three supplied synthetic genomic interval sets with their declared reference and retain exact numerical qualifications."
RUN_ID = "genomic-overlap-workflow437"
FIELDS = ["unfiltered.native_pair_count", "unfiltered.pairwise_overlap_bp_sum",
    "unfiltered.intersection_union_bp", "unfiltered.combined_union_bp", "unfiltered.jaccard_bp",
    "selected.selected_pair_count", "selected.selected_pairwise_bp_sum"]
SOURCES = {"overlap": PROJECTION_SOURCE, "saved": SAVED_SOURCE, "failures": FAILURE_SOURCE}
DATA = [b"chr1\t0\t10\nchr1\t5\t15\n", b"chr1\t7\t12\n", b"chr1\t10\t20\n"]
TABLES = ("runtime_episodes", "runtime_actions", "runtime_observations", "runtime_forms",
    "runtime_report_attempts", "runtime_record_receipts")


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def result_form(*fields, completed=False):
    definitions = genomic_overlap_fact_sources()
    properties = {field: deepcopy(definitions[SOURCES[field]]["report_schema"]) for field in fields}
    if completed:
        properties["completed"] = {"type": "boolean", "x-source": "execution_completed"}
    return validate_closed_schema({"type": "object", "properties": properties,
        "required": list(properties), "additionalProperties": False})


def selector(*, saved=None, minimum=1):
    return {"version": "genomic_overlap_result_selector_v1",
        "mode": "native_result" if saved is None else "saved_sheet_recalculation",
        "comparison_keys": ["AB", "AC", "BC"], "saved_sheet_file": deepcopy(saved),
        "parameters": {"version": "genomic_overlap_calculation_parameters_v1", "minimum_overlap_bp": minimum,
            "minimum_a_fraction": {"numerator": 0, "denominator": 1},
            "minimum_b_fraction": {"numerator": 0, "denominator": 1}},
        "projection": {"kind": "pair_metrics", "offset": 0, "limit": 3,
            "measurement_fields": list(FIELDS), "occurrence_keys": []}}


def source(store, raw, label):
    artifact = store.artifact(raw)
    return store.put("source", {"provider": "fixture.genomic_overlap437." + label,
        "accession": None, "uri": None, "artifact_ref": artifact, "text_ref": None,
        "request_ref": None, "version": None, "retrieved_at": None}, origin="caller")


def identity(store, artifact, format):
    metadata = store.get(artifact)
    return {"artifact_ref": artifact, "sha256": metadata["sha256"],
        "size_bytes": metadata["size"], "format": format}


def artifact_path(store, file):
    return store.path / "artifacts" / file["sha256"][:2] / file["sha256"]


def launch_assignment(job, workspace):
    practical = {"version": "practical_assignment_v1", "assignment_id": "selected-overlap437",
        "resource_id": "here", "resource_kind": "local", "workspace": str(workspace),
        "endpoint": "usable_handoff", "requested_job": requested_job_from_genomic_overlap(job),
        "progress_requirements": [{"key": "handoff", "credit": 7,
            "predicate": {"kind": "requested_job_handoff"}}], "completion_keys": ["handoff"],
        "initial_context": {"revision": 0, "cwd": str(workspace), "environment": {}},
        "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
    return {"version": "execution_launch_assignment_v1", "requests": {"here": practical},
        "immutable_input_versions": [], "constraints": {"allowed_resource_ids": ["here"],
            "allowed_kinds": ["local"], "allocation": deepcopy(POLICY)}}


def rows(store, table):
    return sorted((dict(row) for row in store.db.execute("SELECT * FROM " + table)), key=canonical)


def controller_factory(*, saved, failure):
    def controller(path, initial):
        def estimate(raw, parameters, contexts):
            horizon = 1 if path[-1][0] == "annotation" else 3 if saved else 2
            return YieldEstimate(len(raw), NumericBand.exact(0 if len(raw) >= horizon else 1), parameters,
                {"fixture": "caller_selected_scientific_test_horizon_only"})
        scientific = path[-1][0] in {"annotation", "scientific_process"}
        # The incomplete cases use the ordinary production practical estimator
        # with an explicit fit minimum/cost. Its provider selects a real status
        # action if the failed delivery remains open; there is no endpoint stub.
        return YieldController(str(path), initial, 0 if scientific or not failure else 1e9,
            YieldParameters(100, 50) if scientific or not failure else YieldParameters(2, 1),
            estimate_with_context=estimate if scientific else None)
    return controller


def assemble(store, directory, provider, configuration):
    factory = ExecutionServiceFactory.from_record(configuration["factory"])
    tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / "run", tool_registry=tools)
    flow = Workflow(store, tools, provider, directory / "run", RUN_ID,
        controller_factory=controller_factory(saved=configuration["saved"], failure=configuration["failure"]),
        project_credit=lambda *_args, **_kwargs: 0, annotation_child_roles=("scientific_process",),
        episode_record_receipts=True, initial_known_record_refs=configuration["initial_refs"],
        episode_binding_descriptors=(configuration["scientific_binding"], *application.episode_binding_descriptors),
        role_credit_bindings=application.role_credit_bindings, job_progress_provider=application.job_progress_provider)
    return flow, tools


async def run_root(flow, configuration):
    root = flow.build("annotation", "root", configuration["goal"], configuration["scope"])
    record = await root.run_async(flow.context)
    await root.build_result(record)
    return root, record, json.loads("".join(iter_json(record.as_record())))


def worker_runs(directory):
    """Inspect every real434 prepared capture by its own retained plan, not order."""
    runs = []
    for path in sorted((directory / "run").rglob("prepared.json")):
        captured = json.loads(path.read_bytes())
        if captured.get("version") != "genomic_overlap_worker_capture_v1":
            continue
        plan = json.loads((path.parent / "plan.json").read_bytes())
        runs.append({"directory": str(path.parent), "plan": plan, "capture": captured})
    return runs


def workflow_case(directory, *, failure=None, before_saved=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    store = Store(directory / "state")
    store.create_problem(raw_sequence="ACGTACGT", molecule="dna")
    scope = store.validate_scope()
    data = deepcopy(DATA)
    if failure == "invalid_c":
        data[2] = b"chr1\t10\t10\n"
    reference_source = source(store, canonical({"assembly": "synthetic-overlap437.1",
        "contigs": [{"name": "chr1", "length_bp": 100}]}).encode(), "reference")
    reference = {"assembly_accession_version": "synthetic-overlap437.1", "assembly_label": None,
        "source_refs": [reference_source["id"]], "contigs": [{"chromosome": "chr1", "length_bp": 100,
            "sequence_accession_version": None, "sequence_sha256": None,
            "source_refs": [reference_source["id"]]}], "sequence_dictionary": None}
    initial_refs = [reference_source["id"], reference_source["artifact_ref"]]
    specs, inputs = [], []
    for key, raw in zip("ABC", data):
        supplied = source(store, raw, key)
        file = identity(store, supplied["artifact_ref"], "bed_outer_span_v1")
        specs.append({"set_key": key, "display_label": "synthetic set " + key,
            "source": {"kind": "bed_artifact", "source_ref": supplied["id"], "file": file},
            "reference": deepcopy(reference), "format": "bed_outer_span_v1"})
        inputs.append({"set_key": key, "path": str(artifact_path(store, file))})
        initial_refs.extend((supplied["id"], supplied["artifact_ref"]))
    request = {"version": "genomic_overlap_request_v1", "operation": "analyze_genomic_region_overlap",
        "mode": "unstranded_outer_span", "region_sets": specs, "comparisons": [
            {"comparison_key": a + b, "ordinal": i, "a_set_key": a, "b_set_key": b}
            for i, (a, b) in enumerate((("A", "B"), ("A", "C"), ("B", "C")))], "output_prefix": "overlap"}
    workspace = directory / "workspace"
    workspace.mkdir()
    software = NATIVE.software()
    job = {"version": "native_genomic_overlap_job_v1", "program": "bedtools_intersect_all_pairs",
        "request": request, "software": software, "inputs": inputs,
        "outputs": genomic_overlap_output_files(request), "environment": {"LC_ALL": "C"}}
    launch = launch_assignment(job, workspace)
    resources = {"here": {"kind": "local", "workspace": str(workspace), "policy": deepcopy(POLICY),
        "native_genomic_overlap": [{"operation": request["operation"], "mode": request["mode"],
            "software": deepcopy(software)}]}}
    factory = ExecutionServiceFactory(resources, {}, 3, 2, 1, log_window_bytes=128)
    preliminary_tools = ToolRegistry(store, job_limits=deepcopy(POLICY))
    application = factory(store, run_id=RUN_ID, directory=directory / "run", tool_registry=preliminary_tools)
    binding = prepare_scientific_binding(run_directory=directory / "run", source_directory=PUBLICATION,
        tool_catalog=preliminary_tools.catalog(), child_roles=("scientific_process", "launch", "results"),
        resource_catalogs=application.resource_tool_catalogs)
    library = ScientificProcessLibrary(directory / "run/scientific-process-library")
    scientific_assignment = {"selection": {"version": "scientific_process_selection_v3",
        "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
        "child_tool_info": [{"name": "analyze_genomic_region_overlap", "resources": "local"}]},
        "evidence_refs": scope["subject_refs"],
        "constraints": {"no_external_acquisition": True, "allocation": deepcopy(POLICY)},
        "context": {"supplied_sequence": "ACGTACGT", "molecule": "dna",
            "supplied_genomic_overlap_request": deepcopy(request), "candidate_annotation_required": False}}
    saved = failure is None
    configuration = {"factory": factory.as_record(), "scientific_binding": binding, "goal": GOAL,
        "scope": scope, "initial_refs": initial_refs, "saved": saved, "failure": failure}
    write(directory / "fixture-configuration.json", configuration)
    full_form = result_form("overlap", "saved", "failures", completed=True)
    parent_form = result_form("overlap") if saved else result_form("overlap", "failures")

    class Choices:
        def __init__(self):
            self.calls, self.turns = [], {}
            self.plan = self.target = self.handoff = self.original_return = None
            self.native_bytes = {}
            self.loss = None

        async def complete(self, episode_id, role, instructions, current, schema):
            self.calls.append({"episode_id": episode_id, "role": role, "instructions": instructions,
                "context": deepcopy(current)})
            write(directory / f"decision-{len(self.calls) - 1}.json", self.calls[-1])
            assert not current.get("feedback"), current.get("feedback")
            self.turns[episode_id] = self.turns.get(episode_id, 0) + 1
            turn = self.turns[episode_id]
            if "practical_assignment" in current:
                assert current["practical_assignment"]["constraints"]["allocation"] == POLICY
                if turn == 1:
                    answer = action("practical.job.start")
                else:
                    assert failure and turn == 2
                    answer = action("practical.job.status")
            elif current.get("execution_assignment", {}).get("version") == "execution_launch_assignment_v1":
                if turn == 1:
                    answer = commission("launch_local", current["execution_assignment"]["requests"]["here"],
                        scope, HANDOFF_FORM, objective="Execute the exact supplied interval request on the configured local resource.")
                else:
                    assert failure and turn == 2
                    answer = action("execution.capabilities")
            elif current.get("execution_assignment", {}).get("version") == RESULTS_VERSION:
                assert turn == 1 or failure and turn == 2
                answer = action("execution.results.collect" if turn == 1 else "execution.results.status")
            elif "scientific_process" not in current:
                assert turn == 1
                answer = commission("scientific_process", scientific_assignment, scope, parent_form, objective=GOAL)
            elif turn == 1:
                answer = commission("launch", launch, scope, HANDOFF_FORM,
                    objective="Execute every frozen interval-set comparison with its supplied reference and allocation.")
            elif turn == 2:
                # A genuinely failed launch can return both its start and a
                # later explicitly selected status receipt. Select the actual
                # original start by its recorded operation, never list order.
                receipt_reader = PracticalReceiptInformation(store, RUN_ID)
                handoff, = [reference for reference in current["child_reports"][-1]["references"]
                    if receipt_reader.read(reference, scope)["receipt"]["tool_name"] == "practical.job.start"]
                self.handoff = handoff
                self.target = owner.job_progress_provider.targets.read_target(handoff, scope)
                outcome = await asyncio.to_thread(native_lifecycle.wait_job,
                    native_lifecycle.NativeJobHandle(Path(self.target["execution_id"])))
                assert outcome.returncode == (1 if failure == "invalid_c" else 0), outcome
                self.plan = local_genomic_overlap_plan(self.target["assignment"], self.target["execution_id"])
                # Preserve actual output evidence before the explicitly injected
                # post-execution file loss. These copies are not worker operands.
                evidence = directory / "native-evidence"
                evidence.mkdir()
                for spec in self.plan["requested_job"]["native_genomic_overlap"]["outputs"]:
                    path = Path(self.plan["attempt_directory"]) / spec["relative_path"]
                    if path.is_file():
                        raw = path.read_bytes()
                        self.native_bytes[spec["file_key"]] = raw
                        retained = evidence / spec["relative_path"]
                        retained.parent.mkdir(parents=True, exist_ok=True)
                        retained.write_bytes(raw)
                write(directory / "original-native-plan.json", self.plan)
                write(directory / "native-lifecycle.json", {"returncode": outcome.returncode, "metadata": outcome.metadata})
                if failure == "missing_ac_stdout":
                    spec, = [r for r in job["outputs"] if r["file_key"] == "p1:stdout"]
                    removed = Path(self.plan["attempt_directory"]) / spec["relative_path"]
                    removed.unlink()
                    self.loss = {"kind": "actual_post_execution_output_loss", "path": str(removed),
                        "preserved_control_evidence": "original sealed batch and pair manifests", "comparison_key": "AC"}
                    write(directory / "injected-loss.json", self.loss)
                answer = commission("results", {"version": RESULTS_VERSION, "handoff_ref": handoff,
                    "selector": selector()}, scope, full_form,
                    objective="Return exactly the requested interval measurements, saved sheet identity and located failures.")
            else:
                assert saved and turn == 3
                self.original_return = deepcopy(current["child_reports"][-1])
                assert self.original_return["completed"] and not self.original_return["failures"], self.original_return
                sheet, = self.original_return["saved"]
                if before_saved is not None:
                    before_saved(SimpleNamespace(store=store, owner=owner, flow=flow, directory=directory,
                        workspace=workspace, sheet=sheet, original_return=self.original_return,
                        provider=self, science_context=owner.native_genomic_overlap_returns.context(episode_id)))
                answer = commission("results", {"version": RESULTS_VERSION, "handoff_ref": self.handoff,
                    "selector": selector(saved=sheet, minimum=4)}, scope, full_form,
                    objective="Recalculate the explicitly received saved sheet with minimum_overlap_bp=4; retain the original unfiltered geometry.")
            answer = provider_value(plain(answer), plain(schema))
            Draft202012Validator(plain(schema)).validate(answer)
            return answer

        async def release(self, episode_id):
            pass

    provider = Choices()
    flow, tools = assemble(store, directory, provider, configuration)
    owner = flow.episode_bindings.for_role("results")
    try:
        root, record, archive = asyncio.run(run_root(flow, configuration))
        records = list(walk(archive))
        contexts = {row["episode_id"]: owner.native_genomic_overlap_returns.context(row["episode_id"]) for row in records}
        by_role = {}
        for row in records:
            by_role.setdefault(contexts[row["episode_id"]].role, []).append(row)
        result_contexts = [contexts[row["episode_id"]] for row in by_role["results"]]
        returned = [json.loads(flow.journal.row("runtime_forms", c.episode_id)["form"]) for c in result_contexts]
        outcomes = [json.loads(flow.journal.row("runtime_actions", c.episode_id, 0)["result"]) for c in result_contexts]
        scientific_context, = [contexts[row["episode_id"]] for row in by_role["scientific_process"]]
        forwarded = json.loads(flow.journal.row("runtime_forms", scientific_context.episode_id)["form"])
        case = SimpleNamespace(store=store, directory=directory, flow=flow, tools=tools, owner=owner,
            provider=provider, configuration=configuration, root=root, record=record, archive=archive,
            records=records, contexts=contexts, by_role=by_role, result_contexts=result_contexts,
            returned=returned, outcomes=outcomes, scientific_context=scientific_context,
            root_context=contexts[record.episode_id], forwarded=forwarded, parent_form=parent_form,
            full_form=full_form, scope=scope, workspace=workspace, job=job, failure=failure)
        write(directory / "CASE.json", {"scope": "scripted choices and synthetic intervals; actual Workflow and local native execution",
            "failure": failure, "original_plan": provider.plan, "returned": returned, "forwarded": forwarded,
            "histories": {role: [r["controller_state"] for r in group] for role, group in by_role.items()},
            "archive": archive})
        return case
    except BaseException:
        store.close()
        raise
