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

class RnaComparisonResultFacts:
    def facts(self, context, *, verify_artifacts=True):
        # Authority and actual calculation are always checked. The argument
        # preserves the host port; it is not a validation bypass.
        requested = {node.get("x-source") for node in (plain(context.request).get("report_contract") or {})
            .get("measurements", {}).get("schema", {}).get("properties", {}).values()}
        bodies = list(self._own_bodies(context))
        rows, seen, completed = [], set(), False
        for body in bodies:
            action = self.owner._selected_result_action(context.episode_id, body["operation_key"], body["tool_name"], body["arguments"])
            if action["result"] is None:
                continue
            completed = completed or body["delivery_complete"]
            if PROJECTION_SOURCE in requested:
                for row in body["projection_rows"]:
                    identity = canonical({key: value for key, value in row.items() if key != "result_receipt_key"})
                    if identity not in seen:
                        rows.append(row)
                        seen.add(identity)
        return {PROJECTION_SOURCE: rows, "execution_handoff_refs": [], "execution_blast_hsps": [],
            "execution_result_refs": [], "execution_completed": completed, "execution_result_origin": None}

    def resolve(self, context, reference, namespace):
        if not self.applies(context) or namespace not in IDENTIFIER_NAMESPACES:
            return False
        field = "result_receipt_key" if namespace == IDENTIFIER_NAMESPACES[0] else "calculation_key"
        return any(row[field] == reference for row in self.facts(context)[PROJECTION_SOURCE])

    def retained_reference_access(self, context, reference, namespace):
        # Symbolic receipt identities confer no Store custody, even when a
        # caller supplies an artifact/source namespace for the same string.
        if any(reference.startswith(prefix + ":") for prefix in IDENTIFIER_NAMESPACES):
            return self.resolve(context, reference, namespace)
        if namespace not in {None, "artifact", "source", "execution_result", "execution_handoff"}:
            return None
        if self.applies(context):
            assignment = plain(context.assignment)
            selected = [assignment["handoff_ref"]]
            selected_handoffs = {assignment["handoff_ref"]}
            for member in assignment["selector"]["question"]["membership"]:
                if member["kind"] == "saved_sheet":
                    selected.extend(member["saved_input"][key] for key in SAVED_REFERENCE_FIELDS)
                    selected_handoffs.add(member["saved_input"]["handoff_ref"])
                elif member["kind"] == "received_failure" and member["failure"]["source_ref"] is not None:
                    selected.append(member["failure"]["source_ref"])
            if namespace == "execution_handoff" and reference not in selected_handoffs:
                return False
            if reference in selected:
                allowed = validate_rna_comparison_selected_inputs(self.store, context, assignment["selector"],
                    anchor_handoff_ref=assignment["handoff_ref"], returns=self.returns)
                record = self.store.get(reference)
                return reference in allowed and namespace in {None, "execution_result", record["record_type"],
                    *({"execution_handoff"} if reference in selected_handoffs else set())}
        # Comparison artifacts are internal, and are absent from admitted refs.
        # Recognize exact recorded custody without opening their scientific data.
        for action in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND "
                "json_extract(result,'$.result.version')=?", (self.owner.run_id, VERSION)):
            body = json.loads(action["result"])["result"]
            grading = self._saved_directory(body["episode_id"], body["operation_key"]) / "grading"
            prepared_path = grading / "prepared.json"
            prepared = _read(prepared_path) if prepared_path.exists() else None
            refs = {body[key] for key in ("comparison_sheet_artifact_ref", "components_artifact_ref")}
            if prepared is not None:
                refs.update(value for key, value in prepared.items() if key.endswith("artifact_ref"))
            # Fixed host custody metadata names every internal worker artifact.
            # Do not open scientific inputs, projections, logs or source trees.
            worker_path = grading / "worker-receipt.json"
            if worker_path.exists():
                worker = _read(worker_path)
                refs.update(value for key, value in worker.items() if key.endswith("artifact_ref"))
                refs.update(row["artifact_ref"] for row in worker["output_artifacts"])
                refs.add(worker["input_observation"]["artifact_ref"])
            execution_path = grading / "execution-receipt.json"
            if execution_path.exists():
                execution = _read(execution_path)
                refs.update(execution[key] for key in ("stdout_artifact_ref", "stderr_artifact_ref"))
            if reference in refs:
                return self._independent_artifact_access(context, reference, namespace)
        return None

    def _independent_artifact_access(self, context, reference, namespace):
        """Preserve actual explicit custody of identical content-addressed bytes."""
        self.records.authenticate(context, allow_unsaved=True)
        if namespace not in {None, "artifact", "execution_result"}:
            return False
        old = self.owner.native_rna_structure_results.retained_reference_access(context, reference, namespace)
        if old is not None:
            return old
        assignment = plain(context.assignment)
        explicit = {row.get("artifact_ref") for row in
            assignment.get("requested_job", {}).get("native_rna_structure", {}).get("operands", [])}
        if reference in explicit:
            from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import validate_rna_structure_job_inputs
            return reference in validate_rna_structure_job_inputs(self.store, context, assignment)
        if reference in self.store._refs(assignment) and reference in set(
                EpisodeReceipts(self.store, context.run_id).known(context.episode_id, baseline=True)):
            return True
        scope = self.store.validate_scope(plain(context.scope))
        if any(self.store.get(subject).get("sequence_ref") == reference for subject in scope.get("subject_refs", [])):
            return namespace in {None, "artifact"}
        for action in self.store.db.execute("SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL",
                (context.run_id, context.episode_id)):
            outcome = json.loads(action["result"])
            if outcome.get("status") in {"completed", "partial"} and reference in outcome.get("record_refs", []):
                body = outcome.get("result")
                if isinstance(body, dict) and body.get("version") == VERSION:
                    self._validate_body(body, context.scope)
                return True
        old = self.returns.resolve_received(context, reference, namespace)
        if old is not None:
            return old
        from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import requested_sources
        for attempt in self.returns._attempts(context):
            schema = json.loads(attempt["contract"]).get("measurements", {}).get("schema", {})
            if requested_sources(schema) or any(node.get("x-source") == PROJECTION_SOURCE
                    for node in schema.get("properties", {}).values()):
                continue
            _, form, schema = self.returns._attempt(context, attempt["decision_index"])
            explicit_refs = []
            def collect(value, declared_namespace):
                if declared_namespace in {None, "artifact"}:
                    explicit_refs.append(value)
                return True
            validate_form(form, schema, collect)
            if reference in explicit_refs:
                return True
        return False

