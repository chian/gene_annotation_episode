"""One selected retained comparison action inside the existing results role.

Original inputs and actions establish authority. The separate worker owns only
deterministic calculation/publication. No native observation or acquisition runs.
"""
from __future__ import annotations

from copy import deepcopy
import json

from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.communication import validate_form
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.execution_contracts import obj
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import authenticate_rna_results_commission
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_contracts import CALCULATOR_VERSION, SELECTOR_VERSION, validate_rna_comparison_issue, validate_rna_comparison_selector
from gene_annotation_episode.episodic_workflow.root.rna_structure_comparison_operands import RNAComparisonInputError, SAVED_REFERENCE_FIELDS, _require, resolve_rna_comparison_operands, validate_rna_comparison_selected_inputs
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_views import PROJECTION_SOURCE

from gene_annotation_episode.episodic_workflow.root.library.rna_comparison_result_records import VERSION, IDENTIFIER_NAMESPACES, FIELDS, PREPARED_COPY_FIELDS, VALIDATION_KEYS, result_receipt_key, operation_catalog, _original_keys
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY
from gene_annotation_episode.episodic_workflow.root.rna_comparison_result_credit import RnaComparisonResultCredit
from gene_annotation_episode.episodic_workflow.root.rna_comparison_result_custody import RnaComparisonResultCustody
from gene_annotation_episode.episodic_workflow.root.rna_comparison_result_facts import RnaComparisonResultFacts

class NativeRNAStructureComparisonResults(RnaComparisonResultCredit, RnaComparisonResultCustody, RnaComparisonResultFacts):
    def __init__(self, owner):
        self.owner, self.store = owner, owner.store
        self.directory = owner.directory / "rna-structure-comparison-result-index"
        self.records = EpisodeReturnRecords(owner.store, owner.run_id, failure_prefix="rna_comparison_")

    @property
    def returns(self):
        return self.owner.native_rna_structure_returns

    def applies(self, context):
        return context.role == "results" and plain(context.assignment).get("selector", {}).get("version") == SELECTOR_VERSION

    def _directory(self, context):
        return self.owner._result_directory(context) / "rna-structure-comparison-actions"

    def _resolve_operands(self, context, assignment):
        return resolve_rna_comparison_operands(self.store, context, assignment["selector"],
            anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)

    def _policy(self, target):
        config = self.owner.resources[target["resource_id"]]
        _require(config["kind"] == "local" and config["policy"] == POLICY, "policy_mismatch")
        return LocalJobPolicy(**config["policy"])

    async def execute(self, context, target, tool_name, arguments, operation_key):
        assignment = self._assignment(context)
        _require(target == self.owner._target(context) and target["handle"] == assignment["handoff_ref"], "anchor_mismatch")
        _require(tool_name in {item["name"] for item in operation_catalog()}
            and type(arguments) is dict and not arguments, "invalid_operation")
        selected = self.owner._selected_result_action(context.episode_id, operation_key, tool_name, arguments)
        policy = self._policy(target)
        directory = self._directory(context) / digest(operation_key)
        directory.mkdir(parents=True, exist_ok=True)
        _immutable(directory / "intent.json", self._intent(context, assignment, target,
            operation_key, tool_name, arguments, selected))
        if (directory / "receipt.json").exists():
            body = self._validate_body(_read(directory / "receipt.json"), context.scope)
        else:
            body = {"version": VERSION, "run_id": context.run_id, "episode_id": context.episode_id,
                "scope_key": digest(plain(context.scope)), "assignment_digest": digest(assignment),
                "operation_key": operation_key, "tool_name": tool_name, "arguments": {},
                "selected_action_digest": digest(json.loads(selected["action"])),
                "anchor_handoff_ref": assignment["handoff_ref"], "selector": assignment["selector"],
                "original_receipt_keys": _original_keys(assignment["selector"]), "selected_input_digests": [],
                "comparison_sheet_artifact_ref": None, "comparison_sheet_sha256": None,
                "components_artifact_ref": None, "components_sha256": None,
                "calculator_version": CALCULATOR_VERSION, "projection_rows": [], "issues": [],
                "preparation_failure": None, "delivery_complete": False}
            failure_path = directory / "input-failure.json"
            saved_failure = _read(failure_path) if failure_path.exists() else None
            if saved_failure is not None:
                body["issues"] = saved_failure["issues"]
            else:
                failure = {"issues": [], "cause": None}
                try:
                    operands = self._resolve_operands(context, assignment)
                except RNAComparisonInputError as error:
                    failure = {"issues": [error.issue], "cause": {
                        "exception_type": type(error.__cause__).__name__, "detail": str(error.__cause__)}}
                    body["issues"] = failure["issues"]
                    if tool_name == "execution.results.collect":
                        _immutable(directory / "input-failure.json", failure)
                if tool_name == "execution.results.status":
                    _immutable(directory / "status.json", failure)
                elif not body["issues"]:
                    from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_publication import prepare_rna_comparison_grading, publish_selected_rna_comparison_rows
                    prepared = prepare_rna_comparison_grading(self.store, selector=assignment["selector"],
                        operands=operands, result_receipt_key=result_receipt_key(body), directory=directory / "grading", policy=policy)
                    rows = publish_selected_rna_comparison_rows(self.store, selector=assignment["selector"],
                        prepared=prepared, operands=operands, result_receipt_key=result_receipt_key(body))
                    _require(self.records._equal(rows, prepared["projection_rows"]), "projection_mismatch")
                    body.update({key: deepcopy(prepared[key]) for key in PREPARED_COPY_FIELDS})
            _immutable(directory / "receipt.json", body)
            body = self._validate_body(body, context.scope)
        pointer = {key: body[key] for key in ("run_id", "episode_id", "operation_key")}
        index = self.directory / digest(result_receipt_key(body))
        index.mkdir(parents=True, exist_ok=True)
        _immutable(index / (digest(operation_key) + ".json"), pointer)
        return self._outcome(body)

__all__ = ["NativeRNAStructureComparisonResults", "operation_catalog", "result_receipt_key", "VERSION", "IDENTIFIER_NAMESPACES"]
