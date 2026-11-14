"""Bounded grading preparation, actual-context binding and selected RNA delivery.

The host validates custody and original authority. Scientific arithmetic remains
in the pure calculators. No Store observation, annotation score or retry is made.
"""
from __future__ import annotations

from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_contracts import POLICY

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import TYPE_CHECKING
from gene_annotation_episode.episodic_workflow.root.method_loop.identities import EpisodeRef

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.episodic_workflow.root.communication import plain
from gene_annotation_episode.episodic_workflow.root.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import canonical, digest
from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.episodic_workflow.root.library.native_rna_structure_acquisition import decode_json, require, retained, validate_capture, rna_structure_source_payload, publish_rna_structure_source
from gene_annotation_episode.immutable_json_records import _immutable, _read
from gene_annotation_episode.episodic_workflow.root.practical_receipt_information import PracticalReceiptInformation
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_contracts import RNA_ISSUE_CODES, analyze_rna_input_sequence, issue, validate_rna_input, validate_rna_sheet, validate_rna_components, validate_rna_parameters
from gene_annotation_episode.episodic_workflow.root.library.rna_structure_result_views import merge_issues, project_rna_prepublication, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input
from gene_annotation_episode.episodic_workflow.root.library.tool_grading_artifacts import retain_tool_grading, source_tool_gradings

if TYPE_CHECKING:
    from gene_annotation_episode.episodic_workflow.root.native_rna_structure_returns import NativeRNAStructureReturns

from gene_annotation_episode.episodic_workflow.root.library.rna_result_preparation import validate_prepared_rna_grading
from gene_annotation_episode.episodic_workflow.root.library.rna_result_operand_authority import _qualify_original_handoff, validate_rna_structure_publication_inputs

def publish_selected_rna_structure_rows(store, context, *, source_ref, bundle, capture, prepared, selector):
    EpisodeReturnRecords(store, context.run_id, failure_prefix="rna_").authenticate(context)
    require(context.role == "results" and plain(context.assignment)["selector"] == selector)
    scope = store.validate_scope(plain(context.scope))
    require(bundle["identity"]["run_id"] == context.run_id)
    _qualify_original_handoff(store, context, bundle)
    if selector["acquisition"] == "complete_bound_bundle":
        validate_capture(store, capture, bundle=bundle)
    source = store.get(source_ref)
    expected = rna_structure_source_payload(bundle=bundle, capture=capture, prepared=prepared)
    require(source.get("record_type") == "source" and source.get("origin") == "tool" and
        {k: v for k, v in source.items() if k not in {"id", "record_type", "origin"}} == expected)
    checked = validate_prepared_rna_grading(store, prepared, bundle=bundle, capture=capture, selector=selector)
    require(checked["stable"] in source_tool_gradings(store, source_ref), "rna_invalid_component_schema")
    failures, binding = deepcopy(prepared["failures"]), None
    sheet, components, document = (checked[name] for name in ("sheet", "components", "document"))
    binding_failed = False
    if sheet is not None:
        try:
            binding = validate_rna_structure_publication_inputs(store, context, original_input=sheet["original_input"], capture=capture)
        except ValueError:
            binding_failed = True
            failures = merge_issues(failures, [issue("rna_subject_binding_conflict", stage="binding",
                record_key=bundle["record_key"], field="/subject_binding")])
    rows = []
    for pre in [] if document is None else document["rows"]:
        row = {key: deepcopy(value) for key, value in pre.items() if key not in ("ordinal", "sheet_status", "cells")}
        row.update(source_ref=source_ref, subject_ref=None if binding is None else binding["subject_ref"],
            calculation_key="rna_calculation:" + store.get(prepared["components_artifact_ref"])["sha256"],
            calculation_parameters=deepcopy(components["parameters"]), measurements=[], unavailable=[])
        for cell in pre["cells"]:
            names = ("name", "value", "unit", "numerator", "denominator", "origin") if cell["state"] == "present" else (
                "name", "state", "reason", "unit", "numerator", "denominator", "origin")
            row["measurements" if cell["state"] == "present" else "unavailable"].append({key: cell[key] for key in names})
        row["status"] = ("invalid" if pre["sheet_status"] == "invalid" else "partial" if pre["sheet_status"] == "partial" or row["unavailable"] or binding_failed
            else "bound" if binding is not None else "unbound")
        if binding_failed and "rna_subject_binding_conflict" not in row["qualification_codes"]:
            row["qualification_codes"].append("rna_subject_binding_conflict")
        rows.append(validate_rna_structure_row(row))
    return {"version": "native_rna_structure_publication_v1", "source_ref": source_ref, "record_refs": [source_ref],
        "rows": rows, "failures": failures, "requested_cells_accounted_for": prepared["requested_cells_accounted_for"]}
