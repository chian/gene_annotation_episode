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

class RnaComparisonResultCustody:
    def _saved_directory(self, episode_id, operation_key):
        return (self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) /
            "rna-structure-comparison-actions" / digest(operation_key))

    def _assignment(self, context, *, allow_unsaved=False):
        authenticate_rna_results_commission(self.store, context, allow_unsaved=allow_unsaved)
        _require(self.applies(context), "original_results_owner_required")
        assignment = plain(context.assignment)
        _require(set(assignment) == {"version", "handoff_ref", "selector"}
            and assignment["version"] == "execution_results_assignment_v1", "selected_assignment_conflict")
        selector = validate_rna_comparison_selector(assignment["selector"])
        validate_rna_comparison_selected_inputs(self.store, context, selector,
            anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)
        return assignment

    def _intent(self, context, assignment, target, operation_key, tool_name, arguments, selected):
        return {"run_id": context.run_id, "episode_id": context.episode_id,
            "scope": plain(context.scope), "assignment": assignment, "anchor_target": target,
            "operation_key": operation_key, "tool_name": tool_name, "arguments": arguments,
            "selected_action_digest": digest(json.loads(selected["action"]))}

    @staticmethod
    def _outcome(body):
        return {"status": "completed", "record_refs": [], "changed_record_refs": [],
            "result": deepcopy(body), "feedback": None}

    def _validate_body(self, body, scope):
        _require(type(body) is dict and set(body) == FIELDS and body["version"] == VERSION
            and body["run_id"] == self.owner.run_id, "receipt_mismatch")
        context = self.records.context(body["episode_id"])
        assignment = self._assignment(context)
        self.store.validate_scope(plain(context.scope), parent_scope=plain(scope))
        _require(body["scope_key"] == digest(plain(context.scope))
            and body["assignment_digest"] == digest(assignment)
            and body["anchor_handoff_ref"] == assignment["handoff_ref"]
            and self.records._equal(body["selector"], assignment["selector"]), "receipt_mismatch")
        _require(body["tool_name"] in {item["name"] for item in operation_catalog()}
            and type(body["arguments"]) is dict and not body["arguments"], "selected_action_mismatch")
        selected = self.owner._selected_result_action(body["episode_id"], body["operation_key"],
            body["tool_name"], body["arguments"])
        _require(body["selected_action_digest"] == digest(json.loads(selected["action"])), "selected_action_mismatch")
        directory = self._saved_directory(body["episode_id"], body["operation_key"])
        target = self.owner.job_progress_provider.targets.read_target(assignment["handoff_ref"], context.scope)
        expected_intent = self._intent(context, assignment, target, body["operation_key"],
            body["tool_name"], body["arguments"], selected)
        _require(self.records._equal(_read(directory / "intent.json"), expected_intent)
            and self.records._equal(_read(directory / "receipt.json"), body), "immutable_receipt_mismatch")
        if selected["result"] is not None:
            outcome, expected = json.loads(selected["result"]), self._outcome(body)
            _require(set(outcome) == {*expected, "pending_work_after_action"}
                and self.records._equal({key: outcome[key] for key in expected}, expected), "recorded_outcome_mismatch")
            from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending
            validate_pending(outcome["pending_work_after_action"])
        _require(body["original_receipt_keys"] == _original_keys(assignment["selector"])
            and body["calculator_version"] == CALCULATOR_VERSION and type(body["delivery_complete"]) is bool,
            "receipt_mismatch")
        for issue in body["issues"]:
            validate_rna_comparison_issue(issue)
        if body["tool_name"] == "execution.results.status" or (directory / "input-failure.json").exists():
            status = body["tool_name"] == "execution.results.status"
            failure = _read(directory / ("status.json" if status else "input-failure.json"))
            _require(type(failure) is dict and set(failure) == {"issues", "cause"}
                and self.records._equal(failure["issues"], body["issues"]), "custody_record_mismatch")
            if failure["issues"]:
                _require(len(failure["issues"]) == 1 and type(failure["cause"]) is dict
                    and set(failure["cause"]) == {"exception_type", "detail"}, "custody_record_mismatch")
                problem = failure["issues"][0]
                expected = {"stage": "input", "code": problem["code"], "member_id": problem["member_id"],
                    "comparison_id": None, "selection_id": None, "field": None, "index": None}
                _require(problem == expected and problem["code"] in {"retained_sheet_missing", "retained_sheet_digest_mismatch"}
                    and any(m["member_id"] == problem["member_id"] and m["kind"] == "saved_sheet"
                        for m in assignment["selector"]["question"]["membership"]), "custody_record_mismatch")
            else:
                _require(status and failure["cause"] is None, "custody_record_mismatch")
            _require(not body["delivery_complete"] and body["projection_rows"] == []
                and body["selected_input_digests"] == [] and body["preparation_failure"] is None
                and all(body[key] is None for key in ("comparison_sheet_artifact_ref", "comparison_sheet_sha256",
                    "components_artifact_ref", "components_sha256")), "receipt_mismatch")
        else:
            from gene_annotation_episode.episodic_workflow.root.library.rna_structure_comparison_publication import validate_prepared_rna_comparison
            operands = self._resolve_operands(context, assignment)
            prepared = _read(directory / "grading" / "prepared.json")
            validate_prepared_rna_comparison(self.store, prepared, selector=assignment["selector"],
                operands=operands, result_receipt_key=result_receipt_key(body))
            _require(all(self.records._equal(body[key], prepared[key]) for key in PREPARED_COPY_FIELDS), "prepared_receipt_mismatch")
        return deepcopy(body)

    def read_result(self, context, result):
        self.records.authenticate(context, allow_unsaved=True)
        _require(type(result) is dict and result.get("episode_id") == context.episode_id
            and result.get("assignment_digest") == digest(plain(context.assignment)), "original_context_conflict")
        return self._validate_body(result, context.scope)

    def read_receipt_key(self, key, scope, *, assignment=None):
        directory = self.directory / digest(key)
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            pointer = _read(path)
            _require(type(pointer) is dict and set(pointer) == {"run_id", "episode_id", "operation_key"}
                and pointer["run_id"] == self.owner.run_id, "receipt_pointer_mismatch")
            body = self._validate_body(_read(self._saved_directory(pointer["episode_id"], pointer["operation_key"]) / "receipt.json"), scope)
            _require(key == result_receipt_key(body), "receipt_pointer_mismatch")
            if assignment is None or body["assignment_digest"] == digest(plain(assignment)):
                return body
        raise ValueError("rna_comparison_original_receipt_mismatch")

    def _own_bodies(self, context):
        self.records.authenticate(context, allow_unsaved=True)
        _require(self.applies(context), "original_results_owner_required")
        directory = self._saved_directory(context.episode_id, "unused").parent
        bodies = [_read(path) for path in directory.glob("*/receipt.json")] if directory.exists() else []
        for body in sorted(bodies, key=lambda item: int(item["operation_key"].rsplit(":", 1)[1])):
            _require(body["episode_id"] == context.episode_id and body["assignment_digest"] == digest(plain(context.assignment)), "receipt_mismatch")
            yield self._validate_body(body, context.scope)

