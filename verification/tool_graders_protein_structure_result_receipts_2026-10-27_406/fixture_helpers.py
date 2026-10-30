"""Actual Store/Journal/commission controls; injected or live practical work.

``injected_publication`` deliberately supplies qualification metadata for receipt
mechanism tests. It does not assert that a native scientific job ran. ``live``
launches the ordinary practical operation and retains its real completed row.
"""
from copy import deepcopy
from importlib import import_module
import json
from pathlib import Path
from types import SimpleNamespace

from method_loop.identities import EpisodeRef
from gene_annotation_episode.communication import plain
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_episodes import ExecutionEpisodes
from gene_annotation_episode.native_protein_structure_contracts import (
    POLICY, compile_protein_structure_job, driver_argv, manifest_files,
    realized_environment, requested_job_from_protein_structure, validate_protein_structure_bundle,
)
from gene_annotation_episode.native_protein_structure_returns import NativeProteinStructureReturns
from gene_annotation_episode.practical_execution_records import assess_validations
from gene_annotation_episode.practical_execution_state import PracticalState
from gene_annotation_episode.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.protein_structure_contracts import issue
from gene_annotation_episode.protein_structure_publication import protein_structure_source_payload
from gene_annotation_episode.protein_structure_result_receipts import (
    ProteinResultReceipts, ProteinQualifiedFiles, ProteinFactGroups,
)

F = import_module("verification.tool_graders_protein_structure_execution_2026-10-27_390.fixture_helpers")


def empty_selector():
    return {"version": "protein_structure_result_selector_v1", "acquisition": "complete_bound_bundle",
        "saved_sheet": None, "parameters": None, "projections": [], "return_saved_sheet": False,
        "sequence_allowed_uses": []}


def outcome(receipt):
    refs = receipt["publication"]["record_refs"]
    return {"status": "completed", "record_refs": refs, "changed_record_refs": refs,
        "result": receipt, "feedback": None}


class ReceiptFixture:
    def __init__(self, store, directory, *, run_id="protein406-recorded-injected", kind="inspect"):
        self.store, self.directory, self.run_id = store, Path(directory), run_id
        self.directory.mkdir(parents=True)
        self.journal = Journal(store, run_id)
        self.episode_receipts = EpisodeReceipts(store, run_id)
        self.scope = {"subject_refs": store.create_problem(raw_sequence="AGST", molecule="protein")["subject_refs"]}
        self.root = self.context((("annotation", "root"),), {}, None)
        self.episode_receipts.receive(self.root.episode_id, self.scope["subject_refs"], kind="initial")
        self.owner = SimpleNamespace(store=store, directory=self.directory / "runtime", run_id=run_id)
        self.owner._selected_result_action = lambda *args: ExecutionEpisodes._selected_result_action(self.owner, *args)
        self.receipts = ProteinResultReceipts(self.owner)
        # Narrow reader fixture only: production host407 supplies these ports.
        self.owner.native_protein_structure_results = SimpleNamespace(owns_reference=self.receipts.owns_reference)
        self.returns = self.owner.native_protein_structure_returns = NativeProteinStructureReturns(self.owner)
        self.workspace = self.directory / "producer"
        selected = F.job(self.workspace, kind=kind)
        self.requested = requested_job_from_protein_structure(selected)
        for row in selected["inputs"]:
            assert self.store.artifact(Path(row["path"]).read_bytes()) == row["file_identity"]["artifact_ref"]
        self.assignment = {"version": "practical_assignment_v1", "assignment_id": "fixture-original-native",
            "resource_kind": "local", "resource_id": "selected-local", "workspace": str(self.workspace),
            "endpoint": "usable_handoff", "requested_job": self.requested,
            "progress_requirements": [{"key": "handoff", "credit": 1,
                "predicate": {"kind": "requested_job_handoff"}}], "completion_keys": ["handoff"],
            "initial_context": {"revision": 0, "cwd": str(self.workspace), "environment": {}},
            "inventory_snapshot": {}, "constraints": {"allocation": deepcopy(POLICY)}}
        self.launch = self.child(role="launch_local", assignment=self.assignment, index=0)
        self.launch_key = self.select(self.launch, "practical.job.start")
        self.attempt_root = self.workspace / ".episode-operations" / digest({"run": run_id,
            "episode": self.launch.episode_id}) / digest(self.launch_key)
        self.config = {"kind": "local", "workspace": str(self.workspace), "policy": deepcopy(POLICY),
            "native_protein_structure": [{"operation": selected["request"]["operation"],
                "scientific_mode": selected["request"].get("parameters", {}).get("mode"),
                "software": deepcopy(selected["software"])}]}

    def context(self, path, assignment, contract, parent=None, *, save=True):
        episode_id = EpisodeRef(self.run_id, path).episode_id
        manifest = self.episode_receipts.bind(episode_id, None if parent is None else parent.episode_id)
        request = {"goal": {"goal_id": "protein406-fixture", "objective": "Verify original receipt relationships"},
            "message": {"scope": deepcopy(self.scope), "episode_assignment": deepcopy(assignment),
                "knowledge_inheritance": manifest, "initial_report": {}}, "report_contract": deepcopy(contract)}
        context = BindingContext(self.run_id, episode_id, path[-1][0], path, self.scope, assignment, request)
        if save:
            self.journal.save("runtime_episodes", {"episode_id": episode_id, "path": canonical(path),
                "request": canonical(request), "initial_credit": 0, "state": "active", "completion": None, "archive": None})
        return context

    def child(self, *, role="results", assignment=None, index=1, selector=None, save=True, schema=None):
        if assignment is None:
            assignment = {"version": "execution_results_assignment_v1", "handoff_ref": self.handoff,
                          "selector": deepcopy(selector or empty_selector())}
        schema = schema or {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
        contract = {"decision": "Return requested fixture records", "measurements": {"schema": schema}}
        child = self.context((*self.root.path, (role, "child_" + str(index))), assignment, contract,
                             self.root, save=save)
        action = {"kind": "episode_child", "role": role, "assignment": deepcopy(assignment),
            "scope": deepcopy(self.scope), "purpose": contract["decision"], "schema_json": canonical(schema),
            "goal": child.request["goal"]["objective"], "initial_report_json": "{}"}
        self.journal.save("runtime_actions", {"episode_id": self.root.episode_id, "decision_index": index,
            "action": canonical(action), "result": None, "credit": None})
        return child

    def select(self, context, name="execution.results.collect", *, index=0):
        self.journal.save("runtime_actions", {"episode_id": context.episode_id, "decision_index": index,
            "action": canonical({"kind": "tool", "tool": name, "arguments": {}}), "result": None, "credit": None})
        return f"{self.run_id}:{context.episode_id}:{index}"

    def commit(self, context, result, *, index=0):
        self.store.db.execute("UPDATE runtime_actions SET result=? WHERE run_id=? AND episode_id=? AND decision_index=?",
            (canonical(result), self.run_id, context.episode_id, index))

    def _target(self, source):
        return {"version": "execution_target_v1", "handle": source, "run_id": self.run_id,
            "resource_id": self.assignment["resource_id"], "resource_kind": "local",
            "execution_id": str(self.attempt_root / "native.json"), "request_sha256": digest(self.requested),
            "origin_episode_id": self.launch.episode_id, "assignment": self.assignment, "scope": self.scope}

    def injected_handoff(self):
        state = PracticalState(self.directory / "practical-controls", self.run_id, self.launch.episode_id, self.assignment)
        state.begin(self.launch_key, "practical.job.start", {})
        execution_id = str(self.attempt_root / "native.json")
        result = {"facts": {"requested_job": {"argv": self.requested["argv"], "environment": self.requested["environment"],
            "returncode": 0, "execution_id": execution_id, "requested_job_sha256": digest(self.requested),
            "resource_kind": "local", "status": "completed", "output_paths": [], "handoff": {
                "execution_id": execution_id, "monitor_operation": "practical.job.status", "results_operation": "practical.job.collect"}}},
            "native_outcome": {"attempt_operation_key": self.launch_key, "attempt_id": digest(self.launch_key)}}
        assessments = assess_validations(self.assignment, result, state.context(), tool_name="practical.job.start")
        receipt = state.finish(self.launch_key, result, assessments)
        practical = PracticalReceiptInformation(self.store, self.run_id)
        self.handoff = practical.publish(self.launch, receipt)
        self.commit(self.launch, {"status": "completed", "record_refs": [self.handoff],
            "changed_record_refs": [self.handoff], "result": receipt, "feedback": None})
        self.target = self._target(self.handoff)
        self.episode_receipts.receive(self.root.episode_id, [self.handoff], kind="child_form", source_index=0)
        return self.handoff

    async def live(self):
        """Actual selected practical launch; no injected native result."""
        from gene_annotation_episode.practical_resource_episodes import PracticalResourceEpisodes
        from gene_annotation_episode.execution_progress import ExecutionProgressProvider
        from gene_annotation_episode import native_lifecycle
        import asyncio
        binding = PracticalResourceEpisodes(None, directory=self.directory / "practical-runtime",
            resources={"local": self.config}, store=self.store)
        binding.initialize(self.launch)
        selected = await binding.execute(self.launch, "practical.job.start", {}, self.launch_key)
        assert selected["status"] == "completed", selected
        self.commit(self.launch, selected)
        self.handoff = selected["record_refs"][0]
        self.target = self._target(self.handoff)
        handle = native_lifecycle.NativeJobHandle(Path(self.target["execution_id"]))
        await asyncio.to_thread(native_lifecycle.wait_job, handle)
        self.owner.job_progress_provider = ExecutionProgressProvider(self.store, run_id=self.run_id,
            directory=self.directory / "monitor", resources={self.assignment["resource_id"]: self.config}, api_execution=None,
            log_window_bytes=8192, log_roles=("stdout", "stderr"))
        self.target = self.owner.job_progress_provider.targets.read_target(self.handoff, self.scope)
        self.episode_receipts.receive(self.root.episode_id, [self.handoff], kind="child_form", source_index=0)
        return self.handoff

    def retained(self, raw, format):
        ref = self.store.artifact(raw)
        metadata = self.store.get(ref)
        return {"artifact_ref": ref, "sha256": metadata["sha256"], "byte_length": metadata["size"], "format": format}

    def retained_json(self, value, format):
        return self.retained(canonical(value).encode("utf-8"), format)

    def injected_publication(self, action, proof):
        """A qualified unavailable manifest; no native scientific output claimed."""
        job = self.requested["native_protein_structure"]
        assert job["request"]["operation"] == "inspect"
        plan = {"version": "native_protein_structure_run_plan_v1", "identity": {
            "run_id": self.run_id, "episode_id": self.launch.episode_id, "resource_id": self.assignment["resource_id"],
            "execution_id": self.target["execution_id"], "attempt_id": digest(self.launch_key),
            "operation_key": self.launch_key, "requested_job_sha256": digest(self.requested)},
            "requested_job": self.requested, "attempt_directory": str(self.attempt_root / "protein-structure-attempt"),
            "policy": deepcopy(POLICY)}
        declared, captured = [], []
        problem = issue("native_result_missing", stage="native", artifact_role="native_result")
        for index, row in enumerate(manifest_files(job)):
            if row["role"] == "native_result":
                file, state = None, "absent"
            else:
                worker_input = {"version": "protein_structure_worker_input_v1", "request": job["request"],
                    "software": job["software"], "files": [{"input_id": item["input_id"], "role": item["role"],
                        "file_identity": item["file_identity"], "path": str(Path(plan["attempt_directory"]) /
                            item["staged_relative_path"])} for item in job["inputs"]]}
                raw = (canonical(plan).encode() if row["role"] == "run_plan" else
                    canonical(worker_input).encode() if row["role"] == "worker_input" else
                    Path(next(f["path"] for f in job["inputs"] if f["input_id"] == row["input_id"])).read_bytes()
                    if row["kind"] == "input" else b"injected compact receipt fixture")
                file, state = self.retained(raw, row["format"]), "present"
            declared.append({**row, "state": state, "sha256": None if file is None else file["sha256"],
                "byte_length": None if file is None else file["byte_length"]})
            captured.append({"manifest_index_0based": index, "declared": declared[-1], "observed": file,
                "outcome": "declared_absent" if file is None else "verified", "issue": None})
        bundle = {"version": "native_protein_structure_bundle_v1", "identity": plan["identity"],
            "requested_job": self.requested, "software": job["software"], "driver_argv": driver_argv(plan),
            "worker_argv": compile_protein_structure_job(job, output_directory=plan["attempt_directory"])["argv"],
            "realized_environment": realized_environment(job, plan["attempt_directory"]), "files": declared,
            "returncode": 1, "native_status": "failed", "started_at": "2026-10-27T00:00:00+00:00",
            "finished_at": "2026-10-27T00:00:01+00:00", "measured_duration": {
                "seconds": None, "kind": "unmeasured", "source": "none"}, "failures": [problem], "sealed": True}
        validate_protein_structure_bundle(bundle, plan=plan)
        capture = {"version": "native_protein_structure_capture_v1", "original_plan": plan,
            "bundle_file": self.retained_json(bundle, bundle["version"]), "bundle_validated": True,
            "files": captured, "failures": [], "capture_complete": True}
        worker_plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
            "directory": str(action.worker_directory), "expected_request": job["request"],
            "expected_software": job["software"], "native_result": None}
        result = {"version": "protein_structure_result_worker_result_v1", "mode": "original_native_result",
            "operation": "inspect", "native_result_file": None, "sheet_file": None, "components_file": None,
            "state": "unavailable", "issues": [problem]}
        diagnostic = self.retained_json(result, result["version"])["artifact_ref"]
        execution = {"version": "protein_structure_worker_execution_v1", "outcome": "returned", "returncode": 0,
            "metadata": {"native_returncode": 0, "service_exit": {}, "policy": deepcopy(POLICY), "enforcement": {
                "memory": "systemd_cgroup_v2_memory_max", "swap": "systemd_memory_swap_max_zero", "wall_time": "unset"},
                "verified_cgroup": {"memory_max": POLICY["memory_bytes"], "memory_swap_max": 0, "runtime_max": "infinity"}},
            "failure": None, "stdout_artifact_ref": self.store.artifact(b"injected stdout"),
            "stderr_artifact_ref": self.store.artifact(b"injected stderr"),
            "handle_artifact_ref": self.store.artifact(b"injected lifecycle handle")}
        prepared = {"version": "protein_structure_prepared_worker_v1",
            "plan_artifact_ref": self.retained_json(worker_plan, worker_plan["version"])["artifact_ref"],
            "execution_receipt_artifact_ref": self.retained_json(execution, execution["version"])["artifact_ref"],
            "worker_result_artifact_ref": diagnostic, "diagnostic_files": [
                {"filename": "worker-result.json", "artifact_ref": diagnostic}], "issues": []}
        worker = {"prepared": prepared, "plan": worker_plan, "execution": execution, "result": result}
        source = self.store.put("source", protein_structure_source_payload(bundle=bundle, capture=capture,
            worker_result=result), origin="tool")
        body = {"version": "protein_structure_result_body_v1", "intent": deepcopy(action.intent), "handoff_proof": proof,
            "observation": None, "observation_origin": "not_observed", "original_custody": None,
            "capture": capture, "bundle": bundle, "worker": worker,
            "qualified_files": {key: None for key in ProteinQualifiedFiles.__annotations__}, "calculation": None,
            "issues": [problem], "native_success": False, "capture_complete": True}
        receipt_key = "protein_structure_result_receipt:" + digest({key: action.intent[key]
            for key in ("run_id", "episode_id", "operation_key")})
        custody = {"run_id": self.run_id, "result_episode_id": action.intent["episode_id"],
            "result_operation_key": action.intent["operation_key"], "result_receipt_key": receipt_key,
            "handoff_ref": self.handoff, "source_ref": source["id"],
            "bundle_artifact_ref": capture["bundle_file"]["artifact_ref"],
            "original_request_sha256": action.intent["original_request_sha256"]}
        facts = {key: [] for key in ProteinFactGroups.__annotations__}
        facts["execution_protein_structure_failures"] = [{"version": "protein_structure_failure_return_v1",
            "custody": custody, "projection_id": None, "issue": problem}]
        refs = [capture["bundle_file"]["artifact_ref"], *[row["observed"]["artifact_ref"] for row in captured
            if row["observed"] is not None], prepared["plan_artifact_ref"], prepared["execution_receipt_artifact_ref"],
            diagnostic, execution["stdout_artifact_ref"], execution["stderr_artifact_ref"], execution["handle_artifact_ref"],
            self.store.artifact(b"injected retained lifecycle request")]
        publication = {"version": "protein_structure_result_publication_v1", "body_sha256": digest(body),
            "result_receipt_key": receipt_key, "custody": custody, "source_record": source, "reference_records": [],
            "facts": facts, "accounting": {"projection_ids": [], "failed_projection_ids": [],
                "saved_sheet": "not_requested", "sequence": "not_requested"}, "record_refs": [source["id"]],
            "family_artifact_refs": list(dict.fromkeys(refs)), "delivery_complete": True}
        return body, publication

    async def publish(self, context=None, *, index=0, commit=True):
        context = context or self.child()
        key = self.select(context, index=index)
        async with self.receipts.locked_action(context, target=self.target, tool_name="execution.results.collect",
                arguments={}, operation_key=key) as action:
            proof = self.receipts.read_handoff_proof(action, context=context, target=self.target)
            body, publication = self.injected_publication(action, proof)
            receipt = self.receipts.publish(action, body=body, publication=publication)
        if commit:
            self.commit(context, outcome(receipt), index=index)
        return context, receipt
