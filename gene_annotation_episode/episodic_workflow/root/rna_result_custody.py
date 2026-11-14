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

class RnaResultCustody:
    def _saved_directory(self, episode_id, operation_key):
        return (self.owner.directory / "execution-results" / digest([self.owner.run_id, episode_id]) /
            "native-rna-structure-actions" / digest(operation_key))

    def _context(self, body):
        context = self.records.context(body["episode_id"])
        authenticate_rna_results_commission(self.store, context)
        require(context.role == "results" and plain(context.assignment) == body["assignment"]
            and plain(context.scope) == body["scope"])
        return context

    def _selector(self, assignment, target):
        from gene_annotation_episode.episodic_workflow.root.execution_source_declarations import RESULTS_SCHEMA
        assignment = checked(assignment, RESULTS_SCHEMA, "rna_invalid_input_schema")
        require(is_native_rna_structure_target(target))
        return validate_rna_structure_result_selector(assignment["selector"],
            mode=target["assignment"]["requested_job"]["native_rna_structure"]["mode"])

    def _bundle(self, body):
        return decode_json(self.store.get_artifact(body["capture"]["bundle_artifact_ref"]), canonical_bytes=True)

    def _validate_body(self, body, scope, *, verify_artifacts=False):
        # Authority can be checked before opening saved sheet bytes. Their later
        # absence is a calculation qualification, never permission to reacquire.
        require(type(body) is dict and set(body) == FIELDS and body["version"] == VERSION
            and body["run_id"] == self.owner.run_id)
        context = self._context(body)
        self.store.validate_scope(body["scope"], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body["assignment"]["handoff_ref"], body["scope"])
        require(target == body["target"])
        selector = self._selector(body["assignment"], target)
        require(body["tool_name"] in {item["name"] for item in operation_catalog()} and body["arguments"] == {})
        selected = self.owner._selected_result_action(body["episode_id"], body["operation_key"], body["tool_name"], body["arguments"])
        directory = self._saved_directory(body["episode_id"], body["operation_key"])
        require(_read(directory / "receipt.json") == body)
        require(_read(directory / "intent.json") == {key: body[key] for key in
            ("target", "assignment", "operation_key", "tool_name", "arguments", "scope")})
        require(_read(directory / "observation.json") == body["observation"])
        validate_resource_observation(body["observation"])
        if selected["result"] is not None:
            outcome = json.loads(selected["result"])
            expected = self._outcome(body)
            require(set(outcome) in (set(expected), {*expected, "pending_work_after_action"}) and
                self.records._equal({key: outcome[key] for key in expected}, expected))
            if "pending_work_after_action" in outcome:
                from gene_annotation_episode.episodic_workflow.root.waiting import validate_pending
                validate_pending(outcome["pending_work_after_action"])
        failures = [validate_rna_issue(value) for value in body["failures"]]
        saved = selector["acquisition"] == "retained_sheet_only"
        collecting = body["tool_name"] == "execution.results.collect"
        bundle = None
        if saved:
            original = self.owner.native_rna_structure_returns.resolve_saved_rna_input(context, selector["saved_input"])
            require(all(body[key] == original[key] for key in ("target", "observation", "capture", "native_success", "capture_complete")))
            if collecting:
                require(body["source_ref"] == original["source_ref"])
                bundle = self._bundle(original)
        elif body["capture"] is not None:
            require(collecting and _read(directory / "capture" / "capture.json") == body["capture"])
            require(_read(directory / "capture" / "capture-intent.json") == {"target": target})
            plan = _read(directory / "capture" / "capture-plan.json")
            if plan is not None:
                qualify_target_plan(target, plan)
            if body["capture"]["bundle_validated"]:
                from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import validate_rna_structure_bundle
                require(plan is not None)
                bundle = validate_rna_structure_bundle(self._bundle(body), plan=plan)
            if verify_artifacts:
                # Validate supplied retained custody directly. Authentication
                # invokes neither capture nor original reservation/filesystem.
                validate_capture(self.store, body["capture"], bundle=bundle)
        else:
            require(not collecting)
        if body["source_ref"] is None:
            require(not body["record_refs"] and not body["rows"] and body["prepared"] is None)
        else:
            require(collecting and bundle is not None and body["record_refs"] == [body["source_ref"]])
            source = self.store.get(body["source_ref"])
            require(source.get("record_type") == "source" and source.get("origin") == "tool" and
                {k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}} ==
                rna_structure_source_payload(bundle=bundle, capture=body["capture"],
                    prepared=original["prepared"] if saved else body["prepared"]))
        publication = None
        if body["prepared"] is not None:
            require(_read(directory / "grading" / "prepared.json") == body["prepared"])
            publication = _read(directory / "publication.json")
            require(all(publication[key] == body[key] for key in ("source_ref", "record_refs", "rows")))
            if verify_artifacts:
                validate_prepared_rna_grading(self.store, body["prepared"], bundle=bundle, capture=body["capture"], selector=selector)
                require(publication == publish_selected_rna_structure_rows(self.store, context,
                    source_ref=body["source_ref"], bundle=bundle, capture=body["capture"], prepared=body["prepared"], selector=selector))
        else:
            require(not body["rows"])
        for row in body["rows"]:
            validate_rna_structure_row(row)
            require(row["family"] == selector["projection"]["family"] and row["source_ref"] == body["source_ref"])
        base_failures = _read(directory / "failure-ledger.json")
        expected = prepare_rna_structure_failure_selection(failures=base_failures, selector=selector,
            record_key=target["assignment"]["requested_job"]["native_rna_structure"]["record_key"])
        require(expected == {"failures": failures, "selection": body["failure_selection"]})
        if collecting and publication is not None:
            require(base_failures == publication["failures"])
        elif collecting and not saved and bundle is None:
            require(base_failures == body["capture"]["failures"])
        elif collecting and bundle is not None and body["prepared"] is None:
            failure = _read(directory / "preparation-failure.json")
            require(base_failures == merge_issues([] if saved else bundle["failures"],
                [] if saved else body["capture"]["failures"], [failure]))
        elif not collecting and not saved:
            require(not base_failures)
        native = saved and body["native_success"] or bundle is not None and bundle["returncode"] == 0 and bundle["native_status"] == "complete"
        capture_complete = body["capture"] is not None and body["capture"]["capture_complete"]
        accounted = (expected["selection"]["requested_rows_accounted_for"] if expected["selection"] is not None
            else publication is not None and publication["requested_cells_accounted_for"])
        sheet_available = body["prepared"] is not None and body["prepared"]["sheet_artifact_ref"] is not None
        complete = collecting and body["source_ref"] is not None and accounted and (sheet_available if saved else capture_complete)
        require(all(type(body[key]) is bool for key in ("native_success", "capture_complete", "delivery_complete")))
        require(body["native_success"] == bool(native) and body["capture_complete"] == bool(capture_complete)
            and body["delivery_complete"] == bool(complete))
        return deepcopy(body)

    @staticmethod
    def _outcome(body):
        return {"status": "completed", "record_refs": body["record_refs"], "changed_record_refs": body["record_refs"],
            "result": body, "feedback": None}

    def _index(self, body):
        pointer = {key: body[key] for key in ("run_id", "episode_id", "operation_key")}
        for reference in [result_receipt_key(body), *body["record_refs"]]:
            directory = self.directory / digest(reference)
            directory.mkdir(parents=True, exist_ok=True)
            _immutable(directory / (digest(body["operation_key"]) + ".json"), pointer)

    def _indexed(self, reference, scope, assignment, *, receipt_key=False):
        directory = self.directory / digest(reference)
        for path in sorted(directory.glob("*.json")) if directory.exists() else []:
            pointer = _read(path)
            require(set(pointer) == {"run_id", "episode_id", "operation_key"} and pointer["run_id"] == self.owner.run_id)
            body = self._validate_body(_read(self._saved_directory(pointer["episode_id"], pointer["operation_key"]) / "receipt.json"), scope)
            require(reference == result_receipt_key(body) if receipt_key else reference in body["record_refs"])
            if assignment is None or body["assignment"] == plain(assignment):
                return body
        raise ValueError("rna_original_attempt_mismatch")

    def read_receipt_key(self, key, scope, *, assignment=None):
        return self._indexed(key, scope, assignment, receipt_key=True)

    def read_result(self, reference, scope, *, assignment=None):
        self.store.get(reference)
        return self._indexed(reference, scope, assignment)

