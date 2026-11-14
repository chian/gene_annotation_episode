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

class RnaResultFacts:
    def saved_descriptor(self, body, *, verify_bytes=True):
        prepared = body["prepared"]
        if prepared is None or prepared["sheet_artifact_ref"] is None:
            return None
        if body["assignment"]["selector"]["acquisition"] == "retained_sheet_only":
            return deepcopy(body["assignment"]["selector"]["saved_input"])
        metadata = self.store.get(prepared["sheet_artifact_ref"])
        if verify_bytes:
            retained(self.store, metadata["id"])
        job = body["target"]["assignment"]["requested_job"]["native_rna_structure"]
        return validate_saved_rna_input({"schema": "rna_structure_saved_sheet_input_v1",
            "result_receipt_key": result_receipt_key(body), "handoff_ref": body["assignment"]["handoff_ref"],
            "source_ref": body["source_ref"], "bundle_artifact_ref": body["capture"]["bundle_artifact_ref"],
            "sheet_artifact_ref": metadata["id"], "sheet_sha256": metadata["sha256"],
            **{key: job[key] for key in ("record_key", "operation", "mode")}})

    def _own_bodies(self, context, *, verify_artifacts=False):
        # Initial typed facts are requested before the new episode row exists.
        # Any actual receipt below still requires its saved original context.
        self.records.authenticate(context, allow_unsaved=True)
        directory = self._saved_directory(context.episode_id, "unused").parent
        bodies = [_read(path) for path in directory.glob("*/receipt.json")] if directory.exists() else []
        for body in sorted(bodies, key=lambda item: int(item["operation_key"].rsplit(":", 1)[1])):
            require(body["episode_id"] == context.episode_id and body["assignment"] == plain(context.assignment))
            yield self._validate_body(body, context.scope, verify_artifacts=verify_artifacts)

    def facts(self, context, *, verify_artifacts=True):
        requested = {node.get("x-source") for node in (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {}).get("properties", {}).values()}
        bodies = list(self._own_bodies(context, verify_artifacts=verify_artifacts))
        refs = list(dict.fromkeys(ref for body in bodies for ref in body["record_refs"]))
        result = {"execution_handoff_refs": [], "execution_blast_hsps": [], "execution_result_refs": refs,
            REFERENCE_SOURCE: refs, SAVED_SOURCE: [], **{source: [] for source in FAMILY_SOURCES.values()},
            "execution_completed": any(body["delivery_complete"] for body in bodies),
            "execution_result_origin": deepcopy(ORIGIN) if any(body["native_success"] and body["capture_complete"] and
                body["assignment"]["selector"]["acquisition"] == "complete_bound_bundle" for body in bodies) else None}
        for body in bodies:
            selector = body["assignment"]["selector"]
            family = selector["projection"]["family"]
            if FAMILY_SOURCES[family] in requested and family != "failure":
                result[FAMILY_SOURCES[family]].extend(body["rows"])
            if FAMILY_SOURCES["failure"] in requested:
                result[FAMILY_SOURCES["failure"]].extend(project_rna_structure_failure_rows(body,
                    selector=selector if family == "failure" else None))
            if SAVED_SOURCE in requested:
                descriptor = self.saved_descriptor(body, verify_bytes=verify_artifacts)
                if descriptor is not None:
                    result[SAVED_SOURCE].append(descriptor)
        for source in (*FAMILY_SOURCES.values(), SAVED_SOURCE):
            distinct = []
            for row in result[source]:
                if row not in distinct:
                    distinct.append(row)
            result[source] = distinct
        return result

    def result_identity(self, reference, scope):
        return digest(self._bundle(self.read_result(reference, scope))["identity"])

    def resolve(self, context, reference, namespace):
        if not self.applies(context):
            return False
        facts = self.facts(context)
        rows = [row for source in FAMILY_SOURCES.values() for row in facts[source]]
        key = dict(zip(IDENTIFIER_NAMESPACES, ("row_key", "calculation_key", "result_receipt_key"))).get(namespace)
        if key:
            return any(row.get(key) == reference for row in rows) or namespace == IDENTIFIER_NAMESPACES[2] and any(
                row["result_receipt_key"] == reference for row in facts[SAVED_SOURCE])
        allowed = set(facts[REFERENCE_SOURCE])
        allowed.update(row[name] for row in facts[SAVED_SOURCE] for name in ("handoff_ref", "source_ref", "bundle_artifact_ref", "sheet_artifact_ref"))
        if reference not in allowed:
            return False
        return namespace not in {"source", "artifact"} or self.store.get(reference)["record_type"] == namespace

    def retained_reference_access(self, context, reference, namespace):
        return retained_reference_access(self, context, reference, namespace)


