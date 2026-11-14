"""Selected RNA custody/calculation actions in the existing results episode.

Receipts authenticate recorded work. This adapter chooses no native work,
resource, retry, annotation credit or extra episode observation.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import checked, obj
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_acquisition import ORIGIN, capture_local_rna_structure_bundle, decode_json, is_native_rna_structure_target, publish_rna_structure_source, qualify_target_plan, require, retained, rna_structure_source_payload, validate_capture
from gene_annotation_episode.episodic_workflow.root.library.rna_result_preparation import prepare_rna_structure_grading, prepare_saved_rna_structure_grading, validate_prepared_rna_grading
from gene_annotation_episode.episodic_workflow.root.library.rna_result_publication import publish_selected_rna_structure_rows
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import authenticate_rna_results_commission
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.progress_records import validate_resource_observation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import RNA_ISSUE_CODES, issue, validate_rna_issue
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import FAMILY_SOURCES, IDENTIFIER_NAMESPACES, REFERENCE_SOURCE, SAVED_SOURCE, merge_issues, prepare_rna_structure_failure_selection, project_rna_structure_failure_rows, result_receipt_key, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input

from gene_annotation_episode.episodic_workflow.root.library.rna_result_records import VERSION, FIELDS, operation_catalog
from gene_annotation_episode.episodic_workflow.root.library.rna_result_reference_access import retained_reference_access
from gene_annotation_episode.episodic_workflow.root.rna_result_credit import RnaResultCredit
from gene_annotation_episode.episodic_workflow.root.rna_result_custody import RnaResultCustody
from gene_annotation_episode.episodic_workflow.root.rna_result_facts import RnaResultFacts

class NativeRNAStructureResults(RnaResultCredit, RnaResultCustody, RnaResultFacts):
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory / "native-rna-structure-result-index"
        self.records = EpisodeReturnRecords(owner.store, owner.run_id, failure_prefix="rna_return_")

    def applies(self, context):
        return context.role == "results" and is_native_rna_structure_target(self.owner._target(context))

    def _directory(self, context):
        return self.owner._result_directory(context) / "native-rna-structure-actions"

    def _policy(self, target):
        return LocalJobPolicy(**self.owner.resources[target["resource_id"]]["policy"])

    async def execute(self, context, target, tool_name, arguments, operation_key):
        authenticate_rna_results_commission(self.store, context)
        require(plain(context.assignment)["handoff_ref"] in set(
            EpisodeReceipts(self.store, context.run_id).known(context.episode_id, baseline=True)))
        require(context.role == "results" and target == self.owner._target(context))
        selector = self._selector(plain(context.assignment), target)
        require(tool_name in {item["name"] for item in operation_catalog()} and arguments == {})
        self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        _immutable(directory / "intent.json", {"target": target, "assignment": plain(context.assignment),
            "operation_key": operation_key, "tool_name": tool_name, "arguments": arguments, "scope": plain(context.scope)})
        if (directory / "receipt.json").exists():
            body = self._validate_body(_read(directory / "receipt.json"), context.scope)
        else:
            saved = selector["acquisition"] == "retained_sheet_only"
            original = self.owner.native_rna_structure_returns.resolve_saved_rna_input(context, selector["saved_input"]) if saved else None
            if not (directory / "observation.json").exists():
                observation = original["observation"] if saved else self.owner.job_progress_provider.targets.observe_target(target, operation_key=operation_key)
                validate_resource_observation(observation)
                _immutable(directory / "observation.json", observation)
            body = {"version": VERSION, "run_id": context.run_id, "episode_id": context.episode_id,
                "scope": plain(context.scope), "assignment": plain(context.assignment), "operation_key": operation_key,
                "tool_name": tool_name, "arguments": arguments, "target": target, "observation": _read(directory / "observation.json"),
                "capture": original["capture"] if saved else None, "prepared": None, "source_ref": None, "record_refs": [],
                "rows": [], "failures": [], "failure_selection": None,
                "native_success": original["native_success"] if saved else False,
                "capture_complete": original["capture_complete"] if saved else False, "delivery_complete": False}
            if tool_name == "execution.results.collect":
                capture = original["capture"] if saved else capture_local_rna_structure_bundle(self.store, target=target, directory=directory / "capture")
                body["capture"], body["capture_complete"] = capture, capture["capture_complete"]
                body["failures"] = [] if saved else capture["failures"]
                if capture["bundle_validated"]:
                    bundle = self._bundle(body)
                    body["native_success"] = bundle["returncode"] == 0 and bundle["native_status"] == "complete"
                    try:
                        prepared = (prepare_saved_rna_structure_grading(self.store, context,
                            saved_input=selector["saved_input"], parameters=selector["parameters"], directory=directory / "grading",
                            policy=self._policy(target), selector=selector, returns=self.owner.native_rna_structure_returns) if saved else
                            prepare_rna_structure_grading(self.store, bundle=bundle, capture=capture, directory=directory / "grading",
                                policy=self._policy(target), selector=selector))
                    except (ValueError, OSError, AcquisitionError) as error:
                        prepared = None
                        failure = issue(str(error) if str(error) in RNA_ISSUE_CODES else "rna_capture_unavailable",
                            stage="calculate", record_key=bundle["record_key"])
                        _immutable(directory / "preparation-failure.json", failure)
                        body["failures"] = merge_issues([] if saved else bundle["failures"],
                            [] if saved else capture["failures"], [failure])
                    body["prepared"] = prepared
                    body["source_ref"] = original["source_ref"] if saved else publish_rna_structure_source(self.store, bundle=bundle, capture=capture, prepared=prepared)
                    body["record_refs"] = [body["source_ref"]]
                    if prepared is not None:
                        publication = publish_selected_rna_structure_rows(self.store, context, source_ref=body["source_ref"],
                            bundle=bundle, capture=capture, prepared=prepared, selector=selector)
                        _immutable(directory / "publication.json", publication)
                        body.update({key: publication[key] for key in ("record_refs", "rows", "failures")})
                        body["delivery_complete"] = bool(publication["requested_cells_accounted_for"] and
                            (prepared["sheet_artifact_ref"] is not None if saved else capture["capture_complete"]))
            elif saved:
                try:
                    retained(self.store, selector["saved_input"]["sheet_artifact_ref"])
                except (ValueError, OSError, KeyError):
                    body["failures"] = [issue("rna_capture_unavailable", stage="capture",
                        record_key=selector["saved_input"]["record_key"], field="/selector/saved_input/sheet_artifact_ref")]
            _immutable(directory / "failure-ledger.json", body["failures"])
            selection = prepare_rna_structure_failure_selection(failures=body["failures"], selector=selector,
                record_key=target["assignment"]["requested_job"]["native_rna_structure"]["record_key"])
            body.update(failures=selection["failures"], failure_selection=selection["selection"])
            if selection["selection"] is not None:
                body["delivery_complete"] = bool(tool_name == "execution.results.collect" and body["source_ref"] is not None
                    and selection["selection"]["requested_rows_accounted_for"] and
                    (body["prepared"] is not None and body["prepared"]["sheet_artifact_ref"] is not None if saved else body["capture_complete"]))
            _immutable(directory / "receipt.json", body)
            self._validate_body(body, context.scope)
        self._index(body)
        return self._outcome(body)

__all__ = ["NativeRNAStructureResults", "operation_catalog", "VERSION", "retained_reference_access"]
