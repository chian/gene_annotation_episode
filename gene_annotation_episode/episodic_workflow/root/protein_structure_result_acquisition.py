"""Original selected native capture, saved-sheet preparation and non-cancelling worker observation."""
from __future__ import annotations

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_publication import publish_protein_structure_source
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_records import _require, _problem, _empty_files
from gene_annotation_episode.episodic_workflow.root.protein_structure_operands import validate_protein_structure_selected_inputs
from gene_annotation_episode.episodic_workflow.root.protein_structure_result_receipts import ProteinResultAction
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_acquisition import capture_local_protein_structure_bundle, retained_protein_structure_file, validate_protein_structure_capture
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_contracts import validate_protein_structure_bundle
from gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_preparation import ValidatedProteinWorker, prepare_protein_structure_worker, validate_prepared_protein_structure_worker
from gene_annotation_episode.episodic_workflow.root.progress_records import validate_resource_observation
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_contracts import same
from gene_annotation_episode.episodic_workflow.root.library.protein_structure_result_worker import ProteinResultWorkerPlan
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.state import Store
from pathlib import Path
import asyncio


def _prepare_worker_in_thread(store_path: Path, *, plan: ProteinResultWorkerPlan,
                              policy: LocalJobPolicy) -> ValidatedProteinWorker:
    # SQLite connections stay on their owning thread. Only a detached plan and
    # the same Store's path cross this boundary.
    with Store(store_path) as worker_store:
        prepared = prepare_protein_structure_worker(worker_store, plan=plan, policy=policy)
        return validate_prepared_protein_structure_worker(worker_store, prepared, plan=plan)


class ProteinStructureResultAcquisition:
    async def _prepare_worker(self, *, action: ProteinResultAction,
                              plan: ProteinResultWorkerPlan,
                              policy: LocalJobPolicy) -> ValidatedProteinWorker:
        self.receipts.require_action(action)
        _require(plan["directory"] == str(action.worker_directory), "invalid_output_path")
        _require(not self.store.db.in_transaction)
        task = asyncio.create_task(asyncio.to_thread(_prepare_worker_in_thread,
            self.store.path, plan=deepcopy(plan), policy=policy))
        try:
            return deepcopy(await asyncio.shield(task))
        except asyncio.CancelledError:
            # A cancelled caller still owns the original reservation and action
            # lock until blocking preparation has returned. Never cancel/retry
            # native work or let a second caller start while it is outstanding.
            while not task.done():
                try:
                    await asyncio.shield(task)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
            if task.done() and not task.cancelled():
                task.exception()
            raise

    def _policy(self, target):
        resource = self.owner.resources[target["resource_id"]]
        _require(resource["kind"] == "local")
        return LocalJobPolicy(**resource["policy"])

    async def _original(self, action, context, target, body, *, collecting):
        validate_protein_structure_selected_inputs(self.store, context, body["intent"]["assignment"]["selector"],
            handoff_ref=body["intent"]["assignment"]["handoff_ref"], returns=self._returns)
        body["handoff_proof"] = self.receipts.read_handoff_proof(action, context=context, target=target)
        observation = self.receipts.read_observation(action)
        if observation is None:
            observation = self.owner.job_progress_provider.targets.observe_target(target, operation_key=body["intent"]["operation_key"])
            validate_resource_observation(observation)
            observation = self.receipts.record_observation(action, observation=observation)
        body.update(observation=observation, observation_origin="selected_native_observation")
        if not collecting:
            return None, None
        capture = capture_local_protein_structure_bundle(self.store, target=target, directory=action.capture_directory)
        capture = validate_protein_structure_capture(self.store, capture, target=target)
        body.update(capture=capture, capture_complete=capture["capture_complete"])
        body["issues"].extend(capture["failures"])
        if not capture["bundle_validated"]:
            return None, None
        bundle = validate_protein_structure_bundle(self._json(capture["bundle_file"]), plan=capture["original_plan"])
        body.update(bundle=bundle, native_success=bundle["returncode"] == 0 and bundle["native_status"] == "complete")
        body["issues"].extend(bundle["failures"])
        native_file = self._captured(capture, "native_result")
        plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "original_native_result",
            "directory": str(action.worker_directory),
            "expected_request": deepcopy(bundle["requested_job"]["native_protein_structure"]["request"]),
            "expected_software": deepcopy(bundle["software"]), "native_result": None}
        if native_file is not None:
            plan["native_result"] = {"file_identity": native_file,
                "path": str(retained_protein_structure_file(self.store, native_file))}
        try:
            body["worker"] = await self._prepare_worker(action=action, plan=plan, policy=self._policy(target))
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error))
        self._worker_issues(body)
        scientific = None
        try:
            scientific = self._original_science(body)
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error, stage="native", field=None, role="native_result"))
            body["qualified_files"], body["calculation"] = _empty_files(), None
        worker_result = None if body["worker"] is None else body["worker"]["result"]
        source = publish_protein_structure_source(self.store, bundle=bundle, capture=capture, worker_result=worker_result)
        return scientific, self.store.get(source)

    @staticmethod
    def _worker_issues(body):
        if body["worker"] is not None:
            body["issues"].extend(body["worker"]["prepared"]["issues"])
            if body["worker"]["result"] is not None:
                body["issues"].extend(body["worker"]["result"]["issues"])

    async def _saved(self, action, context, target, body, *, collecting):
        selector = body["intent"]["assignment"]["selector"]
        descriptor = selector["saved_sheet"]
        self._returns.authenticate_received_saved_sheet(context, descriptor, required_use="recalculate")
        custody = descriptor["custody"]
        original = self.receipts.read_completed(episode_id=custody["result_episode_id"],
            operation_key=custody["result_operation_key"], scope=plain(context.scope))
        _require(same(custody, original["publication"]["custody"]))
        body["original_custody"] = deepcopy(custody)
        body["handoff_proof"] = self.receipts.read_handoff_proof(action, context=context, target=target)
        for name in ("bundle", "capture", "native_success", "capture_complete"):
            body[name] = deepcopy(original["body"][name])
        observation = original["body"]["observation"]
        if observation is not None:
            observation = self.receipts.record_observation(action, observation=observation)
        body.update(observation=observation,
            observation_origin="original_saved_observation" if observation is not None else "not_observed")
        source_record = deepcopy(original["publication"]["source_record"]) if collecting else None
        # Authority survives historical byte loss. Actual use of the pair is a
        # separate selected check and its failure leaves delivery incomplete.
        try:
            validate_protein_structure_selected_inputs(self.store, context, selector,
                handoff_ref=body["intent"]["assignment"]["handoff_ref"], returns=self._returns)
            if not collecting:
                return None, None
            plan = {"version": "protein_structure_result_worker_plan_v1", "mode": "saved_sheet_recalculation",
                "directory": str(action.worker_directory), "parameters": deepcopy(selector["parameters"]),
                "sheet": {"file_identity": deepcopy(descriptor["sheet_file"]),
                    "path": str(retained_protein_structure_file(self.store, descriptor["sheet_file"]))},
                "original_components": {"file_identity": deepcopy(descriptor["original_components_file"]),
                    "path": str(retained_protein_structure_file(self.store, descriptor["original_components_file"]))}}
            body["worker"] = await self._prepare_worker(action=action, plan=plan, policy=self._policy(target))
            self._worker_issues(body)
            scientific = self._saved_science(body, original, selector)
            return scientific, source_record
        except (ValueError, OSError) as error:
            body["issues"].append(_problem(error))
            body["qualified_files"], body["calculation"] = _empty_files(), None
            return None, source_record

