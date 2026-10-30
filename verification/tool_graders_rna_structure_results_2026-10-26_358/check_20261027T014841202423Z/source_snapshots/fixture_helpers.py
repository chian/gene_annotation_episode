"""Synthetic original producer bundles, real Store/Journal/action/form adapters.

No RNA import, native scientific process or producer driver is executed here.
The target reader is an explicitly supplied test port; full dispatch is root's
separate integration responsibility. Local reservations use the real producer.
"""
from copy import deepcopy
from dataclasses import replace
import asyncio
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys

from method_loop.episode import EpisodeGoal, EpisodeRequest
from method_loop.identities import EpisodeRef

from gene_annotation_episode.communication import form_with_facts, plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest, validate_target
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.native_rna_structure_contracts import (POLICY, INPUT_NAMES,
    compile_rna_structure_job, requested_job_from_rna_structure, realized_environment,
    validate_rna_structure_bundle)
from gene_annotation_episode.native_rna_structure_local import prepare_local_rna_structure, local_rna_structure_plan
from gene_annotation_episode.native_rna_structure_results import NativeRNAStructureResults
from gene_annotation_episode.native_rna_structure_returns import NativeRNAStructureReturns
from gene_annotation_episode.practical_execution_state import _immutable
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.rna_structure_contracts import issue
from gene_annotation_episode.rna_structure_result_views import (FAMILY_SOURCES, REFERENCE_SOURCE,
    SAVED_SOURCE, rna_structure_fact_sources)
from gene_annotation_episode.runtime import Record, TypedReportContract

REPO = Path(__file__).resolve().parents[2]
CORE_PATH = REPO / "verification/tool_graders_rna_structure_core_2026-10-26_354/fixture_helpers.py"
spec = importlib.util.spec_from_file_location("rna358_synthetic_scientific_fixtures", CORE_PATH)
CORE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CORE)
PARAMETERS = deepcopy(CORE.PARAMETERS)


def encoded(value):
    return (canonical(value) + "\n").encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def selector(family="summary", metrics=None, rows=None):
    return {"version": "native_rna_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "rows": rows or {"offset": 0, "limit": 50},
            "metrics": metrics if metrics is not None else [] if family == "failure" else ["pair_count", "paired_fraction", "long_stem_fraction", "accepted_pair_fraction"]}}


def schema_for(*sources):
    descriptors = rna_structure_fact_sources()
    fields = {"value_" + str(i): deepcopy(descriptors[source]["report_schema"]) for i, source in enumerate(sources)}
    return {"type": "object", "properties": fields, "required": list(fields), "additionalProperties": False}


class SyntheticTargets:
    def __init__(self, fixture):
        self.fixture, self.observations = fixture, []

    def read_target(self, reference, scope):
        assert reference == self.fixture.handoff
        self.fixture.store.validate_scope(self.fixture.target["scope"], parent_scope=plain(scope))
        return deepcopy(self.fixture.target)

    def observe_target(self, target, *, operation_key):
        assert target == self.fixture.target
        self.observations.append(operation_key)
        return {"observed_at": "2026-10-26T00:00:03+00:00", "state": "failed" if self.fixture.failure else "completed",
            "returncode": 1 if self.fixture.failure else 0, "failure_code": "synthetic_native_failure" if self.fixture.failure else None,
            "result_available": True, "measurements": [], "outputs": [], "logs": [], "provenance_refs": [],
            "native": {"fixture": "synthetic_supplied_observation"}}


class Fixture:
    def __init__(self, store, root, *, request=None, prediction=False, failure=False, molecule="rna"):
        self.store, self.root_path, self.run_id, self.failure = store, Path(root), "rna358-synthetic-run", failure
        self.root_path.mkdir(parents=True, exist_ok=True)
        self.journal = Journal(store, self.run_id)
        self.receipts = EpisodeReceipts(store, self.run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="GGGAAACCC", molecule=molecule)["subject_refs"]}
        self.root = self.context((("annotation", "root"),), {}, None)
        subject = store.get(self.scope["subject_refs"][0])
        self.receipts.receive(self.root.episode_id, [subject["id"], subject["sequence_ref"]], kind="initial")
        self.request = deepcopy(request(self) if callable(request) else request or (CORE.prediction_input() if prediction else CORE.feature_input()))
        if failure and not prediction:
            self.request["energy_mode"] = "viennarna_evaluate"
        input_path = self.root_path / "supplied-input.json"
        input_path.write_bytes(encoded(self.request))
        input_ref = store.artifact(input_path.read_bytes(), "application/json")
        self.receipts.receive(self.root.episode_id, [input_ref], kind="initial")
        selected_model = CORE.model_spec() if prediction or self.request.get("energy_mode") == "viennarna_evaluate" else None
        software = {"python_executable": sys.executable, "python_sha256": sha(Path(sys.executable).read_bytes()),
            "python_version": None, "worker_module": "gene_annotation_episode.native_rna_structure_worker",
            "worker_source_sha256": sha((REPO / "gene_annotation_episode/native_rna_structure_worker.py").read_bytes()),
            "viennarna_distribution_version": None, "rna_module_sha256": None, "rna_extension_sha256": None}
        outputs = [{"role": "native_result", "format": "rna_native_record_json_v1", "relative_path": "native-result.json"},
            {"role": "stdout", "format": "text", "relative_path": "stdout.txt"},
            {"role": "stderr", "format": "text", "relative_path": "stderr.txt"}]
        if selected_model is not None:
            outputs.extend([{"role": "model", "format": "vienna_model_json_v1", "relative_path": "model.json"},
                {"role": "effective_parameters", "format": "viennarna_parameter_file", "relative_path": "effective-parameters.par"}])
        self.job = {"version": "native_rna_structure_job_v1", "program": "rna_structure_python",
            "operation": "predict_rna_secondary_structure" if prediction else "analyze_rna_secondary_structure_features",
            "mode": "mfe_prediction" if prediction else "supplied_features", "record_key": self.request["record_key"],
            "software": software, "model": selected_model, "operands": [{"role": "input", "path": str(input_path),
                "format": "rna_input_json_v1", "sha256": sha(input_path.read_bytes()), "size_bytes": input_path.stat().st_size,
                "artifact_ref": input_ref}], "outputs": outputs, "environment": {"PYTHONPATH": str(REPO)},
            "grading_parameters": deepcopy(PARAMETERS)}
        workspace = self.root_path / "workspace"
        workspace.mkdir()
        self.assignment = {"version": "practical_assignment_v1", "assignment_id": "explicitly-synthetic-rna-attempt",
            "resource_kind": "local", "resource_id": "local-rna", "workspace": str(workspace),
            "requested_job": requested_job_from_rna_structure(self.job), "endpoint": "usable_handoff",
            "progress_requirements": [{"key": "handoff", "credit": 1, "predicate": {"kind": "requested_job_handoff"}}],
            "completion_keys": ["handoff"], "initial_context": {"revision": 0, "cwd": str(workspace), "environment": {}},
            "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
        # A distinct synthetic producer root supplies actual practical receipt
        # authority without claiming the separate selected-tool launch route.
        producer = self.context((("launch_local", "synthetic_producer"),), self.assignment, None)
        producer_episode = producer.episode_id
        operation = f"{self.run_id}:{producer_episode}:0"
        self.native_root = workspace / ".episode-operations" / digest({"run": self.run_id, "episode": producer_episode}) / digest(operation)
        state = SimpleNamespace(run_id=self.run_id, episode_id=producer_episode, assignment=self.assignment)
        handle = prepare_local_rna_structure(state, operation, root=self.native_root, policy=LocalJobPolicy(**POLICY))
        self.plan = local_rna_structure_plan(self.assignment, str(handle.path))
        self.attempt = Path(self.plan["attempt_directory"])
        self.attempt.mkdir()
        native = CORE.native_record(self.request, prediction_structure="(((...)))" if prediction else None,
            energy=None if failure or selected_model is None else -1.25,
            native_failure="rna_native_dependency_missing" if failure else None)
        if native["model"] is not None:
            raw_parameters = b"synthetic parameters, never loaded\n"
            native["model"]["parameter_artifact"].update(sha256=sha(raw_parameters), size_bytes=len(raw_parameters))
        contents = {"input": encoded(self.request), "native_result": encoded(native),
            "stdout": b"Explicitly synthetic supplied producer output.\n", "stderr": b""}
        if selected_model is not None and not failure:
            contents["model"] = encoded(native["model"])
            contents["effective_parameters"] = b"synthetic parameters, never loaded\n"
        failures = deepcopy(native["issues"])
        files = []
        declarations = [{"kind": "input", "role": row["role"], "format": row["format"], "relative_path": INPUT_NAMES[row["role"]]}
            for row in self.job["operands"]] + [{"kind": "output", **row} for row in outputs]
        for row in declarations:
            raw = contents.get(row["role"])
            if raw is None:
                files.append({**row, "state": "absent", "sha256": None, "size_bytes": None})
                failures.append(issue("rna_native_dependency_missing", stage="native", record_key=self.request["record_key"], artifact_role=row["role"]))
            else:
                (self.attempt / row["relative_path"]).write_bytes(raw)
                files.append({**row, "state": "present", "sha256": sha(raw), "size_bytes": len(raw)})
        compiled = compile_rna_structure_job(self.job, input_paths={"input": str(self.attempt / "input.json")}, output_directory=str(self.attempt))
        self.bundle = {"version": "native_rna_structure_bundle_v1", "identity": self.plan["identity"],
            "requested_job": self.plan["requested_job"], **{key: self.job[key] for key in ("program", "operation", "mode", "record_key", "software")},
            "realized_argv": compiled["argv"], "environment": realized_environment(self.job, str(self.attempt)),
            "files": files, "returncode": 1 if failure else 0, "native_status": "partial" if failures else "complete",
            "failures": failures, "started_at": "2026-10-26T00:00:00+00:00", "finished_at": "2026-10-26T00:00:02+00:00", "sealed": True}
        validate_rna_structure_bundle(self.bundle, plan=self.plan)
        _immutable(self.attempt / "bundle.json", self.bundle)
        practical_action = {"kind": "tool", "tool": "practical.job.status", "arguments": {}}
        # Status is a later receipt for the same original execution identity.
        status_key = f"{self.run_id}:{producer_episode}:1"
        self.journal.save("runtime_actions", {"episode_id": producer_episode, "decision_index": 1,
            "action": canonical(practical_action), "result": None, "credit": None})
        outcome = {"facts": {"requested_job": {"argv": self.assignment["requested_job"]["argv"],
            "environment": self.assignment["requested_job"]["environment"], "returncode": 1 if failure else 0,
            "execution_id": str(handle.path), "requested_job_sha256": digest(self.assignment["requested_job"]),
            "resource_kind": "local", "status": "failed" if failure else "completed", "output_paths": [],
            "handoff": {"execution_id": str(handle.path), "monitor_operation": "practical.job.status", "results_operation": "practical.job.collect"}}},
            "native_outcome": {"fixture": "explicitly_synthetic_terminal_native_data"}}
        practical = {"version": "practical_action_receipt_v1", "run_id": self.run_id, "episode_id": producer_episode,
            "assignment_sha256": digest(self.assignment), "operation_key": status_key, "tool_name": "practical.job.status", "arguments": {},
            "context_before": self.assignment["initial_context"], "context_after": self.assignment["initial_context"], "outcome": outcome,
            "validations": assess_validations(self.assignment, outcome, self.assignment["initial_context"],
                checked_at="2026-10-26T00:00:02+00:00", tool_name="practical.job.status"),
            "started_at": "2026-10-26T00:00:02+00:00", "finished_at": "2026-10-26T00:00:02+00:00"}
        self.producer, self.practical_receipt = producer, deepcopy(practical)
        self.handoff = PracticalReceiptInformation(store, self.run_id).publish(producer, practical)
        self.journal.save("runtime_actions", {"episode_id": producer_episode, "decision_index": 1,
            "action": canonical(practical_action), "result": canonical({"status": "completed", "record_refs": [self.handoff], "result": practical}), "credit": 0})
        self.receipts.receive(self.root.episode_id, [self.handoff], kind="initial")
        self.target = validate_target({"version": "execution_target_v1", "handle": self.handoff, "run_id": self.run_id,
            "resource_id": "local-rna", "resource_kind": "local", "execution_id": str(handle.path),
            "request_sha256": digest(self.assignment["requested_job"]), "origin_episode_id": producer_episode,
            "assignment": self.assignment, "scope": deepcopy(self.scope)})
        # Actual host methods are used; only producer observation is supplied.
        self.owner = object.__new__(ExecutionEpisodes)
        self.owner.store, self.owner.run_id, self.owner.directory = store, self.run_id, self.root_path / "episodes"
        self.owner.resources = {"local-rna": {"kind": "local", "policy": deepcopy(POLICY)}}
        self.owner.handoff_unit, self.owner.acquired_record_unit = 2, 3
        self.targets = SyntheticTargets(self)
        self.owner.job_progress_provider = SimpleNamespace(targets=self.targets)
        self.results = self.owner.native_rna_structure_results = NativeRNAStructureResults(self.owner)
        self.returns = self.owner.native_rna_structure_returns = NativeRNAStructureReturns(self.owner)

    def context(self, path, assignment, contract, parent=None):
        ident = EpisodeRef(self.run_id, path).episode_id
        self.receipts.bind(ident, None if parent is None else parent.episode_id)
        goal = (EpisodeGoal.root(objective="Verify explicitly synthetic RNA delivery", result_contract={"role": path[-1][0]})
            if parent is None else EpisodeGoal.child(EpisodeGoal.from_record(plain(parent.request)["goal"]),
                objective="Verify supplied RNA delivery", result_contract=contract.schema))
        message = {"scope": deepcopy(self.scope), "initial_report": {}, "episode_assignment": deepcopy(assignment)}
        request = EpisodeRequest(goal, Record(message), contract).as_record()
        context = BindingContext(self.run_id, ident, path[-1][0], path, self.scope, assignment, request)
        self.journal.save("runtime_episodes", {"episode_id": ident, "path": canonical(path), "request": canonical(request),
            "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, *, selection=None, sources=None, parent=None, index=0, role="results"):
        parent = parent or self.root
        selection = selection or selector()
        schema = schema_for(*(sources or [FAMILY_SOURCES[selection["projection"]["family"]]]))
        contract = TypedReportContract("Return exactly requested RNA facts", schema, lambda *_: True)
        assignment = {"version": "execution_results_assignment_v1", "handoff_ref": self.handoff, "selector": deepcopy(selection)} if role == "results" else {}
        child = self.context((*parent.path, (role, "child_" + str(index))), assignment, contract, parent)
        action = {"kind": "episode_child", "role": role, "assignment": assignment, "scope": deepcopy(self.scope),
            "purpose": contract.decision, "schema_json": canonical(schema)}
        self.journal.save("runtime_actions", {"episode_id": parent.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        return child

    def execute(self, child, *, index=0, name="execution.results.collect"):
        key = f"{self.run_id}:{child.episode_id}:{index}"
        action = {"kind": "tool", "tool": name, "arguments": {}}
        self.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        outcome = asyncio.run(self.results.execute(child, self.target, name, {}, key))
        self.journal.save("runtime_actions", {"episode_id": child.episode_id, "decision_index": index,
            "action": canonical(action), "result": canonical(outcome), "credit": 0})
        self.receipts.receive(child.episode_id, outcome["record_refs"], kind="own_action", source_index=index)
        return outcome["result"]

    def returned(self, parent, child):
        contract = plain(child.request)["report_contract"]
        schema = contract["measurements"]["schema"]
        facts = self.results.facts(child) if child.role == "results" else self.returns.received_facts(child, schema)
        form = form_with_facts({}, schema, facts)
        self.journal.save("runtime_forms", {"episode_id": child.episode_id, "facts": canonical(facts), "form": canonical(form)})
        index = int(child.path[-1][1].removeprefix("child_"))
        self.journal.save("runtime_report_attempts", {"parent_episode_id": parent.episode_id, "decision_index": index,
            "delivery_ref": "delivery_" + digest([parent.episode_id, index])[:24], "child_episode_id": child.episode_id,
            "contract": canonical(contract), "form": canonical(form), "failure": None})
        refs = self.returns.record_admission(parent, form, schema, f"{self.run_id}:{parent.episode_id}:{index}:typed_form")
        self.receipts.receive(parent.episode_id, refs, kind="child_form", source_index=index)
        return form

    def saved_selector(self, body, *, long_stem=4, accepted=("AU", "UA")):
        parameters = deepcopy(PARAMETERS)
        parameters["topology"]["long_stem_min_pairs"] = long_stem
        parameters["pair_composition"]["accepted_ordered_pair_types"] = list(accepted)
        return {"version": "native_rna_structure_saved_sheet_selector_v1", "acquisition": "retained_sheet_only",
            "saved_input": self.results.saved_descriptor(body), "parameters": parameters, "projection": selector()["projection"]}


def retain(name, **values):
    output = os.environ.get("RNA_RESULTS_EXAMPLE_OUTPUT")
    if output:
        path = Path(output)
        path.mkdir(parents=True, exist_ok=True)
        (path / (name + ".json")).write_text(json.dumps(values, indent=2, sort_keys=True, allow_nan=False) + "\n")
